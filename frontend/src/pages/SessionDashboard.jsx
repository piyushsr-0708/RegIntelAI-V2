/**
 * SessionDashboard.jsx — RegIntel AI V2
 * Document-centric dashboard for a single analysis session.
 * Always fetches real data from GET /documents/{document_id}/session.
 * No simulated fallback.
 */
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { apiFetch } from "../utils/api";
import Breadcrumbs from "../components/Breadcrumbs";
import SessionSummary from "../components/session/SessionSummary";
import SessionMapTable from "../components/session/SessionMapTable";
import DepartmentImpact from "../components/session/DepartmentImpact";
import { PriorityChart, CapabilityChart } from "../components/session/SessionCharts";
import SessionKnowledgeGraph from "../components/session/SessionKnowledgeGraph";
import VerificationSummary from "../components/session/VerificationSummary";
import AssignmentPreview from "../components/session/AssignmentPreview";

function StageSummaryRow({ stage }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "9px 14px", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ width: 22, height: 22, borderRadius: "50%", background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: "#34d399", fontWeight: 800, flexShrink: 0 }}>✓</div>
      <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>{stage.label}</span>
      <span style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>{stage.records}</span>
      <span style={{ fontSize: 11, color: "#34d399", fontFamily: "monospace", minWidth: 40, textAlign: "right" }}>
        {(stage.duration_ms / 1000).toFixed(1)}s
      </span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 3, height: 14, borderRadius: 2, background: "#10b981" }} />
        {title}
      </div>
      {children}
    </div>
  );
}

/**
 * Minimal chat panel — sends document_id + question to POST /chat,
 * renders the answer in the same card style used across this page.
 */
function ChatPanel({ documentId }) {
  const [question,  setQuestion]  = React.useState("");
  const [answer,    setAnswer]    = React.useState(null);
  const [sources,   setSources]   = React.useState([]);
  const [loading,   setLoading]   = React.useState(false);
  const [error,     setError]     = React.useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setAnswer(null);
    setSources([]);
    setError(null);

    apiFetch("/chat", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, question: question.trim() }),
    })
      .then((data) => {
        setAnswer(data.answer);
        setSources(data.sources || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Request failed.");
        setLoading(false);
      });
  }

  return (
    <div className="card" style={{ padding: "18px 20px" }}>
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 10, marginBottom: answer || error || loading ? 16 : 0 }}>
        <input
          id="chat-question-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`Ask a compliance question about ${documentId}…`}
          disabled={loading}
          style={{
            flex: 1, background: "#0d1520", border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 7, padding: "10px 14px", fontSize: 13, color: "#e2e8f0",
            outline: "none", fontFamily: "inherit",
          }}
        />
        <button
          id="chat-submit-btn"
          type="submit"
          disabled={loading || !question.trim()}
          style={{
            background: loading ? "#1a2332" : "#10b981", color: loading ? "#475569" : "#fff",
            border: "none", borderRadius: 7, padding: "10px 20px", fontSize: 13,
            fontWeight: 700, cursor: loading ? "not-allowed" : "pointer", transition: "background 0.15s",
            whiteSpace: "nowrap",
          }}
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#10b981", fontSize: 12, fontWeight: 600 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" style={{ animation: "spin 1s linear infinite", flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" fill="none" stroke="rgba(16,185,129,0.2)" strokeWidth="3"/>
            <path d="M12 2a10 10 0 0 1 10 10" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round"/>
          </svg>
          Generating answer — this may take up to 60 seconds on CPU…
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", borderRadius: 7, fontSize: 13, color: "#f87171" }}>
          {error}
        </div>
      )}

      {answer && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 8 }}>Answer</div>
          <div style={{ fontSize: 13, color: "#e2e8f0", lineHeight: 1.7, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {answer}
          </div>
          {sources.length > 0 && (
            <div style={{ marginTop: 12, display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 10, color: "#475569", fontWeight: 700, textTransform: "uppercase", alignSelf: "center" }}>Sources:</span>
              {sources.map((s) => (
                <span key={s} style={{ fontSize: 11, fontFamily: "monospace", background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)", color: "#34d399", padding: "2px 8px", borderRadius: 5 }}>
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


export default function SessionDashboard() {
  const { id }   = useParams();
  const navigate = useNavigate();
  const session  = useSession(decodeURIComponent(id));

  const [backendData,    setBackendData]    = React.useState(null);
  const [loadState,      setLoadState]      = React.useState("loading"); // loading | processing | done | error
  const [errorMsg,       setErrorMsg]       = React.useState(null);
  const [statusMessage,  setStatusMessage]  = React.useState(null);

  const docId = session?.document_id;

  React.useEffect(() => {
    if (!docId) {
      setLoadState("error");
      setErrorMsg("No document ID associated with this session.");
      return;
    }

    setLoadState("loading");
    let pollInterval = null;

    function loadSession() {
      apiFetch(`/documents/${docId}/session`)
        .then((data) => {
          setBackendData(data);
          setLoadState("done");
        })
        .catch((err) => {
          console.error("[SessionDashboard] Failed to fetch session:", err);
          setErrorMsg(err.message || "Failed to load session data from backend.");
          setLoadState("error");
        });
    }

    function checkStatus() {
      apiFetch(`/documents/${docId}/status`)
        .then((statusData) => {
          const { status, message } = statusData;
          if (status === "completed") {
            if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
            loadSession();
          } else if (status === "failed") {
            if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
            setErrorMsg(statusData.error || message || "Pipeline failed.");
            setLoadState("error");
          } else {
            // still processing
            setStatusMessage(message || "Processing…");
            setLoadState("processing");
          }
        })
        .catch(() => {
          // Status endpoint unreachable — try loading the session directly.
          // If it succeeds the pipeline completed; if it 404s we stay in loading.
          loadSession();
        });
    }

    // First attempt: try to load the session directly.
    // If it succeeds (pipeline already done), we're done immediately.
    // If it fails with 404, check the status endpoint to decide whether
    // to poll (processing) or show an error (failed / unknown).
    apiFetch(`/documents/${docId}/session`)
      .then((data) => {
        setBackendData(data);
        setLoadState("done");
      })
      .catch(() => {
        // Session not ready yet — check status
        checkStatus();
        pollInterval = setInterval(checkStatus, 2000);
      });

    return () => {
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [docId]);

  // ── Session not in context ─────────────────────────────────────────────────
  if (!session) return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>🔍</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#94a3b8", marginBottom: 8 }}>Session not found</div>
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 20, fontFamily: "monospace" }}>{decodeURIComponent(id)}</div>
      <button onClick={() => navigate("/pipeline")}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Pipeline
      </button>
    </div>
  );

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loadState === "loading") return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="40" height="40" viewBox="0 0 40 40" style={{ animation: "spin 1s linear infinite", marginBottom: 16 }}>
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="4"/>
        <path d="M20 4a16 16 0 0 1 16 16" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round"/>
      </svg>
      <div style={{ fontSize: 14, fontWeight: 700, color: "#10b981" }}>Loading session data…</div>
      <div style={{ fontSize: 12, color: "#475569", marginTop: 6, fontFamily: "monospace" }}>{docId}</div>
    </div>
  );

  // ── Processing (pipeline still running) ────────────────────────────────────
  if (loadState === "processing") return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <svg width="40" height="40" viewBox="0 0 40 40" style={{ animation: "spin 1s linear infinite", marginBottom: 16 }}>
        <circle cx="20" cy="20" r="16" fill="none" stroke="rgba(16,185,129,0.15)" strokeWidth="4"/>
        <path d="M20 4a16 16 0 0 1 16 16" fill="none" stroke="#10b981" strokeWidth="4" strokeLinecap="round"/>
      </svg>
      <div style={{ fontSize: 14, fontWeight: 700, color: "#10b981" }}>Pipeline still running…</div>
      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>{statusMessage}</div>
      <div style={{ fontSize: 11, color: "#475569", marginTop: 4, fontFamily: "monospace" }}>{docId}</div>
      <div style={{ fontSize: 11, color: "#475569", marginTop: 8 }}>This page will update automatically when processing completes.</div>
    </div>
  );

  // ── Backend error ──────────────────────────────────────────────────────────
  if (loadState === "error") return (
    <div style={{ textAlign: "center", padding: 80 }}>
      <div style={{ fontSize: 40, marginBottom: 14 }}>⚠️</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#f87171", marginBottom: 8 }}>Failed to load session</div>
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>{errorMsg}</div>
      <div style={{ fontSize: 11, color: "#475569", marginBottom: 20, fontFamily: "monospace" }}>{docId}</div>
      <button onClick={() => navigate("/pipeline")}
        style={{ padding: "10px 24px", background: "#10b981", color: "#fff", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}>
        ← Back to Pipeline
      </button>
    </div>
  );

  // ── Render real backend data ───────────────────────────────────────────────
  const d = backendData;
  const displaySession = {
    session_id:            session.session_id,
    document_id:           d.document_id,
    filename:              d.filename || session.filename,
    pages:                 d.page_count,
    words:                 d.word_count,
    requirements_found:    d.requirements_count,
    maps_generated:        d.maps_count,
    departments_impacted:  d.departments_count,
    knowledge_graph_nodes: (d.graph?.nodes || []).length,
    knowledge_graph_edges: (d.graph?.edges || []).length,
    automation_percentage: d.maps?.length
      ? Math.round(d.maps.reduce((s, m) => s + (Number(m.automation_percentage) || Number(m.automation_percent) || 0), 0) / d.maps.length)
      : null,
    overall_risk:          null,
    maps:                  (d.maps || []).map((m) => ({
      ...m,
      // Normalise field names so SessionMapTable and SessionMapDetail always find them
      department:           m.department || m.owner_department || "",
      owner_department:     m.owner_department || m.department || "",
      automation_percentage: Number(m.automation_percentage ?? m.automation_percent ?? 0),
      compliance_status:    m.compliance_status || m.status || "DRAFT",
      status:               m.status || m.compliance_status || "DRAFT",
    })),
    requirements:          d.requirements || [],
    verification_plans:    d.verification_plans || [],
    department_impact:     d.department_impact || [],
    graph:                 d.graph || { nodes: [], edges: [] },
    stages:                d.stages || [],
    processing_duration:   d.stages?.reduce((s, st) => s + (st.duration_ms || 0), 0) ?? 0,
    processing_timestamp:  session.processing_timestamp,
    upload_timestamp:      session.upload_timestamp,
  };

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      <button
        onClick={() => navigate("/pipeline")}
        style={{ background: "#1a2332", border: "1.5px solid rgba(255,255,255,0.08)", borderRadius: 7, padding: "8px 16px", fontSize: 12.5, color: "#94a3b8", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 18, cursor: "pointer", transition: "all 0.15s" }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#10b981"; e.currentTarget.style.color = "#10b981"; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"; e.currentTarget.style.color = "#94a3b8"; }}
      >
        ← Back to Pipeline
      </button>

      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.5)" }} />
          <h1 className="page-title">Session Dashboard</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          Analysis session · <span style={{ fontFamily: "monospace", color: "#64748b" }}>{displaySession.session_id}</span>
        </p>
      </div>

      <Section title="Document Summary">
        <SessionSummary session={displaySession} />
      </Section>

      {displaySession.stages.length > 0 && (
        <Section title="Pipeline Summary">
          <div className="card" style={{ overflow: "hidden", marginBottom: 0 }}>
            <div style={{ padding: "10px 14px", background: "#162030", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", fontSize: 11, color: "#475569" }}>
              <span>Stage</span>
              <div style={{ display: "flex", gap: 40 }}><span>Records</span><span>Duration</span></div>
            </div>
            {displaySession.stages.map((stage, i) => (
              <StageSummaryRow key={stage.id || i} stage={stage} />
            ))}
            <div style={{ padding: "10px 14px", background: "#162030", borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", fontSize: 11.5, color: "#34d399", fontWeight: 700 }}>
              <span>Total</span>
              <span style={{ fontFamily: "monospace" }}>{(displaySession.processing_duration / 1000).toFixed(1)}s</span>
            </div>
          </div>
        </Section>
      )}

      <Section title="MAP Summary">
        <SessionMapTable maps={displaySession.maps} sessionId={displaySession.session_id} />
      </Section>

      <Section title="Department Impact">
        <DepartmentImpact department_impact={displaySession.department_impact} />
      </Section>

      <Section title="Distributions">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
          <PriorityChart   maps={displaySession.maps} />
          <CapabilityChart maps={displaySession.maps} />
        </div>
      </Section>

      <Section title="Knowledge Graph">
        <SessionKnowledgeGraph graph={displaySession.graph} />
      </Section>

      <Section title="Verification Plans">
        <VerificationSummary verification_plans={displaySession.verification_plans} />
      </Section>

      <Section title="Assignment Preview">
        <AssignmentPreview maps={displaySession.maps} department_impact={displaySession.department_impact} />
      </Section>

      <Section title="AI Compliance Assistant">
        <ChatPanel documentId={docId} />
      </Section>
    </div>
  );
}
