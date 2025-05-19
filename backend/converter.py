from youtube_client import YouTubeClient
from spotify_client import create_spotify_playlist, search_spotify_track, add_tracks_to_playlist

# 1. Initialize YouTube client and get playlists
yt_client = YouTubeClient()
yt_playlists = yt_client.get_playlists()

# You can later make this dynamic
selected_playlist_id = yt_playlists[0]["id"]
selected_playlist_name = yt_playlists[0]["title"]

# 2. Get videos from selected playlist
video_titles = yt_client.get_videos_from_playlist(selected_playlist_id)

# 3. Create a Spotify playlist with same name
spotify_playlist_id = create_spotify_playlist(f"Syntified: {selected_playlist_name}")

# 4. Match videos to Spotify tracks
track_uris = []
for title in video_titles:
    print(f"🔍 Searching for: {title}")
    uri = search_spotify_track(title)
    if uri:
        print(f"✅ Found: {uri}")
        track_uris.append(uri)
    else:
        print(f"❌ Not found: {title}")

# 5. Add tracks to Spotify playlist
add_tracks_to_playlist(spotify_playlist_id, track_uris)
print("🎉 Playlist created and songs added successfully!")

