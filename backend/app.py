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
import json

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
def convert_playlist():
    data = request.get_json()
    print("Received Data:", data)
    youtube_url = data.get('youtube_url')
    playlist_name = data.get("playlist_name", "Syntify Playlist")
    spotify_token = data.get('spotify_token') or session.get("spotify_token")

    def generate():
        if not data:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Missing request data'})}\n\n"
            return

        if not youtube_url:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Missing YouTube URL'})}\n\n"
            return

        if not spotify_token or spotify_token == "None":
            yield f"data: {json.dumps({'type': 'error', 'message': 'Not authenticated with Spotify. Please login first.'})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'info', 'message': f'Starting conversion for playlist: {playlist_name}'})}\n\n"

        try:
            sp = get_spotify_client_from_token(spotify_token)
            yt_client = YouTubeClient()

            # Extract playlist ID
            playlist_id = None
            if "list=" in youtube_url:
                playlist_id = youtube_url.split("list=")[1].split("&")[0]
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid YouTube playlist URL'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'info', 'message': f'Fetching videos from YouTube playlist ID: {playlist_id}'})}\n\n"
            titles = yt_client.get_videos_from_playlist(playlist_id)
            yield f"data: {json.dumps({'type': 'info', 'message': f'Found {len(titles)} videos in the playlist'})}\n\n"

            spotify_playlist_id = create_spotify_playlist(sp, playlist_name)
            yield f"data: {json.dumps({'type': 'info', 'message': f'Created Spotify playlist with ID: {spotify_playlist_id}'})}\n\n"

            uris = []
            not_found = []
            total_tracks = len(titles)

            for i, title in enumerate(titles, 1):
                yield f"data: {json.dumps({'type': 'searching', 'message': f'Searching for track: {title}', 'current': i, 'total': total_tracks, 'track': title})}\n\n"
                
                uri = search_spotify_track(sp, title)
                if uri:
                    uris.append(uri)
                    yield f"data: {json.dumps({'type': 'found', 'message': f'✓ Found: {title}', 'current': i, 'total': total_tracks, 'track': title})}\n\n"
                else:
                    not_found.append(title)
                    yield f"data: {json.dumps({'type': 'not_found', 'message': f'✗ Not found: {title}', 'current': i, 'total': total_tracks, 'track': title})}\n\n"

            yield f"data: {json.dumps({'type': 'info', 'message': f'Found {len(uris)} tracks on Spotify out of {len(titles)} videos'})}\n\n"

            if not_found:
                yield f"data: {json.dumps({'type': 'warning', 'message': f'Could not find {len(not_found)} tracks'})}\n\n"

            if uris:
                yield f"data: {json.dumps({'type': 'info', 'message': 'Adding tracks to playlist...'})}\n\n"
                add_tracks_to_playlist(sp, spotify_playlist_id, uris)
                yield f"data: {json.dumps({'type': 'success', 'message': 'Playlist created successfully! 🎉', 'playlist_id': spotify_playlist_id, 'stats': {'total_videos': len(titles), 'found_tracks': len(uris), 'not_found': len(not_found)}})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Could not find any tracks on Spotify'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8080)
