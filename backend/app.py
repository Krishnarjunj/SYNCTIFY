import os
from flask import Flask, jsonify, request, redirect, session
from flask import Response, stream_with_context
from youtube_client import YouTubeClient
from spotify_client import (
    sp_oauth,
    get_auth_url,
    get_token,
    get_spotify_client_from_token,
    create_spotify_playlist,
    search_spotify_track,
    add_tracks_to_playlist,
)
from flask_cors import CORS
from dotenv import load_dotenv

# load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:3000", "https://synctify-y2s.vercel.app"])
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SAMESITE'] = None
app.config['SESSION_COOKIE_SECURE'] = False

@app.route("/ping")
def ping():
    return jsonify({"message": "Server is working!"})

@app.route("/login")
def login():
    auth_url = get_auth_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400

    access_token, refresh_token = get_token(code)
    if not access_token:
        return jsonify({"error": "Failed to get access token"}), 400

    #Fetch and log user info
    import requests
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info = requests.get("https://api.spotify.com/v1/me", headers=headers)

    if user_info.status_code != 200:
        print("❌ Failed to get Spotify user info:", user_info.text)
        return jsonify({"error": "Failed to get user info"}), 400

    user_json = user_info.json()
    print("✅ Logged in as:", user_json.get("display_name", "Unknown"))

    #store in session
    session["spotify_token"] = access_token
    session["spotify_user_id"] = user_json["id"]

    return redirect(f"https://synctify-y2s.vercel.app/#token={access_token}")

@app.route("/convert", methods=["POST"])
@app.route("/convert", methods=["POST"])
def convert_playlist():
    data = request.get_json()
    print("Received Data:", data)
    youtube_url = data.get('youtube_url')
    playlist_name = data.get("playlist_name", "Syntify Playlist")
    spotify_token = data.get('spotify_token') or session.get("spotify_token")

    def generate():
        if not data:
            yield "data: Error: Missing request data\n\n"
            return

        if not youtube_url:
            yield "data: Error: Missing YouTube URL\n\n"
            return

        if not spotify_token or spotify_token == "None":
            yield "data: Error: Not authenticated with Spotify. Please login first.\n\n"
            return

        yield f"data: Starting conversion for playlist: {playlist_name}\n\n"

        try:
            sp = get_spotify_client_from_token(spotify_token)
            yt_client = YouTubeClient()

            # Extract playlist ID
            playlist_id = None
            if "list=" in youtube_url:
                playlist_id = youtube_url.split("list=")[1].split("&")[0]
            else:
                yield "data: Error: Invalid YouTube playlist URL\n\n"
                return

            yield f"data: Fetching videos from YouTube playlist ID: {playlist_id}\n\n"
            titles = yt_client.get_videos_from_playlist(playlist_id)
            yield f"data: Found {len(titles)} videos in the playlist\n\n"

            spotify_playlist_id = create_spotify_playlist(sp, playlist_name)
            yield f"data: Created Spotify playlist with ID: {spotify_playlist_id}\n\n"

            uris = []
            not_found = []

            for title in titles:
                yield f"data: Searching for track: {title}\n\n"
                uri = search_spotify_track(sp, title)
                if uri:
                    uris.append(uri)
                else:
                    not_found.append(title)

            yield f"data: Found {len(uris)} tracks on Spotify out of {len(titles)} videos\n\n"

            if not_found:
                yield f"data: Could not find {len(not_found)} tracks\n\n"

            if uris:
                add_tracks_to_playlist(sp, spotify_playlist_id, uris)
                yield f"data: Playlist created successfully! 🎉\n\n"
            else:
                yield f"data: Could not find any tracks on Spotify\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8080)
