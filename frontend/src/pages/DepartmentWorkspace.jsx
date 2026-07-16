/**
 * DepartmentWorkspace.jsx — RegIntel AI V2
 * Fetches real assignments from the FastAPI backend.
 */
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../utils/api";
import { StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

export default function DepartmentWorkspace() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  
  const [assignments, setAssignments] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(30);
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState({ ACTIVE: 0, COMPLETED: 0 });
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [completingId, setCompletingId] = useState(null);
  
  const [evidenceNote, setEvidenceNote] = useState("");
  const [busyId, setBusyId] = useState(null);

  const fetchAssignments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch(`/assignments?page=${page}&page_size=${pageSize}&search=${searchQuery}`);
      setAssignments(data.items || []);
      setTotal(data.total || 0);
      
      const statsData = await apiFetch(`/assignments/stats/summary`);
      const mergedStats = { ACTIVE: 0, COMPLETED: 0, ...statsData };
      setStats(mergedStats);
    } catch (err) {
      console.error("Failed to fetch assignments:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchQuery]);

  useEffect(() => {
    fetchAssignments();
  }, [fetchAssignments]);

  // Handle completion
  const handleComplete = async (assignmentId) => {
    // TASK 2: Prevent duplicate submissions
    if (completingId) {
      return; // Already processing a completion
    }
    
    setCompletingId(assignmentId);
    try {
      await apiFetch(`/assignments/${assignmentId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: 'COMPLETED',
          evidence_note: evidenceNote || undefined
        })
      });
      setEvidenceNote("");
      setExpandedId(null);
      fetchAssignments();
    } catch (err) {
      alert("Error completing assignment: " + err.message);
    } finally {
      setCompletingId(null);
    }
  };

  // Handle reset (dev/test — moves COMPLETED back to ACTIVE)
  const handleReset = async (assignmentId) => {
    setBusyId(assignmentId);
    try {
      await apiFetch(`/assignments/${assignmentId}/reset`, { method: 'POST' });
      fetchAssignments();
    } catch (err) {
      alert("Error resetting assignment: " + err.message);
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#60a5fa,#3b82f6)", boxShadow: "0 0 10px rgba(59,130,246,0.4)" }} />
          <h1 className="page-title">My Assignments</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          {user?.department_name
            ? <><strong style={{ color: "#f1f5f9" }}>{user.department_name}</strong> Department · {total.toLocaleString()} total assignments</>
            : "All Assignments (Admin view)"}
        </p>
      </div>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div className="card animate-fade-up" style={{ padding: "16px 18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Active Tasks</div>
            <StatusBadge status="ACTIVE" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 900, color: "#fbbf24", lineHeight: 1 }}>{stats.ACTIVE || 0}</div>
        </div>
        <div className="card animate-fade-up" style={{ padding: "16px 18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>Completed</div>
            <StatusBadge status="COMPLETED" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 900, color: "#34d399", lineHeight: 1 }}>{stats.COMPLETED || 0}</div>
        </div>
      </div>

      {/* Assignment list */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchAssignments()}
            placeholder="Search assignments (press Enter)"
            style={{ flex: 1, background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, color: "#e2e8f0", padding: "9px 12px", fontSize: 12.5, outline: "none" }}
            onFocus={e => e.target.style.borderColor = "#60a5fa"}
            onBlur={e  => e.target.style.borderColor = "rgba(255,255,255,0.07)"}
          />
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Assignment ID</th>
              <th>Title</th>
              <th>Department</th>
              <th>Status</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ textAlign: "center", padding: "40px" }}>Loading...</td></tr>
            ) : assignments.map((a) => {
              const isExpanded = expandedId === a.id;
              return (
                <>
                  <tr key={a.id} onClick={() => setExpandedId(isExpanded ? null : a.id)} style={{ cursor: "pointer" }}>
                    <td><span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 7px", borderRadius: 5 }}>{a.id.split('-')[0]}</span></td>
                    <td style={{ color: "#d1d5db" }}>{a.title || a.control_name || "Unknown Assignment"}</td>
                    <td style={{ color: "#94a3b8" }}>{a.department_name}</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td style={{ color: "#64748b" }}>{new Date(a.created_at).toLocaleDateString()}</td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={5} style={{ padding: "0 16px 16px" }}>
                        <div style={{ background: "rgba(96,165,250,0.06)", border: "1px solid rgba(96,165,250,0.16)", borderRadius: 10, padding: 16 }}>
                          <div style={{ fontSize: 11, fontWeight: 800, color: "#60a5fa", marginBottom: 12, letterSpacing: "0.08em" }}>ASSIGNMENT DETAIL</div>
                          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            <div style={{ background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
                              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Control Required</div>
                              <div style={{ fontSize: 13, color: "#e2e8f0" }}>{a.control_name}</div>
                            </div>
                            
                            {a.status === 'COMPLETED' && (
                              <div style={{ background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
                                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Verification Agent</div>
                                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                  <button
                                    onClick={() => navigate(`/maps/${a.map_id}`)}
                                    style={{ background: "#3b82f6", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 5, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                                  >
                                    View Verification
                                  </button>
                                  <button
                                    disabled={busyId === a.id}
                                    onClick={() => handleReset(a.id)}
                                    style={{ background: "rgba(251,191,36,0.12)", color: "#fbbf24", border: "1px solid rgba(251,191,36,0.3)", padding: "6px 12px", borderRadius: 5, fontSize: 12, fontWeight: 600, cursor: busyId === a.id ? "wait" : "pointer", opacity: busyId === a.id ? 0.5 : 1 }}
                                  >
                                    {busyId === a.id ? "Resetting…" : "Reset Assignment"}
                                  </button>
                                </div>
                              </div>
                            )}
                            
                            {a.status === 'ACTIVE' && can('assign:complete') && (
                              <div style={{ background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
                                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Evidence & Completion</div>
                                <textarea 
                                  value={evidenceNote}
                                  onChange={e => setEvidenceNote(e.target.value)}
                                  placeholder="Enter evidence notes or reference IDs before completing..."
                                  disabled={completingId === a.id}
                                  style={{ width: "100%", height: 60, background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: "#e2e8f0", padding: "8px", fontSize: 12, marginBottom: 10, resize: "none", opacity: completingId === a.id ? 0.6 : 1 }}
                                />
                                <button 
                                  onClick={() => handleComplete(a.id)}
                                  disabled={completingId === a.id}
                                  style={{ background: completingId === a.id ? "#6b7280" : "#10b981", color: "#fff", border: "none", padding: "6px 12px", borderRadius: 5, fontSize: 12, fontWeight: 600, cursor: completingId === a.id ? "not-allowed" : "pointer", opacity: completingId === a.id ? 0.6 : 1 }}
                                >
                                  {completingId === a.id ? "Processing..." : "Mark as Completed"}
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>

        {!loading && assignments.length === 0 && (
          <div style={{ padding: "52px 40px", textAlign: "center" }}>
            <div style={{ fontSize: 34, marginBottom: 10 }}>📭</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#94a3b8" }}>No assignments found</div>
          </div>
        )}

        <div style={{ padding: "11px 18px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 11.5, color: "#475569", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{total.toLocaleString()} total</span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
