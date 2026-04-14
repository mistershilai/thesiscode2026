import { useState } from "react";
import { useAuth } from "../auth";
import FooterNames from "../components/FooterNames";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="bg-anim" aria-hidden="true">
        <div className="bg-grid" />
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />
        <div className="bg-orb bg-orb-3" />
      </div>

      <div className="login-card">
        <div className="login-header">
          <img src="/logos/kaelo.png" alt="Kaelo" className="login-logo" />
          <h1 className="login-title">Kaelo</h1>
          <p className="login-subtitle">
            Antimicrobial Supply Chain Optimization
          </p>
          <p className="login-subtitle-tswana">
            Go isa melemo e e siameng, ka nako e e siameng
          </p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error">{error}</div>}

          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <button
            type="submit"
            className="btn btn-primary login-btn"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="login-footer">
          <div className="login-flag" />
        </div>
      </div>

      <div className="login-bottom">
        <div className="login-partners">
          <img src="/logos/moh.png" alt="Ministry of Health" className="login-partner-logo login-partner-invert" />
          <img src="/logos/achap.png" alt="ACHAP" className="login-partner-logo login-partner-bg" />
          <img src="/logos/orfe.png" alt="Princeton ORFE" className="login-partner-logo login-partner-bg" />
        </div>
        <div className="login-credits">
          <FooterNames />
        </div>
      </div>
    </div>
  );
}
