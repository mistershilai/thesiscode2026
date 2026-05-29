import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import { useState } from "react";
import { AuthProvider, useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import RegionDetail from "./pages/RegionDetail";
import Optimize from "./pages/Optimize";
import Planning from "./pages/Planning";
import About from "./pages/About";
import Docs from "./pages/Docs";
import Methodology from "./pages/Methodology";
import Login from "./pages/Login";
import Asclepius from "./components/Asclepius";
import FooterNames from "./components/FooterNames";
import "./App.css";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppContent() {
  const { user, logout } = useAuth();
  const [solving, setSolving] = useState(false);
  const location = useLocation();
  const isLoginPage = location.pathname === "/login";

  // Expose setter globally so Optimize/Planning pages can toggle it
  (window as any).__setSolving = setSolving;

  return (
    <>
      {/* Animated background */}
      <div className="bg-anim" aria-hidden="true">
        <div className="bg-grid" />
        <div className="bg-orb bg-orb-1" />
        <div className="bg-orb bg-orb-2" />
        <div className="bg-orb bg-orb-3" />
      </div>

      {/* Asclepius watermark */}
      <Asclepius beating={solving} />

      {!isLoginPage && (
      <nav className="navbar">
        <Link to="/" className="nav-brand">
          <img src="/logos/kaelo.png" alt="Kaelo" className="nav-logo" />
          Kaelo
        </Link>
        <div className="nav-links">
          <Link to="/">Dashboard</Link>
          {user && <Link to="/optimize">Simulate</Link>}
          {user && <Link to="/plan">Plan</Link>}
          <Link to="/methodology">Math</Link>
          <Link to="/about">About</Link>
          <Link to="/docs">Docs</Link>
        </div>
        <div className="nav-user">
          {user ? (
            <>
              <span className="nav-username">{user.name || user.username}</span>
              <button className="nav-logout" onClick={logout}>
                Sign out
              </button>
            </>
          ) : (
            <Link to="/login" className="nav-logout" style={{ textDecoration: "none" }}>
              Sign in
            </Link>
          )}
        </div>
      </nav>
      )}
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/region/:region" element={<RegionDetail />} />
          <Route path="/optimize" element={<ProtectedRoute><Optimize /></ProtectedRoute>} />
          <Route path="/plan" element={<ProtectedRoute><Planning /></ProtectedRoute>} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/about" element={<About />} />
          <Route path="/docs" element={<Docs />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {!isLoginPage && (
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-partners">
            <span className="footer-label">In partnership with</span>
            <div className="footer-logos">
              <a href="https://www.moh.gov.bw/" target="_blank" rel="noopener noreferrer">
                <img src="/logos/moh.png" alt="Ministry of Health, Republic of Botswana" className="footer-logo footer-logo-invert" />
              </a>
              <a href="https://achap.org/" target="_blank" rel="noopener noreferrer">
                <img src="/logos/achap.png" alt="ACHAP - Partnerships for a healthy Africa" className="footer-logo footer-logo-achap" />
              </a>
              <a href="https://chw.princeton.edu/" target="_blank" rel="noopener noreferrer">
                <img src="/logos/chw.png" alt="Princeton Center for Health and Wellbeing" className="footer-logo footer-logo-chw" />
              </a>
              <a href="https://globalhealth.princeton.edu/" target="_blank" rel="noopener noreferrer">
                <img src="/logos/ghp.png" alt="Princeton Global Health Program" className="footer-logo footer-logo-ghp" />
              </a>
            </div>
          </div>
          <div className="footer-partners">
            <span className="footer-label">Built with <span className="footer-heart">&hearts;</span> by researchers from</span>
            <div className="footer-logos">
              <a href="https://orfe.princeton.edu/" target="_blank" rel="noopener noreferrer">
                <img src="/logos/orfe.png" alt="Princeton ORFE" className="footer-logo footer-logo-orfe" />
              </a>
            </div>
          </div>
          <div className="footer-credits">
            <FooterNames />
          </div>
        </div>
      </footer>
      )}
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
