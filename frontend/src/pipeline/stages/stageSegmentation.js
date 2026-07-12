/**
 * stageSegmentation.js — RegIntel AI V2 Pipeline Stage 5
 *
 * Interface:
 *   run(input, rng) → SegmentationOutput
 *
 * Input:  { pages, sections }
 * Output: { segments[], logical_units_count }
 *
 * Each segment: { segment_id, heading, page_start, page_end, word_count }
 *
 * Real integration: replace with pipeline/logical_units/ output.
 * The logical unit builder already produces this structure.
 */
export async function run({ pages, sections }, rng) {
  const count    = Math.max(sections ?? 1, 1); // guard: never 0
  const segments = Array.from({ length: count }, (_, i) => ({
    segment_id:  `SEG_${String(i + 1).padStart(3, "0")}`,
    heading:     `Section ${i + 1}`,
    page_start:  Math.floor((i / count) * pages) + 1,
    page_end:    Math.floor(((i + 1) / count) * pages),
    word_count:  200 + Math.floor(rng() * 400),
  }));

  return {
    segments,
    logical_units_count: count,
  };
}
