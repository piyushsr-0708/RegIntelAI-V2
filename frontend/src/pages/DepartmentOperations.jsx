/**
 * DepartmentOperations.jsx — RegIntel AI V2
 * Department Workspace
 * Answers: "What regulations currently affect this department?"
 */
import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDepartmentSummary, useComplianceRegister } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";
import { PriorityBadge, StatusBadge } from "../components/Badges";

// Copied from SessionSummary.jsx per dependency audit strategy
function StatBox({ label, value, color = "#f1f5f9", mono = false }) {
  return (
    <div style={{ padding: "14px 16px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10 }}>
      <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 900, color, lineHeight: 1, fontFamily: mono ? "monospace" : "inherit" }}>{value ?? "—"}</div>
    </div>
  );
}

export default function DepartmentOperations() {
  const navigate = useNavigate();
  const deptSummary = useDepartmentSummary();
  const allMaps = useComplianceRegister();
  
  // 1. Department Selector logic
  const departments = useMemo(() => deptSummary.map(d => d.department).sort(), [deptSummary]);
  const [selectedDept, setSelectedDept] = useState("");
  
  useEffect(() => {
    if (departments.length > 0 && !selectedDept) {
      setSelectedDept(departments[0]);
    }
  }, [departments, selectedDept]);
  
  // Filter Maps for selected department
  const deptMaps = useMemo(() => {
    if (!selectedDept) return [];
    return allMaps.filter(m => m.department === selectedDept || m.owner_department === selectedDept);
  }, [allMaps, selectedDept]);
  
  // 2. Department Overview (KPIs)
  const totalMaps = deptMaps.length;
  const criticalHigh = deptMaps.filter(m => m.priority === "CRITICAL" || m.priority === "HIGH").length;
  const autoPercent = totalMaps > 0 ? Math.round(deptMaps.reduce((s, m) => s + Number(m.automation_percentage ?? m.automation_percent ?? 0), 0) / totalMaps) : 0;
  
  // 3 & 4. Regulatory Impact / Affected Documents
  const affectedDocs = useMemo(() => {
    const docs = new Set();
    deptMaps.forEach(m => {
      if (m.source_document_id) docs.add(m.source_document_id);
      else if (m.document_id) docs.add(m.document_id);
    });
    return Array.from(docs);
  }, [deptMaps]);

  // 5. Department MAP Explorer State
  const [search, setSearch] = useState("");
  const PAGE_SIZE = 15;
  const [page, setPage] = useState(1);
  
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return deptMaps;
    return deptMaps.filter(m => String(m.map_id || "").toLowerCase().includes(q) || (m.title || "").toLowerCase().includes(q));
  }, [deptMaps, search]);
  
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const inp = { background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "8px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none" };

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />
      
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
            <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.5)" }} />
            <h1 className="page-title">Department Workspace</h1>
          </div>
          <p className="page-subtitle" style={{ paddingLeft: 14 }}>
            Operational view for regulatory obligations affecting {selectedDept || "the department"}.
          </p>
        </div>
        
        {/* Department Selector */}
        {departments.length > 0 && (
          <select 
            value={selectedDept} 
            onChange={(e) => { setSelectedDept(e.target.value); setPage(1); setSearch(""); }}
            style={{ ...inp, minWidth: 220, fontSize: 14, fontWeight: 700 }}
          >
            <option value="" disabled>Select Department...</option>
            {departments.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        )}
      </div>

      {selectedDept ? (
        <>
          {/* Department Overview (KPIs) */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 24 }}>
            <StatBox label="Total Obligations (MAPs)" value={totalMaps.toLocaleString()} color="#38bdf8" />
            <StatBox label="High & Critical Priority" value={criticalHigh.toLocaleString()} color="#f87171" />
            <StatBox label="Affected Documents" value={affectedDocs.length.toLocaleString()} color="#a78bfa" />
            <StatBox label="Automation Profile" value={`${autoPercent}%`} color="#34d399" />
          </div>

          <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>
            
            {/* Regulatory Impact & Affected Documents */}
            <div className="card" style={{ padding: 20, flex: "1 1 300px", maxWidth: 450 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#475569", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 16 }}>
                Regulatory Impact
              </div>
              <p style={{ fontSize: 12.5, color: "#94a3b8", lineHeight: 1.5, marginBottom: 16 }}>
                The following {affectedDocs.length} source documents have generated MAPs currently assigned to {selectedDept}.
              </p>
              
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {affectedDocs.length > 0 ? affectedDocs.map(docId => (
                  <div key={docId} style={{ padding: "10px 14px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8, display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: "rgba(96,165,250,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="#60a5fa" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    </div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0", fontFamily: "monospace" }}>{docId}</span>
                  </div>
                )) : (
                  <div style={{ fontSize: 12, color: "#64748b", fontStyle: "italic" }}>No impacted documents found.</div>
                )}
              </div>
            </div>

            {/* Department MAP Explorer (Table Layout Copied from SessionMapTable) */}
            <div className="card" style={{ flex: "2 1 500px", overflow: "hidden" }}>
              <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#475569", letterSpacing: 0.5, textTransform: "uppercase" }}>
                  Department MAP Explorer
                </div>
                <input
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  placeholder="Search MAP ID, title…"
                  style={{ ...inp, minWidth: 220 }}
                  onFocus={(e) => e.target.style.borderColor = "#38bdf8"}
                  onBlur={(e)  => e.target.style.borderColor = "rgba(255,255,255,0.07)"}
                />
              </div>

              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: 100 }}>MAP ID</th>
                      <th>Title</th>
                      <th style={{ width: 100 }}>Priority</th>
                      <th style={{ width: 110 }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.length > 0 ? paginated.map((m) => {
                      // Navigate to global MAP registry
                      const dest = `/maps/${encodeURIComponent(m.map_id)}`;
                      return (
                        <tr key={m.map_id} style={{ cursor: "pointer" }} onClick={() => navigate(dest)}>
                          <td>
                            <span style={{ fontFamily: "monospace", fontSize: 10.5, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "2px 7px", borderRadius: 5 }}>
                              {m.map_id}
                            </span>
                          </td>
                          <td style={{ color: "#d1d5db", lineHeight: 1.4 }}>
                            {(m.title || m.map_id).length > 80 ? (m.title || m.map_id).slice(0, 80) + "…" : (m.title || m.map_id)}
                          </td>
                          <td><PriorityBadge priority={String(m.priority || "Medium").charAt(0) + String(m.priority || "Medium").slice(1).toLowerCase()} /></td>
                          <td><StatusBadge status={m.compliance_status || m.status} /></td>
                        </tr>
                      );
                    }) : (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center", padding: 30, color: "#64748b", fontSize: 13 }}>
                          No MAPs found matching your criteria.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div style={{ padding: "10px 16px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11.5, color: "#475569" }}>
                <span>{filtered.length.toLocaleString()} records</span>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                    style={{ ...inp, padding: "4px 10px", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
                  <span>Page {page} / {totalPages}</span>
                  <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                    style={{ ...inp, padding: "4px 10px", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div style={{ padding: 40, textAlign: "center", color: "#64748b", fontSize: 14 }}>
          {deptSummary.length === 0 ? "Loading department data..." : "No departments available."}
        </div>
      )}
    </div>
  );
}
