/**
 * Graph.jsx — RegIntel AI V2
 * Milestone 1 stub: shows graph_data if available in FrontendStateContext.
 * Full Cytoscape implementation in Milestone 4 (requires Aggregator to output graph_data).
 */
import { useGraphData } from "../context/FrontendStateContext";
import Breadcrumbs from "../components/Breadcrumbs";

export default function Graph() {
  const graphData = useGraphData();
  const hasData = graphData.nodes.length > 0;

  const counts = {
    circular:    graphData.nodes.filter(n => n.data?.type === "circular").length,
    requirement: graphData.nodes.filter(n => n.data?.type === "requirement").length,
    map:         graphData.nodes.filter(n => n.data?.type === "map").length,
    department:  graphData.nodes.filter(n => n.data?.type === "department").length,
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
          Regulatory relationship network · Circulars → Requirements → MAPs → Departments
        </p>
      </div>

      {hasData ? (
        <div>
          {/* Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
            {[
              ["Circulars",    counts.circular,    "#60a5fa"],
              ["Requirements", counts.requirement, "#34d399"],
              ["MAPs",         counts.map,         "#fb923c"],
              ["Departments",  counts.department,  "#a78bfa"],
            ].map(([lbl, val, c]) => (
              <div key={lbl} className="card animate-fade-up" style={{ padding: "16px 18px", textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 900, color: c, lineHeight: 1 }}>{val.toLocaleString()}</div>
                <div style={{ fontSize: 11, color: "#64748b", marginTop: 5, fontWeight: 600 }}>{lbl}</div>
              </div>
            ))}
          </div>

          {/* Raw node list preview */}
          <div className="card" style={{ padding: 22 }}>
            <div style={{ fontWeight: 700, color: "#f1f5f9", fontSize: 14, marginBottom: 12 }}>Graph Nodes Preview ({graphData.nodes.length} nodes)</div>
            <div style={{ maxHeight: 320, overflowY: "auto" }}>
              {graphData.nodes.slice(0, 100).map((n, i) => (
                <div key={n.data?.id ?? i} style={{ display: "flex", gap: 10, padding: "6px 10px", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: 12, alignItems: "center" }}>
                  <span style={{ fontFamily: "monospace", fontSize: 10, color: "#60a5fa", minWidth: 80 }}>{n.data?.type}</span>
                  <span style={{ fontFamily: "monospace", fontSize: 10, color: "#34d399", minWidth: 120 }}>{n.data?.id}</span>
                  <span style={{ color: "#94a3b8" }}>{n.data?.label}</span>
                </div>
              ))}
              {graphData.nodes.length > 100 && <div style={{ padding: "10px", color: "#475569", fontSize: 11 }}>+ {graphData.nodes.length - 100} more nodes…</div>}
            </div>
          </div>
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "60px 40px" }}>
          <div style={{ fontSize: 44, marginBottom: 16 }}>🕸️</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#64748b", marginBottom: 8 }}>Knowledge Graph Not Yet Available</div>
          <div style={{ fontSize: 13, color: "#475569", maxWidth: 500, margin: "0 auto" }}>
            The Dashboard Aggregator must output a <code style={{ color: "#a78bfa" }}>graph_data</code> key in <code style={{ color: "#a78bfa" }}>frontend_state.json</code> with Cytoscape-compatible node and edge arrays.
          </div>
          <div style={{ marginTop: 20, padding: "16px 20px", background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.2)", borderRadius: 10, fontSize: 12, color: "#94a3b8", maxWidth: 500, margin: "20px auto 0", textAlign: "left" }}>
            <div style={{ fontWeight: 700, color: "#a78bfa", marginBottom: 8 }}>Required JSON shape:</div>
            <pre style={{ fontFamily: "monospace", fontSize: 11, lineHeight: 1.7 }}>{`"graph_data": {
  "nodes": [
    { "data": { "id": "DOC_001", "label": "...", "type": "circular" } }
  ],
  "edges": [
    { "data": { "source": "DOC_001", "target": "REQ_001", "label": "defines" } }
  ]
}`}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
