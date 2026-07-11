/**
 * Badges.jsx — Unchanged from V1 (pure UI, no data dependencies).
 */

export const PRIORITY_META = {
  Critical: { bg: "rgba(239,68,68,0.15)",  text: "#fca5a5", dot: "#ef4444", border: "rgba(239,68,68,0.3)" },
  High:     { bg: "rgba(251,191,36,0.12)",  text: "#fcd34d", dot: "#fbbf24", border: "rgba(251,191,36,0.3)" },
  Medium:   { bg: "rgba(96,165,250,0.12)",  text: "#93c5fd", dot: "#60a5fa", border: "rgba(96,165,250,0.3)" },
  Low:      { bg: "rgba(52,211,153,0.12)",  text: "#6ee7b7", dot: "#34d399", border: "rgba(52,211,153,0.25)" },
};

export const STATUS_META = {
  Pending:       { bg: "rgba(148,163,184,0.1)",  text: "#94a3b8", border: "rgba(148,163,184,0.2)", icon: "○" },
  "In Progress": { bg: "rgba(96,165,250,0.12)",  text: "#93c5fd", border: "rgba(96,165,250,0.25)", icon: "◑" },
  Completed:     { bg: "rgba(52,211,153,0.12)",  text: "#6ee7b7", border: "rgba(52,211,153,0.25)", icon: "●" },
  Overdue:       { bg: "rgba(239,68,68,0.13)",   text: "#fca5a5", border: "rgba(239,68,68,0.28)",  icon: "⚠" },
  // V2 status values from compliance_register
  PENDING:       { bg: "rgba(148,163,184,0.1)",  text: "#94a3b8", border: "rgba(148,163,184,0.2)", icon: "○" },
  NON_COMPLIANT: { bg: "rgba(239,68,68,0.13)",   text: "#fca5a5", border: "rgba(239,68,68,0.28)",  icon: "✕" },
  COMPLIANT:     { bg: "rgba(52,211,153,0.12)",  text: "#6ee7b7", border: "rgba(52,211,153,0.25)", icon: "✓" },
  PARTIAL:       { bg: "rgba(251,191,36,0.12)",  text: "#fcd34d", border: "rgba(251,191,36,0.3)",  icon: "◑" },
};

export function PriorityBadge({ priority, size = "sm" }) {
  const c = PRIORITY_META[priority] || PRIORITY_META.Low;
  return (
    <span style={{
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
      padding: size === "lg" ? "5px 13px" : "3px 9px",
      borderRadius: 20, fontSize: size === "lg" ? 12.5 : 11,
      fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 5,
    }}>
      <span style={{
        width: size === "lg" ? 7 : 5.5, height: size === "lg" ? 7 : 5.5,
        borderRadius: "50%", background: c.dot, display: "inline-block",
        animation: priority === "Critical" ? "pulse-dot 2s ease infinite" : "none",
      }} />
      {priority}
    </span>
  );
}

export function StatusBadge({ status }) {
  const c = STATUS_META[status] || STATUS_META.Pending;
  return (
    <span style={{
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
      padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700,
      display: "inline-flex", alignItems: "center", gap: 4,
    }}>
      <span style={{ fontSize: 8 }}>{c.icon}</span>
      {status}
    </span>
  );
}

export function ImpactScore({ score }) {
  const color = score >= 9 ? "#f87171" : score >= 7 ? "#fbbf24" : score >= 5 ? "#60a5fa" : "#34d399";
  return (
    <span style={{ fontWeight: 800, fontSize: 13.5, color }}>
      {score.toFixed(1)}<span style={{ fontSize: 10, fontWeight: 500, color: "#475569" }}>/10</span>
    </span>
  );
}
