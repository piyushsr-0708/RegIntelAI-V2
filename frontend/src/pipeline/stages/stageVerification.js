/**
 * stageVerification.js — RegIntel AI V2 Pipeline Stage 10
 *
 * Interface:
 *   run(input, rng) → VerificationOutput
 *
 * Input:  { maps }
 * Output: { verification_plans[] }
 *
 * Each plan:
 *   { plan_id, map_id, req_id, title, department, priority,
 *     checks, machine_verifiable, check_types[], status }
 *
 * Real integration: replace body with pipeline/verification_planner/ output.
 * The planner already generates SQL/CMD/API check specifications per MAP.
 */

const CHECK_TYPES = ["SQL_SELECT", "CMD_QUERY", "API_GET", "LOG_AUDIT", "MANUAL_REVIEW"];

export async function run({ maps }, rng) {
  const verification_plans = maps.slice(0, Math.min(maps.length, 30)).map((m) => {
    const checks      = 2 + Math.floor(rng() * 4);
    const auto        = (m.automation_percentage ?? 0) > 0;
    const check_types = Array.from({ length: checks }, () =>
      CHECK_TYPES[Math.floor(rng() * CHECK_TYPES.length)]
    );

    return {
      plan_id:           `VP_${m.map_id}`,
      map_id:            m.map_id,
      req_id:            m.req_id,
      title:             m.title,
      department:        m.department,
      priority:          m.priority,
      checks,
      check_types,
      machine_verifiable: auto,
      status:            "PENDING",
    };
  });

  return { verification_plans };
}
