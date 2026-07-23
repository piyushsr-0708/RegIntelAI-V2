/**
 * stageGraphBuilder.js — RegIntel AI V2 Pipeline Stage 11
 *
 * Interface:
 *   run(input) → GraphOutput
 *
 * Input:  { document_id, requirements, maps, verification_plans }
 * Output: { graph: { nodes[], edges[] } }
 *
 * Node schema:
 *   { id, label, type, color, shape, expanded: false, children: [] }
 *
 * Node types and shapes:
 *   document    → rect
 *   requirement → roundrect
 *   map         → diamond
 *   department  → hexagon
 *   verification→ parallelogram
 *   capability  → circle
 *   priority    → octagon
 *
 * The graph is built as a tree rooted at the document node.
 * Only the document node is expanded by default — all children start collapsed.
 * The SessionKnowledgeGraph component drives progressive expansion from this data.
 *
 * Real integration: replace body with pipeline/map_generator/knowledge_graph.py output.
 */

const NODE_COLORS = {
  document:     "#60a5fa",
  requirement:  "#a78bfa",
  map:          "#34d399",
  department:   "#f97316",
  verification: "#38bdf8",
  capability:   "#22d3ee",
  priority:     "#fbbf24",
};

export async function run({ document_id, requirements, maps, verification_plans }) {
  const safePlans = verification_plans ?? [];
  const nodes = [];
  const edges = [];
  const seen  = new Set();

  const addNode = (id, label, type, extra = {}) => {
    if (seen.has(id)) return;
    seen.add(id);
    nodes.push({
      id, label, type,
      color:    NODE_COLORS[type] ?? "#94a3b8",
      shape:    "rect",
      expanded: false,
      ...extra,
    });
  };

  const addEdge = (source, target, label) => {
    const eid = `${source}__${target}`;
    if (seen.has(eid)) return;
    seen.add(eid);
    edges.push({ id: eid, source, target, label });
  };

  // Layer 0 — Document root (starts expanded to show MAPs)
  const docId = `doc:${document_id ?? "unknown"}`;
  addNode(docId, document_id ?? "(unknown)", "document", { expanded: true, layer: 0 });

  // Layer 1 — MAPs (children of document)
  for (const m of maps) {
    const mId  = `map:${m.map_id}`;
    
    // Find associated verification plan
    const vp = safePlans.find(p => String(p.map_id) === String(m.map_id));
    
    const reqBadgeId = m.req_id || m.source_requirement_id;
    const reqBadge = reqBadgeId ? `Req-${String(reqBadgeId).slice(-4)}` : (m.source_requirement_text ? "Requirement" : "");
    
    addNode(mId, String(m.map_id || "").slice(-12), "map", {
      layer: 1,
      full_id: m.map_id,
      title: m.title,
      priority: m.priority,
      department: m.department,
      compliance_status: m.compliance_status || m.status,
      control_description: m.control_description || m.control_objective || "",
      source_requirement_text: m.source_requirement_text || "",
      ai_rationale: m.ai_rationale || "",
      req_badge: reqBadge,
      verification_plan: vp,
      machine_verifiable: (m.automation_percentage > 0) || (m.automation_percent > 0) || m.machine_verifiable === true || m.is_machine_verifiable === true || (vp ? (vp.machine_verifiable_checks > 0 || (vp.automation_percentage && vp.automation_percentage > 0)) : false),
      automation_percentage: m.automation_percentage || m.automation_percent || 0
    });
    addEdge(docId, mId, "generates");
  }

  // Layer 2 — Departments (children of MAPs, deduplicated)
  const depts = [...new Set(maps.map((m) => m.department).filter(Boolean))];
  for (const dept of depts) {
    const dId = `dept:${dept}`;
    addNode(dId, dept, "department", { layer: 2 });
  }
  for (const m of maps) {
    if (m.department) {
      addEdge(`map:${m.map_id}`, `dept:${m.department}`, "assigned to");
    }
  }

  return { graph: { nodes, edges } };
}

const SHAPE_FOR = {
  document:     "rect",
  requirement:  "roundrect",
  map:          "diamond",
  department:   "hexagon",
  verification: "parallelogram",
  capability:   "circle",
  priority:     "octagon",
};
