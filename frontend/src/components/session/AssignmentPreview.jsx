/**
 * AssignmentPreview.jsx — RegIntel AI V2
 * Preview of what each department will receive after publishing this session.
 */
import { PriorityBadge } from "../Badges";

export default function AssignmentPreview({ maps, department_impact }) {
  if (!department_impact?.length) return null;

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 12 }}>
        Assignment Preview
      </div>
      <div style={{ display: "grid", gap: 12 }}>
        {department_impact.map((d) => {
          const deptMaps = maps.filter((m) => m.department === d.department).slice(0, 5);
          return (
            <div key={d.department} className="card" style={{ padding: "16px 18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#f1f5f9" }}>{d.department}</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <span style={{ fontSize: 11, color: "#a78bfa", background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.2)", padding: "2px 10px", borderRadius: 20, fontWeight: 700 }}>
                    {d.map_count} MAPs
                  </span>
                  {d.critical > 0 && (
                    <span style={{ fontSize: 11, color: "#f87171", background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.2)", padding: "2px 10px", borderRadius: 20, fontWeight: 700 }}>
                      {d.critical} Critical
                    </span>
                  )}
                </div>
              </div>

              {/* Sample MAPs */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {deptMaps.map((m) => (
                  <div key={m.map_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", background: "rgba(255,255,255,0.02)", borderRadius: 7, border: "1px solid rgba(255,255,255,0.04)" }}>
                    <span style={{ fontFamily: "monospace", fontSize: 10, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "1px 6px", borderRadius: 4, flexShrink: 0 }}>
                      {m.map_id.slice(-14)}
                    </span>
                    <span style={{ fontSize: 12, color: "#94a3b8", flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {m.title}
                    </span>
                    <PriorityBadge priority={m.priority.charAt(0) + m.priority.slice(1).toLowerCase()} />
                  </div>
                ))}
                {d.map_count > 5 && (
                  <div style={{ fontSize: 11, color: "#475569", paddingLeft: 10 }}>
                    + {d.map_count - 5} more MAPs
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
