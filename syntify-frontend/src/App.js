import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css'; // We'll add custom CSS

function App() {
  const [ytUrl, setYtUrl] = useState('');
  const [playlistName, setPlaylistName] = useState('');
  const [responseMsg, setResponseMsg] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [playlistId, setPlaylistId] = useState(null);
  const [error, setError] = useState('');
  const [spotifyToken, setSpotifyToken] = useState(null);

  // Check if Spotify token is already stored (user is logged in)
  useEffect(() => {
    // First check for token in URL hash fragment (more secure)
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const tokenFromHash = hashParams.get("token");
    
    // Then check for token in URL query parameters (legacy)
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromQuery = urlParams.get("token");
    
    const token = tokenFromHash || tokenFromQuery;

    if (token) {
      localStorage.setItem("spotify_token", token);
      setSpotifyToken(token);
      setLoggedIn(true);
      // Remove token from URL
      window.history.replaceState({}, document.title, "/");
    } else {
      const existingToken = localStorage.getItem("spotify_token");
      if (existingToken) {
        setSpotifyToken(existingToken);
        setLoggedIn(true);
      }
    }
  }, []);

  const handleSpotifyLogin = () => {
    window.location.href = "http://127.0.0.1:8080/login"; // Use 127.0.0.1 instead of localhost
  };

  const handleConvert = async () => {
    if (!ytUrl) {
      setError("Please enter a YouTube playlist URL");
      return;
    }

    if (!loggedIn || !spotifyToken) {
      setError("Please login with Spotify first");
      return;
    }

    setError('');
    setIsLoading(true);
    setResponseMsg('');
    setPlaylistId(null);

    try {
      const res = await axios.post(
        "http://127.0.0.1:8080/convert", // Use 127.0.0.1 instead of localhost
        {
          youtube_url: ytUrl,
          playlist_name: playlistName || "Syntify Playlist",
          spotify_token: spotifyToken,
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          withCredentials: true,
        }
      );

      setPlaylistId(res.data.playlist_id);

      // Enhanced success message with stats if available
      if (res.data.stats) {
        const { total_videos, found_tracks, not_found } = res.data.stats;
        setResponseMsg(`✅ Playlist Created! Found ${found_tracks} out of ${total_videos} tracks.`);
      } else {
        setResponseMsg("✅ Playlist Created Successfully!");
      }
    } catch (err) {
      console.error("Error details:", err);
      
      if (err.response?.status === 401) {
        // Handle authentication errors
        setError("Spotify authentication expired. Please login again.");
        handleLogout(); // Force logout if token is invalid
      } else {
        setError(err.response?.data?.error || "An error occurred while converting the playlist");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("spotify_token");
    setSpotifyToken(null);
    setLoggedIn(false);
  };

  const openSpotifyPlaylist = () => {
    if (playlistId) {
      window.open(`https://open.spotify.com/playlist/${playlistId}`, '_blank');
    }
  };

  return (
    <div className="app-container">
      <div className="app-content">
        <header>
          <div className="logo">
            <span className="logo-icon">🎵</span>
            <h1>Syntify</h1>
          </div>
          <p className="tagline">Convert YouTube playlists to Spotify in seconds</p>
        </header>

        <div className="auth-section">
          {loggedIn ? (
            <div className="logged-in-container">
              <div className="logged-in-status">
                <div className="status-icon">✓</div>
                <span>Connected to Spotify</span>
              </div>
              <button onClick={handleLogout} className="logout-btn">
                Logout
              </button>
            </div>
          ) : (
            <button onClick={handleSpotifyLogin} className="spotify-login-btn">
              <span className="spotify-icon">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.8-.179-.92-.6-.12-.421.18-.8.6-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.48.66.24 1.08zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" fill="currentColor"/>
                </svg>
              </span>
              Login with Spotify
            </button>
          )}
        </div>

        <div className="converter-section">
          <div className="input-group">
            <label>YouTube Playlist URL</label>
            <input
              type="text"
              value={ytUrl}
              onChange={e => setYtUrl(e.target.value)}
              placeholder="https://www.youtube.com/playlist?list=..."
            />
          </div>

          <div className="input-group">
            <label>Spotify Playlist Name <span className="optional">(optional)</span></label>
            <input
              type="text"
              value={playlistName}
              onChange={e => setPlaylistName(e.target.value)}
              placeholder="My Awesome Playlist"
            />
          </div>

          <button
            className={`convert-btn ${isLoading ? 'loading' : ''}`}
            onClick={handleConvert}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Converting...
              </>
            ) : (
              <>Convert to Spotify</>
            )}
          </button>

          {error && <div className="error-message">{error}</div>}

          {playlistId && (
            <div className="success-container">
              <div className="success-message">{responseMsg}</div>
              <button className="open-spotify-btn" onClick={openSpotifyPlaylist}>
                Open in Spotify
              </button>
            </div>
          )}
        </div>
      </div>

      <footer>
        <p>Syntify - YouTube to Spotify Converter</p>
      </footer>
    </div>
  );
}

export default App;
