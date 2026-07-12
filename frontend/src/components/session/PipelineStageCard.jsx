/**
 * PipelineStageCard.jsx — RegIntel AI V2
 * Displays a single pipeline stage with status, elapsed time, progress, records.
 */

const STATUS_STYLE = {
  pending:    { color: "#475569", bg: "rgba(71,85,105,0.1)",   border: "rgba(71,85,105,0.2)",   icon: "○" },
  running:    { color: "#38bdf8", bg: "rgba(56,189,248,0.1)",  border: "rgba(56,189,248,0.25)", icon: "◌" },
  completed:  { color: "#34d399", bg: "rgba(52,211,153,0.1)",  border: "rgba(52,211,153,0.2)",  icon: "✓" },
  error:      { color: "#f87171", bg: "rgba(248,113,113,0.1)", border: "rgba(248,113,113,0.2)", icon: "✕" },
};

export default function PipelineStageCard({ stage, index, status, progress, elapsed_ms }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.pending;
  const isRunning = status === "running";

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 14,
      padding: "12px 16px",
      background: isRunning ? "rgba(56,189,248,0.05)" : "transparent",
      border: `1px solid ${isRunning ? s.border : "rgba(255,255,255,0.04)"}`,
      borderRadius: 9,
      transition: "all 0.3s ease",
      marginBottom: 6,
    }}>
      {/* Step number */}
      <div style={{
        width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
        background: s.bg, border: `1.5px solid ${s.border}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: isRunning ? 10 : 12, color: s.color, fontWeight: 800,
      }}>
        {isRunning
          ? <svg width="12" height="12" viewBox="0 0 24 24" style={{ animation: "spin 1s linear infinite" }}>
              <circle cx="12" cy="12" r="9" fill="none" stroke="rgba(56,189,248,0.2)" strokeWidth="3"/>
              <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round"/>
            </svg>
          : s.icon}
      </div>

      {/* Label + progress bar */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: isRunning ? 5 : 0 }}>
          <span style={{ fontSize: 13, fontWeight: isRunning ? 700 : 500, color: status === "pending" ? "#475569" : "#e2e8f0" }}>
            {stage.label}
          </span>
          {status !== "pending" && (
            <span style={{ fontSize: 11, color: s.color, fontFamily: "monospace", fontWeight: 700 }}>
              {status === "running" ? `${progress}%` : stage.records}
            </span>
          )}
        </div>
        {isRunning && (
          <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg,#38bdf8,#0ea5e9)", borderRadius: 2, transition: "width 0.2s ease" }} />
          </div>
        )}
      </div>

      {/* Elapsed / records */}
      <div style={{ textAlign: "right", flexShrink: 0, minWidth: 80 }}>
        {status === "completed" && (
          <span style={{ fontSize: 10.5, color: "#475569", fontFamily: "monospace" }}>
            {(stage.duration_ms / 1000).toFixed(1)}s
          </span>
        )}
        {status === "running" && elapsed_ms != null && (
          <span style={{ fontSize: 10.5, color: "#38bdf8", fontFamily: "monospace" }}>
            {(elapsed_ms / 1000).toFixed(1)}s
          </span>
        )}
        {status === "pending" && (
          <span style={{ fontSize: 10.5, color: "#2a3a4f" }}>—</span>
        )}
      </div>
    </div>
  );
}
