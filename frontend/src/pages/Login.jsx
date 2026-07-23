/**
 * Login.jsx — RegIntel AI V2
 * Demo authentication: no backend, no Axios.
 * Validates credentials against bcryptjs hashes in AuthContext.
 * Shows all demo credentials to judges directly on the login screen.
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import logo from "../assets/logo.jpg";

const DEMO_CREDENTIALS = [
  { username: "admin",      password: "admin123",      role: "Head Office Admin",  color: "#10b981" },
  { username: "compliance", password: "compliance123", role: "Compliance Officer", color: "#60a5fa" },
  { username: "risk",       password: "risk123",       role: "Risk Manager",       color: "#fbbf24" },
  { username: "it",         password: "it123",         role: "IT Security",        color: "#a78bfa" },
  { username: "operations", password: "ops123",        role: "Operations Manager", color: "#34d399" },
  { username: "audit",      password: "audit123",      role: "Internal Audit",     color: "#fb923c" },
];

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const navigate = useNavigate();
  const { login, isAdmin, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate(isAdmin ? "/" : "/workspace", { replace: true });
    }
  }, [isAuthenticated, isAdmin, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result = await login(username, password);

    if (result.success) {
      const isUserAdmin = result.user.permissions?.includes('*') || result.user.permissions?.includes('user:write');
      navigate(isUserAdmin ? "/" : "/workspace");
    } else {
      setError(result.error);
    }
    setLoading(false);
  };

  const handleQuickLogin = async (cred) => {
    setError("");
    setLoading(true);
    const result = await login(cred.username, cred.password);
    if (result.success) {
      const isUserAdmin = result.user.permissions?.includes('*') || result.user.permissions?.includes('user:write');
      navigate(isUserAdmin ? "/" : "/workspace");
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex",
      background: "linear-gradient(135deg, #0f172a 0%, #111827 50%, #0c1a30 100%)",
      fontFamily: "'Inter','Segoe UI',system-ui,sans-serif",
    }}>
      {/* Left panel — branding */}
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: "60px 80px", position: "relative", overflow: "hidden",
      }}>
        {/* Background glow */}
        <div style={{ position: "absolute", top: "30%", left: "40%", width: 400, height: 400, borderRadius: "50%", background: "rgba(16,185,129,0.06)", filter: "blur(80px)", pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 1, maxWidth: 480 }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 40 }}>
            <img
              src={logo}
              alt="RegIntel AI"
              style={{ width: 64, height: 64, borderRadius: 16, objectFit: "cover", boxShadow: "0 0 36px rgba(16,185,129,0.4)" }}
            />
            <div>
              <div style={{ fontSize: 28, fontWeight: 900, color: "#f1f5f9", letterSpacing: -0.5, lineHeight: 1 }}>RegIntel AI</div>
              <div style={{ fontSize: 13, color: "#10b981", fontWeight: 600, marginTop: 4 }}>Compliance Intelligence Platform</div>
            </div>
          </div>

          {/* Tagline */}
          <h1 style={{ fontSize: 32, fontWeight: 900, color: "#f1f5f9", letterSpacing: -0.5, lineHeight: 1.25, marginBottom: 16 }}>
            Autonomous Regulatory<br />
            <span style={{ background: "linear-gradient(135deg,#10b981,#34d399)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Compliance Intelligence
            </span>
          </h1>
          <p style={{ fontSize: 15, color: "#64748b", lineHeight: 1.7, marginBottom: 40 }}>
            Built for the Canara Bank SuRaksha Hackathon. Processes 354 RBI regulatory documents,
            extracts 59,125 Measurable Action Points, and autonomously validates compliance.
          </p>

          {/* Pipeline stat pills */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
            {[
              ["354", "RBI Documents", "#10b981"],
              ["59,125", "MAPs Generated", "#60a5fa"],
              ["178,467", "Checks Planned", "#a78bfa"],
            ].map(([val, label, color]) => (
              <div key={label} style={{ padding: "14px 16px", background: "rgba(255,255,255,0.03)", border: `1px solid ${color}20`, borderRadius: 10, textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 900, color, lineHeight: 1 }}>{val}</div>
                <div style={{ fontSize: 10.5, color: "#475569", marginTop: 4, fontWeight: 600 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — login form */}
      <div style={{ width: 460, display: "flex", flexDirection: "column", justifyContent: "center", padding: "48px 52px", background: "rgba(10,18,32,0.6)", borderLeft: "1px solid rgba(255,255,255,0.06)", backdropFilter: "blur(12px)" }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#f1f5f9", marginBottom: 6 }}>Sign in</div>
          <div style={{ fontSize: 13, color: "#64748b" }}>Access the compliance intelligence dashboard</div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#94a3b8", marginBottom: 7, letterSpacing: 0.4 }}>USERNAME</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              disabled={loading}
              placeholder="Enter username"
              style={{ width: "100%", padding: "12px 14px", fontSize: 14, border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 9, background: "#162030", color: "#e2e8f0", outline: "none", boxSizing: "border-box", transition: "border-color 0.2s" }}
              onFocus={e => e.target.style.borderColor = "#10b981"}
              onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.08)"}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#94a3b8", marginBottom: 7, letterSpacing: 0.4 }}>PASSWORD</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              disabled={loading}
              placeholder="Enter password"
              style={{ width: "100%", padding: "12px 14px", fontSize: 14, border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 9, background: "#162030", color: "#e2e8f0", outline: "none", boxSizing: "border-box", transition: "border-color 0.2s" }}
              onFocus={e => e.target.style.borderColor = "#10b981"}
              onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.08)"}
            />
          </div>

          {error && (
            <div style={{ padding: "10px 14px", background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", borderRadius: 8, color: "#fca5a5", fontSize: 13, fontWeight: 500 }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{ padding: "14px", fontSize: 14, fontWeight: 700, color: "#fff", background: loading ? "#334155" : "linear-gradient(135deg,#10b981,#059669)", border: "none", borderRadius: 9, cursor: loading ? "not-allowed" : "pointer", transition: "all 0.2s", boxShadow: loading ? "none" : "0 4px 14px rgba(16,185,129,0.3)", marginTop: 4 }}
            onMouseEnter={e => { if (!loading) { e.target.style.transform = "translateY(-1px)"; e.target.style.boxShadow = "0 6px 20px rgba(16,185,129,0.4)"; }}}
            onMouseLeave={e => { e.target.style.transform = "translateY(0)"; e.target.style.boxShadow = loading ? "none" : "0 4px 14px rgba(16,185,129,0.3)"; }}
          >
            {loading ? "Authenticating…" : "Sign In"}
          </button>
        </form>

        {/* Demo credential quick-login buttons */}
        <div style={{ marginTop: 32 }}>
          <div style={{ fontSize: 10.5, fontWeight: 700, color: "#334155", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: 12 }}>Demo — Quick Login</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {DEMO_CREDENTIALS.map(cred => (
              <button
                key={cred.username}
                onClick={() => handleQuickLogin(cred)}
                disabled={loading}
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 13px", background: "rgba(255,255,255,0.03)", border: `1px solid ${cred.color}18`, borderRadius: 8, cursor: loading ? "not-allowed" : "pointer", transition: "all 0.15s" }}
                onMouseEnter={e => { if (!loading) { e.currentTarget.style.background = `${cred.color}0e`; e.currentTarget.style.borderColor = `${cred.color}35`; }}}
                onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; e.currentTarget.style.borderColor = `${cred.color}18`; }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 24, height: 24, borderRadius: 6, background: `${cred.color}20`, border: `1px solid ${cred.color}35`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 800, color: cred.color }}>
                    {cred.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0", lineHeight: 1 }}>{cred.username}</div>
                    <div style={{ fontSize: 10.5, color: "#475569", marginTop: 2 }}>{cred.role}</div>
                  </div>
                </div>
                <div style={{ fontSize: 10, fontFamily: "monospace", color: "#334155" }}>{cred.password}</div>
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 24, fontSize: 11, color: "#1e3040", textAlign: "center" }}>
          RegIntel AI v2.0 · Canara Bank SuRaksha Hackathon
        </div>
      </div>
    </div>
  );
}
