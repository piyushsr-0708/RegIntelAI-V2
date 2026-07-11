/**
 * MapDetail.jsx — RegIntel AI V2
 * Milestone 1 stub: reads from compliance_register + detailed_maps (if available).
 * Full implementation in Milestone 4 (requires Aggregator to output detailed_maps).
 */
import { useParams, useNavigate } from "react-router-dom";
import { useComplianceRegister, useMapDetail } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

export default function MapDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const mapId = decodeURIComponent(id);

  const register = useComplianceRegister();
  const detail   = useMapDetail(mapId);

  const listItem = register.find(m => m.map_id === mapId);

  if (!listItem) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 44, marginBottom: 12 }}>📋</div>
      <div style={{ fontSize: 17, fontWeight: 700, color: "#94a3b8" }}>MAP not found</div>
      <button onClick={() => navigate("/maps")} style={{ marginTop: 16, padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>← Back to Register</button>
    </div>
  );

  const pColor = { CRITICAL: "#f87171", HIGH: "#fbbf24", MEDIUM: "#60a5fa", LOW: "#34d399" }[listItem.priority] || "#94a3b8";

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />
      <button onClick={() => navigate("/maps")} style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}>
        ← Back to Register
      </button>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontFamily: "monospace", fontSize: 11.5, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 9px", borderRadius: 5, border: "1px solid rgba(52,211,153,0.2)" }}>{listItem.map_id}</span>
            <PriorityBadge priority={listItem.priority.charAt(0) + listItem.priority.slice(1).toLowerCase()} size="lg" />
            <StatusBadge status={listItem.compliance_status} />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.35 }}>{listItem.title}</h1>
        </div>
        <div style={{ textAlign: "center", flexShrink: 0, padding: "14px 20px", background: `${pColor}10`, border: `1px solid ${pColor}30`, borderRadius: 10 }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, marginBottom: 4 }}>AUTOMATION</div>
          <div style={{ fontSize: 24, fontWeight: 900, color: pColor }}>{listItem.automation_percentage.toFixed(1)}%</div>
        </div>
      </div>

      {/* Details grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 16 }}>
        {[
          ["DOCUMENT", listItem.document_id, "#60a5fa"],
          ["DEPARTMENT", listItem.department, "#a78bfa"],
          ["DECISION RATIONALE", listItem.decision_rationale, "#94a3b8"],
        ].map(([label, val, color]) => (
          <div key={label} className="card" style={{ padding: "14px 16px" }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: 0.5 }}>{label}</div>
            <div style={{ fontSize: 13, color, fontWeight: 600, wordBreak: "break-word" }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Business capabilities */}
      {listItem.business_capability?.length > 0 && (
        <div className="card" style={{ padding: 18, marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, marginBottom: 10, letterSpacing: 0.5 }}>BUSINESS CAPABILITIES</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
            {listItem.business_capability.map(cap => (
              <span key={cap} style={{ padding: "4px 12px", borderRadius: 20, background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.2)", fontSize: 12, color: "#60a5fa", fontWeight: 600 }}>{cap}</span>
            ))}
          </div>
        </div>
      )}

      {/* Detail section (available after Milestone 4) */}
      {detail ? (
        <div className="card" style={{ padding: 22, background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.15)" }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: "#10b981", marginBottom: 12, letterSpacing: 0.7 }}>AI REASONING (from Aggregator)</div>
          <pre style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.7, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(detail, null, 2)}</pre>
        </div>
      ) : (
        <div style={{ padding: "14px 18px", background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.2)", borderRadius: 10, fontSize: 12, color: "#94a3b8" }}>
          <strong style={{ color: "#a78bfa" }}>Milestone 4 pending.</strong>{" "}
          Deep-dive MAP details (AI reasoning, source requirement text, related MAPs, verification plan summary) require the Dashboard Aggregator to output <code style={{ color: "#c4b5fd" }}>detailed_maps</code> in <code style={{ color: "#c4b5fd" }}>frontend_state.json</code>.
        </div>
      )}
    </div>
  );
}
