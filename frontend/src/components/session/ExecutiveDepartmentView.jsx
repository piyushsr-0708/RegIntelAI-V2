/**
 * ExecutiveDepartmentView.jsx — RegIntel AI V2
 *
 * Sankey-Style Regulatory Flow Visualization
 * ─────────────────────────────────────────────
 * Renders the AI's distribution of regulatory obligations as an animated
 * SVG flow: Source Document → curved weighted paths → Department nodes.
 *
 * Design: Microsoft Defender / Azure Portal / IBM QRadar aesthetic.
 * No external graph libraries — pure React + native SVG + CSS.
 *
 * Props (unchanged interface — compatible with SessionKnowledgeGraph):
 *   graph       — { nodes[], edges[] } from stageGraphBuilder
 *   selectedId  — current selected node id (drives right-side panel)
 *   onSelect    — (mapNode) → void  — fires when a MAP card is clicked
 *   onNavigate  — (mapId)   → void  — fires when Details → is clicked
 *
 * Feature flag: set USE_DEPARTMENT_CONTAINERS = false to fall back to
 * the original SVG renderer in SessionKnowledgeGraph.jsx.
 */

import { useState, useMemo, useEffect } from "react";
import { PRIORITY_META } from "../Badges";

// ─── Feature flag ──────────────────────────────────────────────────────────────
export const USE_DEPARTMENT_CONTAINERS = true;

// ─── SVG canvas constants ──────────────────────────────────────────────────────
const VW         = 900;   // viewBox width
const DOC_W      = 230;   // document node width
const DOC_H      = 58;    // document node height
const DOC_Y      = 24;    // top padding before doc node
const DOC_CX     = VW / 2;
const DOC_BOT    = DOC_Y + DOC_H;  // bottom y of doc node

const MID_Y      = 178;  // y of the "AI distribution" label strip
const DEPT_Y     = 234;  // top of department nodes
const DEPT_H     = 98;   // department node height
const DEPT_GAP   = 16;   // gap between department nodes
const SVG_PAD    = 44;   // horizontal padding

// Path control-point ratios (cubic bezier tuning)
const CP_SRC_RATIO = 0.52;   // how far down from doc the first CP is
const CP_DST_RATIO = 0.38;   // how far above dept the second CP is

// Animation timings (ms)
const T_DOC   = 0;
const T_STRIP = 220;
const T_PATH  = 360;
const T_DEPT  = 560;
const T_LABEL = 720;
const PATH_STRIDE = 80;  // stagger between each dept path
const DEPT_STRIDE = 70;

// ─── Module-level flag: inject keyframes only once ────────────────────────────
let _cssInjected = false;

const KEYFRAMES = `
@keyframes edv-doc-in {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: translateY(0);     }
}
@keyframes edv-strip-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes edv-path-in {
  from { stroke-dashoffset: 900; opacity: 0; }
  to   { stroke-dashoffset: 0;   opacity: 1; }
}
@keyframes edv-dept-in {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0);    }
}
@keyframes edv-label-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes edv-map-card-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0);   }
}
@keyframes edv-expand-in {
  from { opacity: 0; transform: scaleY(0.94); }
  to   { opacity: 1; transform: scaleY(1);    }
}
`;

function ensureCss() {
  if (_cssInjected) return;
  _cssInjected = true;
  const el = document.createElement("style");
  el.setAttribute("data-edv", "1");
  el.textContent = KEYFRAMES;
  document.head.appendChild(el);
}

// ─── Priority helpers ──────────────────────────────────────────────────────────
const PRIO_RANK = { critical: 0, high: 1, medium: 2, low: 3 };

function prioRank(p) {
  return PRIO_RANK[String(p || "").toLowerCase()] ?? 99;
}

function normalizePriority(p) {
  if (!p) return "Medium";
  const s = String(p);
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

// ─── Status accent colour ──────────────────────────────────────────────────────
function statusAccent(status) {
  if (!status) return "#64748b";
  const s = String(status).toLowerCase();
  if (s.includes("non") || s.includes("critical")) return "#ef4444";
  if (s.includes("partial") || s.includes("pending") || s.includes("in_progress") || s.includes("in progress")) return "#fbbf24";
  if (s.includes("compliant") || s.includes("complete")) return "#10b981";
  return "#64748b";
}

// ─── Data model ───────────────────────────────────────────────────────────────
function buildData(nodes) {
  const docNode  = nodes.find((n) => n.type === "document");
  const mapNodes = nodes.filter((n) => n.type === "map");

  const deptMap = new Map();
  for (const m of mapNodes) {
    const d = m.department || m.owner_department || "Unassigned";
    if (!deptMap.has(d)) deptMap.set(d, { name: d, maps: [] });
    deptMap.get(d).maps.push(m);
  }

  const depts = [...deptMap.values()].sort(
    (a, b) => b.maps.length - a.maps.length || a.name.localeCompare(b.name)
  );

  for (const d of depts) {
    d.maps.sort((a, b) => prioRank(a.priority) - prioRank(b.priority));
  }

  return { docNode, depts, totalMaps: mapNodes.length };
}

// ─── Layout engine ─────────────────────────────────────────────────────────────
function computeLayout(depts) {
  const n = depts.length;
  if (n === 0) return [];

  // Available horizontal space
  const avail = VW - 2 * SVG_PAD;

  // Scale dept node width if too many depts
  let dW   = 148;
  let gap  = DEPT_GAP;
  const totalNatural = n * dW + (n - 1) * gap;
  if (totalNatural > avail) {
    gap  = Math.max(8, gap - 4);
    dW   = Math.max(88, Math.floor((avail - (n - 1) * gap) / n));
  }

  const totalW = n * dW + (n - 1) * gap;
  const startX = (VW - totalW) / 2;

  return depts.map((dept, i) => ({
    ...dept,
    x:  startX + i * (dW + gap),
    cx: startX + i * (dW + gap) + dW / 2,
    dW,
    dH: DEPT_H,
  }));
}

// ─── SVG cubic-bezier path string ─────────────────────────────────────────────
function sankeyPath(srcX, srcY, dstX, dstY) {
  const spanY = dstY - srcY;
  const cp1y  = srcY + spanY * CP_SRC_RATIO;
  const cp2y  = dstY - spanY * CP_DST_RATIO;
  return `M ${srcX},${srcY} C ${srcX},${cp1y} ${dstX},${cp2y} ${dstX},${dstY}`;
}

// ─── MapCard (HTML, below SVG) ─────────────────────────────────────────────────
function MapCard({ mapNode, isSelected, onSelect, onNavigate, animDelay }) {
  const priority  = normalizePriority(mapNode.priority);
  const pm        = PRIORITY_META[priority] || PRIORITY_META.Medium;
  const compliance = mapNode.compliance_status || mapNode.status || "PENDING";
  const sColor    = statusAccent(compliance);
  const isAuto    = !!mapNode.machine_verifiable;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(mapNode)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(mapNode)}
      style={{
        background:   isSelected ? "rgba(16,185,129,0.07)" : "rgba(10,16,28,0.75)",
        border:       isSelected ? "1px solid rgba(16,185,129,0.35)" : "1px solid rgba(255,255,255,0.065)",
        borderRadius: 8,
        padding:      "10px 12px",
        cursor:       "pointer",
        outline:      "none",
        animation:    `edv-map-card-in 0.32s ease both ${animDelay}ms`,
        transition:   "background 0.1s, border-color 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background    = "rgba(16,185,129,0.04)";
          e.currentTarget.style.borderColor   = "rgba(16,185,129,0.2)";
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background    = "rgba(10,16,28,0.75)";
          e.currentTarget.style.borderColor   = "rgba(255,255,255,0.065)";
        }
      }}
    >
      {/* Row 1: ID + AUTO badge */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 5, gap: 4 }}>
        <span style={{
          fontFamily: "monospace", fontSize: 9, fontWeight: 700,
          color: "#34d399", background: "rgba(52,211,153,0.07)",
          border: "1px solid rgba(52,211,153,0.14)",
          padding: "1px 5px", borderRadius: 3,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          maxWidth: "62%",
        }}>
          {mapNode.full_id || mapNode.id}
        </span>
        {isAuto && (
          <span style={{
            fontSize: 7.5, fontWeight: 800, color: "#34d399",
            background: "rgba(52,211,153,0.08)", border: "1px solid rgba(52,211,153,0.18)",
            padding: "1px 5px", borderRadius: 3, letterSpacing: 0.3, flexShrink: 0,
          }}>
            AUTO
          </span>
        )}
      </div>

      {/* Row 2: Title */}
      <div style={{
        fontSize: 11.5, fontWeight: 600, color: "#dde3ed", lineHeight: 1.4, marginBottom: 8,
        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
      }}>
        {mapNode.title || mapNode.label || mapNode.id}
      </div>

      {/* Row 3: Badges + Details */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
        <span style={{
          fontSize: 9, fontWeight: 700, padding: "1px 7px", borderRadius: 10,
          background: pm.bg, color: pm.text, border: `1px solid ${pm.border}`,
          display: "inline-flex", alignItems: "center", gap: 3, flexShrink: 0,
        }}>
          <span style={{ width: 4, height: 4, borderRadius: "50%", background: pm.dot, display: "inline-block" }} />
          {priority}
        </span>
        <span style={{
          fontSize: 9, fontWeight: 700, padding: "1px 7px", borderRadius: 10,
          background: `${sColor}14`, color: sColor, border: `1px solid ${sColor}30`, flexShrink: 0,
        }}>
          {String(compliance).replace(/_/g, " ")}
        </span>
        <div style={{ flex: 1 }} />
        {mapNode.full_id && (
          <button
            onClick={(e) => { e.stopPropagation(); onNavigate(mapNode.full_id); }}
            style={{
              fontSize: 8.5, fontWeight: 700, padding: "2px 7px",
              background: "rgba(56,189,248,0.07)", border: "1px solid rgba(56,189,248,0.18)",
              borderRadius: 4, color: "#38bdf8", cursor: "pointer",
              fontFamily: "inherit", flexShrink: 0,
              transition: "background 0.1s",
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(56,189,248,0.15)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(56,189,248,0.07)"; }}
          >
            Details →
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Main exported component ───────────────────────────────────────────────────
export default function ExecutiveDepartmentView({ graph, selectedId, onSelect, onNavigate }) {
  const { nodes } = graph ?? { nodes: [], edges: [] };

  // Trigger animation sequence after first paint
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    ensureCss();
    const t = requestAnimationFrame(() => setPhase(1));
    return () => cancelAnimationFrame(t);
  }, []);

  const { docNode, depts, totalMaps } = useMemo(() => buildData(nodes), [nodes]);
  const layout = useMemo(() => computeLayout(depts), [depts]);

  const [expandedDept, setExpandedDept] = useState(null);

  if (!nodes.length || !depts.length) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "#475569", fontSize: 13 }}>
        No regulatory flow data available.
      </div>
    );
  }

  const svgH       = DEPT_Y + DEPT_H + 36;
  const animated   = phase >= 1;

  // Document label
  const rawDocId = docNode?.label
    || (docNode?.id ?? "").replace("doc:", "")
    || "Source Document";
  const docLabel = rawDocId.length > 30 ? rawDocId.slice(0, 28) + "…" : rawDocId;

  const expandedData = layout.find((d) => d.name === expandedDept) ?? null;

  const handleDeptClick = (name) => {
    setExpandedDept((prev) => (prev === name ? null : name));
  };

  return (
    <div>
      {/* ── SVG Sankey canvas ──────────────────────────────────────────── */}
      <svg
        viewBox={`0 0 ${VW} ${svgH}`}
        width="100%"
        style={{ display: "block", overflow: "visible" }}
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Regulatory obligation flow from source document to departments"
      >
        <defs>
          {/* Glow filter for doc node */}
          <filter id="edv-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Soft shadow for dept nodes */}
          <filter id="edv-shadow" x="-15%" y="-15%" width="130%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="5" floodColor="#000" floodOpacity="0.4" />
          </filter>
          {/* Dept glow when selected */}
          <filter id="edv-dept-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ── 1. Document node ──────────────────────────────────────────── */}
        <g
          style={{
            animation: animated
              ? `edv-doc-in 0.48s cubic-bezier(0.2,0,0,1) ${T_DOC}ms both`
              : "none",
            transformBox:    "fill-box",
            transformOrigin: "center",
          }}
        >
          {/* Ambient glow ring */}
          <ellipse
            cx={DOC_CX}
            cy={DOC_Y + DOC_H / 2}
            rx={DOC_W / 2 + 12}
            ry={DOC_H / 2 + 8}
            fill="none"
            stroke="rgba(16,185,129,0.1)"
            strokeWidth={8}
            filter="url(#edv-glow)"
          />
          {/* Main rect */}
          <rect
            x={DOC_CX - DOC_W / 2}
            y={DOC_Y}
            width={DOC_W}
            height={DOC_H}
            rx={11}
            fill="rgba(15,23,42,0.92)"
            stroke="rgba(16,185,129,0.42)"
            strokeWidth={1.5}
          />
          {/* Left accent bar */}
          <rect
            x={DOC_CX - DOC_W / 2}
            y={DOC_Y + 10}
            width={3}
            height={DOC_H - 20}
            rx={1.5}
            fill="#10b981"
          />
          {/* Document icon */}
          <text
            x={DOC_CX - DOC_W / 2 + 22}
            y={DOC_Y + DOC_H / 2 + 6}
            fontSize={18}
            textAnchor="middle"
          >
            📄
          </text>
          {/* Label: SOURCE DOCUMENT */}
          <text
            x={DOC_CX + 8}
            y={DOC_Y + DOC_H / 2 - 8}
            fontSize={9}
            fontWeight={700}
            fill="#475569"
            letterSpacing={0.8}
            textAnchor="middle"
          >
            SOURCE DOCUMENT
          </text>
          {/* Doc ID */}
          <text
            x={DOC_CX + 8}
            y={DOC_Y + DOC_H / 2 + 9}
            fontSize={12}
            fontWeight={700}
            fill="#f1f5f9"
            textAnchor="middle"
          >
            {docLabel}
          </text>
          {/* MAP count badge */}
          <rect
            x={DOC_CX + DOC_W / 2 - 68}
            y={DOC_Y + DOC_H / 2 - 12}
            width={60}
            height={22}
            rx={5}
            fill="rgba(52,211,153,0.1)"
            stroke="rgba(52,211,153,0.25)"
            strokeWidth={1}
          />
          <text
            x={DOC_CX + DOC_W / 2 - 38}
            y={DOC_Y + DOC_H / 2 + 4}
            fontSize={10}
            fontWeight={800}
            fill="#34d399"
            textAnchor="middle"
          >
            {totalMaps} MAPs
          </text>
        </g>

        {/* ── 2. Distribution strip label ───────────────────────────────── */}
        <g
          style={{
            animation: animated
              ? `edv-strip-in 0.4s ease both ${T_STRIP}ms`
              : "none",
          }}
        >
          <text
            x={DOC_CX}
            y={MID_Y}
            textAnchor="middle"
            fontSize={9}
            fontWeight={700}
            fill="#1e3a2f"
            letterSpacing={1.2}
          >
            ── AI OBLIGATION DISTRIBUTION ──
          </text>
        </g>

        {/* ── 3. Sankey flow paths ──────────────────────────────────────── */}
        {layout.map((dept, i) => {
          // Stroke-width proportional to MAP count (min 2, max 22)
          const weight = dept.maps.length / Math.max(1, totalMaps);
          const sw     = Math.max(2.5, Math.round(weight * 22 * 10) / 10);
          // Opacity also scales with weight so thin paths are subtle
          const baseOp = 0.22 + weight * 0.52;
          const pathD  = sankeyPath(DOC_CX, DOC_BOT, dept.cx, DEPT_Y);
          const delay  = T_PATH + i * PATH_STRIDE;

          return (
            <path
              key={dept.name + "-p"}
              d={pathD}
              fill="none"
              stroke="#10b981"
              strokeWidth={sw}
              strokeLinecap="round"
              strokeDasharray="900"
              style={{
                opacity:   baseOp,
                animation: animated
                  ? `edv-path-in 0.62s cubic-bezier(0.4,0,0.2,1) ${delay}ms both`
                  : "none",
                transformBox: "fill-box",
              }}
            />
          );
        })}

        {/* ── 4. Department nodes ───────────────────────────────────────── */}
        {layout.map((dept, i) => {
          const isExpanded = expandedDept === dept.name;
          const topPKey    = normalizePriority(dept.maps[0]?.priority);
          const pm         = PRIORITY_META[topPKey] || PRIORITY_META.Medium;
          const autoCount  = dept.maps.filter((m) => m.machine_verifiable).length;
          const delay      = T_DEPT + i * DEPT_STRIDE;
          const { x, cx, dW } = dept;

          return (
            <g
              key={dept.name + "-n"}
              onClick={() => handleDeptClick(dept.name)}
              role="button"
              aria-label={`${dept.name} department — ${dept.maps.length} MAPs`}
              style={{
                cursor:          "pointer",
                animation:       animated ? `edv-dept-in 0.48s cubic-bezier(0.2,0,0,1) ${delay}ms both` : "none",
                transformBox:    "fill-box",
                transformOrigin: "center",
              }}
            >
              {/* Glow ring when expanded */}
              {isExpanded && (
                <rect
                  x={x - 4}
                  y={DEPT_Y - 4}
                  width={dW + 8}
                  height={DEPT_H + 8}
                  rx={14}
                  fill="none"
                  stroke="rgba(16,185,129,0.28)"
                  strokeWidth={2.5}
                  filter="url(#edv-dept-glow)"
                />
              )}

              {/* Card background */}
              <rect
                x={x}
                y={DEPT_Y}
                width={dW}
                height={DEPT_H}
                rx={10}
                fill={isExpanded ? "rgba(16,185,129,0.08)" : "rgba(20,30,46,0.94)"}
                stroke={isExpanded ? "rgba(16,185,129,0.45)" : "rgba(255,255,255,0.08)"}
                strokeWidth={1.5}
                filter="url(#edv-shadow)"
              />

              {/* Dept icon */}
              <text x={cx} y={DEPT_Y + 22} textAnchor="middle" fontSize={15}>
                🏢
              </text>

              {/* Dept name */}
              <text
                x={cx}
                y={DEPT_Y + 38}
                textAnchor="middle"
                fontSize={Math.max(9.5, Math.min(11, (dW / 13)))}
                fontWeight={700}
                fill={isExpanded ? "#34d399" : "#e2e8f0"}
              >
                {dept.name.length > Math.floor(dW / 8)
                  ? dept.name.slice(0, Math.floor(dW / 8) - 1) + "…"
                  : dept.name}
              </text>

              {/* MAP count · Auto count */}
              <text
                x={cx}
                y={DEPT_Y + 53}
                textAnchor="middle"
                fontSize={9}
                fill="#64748b"
                fontWeight={600}
              >
                {dept.maps.length} MAP{dept.maps.length !== 1 ? "s" : ""}
                {"  ·  "}
                {autoCount} Auto
              </text>

              {/* Priority pill */}
              <rect
                x={cx - 28}
                y={DEPT_Y + 60}
                width={56}
                height={18}
                rx={9}
                fill={pm.bg}
                stroke={pm.border}
                strokeWidth={1}
              />
              {/* Priority dot */}
              <circle cx={cx - 13} cy={DEPT_Y + 69} r={3} fill={pm.dot} />
              <text
                x={cx + 4}
                y={DEPT_Y + 73}
                textAnchor="middle"
                fontSize={9}
                fontWeight={800}
                fill={pm.text}
              >
                {topPKey}
              </text>

              {/* Expand chevron */}
              <text
                x={cx}
                y={DEPT_Y + DEPT_H - 6}
                textAnchor="middle"
                fontSize={8}
                fill={isExpanded ? "#34d399" : "#2d3a4a"}
                fontWeight={700}
              >
                {isExpanded ? "▲" : "▼"}
              </text>
            </g>
          );
        })}

        {/* ── 5. MAP count labels on paths ──────────────────────────────── */}
        {layout.map((dept, i) => {
          // Bezier midpoint at t=0.5 for this specific path shape
          // Since cp1x = srcX and cp2x = dstX, midpoint x = 0.5*(srcX + dstX)
          const mx    = (DOC_CX + dept.cx) / 2;
          // Approximate y at t=0.5 using control points
          const spanY = DEPT_Y - DOC_BOT;
          const cp1y  = DOC_BOT + spanY * CP_SRC_RATIO;
          const cp2y  = DEPT_Y  - spanY * CP_DST_RATIO;
          // Cubic bezier y at t=0.5
          const my    = 0.125 * DOC_BOT + 0.375 * cp1y + 0.375 * cp2y + 0.125 * DEPT_Y;
          const delay = T_LABEL + i * 60;

          return (
            <g
              key={dept.name + "-lbl"}
              style={{
                animation: animated ? `edv-label-in 0.3s ease both ${delay}ms` : "none",
                pointerEvents: "none",
              }}
            >
              <rect
                x={mx - 14}
                y={my - 10}
                width={28}
                height={18}
                rx={5}
                fill="rgba(10,17,30,0.88)"
                stroke="rgba(16,185,129,0.22)"
                strokeWidth={1}
              />
              <text
                x={mx}
                y={my + 4}
                textAnchor="middle"
                fontSize={9.5}
                fontWeight={800}
                fill="#34d399"
              >
                {dept.maps.length}
              </text>
            </g>
          );
        })}
      </svg>

      {/* ── Hint row ──────────────────────────────────────────────────────── */}
      <div style={{
        display: "flex", alignItems: "center", gap: 14,
        marginTop: 8, marginBottom: expandedData ? 8 : 0,
        fontSize: 10, color: "#2d3a4a", flexWrap: "wrap",
      }}>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 7, height: 7, borderRadius: 2, background: "#34d399", display: "inline-block" }} />
          AUTO — machine verifiable
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 14, height: 3, borderRadius: 2, background: "rgba(16,185,129,0.6)", display: "inline-block" }} />
          Path width ∝ MAP count
        </span>
        <span style={{ marginLeft: "auto", fontStyle: "italic", color: "#1e2a3a", fontSize: 9 }}>
          Click a department node to expand obligations · click a MAP card to inspect →
        </span>
      </div>

      {/* ── Expanded Department MAP panel ─────────────────────────────────── */}
      {expandedData && (
        <div
          key={expandedData.name}
          style={{
            marginTop: 10,
            background:   "rgba(12,19,30,0.88)",
            border:       "1px solid rgba(16,185,129,0.2)",
            borderRadius: 10,
            overflow:     "hidden",
            animation:    "edv-expand-in 0.35s cubic-bezier(0.2,0,0,1) both",
            transformOrigin: "top center",
          }}
        >
          {/* Header */}
          <div style={{
            display:      "flex",
            alignItems:   "center",
            gap:          10,
            padding:      "11px 16px",
            background:   "rgba(16,185,129,0.04)",
            borderBottom: "1px solid rgba(16,185,129,0.12)",
          }}>
            <span style={{ fontSize: 14 }}>🏢</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 11, fontWeight: 700, color: "#34d399",
                letterSpacing: 0.5, textTransform: "uppercase",
              }}>
                {expandedData.name}
              </div>
              <div style={{ fontSize: 9.5, color: "#475569", marginTop: 1 }}>
                {expandedData.maps.length} regulatory obligation{expandedData.maps.length !== 1 ? "s" : ""}
                {" · "}
                {expandedData.maps.filter((m) => m.machine_verifiable).length} machine-verifiable
                {" · click a card to inspect →"}
              </div>
            </div>
            <button
              onClick={() => setExpandedDept(null)}
              aria-label="Collapse department"
              style={{
                background:  "transparent",
                border:      "1px solid rgba(255,255,255,0.07)",
                borderRadius: 6,
                color:       "#475569",
                fontSize:    12,
                cursor:      "pointer",
                padding:     "3px 9px",
                lineHeight:  1.3,
                fontFamily:  "inherit",
                transition:  "color 0.1s, border-color 0.1s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = "#94a3b8"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.14)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = "#475569"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)"; }}
            >
              ✕ Collapse
            </button>
          </div>

          {/* MAP card grid */}
          <div style={{
            padding:             "12px",
            display:             "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(228px, 1fr))",
            gap:                 8,
          }}>
            {expandedData.maps.map((m, idx) => (
              <MapCard
                key={m.id}
                mapNode={m}
                isSelected={selectedId === m.id}
                onSelect={onSelect}
                onNavigate={onNavigate}
                animDelay={idx * 38}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
