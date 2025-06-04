import os
import requests
import re
import base64
from urllib.parse import urlencode
from fuzzywuzzy import fuzz, process
from dotenv import load_dotenv

# load environment variables
load_dotenv()

# Spotify API endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = 'https://synctify.onrender.com/callback'  # REdirect uri


def sp_oauth():
    return {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'scope': 'playlist-modify-public playlist-modify-private',
    }

def get_auth_url():
    if not CLIENT_ID:
        raise ValueError("Missing Spotify CLIENT_ID. Check your .env file and ensure SPOTIFY_CLIENT_ID is set correctly.")

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'playlist-modify-public playlist-modify-private',
        'show_dialog': True  
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    print(f"Generated auth URL: {auth_url}")
    return auth_url

def get_token(code):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("Missing Spotify credentials. Check your .env file and ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set correctly.")

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    headers = {
        'Authorization': f"Basic {auth_header}",
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    print("Requesting token with data:", data)
    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        print(f"Error getting token: {response.status_code} - {response.text}")
        return None, None

    response_data = response.json()
    return response_data.get('access_token'), response_data.get('refresh_token')


def get_spotify_client_from_token(token):
    return {'token': token}

def create_spotify_playlist(sp, name):
    if not sp or not sp.get('token'):
        raise ValueError("Invalid Spotify client or missing token")

    user_info = get_user_info(sp)
    if not user_info or 'id' not in user_info:
        raise ValueError("Could not get Spotify user info")

    user_id = user_info['id']

    headers = {
        'Authorization': f"Bearer {sp['token']}",
        'Content-Type': 'application/json'
    }
    data = {
        'name': name,
        'description': 'Created with Syntify - YouTube to Spotify converter',
        'public': True
    }
    endpoint = f"{API_BASE_URL}users/{user_id}/playlists"

    response = requests.post(endpoint, headers=headers, json=data)

    if response.status_code != 201:
        print(f"Error creating playlist: {response.status_code} - {response.text}")
        raise ValueError(f"Failed to create playlist: {response.text}")

    playlist_info = response.json()
    return playlist_info['id']

def get_user_info(sp):
    if not sp or not sp.get('token'):
        raise ValueError("Invalid Spotify client or missing token")

    headers = {'Authorization': f"Bearer {sp['token']}"}
    response = requests.get(f"{API_BASE_URL}me", headers=headers)

    if response.status_code != 200:
        print(f"Error getting user info: {response.status_code} - {response.text}")
        raise ValueError("Failed to get Spotify user information")

    return response.json()

def clean_title(title):
    """Clean YouTube video title to improve search accuracy"""
    # removing common parameters
    patterns = [
        r'\(Official Video\)', r'\(Official Music Video\)', r'\(Official Audio\)', r'\(Audio\)',
        r'\[Official Video\]', r'\[Official Music Video\]', r'\[Official Audio\]', r'\[Audio\]',
        r'\(Lyrics\)', r'\[Lyrics\]', r'\(Lyric Video\)', r'\[Lyric Video\]',
        r'\(HD\)', r'\[HD\]', r'\(HQ\)', r'\[HQ\]', r'\(4K\)', r'\[4K\]',
        r'Official Music Video', r'Official Video', r'Official Audio',
        r'High Quality', r'Full HD', r'VEVO', r'vevo',
        r'\d{4} new', r'\d{4}[.-]\d{2}[.-]\d{2}', r'\d+[.-]\d+[.-]\d+',  # dates
        r'\(\d+\)', r'\[\d+\]',  # numbered videos
    ]


    title = re.sub(r'\bft\.|\bfeat\.|\bfeaturing\b', 'feat', title, flags=re.IGNORECASE)

    for pattern in patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    title = re.sub(r'[^\w\s\']', ' ', title)  # Keep apostrophes for names like "Don't"
    title = re.sub(r'\s+', ' ', title).strip()

    return title

def extract_artist_and_track(title):
    """Try to extract artist and track from common YouTube title formats"""
    dash_split = re.split(r'\s*-\s*', title, 1)
    if len(dash_split) == 2:
        artist, track = dash_split
        if ' feat' in artist.lower() and ' feat' not in track.lower():
            artist, track = track, artist
        return artist, track

    feat_match = re.search(r'(.*?)\s+feat\.?\s+(.*)', title, re.IGNORECASE)
    if feat_match:
        return feat_match.group(1), f"{feat_match.group(1)} feat. {feat_match.group(2)}"

    return None, title

def search_spotify_track(sp, title):
    """Enhanced search to improve matching accuracy between YouTube and Spotify"""
    if not sp or not sp.get('token'):
        raise ValueError("Invalid Spotify client or missing token")

    clean_video_title = clean_title(title)

    artist, track = extract_artist_and_track(clean_video_title)

    headers = {'Authorization': f"Bearer {sp['token']}"}

    if artist and len(artist) > 1 and len(track) > 1:
        search_query = f"artist:{artist} track:{track}"
        response = requests.get(
            f"{API_BASE_URL}search?q={search_query}&type=track&limit=5",
            headers=headers
        )

        if response.status_code != 200:
            print(f"Error searching track: {response.status_code} - {response.text}")
            return None

        results = response.json()

        if results.get('tracks', {}).get('items'):
            tracks = results['tracks']['items']
            best_match = None
            best_score = 0

            for t in tracks:
                combined = f"{t['artists'][0]['name']} - {t['name']}"
                score = fuzz.ratio(clean_video_title.lower(), combined.lower())
                if score > best_score:
                    best_score = score
                    best_match = t

            if best_score > 70:
                return best_match['uri']

    # Second search strategy: Full title search
    search_query = clean_video_title
    response = requests.get(
        f"{API_BASE_URL}search?q={search_query}&type=track&limit=5",
        headers=headers
    )

    if response.status_code != 200:
        print(f"Error searching track: {response.status_code} - {response.text}")
        return None

    results = response.json()

    if results.get('tracks', {}).get('items'):
        # Use fuzzy matching to find the best match
        tracks = results['tracks']['items']
        candidates = []

        for t in tracks:
            artist_name = t['artists'][0]['name']
            track_name = t['name']
            combined = f"{artist_name} - {track_name}"
            candidates.append((combined, t['uri']))

        best_match, score = process.extractOne(clean_video_title, [c[0] for c in candidates])

        if score > 65:  # Threshold for acceptable match
            return [c[1] for c in candidates if c[0] == best_match][0]

    # Third search strategy: Try with just the track name if artist extraction was attempted
    if artist and track:
        search_query = track
        response = requests.get(
            f"{API_BASE_URL}search?q={search_query}&type=track&limit=3",
            headers=headers
        )

        if response.status_code != 200:
            print(f"Error searching track: {response.status_code} - {response.text}")
            return None

        results = response.json()

        if results.get('tracks', {}).get('items'):
            return results['tracks']['items'][0]['uri']

    # If all strategies fail
    print(f"Could not find a match for: {title}")
    return None

def add_tracks_to_playlist(sp, playlist_id, uris):
    if not sp or not sp.get('token'):
        raise ValueError("Invalid Spotify client or missing token")

    if not playlist_id:
        raise ValueError("Invalid playlist ID")

    if not uris:
        print("No tracks to add to playlist")
        return

    headers = {
        'Authorization': f"Bearer {sp['token']}",
        'Content-Type': 'application/json'
    }

    data = {
        'uris': uris
    }

    endpoint = f"{API_BASE_URL}playlists/{playlist_id}/tracks"
    response = requests.post(endpoint, headers=headers, json=data)

    if response.status_code not in [200, 201]:
        print(f"Error adding tracks: {response.status_code} - {response.text}")
        raise ValueError("Failed to add tracks to playlist")

    print(f"Successfully added {len(uris)} tracks to playlist.")

def refresh_access_token(refresh_token):
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    headers = {
        'Authorization': f"Basic {auth_header}",
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        raise ValueError("Failed to refresh access token")

    return response.json().get('access_token')
