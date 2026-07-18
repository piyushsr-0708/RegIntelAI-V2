/**
 * VerificationSummary.jsx — RegIntel AI V2
 * Verification plans generated for this session.
 */
import { PriorityBadge } from "../Badges";

export default function VerificationSummary({ verification_plans }) {
  if (!verification_plans?.length) return null;

  return (
    <div className="card" style={{ overflow: "hidden", marginBottom: 20 }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase" }}>
          Verification Plans — {verification_plans.length} generated
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              {["Plan ID", "MAP ID", "Department", "Priority", "Checks", "Machine Verifiable", "Status"].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {verification_plans.map((vp) => {
              const planId   = String(vp.plan_id ?? "");
              const mapId    = String(vp.map_id ?? vp.requirement_id ?? "");
              const dept     = String(vp.department ?? (vp.candidate_departments ?? [])[0] ?? "—");
              const priority = String(vp.priority ?? vp.criticality ?? "MEDIUM");
              const checks   = Array.isArray(vp.checks) ? vp.checks.length : (vp.checks ?? vp.total_checks ?? 0);
              const machineVerifiable = vp.machine_verifiable ?? (vp.machine_verifiable_checks > 0) ?? false;
              const status   = vp.status ?? "PENDING";
              return (
              <tr key={planId} style={{ cursor: "default" }}>
                <td>
                  <span style={{ fontFamily: "monospace", fontSize: 10, color: "#60a5fa", background: "rgba(96,165,250,0.1)", padding: "2px 6px", borderRadius: 4 }}>
                    {planId.slice(-16)}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: "monospace", fontSize: 10, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "2px 6px", borderRadius: 4 }}>
                    {mapId ? mapId.slice(-16) : "—"}
                  </span>
                </td>
                <td style={{ fontSize: 12, color: "#94a3b8" }}>{dept}</td>
                <td><PriorityBadge priority={priority.charAt(0) + priority.slice(1).toLowerCase()} /></td>
                <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: 12 }}>{checks}</td>
                <td>
                  <span style={{ fontSize: 11, fontWeight: 700, color: machineVerifiable ? "#34d399" : "#475569" }}>
                    {machineVerifiable ? "✓ Yes" : "✕ No"}
                  </span>
                </td>
                <td>
                  <span style={{ fontSize: 11, color: "#94a3b8", background: "rgba(148,163,184,0.1)", border: "1px solid rgba(148,163,184,0.2)", padding: "2px 8px", borderRadius: 20, fontWeight: 700 }}>
                    {status}
                  </span>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
