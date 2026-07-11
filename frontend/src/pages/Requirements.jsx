/**
 * Requirements.jsx — RegIntel AI V2
 * Requirement Search over compliance_register (59,125 MAPs).
 * requirements_taxonomy is not emitted by the aggregator; compliance_register
 * is the authoritative searchable corpus available in frontend_state.json.
 */
import { useState, useMemo, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useComplianceRegister } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

const PAGE_SIZE = 50;

const PRIORITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const CAP_COLOR = {
  "Cyber Security": "#f87171", "AML": "#fbbf24", "KYC": "#fbbf24",
  "Fraud Risk": "#fb923c", "Treasury": "#a78bfa", "Foreign Exchange": "#a78bfa",
  "Capital Adequacy": "#60a5fa", "Liquidity": "#60a5fa", "Prudential Regulation": "#60a5fa",
  "IT Governance": "#34d399", "Governance": "#34d399", "Audit": "#94a3b8",
  "Reporting": "#94a3b8", "Risk Management": "#fb923c", "Outsourcing": "#94a3b8",
  "Digital Payments": "#22d3ee", "Customer Protection": "#22d3ee", "General": "#475569",
};

const inp = {
  background: "#162030",
  border: "1.5px solid rgba(255,255,255,0.07)",
  borderRadius: 7,
  padding: "9px 12px",
  fontSize: 12.5,
  color: "#e2e8f0",
  outline: "none",
};

/** Highlight all occurrences of `term` inside `text`. Returns array of spans. */
function Highlight({ text, term }) {
  if (!term || !text) return <>{text}</>;
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === term.toLowerCase()
          ? <mark key={i} style={{ background: "rgba(251,191,36,0.25)", color: "#fbbf24", borderRadius: 2, padding: "0 1px" }}>{part}</mark>
          : part
      )}
    </>
  );
}

export default function Requirements() {
  const navigate  = useNavigate();
  const register  = useComplianceRegister();
  const searchRef = useRef(null);

  const [query,      setQuery]      = useState("");
  const [department, setDepartment] = useState("");
  const [priority,   setPriority]   = useState("");
  const [status,     setStatus]     = useState("");
  const [sortKey,    setSortKey]    = useState("priority");
  const [sortDir,    setSortDir]    = useState("asc");
  const [page,       setPage]       = useState(1);

  // ── Derived filter options ────────────────────────────────────────────────
  const departments = useMemo(() => [...new Set(register.map(r => r.department))].sort(), [register]);
  const priorities  = useMemo(() => ["CRITICAL", "HIGH", "MEDIUM", "LOW"].filter(p => register.some(r => r.priority === p)), [register]);
  const statuses    = useMemo(() => [...new Set(register.map(r => r.compliance_status))].sort(), [register]);

  // ── Filtering ─────────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return register.filter(r => {
      if (department && r.department !== department) return false;
      if (priority   && r.priority   !== priority)   return false;
      if (status     && r.compliance_status !== status) return false;
      if (!q) return true;
      return (
        r.map_id?.toLowerCase().includes(q) ||
        r.document_id?.toLowerCase().includes(q) ||
        r.title?.toLowerCase().includes(q) ||
        r.decision_rationale?.toLowerCase().includes(q) ||
        r.business_capability?.some(c => c.toLowerCase().includes(q))
      );
    });
  }, [register, query, department, priority, status]);

  // ── Sorting ───────────────────────────────────────────────────────────────
  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      let va, vb;
      if (sortKey === "priority") {
        va = PRIORITY_ORDER[a.priority] ?? 99;
        vb = PRIORITY_ORDER[b.priority] ?? 99;
      } else if (sortKey === "automation_percentage" || sortKey === "failed_blocker_count") {
        va = a[sortKey] ?? 0;
        vb = b[sortKey] ?? 0;
      } else {
        va = String(a[sortKey] ?? "").toLowerCase();
        vb = String(b[sortKey] ?? "").toLowerCase();
        return sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return sortDir === "asc" ? va - vb : vb - va;
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const paginated  = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleQuery = useCallback(e => { setQuery(e.target.value); setPage(1); }, []);
  const handleSort  = useCallback(key => {
    setSortDir(d => key === sortKey ? (d === "asc" ? "desc" : "asc") : "asc");
    setSortKey(key);
    setPage(1);
  }, [sortKey]);

  const clearAll = useCallback(() => {
    setQuery(""); setDepartment(""); setPriority(""); setStatus("");
    setSortKey("priority"); setSortDir("asc"); setPage(1);
    searchRef.current?.focus();
  }, []);

  const hasFilters = query || department || priority || status;

  const SortBtn = ({ k, label }) => (
    <button
      onClick={() => handleSort(k)}
      style={{ background: "transparent", border: "none", color: sortKey === k ? "#38bdf8" : "#475569", cursor: "pointer", padding: "4px 8px", fontSize: 11.5, fontWeight: 700, borderRadius: 5, transition: "color 0.15s" }}
    >
      {label} {sortKey === k ? (sortDir === "asc" ? "↑" : "↓") : ""}
    </button>
  );

  return (
    <div>
      <Breadcrumbs />

      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
            <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#38bdf8,#0ea5e9)", boxShadow: "0 0 10px rgba(56,189,248,0.4)" }} />
            <h1 className="page-title">Requirement Search</h1>
          </div>
          <p className="page-subtitle" style={{ paddingLeft: 14 }}>
            <strong style={{ color: "#f1f5f9" }}>{register.length.toLocaleString()}</strong> MAPs across{" "}
            <strong style={{ color: "#f1f5f9" }}>{departments.length}</strong> departments
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {[
            ["CRITICAL", register.filter(r => r.priority === "CRITICAL").length, "#f87171", "rgba(239,68,68,0.12)"],
            ["HIGH",     register.filter(r => r.priority === "HIGH").length,     "#fbbf24", "rgba(251,191,36,0.1)"],
          ].map(([lbl, val, c, bg]) => (
            <div key={lbl} style={{ background: bg, border: `1px solid ${c}25`, borderRadius: 9, padding: "9px 16px", textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 900, color: c, lineHeight: 1 }}>{val.toLocaleString()}</div>
              <div style={{ fontSize: 10.5, color: "#64748b", marginTop: 2, fontWeight: 600 }}>{lbl}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Filter bar ───────────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "14px 18px", marginBottom: 14, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        {/* Search input with keyboard focus */}
        <div style={{ position: "relative", flex: 1, minWidth: 240 }}>
          <svg style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", opacity: 0.35, pointerEvents: "none" }}
            width="13" height="13" fill="none" stroke="#94a3b8" strokeWidth="2" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            ref={searchRef}
            autoFocus
            type="text"
            value={query}
            onChange={handleQuery}
            placeholder="Search MAP ID, document, title, rationale, capability…"
            style={{ ...inp, width: "100%", paddingLeft: 30, boxSizing: "border-box" }}
            onFocus={e  => e.target.style.borderColor = "#38bdf8"}
            onBlur={e   => e.target.style.borderColor = "rgba(255,255,255,0.07)"}
            onKeyDown={e => e.key === "Escape" && clearAll()}
          />
          {query && (
            <button onClick={() => { setQuery(""); setPage(1); searchRef.current?.focus(); }}
              style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 2 }}
              title="Clear search">✕</button>
          )}
        </div>

        <select value={department} onChange={e => { setDepartment(e.target.value); setPage(1); }} style={{ ...inp, minWidth: 160 }}>
          <option value="">All Departments</option>
          {departments.map(d => <option key={d} value={d}>{d}</option>)}
        </select>

        <select value={priority} onChange={e => { setPriority(e.target.value); setPage(1); }} style={{ ...inp, minWidth: 140 }}>
          <option value="">All Priorities</option>
          {priorities.map(p => <option key={p} value={p}>{p}</option>)}
        </select>

        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }} style={{ ...inp, minWidth: 170 }}>
          <option value="">All Statuses</option>
          {statuses.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        {hasFilters && (
          <button onClick={clearAll}
            style={{ ...inp, padding: "9px 14px", cursor: "pointer", color: "#f87171", borderColor: "rgba(248,113,113,0.25)", whiteSpace: "nowrap", fontWeight: 600 }}>
            Clear ✕
          </button>
        )}
      </div>

      {/* ── Sort bar + result count ───────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <div style={{ fontSize: 12, color: "#475569" }}>
          <strong style={{ color: "#94a3b8" }}>{sorted.length.toLocaleString()}</strong> result{sorted.length !== 1 ? "s" : ""}
          {hasFilters && <span style={{ color: "#38bdf8", marginLeft: 6 }}>filtered</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 11, color: "#475569", fontWeight: 600, marginRight: 4 }}>SORT:</span>
          <SortBtn k="priority"             label="Priority" />
          <SortBtn k="title"                label="Title" />
          <SortBtn k="department"           label="Dept" />
          <SortBtn k="automation_percentage" label="Automation" />
          <SortBtn k="failed_blocker_count"  label="Blockers" />
        </div>
      </div>

      {/* ── Empty state ───────────────────────────────────────────────────── */}
      {sorted.length === 0 && (
        <div style={{ textAlign: "center", padding: "60px 40px" }}>
          <div style={{ fontSize: 40, marginBottom: 14 }}>🔍</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>No results found</div>
          <div style={{ fontSize: 13, color: "#475569", marginBottom: 20 }}>
            No MAPs match <strong style={{ color: "#94a3b8" }}>"{query}"</strong>
            {department && <> in <strong style={{ color: "#a78bfa" }}>{department}</strong></>}
            {priority   && <> with priority <strong style={{ color: "#fbbf24" }}>{priority}</strong></>}
          </div>
          <button onClick={clearAll}
            style={{ padding: "9px 22px", background: "#38bdf8", color: "#0f172a", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer", fontSize: 13 }}>
            Clear filters
          </button>
        </div>
      )}

      {/* ── Results ───────────────────────────────────────────────────────── */}
      {paginated.map((r, i) => (
        <div
          key={r.map_id}
          className="card animate-fade-up"
          onClick={() => navigate(`/registry/${encodeURIComponent(r.map_id)}`)}
          style={{ padding: "15px 18px", marginBottom: 8, borderLeft: "3px solid #38bdf8", cursor: "pointer", animationDelay: `${Math.min(i, 20) * 18}ms`, transition: "border-color 0.15s" }}
          onMouseEnter={e => e.currentTarget.style.borderColor = "#0ea5e9"}
          onMouseLeave={e => e.currentTarget.style.borderColor = "#38bdf8"}
        >
          {/* Row 1: badges */}
          <div style={{ display: "flex", gap: 7, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontFamily: "monospace", fontSize: 10.5, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "2px 8px", borderRadius: 5, border: "1px solid rgba(52,211,153,0.2)" }}>
              <Highlight text={r.map_id} term={query} />
            </span>
            <span style={{ fontFamily: "monospace", fontSize: 10, fontWeight: 600, color: "#60a5fa", background: "rgba(96,165,250,0.1)", padding: "2px 6px", borderRadius: 4 }}>
              <Highlight text={r.document_id} term={query} />
            </span>
            <PriorityBadge priority={r.priority.charAt(0) + r.priority.slice(1).toLowerCase()} />
            <StatusBadge status={r.compliance_status} />
            <span style={{ fontSize: 11, color: "#64748b", background: "#162030", padding: "2px 8px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.05)" }}>
              {r.department}
            </span>
            {r.failed_blocker_count > 0 && (
              <span style={{ fontSize: 10.5, color: "#f87171", background: "rgba(248,113,113,0.1)", padding: "2px 8px", borderRadius: 5, border: "1px solid rgba(248,113,113,0.2)", fontWeight: 700 }}>
                {r.failed_blocker_count} blocker{r.failed_blocker_count !== 1 ? "s" : ""}
              </span>
            )}
            <span style={{ marginLeft: "auto", fontSize: 11, color: "#475569", fontFamily: "monospace" }}>
              {r.automation_percentage != null ? `${r.automation_percentage.toFixed(1)}% auto` : ""}
            </span>
          </div>

          {/* Row 2: title */}
          <div style={{ fontSize: 13.5, color: "#cbd5e1", lineHeight: 1.55, marginBottom: r.business_capability?.length ? 8 : 0 }}>
            <Highlight text={r.title} term={query} />
          </div>

          {/* Row 3: capabilities */}
          {r.business_capability?.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
              {r.business_capability.map(cap => {
                const c = CAP_COLOR[cap] ?? "#94a3b8";
                return (
                  <span key={cap} style={{ fontSize: 10.5, color: c, background: `${c}12`, border: `1px solid ${c}25`, padding: "2px 8px", borderRadius: 20, fontWeight: 600 }}>
                    <Highlight text={cap} term={query} />
                  </span>
                );
              })}
            </div>
          )}
        </div>
      ))}

      {/* ── Pagination ────────────────────────────────────────────────────── */}
      {sorted.length > PAGE_SIZE && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 18px", background: "#162030", borderRadius: 8, border: "1px solid rgba(255,255,255,0.04)", marginTop: 14, fontSize: 11.5, color: "#475569" }}>
          <span>
            Showing {((page - 1) * PAGE_SIZE + 1).toLocaleString()}–{Math.min(page * PAGE_SIZE, sorted.length).toLocaleString()} of {sorted.length.toLocaleString()}
          </span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              style={{ ...inp, padding: "5px 10px", cursor: page === 1 ? "not-allowed" : "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              style={{ ...inp, padding: "5px 10px", cursor: page >= totalPages ? "not-allowed" : "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
