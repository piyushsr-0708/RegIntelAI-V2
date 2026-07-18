/**
 * MapDetail.jsx — RegIntel AI V2
 * Reads from: compliance_register (frontend_state.json) for summary
 * Fetches: /maps/{map_id}/detail API for complete MAP information
 */
import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { useFrontendState, useComplianceRegister } from "../context/FrontendStateContext";
import { fetchMapDetail } from "../utils/api";
import { useSession } from "../context/SessionContext";
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
  const { id, sessionId, mapId: paramMapId } = useParams();
  const navigate = useNavigate();
  const mapId = decodeURIComponent(id || paramMapId);

  const { state, loading } = useFrontendState();
  const register = useComplianceRegister();
  const session = useSession(sessionId ? decodeURIComponent(sessionId) : null);
  
  const isSessionRoute = Boolean(sessionId);
  const backDest = isSessionRoute ? `/session/${encodeURIComponent(sessionId)}` : "/maps";
  const backText = isSessionRoute ? "← Back to Session" : "← Back to Register";
  
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(true);
  const [detailError, setDetailError] = useState(null);

  // Fetch detailed MAP data from API
  useEffect(() => {
    async function loadDetail() {
      try {
        setDetailLoading(true);
        const data = await fetchMapDetail(mapId);
        setDetailData(data);
        setDetailError(null);
      } catch (err) {
        setDetailError(err.message);
      } finally {
        setDetailLoading(false);
      }
    }
    
    if (mapId) {
      loadDetail();
    }
  }, [mapId]);

  // Re-fetch when the tab regains focus so MAP status reflects recent approvals
  useEffect(() => {
    if (!mapId) return;
    function onFocus() {
      fetchMapDetail(mapId)
        .then((data) => setDetailData(data))
        .catch(() => {});
    }
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [mapId]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (loading || detailLoading) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="36" height="36" viewBox="0 0 36 36" style={{ animation: "spin 1s linear infinite", marginBottom: 14 }}>
        <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="3" />
        <path d="M18 4a14 14 0 0 1 14 14" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <div style={{ fontSize: 13, color: "#10b981", fontWeight: 600 }}>Loading MAP…</div>
    </div>
  );

  const listItem = register.find(m => m.map_id === mapId) || session?.maps?.find(m => m.map_id === mapId);

  // ── Not found state ────────────────────────────────────────────────────────
  if (!listItem) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 44, marginBottom: 12 }}>📋</div>
      <div style={{ fontSize: 17, fontWeight: 700, color: "#94a3b8", marginBottom: 6 }}>MAP not found</div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20 }}>{mapId}</div>
      <button
        onClick={() => navigate(backDest)}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
      >
        {backText}
      </button>
    </div>
  );

  // ── Derive document-level metadata from documents_table ───────────────────
  const docRow = state?.documents_table?.find(d => d.document_id === listItem.document_id) ?? null;
  const pipelineRun = state?.timeline_metadata?.last_pipeline_run ?? null;

  const pColor = PRIORITY_COLOR[listItem.priority] ?? "#94a3b8";
  
  // Use live API data for verification-related fields (compliance_status, decision_rationale, failed_blocker_count, automation_percentage)
  // Fallback to cached register data if API hasn't loaded yet
  const complianceStatus = detailData?.verification_plan ? 
    (detailData.compliance_decision?.verdict || "PENDING") : 
    listItem.compliance_status;
  
  const decisionRationale = detailData?.compliance_decision?.rationale || listItem.decision_rationale;
  
  const failedBlockerCount = detailData?.compliance_decision ? 
    (detailData.compliance_decision.failed_blocker_count || 0) : 
    (listItem.failed_blocker_count ?? 0);
  
  const autoVal = detailData?.verification_plan?.automation_percentage != null ? 
    detailData.verification_plan.automation_percentage.toFixed(1) : 
    (listItem.automation_percentage != null ? listItem.automation_percentage.toFixed(1) : "N/A");

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Back button */}
      <button
        onClick={() => navigate(backDest)}
        style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}
      >
        {backText}
      </button>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 20 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "monospace", fontSize: 11.5, fontWeight: 800, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 9px", borderRadius: 5, border: "1px solid rgba(52,211,153,0.2)" }}>
              {listItem.map_id}
            </span>
            <PriorityBadge priority={String(listItem.priority || "Medium").charAt(0) + String(listItem.priority || "Medium").slice(1).toLowerCase()} size="lg" />
            <StatusBadge status={complianceStatus} />
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
        <MetaCard label="COMPLIANCE STATUS" value={complianceStatus} color="#94a3b8" />
        <MetaCard label="FAILED BLOCKERS"   value={failedBlockerCount} color={failedBlockerCount > 0 ? "#f87171" : "#34d399"} />
        <MetaCard label="AUTOMATION %"  value={`${autoVal}%`}          color={pColor} />
      </div>

      {/* ── Decision rationale ─────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>DECISION RATIONALE</div>
        <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.65 }}>{decisionRationale}</div>
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
      {detailError && (
        <div style={{ padding: "13px 16px", background: "rgba(248,113,113,0.05)", border: "1px solid rgba(248,113,113,0.12)", borderRadius: 9, fontSize: 12, color: "#f87171", lineHeight: 1.6, marginBottom: 14 }}>
          <span style={{ fontWeight: 700 }}>Error loading detailed MAP data:</span> {detailError}
        </div>
      )}

      {/* ── MAP Objective ──────────────────────────────────────────────────── */}
      {detailData?.objective && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>OBJECTIVE</div>
          <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.65 }}>{detailData.objective}</div>
        </div>
      )}

      {/* ── Verification Plan ──────────────────────────────────────────────── */}
      {detailData?.verification_plan && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 12, letterSpacing: 0.5 }}>VERIFICATION PLAN</div>
          {detailData.verification_plan.plan_id && (
            <div style={{ marginBottom: 12 }}>
              <span style={{ fontFamily: "monospace", fontSize: 11.5, fontWeight: 800, color: "#a78bfa", background: "rgba(167,139,250,0.1)", padding: "3px 9px", borderRadius: 5, border: "1px solid rgba(167,139,250,0.2)" }}>
                {detailData.verification_plan.plan_id}
              </span>
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 12 }}>
            {detailData.verification_plan.control_name && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>CONTROL NAME</div>
                <div style={{ fontSize: 12, color: "#cbd5e1", fontWeight: 600 }}>{detailData.verification_plan.control_name}</div>
              </div>
            )}
            {detailData.verification_plan.business_capability && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>BUSINESS CAPABILITY</div>
                <div style={{ fontSize: 12, color: "#cbd5e1", fontWeight: 600 }}>{detailData.verification_plan.business_capability}</div>
              </div>
            )}
            {detailData.verification_plan.control_category && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>CATEGORY</div>
                <div style={{ fontSize: 12, color: "#cbd5e1", fontWeight: 600 }}>{detailData.verification_plan.control_category}</div>
              </div>
            )}
          </div>
          {(detailData.verification_plan.total_checks != null || detailData.verification_plan.automation_percentage != null) && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              {detailData.verification_plan.total_checks != null && (
                <StatPill label="TOTAL CHECKS" value={detailData.verification_plan.total_checks} color="#60a5fa" />
              )}
              {detailData.verification_plan.mandatory_checks != null && (
                <StatPill label="MANDATORY" value={detailData.verification_plan.mandatory_checks} color="#f87171" />
              )}
              {detailData.verification_plan.machine_verifiable_checks != null && (
                <StatPill label="AUTOMATED" value={detailData.verification_plan.machine_verifiable_checks} color="#34d399" />
              )}
              {detailData.verification_plan.automation_percentage != null && (
                <StatPill label="AUTOMATION %" value={`${detailData.verification_plan.automation_percentage.toFixed(1)}%`} color="#a78bfa" />
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Verification Agent ─────────────────────────────────────────────── */}
      {detailData?.agent_decision && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14, background: "rgba(16,185,129,0.02)", border: "1px solid rgba(16,185,129,0.1)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 18 }}>🤖</span>
            <div style={{ fontSize: 10, color: "#10b981", fontWeight: 700, letterSpacing: 0.5 }}>VERIFICATION AGENT</div>
          </div>
          
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>VERDICT</div>
              <span style={{ 
                fontSize: 12, 
                fontWeight: 700, 
                color: detailData.agent_decision.verdict === "GO" ? "#34d399" : detailData.agent_decision.verdict === "ESCALATE" ? "#fbbf24" : "#f87171",
                background: detailData.agent_decision.verdict === "GO" ? "rgba(52,211,153,0.1)" : detailData.agent_decision.verdict === "ESCALATE" ? "rgba(251,191,36,0.1)" : "rgba(248,113,113,0.1)",
                padding: "4px 10px",
                borderRadius: 5,
                border: detailData.agent_decision.verdict === "GO" ? "1px solid rgba(52,211,153,0.2)" : detailData.agent_decision.verdict === "ESCALATE" ? "1px solid rgba(251,191,36,0.2)" : "1px solid rgba(248,113,113,0.2)"
              }}>
                {detailData.agent_decision.verdict}
              </span>
            </div>
            
            {detailData.agent_decision.confidence_score != null && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>CONFIDENCE</div>
                <div style={{ fontSize: 12, color: "#cbd5e1", fontWeight: 600 }}>
                  {(detailData.agent_decision.confidence_score * 100).toFixed(0)}%
                </div>
              </div>
            )}
            
            {detailData.agent_decision.automation_feasibility && (
              <div>
                <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 4 }}>AUTOMATION</div>
                <div style={{ fontSize: 12, color: "#cbd5e1", fontWeight: 600 }}>
                  {detailData.agent_decision.automation_feasibility}
                </div>
              </div>
            )}
          </div>
          
          {detailData.agent_decision.reasoning && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6 }}>REASONING</div>
              <div style={{ fontSize: 12, color: "#cbd5e1", lineHeight: 1.6 }}>
                {detailData.agent_decision.reasoning}
              </div>
            </div>
          )}
          
          {detailData.agent_decision.recommended_action && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 6 }}>RECOMMENDATION</div>
              <div style={{ fontSize: 12, color: "#10b981", lineHeight: 1.6, fontWeight: 600 }}>
                {detailData.agent_decision.recommended_action}
              </div>
            </div>
          )}
          
          {(detailData.agent_decision.automated_checks_available != null || detailData.agent_decision.manual_checks_required != null) && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {detailData.agent_decision.automated_checks_available != null && (
                <div style={{ textAlign: "center", padding: "10px 16px", background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.2)", borderRadius: 7 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "#34d399", lineHeight: 1 }}>
                    {detailData.agent_decision.automated_checks_available}
                  </div>
                  <div style={{ fontSize: 9, color: "#64748b", marginTop: 3, fontWeight: 600 }}>AUTOMATED</div>
                </div>
              )}
              {detailData.agent_decision.manual_checks_required != null && (
                <div style={{ textAlign: "center", padding: "10px 16px", background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.2)", borderRadius: 7 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "#fbbf24", lineHeight: 1 }}>
                    {detailData.agent_decision.manual_checks_required}
                  </div>
                  <div style={{ fontSize: 9, color: "#64748b", marginTop: 3, fontWeight: 600 }}>MANUAL</div>
                </div>
              )}
              {detailData.agent_decision.total_checks != null && (
                <div style={{ textAlign: "center", padding: "10px 16px", background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.2)", borderRadius: 7 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "#60a5fa", lineHeight: 1 }}>
                    {detailData.agent_decision.total_checks}
                  </div>
                  <div style={{ fontSize: 9, color: "#64748b", marginTop: 3, fontWeight: 600 }}>TOTAL</div>
                </div>
              )}
            </div>
          )}
          
          {(detailData.agent_decision.regulatory_intent || detailData.agent_decision.control_objective) && (
            <div style={{ marginTop: 14, padding: "12px", background: "rgba(255,255,255,0.02)", borderRadius: 6, border: "1px solid rgba(255,255,255,0.05)" }}>
              {detailData.agent_decision.regulatory_intent && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>REGULATORY INTENT: </span>
                  <span style={{ fontSize: 11, color: "#94a3b8" }}>{detailData.agent_decision.regulatory_intent}</span>
                </div>
              )}
              {detailData.agent_decision.control_objective && (
                <div>
                  <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>CONTROL OBJECTIVE: </span>
                  <span style={{ fontSize: 11, color: "#94a3b8" }}>{detailData.agent_decision.control_objective}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Verification Checks ─────────────────────────────────────────────── */}
      {detailData?.verification_plan?.checks && detailData.verification_plan.checks.length > 0 && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 12, letterSpacing: 0.5 }}>
            VERIFICATION CHECKS ({detailData.verification_plan.checks.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {detailData.verification_plan.checks.map((check) => (
              <div key={check.check_id} style={{ padding: "12px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#34d399", marginBottom: 4, fontFamily: "monospace" }}>
                      {check.check_id}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", marginBottom: 6 }}>
                      {check.title}
                    </div>
                    <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6, marginBottom: 8 }}>
                      {check.description}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0, marginLeft: 12 }}>
                    {check.mandatory && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#f87171", background: "rgba(248,113,113,0.1)", padding: "3px 8px", borderRadius: 4, border: "1px solid rgba(248,113,113,0.2)" }}>
                        MANDATORY
                      </span>
                    )}
                    {check.machine_verifiable && (
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#34d399", background: "rgba(52,211,153,0.1)", padding: "3px 8px", borderRadius: 4, border: "1px solid rgba(52,211,153,0.2)" }}>
                        AUTOMATED
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, fontSize: 11 }}>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>PLATFORM: </span>
                    <span style={{ color: "#94a3b8" }}>{check.verification_platform || "N/A"}</span>
                  </div>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>MECHANISM: </span>
                    <span style={{ color: "#94a3b8" }}>{check.verification_mechanism || "N/A"}</span>
                  </div>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>IMPACT: </span>
                    <span style={{ color: check.failure_impact === "BLOCKER" ? "#f87171" : check.failure_impact === "MAJOR" ? "#fbbf24" : "#94a3b8" }}>
                      {check.failure_impact || "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Implementation Tasks ────────────────────────────────────────────── */}
      {detailData?.tasks && detailData.tasks.length > 0 && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 12, letterSpacing: 0.5 }}>
            IMPLEMENTATION TASKS ({detailData.tasks.length})
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {detailData.tasks.map((task) => (
              <div key={task.task_id} style={{ padding: "12px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "#60a5fa", fontFamily: "monospace" }}>
                        Task {task.task_number}
                      </span>
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#a78bfa", background: "rgba(167,139,250,0.1)", padding: "2px 8px", borderRadius: 4 }}>
                        {task.task_type}
                      </span>
                      {task.approval_required && (
                        <span style={{ fontSize: 10, fontWeight: 700, color: "#fbbf24", background: "rgba(251,191,36,0.1)", padding: "2px 8px", borderRadius: 4 }}>
                          APPROVAL REQ
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", marginBottom: 6 }}>
                      {task.title}
                    </div>
                    <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6, marginBottom: 8 }}>
                      {task.description}
                    </div>
                  </div>
                  <PriorityBadge priority={String(task.priority || "Medium").charAt(0) + String(task.priority || "Medium").slice(1).toLowerCase()} size="sm" />
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10, fontSize: 11 }}>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>DEPARTMENT: </span>
                    <span style={{ color: "#94a3b8" }}>{task.assigned_department}</span>
                  </div>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>EFFORT: </span>
                    <span style={{ color: "#94a3b8" }}>{task.estimated_effort_hours}h</span>
                  </div>
                  <div>
                    <span style={{ color: "#475569", fontWeight: 700 }}>STATUS: </span>
                    <span style={{ color: task.status === "COMPLETED" ? "#34d399" : task.status === "IN_PROGRESS" ? "#60a5fa" : "#94a3b8" }}>
                      {task.status}
                    </span>
                  </div>
                  {task.deliverable && (
                    <div>
                      <span style={{ color: "#475569", fontWeight: 700 }}>DELIVERABLE: </span>
                      <span style={{ color: "#94a3b8" }}>{task.deliverable}</span>
                    </div>
                  )}
                </div>
                {task.dependencies && task.dependencies.length > 0 && (
                  <div style={{ marginTop: 8, fontSize: 11 }}>
                    <span style={{ color: "#475569", fontWeight: 700 }}>DEPENDS ON: </span>
                    <span style={{ color: "#94a3b8", fontFamily: "monospace" }}>{task.dependencies.join(", ")}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Compliance Decision ─────────────────────────────────────────────── */}
      {detailData?.compliance_decision && (
        <div className="card" style={{ padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>COMPLIANCE DECISION</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div>
              <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>VERDICT: </span>
              <span style={{ fontSize: 12, color: detailData.compliance_decision.verdict === "COMPLIANT" ? "#34d399" : detailData.compliance_decision.verdict === "NON_COMPLIANT" ? "#f87171" : "#fbbf24", fontWeight: 700 }}>
                {detailData.compliance_decision.verdict}
              </span>
            </div>
            {detailData.compliance_decision.department && (
              <div>
                <span style={{ fontSize: 10, color: "#475569", fontWeight: 700 }}>DEPARTMENT: </span>
                <span style={{ fontSize: 12, color: "#94a3b8", fontWeight: 600 }}>{detailData.compliance_decision.department}</span>
              </div>
            )}
          </div>
          {detailData.compliance_decision.rationale && (
            <div style={{ fontSize: 12, color: "#cbd5e1", lineHeight: 1.6 }}>{detailData.compliance_decision.rationale}</div>
          )}
        </div>
      )}

      {/* Session context footer */}
      {isSessionRoute && (
        <div style={{ padding: "12px 16px", background: "rgba(96,165,250,0.05)", border: "1px solid rgba(96,165,250,0.12)", borderRadius: 9, fontSize: 12, color: "#64748b", lineHeight: 1.6, marginTop: 14 }}>
          <span style={{ color: "#60a5fa", fontWeight: 700 }}>Session artefact</span> — this MAP was generated during session{" "}
          <code style={{ color: "#94a3b8", fontSize: 11 }}>{decodeURIComponent(sessionId)}</code> from document{" "}
          <code style={{ color: "#60a5fa", fontSize: 11 }}>{listItem?.document_id ?? "—"}</code>.
        </div>
      )}
    </div>
  );
}
