/**
 * PipelineOrchestrator.js — RegIntel AI V2
 *
 * The single entry point for all pipeline execution.
 * No UI component calls a stage module directly — everything flows through here.
 *
 * Architecture:
 *   Pipeline.jsx → PipelineOrchestrator.run() → stage modules (in order)
 *                                              → onStageComplete callback (UI updates)
 *                                              → returns completed SessionData
 *
 * Each stage module exposes:
 *   run(input, rng?) → Promise<StageOutput>
 *
 * The orchestrator:
 *   1. Calls each stage in sequence, passing accumulated context.
 *   2. Fires onStageComplete(stageIndex, stageResult) after each stage.
 *   3. Animates stage duration via a configurable tick interval.
 *   4. Returns the final aggregated session data.
 *
 * Future integration:
 *   To connect a real offline stage, replace the import of the mock module
 *   with a module that calls the Python pipeline via a local IPC bridge
 *   (e.g. Tauri invoke, or a localhost-only HTTP server bundled with the app).
 *   The orchestrator interface does not change.
 */

import { seedRng, PIPELINE_STAGE_DEFS } from "./pipelineUtils.js";
import * as StageUpload       from "./stages/stageUpload.js";
import * as StageParser       from "./stages/stageParser.js";
import * as StageMetadata     from "./stages/stageMetadata.js";
import * as StageCleaning     from "./stages/stageCleaning.js";
import * as StageSegmentation from "./stages/stageSegmentation.js";
import * as StageExtraction   from "./stages/stageExtraction.js";
import * as StageMapGen       from "./stages/stageMapGeneration.js";
import * as StageDept         from "./stages/stageDeptAssignment.js";
import * as StagePriority     from "./stages/stagePriority.js";
import * as StageVerification from "./stages/stageVerification.js";
import * as StageGraph        from "./stages/stageGraphBuilder.js";
import * as StageDashboard    from "./stages/stageDashboardAggregator.js";

// ─── Stage registry — ordered, matches PIPELINE_STAGE_DEFS ───────────────────
// Each entry: { def (from PIPELINE_STAGE_DEFS), module (stage module) }
// The "completed" entry has no module — it is a terminal marker only.
const STAGE_REGISTRY = [
  { module: StageUpload       },  // 0  upload
  { module: StageParser       },  // 1  parsing
  { module: StageMetadata     },  // 2  metadata
  { module: StageCleaning     },  // 3  cleaning
  { module: StageSegmentation },  // 4  segmentation
  { module: StageExtraction   },  // 5  extraction
  { module: StageMapGen       },  // 6  map_generation
  { module: StageDept         },  // 7  dept_assignment
  { module: StagePriority     },  // 8  priority
  { module: StageVerification },  // 9  verification
  { module: StageGraph        },  // 10 graph
  { module: StageDashboard    },  // 11 dashboard
  { module: null              },  // 12 completed (terminal)
];

const TICK_MS = 50; // progress animation resolution

/**
 * PipelineOrchestrator.run(options)
 *
 * @param {File}     options.file               - The uploaded File object
 * @param {Array}    options.complianceRegister  - From FrontendStateContext
 * @param {Function} options.onStageStart(i)     - Called when stage i begins
 * @param {Function} options.onStageProgress(i, pct, elapsed_ms) - Called during stage
 * @param {Function} options.onStageComplete(i, result) - Called when stage i finishes
 * @returns {Promise<SessionData>}
 */
export async function run({ file, complianceRegister, onStageStart, onStageProgress, onStageComplete }) {
  const rng = seedRng(file.name);

  // Accumulated context — each stage reads from and writes to this object.
  // file is included so stageUpload can access it directly.
  let ctx = { file, complianceRegister };

  // Pre-compute all stage durations deterministically (same seed = same timings)
  const durations = PIPELINE_STAGE_DEFS.map((def) => {
    const jitter = 0.7 + rng() * 0.6;
    return Math.round(def.base_ms * jitter);
  });

  const stageResults = [];

  for (let i = 0; i < PIPELINE_STAGE_DEFS.length; i++) {
    const def    = PIPELINE_STAGE_DEFS[i];
    const entry  = STAGE_REGISTRY[i];
    const dur_ms = durations[i];

    onStageStart?.(i);

    // ── Run the stage module first, then animate concurrently ────────────
    // Both the stage execution and the animation timer run in parallel.
    // The animation resolves after dur_ms; the stage output is awaited after.
    const stageStart = Date.now();

    // Start stage execution immediately — pass current ctx and rng
    const stageOutputPromise = entry.module?.run
      ? entry.module.run(ctx, rng).catch((err) => {
          console.error(`[Pipeline] Stage ${def.id} threw:`, err);
          return {}; // degrade gracefully — never hang
        })
      : Promise.resolve({});

    // Animate progress for dur_ms
    await new Promise((resolve) => {
      const interval = setInterval(() => {
        const elapsed  = Date.now() - stageStart;
        const progress = Math.min(99, Math.round((elapsed / dur_ms) * 100));
        onStageProgress?.(i, progress, elapsed);
        if (elapsed >= dur_ms) { clearInterval(interval); resolve(); }
      }, TICK_MS);
    });

    // Await stage output (resolves instantly for all mock stages)
    const output = await stageOutputPromise;

    // Merge output into accumulated context
    ctx = { ...ctx, ...output };

    const stageRecord = {
      id:            def.id,
      label:         def.label,
      duration_ms:   dur_ms,
      records:       summariseOutput(def.id, ctx),
      records_label: def.records_label ?? "",
      status:        "completed",
    };

    stageResults.push(stageRecord);
    onStageProgress?.(i, 100, dur_ms);
    onStageComplete?.(i, stageRecord);
  }

  // Attach the stage records array to the aggregated session data.
  // stageDashboardAggregator runs as stage 11 and already built the session
  // object — we just stamp the stages list and processing_duration onto it here.
  const processing_duration = stageResults.reduce((s, st) => s + st.duration_ms, 0);
  return { ...ctx, stages: stageResults, processing_duration };
}

// ─── Human-readable output summary per stage ─────────────────────────────────
function summariseOutput(stageId, ctx) {
  switch (stageId) {
    case "upload":          return `${((ctx.file_size_bytes ?? 0) / 1024).toFixed(1)} KB`;
    case "parsing":         return `${ctx.pages ?? 0} pages`;
    case "metadata":        return `${ctx.fields_extracted ?? 0} fields`;
    case "cleaning":        return `${(ctx.tokens_cleaned ?? 0).toLocaleString()} tokens`;
    case "segmentation":    return `${ctx.logical_units_count ?? 0} segments`;
    case "extraction":      return `${ctx.requirements?.length ?? 0} requirements`;
    case "map_generation":  return `${ctx.maps?.length ?? 0} MAPs`;
    case "dept_assignment": return `${ctx.department_impact?.length ?? 0} departments`;
    case "priority":        return `${ctx.maps?.length ?? 0} priorities set`;
    case "verification":    return `${ctx.verification_plans?.length ?? 0} plans`;
    case "graph":           return `${ctx.graph?.nodes?.length ?? 0} nodes`;
    case "dashboard":       return `${ctx.maps?.length ?? 0} MAPs aggregated`;
    case "completed":       return `13 stages`;
    default:                return "—";
  }
}
