/**
 * stageMapGeneration.js — RegIntel AI V2 Pipeline Stage 7
 *
 * Interface:
 *   run(input, rng) → MapGenerationOutput
 *
 * Input:  { document_id, requirements }
 * Output: { maps[] }
 *
 * Each MAP:
 *   { map_id, document_id, req_id, title, business_capability[],
 *     compliance_status, automation_percentage, failed_blocker_count,
 *     decision_rationale, _req_text, _source_page, _confidence }
 *
 * Real integration: replace with pipeline/map_generator/ output.
 * The MAP generator already produces this schema from reasoned controls.
 */
export async function run({ document_id, requirements }, rng) {
  const maps = requirements.map((req, i) => {
    const src = req._source_map ?? {};
    return {
      map_id:               src.map_id?.replace(src.document_id ?? "", document_id) ?? `MAP_${document_id}_req${i + 1}`,
      document_id,
      req_id:               req.req_id,
      title:                src.title ?? `MAP: ${req.text.slice(0, 60)}`,
      department:           src.department ?? "Compliance",
      priority:             src.priority ?? "MEDIUM",
      business_capability:  req.keywords,
      compliance_status:    src.compliance_status ?? "PENDING",
      automation_percentage: src.automation_percentage ?? 0,
      failed_blocker_count: src.failed_blocker_count ?? 0,
      decision_rationale:   src.decision_rationale ?? "No verification plan found.",
      // Session-only enrichment fields
      _req_text:    req.text,
      _source_page: req.source_page,
      _confidence:  req.confidence,
      _obligation:  req.obligation_type,
    };
  });

  return { maps };
}
