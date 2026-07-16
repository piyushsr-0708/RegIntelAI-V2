/**
 * stageParser.js — RegIntel AI V2 Pipeline Stage 2
 *
 * Interface:
 *   run(input, rng) → ParserOutput
 *
 * Input:  { filename, file_size_bytes, document_id }
 * Output: { pages, words, sections, raw_text_preview, parse_method }
 *
 * Note: Backend is processing the document in background.
 * This stage provides UI feedback only.
 */
export async function run({ file_size_bytes, document_id }, rng) {
  console.log("[stageParser] Backend processing document:", document_id);
  
  // Simulate minimal processing for UI feedback
  const pages    = 8 + Math.floor(rng() * 120);
  const words    = pages * (280 + Math.floor(rng() * 120));
  const sections = Math.ceil(pages / 4);

  return {
    pages,
    words,
    sections,
    raw_text_preview: `Document ${document_id} is being processed by the backend pipeline.`,
    parse_method:     "backend_pdf_parser",
  };
}
