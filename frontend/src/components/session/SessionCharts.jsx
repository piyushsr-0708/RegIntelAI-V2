/**
 * PriorityChart.jsx — RegIntel AI V2
 * Priority distribution chart for the Session Dashboard (pure SVG bars).
 */

const PRIO_COLORS = { CRITICAL: "#f87171", HIGH: "#fbbf24", MEDIUM: "#60a5fa", LOW: "#34d399" };

function HBar({ label, value, max, color, total }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 11.5, color, fontWeight: 700, fontFamily: "monospace" }}>
          {value.toLocaleString()}
          {total > 0 && <span style={{ color: "#475569", fontWeight: 400 }}> ({((value / total) * 100).toFixed(1)}%)</span>}
        </span>
      </div>
      <div style={{ height: 7, background: "rgba(255,255,255,0.05)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

export function PriorityChart({ maps }) {
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const m of maps) if (m.priority in counts) counts[m.priority]++;
  const max   = Math.max(...Object.values(counts), 1);
  const total = maps.length;

  return (
    <div className="card" style={{ padding: "18px 20px", marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 16 }}>
        Priority Distribution
      </div>
      {Object.entries(PRIO_COLORS).map(([p, color]) => (
        <HBar key={p} label={p} value={counts[p]} max={max} color={color} total={total} />
      ))}
    </div>
  );
}

/**
 * CapabilityChart.jsx — RegIntel AI V2
 * Business capability distribution for the Session Dashboard.
 */
const CAP_COLORS = ["#38bdf8","#a78bfa","#10b981","#fbbf24","#f87171","#fb923c","#34d399","#60a5fa"];

export function CapabilityChart({ maps }) {
  const counts = {};
  for (const m of maps) for (const c of (m.business_capability ?? [])) counts[c] = (counts[c] ?? 0) + 1;
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max    = sorted[0]?.[1] ?? 1;
  const total  = maps.length;

  return (
    <div className="card" style={{ padding: "18px 20px", marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 16 }}>
        Business Capability Distribution
      </div>
      {sorted.map(([cap, count], i) => (
        <HBar key={cap} label={cap} value={count} max={max} color={CAP_COLORS[i % CAP_COLORS.length]} total={total} />
      ))}
      {sorted.length === 0 && (
        <div style={{ color: "#475569", fontSize: 12, textAlign: "center", padding: "20px 0" }}>No capability data.</div>
      )}
    </div>
  );
}
