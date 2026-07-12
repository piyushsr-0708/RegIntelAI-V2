/**
 * stageExtraction.js — RegIntel AI V2 Pipeline Stage 6
 *
 * Interface:
 *   run(input, rng) → ExtractionOutput
 *
 * Input:  { document_id, segments, complianceRegister }
 * Output: { requirements[] }
 *
 * Each requirement:
 *   { req_id, text, obligation_type, source_segment, source_page,
 *     keywords[], confidence }
 *
 * Real integration: replace with pipeline/extractor/ output.
 * The requirement extractor already produces this schema.
 * complianceRegister is used here only to seed realistic requirement text
 * from existing data; the real extractor reads from parsed document text.
 */

const OBLIGATION_TYPES = ["SHALL", "MUST", "SHOULD", "MAY", "PROHIBITED"];

export async function run({ document_id, segments, complianceRegister }, rng) {
  const safeSegments = (segments && segments.length > 0) ? segments : [{ segment_id: "SEG_001" }];

  // Use real MAPs for this doc if available, else synthesise from register slice
  let sourceMaps = complianceRegister.filter((m) => m.document_id === document_id);
  if (sourceMaps.length === 0) {
    const offset = Math.floor(rng() * Math.max(0, complianceRegister.length - 80));
    const count  = 20 + Math.floor(rng() * 60);
    sourceMaps = complianceRegister.slice(offset, offset + count);
  }

  const requirements = sourceMaps.map((m, i) => ({
    req_id:          `${document_id}_req${i + 1}`,
    text:            m.title.replace(/^MAP:\s*/i, ""),
    obligation_type: OBLIGATION_TYPES[Math.floor(rng() * OBLIGATION_TYPES.length)],
    source_segment:  safeSegments[Math.floor(rng() * safeSegments.length)]?.segment_id ?? "SEG_001",
    source_page:     1 + Math.floor(rng() * Math.max(1, safeSegments.length * 3)),
    keywords:        m.business_capability ?? ["General"],
    confidence:      0.70 + rng() * 0.29,
    _source_map:     m,
  }));

  return { requirements };
}
