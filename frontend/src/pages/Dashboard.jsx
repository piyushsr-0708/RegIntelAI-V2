/**
 * Dashboard.jsx — RegIntel AI V2
 * Executive dashboard wired directly to dashboard state from the pipeline.
 * Charts: Priority Distribution, Department MAPs, Compliance Status,
 *         Automation Coverage, Top Capabilities — all pure SVG, no library.
 */
import { useMemo } from "react";
import {
  useExecutiveKpis,
  useDepartmentSummary,
  useMetadata,
  useComplianceRegister,
} from "../context/FrontendStateContext";

// ─── Existing KPI tile (unchanged) ────────────────────────────────────────────
const KpiTile = ({ label, value, color, sub }) => (
  <div className="card animate-fade-up" style={{ padding: "22px 20px", position: "relative", overflow: "hidden" }}>
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 3, background: color }} />
    <div style={{ fontSize: 32, fontWeight: 900, color: "#f1f5f9", letterSpacing: -1, lineHeight: 1, marginBottom: 8 }}>
      {typeof value === "number" ? value.toLocaleString() : value}
    </div>
    <div style={{ fontSize: 12, fontWeight: 700, color: "#94a3b8", marginBottom: 2 }}>{label}</div>
    {sub && <div style={{ fontSize: 11, color: "#475569" }}>{sub}</div>}
  </div>
);

const formatValue = (value) => {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toLocaleString();
  return value;
};

// ─── Chart: Horizontal bar ────────────────────────────────────────────────────
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

// ─── Chart: Donut ─────────────────────────────────────────────────────────────
function DonutChart({ segments, size = 120 }) {
  const total = segments.reduce((s, x) => s + x.value, 0);
  if (total === 0) return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={size * 0.38} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={size * 0.14} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fill="#475569" fontSize={size * 0.13} fontWeight="700">0</text>
    </svg>
  );

  const cx = size / 2, cy = size / 2, r = size * 0.38, sw = size * 0.14;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={sw} />
      {segments.map((seg, i) => {
        const dash = (seg.value / total) * circ;
        const gap  = circ - dash;
        const el = (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={seg.color} strokeWidth={sw}
            strokeDasharray={`${dash} ${gap}`}
            strokeDashoffset={-offset}
            strokeLinecap="butt"
          />
        );
        offset += dash;
        return el;
      })}
    </svg>
  );
}

// ─── Chart: Arc gauge ─────────────────────────────────────────────────────────
function ArcGauge({ pct, color, size = 120 }) {
  const cx = size / 2, cy = size * 0.62, r = size * 0.38;
  const startX = cx - r;
  const endAngle = Math.PI * (pct / 100);
  const ex = cx + r * Math.cos(Math.PI - endAngle);
  const ey = cy - r * Math.sin(Math.PI - endAngle);
  const large = endAngle > Math.PI / 2 ? 1 : 0;

  return (
    <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
      {/* Track */}
      <path d={`M ${startX} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={size * 0.13} strokeLinecap="round" />
      {/* Fill */}
      {pct > 0 && (
        <path d={`M ${startX} ${cy} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`}
          fill="none" stroke={color} strokeWidth={size * 0.13} strokeLinecap="round" />
      )}
      <text x={cx} y={cy - 4} textAnchor="middle" fill={color} fontSize={size * 0.2} fontWeight="900" fontFamily="monospace">
        {pct.toFixed(1)}%
      </text>
      <text x={cx} y={cy + 12} textAnchor="middle" fill="#475569" fontSize={size * 0.1} fontWeight="700">
        AUTOMATION
      </text>
    </svg>
  );
}

// ─── Chart card wrapper ────────────────────────────────────────────────────────
function ChartCard({ title, children, style }) {
  return (
    <div className="card" style={{ padding: "18px 20px", ...style }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, marginBottom: 16, textTransform: "uppercase" }}>{title}</div>
      {children}
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const kpis       = useExecutiveKpis();
  const deptSummary = useDepartmentSummary();
  const metadata   = useMetadata();
  const register   = useComplianceRegister();

  // Priority distribution — derived from compliance_register
  const priorityCounts = useMemo(() => {
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    for (const r of register) if (r.priority in counts) counts[r.priority]++;
    return counts;
  }, [register]);

  // Top 8 capabilities — derived from compliance_register
  const topCaps = useMemo(() => {
    const counts = {};
    for (const r of register) for (const c of (r.business_capability ?? [])) counts[c] = (counts[c] ?? 0) + 1;
    return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  }, [register]);

  if (!kpis) return <div style={{ color: "#94a3b8", padding: 40 }}>Loading dashboard data…</div>;

  const hasKpiData = Object.values(kpis).some(v => v !== null && v !== undefined && v !== "");
  if (!hasKpiData) return <div style={{ color: "#94a3b8", padding: 40 }}>No dashboard data available yet.</div>;

  const complianceRate = kpis.total_documents > 0
    ? ((kpis.compliant_documents / kpis.total_documents) * 100).toFixed(1)
    : "0.0";

  const deptMax   = Math.max(...deptSummary.map(d => d.total_maps), 1);
  const prioMax   = Math.max(...Object.values(priorityCounts), 1);
  const prioTotal = register.length;
  const capMax    = topCaps[0]?.[1] ?? 1;

  const PRIO_COLORS = { CRITICAL: "#f87171", HIGH: "#fbbf24", MEDIUM: "#60a5fa", LOW: "#34d399" };
  const DEPT_COLORS = ["#a78bfa", "#10b981", "#60a5fa", "#fbbf24", "#f87171"];

  const statusSegments = [
    { label: "Compliant",    value: kpis.compliant_documents,           color: "#34d399" },
    { label: "Partial",      value: kpis.partially_compliant_documents, color: "#fbbf24" },
    { label: "Non-Compliant",value: kpis.non_compliant_documents,       color: "#f87171" },
    { label: "Pending",      value: kpis.pending_documents,             color: "#94a3b8" },
  ].filter(s => s.value > 0);

  return (
    <div>
      {/* ── Page header (unchanged) ─────────────────────────────────────── */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
            <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.5)" }} />
            <h1 className="page-title">Executive Dashboard</h1>
          </div>
          <p className="page-subtitle" style={{ paddingLeft: 14 }}>
            RBI Compliance Intelligence · {formatValue(kpis.total_documents)} documents · {formatValue(kpis.total_maps)} MAPs
          </p>
        </div>
        {metadata && (
          <div style={{ background: "#1a2332", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 9, padding: "9px 16px", textAlign: "right" }}>
            <div style={{ fontSize: 9.5, color: "#475569", fontWeight: 700, letterSpacing: 0.5 }}>PIPELINE RUN</div>
            <div style={{ fontSize: 12.5, fontWeight: 700, color: "#f1f5f9", marginTop: 2 }}>
              {new Date(metadata.generated_timestamp).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
            </div>
            <div style={{ fontSize: 10, color: "#10b981", marginTop: 1, fontWeight: 700 }}>● v{metadata.pipeline_version}</div>
          </div>
        )}
      </div>

      {/* ── KPI row 1 (unchanged) ───────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginBottom: 14 }}>
        <KpiTile label="Total Documents"     value={kpis.total_documents}   color="#a78bfa" sub="RBI Regulatory Circulars" />
        <KpiTile label="MAPs Generated"      value={kpis.total_maps}        color="#10b981" sub="Measurable Action Points" />
        <KpiTile label="Verification Checks" value={kpis.total_checks}      color="#60a5fa" sub="Planned across all MAPs" />
        <KpiTile label="Automation Rate"     value={`${kpis.automation_percentage}%`} color="#fbbf24" sub="Machine-verifiable checks" />
      </div>

      {/* ── KPI row 2 (unchanged) ───────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginBottom: 20 }}>
        <KpiTile label="Compliant Docs"      value={kpis.compliant_documents}           color="#34d399" sub="Fully passing" />
        <KpiTile label="Partially Compliant" value={kpis.partially_compliant_documents} color="#fbbf24" sub="Partial pass" />
        <KpiTile label="Non-Compliant"       value={kpis.non_compliant_documents}       color="#ef4444" sub="Failing checks" />
        <KpiTile label="Pending Review"      value={kpis.pending_documents}             color="#94a3b8" sub="Awaiting execution" />
      </div>

      {/* ── Executive Summary card (unchanged) ─────────────────────────── */}
      <div className="card" style={{ padding: 22, marginBottom: 20 }}>
        <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 14 }}>Executive Summary</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
          <div style={{ padding: "14px 16px", background: "rgba(16,185,129,0.08)", borderRadius: 10, border: "1px solid rgba(16,185,129,0.18)" }}>
            <div style={{ fontSize: 22, fontWeight: 900, color: "#34d399" }}>{complianceRate}%</div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 3, fontWeight: 700 }}>Overall compliance rate</div>
          </div>
          <div style={{ padding: "14px 16px", background: "rgba(148,163,184,0.08)", borderRadius: 10, border: "1px solid rgba(148,163,184,0.18)" }}>
            <div style={{ fontSize: 22, fontWeight: 900, color: "#94a3b8" }}>{formatValue(kpis.pending_documents)}</div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 3, fontWeight: 700 }}>Pending review</div>
          </div>
          <div style={{ padding: "14px 16px", background: "rgba(251,191,36,0.08)", borderRadius: 10, border: "1px solid rgba(251,191,36,0.18)" }}>
            <div style={{ fontSize: 22, fontWeight: 900, color: "#fbbf24" }}>{kpis.automation_percentage}%</div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 3, fontWeight: 700 }}>Automation coverage</div>
          </div>
        </div>
      </div>

      {/* ── Charts row 1: Priority + Department ─────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 14, marginBottom: 14 }}>

        {/* Priority Distribution */}
        <ChartCard title="Priority Distribution">
          {Object.entries(PRIO_COLORS).map(([p, color]) => (
            <HBar key={p} label={p} value={priorityCounts[p]} max={prioMax} color={color} total={prioTotal} />
          ))}
        </ChartCard>

        {/* Department MAP Distribution */}
        <ChartCard title="Department MAP Distribution">
          {deptSummary.map((d, i) => (
            <HBar key={d.department} label={d.department} value={d.total_maps} max={deptMax} color={DEPT_COLORS[i % DEPT_COLORS.length]} total={kpis.total_maps} />
          ))}
        </ChartCard>
      </div>

      {/* ── Charts row 2: Status donut + Automation gauge + Capabilities ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14, marginBottom: 20 }}>

        {/* Compliance Status Distribution */}
        <ChartCard title="Document Compliance Status">
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div style={{ flexShrink: 0 }}>
              <DonutChart segments={statusSegments} size={110} />
            </div>
            <div style={{ flex: 1 }}>
              {[
                { label: "Compliant",     value: kpis.compliant_documents,           color: "#34d399" },
                { label: "Partial",       value: kpis.partially_compliant_documents, color: "#fbbf24" },
                { label: "Non-Compliant", value: kpis.non_compliant_documents,       color: "#f87171" },
                { label: "Pending",       value: kpis.pending_documents,             color: "#94a3b8" },
              ].map(s => (
                <div key={s.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 7 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: "#94a3b8" }}>{s.label}</span>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 700, color: s.color, fontFamily: "monospace" }}>{s.value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>

        {/* Automation Coverage gauge */}
        <ChartCard title="Automation Coverage">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <ArcGauge pct={kpis.automation_percentage} color="#fbbf24" size={140} />
            <div style={{ display: "flex", gap: 20, fontSize: 12 }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 900, color: "#fbbf24", fontSize: 16 }}>{kpis.automation_percentage}%</div>
                <div style={{ color: "#475569", fontSize: 10.5, fontWeight: 600 }}>AUTOMATED</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontWeight: 900, color: "#475569", fontSize: 16 }}>{(100 - kpis.automation_percentage).toFixed(1)}%</div>
                <div style={{ color: "#475569", fontSize: 10.5, fontWeight: 600 }}>MANUAL</div>
              </div>
            </div>
          </div>
        </ChartCard>

        {/* Top Capabilities */}
        <ChartCard title="Top Capabilities by MAP Count">
          {topCaps.map(([cap, count], i) => {
            const colors = ["#38bdf8","#a78bfa","#10b981","#fbbf24","#f87171","#fb923c","#34d399","#60a5fa"];
            return <HBar key={cap} label={cap} value={count} max={capMax} color={colors[i % colors.length]} total={prioTotal} />;
          })}
        </ChartCard>
      </div>

      {/* ── Department table (unchanged) ────────────────────────────────── */}
      <div className="card" style={{ padding: 22 }}>
        <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 16 }}>Department Compliance Summary</div>
        {deptSummary.length === 0 ? (
          <div style={{ padding: "24px 0", textAlign: "center", color: "#64748b" }}>No department data available.</div>
        ) : (
          <div className="card" style={{ overflow: "hidden" }}>
            <table className="data-table">
              <thead>
                <tr>
                  {["Department", "Total MAPs", "Compliant", "Partial", "Non-Compliant", "Pending"].map(h => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deptSummary.map(dept => (
                  <tr key={dept.department} style={{ cursor: "default" }}>
                    <td style={{ fontWeight: 700, color: "#e2e8f0" }}>{dept.department}</td>
                    <td style={{ fontWeight: 700, color: "#a78bfa" }}>{formatValue(dept.total_maps)}</td>
                    <td style={{ color: "#34d399", fontWeight: 600 }}>{formatValue(dept.compliant)}</td>
                    <td style={{ color: "#fbbf24", fontWeight: 600 }}>{formatValue(dept.partial)}</td>
                    <td style={{ color: "#ef4444", fontWeight: 600 }}>{formatValue(dept.non_compliant)}</td>
                    <td style={{ color: "#94a3b8", fontWeight: 600 }}>{formatValue(dept.pending)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
