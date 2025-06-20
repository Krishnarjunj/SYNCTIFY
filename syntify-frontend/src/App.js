import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [ytUrl, setYtUrl] = useState('');
  const [playlistName, setPlaylistName] = useState('');
  const [responseMsg, setResponseMsg] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [playlistId, setPlaylistId] = useState(null);
  const [error, setError] = useState('');
  const [spotifyToken, setSpotifyToken] = useState(null);
  
  // New states for real-time updates
  const [searchProgress, setSearchProgress] = useState({
    current: 0,
    total: 0,
    currentTrack: '',
    foundTracks: 0,
    notFoundTracks: 0,
    isSearching: false,
    logs: []
  });

  useEffect(() => {
    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const tokenFromHash = hashParams.get("token");

    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromQuery = urlParams.get("token");

    const token = tokenFromHash || tokenFromQuery;

    if (token) {
      localStorage.setItem("spotify_token", token);
      setSpotifyToken(token);
      setLoggedIn(true);
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
    window.location.href = "https://synctify.onrender.com/login";
  };

  const resetProgress = () => {
    setSearchProgress({
      current: 0,
      total: 0,
      currentTrack: '',
      foundTracks: 0,
      notFoundTracks: 0,
      isSearching: false,
      logs: []
    });
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
    resetProgress();

    try {
      // Use EventSource for Server-Sent Events
      const eventSource = new EventSource(
        `https://synctify.onrender.com/convert`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            youtube_url: ytUrl,
            playlist_name: playlistName || "SYNCTIFY Playlist",
            spotify_token: spotifyToken,
          })
        }
      );

      // Since EventSource doesn't support POST, we'll use fetch with streaming
      const response = await fetch("https://synctify.onrender.com/convert", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          youtube_url: ytUrl,
          playlist_name: playlistName || "SYNCTIFY Playlist",
          spotify_token: spotifyToken,
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              handleStreamMessage(data);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

    } catch (err) {
      console.error("Error details:", err);

      if (err.response?.status === 401) {
        setError("Spotify authentication expired. Please login again.");
        handleLogout();
      } else {
        setError(err.response?.data?.error || err.message || "An error occurred while converting the playlist");
      }
    } finally {
      setIsLoading(false);
      setSearchProgress(prev => ({ ...prev, isSearching: false }));
    }
  };

  const handleStreamMessage = (data) => {
    const { type, message, current, total, track, playlist_id, stats } = data;

    // Add to logs
    setSearchProgress(prev => ({
      ...prev,
      logs: [...prev.logs.slice(-20), { type, message, timestamp: Date.now() }] // Keep last 20 logs
    }));

    switch (type) {
      case 'searching':
        setSearchProgress(prev => ({
          ...prev,
          current: current || prev.current,
          total: total || prev.total,
          currentTrack: track || '',
          isSearching: true
        }));
        break;

      case 'found':
        setSearchProgress(prev => ({
          ...prev,
          foundTracks: prev.foundTracks + 1,
          current: current || prev.current
        }));
        break;

      case 'not_found':
        setSearchProgress(prev => ({
          ...prev,
          notFoundTracks: prev.notFoundTracks + 1,
          current: current || prev.current
        }));
        break;

      case 'success':
        setPlaylistId(playlist_id);
        if (stats) {
          const { total_videos, found_tracks, not_found } = stats;
          setResponseMsg(`✅ Playlist Created! Found ${found_tracks} out of ${total_videos} tracks.`);
        } else {
          setResponseMsg("✅ Playlist Created Successfully!");
        }
        setSearchProgress(prev => ({ ...prev, isSearching: false }));
        break;

      case 'error':
        setError(message);
        setSearchProgress(prev => ({ ...prev, isSearching: false }));
        break;

      default:
        // Handle info, warning, etc.
        break;
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("spotify_token");
    setSpotifyToken(null);
    setLoggedIn(false);
    setPlaylistId(null);
    setResponseMsg('');
    setError('');
    resetProgress();
  };

  const openSpotifyPlaylist = () => {
    if (playlistId) {
      window.open(`https://open.spotify.com/playlist/${playlistId}`, '_blank');
    }
  };

  return (
    <div className="app-container">
      <div className="background-gradient">
        <div className="gradient-overlay"></div>
      </div>

      <div className="floating-particles">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="particle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`,
              animationDuration: `${2 + Math.random() * 2}s`
            }}
          />
        ))}
      </div>

      <div className="main-content">
        {/* Header */}
        <header className="app-header">
          <h1 className="app-title">
            <span className="sync">SYNC</span>
            <span className="tify">TIFY</span>
          </h1>

          {/* 🎵 Music Bars Here */}
          <div className="music-bars">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bar"></div>
            ))}
          </div>

          <p className="app-tagline">Transform YouTube playlists into Spotify playlists</p>
        </header>

        {/* Main Card */}
        <div className="main-card">
          {/* Auth Section */}
          <div className="auth-section">
            {loggedIn ? (
              <div className="logged-in-container">
                <div className="status-info">
                  <div className="status-icon">
                    <span className="check-icon">✓</span>
                  </div>
                  <div className="status-text">
                    <p className="status-title">Connected to Spotify</p>
                    <p className="status-subtitle">Ready to convert playlists</p>
                  </div>
                </div>
                <button onClick={handleLogout} className="logout-btn">
                  <span className="logout-icon">⚙</span>
                  Logout
                </button>
              </div>
            ) : (
              <button onClick={handleSpotifyLogin} className="spotify-login-btn">
                <svg viewBox="0 0 24 24" className="spotify-icon" fill="currentColor">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.8-.179-.92-.6-.12-.421.18-.8.6-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.48.66.24 1.08zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                Connect with Spotify
              </button>
            )}
          </div>

          {/* Input Fields */}
          <div className="input-section">
            <div className="input-group youtube-input">
              <label className="input-label">
                <div className="label-indicator youtube-indicator"></div>
                YouTube Playlist URL
              </label>
              <input
                type="text"
                value={ytUrl}
                onChange={e => setYtUrl(e.target.value)}
                placeholder="https://www.youtube.com/playlist?list=..."
                className="input-field"
              />
            </div>

            <div className="input-group spotify-input">
              <label className="input-label">
                <div className="label-indicator spotify-indicator"></div>
                Playlist Name
                <span className="optional-text">(optional)</span>
              </label>
              <input
                type="text"
                value={playlistName}
                onChange={e => setPlaylistName(e.target.value)}
                placeholder="My Awesome Playlist"
                className="input-field"
              />
            </div>
          </div>

          <button
            onClick={handleConvert}
            disabled={isLoading}
            className={`convert-btn ${isLoading ? 'loading' : ''}`}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Converting ...
              </>
            ) : (
              <>
                <span className="play-icon">▶</span>
                Convert to Spotify
              </>
            )}
          </button>

          {/* Progress Section */}
          {searchProgress.isSearching && (
            <div className="progress-section">
              <div className="progress-header">
                <h3>🎵 Searching for tracks...</h3>
                <div className="progress-stats">
                  <span className="found-count">✓ {searchProgress.foundTracks}</span>
                  <span className="not-found-count">✗ {searchProgress.notFoundTracks}</span>
                  <span className="total-count">{searchProgress.current}/{searchProgress.total}</span>
                </div>
              </div>
              
              {searchProgress.total > 0 && (
                <div className="progress-bar-container">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ width: `${(searchProgress.current / searchProgress.total) * 100}%` }}
                    ></div>
                  </div>
                  <span className="progress-percentage">
                    {Math.round((searchProgress.current / searchProgress.total) * 100)}%
                  </span>
                </div>
              )}

              {searchProgress.currentTrack && (
                <div className="current-track">
                  <span className="track-label">Currently searching:</span>
                  <span className="track-name">{searchProgress.currentTrack}</span>
                </div>
              )}
            </div>
          )}

          {/* Live Log Section */}
          {searchProgress.logs.length > 0 && (
            <div className="log-section">
              <div className="log-container">
                {searchProgress.logs.slice(-5).map((log, index) => (
                  <div key={`${log.timestamp}-${index}`} className={`log-item log-${log.type}`}>
                    <span className="log-message">{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="error-message">
              <p>{error}</p>
            </div>
          )}

          {playlistId && (
            <div className="success-container">
              <p className="success-message">{responseMsg}</p>
              <button onClick={openSpotifyPlaylist} className="open-spotify-btn">
                <span className="external-icon">🔗</span>
                Open in Spotify
              </button>
            </div>
          )}
        </div>

        <footer className="app-footer">
          <p>Made by Krish</p>
        </footer>
      </div>

      <div className="bubble-container">
        {[...Array(50)].map((_, i) => {
          const size = Math.random() * 10 + 10;
          const left = Math.random() * 100;
          const duration = 5 + Math.random() * 5;
          const delay = Math.random() * 5;
          const color = 'rgba(0, 255, 38, 0.5)';

          return (
            <div
              key={i}
              className="bubble"
              style={{
                width: `${size}px`,
                height: `${size}px`,
                left: `${left}%`,
                backgroundColor: color,
                animationDuration: `${duration}s`,
                animationDelay: `${delay}s`
              }}
            ></div>
          );
        })}
      </div>
    </div>
  );
}

export default App;
