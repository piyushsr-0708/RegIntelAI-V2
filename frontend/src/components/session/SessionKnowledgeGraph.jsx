/**
 * SessionKnowledgeGraph.jsx — RegIntel AI V2
 * Hierarchical layered graph with progressive expansion.
 * Pure SVG — no cytoscape. No external library.
 *
 * Layout: top-down layers
 *   Layer 0: Document
 *   Layer 1: Requirements
 *   Layer 2: MAPs
 *   Layer 3: Departments
 *   Layer 4: Verification Plans
 *   Layer 5: Capabilities
 *
 * Node shapes (drawn as SVG primitives):
 *   document     → rect
 *   requirement  → roundrect
 *   map          → diamond
 *   department   → hexagon
 *   verification → parallelogram
 *   capability   → circle
 *
 * Progressive expansion:
 *   Initially only Layer 0 (Document) is visible.
 *   Clicking a node expands its direct children.
 *   Clicking again collapses them.
 */
import { useState, useMemo, useCallback, useRef } from "react";

// ─── Constants ────────────────────────────────────────────────────────────────
const NODE_W  = 90;
const NODE_H  = 32;
const H_GAP   = 18;   // horizontal gap between siblings
const V_GAP   = 70;   // vertical gap between layers
const PAD     = 40;   // canvas padding

const LAYER_LABELS = ["Document", "Requirements", "MAPs", "Departments", "Verification", "Capabilities"];

const NODE_COLORS = {
  document:     "#60a5fa",
  requirement:  "#a78bfa",
  map:          "#34d399",
  department:   "#f97316",
  verification: "#38bdf8",
  capability:   "#22d3ee",
};

const LEGEND = Object.entries(NODE_COLORS);

// ─── Shape renderers ──────────────────────────────────────────────────────────
function NodeShape({ type, x, y, w, h, color, selected }) {
  const stroke      = selected ? "#f1f5f9" : color;
  const strokeWidth = selected ? 2.5 : 1.5;
  const fill        = `${color}22`;

  switch (type) {
    case "document":
      return <rect x={x} y={y} width={w} height={h} rx={4} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    case "requirement":
      return <rect x={x} y={y} width={w} height={h} rx={10} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    case "map": {
      const cx = x + w / 2, cy = y + h / 2;
      const pts = `${cx},${y} ${x + w},${cy} ${cx},${y + h} ${x},${cy}`;
      return <polygon points={pts} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    case "department": {
      const cx = x + w / 2, cy = y + h / 2;
      const r  = Math.min(w, h) / 2;
      const pts = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
      }).join(" ");
      return <polygon points={pts} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    case "verification": {
      const skew = 8;
      const pts  = `${x + skew},${y} ${x + w},${y} ${x + w - skew},${y + h} ${x},${y + h}`;
      return <polygon points={pts} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    case "capability": {
      const cx = x + w / 2, cy = y + h / 2, r = Math.min(w, h) / 2;
      return <circle cx={cx} cy={cy} r={r} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
    }
    default:
      return <rect x={x} y={y} width={w} height={h} rx={4} fill={fill} stroke={stroke} strokeWidth={strokeWidth} />;
  }
}

// ─── Layout engine ────────────────────────────────────────────────────────────
/**
 * Compute (x, y) positions for all visible nodes.
 * Nodes are grouped by layer; each layer is centred horizontally.
 */
function computeLayout(nodes, edges, expandedIds) {
  // Determine which nodes are visible:
  // A node is visible if it is the document root OR its parent is expanded.
  const parentOf = {};
  for (const e of edges) {
    if (!parentOf[e.target]) parentOf[e.target] = e.source;
  }

  const visible = new Set();
  for (const n of nodes) {
    if (n.layer === 0) { visible.add(n.id); continue; }
    const parent = parentOf[n.id];
    if (parent && expandedIds.has(parent)) visible.add(n.id);
  }

  // Group visible nodes by layer
  const byLayer = {};
  for (const n of nodes) {
    if (!visible.has(n.id)) continue;
    (byLayer[n.layer] = byLayer[n.layer] ?? []).push(n);
  }

  const positions = {};
  let maxWidth = 0;

  for (const [layerStr, layerNodes] of Object.entries(byLayer)) {
    const layer    = Number(layerStr);
    const count    = layerNodes.length;
    const rowWidth = count * NODE_W + (count - 1) * H_GAP;
    maxWidth       = Math.max(maxWidth, rowWidth);

    layerNodes.forEach((n, i) => {
      positions[n.id] = {
        x: PAD + i * (NODE_W + H_GAP),
        y: PAD + layer * (NODE_H + V_GAP),
        rowWidth,
      };
    });
  }

  // Centre each layer
  for (const [layerStr, layerNodes] of Object.entries(byLayer)) {
    const rowWidth = layerNodes[0] ? positions[layerNodes[0].id].rowWidth : 0;
    const offset   = (maxWidth - rowWidth) / 2;
    for (const n of layerNodes) {
      positions[n.id].x += offset;
    }
  }

  const maxLayer  = Math.max(...Object.keys(byLayer).map(Number), 0);
  const svgWidth  = maxWidth + PAD * 2;
  const svgHeight = PAD + (maxLayer + 1) * (NODE_H + V_GAP) + PAD;

  return { positions, visible, svgWidth, svgHeight };
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SessionKnowledgeGraph({ graph }) {
  const [expandedIds, setExpandedIds] = useState(() => {
    // Start with document node expanded
    const s = new Set();
    const docNode = graph?.nodes?.find((n) => n.layer === 0);
    if (docNode) s.add(docNode.id);
    return s;
  });
  const [selected, setSelected] = useState(null);
  const [pan, setPan]           = useState({ x: 0, y: 0 });
  const [zoom, setZoom]         = useState(1);
  const svgRef                  = useRef(null);
  const isPanning               = useRef(false);
  const panStart                = useRef({ x: 0, y: 0 });

  const { nodes, edges } = graph ?? { nodes: [], edges: [] };

  const { positions, visible, svgWidth, svgHeight } = useMemo(
    () => computeLayout(nodes, edges, expandedIds),
    [nodes, edges, expandedIds]
  );

  // Children lookup
  const childrenOf = useMemo(() => {
    const map = {};
    for (const e of edges) (map[e.source] = map[e.source] ?? []).push(e.target);
    return map;
  }, [edges]);

  const toggleExpand = useCallback((nodeId) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId); else next.add(nodeId);
      return next;
    });
    setSelected(nodeId);
  }, []);

  const selectedNode = nodes.find((n) => n.id === selected) ?? null;

  // ── Pan handlers ────────────────────────────────────────────────────────────
  const onMouseDown = (e) => {
    if (e.target.closest("[data-node]")) return;
    isPanning.current = true;
    panStart.current  = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };
  const onMouseMove = (e) => {
    if (!isPanning.current) return;
    setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y });
  };
  const onMouseUp = () => { isPanning.current = false; };

  const zoomIn  = () => setZoom((z) => Math.min(2, z + 0.15));
  const zoomOut = () => setZoom((z) => Math.max(0.3, z - 0.15));
  const reset   = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  if (!nodes.length) return (
    <div style={{ padding: 40, textAlign: "center", color: "#475569", fontSize: 13 }}>
      No graph data available.
    </div>
  );

  return (
    <div className="card" style={{ padding: 18, marginBottom: 20 }}>
      {/* Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase" }}>
            Session Knowledge Graph
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>
            {visible.size} nodes visible · click a node to expand its children
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {[["−", zoomOut], ["+", zoomIn], ["Reset", reset]].map(([lbl, fn]) => (
            <button key={lbl} onClick={fn}
              style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#94a3b8", cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
              {lbl}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 14 }}>
        {/* SVG canvas */}
        <div style={{ overflow: "hidden", borderRadius: 10, background: "linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.97))", border: "1px solid rgba(255,255,255,0.06)", cursor: "grab", userSelect: "none" }}
          onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}>
          <svg
            ref={svgRef}
            width="100%" height={420}
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            style={{ display: "block" }}
          >
            <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
              {/* Layer labels */}
              {LAYER_LABELS.map((lbl, layer) => {
                const hasVisible = nodes.some((n) => n.layer === layer && visible.has(n.id));
                if (!hasVisible) return null;
                return (
                  <text key={layer}
                    x={8} y={PAD + layer * (NODE_H + V_GAP) + NODE_H / 2 + 4}
                    fontSize={8} fill="rgba(148,163,184,0.35)" fontWeight={700}>
                    {lbl.toUpperCase()}
                  </text>
                );
              })}

              {/* Edges — only between visible nodes */}
              {edges.map((e) => {
                if (!visible.has(e.source) || !visible.has(e.target)) return null;
                const s = positions[e.source];
                const t = positions[e.target];
                if (!s || !t) return null;
                const sx = s.x + NODE_W / 2, sy = s.y + NODE_H;
                const tx = t.x + NODE_W / 2, ty = t.y;
                const my = (sy + ty) / 2;
                return (
                  <g key={e.id}>
                    <path d={`M${sx},${sy} C${sx},${my} ${tx},${my} ${tx},${ty}`}
                      fill="none" stroke="rgba(96,165,250,0.2)" strokeWidth={1.2} />
                    <polygon
                      points={`${tx},${ty} ${tx - 4},${ty - 7} ${tx + 4},${ty - 7}`}
                      fill="rgba(96,165,250,0.3)" />
                  </g>
                );
              })}

              {/* Nodes */}
              {nodes.map((n) => {
                if (!visible.has(n.id)) return null;
                const pos = positions[n.id];
                if (!pos) return null;
                const { x, y } = pos;
                const isSelected  = selected === n.id;
                const isExpanded  = expandedIds.has(n.id);
                const hasChildren = (childrenOf[n.id]?.length ?? 0) > 0;
                const color       = n.color ?? NODE_COLORS[n.type] ?? "#94a3b8";

                return (
                  <g key={n.id} data-node="1"
                    style={{ cursor: "pointer" }}
                    onClick={() => toggleExpand(n.id)}>
                    <NodeShape type={n.type} x={x} y={y} w={NODE_W} h={NODE_H} color={color} selected={isSelected} />
                    {/* Label */}
                    <text x={x + NODE_W / 2} y={y + NODE_H / 2 + 4}
                      textAnchor="middle" fontSize={8.5} fontWeight={600}
                      fill={isSelected ? "#f1f5f9" : "#cbd5e1"}
                      style={{ pointerEvents: "none" }}>
                      {n.label.length > 12 ? n.label.slice(0, 11) + "…" : n.label}
                    </text>
                    {/* Expand indicator */}
                    {hasChildren && (
                      <text x={x + NODE_W - 6} y={y + 10}
                        fontSize={8} fill={color} fontWeight={900}
                        style={{ pointerEvents: "none" }}>
                        {isExpanded ? "−" : "+"}
                      </text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Side panel */}
        <div>
          {/* Legend */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>LEGEND</div>
            {LEGEND.map(([type, color]) => (
              <div key={type} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 5 }}>
                <div style={{ width: 10, height: 10, borderRadius: type === "capability" ? "50%" : 2, background: color, flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: "#94a3b8", textTransform: "capitalize" }}>{type}</span>
              </div>
            ))}
          </div>

          {/* Selected node detail */}
          {selectedNode ? (
            <div style={{ background: "rgba(15,23,42,0.5)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 9, padding: 12 }}>
              <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, marginBottom: 8, letterSpacing: 0.5 }}>SELECTED</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: selectedNode.color ?? "#f1f5f9", marginBottom: 8 }}>
                {selectedNode.label}
              </div>
              {[
                ["Type",       selectedNode.type],
                ["Layer",      LAYER_LABELS[selectedNode.layer] ?? selectedNode.layer],
                ["Children",   (childrenOf[selectedNode.id]?.length ?? 0).toString()],
                selectedNode.text       && ["Requirement", selectedNode.text.slice(0, 80) + (selectedNode.text.length > 80 ? "…" : "")],
                selectedNode.obligation && ["Obligation",  selectedNode.obligation],
                selectedNode.source_page && ["Source Page", `p.${selectedNode.source_page}`],
                selectedNode.confidence  && ["Confidence",  `${(selectedNode.confidence * 100).toFixed(0)}%`],
                selectedNode.priority    && ["Priority",    selectedNode.priority],
                selectedNode.checks      && ["Checks",      selectedNode.checks],
              ].filter(Boolean).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 5 }}>
                  <div style={{ fontSize: 9.5, color: "#475569", fontWeight: 700 }}>{k}</div>
                  <div style={{ fontSize: 11, color: "#e2e8f0", lineHeight: 1.4, wordBreak: "break-word" }}>{v}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 11, color: "#475569", lineHeight: 1.7 }}>
              Click any node to expand its children and inspect its details.<br /><br />
              <span style={{ color: "#64748b" }}>+ = has children · − = expanded</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
