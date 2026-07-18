/**
 * Maps.jsx — RegIntel AI V2
 * Compliance Register table bound directly to FrontendStateContext register data.
 */
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useComplianceRegister } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

export default function Maps() {
  const navigate = useNavigate();
  const register = useComplianceRegister() ?? [];
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("");
  const [complianceStatus, setComplianceStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: "asc" });

  const departments = useMemo(() => [...new Set(register.map((item) => item.department))].sort(), [register]);
  const complianceStatuses = useMemo(() => [...new Set(register.map((item) => item.compliance_status))].sort(), [register]);
  const priorities = useMemo(() => [...new Set(register.map((item) => item.priority))].sort(), [register]);

  const filteredRegister = useMemo(() => {
    const query = search.trim().toLowerCase();

    return register.filter((item) => {
      const matchesSearch = !query || [item.map_id, item.document_id, item.department, item.title].some((field) => String(field ?? "").toLowerCase().includes(query));
      const matchesDepartment = !department || item.department === department;
      const matchesStatus = !complianceStatus || item.compliance_status === complianceStatus;
      const matchesPriority = !priority || item.priority === priority;

      return matchesSearch && matchesDepartment && matchesStatus && matchesPriority;
    });
  }, [register, search, department, complianceStatus, priority]);

  const sortedRegister = useMemo(() => {
    const items = [...filteredRegister];
    if (!sortConfig.key) return items;

    items.sort((a, b) => {
      const valueA = a[sortConfig.key];
      const valueB = b[sortConfig.key];

      if (sortConfig.key === "automation_percentage") {
        const diff = Number(valueA) - Number(valueB);
        return sortConfig.direction === "asc" ? diff : -diff;
      }

      const textA = String(valueA ?? "").toLowerCase();
      const textB = String(valueB ?? "").toLowerCase();
      const diff = textA.localeCompare(textB);
      return sortConfig.direction === "asc" ? diff : -diff;
    });

    return items;
  }, [filteredRegister, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedRegister.length / 50));
  const paginatedRegister = sortedRegister.slice((page - 1) * 50, page * 50);

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
            <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#a78bfa,#7c3aed)", boxShadow: "0 0 10px rgba(139,92,246,0.4)" }} />
            <h1 className="page-title">Compliance Register</h1>
          </div>
          <p className="page-subtitle" style={{ paddingLeft: 14 }}>
            Showing <strong style={{ color: "#f1f5f9" }}>{register.length.toLocaleString()}</strong> of {register.length.toLocaleString()} Measurable Action Points
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {[["CRITICAL", register.filter(m => m.priority === "CRITICAL").length, "#f87171", "rgba(239,68,68,0.12)"],
            ["PENDING", register.filter(m => m.compliance_status === "PENDING").length, "#fbbf24", "rgba(251,191,36,0.1)"]
          ].map(([lbl, val, c, bg]) => (
            <div key={lbl} style={{ background: bg, border: `1px solid ${c}25`, borderRadius: 9, padding: "9px 16px", textAlign: "center" }}>
              <div style={{ fontSize: 22, fontWeight: 900, color: c, lineHeight: 1 }}>{val.toLocaleString()}</div>
              <div style={{ fontSize: 10.5, color: "#64748b", marginTop: 2, fontWeight: 600 }}>{lbl}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ padding: "14px 18px", marginBottom: 16, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search MAP ID, Document ID, Department, Title"
          style={{ flex: 1, minWidth: 220, background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none", transition: "border-color 0.15s" }}
          onFocus={e => e.target.style.borderColor = "#a78bfa"}
          onBlur={e  => e.target.style.borderColor = "rgba(255,255,255,0.07)"}
        />
        <select value={department} onChange={(e) => { setDepartment(e.target.value); setPage(1); }} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none", minWidth: 160 }}>
          <option value="">All Departments</option>
          {departments.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select value={complianceStatus} onChange={(e) => { setComplianceStatus(e.target.value); setPage(1); }} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none", minWidth: 170 }}>
          <option value="">All Compliance Statuses</option>
          {complianceStatuses.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <select value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none", minWidth: 140 }}>
          <option value="">All Priorities</option>
          {priorities.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </div>

      <div className="card" style={{ overflow: "hidden", overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              {[
                { label: "MAP ID", key: null },
                { label: "Document", key: null },
                { label: "Title", key: null },
                { label: "Department", key: "department" },
                { label: "Priority", key: "priority" },
                { label: "Status", key: "compliance_status" },
                { label: "Automation", key: "automation_percentage" }
              ].map((column) => (
                <th key={column.label}>
                  {column.key ? (
                    <button
                      onClick={() => {
                        setPage(1);
                        setSortConfig((current) => ({
                          key: column.key,
                          direction: current.key === column.key && current.direction === "asc" ? "desc" : "asc"
                        }));
                      }}
                      style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer", padding: 0, font: "inherit" }}
                    >
                      {column.label} {sortConfig.key === column.key ? (sortConfig.direction === "asc" ? "↑" : "↓") : ""}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedRegister.map(m => (
              <tr key={m.map_id} onClick={() => navigate(`/registry/${encodeURIComponent(m.map_id)}`)} style={{ cursor: "pointer" }}>
                <td><span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 7px", borderRadius: 5 }}>{m.map_id}</span></td>
                <td><span style={{ fontFamily: "monospace", fontSize: 10, fontWeight: 600, color: "#60a5fa", background: "rgba(96,165,250,0.1)", padding: "2px 6px", borderRadius: 4 }}>{m.document_id}</span></td>
                <td style={{ maxWidth: 280, color: "#d1d5db", lineHeight: 1.4 }}>{m.title.length > 80 ? m.title.substring(0, 80) + "…" : m.title}</td>
                <td><span style={{ fontSize: 11.5, color: "#94a3b8", background: "#162030", padding: "3px 9px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.06)" }}>{m.department}</span></td>
                <td><PriorityBadge priority={String(m.priority || "Medium").charAt(0) + String(m.priority || "Medium").slice(1).toLowerCase()} /></td>
                <td><StatusBadge status={m.compliance_status} /></td>
                <td style={{ color: "#64748b", fontSize: 12, fontFamily: "monospace" }}>{m.automation_percentage.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ padding: "11px 18px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 11.5, color: "#475569", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{filteredRegister.length.toLocaleString()} records</span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
