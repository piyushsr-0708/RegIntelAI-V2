/**
 * stageDashboardAggregator.js — RegIntel AI V2 Pipeline Stage 12
 *
 * Interface:
 *   run(input) → SessionData
 *
 * Input:  all prior stage outputs merged into one context object
 * Output: the complete session data object stored in SessionContext
 *
 * This stage mirrors the role of pipeline/aggregator/dashboard_aggregator.py
 * but operates on a single document session rather than the full corpus.
 *
 * Real integration: when the Python aggregator is extended to accept a
 * single document_id argument, this stage can invoke it via IPC and parse
 * the resulting JSON directly into the session — no UI changes required.
 */
export async function run(ctx) {
  const {
    document_id, filename, upload_timestamp,
    pages, words, sections,
    title, document_type, issuer, effective_date, circular_number,
    requirements,
    maps,
    department_impact,
    overall_risk, priority_distribution,
    verification_plans,
    graph,
  } = ctx;

  // stages is NOT available here — it is attached by the orchestrator after
  // all stages complete. Do not destructure or reference it in this module.

  const autoAvg = maps.reduce((s, m) => s + (m.automation_percentage ?? 0), 0) / Math.max(maps.length, 1);

  return {
    document_id,
    filename,
    upload_timestamp,
    pages,
    words,
    sections,
    title,
    document_type,
    issuer,
    effective_date,
    circular_number,
    requirements_found:    requirements.length,
    maps_generated:        maps.length,
    departments_impacted:  department_impact.length,
    knowledge_graph_nodes: graph.nodes.length,
    knowledge_graph_edges: graph.edges.length,
    automation_percentage: parseFloat(autoAvg.toFixed(1)),
    overall_risk,
    priority_distribution,
    requirements,
    maps,
    department_impact,
    verification_plans,
    graph,
    processing_timestamp: new Date().toISOString(),
    // processing_duration is computed by the orchestrator once stages are known
  };
}
