import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ExecutiveDepartmentView, { USE_DEPARTMENT_CONTAINERS } from "./ExecutiveDepartmentView";

// ─── Constants ────────────────────────────────────────────────────────────────
const NODE_W  = 180;
const NODE_H  = 54;
const H_GAP   = 40;   
const V_GAP   = 100;   
const PAD     = 60;   

const LAYER_LABELS = ["Document", "MAPs", "Departments"];

const NODE_ICONS = {
  document: "📄",
  requirement: "📑",
  map: "🎯",
  department: "🏢",
  verification: "✔",
  capability: "⚙"
};

const DEFAULT_COLORS = {
  document:     "#3b82f6", // Blue
  requirement:  "#0ea5e9", // Light Blue
  map:          "#64748b", // Default (overridden by status)
  department:   "#a855f7", // Purple
  verification: "#64748b", // Default (overridden by status)
  capability:   "#06b6d4",
};

function getStatusColor(status) {
  if (!status) return null;
  const s = String(status).toLowerCase();
  if (s.includes("non-compliant") || s.includes("critical") || s.includes("high")) return "#ef4444"; // Red
  if (s.includes("pending") || s.includes("medium") || s.includes("in progress")) return "#facc15"; // Yellow
  if (s.includes("compliant") || s.includes("low") || s.includes("completed")) return "#10b981"; // Green
  return null;
}

function getNodeColor(node) {
  const statusColor = getStatusColor(node.status || node.complianceStatus || node.priority);
  if (statusColor && (node.type === "map" || node.type === "verification" || node.type === "requirement")) {
    return statusColor;
  }
  return n => n.color ?? DEFAULT_COLORS[n.type] ?? "#94a3b8";
}

function wrapText(text, maxChars) {
  const words = text.split(" ");
  const lines = [];
  let current = "";
  for (const word of words) {
    if ((current + word).length > maxChars) {
      if (current) lines.push(current.trim());
      current = word + " ";
    } else {
      current += word + " ";
    }
  }
  if (current) lines.push(current.trim());
  return lines.slice(0, 3); // Max 3 lines
}

// ─── Shape renderers ──────────────────────────────────────────────────────────
function NodeShape({ type, x, y, w, h, color, selected }) {
  const stroke      = selected ? "#ffffff" : color;
  const strokeWidth = selected ? 3.5 : 2;
  const fill        = selected ? `${color}44` : `${color}18`;

  return <rect x={x} y={y} width={w} height={h} rx={8} fill={fill} stroke={stroke} strokeWidth={strokeWidth} filter="url(#drop-shadow)" />;
}

// ─── Layout engine ────────────────────────────────────────────────────────────
function computeLayout(nodes, edges, expandedIds) {
  const childrenOf = {};
  const parentOf = {};
  
  for (const e of edges) {
    if (!childrenOf[e.source]) childrenOf[e.source] = [];
    childrenOf[e.source].push(e.target);
    if (!parentOf[e.target]) parentOf[e.target] = [];
    parentOf[e.target].push(e.source);
  }

  const visible = new Set();
  const rootNodes = [];
  
  for (const n of nodes) {
    if (n.layer === 0) { 
      visible.add(n.id); 
      rootNodes.push(n.id);
    } else {
      const parents = parentOf[n.id] || [];
      const hasExpandedParent = parents.some(p => expandedIds.has(p));
      if (hasExpandedParent) {
        visible.add(n.id);
      }
    }
  }

  const positions = {};
  nodes.forEach(n => {
    if (visible.has(n.id)) {
      positions[n.id] = { y: PAD + n.layer * (NODE_H + V_GAP), x: 0 };
    }
  });

  let nextLeafX = PAD;
  const assignedX = new Set();

  function assignX(nodeId) {
    if (assignedX.has(nodeId)) return positions[nodeId].x;
    
    const children = (childrenOf[nodeId] || []).filter(c => visible.has(c));
    
    if (children.length === 0 || !expandedIds.has(nodeId)) {
      positions[nodeId].x = nextLeafX;
      nextLeafX += NODE_W + H_GAP;
    } else {
      let sumX = 0;
      let count = 0;
      children.forEach(childId => {
        const childX = assignX(childId);
        sumX += childX;
        count++;
      });
      positions[nodeId].x = sumX / count;
      if (positions[nodeId].x < nextLeafX) {
        positions[nodeId].x = nextLeafX;
        nextLeafX += NODE_W + H_GAP;
      }
    }
    assignedX.add(nodeId);
    return positions[nodeId].x;
  }

  rootNodes.forEach(root => assignX(root));

  nodes.forEach(n => {
    if (visible.has(n.id) && !assignedX.has(n.id)) {
      assignX(n.id);
    }
  });

  const maxLayer  = Math.max(...nodes.filter(n => visible.has(n.id)).map(n => n.layer), 0);
  const svgWidth  = nextLeafX + PAD;
  const svgHeight = PAD + (maxLayer + 1) * (NODE_H + V_GAP) + PAD;

  return { positions, visible, svgWidth, svgHeight };
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function SessionKnowledgeGraph({ graph }) {
  const navigate = useNavigate();
  const { id: sessionId } = useParams();
  
  const [expandedIds, setExpandedIds] = useState(() => {
    const s = new Set();
    const docNode = graph?.nodes?.find((n) => n.layer === 0);
    if (docNode) s.add(docNode.id);
    return s;
  });
  const [selected, setSelected] = useState(null);
  
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  
  const gRef = useRef(null);
  const isPanning = useRef(false);
  const startDrag = useRef({ x: 0, y: 0 });
  const currentPan = useRef({ x: 0, y: 0 });

  const { nodes, edges } = graph ?? { nodes: [], edges: [] };

  const { positions, visible, svgWidth, svgHeight } = useMemo(
    () => computeLayout(nodes, edges, expandedIds),
    [nodes, edges, expandedIds]
  );

  const childrenOf = useMemo(() => {
    const map = {};
    for (const e of edges) (map[e.source] = map[e.source] ?? []).push(e.target);
    return map;
  }, [edges]);

  const parentOf = useMemo(() => {
    const map = {};
    for (const e of edges) (map[e.target] = map[e.target] ?? []).push(e.source);
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

  const onMouseDown = (e) => {
    if (e.target.closest("[data-node]")) return;
    isPanning.current = true;
    startDrag.current = { x: e.clientX, y: e.clientY };
    currentPan.current = { ...pan };
  };

  const onMouseMove = (e) => {
    if (!isPanning.current || !gRef.current) return;
    const dx = e.clientX - startDrag.current.x;
    const dy = e.clientY - startDrag.current.y;
    
    const newX = currentPan.current.x + dx;
    const newY = currentPan.current.y + dy;
    
    gRef.current.setAttribute("transform", `translate(${newX},${newY}) scale(${zoom})`);
  };

  const onMouseUp = (e) => {
    if (!isPanning.current) return;
    isPanning.current = false;
    
    const dx = e.clientX - startDrag.current.x;
    const dy = e.clientY - startDrag.current.y;
    
    setPan({ x: currentPan.current.x + dx, y: currentPan.current.y + dy });
  };

  const svgContainerRef = useRef(null);

  useEffect(() => {
    if (gRef.current) {
      gRef.current.setAttribute("transform", `translate(${pan.x},${pan.y}) scale(${zoom})`);
    }
  }, [zoom, pan]);

  const zoomIn  = useCallback(() => setZoom((z) => Math.min(3, z + 0.2)), []);
  const zoomOut = useCallback(() => setZoom((z) => Math.max(0.1, z - 0.2)), []);
  const reset   = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  const fitView = useCallback(() => {
    if (!svgContainerRef.current || svgWidth === 0) return;
    const { clientWidth, clientHeight } = svgContainerRef.current;
    const scaleX = clientWidth / svgWidth;
    const scaleY = clientHeight / svgHeight;
    const newScale = Math.min(scaleX, scaleY) * 0.95;
    const finalZoom = Math.max(0.1, Math.min(newScale, 1.2));
    
    setZoom(finalZoom);
    setPan({
      x: (clientWidth - (svgWidth * finalZoom)) / 2,
      y: (clientHeight - (svgHeight * finalZoom)) / 2
    });
  }, [svgWidth, svgHeight]);

  useEffect(() => {
    if (svgWidth > 0 && svgHeight > 0) fitView();
  }, [svgWidth, svgHeight, fitView]);

  useEffect(() => {
    const el = svgContainerRef.current;
    if (!el) return;
    const handleWheel = (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      const scale = e.ctrlKey ? -e.deltaY * 0.01 : delta; // Handle pinch vs scroll
      setZoom(z => Math.min(Math.max(0.1, z + scale), 3));
    };
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, []);

  if (!nodes.length) return (
    <div style={{ padding: 40, textAlign: "center", color: "#475569", fontSize: 13 }}>
      No graph data available.
    </div>
  );

  // ── Executive Department View (feature-flagged) ─────────────────────────────
  // When USE_DEPARTMENT_CONTAINERS is true, the left canvas area is replaced with
  // the structured department containers. The right-side details panel (selectedNode
  // inspection, AI traceability, navigation button) is UNCHANGED in both modes.
  const handleDeptViewSelect = useCallback((mapNode) => {
    setSelected(mapNode.id);
  }, []);

  const handleDeptViewNavigate = useCallback((mapId) => {
    navigate(
      sessionId
        ? `/session/${encodeURIComponent(sessionId)}/map/${encodeURIComponent(mapId)}`
        : `/maps/${encodeURIComponent(mapId)}`
    );
  }, [navigate, sessionId]);


  return (
    <div className="card" style={{ padding: 18, marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", letterSpacing: 0.6, textTransform: "uppercase" }}>
            {USE_DEPARTMENT_CONTAINERS ? "Executive Department View" : "Session Knowledge Graph"}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>
            {USE_DEPARTMENT_CONTAINERS
              ? `${nodes.filter(n => n.type === "map").length} MAPs across ${nodes.filter(n => n.type === "department").length} departments`
              : `${visible.size} nodes visible · Document → MAPs → Departments`
            }
          </div>
        </div>
        {/* SVG controls shown only in legacy mode */}
        {!USE_DEPARTMENT_CONTAINERS && (
          <div style={{ display: "flex", gap: 6 }}>
            {[["−", zoomOut], ["+", zoomIn], ["Fit View", fitView], ["Reset", reset]].map(([lbl, fn]) => (
              <button key={lbl} onClick={fn}
                style={{ background: "#162030", border: "1.5px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "5px 10px", color: "#94a3b8", cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                {lbl}
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: USE_DEPARTMENT_CONTAINERS ? "1fr 280px" : "1fr 280px", gap: 18 }}>
        {/* ── Canvas area: switches between Executive View and legacy SVG ──── */}
        {USE_DEPARTMENT_CONTAINERS ? (
          // ── NEW: Executive Department View ──────────────────────────────────
          <div style={{ overflow: "auto", borderRadius: 10, background: "rgba(10,16,28,0.55)", border: "1px solid rgba(255,255,255,0.055)", padding: "16px" }}>
            <ExecutiveDepartmentView
              graph={graph}
              selectedId={selected}
              onSelect={handleDeptViewSelect}
              onNavigate={handleDeptViewNavigate}
            />
          </div>
        ) : (
          // ── LEGACY: Original SVG renderer (kept intact as fallback) ─────────
          <div ref={svgContainerRef} style={{ overflow: "hidden", borderRadius: 10, background: "linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.97))", border: "1px solid rgba(255,255,255,0.06)", cursor: isPanning.current ? "grabbing" : "grab", userSelect: "none", height: "calc(100vh - 250px)", minHeight: 500, maxHeight: 800 }}
            onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}>
            <svg
              width="100%" height="100%"
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              style={{ display: "block" }}
            >
              <defs>
                <filter id="drop-shadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#000000" floodOpacity="0.4"/>
                </filter>
              </defs>
              <g ref={gRef}>
                {LAYER_LABELS.map((lbl, layer) => {
                  const hasVisible = nodes.some((n) => n.layer === layer && visible.has(n.id));
                  if (!hasVisible) return null;
                  return (
                    <text key={layer}
                      x={12} y={PAD + layer * (NODE_H + V_GAP) + NODE_H / 2 + 4}
                      fontSize={11} fill="rgba(148,163,184,0.3)" fontWeight={800} letterSpacing={1}>
                      {lbl.toUpperCase()}
                    </text>
                  );
                })}

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
                        fill="none" stroke="rgba(96,165,250,0.25)" strokeWidth={2.5} />
                      <polygon
                        points={`${tx},${ty} ${tx - 5},${ty - 8} ${tx + 5},${ty - 8}`}
                        fill="rgba(96,165,250,0.4)" />
                    </g>
                  );
                })}

                {nodes.map((n) => {
                  if (!visible.has(n.id)) return null;
                  const pos = positions[n.id];
                  if (!pos) return null;
                  const { x, y } = pos;
                  const isSelected  = selected === n.id;
                  const isExpanded  = expandedIds.has(n.id);
                  const hasChildren = (childrenOf[n.id]?.length ?? 0) > 0;
                  
                  let explicitColor = getNodeColor(n);
                  if (typeof explicitColor === 'function') explicitColor = explicitColor(n);
                  const color = explicitColor;
                  
                  const labelText = String(n.label ?? n.title ?? "");
                  const isNonCompliant = String(n.status || "").toLowerCase().includes("non-compliant");
                  const icon = isNonCompliant ? "⚠" : (NODE_ICONS[n.type] || "🔹");
                  
                  const wrappedLines = wrapText(labelText, 24);
                  
                  const textY = y + (NODE_H / 2) - ((wrappedLines.length - 1) * 6) + 3;

                  return (
                    <g key={n.id} data-node="1"
                      style={{ cursor: "pointer" }}
                      onClick={() => toggleExpand(n.id)}>
                      <NodeShape type={n.type} x={x} y={y} w={NODE_W} h={NODE_H} color={color} selected={isSelected} />
                      
                      <text x={x + 14} y={y + NODE_H / 2 + 5} fontSize={14}>{icon}</text>
                      
                      <text x={x + NODE_W / 2 + 8} y={textY}
                        textAnchor="middle" fontSize={10} fontWeight={600}
                        fill={isSelected ? "#ffffff" : "#f1f5f9"}
                        style={{ pointerEvents: "none" }}>
                        {wrappedLines.map((line, idx) => (
                          <tspan key={idx} x={x + NODE_W / 2 + 8} dy={idx === 0 ? 0 : 13}>{line}</tspan>
                        ))}
                      </text>

                      {n.req_badge && (
                        <g transform={`translate(${x + NODE_W / 2}, ${y - 10})`}>
                          <rect x="-40" y="0" width="80" height="16" rx="4" fill="rgba(167,139,250,0.15)" stroke="rgba(167,139,250,0.3)" />
                          <text x="0" y="11" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#c084fc">{n.req_badge}</text>
                        </g>
                      )}

                      {hasChildren && (
                        <g transform={`translate(${x + NODE_W - 14}, ${y + NODE_H - 10})`}>
                          <circle cx="0" cy="0" r="8" fill={color} opacity="0.9" />
                          <text x="0" y="3.5" textAnchor="middle" fontSize={11} fill="#0f172a" fontWeight="900" style={{ pointerEvents: "none" }}>
                            {isExpanded ? "−" : "+"}
                          </text>
                        </g>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
        )}

        {/* AI Analysis Panel */}
        <div>
          {selectedNode ? (
            <div style={{ background: "rgba(15,23,42,0.6)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 18 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
                <div style={{ fontSize: 22 }}>
                  {String(selectedNode.status || "").toLowerCase().includes("non-compliant") ? "⚠" : (NODE_ICONS[selectedNode.type] || "🔹")}
                </div>
                <div>
                  <div style={{ fontSize: 9.5, color: "#60a5fa", fontWeight: 800, letterSpacing: 1.2 }}>AI ANALYSIS</div>
                  <div style={{ fontSize: 13, color: "#f8fafc", fontWeight: 700, textTransform: "capitalize" }}>{selectedNode.type} Entity</div>
                </div>
              </div>

              <div style={{ background: "rgba(2,6,23,0.5)", borderRadius: 8, padding: 12, marginBottom: 16, borderLeft: `3px solid ${typeof getNodeColor(selectedNode) === 'function' ? getNodeColor(selectedNode)(selectedNode) : getNodeColor(selectedNode)}` }}>
                <div style={{ fontSize: 10, color: "#94a3b8", fontWeight: 700, marginBottom: 5 }}>About this node</div>
                <div style={{ fontSize: 11.5, color: "#e2e8f0", lineHeight: 1.5 }}>
                  This is a <strong>{selectedNode.type}</strong> entity from the compliance pipeline.
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {selectedNode.title && (
                  <div>
                    <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 3 }}>MAP TITLE</div>
                    <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 700, lineHeight: 1.4 }}>{selectedNode.title}</div>
                  </div>
                )}
                {selectedNode.control_description && (
                  <div>
                    <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 3 }}>BUSINESS DESCRIPTION</div>
                    <div style={{ fontSize: 12, color: "#e2e8f0", lineHeight: 1.4 }}>{selectedNode.control_description}</div>
                  </div>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {selectedNode.department && (
                    <div>
                      <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 3 }}>DEPARTMENT</div>
                      <div style={{ fontSize: 11.5, color: "#e2e8f0" }}>🏢 {selectedNode.department}</div>
                    </div>
                  )}
                  {selectedNode.priority && (
                    <div>
                      <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 3 }}>PRIORITY</div>
                      <span style={{ fontSize: 10.5, fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "rgba(255,255,255,0.05)", color: "#e2e8f0" }}>
                        {selectedNode.priority.toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
                {selectedNode.compliance_status && (
                  <div>
                    <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 3 }}>COMPLIANCE STATUS</div>
                    <span style={{ fontSize: 10.5, fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: `${getStatusColor(selectedNode.compliance_status)}33`, color: getStatusColor(selectedNode.compliance_status) || "#e2e8f0" }}>
                      {selectedNode.compliance_status.toUpperCase()}
                    </span>
                  </div>
                )}
                {selectedNode.verification_plan && (
                  <div style={{ background: "rgba(255,255,255,0.02)", padding: "10px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)", marginTop: 4 }}>
                    <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>VERIFICATION SUMMARY</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                      <span style={{ fontSize: 11.5, color: "#cbd5e1" }}>
                        Checks: <strong>{selectedNode.verification_plan.total_checks || selectedNode.verification_plan.checks?.length || 0}</strong>
                      </span>
                      <span style={{ fontSize: 9, fontWeight: 800, color: selectedNode.machine_verifiable ? "#34d399" : "#fbbf24", background: selectedNode.machine_verifiable ? "rgba(52,211,153,0.1)" : "rgba(251,191,36,0.1)", padding: "3px 6px", borderRadius: "4px" }}>
                        {selectedNode.machine_verifiable ? "MACHINE VERIFIABLE" : "MANUAL VERIFICATION"}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {(selectedNode.source_requirement_text || selectedNode.ai_rationale) && (
                <div style={{ marginTop: 16, paddingTop: 14, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                  <div style={{ fontSize: 9.5, color: "#a78bfa", fontWeight: 800, letterSpacing: 1.2, marginBottom: 10 }}>AI TRACEABILITY</div>
                  {selectedNode.source_requirement_text && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>SOURCE REQUIREMENT</div>
                      <div style={{ fontSize: 11, color: "#94a3b8", fontFamily: "monospace", padding: "10px", background: "rgba(15,23,42,0.4)", borderRadius: "6px", borderLeft: "2px solid #a78bfa" }}>
                        "{selectedNode.source_requirement_text}"
                      </div>
                    </div>
                  )}
                  {selectedNode.ai_rationale && (
                    <div>
                      <div style={{ fontSize: 9.5, color: "#64748b", fontWeight: 700, marginBottom: 4 }}>AI RATIONALE</div>
                      <div style={{ fontSize: 11.5, color: "#cbd5e1", lineHeight: 1.5 }}>
                        {selectedNode.ai_rationale}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {selectedNode.type === "map" && selectedNode.full_id && (
                <button 
                  onClick={() => navigate(sessionId ? `/session/${encodeURIComponent(sessionId)}/map/${encodeURIComponent(selectedNode.full_id)}` : `/maps/${encodeURIComponent(selectedNode.full_id)}`)}
                  style={{ width: "100%", marginTop: 16, padding: "10px", background: "#3b82f6", color: "#ffffff", border: "none", borderRadius: "6px", fontWeight: "700", cursor: "pointer", fontSize: 12, transition: "background 0.2s" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "#2563eb"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "#3b82f6"}
                >
                  View Full MAP Details
                </button>
              )}
            </div>
          ) : (
            <div style={{ padding: 20, background: "rgba(15,23,42,0.4)", borderRadius: 12, border: "1px dashed rgba(255,255,255,0.1)" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#e2e8f0", marginBottom: 8 }}>Interactive Decomposition</div>
              <div style={{ fontSize: 11.5, color: "#94a3b8", lineHeight: 1.6 }}>
                Click any node on the canvas to trace the AI's deterministic reasoning from the raw regulatory circular down to the operational capability level.
                <br /><br />
                <span style={{ color: "#64748b" }}><strong>+</strong> = Uncover dependencies</span><br />
                <span style={{ color: "#64748b" }}><strong>−</strong> = Collapse layer</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
