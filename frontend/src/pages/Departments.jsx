/**
 * Departments.jsx — RegIntel AI V2
 * Milestone 1 stub: risk ranking + heatmap from department_summary.
 * Full version in Milestone 2.
 */
import { useDepartmentSummary } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";

const riskScore = (dept) => {
  const total = dept.total_maps || 1;
  return Math.round(((dept.non_compliant * 3 + dept.partial * 1) / (total * 3)) * 100);
};

const RISK_COLOR = (s) => s >= 70 ? "#f87171" : s >= 45 ? "#fbbf24" : s >= 25 ? "#60a5fa" : "#34d399";

export default function Departments() {
  const deptSummary = useDepartmentSummary();
  const sorted = [...deptSummary].map(d => ({ ...d, risk: riskScore(d) })).sort((a, b) => b.risk - a.risk);
  const maxRisk = Math.max(...sorted.map(d => d.risk), 1);
  const totalMaps = sorted.reduce((a, d) => a + d.total_maps, 0);

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#f87171,#ef4444)", boxShadow: "0 0 10px rgba(239,68,68,0.4)" }} />
          <h1 className="page-title">Department Risk Dashboard</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          Compliance burden across <strong style={{ color: "#f1f5f9" }}>{sorted.length}</strong> departments · {totalMaps.toLocaleString()} total MAPs
        </p>
      </div>

      {/* Top 3 alert cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 22 }}>
        {sorted.slice(0, 3).map((d, i) => {
          const color = RISK_COLOR(d.risk);
          return (
            <div key={d.department} className="card animate-fade-up" style={{ padding: "18px 20px", borderLeft: `3px solid ${color}`, animationDelay: `${i * 60}ms` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 10 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: color, display: "inline-block", animation: "pulse-dot 2s ease infinite" }} />
                <span style={{ fontSize: 10, fontWeight: 700, color, letterSpacing: 0.5 }}>#{i + 1} HIGHEST RISK</span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#f1f5f9", marginBottom: 12, lineHeight: 1.3 }}>{d.department}</div>
              <div style={{ display: "flex", gap: 20 }}>
                {[["Risk Score", d.risk, color], ["Non-Compliant", d.non_compliant, "#f87171"], ["Total MAPs", d.total_maps, "#94a3b8"]].map(([lbl, val, c]) => (
                  <div key={lbl}>
                    <div style={{ fontSize: 22, fontWeight: 900, color: c, lineHeight: 1 }}>{val.toLocaleString()}</div>
                    <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{lbl}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Risk ranking bar chart */}
      <div className="card" style={{ padding: "22px 20px", marginBottom: 18 }}>
        <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 16 }}>Department Risk Ranking (Computed)</div>
        <svg width="100%" height={Math.max(260, 10 + sorted.length * 30)} viewBox={`0 0 560 ${Math.max(260, 10 + sorted.length * 30)}`} preserveAspectRatio="xMinYMin meet" style={{ display: "block" }}>
          {sorted.map((d, i) => {
            const labelW = 160, barH = 16, gap = 14, top = 6;
            const y = top + i * (barH + gap);
            const maxBarW = 340;
            const barW = (d.risk / maxRisk) * maxBarW;
            const color = RISK_COLOR(d.risk);
            return (
              <g key={d.department}>
                <text x={0} y={y + barH / 2 + 4} fontSize={10.5} fill="#94a3b8" fontWeight="500">{d.department}</text>
                <rect x={labelW} y={y} width={Math.max(barW, 4)} height={barH} rx={3} fill={color} opacity={0.8} />
                <text x={labelW + Math.max(barW, 4) + 8} y={y + barH / 2 + 4} fontSize={10.5} fill="#64748b" fontWeight="700">{d.risk}</text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Priority heatmap */}
      <div className="card" style={{ padding: 22, marginBottom: 18 }}>
        <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 4 }}>Priority Heatmap</div>
        <div style={{ fontSize: 11.5, color: "#64748b", marginBottom: 16 }}>MAP counts by department and compliance status</div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "3px", minWidth: 520 }}>
            <thead>
              <tr>
                <th style={{ padding: "7px 12px", textAlign: "left", fontSize: 11, color: "#475569", fontWeight: 700 }}>Department</th>
                {[["Compliant","#34d399"],["Partial","#fbbf24"],["Non-Compliant","#f87171"],["Pending","#94a3b8"]].map(([lbl, c]) => (
                  <th key={lbl} style={{ padding: "7px 14px", textAlign: "center", fontSize: 11, fontWeight: 700, color: c }}>{lbl}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map(d => (
                <tr key={d.department}>
                  <td style={{ padding: "5px 12px", fontSize: 12, color: "#94a3b8", fontWeight: 500, whiteSpace: "nowrap" }}>{d.department}</td>
                  {[d.compliant, d.partial, d.non_compliant, d.pending].map((v, j) => {
                    const colors = ["#34d399","#fbbf24","#f87171","#94a3b8"];
                    const c = colors[j];
                    return (
                      <td key={j} style={{ padding: "4px 14px", textAlign: "center" }}>
                        <div style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: 38, height: 32, borderRadius: 6, background: `${c}18`, fontWeight: 800, fontSize: 13.5, color: c }}>
                          {v?.toLocaleString() ?? 0}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
