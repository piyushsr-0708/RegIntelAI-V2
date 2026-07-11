/**
 * FullTextModal.jsx — Ported from V1.
 * No Axios or backend calls. Data is passed entirely via props.
 */
import React from "react";

export default function FullTextModal({ isOpen, onClose, data, type = "requirement" }) {
  if (!isOpen || !data) return null;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      onClick={handleBackdropClick}
      style={{
        position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
        background: "rgba(0, 0, 0, 0.75)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 9999, padding: 20,
      }}
    >
      <div style={{
        background: "#1a2332", borderRadius: 12, maxWidth: 900, width: "100%",
        maxHeight: "90vh", display: "flex", flexDirection: "column",
        border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }}>
        {/* Header */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid rgba(255,255,255,0.1)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#f1f5f9", marginBottom: 4 }}>
              {type === "assignment" ? "Assignment Details" : "Requirement Details"}
            </div>
            <div style={{ fontSize: 12, color: "#64748b", fontFamily: "monospace", fontWeight: 600 }}>
              {type === "assignment" && data.requirement?.requirement_id
                ? `Requirement: ${data.requirement.requirement_id}`
                : data.requirement_id || data.req_id || data.map_id || "ID not available"}
            </div>
          </div>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#94a3b8", fontSize: 24, cursor: "pointer", padding: 0, width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 6, transition: "all 0.2s" }}
            onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.1)"; e.currentTarget.style.color = "#f1f5f9"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#94a3b8"; }}>
            ×
          </button>
        </div>

        {/* Metadata */}
        <div style={{ padding: "16px 24px", borderBottom: "1px solid rgba(255,255,255,0.05)", background: "#162030" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
            {data.department && (
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>DEPARTMENT</div>
                <div style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 600 }}>{data.department}</div>
              </div>
            )}
            {data.compliance_status && (
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>STATUS</div>
                <div style={{ fontSize: 11, color: data.compliance_status === "COMPLIANT" ? "#34d399" : data.compliance_status === "NON_COMPLIANT" ? "#f87171" : "#fbbf24", fontWeight: 700, textTransform: "uppercase" }}>
                  {data.compliance_status}
                </div>
              </div>
            )}
            {data.priority && (
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>PRIORITY</div>
                <div style={{ fontSize: 11, color: data.priority === "CRITICAL" ? "#ef4444" : data.priority === "HIGH" ? "#fbbf24" : "#60a5fa", fontWeight: 700 }}>
                  {data.priority}
                </div>
              </div>
            )}
            {data.automation_percentage != null && (
              <div>
                <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 2 }}>AUTOMATION</div>
                <div style={{ fontSize: 13, color: "#34d399", fontWeight: 600 }}>{data.automation_percentage.toFixed(1)}%</div>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px" }}>
          <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>TITLE / DESCRIPTION</div>
          <div style={{ fontSize: 14, color: "#e2e8f0", lineHeight: 1.7, whiteSpace: "pre-wrap", wordWrap: "break-word" }}>
            {data.title || data.text || data.requirement?.text || "No text available"}
          </div>
          {data.decision_rationale && (
            <div style={{ marginTop: 20, paddingTop: 20, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>DECISION RATIONALE</div>
              <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{data.decision_rationale}</div>
            </div>
          )}
          {data.business_capability?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, marginBottom: 8 }}>BUSINESS CAPABILITIES</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {data.business_capability.map(cap => (
                  <span key={cap} style={{ padding: "3px 10px", borderRadius: 20, background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.2)", fontSize: 11, color: "#60a5fa", fontWeight: 600 }}>{cap}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid rgba(255,255,255,0.1)", display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "10px 24px", borderRadius: 8, background: "#60a5fa", color: "#fff", border: "none", fontSize: 13, fontWeight: 700, cursor: "pointer", transition: "all 0.2s" }}
            onMouseEnter={e => e.currentTarget.style.background = "#3b82f6"}
            onMouseLeave={e => e.currentTarget.style.background = "#60a5fa"}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
