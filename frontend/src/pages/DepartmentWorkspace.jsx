/**
 * DepartmentWorkspace.jsx — RegIntel AI V2
 * Milestone 1 stub: filters compliance_register to current user's department.
 * Full implementation in Milestone 3.
 */
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useComplianceRegister, useMapDetail } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

const ITEMS_PER_PAGE = 30;

export default function DepartmentWorkspace() {
  const { user, isAdmin } = useAuth();
  const register = useComplianceRegister();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortConfig, setSortConfig] = useState({ key: "title", direction: "asc" });
  const [expandedMapId, setExpandedMapId] = useState(null);

  const activeDepartment = useMemo(() => {
    if (isAdmin || user?.role === "head_office") return null;
    return user?.department ?? null;
  }, [isAdmin, user]);

  const visibleMaps = useMemo(() => {
    if (!activeDepartment) return register;
    return register.filter((map) => map.department === activeDepartment);
  }, [register, activeDepartment]);

  const filteredMaps = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return visibleMaps;

    return visibleMaps.filter((map) => {
      const haystack = [map.map_id, map.title, map.department, map.compliance_status, map.priority, map.decision_rationale]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [visibleMaps, searchQuery]);

  const sortedMaps = useMemo(() => {
    const items = [...filteredMaps];
    const direction = sortConfig.direction === "asc" ? 1 : -1;

    items.sort((a, b) => {
      const valueA = a[sortConfig.key];
      const valueB = b[sortConfig.key];

      if (sortConfig.key === "priority") {
        const priorityOrder = { Critical: 4, High: 3, Medium: 2, Low: 1 };
        return ((priorityOrder[valueA] || 0) - (priorityOrder[valueB] || 0)) * direction;
      }

      if (sortConfig.key === "automation_percentage") {
        return ((Number(valueA) || 0) - (Number(valueB) || 0)) * direction;
      }

      if (sortConfig.key === "compliance_status") {
        const statusOrder = { COMPLIANT: 3, NON_COMPLIANT: 2, PENDING: 1 };
        return ((statusOrder[valueA] || 0) - (statusOrder[valueB] || 0)) * direction;
      }

      if (typeof valueA === "string" && typeof valueB === "string") {
        return valueA.localeCompare(valueB) * direction;
      }

      return ((valueA || 0) - (valueB || 0)) * direction;
    });

    return items;
  }, [filteredMaps, sortConfig]);

  useEffect(() => {
    setPage(1);
  }, [searchQuery, sortConfig]);

  const paginated = sortedMaps.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);
  const totalPages = Math.ceil(sortedMaps.length / ITEMS_PER_PAGE) || 1;

  const stats = useMemo(() => {
    const compliant = visibleMaps.filter((map) => map.compliance_status === "COMPLIANT").length;
    const nonCompliant = visibleMaps.filter((map) => map.compliance_status === "NON_COMPLIANT").length;
    const pending = visibleMaps.filter((map) => map.compliance_status === "PENDING").length;
    const openTasks = nonCompliant + pending;
    const automation = visibleMaps.length
      ? visibleMaps.reduce((sum, map) => sum + (Number(map.automation_percentage) || 0), 0) / visibleMaps.length
      : 0;

    return {
      total: visibleMaps.length,
      compliant,
      nonCompliant,
      pending,
      openTasks,
      automation,
    };
  }, [visibleMaps]);

  const summaryCards = [
    { label: "Open Tasks", value: stats.openTasks.toLocaleString(), color: "#fbbf24", badge: <StatusBadge status="PENDING" /> },
    { label: "Compliant", value: stats.compliant.toLocaleString(), color: "#34d399", badge: <StatusBadge status="COMPLIANT" /> },
    { label: "Non-Compliant", value: stats.nonCompliant.toLocaleString(), color: "#f87171", badge: <StatusBadge status="NON_COMPLIANT" /> },
    { label: "Pending", value: stats.pending.toLocaleString(), color: "#94a3b8", badge: <StatusBadge status="PENDING" /> },
    { label: "Automation %", value: `${stats.automation.toFixed(1)}%`, color: "#60a5fa", badge: <PriorityBadge priority="Medium" /> },
  ];

  const detail = useMapDetail(expandedMapId);
  const expandedItem = useMemo(() => visibleMaps.find((map) => map.map_id === expandedMapId) ?? null, [visibleMaps, expandedMapId]);

  const toggleExpanded = (mapId) => {
    setExpandedMapId((current) => (current === mapId ? null : mapId));
  };

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#60a5fa,#3b82f6)", boxShadow: "0 0 10px rgba(59,130,246,0.4)" }} />
          <h1 className="page-title">My Assignments</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          {activeDepartment
            ? <><strong style={{ color: "#f1f5f9" }}>{activeDepartment}</strong> Department · {visibleMaps.length.toLocaleString()} MAPs assigned</>
            : "All MAPs (Admin view)"}
        </p>
      </div>

      {/* Department summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 12, marginBottom: 20 }}>
        {summaryCards.map((item) => (
          <div key={item.label} className="card animate-fade-up" style={{ padding: "16px 18px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <div style={{ fontSize: 11, color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>{item.label}</div>
              {item.badge}
            </div>
            <div style={{ fontSize: 28, fontWeight: 900, color: item.color, lineHeight: 1 }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* MAP list */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <input
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Search assignments"
            style={{ flex: 1, background: "#0f172a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", padding: "8px 10px", fontSize: 13 }}
          />
        </div>

        <table className="data-table">
          <thead>
            <tr>
              {[
                { key: "map_id", label: "MAP ID" },
                { key: "title", label: "Title" },
                { key: "priority", label: "Priority" },
                { key: "compliance_status", label: "Status" },
                { key: "automation_percentage", label: "Automation %" },
                { key: "decision_rationale", label: "Decision" },
              ].map((header) => (
                <th key={header.key}>
                  <button
                    onClick={() => setSortConfig((current) => ({
                      key: header.key,
                      direction: current.key === header.key && current.direction === "asc" ? "desc" : "asc",
                    }))}
                    style={{ background: "transparent", border: 0, color: "inherit", padding: 0, cursor: "pointer", font: "inherit" }}
                  >
                    {header.label}
                    {sortConfig.key === header.key ? (sortConfig.direction === "asc" ? " ↑" : " ↓") : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((m) => {
              const isExpanded = expandedMapId === m.map_id;
              return (
                <>
                  <tr key={m.map_id} onClick={() => toggleExpanded(m.map_id)} style={{ cursor: "pointer" }}>
                    <td><span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 7px", borderRadius: 5 }}>{m.map_id}</span></td>
                    <td style={{ maxWidth: 340, color: "#d1d5db", lineHeight: 1.4 }}>{m.title.length > 90 ? m.title.substring(0, 90) + "…" : m.title}</td>
                    <td><PriorityBadge priority={m.priority.charAt(0) + m.priority.slice(1).toLowerCase()} /></td>
                    <td><StatusBadge status={m.compliance_status} /></td>
                    <td style={{ fontFamily: "monospace", color: "#64748b" }}>{(Number(m.automation_percentage) || 0).toFixed(1)}%</td>
                    <td style={{ maxWidth: 220, color: "#94a3b8", lineHeight: 1.4 }}>
                      {m.decision_rationale ? (m.decision_rationale.length > 70 ? `${m.decision_rationale.substring(0, 70)}…` : m.decision_rationale) : "Pending review"}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${m.map_id}-details`}>
                      <td colSpan={6} style={{ padding: "0 16px 16px" }}>
                        <div style={{ background: "rgba(96,165,250,0.06)", border: "1px solid rgba(96,165,250,0.16)", borderRadius: 10, padding: 16 }}>
                          <div style={{ fontSize: 11, fontWeight: 800, color: "#60a5fa", marginBottom: 12, letterSpacing: "0.08em" }}>TASK DETAIL</div>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
                            {[
                              ["Requirement", detail?.requirement?.text || detail?.requirement_text || detail?.requirement || expandedItem?.title || "Requirement details will appear when detailed map metadata is available."],
                              ["Reasoning summary", detail?.reasoning_summary || detail?.reasoning || detail?.summary || expandedItem?.decision_rationale || "Reasoning summary will appear when detailed map metadata is available."],
                              ["Department", expandedItem?.department || "Department not available"],
                              ["Compliance decision", expandedItem?.compliance_status || "Decision not available"],
                            ].map(([label, value]) => (
                              <div key={label} style={{ background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
                                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>{label}</div>
                                <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{value}</div>
                              </div>
                            ))}
                            <div style={{ gridColumn: "1 / -1", background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: 12 }}>
                              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em", textTransform: "uppercase" }}>Evidence summary</div>
                              <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                                {detail?.evidence_summary || detail?.evidence || detail?.evidence_text || "Evidence summary will appear when detailed map metadata is available."}
                              </div>
                            </div>
                          </div>
                          {!detail && (
                            <div style={{ marginTop: 12, padding: "10px 12px", background: "rgba(16,185,129,0.07)", border: "1px solid rgba(16,185,129,0.16)", borderRadius: 8, color: "#94a3b8", fontSize: 12 }}>
                              <strong style={{ color: "#34d399" }}>Detailed map data is not available.</strong> A professional placeholder is shown until the aggregator provides richer task detail.
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>

        {sortedMaps.length === 0 && (
          <div style={{ padding: "52px 40px", textAlign: "center" }}>
            <div style={{ fontSize: 34, marginBottom: 10 }}>📭</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#94a3b8" }}>No assignments found for your department</div>
          </div>
        )}

        {/* Pagination */}
        <div style={{ padding: "11px 18px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.04)", fontSize: 11.5, color: "#475569", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{sortedMaps.length.toLocaleString()} assignments</span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#e2e8f0", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      </div>

    </div>
  );
}
