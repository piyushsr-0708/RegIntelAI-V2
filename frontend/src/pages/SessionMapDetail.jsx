/**
 * SessionMapDetail.jsx — RegIntel AI V2
 * Session-scoped MAP detail page.
 * Reads from SessionContext only — never redirects to the Compliance Register.
 * Route: /session/:sessionId/map/:mapId
 */
import { useParams, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
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

  const backToSession = () => navigate(`/session/${encodeURIComponent(sessionId)}`);

  if (!session) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>🔍</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#94a3b8", marginBottom: 8 }}>Session not found</div>
      <button onClick={() => navigate("/pipeline")}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Pipeline
      </button>
    </div>
  );

  const decodedMapId = decodeURIComponent(mapId);
  const map = session.maps?.find((m) => m.map_id === decodedMapId);

  if (!map) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>📋</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#94a3b8", marginBottom: 8 }}>MAP not found in this session</div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20, fontFamily: "monospace" }}>{decodedMapId}</div>
      <button onClick={backToSession}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Session
      </button>
    </div>
  );

  const pColor = PRIO_COLOR[map.priority] ?? "#94a3b8";

  // Find matching verification plan
  const vp = session.verification_plans?.find((v) => v.map_id === map.map_id);

  // Find matching requirement
  const req = session.requirements?.find((r) => r.req_id === map.req_id);

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Back button */}
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
              {map.map_id}
            </span>
            <PriorityBadge priority={map.priority.charAt(0) + map.priority.slice(1).toLowerCase()} size="lg" />
            <StatusBadge status={map.compliance_status} />
            <span style={{ fontSize: 11, color: "#64748b", background: "#162030", padding: "2px 8px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.06)" }}>
              {map.department}
            </span>
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.4, margin: 0 }}>{map.title}</h1>
        </div>
        <div style={{ textAlign: "center", flexShrink: 0, padding: "12px 18px", background: `${pColor}10`, border: `1px solid ${pColor}30`, borderRadius: 10 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 3 }}>AUTOMATION</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: pColor }}>{(map.automation_percentage ?? 0).toFixed(1)}%</div>
        </div>
      </div>

      {/* 1 — Source Requirement */}
      <Card title="Source Requirement" accent="#a78bfa">
        <Field label="Requirement ID"   value={map.req_id}       mono />
        <Field label="Requirement Text" value={map._req_text ?? req?.text ?? map.title.replace(/^MAP:\s*/i, "")} pre />
        <Field label="Obligation Type"  value={map._obligation ?? req?.obligation_type} color="#fbbf24" />
        <Field label="Source Page"      value={map._source_page != null ? `Page ${map._source_page}` : null} />
        <Field label="Confidence"       value={map._confidence != null ? `${(map._confidence * 100).toFixed(0)}%` : req?.confidence != null ? `${(req.confidence * 100).toFixed(0)}%` : null} color="#34d399" />
        {req?.keywords?.length > 0 && (
          <div>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>Keywords</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {req.keywords.map((k) => (
                <span key={k} style={{ fontSize: 11, color: "#38bdf8", background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.2)", padding: "2px 9px", borderRadius: 20, fontWeight: 600 }}>{k}</span>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* 2 — Generated MAP */}
      <Card title="Generated MAP" accent="#34d399">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 14 }}>
          {[
            ["Document",   map.document_id,       "#60a5fa"],
            ["Department", map.department,         "#a78bfa"],
            ["Priority",   map.priority,           pColor],
            ["Status",     map.compliance_status,  "#94a3b8"],
            ["Blockers",   map.failed_blocker_count ?? 0, map.failed_blocker_count > 0 ? "#f87171" : "#34d399"],
          ].map(([lbl, val, c]) => (
            <div key={lbl} style={{ padding: "10px 12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
              <div style={{ fontSize: 9.5, color: "#475569", fontWeight: 700, marginBottom: 4, textTransform: "uppercase" }}>{lbl}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: c }}>{val}</div>
            </div>
          ))}
        </div>
        <Field label="Decision Rationale" value={map.decision_rationale} />
        {map.business_capability?.length > 0 && (
          <div>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>Business Capabilities</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {map.business_capability.map((c) => (
                <span key={c} style={{ fontSize: 11, color: "#22d3ee", background: "rgba(34,211,238,0.1)", border: "1px solid rgba(34,211,238,0.2)", padding: "2px 9px", borderRadius: 20, fontWeight: 600 }}>{c}</span>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* 3 — Verification Plan */}
      <Card title="Verification Plan" accent="#38bdf8">
        {vp && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, marginBottom: 14 }}>
              {[
                ["Plan ID",  vp.plan_id.slice(-16), "#60a5fa"],
                ["Checks",   vp.checks,             "#a78bfa"],
                ["Machine Verifiable", vp.machine_verifiable ? "Yes" : "No", vp.machine_verifiable ? "#34d399" : "#475569"],
                ["Status",   vp.status,             "#94a3b8"],
              ].map(([lbl, val, c]) => (
                <div key={lbl} style={{ padding: "10px 12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
                  <div style={{ fontSize: 9.5, color: "#475569", fontWeight: 700, marginBottom: 4, textTransform: "uppercase" }}>{lbl}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: c }}>{val}</div>
                </div>
              ))}
            </div>
            {vp.check_types?.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>Check Types</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {vp.check_types.map((ct, i) => (
                    <span key={i} style={{ fontSize: 11, color: "#38bdf8", background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.2)", padding: "2px 9px", borderRadius: 6, fontFamily: "monospace", fontWeight: 600 }}>{ct}</span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      {/* 4 — Session context */}
      <div style={{ padding: "12px 16px", background: "rgba(96,165,250,0.05)", border: "1px solid rgba(96,165,250,0.12)", borderRadius: 9, fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
        <span style={{ color: "#60a5fa", fontWeight: 700 }}>Session artefact</span> — this MAP was generated during session{" "}
        <code style={{ color: "#94a3b8", fontSize: 11 }}>{session.session_id}</code> from document{" "}
        <code style={{ color: "#60a5fa", fontSize: 11 }}>{session.document_id}</code>.
        It exists only in the current browser session and is not persisted to the Compliance Register.
      </div>
    </div>
  );
}
