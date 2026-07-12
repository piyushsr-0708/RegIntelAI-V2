/**
 * stagePriority.js — RegIntel AI V2 Pipeline Stage 9
 *
 * Interface:
 *   run(input) → PriorityOutput
 *
 * Input:  { maps, department_impact }
 * Output: { maps, department_impact, overall_risk, priority_distribution }
 *
 * overall_risk: "HIGH" | "MEDIUM" | "LOW"
 * priority_distribution: { CRITICAL, HIGH, MEDIUM, LOW }
 *
 * Real integration: replace body with pipeline/reasoning/ priority engine.
 * The CRE already scores each control by regulatory intent and risk domain.
 */
export async function run({ maps, department_impact }) {
  const W = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
  const riskVal = maps.reduce((s, m) => s + (W[m.priority] ?? 1), 0) / Math.max(maps.length, 1);
  const overall_risk = riskVal >= 3 ? "HIGH" : riskVal >= 2 ? "MEDIUM" : "LOW";

  const priority_distribution = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const m of maps) if (m.priority in priority_distribution) priority_distribution[m.priority]++;

  return { maps, department_impact, overall_risk, priority_distribution };
}
