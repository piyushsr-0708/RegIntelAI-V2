/**
 * stageDeptAssignment.js — RegIntel AI V2 Pipeline Stage 8
 *
 * Interface:
 *   run(input) → DeptAssignmentOutput
 *
 * Input:  { maps }
 * Output: { maps, department_impact[] }
 *
 * Each department_impact:
 *   { department, map_count, critical, high, medium, low }
 *
 * Real integration: replace body with pipeline/derivation/ department
 * assignment logic. The derivation module already maps capability domains
 * to departments via the banking ontology matrix.
 */
export async function run({ maps }) {
  const depts = [...new Set(maps.map((m) => m.department))];

  const department_impact = depts.map((dept) => {
    const dm = maps.filter((m) => m.department === dept);
    return {
      department: dept,
      map_count:  dm.length,
      critical:   dm.filter((m) => m.priority === "CRITICAL").length,
      high:       dm.filter((m) => m.priority === "HIGH").length,
      medium:     dm.filter((m) => m.priority === "MEDIUM").length,
      low:        dm.filter((m) => m.priority === "LOW").length,
    };
  });

  return { maps, department_impact };
}
