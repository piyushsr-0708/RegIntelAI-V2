/**
 * SessionMapDetail.jsx — RegIntel AI V2
 * Session-scoped MAP detail page.
 * Route: /session/:sessionId/map/:mapId
 *
 * Fetches MAP data from GET /maps/{map_id}/detail (same endpoint as MapDetail.jsx).
 * Does NOT rely on session.maps in-memory array, which is empty after browser refresh.
 */
import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useSession } from "../context/SessionContext";
import { fetchMapDetail } from "../utils/api";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

const PRIO_COLOR = { CRITICAL: "#f87171", HIGH: "#fbbf24", MEDIUM: "#60a5fa", LOW: "#34d399" };

function Field({ label, value, color = "#cbd5e1", mono = false, pre = false }) {
  if (value == null || value === "") return null;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 5 }}>
        {label}
      </div>
      {pre ? (
        <pre style={{ fontSize: 12.5, color, lineHeight: 1.65, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: 0, fontFamily: mono ? "monospace" : "inherit" }}>
          {value}
        </pre>
      ) : (
        <div style={{ fontSize: 13, color, lineHeight: 1.6, fontFamily: mono ? "monospace" : "inherit", wordBreak: "break-word" }}>
          {value}
        </div>
      )}
    </div>
  );
}

function Card({ title, children, accent }) {
  return (
    <div className="card" style={{ padding: "18px 20px", marginBottom: 16, borderLeft: accent ? `3px solid ${accent}` : undefined }}>
      {title && (
        <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 14 }}>
          {title}
        </div>
      )}
      {children}
    </div>
  );
}

export default function SessionMapDetail() {
  const { sessionId, mapId } = useParams();
  const navigate = useNavigate();
  const session  = useSession(decodeURIComponent(sessionId));

  const [mapData,  setMapData]  = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);

  const decodedMapId = decodeURIComponent(mapId);
  const backToSession = () => navigate(`/session/${encodeURIComponent(sessionId)}`);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchMapDetail(decodedMapId)
      .then((data) => { setMapData(data); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [decodedMapId]);

  // ── Loading (covers both MAP fetch and any SessionContext init delay) ───────
  if (loading) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="36" height="36" viewBox="0 0 36 36" style={{ animation: "spin 1s linear infinite", marginBottom: 14 }}>
        <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="3"/>
        <path d="M18 4a14 14 0 0 1 14 14" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round"/>
      </svg>
      <div style={{ fontSize: 13, color: "#10b981", fontWeight: 600 }}>Loading MAP…</div>
    </div>
  );

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error || !mapData) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>📋</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#94a3b8", marginBottom: 8 }}>
        {error ? "Failed to load MAP" : "MAP not found"}
      </div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20, fontFamily: "monospace" }}>{decodedMapId}</div>
      {error && <div style={{ fontSize: 12, color: "#f87171", marginBottom: 16 }}>{error}</div>}
      <button onClick={backToSession}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Session
      </button>
    </div>
  );

  // mapData comes from GET /maps/{id}/detail — shape mirrors MapDetail.jsx usage
  // The detail endpoint returns the full MAP record plus verification_plan, tasks, etc.
  // For the session view we use the fields available from the detail response.
  const m = mapData;
  const priority = String(m.priority ?? m.criticality ?? "MEDIUM");
  const pColor = PRIO_COLOR[priority] ?? "#94a3b8";

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      <button
        onClick={backToSession}
        style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}
      >
        ← Back to Session
      </button>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 9px", borderRadius: 5, border: "1px solid rgba(52,211,153,0.2)" }}>
              {decodedMapId}
            </span>
            <PriorityBadge priority={priority.charAt(0) + priority.slice(1).toLowerCase()} size="lg" />
            <StatusBadge status={m.compliance_status ?? m.status} />
            {(m.department_name ?? m.owner_department) && (
              <span style={{ fontSize: 11, color: "#64748b", background: "#162030", padding: "2px 8px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.06)" }}>
                {m.department_name ?? m.owner_department}
              </span>
            )}
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.4, margin: 0 }}>
            {m.control_name ?? m.title ?? decodedMapId}
          </h1>
        </div>
        <div style={{ textAlign: "center", flexShrink: 0, padding: "12px 18px", background: `${pColor}10`, border: `1px solid ${pColor}30`, borderRadius: 10 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 3 }}>AUTOMATION</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: pColor }}>
            {(m.automation_percent ?? m.automation_percentage) != null
              ? `${Number(m.automation_percent ?? m.automation_percentage).toFixed(1)}%`
              : "—"}
          </div>
        </div>
      </div>

      {/* Core fields */}
      <Card title="MAP Detail" accent="#34d399">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 14 }}>
          {[
            ["Document",   m.source_document_id ?? m.document_id ?? m.control_id?.split("-")[0], "#60a5fa"],
            ["Department", m.department_name ?? m.owner_department,                               "#a78bfa"],
            ["Priority",   priority,                                                               pColor],
            ["Status",     m.status,                                                               "#94a3b8"],
          ].map(([lbl, val, c]) => val ? (
            <div key={lbl} style={{ padding: "10px 12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
              <div style={{ fontSize: 9.5, color: "#475569", fontWeight: 700, marginBottom: 4, textTransform: "uppercase" }}>{lbl}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: c }}>{val}</div>
            </div>
          ) : null)}
        </div>
        <Field label="Control Objective"   value={m.control_objective ?? m.objective} pre />
        <Field label="Control Description"  value={m.control_description ?? m.description} pre />
        <Field label="AI Rationale"         value={m.ai_rationale} />
        <Field label="Source Requirement"   value={m.source_requirement_text} pre />
      </Card>

      {/* Verification Plan */}
      {m.verification_plan && (
        <Card title="Verification Plan" accent="#38bdf8">
          <Field label="Plan" value={typeof m.verification_plan === 'object' ? JSON.stringify(m.verification_plan, null, 2) : m.verification_plan} pre />
        </Card>
      )}

      {/* Session context footer */}
      <div style={{ padding: "12px 16px", background: "rgba(96,165,250,0.05)", border: "1px solid rgba(96,165,250,0.12)", borderRadius: 9, fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
        <span style={{ color: "#60a5fa", fontWeight: 700 }}>Session artefact</span> — this MAP was generated during session{" "}
        <code style={{ color: "#94a3b8", fontSize: 11 }}>{session?.session_id ?? decodeURIComponent(sessionId)}</code> from document{" "}
        <code style={{ color: "#60a5fa", fontSize: 11 }}>{session?.document_id ?? m.source_document_id ?? m.document_id ?? "—"}</code>.
      </div>
    </div>
  );
}
