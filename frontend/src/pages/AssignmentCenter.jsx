/**
 * AssignmentCenter.jsx — RegIntel AI V2
 * Admin-only. Review DRAFT MAPs, reassign departments, approve/reject, generate assignments.
 * Uses live FastAPI backend endpoints.
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import Breadcrumbs from "../components/Breadcrumbs";

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function AssignmentCenter() {
  const { can } = useAuth();
  
  const [maps, setMaps] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({});
  const [busyMapId, setBusyMapId] = useState(null);

  const fetchMaps = useCallback(async () => {
    setLoading(true);
    try {
      const [data, statsData, departmentsData] = await Promise.all([
        apiFetch(`/maps?status=DRAFT&page=${page}&page_size=${pageSize}`),
        apiFetch(`/maps/stats/summary`),
        apiFetch(`/departments`),
      ]);
      setMaps(data.items || []);
      setTotal(data.total || 0);
      setStats(statsData || {});
      setDepartments(departmentsData || []);
    } catch (err) {
      console.error("Failed to fetch assignment center data:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchMaps();
  }, [fetchMaps]);

  // Handle Updates
  const handleUpdate = async (mapId, updates) => {
    setBusyMapId(mapId);
    try {
      await apiFetch(`/maps/${mapId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
      });
      await fetchMaps();
    } catch (err) {
      alert("Error updating MAP: " + err.message);
    } finally {
      setBusyMapId(null);
    }
  };

  const handleApprove = async (mapId) => {
    setBusyMapId(mapId);
    try {
      await apiFetch(`/maps/${mapId}/approve`, {
        method: 'POST'
      });
      await fetchMaps();
    } catch (err) {
      alert("Error approving MAP: " + err.message);
    } finally {
      setBusyMapId(null);
    }
  };

  const handleReject = async (mapId) => {
    setBusyMapId(mapId);
    try {
      await apiFetch(`/maps/${mapId}/reject`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      await fetchMaps();
    } catch (err) {
      alert("Error rejecting MAP: " + err.message);
    } finally {
      setBusyMapId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  
  if (!can('map:approve')) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <h2>Access Denied</h2>
        <p>You do not have permission to access the Assignment Center.</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Header */}
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.4)" }} />
          <h1 className="page-title">Assignment Center</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          Review drafted MAPs, assign departments, and approve to create trackable assignments.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 20, alignItems: "start" }}>

        {/* ── Left: summary ─────────────────────────────────── */}
        <div>
          <div className="card" style={{ padding: "16px 18px", marginTop: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 12 }}>
              System MAP Summary
            </div>
            {[
              ["Draft",         stats.DRAFT || 0,        "#fbbf24"],
              ["Approved",      stats.APPROVED || 0,     "#34d399"],
              ["Rejected",      stats.REJECTED || 0,     "#f87171"],
            ].map(([lbl, val, c]) => (
              <div key={lbl} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <span style={{ fontSize: 12, color: "#64748b" }}>{lbl}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: c }}>{val}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Right: MAP review table ────────────────────────────────── */}
        <div>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            
            {/* Table header */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 130px 110px 110px", gap: 10, padding: "8px 14px", background: "#162030", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: 0.5, textTransform: "uppercase" }}>
              <span>MAP Detail</span>
              <span>Department</span>
              <span>Status</span>
              <span>Actions</span>
            </div>

            {/* Rows */}
            <div style={{ maxHeight: 600, overflowY: "auto" }}>
              {loading ? (
                <div style={{ padding: "40px 24px", textAlign: "center", color: "#475569" }}>Loading DRAFT MAPs...</div>
              ) : maps.length === 0 ? (
                <div style={{ padding: "40px 24px", textAlign: "center", color: "#475569", fontSize: 13 }}>No pending MAPs to review.</div>
              ) : (
                maps.map((m) => (
                  <div key={m.id} style={{
                    display: "grid", gridTemplateColumns: "1fr 130px 110px 110px",
                    alignItems: "center", gap: 10, padding: "10px 14px",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                  }}>
                    {/* Title + ID */}
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.control_name || "New Control"}</div>
                      <div style={{ fontSize: 10, color: "#475569", fontFamily: "monospace", marginTop: 2 }}>{m.id.split('-')[0]}</div>
                    </div>

                    {/* Department selector */}
                    <select
                      value={m.department_id || ""}
                      onChange={(e) => handleUpdate(m.id, { department_id: e.target.value })}
                      disabled={busyMapId === m.id || departments.length === 0 || !can('map:write')}
                      style={{ fontSize: 11, background: "#162030", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 6, color: "#a78bfa", padding: "4px 6px" }}
                    >
                      {!m.department_id && <option value="">Select Dept</option>}
                      {departments.map((department) => (
                        <option key={department.id} value={department.id}>
                          {department.name}
                        </option>
                      ))}
                    </select>

                    {/* Status */}
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#fbbf24" }}>
                      {m.status}
                    </div>

                    {/* Actions */}
                    <div style={{ display: "flex", gap: 5 }}>
                      <button disabled={busyMapId === m.id} onClick={() => handleApprove(m.id)} style={{ fontSize: 10, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.25)", borderRadius: 5, padding: "4px 8px", cursor: busyMapId === m.id ? "wait" : "pointer", opacity: busyMapId === m.id ? 0.5 : 1 }}>Approve</button>
                      <button disabled={busyMapId === m.id} onClick={() => handleReject(m.id)}  style={{ fontSize: 10, fontWeight: 700, color: "#f87171", background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)", borderRadius: 5, padding: "4px 8px", cursor: busyMapId === m.id ? "wait" : "pointer", opacity: busyMapId === m.id ? 0.5 : 1 }}>Reject</button>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            {/* Pagination */}
            <div style={{ padding: "11px 18px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 11.5, color: "#475569", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{total.toLocaleString()} pending approvals</span>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
                <span>Page {page} / {totalPages}</span>
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
