/**
 * DepartmentWorkspace.jsx — RegIntel AI V2
 * Milestone 1 stub: filters compliance_register to current user's department.
 * Full implementation in Milestone 3.
 */
import { useState, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { useComplianceRegister, useFrontendState } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

const ITEMS_PER_PAGE = 30;

export default function DepartmentWorkspace() {
  const { user } = useAuth();
  const register = useComplianceRegister();
  const { state } = useFrontendState();
  const [page, setPage] = useState(1);

  // Filter MAPs for the logged-in user's department
  const myMaps = useMemo(() => {
    if (!user?.department) return register;
    return register.filter(m => m.department === user.department);
  }, [register, user]);

  const paginated = myMaps.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);
  const totalPages = Math.ceil(myMaps.length / ITEMS_PER_PAGE) || 1;

  // Stats
  const stats = useMemo(() => ({
    total:        myMaps.length,
    compliant:    myMaps.filter(m => m.compliance_status === "COMPLIANT").length,
    nonCompliant: myMaps.filter(m => m.compliance_status === "NON_COMPLIANT").length,
    pending:      myMaps.filter(m => m.compliance_status === "PENDING").length,
  }), [myMaps]);

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#60a5fa,#3b82f6)", boxShadow: "0 0 10px rgba(59,130,246,0.4)" }} />
          <h1 className="page-title">My Assignments</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          {user?.department
            ? <><strong style={{ color: "#f1f5f9" }}>{user.department}</strong> Department · {myMaps.length.toLocaleString()} MAPs assigned</>
            : "All MAPs (Admin view)"}
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
        {[
          ["Total MAPs", stats.total, "#a78bfa"],
          ["Compliant", stats.compliant, "#34d399"],
          ["Non-Compliant", stats.nonCompliant, "#f87171"],
          ["Pending", stats.pending, "#94a3b8"],
        ].map(([lbl, val, c]) => (
          <div key={lbl} className="card animate-fade-up" style={{ padding: "16px 18px", textAlign: "center" }}>
            <div style={{ fontSize: 28, fontWeight: 900, color: c, lineHeight: 1 }}>{val.toLocaleString()}</div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 5, fontWeight: 600 }}>{lbl}</div>
          </div>
        ))}
      </div>

      {/* MAP list */}
      <div className="card" style={{ overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              {["MAP ID", "Title", "Priority", "Status", "Automation %"].map(h => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map(m => (
              <tr key={m.map_id} style={{ cursor: "default" }}>
                <td><span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 7px", borderRadius: 5 }}>{m.map_id}</span></td>
                <td style={{ maxWidth: 340, color: "#d1d5db", lineHeight: 1.4 }}>{m.title.length > 90 ? m.title.substring(0, 90) + "…" : m.title}</td>
                <td><PriorityBadge priority={m.priority.charAt(0) + m.priority.slice(1).toLowerCase()} /></td>
                <td><StatusBadge status={m.compliance_status} /></td>
                <td style={{ fontFamily: "monospace", color: "#64748b" }}>{m.automation_percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>

        {myMaps.length === 0 && (
          <div style={{ padding: "52px 40px", textAlign: "center" }}>
            <div style={{ fontSize: 34, marginBottom: 10 }}>📭</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#94a3b8" }}>No assignments found for your department</div>
          </div>
        )}

        {/* Pagination */}
        <div style={{ padding: "11px 18px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 11.5, color: "#475569", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{myMaps.length.toLocaleString()} assignments</span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 20, padding: "14px 18px", background: "rgba(96,165,250,0.07)", border: "1px solid rgba(96,165,250,0.2)", borderRadius: 10, fontSize: 12, color: "#94a3b8" }}>
        <strong style={{ color: "#60a5fa" }}>Milestone 1 stub.</strong>{" "}
        Status updates, task details, and reporting will be implemented in Milestone 3.
      </div>
    </div>
  );
}
