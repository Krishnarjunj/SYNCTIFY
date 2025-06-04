**NOT COMPLETED YET!**

https://synctify-y2s.vercel.app/


**App.py Explanation**

**import os** - This interacts with the operating system. In this case used to extract the environment variables from the .env file. The environment variables in this case are the SPOTIFY CLIENT ID and the SECRET SPOTIFY CLIENT ID, and the YOUTUBE API KEY.

| Function   | Purpose                                                        |
| ---------- | -------------------------------------------------------------- |
|  Flask     | Creates the web app                                            |
|  jsonify   | Converts Python dictionaries/lists to JSON responses           |
|  request   | Lets you access incoming data (e.g. `POST` or `GET` requests)  |
|  redirect  | Redirects the browser to another URL (e.g. Spotify login page) |
|  session   | Stores data between requests (e.g. Spotify token)              |


| Function / Object                 | Role                                                   |
| --------------------------------- | ------------------------------------------------------ |
|   sp_oauth                        | Handles Spotify OAuth (login) setup                    |
|   get_auth_url()                  | Returns the Spotify login URL                          |
|   get_token(code)                 | Exchanges the Spotify code for an access token         |
|   get_spotify_client_from_token() | Initializes a Spotify client using the access token    |
|  create_spotify_playlist()        | Creates a new playlist on the user’s Spotify account   |
|  search_spotify_track()           | Searches for a track on Spotify by title               |
|  add_tracks_to_playlist()         | Adds found tracks (by URI) to the new Spotify playlist |

