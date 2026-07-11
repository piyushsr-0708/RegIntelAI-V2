/**
 * AssignmentCenter.jsx — RegIntel AI V2
 * Milestone 1 stub: Shows department-level compliance summary from FrontendStateContext.
 * Full publish/assign workflow in Milestone 2.
 */
import { useDepartmentSummary, useExecutiveKpis } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";

export default function AssignmentCenter() {
  const deptSummary = useDepartmentSummary();
  const kpis = useExecutiveKpis();

  const totalPending = deptSummary.reduce((a, d) => a + (d.pending ?? 0), 0);

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.4)" }} />
          <h1 className="page-title">Assignment Center</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>Review and track compliance assignments across departments</p>
      </div>

      {/* Summary card */}
      <div style={{ background: "linear-gradient(135deg, #064e3b 0%, #065f46 100%)", borderRadius: 12, padding: 24, marginBottom: 24, border: "1px solid rgba(16,185,129,0.3)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 48, height: 48, borderRadius: 10, background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>📋</div>
          <div>
            <div style={{ fontSize: 34, fontWeight: 900, color: "#fff", lineHeight: 1 }}>{totalPending.toLocaleString()}</div>
            <div style={{ fontSize: 14, color: "rgba(255,255,255,0.8)", marginTop: 3 }}>
              Pending MAPs Across {deptSummary.length} Departments
            </div>
          </div>
          {kpis && (
            <div style={{ marginLeft: "auto", textAlign: "right" }}>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 4 }}>Total MAPs</div>
              <div style={{ fontSize: 20, fontWeight: 900, color: "#34d399" }}>{kpis.total_maps.toLocaleString()}</div>
            </div>
          )}
        </div>
      </div>

      {/* Department assignment cards */}
      <div style={{ display: "grid", gap: 14 }}>
        {deptSummary.map((dept, i) => (
          <div key={dept.department} className="card animate-fade-up" style={{ padding: 22, animationDelay: `${i * 30}ms` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 17, fontWeight: 700, color: "#f1f5f9", marginBottom: 12 }}>{dept.department}</h3>
                <div style={{ display: "flex", gap: 20 }}>
                  {[
                    ["Total", dept.total_maps, "#a78bfa"],
                    ["Compliant", dept.compliant, "#34d399"],
                    ["Partial", dept.partial, "#fbbf24"],
                    ["Non-Compliant", dept.non_compliant, "#f87171"],
                    ["Pending", dept.pending, "#94a3b8"],
                  ].map(([lbl, val, c]) => (
                    <div key={lbl}>
                      <div style={{ fontSize: 22, fontWeight: 900, color: c, lineHeight: 1 }}>{val?.toLocaleString() ?? 0}</div>
                      <div style={{ fontSize: 10, color: "#475569", marginTop: 3 }}>{lbl}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Progress bar */}
              <div style={{ width: 180, flexShrink: 0 }}>
                <div style={{ fontSize: 10.5, color: "#475569", fontWeight: 600, marginBottom: 6 }}>COMPLIANCE PROGRESS</div>
                <div style={{ height: 8, background: "#162030", borderRadius: 4, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${dept.total_maps ? (dept.compliant / dept.total_maps) * 100 : 0}%`, background: "linear-gradient(90deg,#10b981,#34d399)", borderRadius: 4, transition: "width 0.6s ease" }} />
                </div>
                <div style={{ fontSize: 11, color: "#34d399", fontWeight: 700, marginTop: 4 }}>
                  {dept.total_maps ? ((dept.compliant / dept.total_maps) * 100).toFixed(1) : 0}% compliant
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 20, padding: "14px 18px", background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.2)", borderRadius: 10, fontSize: 12, color: "#94a3b8" }}>
        <strong style={{ color: "#a78bfa" }}>Milestone 1 stub.</strong>{" "}
        The Publish/Assign workflow with per-MAP requirement previews will be implemented in Milestone 2.
      </div>
    </div>
  );
}
