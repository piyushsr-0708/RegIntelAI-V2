import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { useComplianceRegister } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";

const GRAPH_SCOPE_LIMIT = 120;
const NODE_COLORS = {
  document: "#60a5fa",
  map: "#34d399",
  department: "#a78bfa",
  priority: "#fbbf24",
  status: "#fb923c",
};

function buildGraphData(records) {
  const scope = records.slice(0, GRAPH_SCOPE_LIMIT);
  const documentCounts = new Map();
  const departmentCounts = new Map();
  const priorityCounts = new Map();
  const statusCounts = new Map();

  scope.forEach((entry) => {
    const documentId = entry.document_id || "Unknown Document";
    const department = entry.department || "Unassigned";
    const priority = entry.priority || "Unknown";
    const status = entry.compliance_status || "Unknown";

    documentCounts.set(documentId, (documentCounts.get(documentId) || 0) + 1);
    departmentCounts.set(department, (departmentCounts.get(department) || 0) + 1);
    priorityCounts.set(priority, (priorityCounts.get(priority) || 0) + 1);
    statusCounts.set(status, (statusCounts.get(status) || 0) + 1);
  });

  const nodes = [];
  const edges = [];
  const seenNodes = new Set();
  const seenEdges = new Set();

  const addNode = (id, label, type, extra = {}) => {
    if (seenNodes.has(id)) return;
    seenNodes.add(id);
    nodes.push({
      data: {
        id,
        label,
        type,
        ...extra,
      },
    });
  };

  const addEdge = (source, target, label) => {
    if (!source || !target || source === target) return;
    const edgeId = `${source}-${target}-${label}`;
    if (seenEdges.has(edgeId)) return;
    seenEdges.add(edgeId);
    edges.push({
      data: {
        id: edgeId,
        source,
        target,
        label,
      },
    });
  };

  scope.forEach((entry, index) => {
    const documentId = entry.document_id || `Document ${index + 1}`;
    const mapId = entry.map_id || `map-${index + 1}`;
    const department = entry.department || "Unassigned";
    const priority = entry.priority || "Unknown";
    const status = entry.compliance_status || "Unknown";
    const documentKey = `document:${documentId}`;
    const mapKey = `map:${mapId}`;
    const departmentKey = `department:${department}`;
    const priorityKey = `priority:${priority}`;
    const statusKey = `status:${status}`;

    addNode(documentKey, `Document ${documentId}`, "document", {
      documentId,
      entryCount: documentCounts.get(documentId) || 1,
    });

    addNode(mapKey, `${mapId}`.length > 30 ? `${mapId.slice(0, 27)}…` : mapId, "map", {
      mapId,
      title: entry.title || "Untitled MAP",
      department,
      priority,
      complianceStatus: status,
      businessCapability: Array.isArray(entry.business_capability)
        ? entry.business_capability.join(", ")
        : entry.business_capability || "N/A",
      automationPercentage: entry.automation_percentage ?? null,
      documentId,
    });

    addNode(departmentKey, department, "department", {
      department,
      entryCount: departmentCounts.get(department) || 1,
    });

    addNode(priorityKey, priority, "priority", {
      priority,
      entryCount: priorityCounts.get(priority) || 1,
    });

    addNode(statusKey, status, "status", {
      complianceStatus: status,
      entryCount: statusCounts.get(status) || 1,
    });

    addEdge(documentKey, mapKey, "references");
    addEdge(mapKey, departmentKey, "assigned to");
    addEdge(mapKey, priorityKey, "priority");
    addEdge(mapKey, statusKey, "status");
  });

  return {
    nodes,
    edges,
    stats: {
      records: scope.length,
      documents: documentCounts.size,
      maps: scope.length,
      departments: departmentCounts.size,
      priorities: priorityCounts.size,
      statuses: statusCounts.size,
    },
  };
}

export default function Graph() {
  const records = useComplianceRegister();
  const graph = useMemo(() => buildGraphData(records), [records]);
  const graphContainerRef = useRef(null);
  const cyRef = useRef(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!graphContainerRef.current) return undefined;

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: graphContainerRef.current,
      elements: [...graph.nodes, ...graph.edges],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            width: 28,
            height: 28,
            "font-size": 10,
            "font-weight": 700,
            color: "#f8fafc",
            "text-valign": "center",
            "text-halign": "center",
            "border-width": 2,
            "border-color": "#0f172a",
            "background-color": (ele) => NODE_COLORS[ele.data("type")] || "#64748b",
            "background-opacity": 0.95,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": "rgba(96,165,250,0.3)",
            "target-arrow-color": "rgba(96,165,250,0.3)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: "#94a3b8",
            "text-rotation": "autorotate",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#34d399",
            "border-width": 3,
          },
        },
        {
          selector: "node.search-match",
          style: {
            "background-color": "#fbbf24",
            "border-color": "#f59e0b",
            "border-width": 3,
          },
        },
        {
          selector: "node.faded",
          style: {
            opacity: 0.22,
          },
        },
        {
          selector: "edge.highlighted",
          style: {
            width: 2.2,
            "line-color": "rgba(251, 191, 36, 0.75)",
            "target-arrow-color": "rgba(251, 191, 36, 0.75)",
          },
        },
        {
          selector: "edge.faded",
          style: {
            opacity: 0.2,
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        padding: 24,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 90,
      },
    });

    cyRef.current = cy;

    cy.on("tap", "node", (event) => {
      const nodeId = event.target.id();
      setSelectedNodeId(nodeId);
    });

    cy.on("tap", (event) => {
      if (event.target === cy) {
        setSelectedNodeId(null);
      }
    });

    cy.fit();
    if (graph.nodes.length > 0) {
      cy.zoom({ level: 0.9 });
      cy.center();
    }

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graph.nodes, graph.edges]);

  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;
    const term = searchTerm.trim().toLowerCase();

    cy.batch(() => {
      cy.elements().removeClass("search-match");
      cy.elements().removeClass("highlighted");
      cy.elements().removeClass("faded");
      cy.elements().removeClass("selected");

      if (!term) {
        if (selectedNodeId) {
          cy.getElementById(selectedNodeId).addClass("selected");
        }
        return;
      }

      const matchingNodes = cy.nodes().filter((node) => {
        const label = node.data("label") || "";
        const id = node.data("id") || "";
        return label.toLowerCase().includes(term) || id.toLowerCase().includes(term);
      });

      if (matchingNodes.length === 0) {
        cy.elements().addClass("faded");
        return;
      }

      matchingNodes.addClass("search-match");
      const relatedEdges = matchingNodes.edgesWith(cy.edges());
      relatedEdges.addClass("highlighted");
      cy.elements().difference(matchingNodes).difference(relatedEdges).addClass("faded");

      if (selectedNodeId) {
        cy.getElementById(selectedNodeId).addClass("selected");
      }
    });
  }, [searchTerm, selectedNodeId, graph.nodes.length]);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return graph.nodes.find((node) => node.data.id === selectedNodeId)?.data || null;
  }, [graph.nodes, selectedNodeId]);

  const metadataRows = selectedNode
    ? [
        ["Type", selectedNode.type || "—"],
        ["ID", selectedNode.id || "—"],
        ["Label", selectedNode.label || "—"],
        ["Entries", selectedNode.entryCount || "1"],
        ["Document", selectedNode.documentId || "—"],
        ["Department", selectedNode.department || "—"],
        ["Priority", selectedNode.priority || "—"],
        ["Compliance status", selectedNode.complianceStatus || "—"],
        ["Title", selectedNode.title || "—"],
        ["Capability", selectedNode.businessCapability || "—"],
        ["Automation", selectedNode.automationPercentage != null ? `${selectedNode.automationPercentage}%` : "—"],
      ]
    : [];

  const zoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
    }
  };

  const zoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const resetView = () => {
    if (cyRef.current) {
      cyRef.current.fit();
      cyRef.current.zoom({ level: 0.9 });
      cyRef.current.center();
    }
  };

  return (
    <div>
      <Breadcrumbs />
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
          <div style={{ width: 4, height: 28, borderRadius: 2, background: "linear-gradient(180deg,#a78bfa,#7c3aed)", boxShadow: "0 0 10px rgba(139,92,246,0.4)" }} />
          <h1 className="page-title">Knowledge Graph</h1>
        </div>
        <p className="page-subtitle" style={{ paddingLeft: 14 }}>
          Live relationship graph derived from the compliance register dataset.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2.1fr 0.9fr", gap: 18, alignItems: "start" }}>
        <div className="card" style={{ padding: 18, minHeight: 620 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#34d399", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Live graph view
              </div>
              <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 4 }}>
                Document → MAP → Department / Priority / Compliance status
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <input
                className="input-base"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search node"
                style={{ width: 180 }}
              />
              <button type="button" className="input-base" onClick={zoomOut} style={{ width: 38, padding: "9px 0", textAlign: "center", cursor: "pointer" }} aria-label="Zoom out">
                −
              </button>
              <button type="button" className="input-base" onClick={zoomIn} style={{ width: 38, padding: "9px 0", textAlign: "center", cursor: "pointer" }} aria-label="Zoom in">
                +
              </button>
              <button type="button" className="input-base" onClick={resetView} style={{ padding: "9px 12px", fontSize: 12, cursor: "pointer" }}>
                Reset
              </button>
            </div>
          </div>

          <div ref={graphContainerRef} style={{ width: "100%", height: 500, minHeight: 400, borderRadius: 12, overflow: "hidden", background: "linear-gradient(180deg, rgba(15,23,42,0.78) 0%, rgba(2,6,23,0.96) 100%)", border: "1px solid rgba(255,255,255,0.06)" }} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginTop: 14 }}>
            {[
              ["Records", graph.stats.records, "#60a5fa"],
              ["Documents", graph.stats.documents, "#34d399"],
              ["Departments", graph.stats.departments, "#a78bfa"],
              ["Statuses", graph.stats.statuses, "#fb923c"],
            ].map(([label, value, color]) => (
              <div key={label} style={{ padding: "12px 10px", borderRadius: 10, background: "rgba(15,23,42,0.54)", border: "1px solid rgba(255,255,255,0.05)" }}>
                <div style={{ fontSize: 20, fontWeight: 800, color }}>{value}</div>
                <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 18, minHeight: 620 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#34d399", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>
            Node details
          </div>
          {selectedNode ? (
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#f8fafc", marginBottom: 10 }}>{selectedNode.label}</div>
              <div style={{ display: "grid", gap: 8 }}>
                {metadataRows.map(([label, value]) => (
                  <div key={label} style={{ padding: "10px 12px", borderRadius: 10, background: "rgba(15,23,42,0.47)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 3 }}>{label}</div>
                    <div style={{ fontSize: 12, color: "#e2e8f0", lineHeight: 1.45 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: "#64748b", lineHeight: 1.65, fontSize: 13 }}>
              Click a node to inspect its document, department, priority, and compliance status metadata. Use the search field to highlight matching nodes and their relationships.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
