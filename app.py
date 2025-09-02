import os
import json
import random
from datetime import datetime, timedelta
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# For YouTube and Spotify APIs
from googleapiclient.discovery import build
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# Load environment variables from .env file
load_dotenv()

# --- DATABASE SETUP ---
DATABASE = 'chatbot.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# --- API CLIENT SETUP ---
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)) if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET else None


# Configure Flask app
app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24) # Necessary for session management
CORS(app)

# Initialize the database
init_db()

# Configure Gemini AI
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Error configuring Gemini AI: {e}")
    model = None

# --- ENHANCED SYSTEM PROMPT FOR CONVERSATIONAL AWARENESS ---
SYSTEM_PROMPT = """
You are a conversation-aware AI assistant. Your primary job is to analyze the user's query, considering the **entire conversation history**, and convert it into a specific JSON command.
You have access to the current date, which is {current_date}.
Respond in a single, minified JSON format ONLY.

**Core Task: Generate a JSON Command**

1.  **Instructional Queries**: If the user wants you to *do* something (play, search, get info), the JSON output must have:
    - "action": "instruction"
    - "instruction": A list of command objects.

2.  **Conversational Queries**: If the user is asking a general question, greeting you, or making small talk, the JSON output must have:
    - "action": "conversation"
    - "speech": Your friendly, professional reply as a string.

**NEW: Contextual Understanding & Follow-up Commands**
You MUST use the conversation history to understand vague follow-up queries. Infer the user's intent from the last command you executed.

* **Example 1: Repeating an action**
    * History -> User: "play a random video"
    * Current Query -> User: "another one"
    * Your Logic: The user wants to repeat the last action. You should generate a NEW random video topic.
    * Your JSON Output: {{"action":"instruction","instruction":[{{"play_youtube_direct":"astrophysics documentary"}}]}}

* **Example 2: Modifying an action**
    * History -> User: "what's the weather in london?"
    * Current Query -> User: "what about in paris?"
    * Your Logic: The user is asking for the weather again, but for a new city.
    * Your JSON Output: {{"action":"instruction","instruction":[{{"get_weather":"paris"}}]}}

**NEW: Specific Command Handling for Vague Requests**
* **For YouTube:** If the user asks to "play a video", "play something about space", "play music", or any other vague video request without a specific title, you MUST generate a relevant and creative search query yourself. For example, if the user says "play something funny", you could generate `{{"action":"instruction","instruction":[{{"play_youtube_direct":"try not to laugh challenge"}}]}}`. If they say "no music", you must pick a non-music topic like "popular science videos".
* **For Spotify:** If the user asks to "play a song" or "play music" without specifying a title, you MUST choose a popular, well-known song title from your own knowledge and use it as the value. Do not use a placeholder. Example: A user says "play a song" and you generate `{{"action":"instruction","instruction":[{{"play_spotify_direct":"Stairway to Heaven"}}]}}`.

**Supported Command Objects:**
- {{"play_youtube_direct": "video_name"}}
- {{"play_spotify_direct": "song_or_artist_name"}}
- {{"search_google": "search_term"}}
- {{"get_time": "current"}}
- {{"get_date": "query"}} (e.g., "full_date", "year", "last_year")
- {{"get_weather": "city_name"}}
- {{"open_website": "website_name"}}
- {{"send_whatsapp": {{"number": "phone_number", "message": "your_message"}}}}
"""

# --- HELPER FUNCTIONS ---

def get_youtube_video_url(search_term):
    if not youtube:
        return None, "YouTube API is not configured."
    try:
        # Search for a list of videos instead of just one
        search_response = youtube.search().list(
            q=search_term,
            part='id',
            maxResults=5, # Get 5 results to have a better chance of finding an embeddable one
            type='video'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        if not video_ids:
            return None, f"I couldn't find any YouTube videos for '{search_term}'."

        # Check the status of each video to see if it's embeddable
        video_details_response = youtube.videos().list(
            part='status',
            id=','.join(video_ids)
        ).execute()

        # Find the first embeddable video
        for item in video_details_response.get('items', []):
            if item['status']['embeddable']:
                embeddable_video_id = item['id']
                return f"https://www.youtube.com/embed/{embeddable_video_id}", f"Playing the top result for '{search_term}' on YouTube."

        # If no embeddable videos were found in the top results
        return None, f"Sorry, I found videos for '{search_term}', but none of them can be played here."

    except Exception as e:
        print(f"YouTube API Error: {e}")
        return None, f"Sorry, I couldn't find a video for '{search_term}' on YouTube."


def get_spotify_track_url(search_term):
    if not spotify:
        return None, "Spotify API is not configured."
        
    try:
        results = spotify.search(q=f'track:{search_term}', type='track', limit=1)
        if not results or not results['tracks']['items']:
            return None, f"Sorry, I couldn't find the song '{search_term}' on Spotify."
        
        track = results['tracks']['items'][0]
        track_id = track['id']
        track_name = track['name']
        track_url = f"https://open.spotify.com/embed/track/{track_id}"
        return track_url, f"Playing '{track_name}' on Spotify."
    except Exception as e:
        print(f"Spotify API Error: {e}")
        return None, f"Sorry, I couldn't play '{search_term}' on Spotify."


def get_weather(city):
    if not WEATHER_API_KEY:
        return "Weather API key is not configured."
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        description = data['weather'][0]['description']
        temp = data['main']['temp']
        return f"The weather in {city} is currently {description} with a temperature of {temp}°C."
    except requests.exceptions.RequestException as e:
        print(f"Weather API error: {e}")
        return f"Sorry, I couldn't fetch the weather for {city}."
    except KeyError:
        return f"Sorry, I couldn't find weather data for {city}."

# --- MAIN AND AUTHENTICATION ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            return redirect(url_for('chatbot'))
        else:
            flash('Invalid credentials. Please try again.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            flash('Username already exists.')
            conn.close()
        else:
            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))
    return render_template('signup.html')
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chatbot')
def chatbot():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('chatbot.html')

# --- API ROUTES ---

@app.route('/api/chat', methods=['POST'])
def chat_api():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    if not model:
        return jsonify({"action": "conversation", "speech": "AI model is not configured."}), 500

    user_id = session.get('user_id')
    user_query = request.json.get('message')
    if not user_query:
        return jsonify({"error": "No message provided"}), 400

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Build history string from DB
        cursor.execute("SELECT user_message, bot_response FROM conversations WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
        history_rows = cursor.fetchall()
        history_str = "\n".join([f"User: {row[0]}\nAI: {row[1]}" for row in history_rows])

        today_str = datetime.now().strftime("%A, %B %d, %Y")
        prompt_with_date = SYSTEM_PROMPT.format(current_date=today_str)
        
        full_prompt = f"{prompt_with_date}\n\n--- Conversation History ---\n{history_str}\n\n--- Current Query ---\nUser: \"{user_query}\""
        response = model.generate_content(full_prompt)
        response_text = response.text.strip().replace('```json', '').replace('```', '')
        response_json = json.loads(response_text)
        
        bot_response_text = ""
        # --- SERVER-SIDE ACTION PROCESSING ---
        if response_json.get("action") == "instruction":
            final_instructions = []
            confirmation_speech = []
            for instr in response_json.get("instruction", []):
                command = list(instr.keys())[0]
                value = instr[command]
                if command == "get_time":
                    now = datetime.now()
                    current_time = now.strftime("%I:%M %p")
                    confirmation_speech.append(f"The current time is {current_time}.")
                elif command == "get_date":
                    now = datetime.now()
                    if value == "full_date": confirmation_speech.append(f"Today is {now.strftime('%A, %B %d, %Y')}.")
                    elif value == "year": confirmation_speech.append(f"The current year is {now.year}.")
                    elif value == "last_year": confirmation_speech.append(f"Last year was {now.year - 1}.")
                    else: confirmation_speech.append(f"The date today is {now.strftime('%Y-%m-%d')}.")
                elif command == "get_weather":
                    confirmation_speech.append(get_weather(value))
                elif command == "play_youtube_direct":
                    url, speech = get_youtube_video_url(value)
                    if url: final_instructions.append({"open_url": url})
                    confirmation_speech.append(speech)
                elif command == "play_spotify_direct":
                    url, speech = get_spotify_track_url(value)
                    if url: final_instructions.append({"open_url": url})
                    confirmation_speech.append(speech)
                else:
                    final_instructions.append(instr)

            final_response = {}
            if confirmation_speech:
                final_response["action"] = "instruction_and_conversation"
                final_response["speech"] = " ".join(confirmation_speech)
                final_response["instruction"] = final_instructions
            else:
                final_response = response_json
                final_response['instruction'] = final_instructions
            
            bot_response_text = final_response.get("speech", "Executing instruction.")
            cursor.execute("INSERT INTO conversations (user_id, user_message, bot_response) VALUES (?, ?, ?)",
                           (user_id, user_query, bot_response_text))
            conn.commit()
            return jsonify(final_response)

        bot_response_text = response_json.get("speech")
        cursor.execute("INSERT INTO conversations (user_id, user_message, bot_response) VALUES (?, ?, ?)",
                       (user_id, user_query, bot_response_text))
        conn.commit()
        return jsonify(response_json)

    except json.JSONDecodeError:
        print(f"Error decoding JSON from model response: {response_text}")
        return jsonify({"action": "conversation", "speech": "I'm having a little trouble understanding. Could you rephrase that?"}), 500
    except Exception as e:
        print(f"An error occurred in /api/chat: {e}")
        return jsonify({"action": "conversation", "speech": "I'm sorry, an unexpected error occurred. Please try again."}), 500
    finally:
        conn.close()

@app.route('/api/history', methods=['GET'])
def get_history():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session.get('user_id')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_message, bot_response FROM conversations WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
    history_rows = cursor.fetchall()
    conn.close()
    
    history_list = [{"user": row[0], "bot": row[1]} for row in history_rows]
    return jsonify(history_list)

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session.get('user_id')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "History cleared successfully."})

if __name__ == '__main__':
    app.run(debug=True)

