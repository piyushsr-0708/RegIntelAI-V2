/**
 * SessionDashboard.jsx — RegIntel AI V2
 * Document-centric dashboard for a single analysis session.
 * Reads from SessionContext only — NOT the global compliance register.
 * 9 sections: Summary, Pipeline, MAPs, Dept Impact, Priority, Capability,
 *             Knowledge Graph, Verification Plans, Assignment Preview.
 */
import { useParams, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import Breadcrumbs from "../components/Breadcrumbs";
import SessionSummary from "../components/session/SessionSummary";
import SessionMapTable from "../components/session/SessionMapTable";
import DepartmentImpact from "../components/session/DepartmentImpact";
import { PriorityChart, CapabilityChart } from "../components/session/SessionCharts";
import SessionKnowledgeGraph from "../components/session/SessionKnowledgeGraph";
import VerificationSummary from "../components/session/VerificationSummary";
import AssignmentPreview from "../components/session/AssignmentPreview";

// ─── Pipeline stage summary row ───────────────────────────────────────────────
function StageSummaryRow({ stage }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "9px 14px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#34d399", fontWeight: 800, flexShrink: 0 }}>✓</div>
      <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>{stage.label}</span>
      <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>{stage.records}</span>
      <span style={{ fontSize: 11, color: "#34d399", fontFamily: "monospace", minWidth: 40, textAlign: "right" }}>
        {(stage.duration_ms / 1000).toFixed(1)}s
      </span>
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 3, height: 14, borderRadius: 2, background: "#10b981" }} />
        {title}
      </div>
      {children}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function SessionDashboard() {
  const { id }   = useParams();
  const navigate = useNavigate();
  const session  = useSession(decodeURIComponent(id));

  if (!session) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>🔍</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#94a3b8", marginBottom: 8 }}>Session not found</div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20, fontFamily: "monospace" }}>{decodeURIComponent(id)}</div>
      <button onClick={() => navigate("/pipeline")}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Pipeline
      </button>
    </div>
  );

  if (session.status === "processing") return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="40" height="40" viewBox="0 0 40 40" style={{ animation: "spin 1s linear infinite", marginBottom: 16 }}>
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="4"/>
        <path d="M20 4a16 16 0 0 1 16 16" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round"/>
      </svg>
      <div style={{ fontSize: 14, fontWeight: 700, color: "#10b981" }}>Pipeline still running…</div>
    </div>
  );

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Back button */}
      <button
        onClick={() => navigate("/pipeline")}
        style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}
      >
        ← Back to Pipeline
      </button>

      {/* Page header */}
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.5)" }} />
          <h1 className="page-title">Session Dashboard</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          Analysis session · <span style={{ fontFamily: "monospace", color: "#64748b" }}>{session.session_id}</span>
        </p>
      </div>

      {/* 1 — Document Summary */}
      <Section title="Document Summary">
        <SessionSummary session={session} />
      </Section>

      {/* 2 — Pipeline Summary */}
      <Section title="Pipeline Summary">
        <div className="card" style={{ overflow: "hidden", marginBottom: 0 }}>
          <div style={{ padding: "10px 14px", background: "#162030", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", fontSize: 11, color: "#475569" }}>
            <span>Stage</span>
            <div style={{ display: "flex", gap: 40 }}>
              <span>Records</span>
              <span>Duration</span>
            </div>
          </div>
          {session.stages.map((stage) => (
            <StageSummaryRow key={stage.id} stage={stage} />
          ))}
          <div style={{ padding: "10px 14px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", fontSize: 11.5, color: "#34d399", fontWeight: 700 }}>
            <span>Total</span>
            <span style={{ fontFamily: "monospace" }}>{(session.processing_duration / 1000).toFixed(1)}s</span>
          </div>
        </div>
      </Section>

      {/* 3 — MAP Summary */}
      <Section title="MAP Summary">
        <SessionMapTable maps={session.maps} sessionId={session.session_id} />
      </Section>

      {/* 4 — Department Impact */}
      <Section title="Department Impact">
        <DepartmentImpact department_impact={session.department_impact} />
      </Section>

      {/* 5 + 6 — Charts side by side */}
      <Section title="Distributions">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
          <PriorityChart    maps={session.maps} />
          <CapabilityChart  maps={session.maps} />
        </div>
      </Section>

      {/* 7 — Knowledge Graph */}
      <Section title="Knowledge Graph">
        <SessionKnowledgeGraph graph={session.graph} />
      </Section>

      {/* 8 — Verification Plans */}
      <Section title="Verification Plans">
        <VerificationSummary verification_plans={session.verification_plans} />
      </Section>

      {/* 9 — Assignment Preview */}
      <Section title="Assignment Preview">
        <AssignmentPreview maps={session.maps} department_impact={session.department_impact} />
      </Section>
    </div>
  );
}
