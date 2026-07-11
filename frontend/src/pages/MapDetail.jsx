/**
 * MapDetail.jsx — RegIntel AI V2
 * Reads from: compliance_register, documents_table, timeline_metadata (all in frontend_state.json).
 * No backend. No detailed_maps (not emitted by aggregator).
 */
import { useParams, useNavigate } from "react-router-dom";
import { useFrontendState, useComplianceRegister } from "../context/FrontendStateContext";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import Breadcrumbs from "../components/Breadcrumbs";

const PRIORITY_COLOR = { CRITICAL: "#f87171", HIGH: "#fbbf24", MEDIUM: "#60a5fa", LOW: "#34d399" };
const CAP_DOMAIN_COLOR = {
  "Cyber Security": "#f87171", "AML": "#fbbf24", "KYC": "#fbbf24",
  "Fraud Risk": "#fb923c", "Treasury": "#a78bfa", "Foreign Exchange": "#a78bfa",
  "Capital Adequacy": "#60a5fa", "Liquidity": "#60a5fa", "Prudential Regulation": "#60a5fa",
  "IT Governance": "#34d399", "Governance": "#34d399", "Audit": "#94a3b8",
  "Reporting": "#94a3b8", "Risk Management": "#fb923c", "Outsourcing": "#94a3b8",
  "Digital Payments": "#22d3ee", "Customer Protection": "#22d3ee", "General": "#475569",
};

function MetaCard({ label, value, color = "#94a3b8", mono = false }) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6, letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 13, color, fontWeight: 600, wordBreak: "break-word", fontFamily: mono ? "monospace" : "inherit" }}>{value ?? "—"}</div>
    </div>
  );
}

function StatPill({ label, value, color }) {
  return (
    <div style={{ textAlign: "center", padding: "12px 18px", background: `${color}10`, border: `1px solid ${color}25`, borderRadius: 9 }}>
      <div style={{ fontSize: 20, fontWeight: 900, color, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 10, color: "#64748b", marginTop: 3, fontWeight: 600 }}>{label}</div>
    </div>
  );
}

export default function MapDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const mapId = decodeURIComponent(id);

  const { state, loading } = useFrontendState();
  const register = useComplianceRegister();

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="36" height="36" viewBox="0 0 36 36" style={{ animation: "spin 1s linear infinite", marginBottom: 14 }}>
        <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="3" />
        <path d="M18 4a14 14 0 0 1 14 14" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <div style={{ fontSize: 13, color: "#10b981", fontWeight: 600 }}>Loading MAP…</div>
    </div>
  );

  const listItem = register.find(m => m.map_id === mapId);

  // ── Not found state ────────────────────────────────────────────────────────
  if (!listItem) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 44, marginBottom: 12 }}>📋</div>
      <div style={{ fontSize: 17, fontWeight: 700, color: "#94a3b8", marginBottom: 6 }}>MAP not found</div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20 }}>{mapId}</div>
      <button
        onClick={() => navigate("/maps")}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
      >
        ← Back to Register
      </button>
    </div>
  );

  // ── Derive document-level metadata from documents_table ───────────────────
  const docRow = state?.documents_table?.find(d => d.document_id === listItem.document_id) ?? null;
  const pipelineRun = state?.timeline_metadata?.last_pipeline_run ?? null;

  const pColor = PRIORITY_COLOR[listItem.priority] ?? "#94a3b8";
  const autoVal = listItem.automation_percentage != null ? listItem.automation_percentage.toFixed(1) : "N/A";

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Back button */}
      <button
        onClick={() => navigate("/maps")}
        style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}
      >
        ← Back to Register
      </button>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: 11.5, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 9px", borderRadius: 5, border: "1px solid rgba(52,211,153,0.2)" }}>
              {listItem.map_id}
            </span>
            <PriorityBadge priority={listItem.priority.charAt(0) + listItem.priority.slice(1).toLowerCase()} size="lg" />
            <StatusBadge status={listItem.compliance_status} />
          </div>
          <h1 style={{ fontSize: 19, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.4, margin: 0 }}>{listItem.title}</h1>
        </div>
        <div style={{ textAlign: "center", flexShrink: 0, padding: "14px 20px", background: `${pColor}10`, border: `1px solid ${pColor}30`, borderRadius: 10 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>AUTOMATION</div>
          <div style={{ fontSize: 26, fontWeight: 900, color: pColor }}>{autoVal}%</div>
        </div>
      </div>

      {/* ── Core metadata grid ─────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 14 }}>
        <MetaCard label="DOCUMENT ID"   value={listItem.document_id}   color="#60a5fa" mono />
        <MetaCard label="DEPARTMENT"    value={listItem.department}     color="#a78bfa" />
        <MetaCard label="PRIORITY"      value={listItem.priority}       color={pColor} />
        <MetaCard label="COMPLIANCE STATUS" value={listItem.compliance_status} color="#94a3b8" />
        <MetaCard label="FAILED BLOCKERS"   value={listItem.failed_blocker_count ?? 0} color={listItem.failed_blocker_count > 0 ? "#f87171" : "#34d399"} />
        <MetaCard label="AUTOMATION %"  value={`${autoVal}%`}          color={pColor} />
      </div>

      {/* ── Decision rationale ─────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>DECISION RATIONALE</div>
        <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.65 }}>{listItem.decision_rationale}</div>
      </div>

      {/* ── Business capabilities ──────────────────────────────────────────── */}
      {listItem.business_capability?.length > 0 && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 10, letterSpacing: 0.5 }}>BUSINESS CAPABILITIES</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
            {listItem.business_capability.map(cap => {
              const c = CAP_DOMAIN_COLOR[cap] ?? "#94a3b8";
              return (
                <span key={cap} style={{ padding: "4px 12px", borderRadius: 20, background: `${c}15`, border: `1px solid ${c}30`, fontSize: 12, color: c, fontWeight: 600 }}>
                  {cap}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Document-level pipeline metadata ──────────────────────────────── */}
      {docRow && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 12, letterSpacing: 0.5 }}>DOCUMENT PIPELINE METADATA</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            <StatPill label="PLANS"       value={docRow.plans}   color="#60a5fa" />
            <StatPill label="CHECKS"      value={docRow.checks}  color="#a78bfa" />
            <StatPill label="DOC AUTOMATION" value={`${docRow.automation_percentage?.toFixed(1) ?? "N/A"}%`} color="#34d399" />
            <StatPill label="VERDICT"     value={docRow.verdict} color={docRow.verdict === "COMPLIANT" ? "#34d399" : docRow.verdict === "NON_COMPLIANT" ? "#f87171" : "#fbbf24"} />
          </div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div>
              <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>DOCUMENT STATUS: </span>
              <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600 }}>{docRow.status}</span>
            </div>
            {pipelineRun && (
              <div>
                <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>LAST PIPELINE RUN: </span>
                <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600, fontFamily: "monospace" }}>
                  {new Date(pipelineRun).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Requirement text note ──────────────────────────────────────────── */}
      <div style={{ padding: "13px 16px", background: "rgba(96,165,250,0.05)", border: "1px solid rgba(96,165,250,0.12)", borderRadius: 9, fontSize: 12, color: "#64748b", lineHeight: 1.6 }}>
        <span style={{ color: "#60a5fa", fontWeight: 700 }}>Full requirement text</span> is stored in{" "}
        <code style={{ color: "#93c5fd", fontSize: 11 }}>datasets/requirements/</code> and{" "}
        <code style={{ color: "#93c5fd", fontSize: 11 }}>datasets/reasoned_controls/</code>.
        {" "}The MAP ID <code style={{ color: "#34d399", fontSize: 11 }}>{listItem.map_id}</code> maps to document{" "}
        <code style={{ color: "#60a5fa", fontSize: 11 }}>{listItem.document_id}</code>.
        {" "}Emit <code style={{ color: "#93c5fd", fontSize: 11 }}>detailed_maps</code> from the Dashboard Aggregator to surface requirement text inline.
      </div>
    </div>
  );
}
