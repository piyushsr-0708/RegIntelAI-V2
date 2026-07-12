/**
 * stageCleaning.js — RegIntel AI V2 Pipeline Stage 4
 *
 * Interface:
 *   run(input, rng) → CleaningOutput
 *
 * Input:  { words, pages }
 * Output: { tokens_cleaned, noise_removed, normalisation_passes }
 *
 * Real integration: replace with pipeline/normalizer/text_cleaner.py output.
 */
export async function run({ words, pages }, rng) {
  const noise = Math.floor(words * (0.02 + rng() * 0.05));
  return {
    tokens_cleaned:       words,
    noise_removed:        noise,
    normalisation_passes: 3,
  };
}
