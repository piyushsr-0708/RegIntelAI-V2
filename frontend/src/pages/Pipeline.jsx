/**
 * Pipeline.jsx — RegIntel AI V2
 * Entry point for processing a new regulatory document.
 * All execution flows through PipelineOrchestrator — no stage module is
 * called directly from this component.
 * 100% offline. No API calls. No backend.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useSessionContext } from "../context/SessionContext";
import { PIPELINE_STAGE_DEFS } from "../pipeline/pipelineUtils";
import * as PipelineOrchestrator from "../pipeline/PipelineOrchestrator";
import PipelineStageCard from "../components/session/PipelineStageCard";
import Breadcrumbs from "../components/Breadcrumbs";

const PHASE = { IDLE: "idle", RUNNING: "running", DONE: "done", ERROR: "error" };

const INIT_STAGES = PIPELINE_STAGE_DEFS.map(() => ({
  status: "pending", progress: 0, elapsed_ms: 0,
}));

export default function Pipeline() {
  const navigate   = useNavigate();
  const { can } = useAuth();
  const { createSession, updateSession } = useSessionContext();

  const [phase,        setPhase]        = useState(PHASE.IDLE);
  const [file,         setFile]         = useState(null);
  const [dragOver,     setDragOver]     = useState(false);
  const [sessionId,    setSessionId]    = useState(null);
  const [stageStates,  setStageStates]  = useState(INIT_STAGES);
  const [totalElapsed, setTotalElapsed] = useState(0);
  const [errorMsg,     setErrorMsg]     = useState(null);

  const fileInputRef = useRef(null);
  const timerRef     = useRef(null);
  const startRef     = useRef(null);

  // ── Total elapsed ticker ───────────────────────────────────────────────────
  useEffect(() => {
    if (phase === PHASE.RUNNING) {
      startRef.current = Date.now();
      timerRef.current = setInterval(() => setTotalElapsed(Date.now() - startRef.current), 100);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [phase]);

  // ── File selection ─────────────────────────────────────────────────────────
  const handleFile = useCallback((f) => {
    if (!f) return;
    setFile(f);
    setPhase(PHASE.IDLE);
    setStageStates(INIT_STAGES);
    setTotalElapsed(0);
    setSessionId(null);
    setErrorMsg(null);
  }, []);

  const onInputChange = (e) => handleFile(e.target.files?.[0] ?? null);
  const onDrop = (e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0] ?? null); };

  // ── Run pipeline via orchestrator ──────────────────────────────────────────
  const runPipeline = useCallback(async () => {
    if (!file) return;

    const sid = createSession(file.name);
    setSessionId(sid);
    setPhase(PHASE.RUNNING);
    setErrorMsg(null);

    try {
      const result = await PipelineOrchestrator.run({
        file,

        onUploadComplete: (document_id) => {
          // Persist the real backend document_id as soon as upload succeeds,
          // before the pipeline finishes. Fixes stale document_id after refresh.
          updateSession(sid, { document_id, status: "processing" });
        },

        onStageStart: (i) => {
          setStageStates((prev) =>
            prev.map((s, idx) => idx === i ? { status: "running", progress: 0, elapsed_ms: 0 } : s)
          );
        },

        onStageProgress: (i, pct, elapsed_ms) => {
          setStageStates((prev) =>
            prev.map((s, idx) => idx === i ? { ...s, progress: pct, elapsed_ms } : s)
          );
        },

        onStageComplete: (i) => {
          setStageStates((prev) =>
            prev.map((s, idx) => idx === i ? { ...s, status: "completed", progress: 100 } : s)
          );
        },
      });

      // Store the real document_id from the backend into the session
      updateSession(sid, { document_id: result.document_id, status: "completed" });
      setPhase(PHASE.DONE);
      setTimeout(() => navigate(`/session/${encodeURIComponent(sid)}`), 700);
    } catch (err) {
      console.error("[Pipeline] Upload/pipeline error:", err);
      setErrorMsg(err.message || "Upload failed");
      setPhase(PHASE.ERROR);
      // Remove the incomplete session so it doesn't appear in Recent Sessions
      updateSession(sid, { status: "failed" });
    }
  }, [file, createSession, updateSession, navigate]);

  const completedCount  = stageStates.filter((s) => s.status === "completed").length;
  const overallProgress = Math.round((completedCount / PIPELINE_STAGE_DEFS.length) * 100);

  const inp = {
    background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)",
    borderRadius: 7, padding: "9px 12px", fontSize: 12.5, color: "#e2e8f0", outline: "none",
  };

  return (
    <div className="animate-fade-in">
      <Breadcrumbs />

      {/* Header */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
            <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#10b981,#059669)", boxShadow: "0 0 10px rgba(16,185,129,0.5)" }} />
            <h1 className="page-title">Analysis Pipeline</h1>
          </div>
          <p className="page-subtitle" style={{ paddingLeft: 14 }}>
            Upload a regulatory document to create a new analysis session
          </p>
        </div>
        {phase === PHASE.RUNNING && (
          <div style={{ background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: 9, padding: "10px 18px", textAlign: "right" }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 3 }}>ELAPSED</div>
            <div style={{ fontSize: 18, fontWeight: 900, color: "#10b981", fontFamily: "monospace" }}>
              {(totalElapsed / 1000).toFixed(1)}s
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: 20, alignItems: "start" }}>

        {/* ── Left: upload + controls ──────────────────────────────────── */}
        <div>
          {/* Drop zone */}
          <div
            onDragOver={(e) => { if (can('doc:upload')) { e.preventDefault(); setDragOver(true); } }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { if (can('doc:upload')) onDrop(e); }}
            onClick={() => can('doc:upload') && phase === PHASE.IDLE && fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${dragOver ? "#10b981" : file ? "rgba(16,185,129,0.4)" : "rgba(255,255,255,0.1)"}`,
              borderRadius: 12, padding: "36px 24px", textAlign: "center",
              background: dragOver ? "rgba(16,185,129,0.05)" : "rgba(255,255,255,0.02)",
              cursor: can('doc:upload') ? (phase === PHASE.IDLE ? "pointer" : "default") : "not-allowed",
              opacity: can('doc:upload') ? 1 : 0.5,
              transition: "all 0.2s ease", marginBottom: 16,
            }}
          >
            <input ref={fileInputRef} type="file" accept=".pdf,.txt,.docx" onChange={onInputChange} style={{ display: "none" }} />
            {file ? (
              <>
                <div style={{ fontSize: 36, marginBottom: 10 }}>📄</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#f1f5f9", marginBottom: 4 }}>{file.name}</div>
                <div style={{ fontSize: 12, color: "#475569" }}>{(file.size / 1024).toFixed(1)} KB</div>
                {phase === PHASE.IDLE && <div style={{ fontSize: 11, color: "#64748b", marginTop: 8 }}>Click to change file</div>}
              </>
            ) : (
              <>
                <div style={{ fontSize: 36, marginBottom: 12 }}>📂</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#94a3b8", marginBottom: 6 }}>Drop a document here</div>
                <div style={{ fontSize: 12, color: "#475569" }}>or click to browse · PDF, TXT, DOCX</div>
              </>
            )}
          </div>

          {/* Run button */}
          {phase === PHASE.IDLE && file && can('doc:upload') && (
            <button
              onClick={runPipeline}
              style={{ width: "100%", padding: "14px", fontSize: 14, fontWeight: 700, color: "#fff", background: "linear-gradient(135deg,#10b981,#059669)", border: "none", borderRadius: 9, cursor: "pointer", boxShadow: "0 4px 14px rgba(16,185,129,0.3)", transition: "all 0.2s", marginBottom: 16 }}
              onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-1px)"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(16,185,129,0.4)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 4px 14px rgba(16,185,129,0.3)"; }}
            >
              ▶ Run Analysis Pipeline
            </button>
          )}

          {/* Progress bar */}
          {phase === PHASE.RUNNING && (
            <div style={{ padding: "12px 16px", background: "rgba(56,189,248,0.07)", border: "1px solid rgba(56,189,248,0.2)", borderRadius: 9, marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: "#38bdf8", fontWeight: 700 }}>Processing…</span>
                <span style={{ fontSize: 12, color: "#38bdf8", fontFamily: "monospace", fontWeight: 700 }}>{overallProgress}%</span>
              </div>
              <div style={{ height: 5, background: "rgba(255,255,255,0.06)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${overallProgress}%`, background: "linear-gradient(90deg,#38bdf8,#0ea5e9)", borderRadius: 3, transition: "width 0.3s ease" }} />
              </div>
              <div style={{ fontSize: 11, color: "#475569", marginTop: 6 }}>
                Stage {Math.min(completedCount + 1, PIPELINE_STAGE_DEFS.length)} of {PIPELINE_STAGE_DEFS.length}
              </div>
            </div>
          )}

          {/* Done */}
          {phase === PHASE.DONE && (
            <div style={{ padding: "14px 16px", background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.25)", borderRadius: 9, marginBottom: 16, textAlign: "center" }}>
              <div style={{ fontSize: 22, marginBottom: 6 }}>✅</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#34d399" }}>Pipeline complete — navigating to session…</div>
            </div>
          )}

          {/* Error */}
          {phase === PHASE.ERROR && (
            <div style={{ padding: "14px 16px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 9, marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#f87171", marginBottom: 4 }}>⚠ Upload failed</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{errorMsg}</div>
              <button
                onClick={() => { setPhase(PHASE.IDLE); setStageStates(INIT_STAGES); }}
                style={{ marginTop: 10, padding: "6px 14px", background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 6, color: "#f87171", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                Try again
              </button>
            </div>
          )}

          {/* Session ID */}
          {sessionId && (
            <div style={{ padding: "10px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, fontSize: 11, color: "#475569", marginBottom: 4 }}>
              <span style={{ color: "#64748b", fontWeight: 700 }}>Session: </span>
              <span style={{ fontFamily: "monospace", color: "#94a3b8" }}>{sessionId}</span>
            </div>
          )}

          <RecentSessions />
        </div>

        {/* ── Right: stage list ────────────────────────────────────────── */}
        <div className="card" style={{ padding: "18px 20px" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 14 }}>
            Pipeline Stages
          </div>
          {PIPELINE_STAGE_DEFS.map((def, i) => (
            <PipelineStageCard
              key={def.id}
              stage={def}
              index={i}
              status={stageStates[i].status}
              progress={stageStates[i].progress}
              elapsed_ms={stageStates[i].elapsed_ms}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Recent sessions list ───────────────────────────────────────────────────────
function RecentSessions() {
  const { sessions } = useSessionContext();
  const navigate     = useNavigate();
  if (!sessions.length) return null;

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase", marginBottom: 10 }}>
        Recent Sessions
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {sessions.filter(s => s.status !== "failed").slice(0, 5).map((s) => (
          <button
            key={s.session_id}
            onClick={() => s.status === "completed" && navigate(`/session/${encodeURIComponent(s.session_id)}`)}
            style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 12px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, cursor: s.status === "completed" ? "pointer" : "default", textAlign: "left", transition: "all 0.15s" }}
            onMouseEnter={(e) => { if (s.status === "completed") e.currentTarget.style.borderColor = "rgba(16,185,129,0.3)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; }}
          >
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#e2e8f0" }}>{s.filename}</div>
              <div style={{ fontSize: 10, color: "#475569", fontFamily: "monospace", marginTop: 2 }}>{s.session_id}</div>
            </div>
            <span style={{ fontSize: 10, fontWeight: 700, color: s.status === "completed" ? "#34d399" : "#38bdf8", background: s.status === "completed" ? "rgba(52,211,153,0.1)" : "rgba(56,189,248,0.1)", padding: "2px 8px", borderRadius: 20, flexShrink: 0 }}>
              {s.status === "completed" ? "DONE" : "RUNNING"}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
