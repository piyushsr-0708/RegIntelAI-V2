/**
 * SessionMapTable.jsx — RegIntel AI V2
 * Paginated table of MAPs belonging to this session only.
 */
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { PriorityBadge, StatusBadge } from "../Badges";

const PAGE_SIZE = 20;

export default function SessionMapTable({ maps, sessionId }) {
  const navigate = useNavigate();
  const params   = useParams();
  const sid      = sessionId ?? params.id;
  const [page, setPage]     = useState(1);
  const [search, setSearch] = useState("");

  const filtered = maps.filter((m) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    const dept = (m.department || m.owner_department || "").toLowerCase();
    return String(m.map_id || "").toLowerCase().includes(q) || (m.title || "").toLowerCase().includes(q) || dept.includes(q);
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated  = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const inp = { background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "8px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none" };

  return (
    <div className="card" style={{ overflow: "hidden", marginBottom: 20 }}>
      {/* Toolbar */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#475569", letterSpacing: 0.5, textTransform: "uppercase" }}>
          MAP Summary — {maps.length.toLocaleString()} MAPs
        </div>
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search MAP ID, title, department…"
          style={{ ...inp, minWidth: 240 }}
          onFocus={(e) => e.target.style.borderColor = "#38bdf8"}
          onBlur={(e)  => e.target.style.borderColor = "rgba(255,255,255,0.07)"}
        />
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              {["MAP ID", "Title", "Department", "Priority", "Automation %", "Status", ""].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((m) => {
              const dest = `/session/${encodeURIComponent(sid)}/map/${encodeURIComponent(m.map_id)}`;
              return (
                <tr key={m.map_id} style={{ cursor: "pointer" }} onClick={() => navigate(dest)}>
                  <td>
                    <span style={{ fontFamily: "monospace", fontSize: 10.5, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "2px 7px", borderRadius: 5 }}>
                      {m.map_id}
                    </span>
                  </td>
                  <td style={{ maxWidth: 260, color: "#d1d5db", lineHeight: 1.4 }}>
                    {(m.title || m.map_id).length > 70 ? (m.title || m.map_id).slice(0, 70) + "…" : (m.title || m.map_id)}
                  </td>
                  <td>
                    <span style={{ fontSize: 11, color: "#94a3b8", background: "#162030", padding: "2px 8px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.06)" }}>
                      {m.department || m.owner_department || "—"}
                    </span>
                  </td>
                  <td><PriorityBadge priority={String(m.priority || "Medium").charAt(0) + String(m.priority || "Medium").slice(1).toLowerCase()} /></td>
                  <td style={{ fontFamily: "monospace", color: "#64748b", fontSize: 12 }}>
                    {(m.automation_percentage ?? m.automation_percent ?? 0).toFixed(1)}%
                  </td>
                  <td><StatusBadge status={m.compliance_status || m.status} /></td>
                  <td>
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(dest); }}
                      style={{ background: "rgba(56,189,248,0.1)", border: "1px solid rgba(56,189,248,0.2)", borderRadius: 6, padding: "3px 10px", fontSize: 11, color: "#38bdf8", cursor: "pointer", fontWeight: 600 }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
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
  );
}
