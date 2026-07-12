/**
 * DepartmentImpact.jsx — RegIntel AI V2
 * Department impact cards for the Session Dashboard.
 */

const DEPT_COLORS = ["#a78bfa", "#10b981", "#60a5fa", "#fbbf24", "#f87171"];

export default function DepartmentImpact({ department_impact }) {
  if (!department_impact?.length) return null;

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 12 }}>
        Department Impact
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
        {department_impact.map((d, i) => {
          const color = DEPT_COLORS[i % DEPT_COLORS.length];
          return (
            <div key={d.department} className="card" style={{ padding: "16px 18px", borderLeft: `3px solid ${color}` }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", marginBottom: 10 }}>{d.department}</div>
              <div style={{ fontSize: 22, fontWeight: 900, color, marginBottom: 10 }}>{d.map_count.toLocaleString()}</div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {[
                  ["Critical", d.critical, "#f87171"],
                  ["High",     d.high,     "#fbbf24"],
                  ["Medium",   d.medium,   "#60a5fa"],
                  ["Low",      d.low,      "#34d399"],
                ].map(([lbl, val, c]) => (
                  <div key={lbl}>
                    <div style={{ fontSize: 14, fontWeight: 800, color: c, lineHeight: 1 }}>{val}</div>
                    <div style={{ fontSize: 9.5, color: "#475569", marginTop: 2, fontWeight: 600 }}>{lbl}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
