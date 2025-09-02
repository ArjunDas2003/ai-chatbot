# AI Assistant Web Application

This is a fully-featured, conversation-aware AI assistant built with a Flask backend and a dynamic, modern frontend. The assistant can play media from YouTube and Spotify, provide real-time information like weather and time, and maintains a persistent chat history for each user, allowing for contextual follow-up questions.

## Features

* **User Authentication**: Secure login, signup, and session management.
* **Persistent Memory**: User data and conversation histories are stored in a **SQLite database**.
* **Conversation-Aware AI**: The chatbot remembers previous parts of the conversation to understand context (e.g., "play another one").
* **Interactive Media Player**: Plays YouTube videos and Spotify tracks directly on the page in an embedded player.
* **Rich Commands**:
    * Play specific or random music/videos from YouTube & Spotify.
    * Get the current time and date.
    * Fetch real-time weather information for any city.
    * Open websites and search Google.
    * Send messages via WhatsApp Web.
* **Voice-to-Text**: Use your microphone to talk to the assistant.
* **Modern UI**: A clean, stylish interface with a purple-themed aesthetic and dynamic background animations.
* **Fully Responsive**: Works seamlessly on both desktop and mobile devices.

## Project Structure

```
/
|-- app.py                  # The core Flask backend application
|-- requirements.txt        # Python dependencies
|-- .env                    # Environment variables (API keys)
|-- database.db             # SQLite database file (created on first run)
|-- templates/
|   |-- index.html          # The main landing page
|   |-- login.html          # User login page
|   |-- signup.html         # User registration page
|   |-- chatbot.html        # The main chatbot interface
|-- README.md               # This file
|-- api_design.md           # Documentation for the AI's JSON format
```

## Installation and Setup

**1. Clone the Repository**

```bash
git clone https://github.com/ArjunDas2003/ai-chatbot.git
```
```bash
cd ai-chatbot
```

**2. Create a Python Virtual Environment**

```bash
# For Windows
python -m venv venv
venv\Scripts\activate

# For macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**

```bash
pip install -r requirements.txt
```

**4. API Key Setup (Crucial Step)**

This project requires several API keys to function correctly. Follow the steps below to get them, then create a file named `.env` in the root of the project and add them to it.

**I. Google APIs (Gemini & YouTube)**

You'll need two keys from Google.

* **Gemini API Key (for the AI model):**
    1.  Go to **Google AI Studio**: <https://aistudio.google.com/>
    2.  Sign in with your Google account.
    3.  Click on "**Get API key**" and then "**Create API key in new project**".
    4.  Copy the generated key. In your `.env` file, add: `GEMINI_API_KEY="YOUR_GEMINI_KEY"`

* **YouTube Data API v3 Key (for video search):**
    1.  Go to the **Google Cloud Console**: <https://console.cloud.google.com/>
    2.  Create a new project (or select an existing one).
    3.  In the search bar at the top, type "**YouTube Data API v3**" and select it.
    4.  Click the "**ENABLE**" button.
    5.  Once enabled, go to "**Credentials**" from the left-hand menu.
    6.  Click "**+ CREATE CREDENTIALS**" at the top and select "**API key**".
    7.  Copy the key. In your `.env` file, add: `YOUTUBE_API_KEY="YOUR_YOUTUBE_KEY"`

**II. Spotify API (for music search)**

1.  Go to the **Spotify Developer Dashboard**: <https://developer.spotify.com/dashboard/>
2.  Log in with your Spotify account.
3.  Click "**Create app**". Give it a name and description.
4.  You may be asked for a **Redirect URI**. For this project's local setup, you can add `http://127.0.0.1:5000/` and save. This step is necessary for Spotify to authorize your application.
5.  Once the app is created, you will see your **Client ID** and a button to show your **Client Secret**.
6.  Copy both credentials. In your `.env` file, add:
    ```
    SPOTIPY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID"
    SPOTIPY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET"
    ```

**III. OpenWeatherMap API (for weather data)**

1.  Go to **OpenWeatherMap**: <https://openweathermap.org/>
2.  Create a free account.
3.  After signing in, click on your username in the top right and go to "**My API keys**".
4.  You will find a default API key already generated for you.
5.  Copy the key. In your `.env` file, add: `WEATHER_API_KEY="YOUR_OPENWEATHER_KEY"`

**5. Create the `.env` file**

Your final `.env` file in the root directory should look like this, filled with the keys you obtained:

```
GEMINI_API_KEY="YOUR_GEMINI_KEY"
YOUTUBE_API_KEY="YOUR_YOUTUBE_KEY"
SPOTIPY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID"
SPOTIPY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET"
WEATHER_API_KEY="YOUR_OPENWEATHER_KEY"
FLASK_SECRET_KEY="YOUR_OWN_RANDOM_SECRET_KEY"
```

**Important:** You will also need a `FLASK_SECRET_KEY` for session management. You can generate a random string for this.

**6. Run the Application**

```bash
flask run
```
