import os
from flask import Flask, jsonify, request, redirect, session
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
CORS(app, supports_credentials=True, origins=["https://synctify-y2s.vercel.app"])
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

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

    if not data:
        return jsonify({'error':'Missing request data'}), 400

    youtube_url = data.get('youtube_url')
    playlist_name = data.get("playlist_name", "Syntify Playlist")

    # try to get token from request first then from session as fallback
    spotify_token = data.get('spotify_token')
    if not spotify_token or spotify_token == "None":
        spotify_token = session.get("spotify_token")

    print(f"Token type: {type(spotify_token)}, Value: {spotify_token}")

    if not youtube_url:
        return jsonify({"error": "Missing YouTube URL"}), 400

    if not spotify_token or spotify_token == "None":
        return jsonify({"error": "Not authenticated with Spotify. Please login first."}), 401

    try:
        sp = get_spotify_client_from_token(spotify_token)
        yt_client = YouTubeClient()

        # playlist ID extraction
        playlist_id = None
        if "list=" in youtube_url:
            playlist_id = youtube_url.split("list=")[1]
            # Handle additional parameters after the playlist ID
            if "&" in playlist_id:
                playlist_id = playlist_id.split("&")[0]

        if not playlist_id:
            return jsonify({"error": "Invalid YouTube playlist URL"}), 400

        print(f"Fetching videos from YouTube playlist ID: {playlist_id}")
        titles = yt_client.get_videos_from_playlist(playlist_id)
        print(f"Found {len(titles)} videos in the playlist")

        spotify_playlist_id = create_spotify_playlist(sp, playlist_name)
        print(f"Created Spotify playlist with ID: {spotify_playlist_id}")

        uris = []
        not_found = []

        for title in titles:
            print(f"Searching for track: {title}")
            uri = search_spotify_track(sp, title)
            if uri:
                uris.append(uri)
            else:
                not_found.append(title)

        print(f"Found {len(uris)} tracks on Spotify out of {len(titles)} videos")

        if not_found:
            print(f"Could not find {len(not_found)} tracks: {', '.join(not_found[:5])}")
            if len(not_found) > 5:
                print(f"...and {len(not_found) - 5} more")

        if uris:
            add_tracks_to_playlist(sp, spotify_playlist_id, uris)
            return jsonify({
                "message": "Success",
                "playlist_id": spotify_playlist_id,
                "stats": {
                    "total_videos": len(titles),
                    "found_tracks": len(uris),
                    "not_found": len(not_found)
                }
            }), 200
        else:
            return jsonify({"error": "Could not find any tracks on Spotify from this playlist"}), 404

    except Exception as e:
        import traceback
        print(f"Error in convert_playlist: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000)) 
    app.run(host='0.0.0.0', port=port, debug=True)
