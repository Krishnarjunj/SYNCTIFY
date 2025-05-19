from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import re

class YouTubeClient:
    def __init__(self):
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("Missing YouTube API key. Set YOUTUBE_API_KEY environment variable.")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def get_videos_from_playlist(self, playlist_id):
        """Get video titles from a YouTube playlist with improved title extraction"""
        if not playlist_id:
            raise ValueError("Invalid playlist ID")

        try:
            playlist_response = self.youtube.playlists().list(
                part='snippet',
                id=playlist_id
            ).execute()

            if not playlist_response.get('items'):
                print(f"Warning: Could not fetch playlist info for {playlist_id}. It may be private.")
        except HttpError as e:
            print(f"Error fetching playlist info: {str(e)}")

        titles = []
        next_page_token = None

        max_results = 50

        while True:
            try:
                response = self.youtube.playlistItems().list(
                    part='snippet',
                    maxResults=max_results,
                    playlistId=playlist_id,
                    pageToken=next_page_token
                ).execute()

                for item in response['items']:
                    if 'snippet' in item and 'title' in item['snippet']:
                        video_title = item['snippet'].get('title')

                        if video_title != 'Deleted video' and video_title != 'Private video':
                            if 'videoOwnerChannelTitle' in item['snippet']:
                                channel = item['snippet']['videoOwnerChannelTitle']
                                channel = re.sub(r'\s*-\s*Topic$', '', channel)

                                if channel and channel not in video_title:
                                    if ' - ' not in video_title:
                                        video_title = f"{channel} - {video_title}"

                            titles.append(video_title)

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

            except HttpError as e:
                print(f"An HTTP error occurred: {e}")
                break

        print(f"Found {len(titles)} videos in YouTube playlist")
        return titles

    def get_video_details(self, video_id):
        """Get detailed information about a specific video"""
        try:
            response = self.youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute()

            if response['items']:
                return response['items'][0]['snippet']
            return None
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None
