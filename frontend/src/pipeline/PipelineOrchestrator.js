/**
 * PipelineOrchestrator.js — RegIntel AI V2
 *
 * Real upload workflow:
 *   1. POST /documents/upload  → receive document_id
 *   2. Poll GET /documents/{document_id}/status every 2 s
 *   3. Drive the progress UI via callbacks
 *   4. On completion, return { document_id, status: "completed" }
 *      so Pipeline.jsx can navigate to SessionDashboard.
 *
 * The simulated JS stage modules are no longer executed.
 */

import { PIPELINE_STAGE_DEFS } from "./pipelineUtils.js";

const API_BASE_URL = "http://localhost:8000";
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS  = 30 * 60 * 1000; // 30 minutes

// Map backend stage keys to the frontend stage index (0-based, matches PIPELINE_STAGE_DEFS)
const STAGE_KEY_TO_INDEX = {
  QUEUED:                         0,
  STARTING:                       0,
  PDF_PARSER:                     1,
  DOCUMENT_NORMALIZER:            2,
  HIERARCHY_BUILDER:              3,
  LOGICAL_UNIT_BUILDER:           4,
  REQUIREMENT_EXTRACTOR:          5,
  REQUIREMENT_ENRICHER:           6,
  COMPLIANCE_INTERPRETER:         7,
  COMPLIANCE_REASONING_ENGINE:    8,
  CONTROL_DERIVER:                9,
  VERIFICATION_RULE_GENERATOR:    9,
  VERIFICATION_PLANNER:           10,
  MAP_GENERATOR:                  11,
  DATABASE_INGEST:                11,
  DASHBOARD_AGGREGATOR:           12,
  COMPLETED:                      PIPELINE_STAGE_DEFS.length - 1,
};

/**
 * PipelineOrchestrator.run(options)
 *
 * @param {File}     options.file
 * @param {Function} options.onStageStart(i)
 * @param {Function} options.onStageProgress(i, pct, elapsed_ms)
 * @param {Function} options.onStageComplete(i, result)
 * @returns {Promise<{ document_id, status }>}
 * @throws  {Error} if upload fails
 */
export async function run({ file, onUploadComplete, onStageStart, onStageProgress, onStageComplete }) {
  const token = sessionStorage.getItem("regintel_jwt");
  if (!token) throw new Error("Not authenticated");

  // ── Stage 0: Upload ────────────────────────────────────────────────────────
  onStageStart?.(0);
  onStageProgress?.(0, 10, 0);

  const formData = new FormData();
  formData.append("file", file);

  const uploadStart = Date.now();
  const uploadRes = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!uploadRes.ok) {
    const err = await uploadRes.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || `Upload failed (${uploadRes.status})`);
  }

  const uploadData = await uploadRes.json();
  const document_id = uploadData.document_id;

  onStageProgress?.(0, 100, Date.now() - uploadStart);
  onStageComplete?.(0, { id: "upload", label: "Upload", status: "completed", records: `${(file.size / 1024).toFixed(1)} KB`, duration_ms: Date.now() - uploadStart });

  // Notify caller of the real document_id immediately after upload
  onUploadComplete?.(document_id);

  // If the backend already completed (duplicate), skip polling
  if (uploadData.status === "completed") {
    _markRemainingComplete(onStageStart, onStageProgress, onStageComplete, 1);
    return { document_id, status: "completed" };
  }

  // ── Poll status ────────────────────────────────────────────────────────────
  let lastStageIndex = 0;
  const pollStart = Date.now();

  return new Promise((resolve, reject) => {
    const interval = setInterval(async () => {
      // FIX 3: enforce 30-minute timeout
      if (Date.now() - pollStart > POLL_TIMEOUT_MS) {
        clearInterval(interval);
        reject(new Error("Pipeline timed out after 30 minutes"));
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/documents/${document_id}/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) return; // transient error — keep polling

        const statusData = await res.json();
        const { status, current_stage, progress } = statusData;

        const stageIndex = STAGE_KEY_TO_INDEX[current_stage] ?? lastStageIndex;
        const elapsed = Date.now() - pollStart;

        // Advance UI through any newly completed stages
        for (let i = lastStageIndex + 1; i <= stageIndex; i++) {
          onStageStart?.(i);
          onStageProgress?.(i, 100, elapsed);
          onStageComplete?.(i, {
            id: PIPELINE_STAGE_DEFS[i]?.id,
            label: PIPELINE_STAGE_DEFS[i]?.label,
            status: "completed",
            records: "—",
            duration_ms: 0,
          });
        }

        // Update progress on the current stage
        if (stageIndex >= lastStageIndex) {
          onStageProgress?.(stageIndex, Math.min(progress ?? 50, 99), elapsed);
        }

        lastStageIndex = Math.max(lastStageIndex, stageIndex);

        if (status === "completed") {
          clearInterval(interval);
          // Mark any remaining stages complete
          _markRemainingComplete(onStageStart, onStageProgress, onStageComplete, lastStageIndex + 1);
          resolve({ document_id, status: "completed" });
        } else if (status === "failed") {
          clearInterval(interval);
          reject(new Error(statusData.error || `Pipeline failed at ${current_stage}`));
        }
      } catch (e) {
        // Network hiccup — keep polling
        console.warn("[PipelineOrchestrator] Poll error (will retry):", e.message);
      }
    }, POLL_INTERVAL_MS);
  });
}

function _markRemainingComplete(onStageStart, onStageProgress, onStageComplete, fromIndex) {
  for (let i = fromIndex; i < PIPELINE_STAGE_DEFS.length; i++) {
    onStageStart?.(i);
    onStageProgress?.(i, 100, 0);
    onStageComplete?.(i, {
      id: PIPELINE_STAGE_DEFS[i]?.id,
      label: PIPELINE_STAGE_DEFS[i]?.label,
      status: "completed",
      records: "—",
      duration_ms: 0,
    });
  }
}
