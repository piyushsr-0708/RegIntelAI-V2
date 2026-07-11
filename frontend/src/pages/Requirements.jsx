/**
 * Requirements.jsx — RegIntel AI V2
 * Milestone 1 stub: shows requirements_taxonomy if available in FrontendStateContext.
 * Full implementation in Milestone 4 (requires Aggregator to output requirements_taxonomy).
 */
import { useState, useMemo } from "react";
import { useRequirementsTaxonomy } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";

const ITEMS_PER_PAGE = 50;

export default function Requirements() {
  const taxonomy = useRequirementsTaxonomy();
  const [query, setQuery]   = useState("");
  const [domain, setDomain] = useState("");
  const [page, setPage]     = useState(1);

  const DOMAINS = useMemo(() => [...new Set(taxonomy.map(r => r.domain).filter(Boolean))].sort(), [taxonomy]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return taxonomy.filter(r =>
      (!q || r.text?.toLowerCase().includes(q) || r.req_id?.toLowerCase().includes(q)) &&
      (!domain || r.domain === domain)
    );
  }, [taxonomy, query, domain]);

  const paginated = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);
  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE) || 1;

  const inp = { background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none" };

  if (taxonomy.length === 0) return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#38bdf8,#0ea5e9)", boxShadow: "0 0 10px rgba(56,189,248,0.4)" }} />
          <h1 className="page-title">Requirement Search</h1>
        </div>
      </div>
      <div style={{ textAlign: "center", padding: "60px 40px" }}>
        <div style={{ fontSize: 44, marginBottom: 16 }}>📋</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>Requirements Taxonomy Not Yet Available</div>
        <div style={{ fontSize: 13, color: "#475569", maxWidth: 480, margin: "0 auto" }}>
          The Dashboard Aggregator must be updated to output a <code style={{ color: "#38bdf8" }}>requirements_taxonomy</code> array in <code style={{ color: "#38bdf8" }}>frontend_state.json</code>.
        </div>
        <div style={{ marginTop: 20, padding: "14px 20px", background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.2)", borderRadius: 10, fontSize: 12, color: "#94a3b8", maxWidth: 480, margin: "20px auto 0" }}>
          <strong style={{ color: "#a78bfa" }}>Required fields per requirement:</strong>{" "}
          <code>req_id</code>, <code>text</code>, <code>domain</code>, <code>subdomain</code>, <code>source_document</code>
        </div>
      </div>
    </div>
  );

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#38bdf8,#0ea5e9)", boxShadow: "0 0 10px rgba(56,189,248,0.4)" }} />
          <h1 className="page-title">Requirement Search</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          <strong style={{ color: "#f1f5f9" }}>{taxonomy.length}</strong> requirements across <strong style={{ color: "#f1f5f9" }}>{DOMAINS.length}</strong> domains
        </p>
      </div>

      {/* Filters */}
      <div className="card" style={{ padding: "14px 18px", marginBottom: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <svg style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", opacity: 0.35 }} width="13" height="13" fill="none" stroke="#94a3b8" strokeWidth="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input placeholder="Search by keyword, REQ ID…" value={query} onChange={e => { setQuery(e.target.value); setPage(1); }}
            style={{ ...inp, width: "100%", paddingLeft: 30 }}
            onFocus={e => e.target.style.borderColor = "#10b981"}
            onBlur={e  => e.target.style.borderColor = "rgba(255,255,255,0.07)"} />
        </div>
        <select value={domain} onChange={e => { setDomain(e.target.value); setPage(1); }} style={{ ...inp, minWidth: 160 }}>
          <option value="">All Domains</option>
          {DOMAINS.map(d => <option key={d}>{d}</option>)}
        </select>
      </div>

      {/* Results */}
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 12 }}><strong style={{ color: "#94a3b8" }}>{filtered.length}</strong> results</div>
      {paginated.map((r, i) => (
        <div key={r.req_id} className="card animate-fade-up" style={{ padding: "16px 20px", marginBottom: 9, borderLeft: "3px solid #38bdf8", animationDelay: `${i * 20}ms` }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 9px", borderRadius: 5 }}>{r.req_id}</span>
            {r.domain && <span style={{ fontSize: 11, fontWeight: 700, color: "#38bdf8", background: "rgba(56,189,248,0.1)", padding: "3px 10px", borderRadius: 20, border: "1px solid rgba(56,189,248,0.2)" }}>{r.domain}</span>}
            {r.subdomain && <span style={{ fontSize: 11, color: "#64748b", background: "#162030", padding: "3px 10px", borderRadius: 10 }}>{r.subdomain}</span>}
            {r.source_document && <span style={{ fontSize: 10.5, color: "#475569", marginLeft: "auto" }}>{r.source_document}</span>}
          </div>
          <p style={{ fontSize: 13.5, color: "#94a3b8", lineHeight: 1.7, margin: 0 }}>{r.text}</p>
        </div>
      ))}

      {/* Pagination */}
      {filtered.length > ITEMS_PER_PAGE && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px", background: "#162030", borderRadius: 8, border: "1px solid rgba(255,255,255,0.04)", marginTop: 14, fontSize: 11.5, color: "#475569" }}>
          <span>Showing {(page - 1) * ITEMS_PER_PAGE + 1} – {Math.min(page * ITEMS_PER_PAGE, filtered.length)} of {filtered.length}</span>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ ...inp, padding: "5px 10px", cursor: "pointer", opacity: page === 1 ? 0.4 : 1 }}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} style={{ ...inp, padding: "5px 10px", cursor: "pointer", opacity: page >= totalPages ? 0.4 : 1 }}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
}
