/**
 * Sidebar.jsx — RegIntel AI V2
 * Navigation is role-based using the new RBAC system via AuthContext.
 */
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useFrontendState } from "../context/FrontendStateContext";
import logo from "../assets/logo.jpg";

export default function Sidebar() {
  const { user, isAdmin, can } = useAuth();
  const { state } = useFrontendState();

  const NAV = [
    {
      to: "/", label: "Executive Dashboard", show: can("pipeline:read") && isAdmin,
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
    },
    {
      to: "/pipeline", label: "Analysis Pipeline", show: can("pipeline:read"),
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
    },
    {
      to: "/maps", label: "Compliance Register", show: can("map:read") && isAdmin,
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/></svg>
    },
    {
      to: "/departments", label: "Department Risk", show: can("dept:read") && isAdmin,
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M3 21h18M9 21V7l3-4 3 4v14M9 12h6"/></svg>
    },
    {
      to: "/assignment-center", label: "Assignment Center", show: can("map:approve"),
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/></svg>
    },
    {
      to: "/workspace", label: "My Assignments", show: can("assign:read"),
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/></svg>
    },
    {
      to: "/requirements", label: "Requirement Search", show: true,
      icon: <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
    },
    // The Global Knowledge Graph route (/graph) is disabled from normal navigation for the hackathon.
  ].filter(item => item.show);

  return (
    <aside style={{
      width: 252, minHeight: "100vh", flexShrink: 0,
      background: "linear-gradient(180deg, #060f1e 0%, #0a1628 50%, #0c1a30 100%)",
      display: "flex", flexDirection: "column",
      borderRight: "1px solid rgba(59,130,246,0.08)",
      boxShadow: "4px 0 24px rgba(0,0,0,0.25)",
    }}>
      {/* Logo */}
      <div style={{ padding: "28px 24px 22px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <img
            src={logo}
            alt="RegIntel AI"
            style={{ width: 36, height: 36, borderRadius: 9, objectFit: "cover", flexShrink: 0, boxShadow: "0 0 16px rgba(16,185,129,0.3)" }}
          />
          <div>
            <div style={{ color: "#f8fafc", fontWeight: 800, fontSize: 14, letterSpacing: 0.3 }}>RegIntel AI</div>
            <div style={{ color: "#10b981", fontSize: 10, fontWeight: 600, letterSpacing: 0.5 }}>v2.0</div>
          </div>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "rgba(16,185,129,0.12)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 20, padding: "3px 10px", marginTop: 2 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", display: "inline-block", animation: "pulse-dot 2s ease-in-out infinite" }} />
          <span style={{ color: "#10b981", fontSize: 10, fontWeight: 600, letterSpacing: 0.3 }}>LIVE DATA</span>
        </div>
        {/* Show doc count from state */}
        {state?.metadata && (
          <div style={{ marginTop: 8, fontSize: 10, color: "#334155", fontFamily: "monospace" }}>
            {state.metadata.total_documents} docs · {state.executive_kpis?.total_maps?.toLocaleString()} MAPs
          </div>
        )}
      </div>

      {/* Role indicator */}
      {user && (
        <div style={{ padding: "12px 24px 4px" }}>
          <div style={{ fontSize: 9.5, fontWeight: 700, color: "rgba(148,163,184,0.4)", letterSpacing: 1.1, textTransform: "uppercase", marginBottom: 4 }}>Logged in as</div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8" }}>
            <span style={{ color: isAdmin ? "#10b981" : "#60a5fa" }}>{user.full_name}</span>
            {user.department_name && <span style={{ color: "#475569" }}> · {user.department_name}</span>}
          </div>
        </div>
      )}

      {/* Nav label */}
      <div style={{ padding: "14px 24px 8px" }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: "rgba(148,163,184,0.5)", letterSpacing: 1.2, textTransform: "uppercase" }}>Navigation</span>
      </div>

      {/* Nav Links */}
      <nav style={{ flex: 1, padding: "0 12px" }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            style={({ isActive }) => ({
              display: "flex", alignItems: "center", gap: 11,
              padding: "11px 14px", marginBottom: 3,
              textDecoration: "none",
              color: isActive ? "#f8fafc" : "rgba(148,163,184,0.75)",
              background: isActive
                ? "linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(5,150,105,0.1) 100%)"
                : "transparent",
              borderRadius: 9,
              border: isActive ? "1px solid rgba(16,185,129,0.2)" : "1px solid transparent",
              fontSize: 13.5, fontWeight: isActive ? 600 : 400,
              transition: "all 0.18s ease",
              boxShadow: isActive ? "0 2px 12px rgba(16,185,129,0.12)" : "none",
            })}
            onMouseEnter={(e) => {
              if (!e.currentTarget.style.background.includes("16,185,129")) {
                e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                e.currentTarget.style.color = "#cbd5e1";
              }
            }}
            onMouseLeave={(e) => {
              if (!e.currentTarget.style.background.includes("16,185,129")) {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "rgba(148,163,184,0.75)";
              }
            }}
          >
            <span style={{ opacity: 0.9, flexShrink: 0 }}>{icon}</span>
            <span style={{ flex: 1 }}>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: "16px 24px 20px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <div style={{ fontSize: 11, color: "rgba(100,116,139,0.6)", marginBottom: 3 }}>RBI Compliance Intelligence</div>
        <div style={{ fontSize: 10, color: "rgba(100,116,139,0.4)" }}>Canara Bank SuRaksha · v2.0</div>
      </div>
    </aside>
  );
}
