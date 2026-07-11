/**
 * Dashboard.jsx — RegIntel AI V2
 * Executive dashboard wired directly to dashboard state from the pipeline.
 */
import { useExecutiveKpis, useDepartmentSummary, useMetadata } from "../context/FrontendStateContext";

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

export default function Dashboard() {
  const kpis = useExecutiveKpis();
  const deptSummary = useDepartmentSummary();
  const metadata = useMetadata();

  if (!kpis) {
    return (
      <div style={{ color: "#94a3b8", padding: 40 }}>
        Loading dashboard data…
      </div>
    );
  }

  const hasKpiData = Object.values(kpis).some((value) => value !== null && value !== undefined && value !== "");
  if (!hasKpiData) {
    return (
      <div style={{ color: "#94a3b8", padding: 40 }}>
        No dashboard data available yet.
      </div>
    );
  }

  const complianceRate = kpis.total_documents > 0
    ? ((kpis.compliant_documents / kpis.total_documents) * 100).toFixed(1)
    : "0.0";

  return (
    <div>
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginBottom: 24 }}>
        <KpiTile label="Total Documents" value={kpis.total_documents} color="#a78bfa" sub="RBI Regulatory Circulars" />
        <KpiTile label="MAPs Generated" value={kpis.total_maps} color="#10b981" sub="Measurable Action Points" />
        <KpiTile label="Verification Checks" value={kpis.total_checks} color="#60a5fa" sub="Planned across all MAPs" />
        <KpiTile label="Automation Rate" value={`${kpis.automation_percentage}%`} color="#fbbf24" sub="Machine-verifiable checks" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14, marginBottom: 24 }}>
        <KpiTile label="Compliant Docs" value={kpis.compliant_documents} color="#34d399" sub="Fully passing" />
        <KpiTile label="Partially Compliant" value={kpis.partially_compliant_documents} color="#fbbf24" sub="Partial pass" />
        <KpiTile label="Non-Compliant" value={kpis.non_compliant_documents} color="#ef4444" sub="Failing checks" />
        <KpiTile label="Pending Review" value={kpis.pending_documents} color="#94a3b8" sub="Awaiting execution" />
      </div>

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

      <div className="card" style={{ padding: 22 }}>
        <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 16 }}>Department Compliance Summary</div>
        {deptSummary.length === 0 ? (
          <div style={{ padding: "24px 0", textAlign: "center", color: "#64748b" }}>No department data available.</div>
        ) : (
          <div className="card" style={{ overflow: "hidden" }}>
            <table className="data-table">
              <thead>
                <tr>
                  {["Department", "Total MAPs", "Compliant", "Partial", "Non-Compliant", "Pending"].map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deptSummary.map((dept) => (
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
