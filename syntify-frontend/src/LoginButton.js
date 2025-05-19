// LoginButton.jsx (React)

export default function LoginButton() {
  const handleLogin = () => {
    window.location.href = "http://localhost:5000/login"; // Your backend route
  };

  return (
    <button onClick={handleLogin} className="btn btn-primary">
      Login with Spotify
    </button>
  );
}
