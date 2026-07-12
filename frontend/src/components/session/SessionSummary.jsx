/**
 * SessionSummary.jsx — RegIntel AI V2
 * Document summary section for the Session Dashboard.
 */

const RISK_COLOR = { HIGH: "#f87171", MEDIUM: "#fbbf24", LOW: "#34d399" };

function StatBox({ label, value, color = "#f1f5f9", mono = false }) {
  return (
    <div style={{ padding: "14px 16px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10 }}>
      <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 900, color, lineHeight: 1, fontFamily: mono ? "monospace" : "inherit" }}>{value ?? "—"}</div>
    </div>
  );
}

export default function SessionSummary({ session }) {
  const riskColor = RISK_COLOR[session.overall_risk] ?? "#94a3b8";
  const durationSec = session.processing_duration ? (session.processing_duration / 1000).toFixed(1) : "—";

  return (
    <div className="card" style={{ padding: 22, marginBottom: 20 }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 18 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: "rgba(96,165,250,0.15)", border: "1px solid rgba(96,165,250,0.25)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" strokeWidth="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#f1f5f9" }}>{session.filename}</div>
              <div style={{ fontSize: 11, color: "#475569", fontFamily: "monospace", marginTop: 2 }}>{session.document_id}</div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: "#475569" }}>
            Uploaded {new Date(session.upload_timestamp).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          <div style={{ padding: "10px 16px", background: `${riskColor}12`, border: `1px solid ${riskColor}30`, borderRadius: 9, textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 3 }}>OVERALL RISK</div>
            <div style={{ fontSize: 16, fontWeight: 900, color: riskColor }}>{session.overall_risk ?? "—"}</div>
          </div>
          <div style={{ padding: "10px 16px", background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.2)", borderRadius: 9, textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 3 }}>STATUS</div>
            <div style={{ fontSize: 13, fontWeight: 800, color: "#34d399" }}>COMPLETED</div>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
        <StatBox label="Pages"           value={session.pages?.toLocaleString()} />
        <StatBox label="Words"           value={session.words?.toLocaleString()} />
        <StatBox label="Requirements"    value={session.requirements_found?.toLocaleString()} color="#60a5fa" />
        <StatBox label="MAPs Generated"  value={session.maps_generated?.toLocaleString()}     color="#10b981" />
        <StatBox label="Departments"     value={session.departments_impacted}                  color="#a78bfa" />
        <StatBox label="Graph Nodes"     value={session.knowledge_graph_nodes?.toLocaleString()} />
        <StatBox label="Automation %"    value={`${session.automation_percentage ?? 0}%`}      color="#fbbf24" />
        <StatBox label="Processing Time" value={`${durationSec}s`}                             color="#34d399" mono />
      </div>
    </div>
  );
}
