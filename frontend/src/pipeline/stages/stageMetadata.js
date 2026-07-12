/**
 * stageMetadata.js — RegIntel AI V2 Pipeline Stage 3
 *
 * Interface:
 *   run(input, rng) → MetadataOutput
 *
 * Input:  { document_id, filename, pages }
 * Output: { title, document_type, issuer, effective_date, circular_number,
 *           fields_extracted }
 *
 * Real integration: replace body with pipeline/normalizer/ output.
 * The normalizer already extracts RBI circular metadata from parsed text.
 */

const DOC_TYPES  = ["Master Direction", "Circular", "Notification", "Guidelines", "Framework"];
const ISSUERS    = ["Reserve Bank of India", "RBI Department of Regulation", "RBI Department of Supervision"];

export async function run({ document_id, filename }, rng) {
  const typeIdx   = Math.floor(rng() * DOC_TYPES.length);
  const issuerIdx = Math.floor(rng() * ISSUERS.length);
  const year      = 2018 + Math.floor(rng() * 7);
  const month     = 1   + Math.floor(rng() * 12);
  const day       = 1   + Math.floor(rng() * 28);

  const title = `${DOC_TYPES[typeIdx]} on ${document_id.replace(/_/g, " ")}`;

  return {
    title,
    document_type:   DOC_TYPES[typeIdx],
    issuer:          ISSUERS[issuerIdx],
    effective_date:  `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
    circular_number: `RBI/${year}/${document_id}`,
    fields_extracted: 12 + Math.floor(rng() * 8),
  };
}
