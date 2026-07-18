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

  // Layer 0 — Document root (starts expanded to show requirements)
  const docId = `doc:${document_id ?? "unknown"}`;
  addNode(docId, document_id ?? "(unknown)", "document", { expanded: true, layer: 0 });

  // Layer 1 — Requirements (children of document)
  for (const req of requirements) {
    const rId = `req:${req.req_id}`;
    addNode(rId, req.req_id.slice(-8), "requirement", {
      layer: 1,
      full_id: req.req_id,
      text: req.text,
      obligation: req.obligation_type,
      source_page: req.source_page,
      confidence: req.confidence,
    });
    addEdge(docId, rId, "contains");
  }

  // Layer 2 — MAPs (children of requirements)
  for (const m of maps) {
    const mId  = `map:${m.map_id}`;
    const rId  = `req:${m.req_id}`;
    addNode(mId, String(m.map_id || "").slice(-12), "map", {
      layer: 2,
      full_id: m.map_id,
      title: m.title,
      priority: m.priority,
      department: m.department,
    });
    addEdge(rId, mId, "generates");
  }

  // Layer 3 — Departments (children of MAPs, deduplicated)
  const depts = [...new Set(maps.map((m) => m.department))];
  for (const dept of depts) {
    const dId = `dept:${dept}`;
    addNode(dId, dept, "department", { layer: 3 });
  }
  for (const m of maps) {
    addEdge(`map:${m.map_id}`, `dept:${m.department}`, "assigned to");
  }

  // Layer 4 — Verification Plans (children of MAPs)
  for (const vp of safePlans) {
    const vId = `vp:${vp.plan_id}`;
    addNode(vId, String(vp.plan_id || "").slice(-10), "verification", {
      layer: 4,
      checks: vp.checks,
      machine_verifiable: vp.machine_verifiable,
    });
    addEdge(`map:${vp.map_id}`, vId, "verified by");
  }

  // Layer 5 — Capabilities (children of MAPs, deduplicated)
  const caps = [...new Set(maps.flatMap((m) => m.business_capability ?? []))];
  for (const cap of caps) {
    const cId = `cap:${cap}`;
    addNode(cId, cap, "capability", { layer: 5 });
  }
  for (const m of maps) {
    for (const cap of (m.business_capability ?? []).slice(0, 1)) {
      addEdge(`map:${m.map_id}`, `cap:${cap}`, "capability");
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
