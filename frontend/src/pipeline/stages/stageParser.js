/**
 * stageParser.js — RegIntel AI V2 Pipeline Stage 2
 *
 * Interface:
 *   run(input, rng) → ParserOutput
 *
 * Input:  { filename, file_size_bytes, document_id }
 * Output: { pages, words, sections, raw_text_preview, parse_method }
 *
 * Real integration: replace body with a call to pipeline/parser/pdf_parser.py
 * via a local IPC bridge (e.g. window.__TAURI__ invoke, or a local HTTP server
 * on localhost that is part of the offline desktop bundle).
 * The Python parser already exists at pipeline/parser/ in this repository.
 */
export async function run({ file_size_bytes }, rng) {
  const pages    = 8 + Math.floor(rng() * 120);
  const words    = pages * (280 + Math.floor(rng() * 120));
  const sections = Math.ceil(pages / 4);

  return {
    pages,
    words,
    sections,
    raw_text_preview: `[Mock] Document parsed. ${pages} pages, ${words.toLocaleString()} words across ${sections} sections.`,
    parse_method:     "mock_pdf_parser_v1",
  };
}
