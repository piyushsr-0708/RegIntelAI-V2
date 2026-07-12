/**
 * pipelineUtils.js — RegIntel AI V2
 * Shared utilities for all pipeline stage modules.
 * No external dependencies. No API calls.
 */

/**
 * seedRng(seed)
 * Returns a deterministic pseudo-random number generator (xorshift32).
 * Same seed always produces the same sequence — essential for reproducible sessions.
 *
 * Real integration: replace with a server-side PRNG or remove entirely when
 * stages produce real outputs from actual document content.
 */
export function seedRng(seed) {
  let h = 0x811c9dc5;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = (Math.imul(h, 0x01000193)) >>> 0;
  }
  let state = h || 1;
  return () => {
    state ^= state << 13;
    state ^= state >> 17;
    state ^= state << 5;
    state = state >>> 0;
    return state / 0xffffffff;
  };
}

/**
 * deriveDocumentId(filename)
 * Converts a filename to a canonical document_id.
 * "MD 10190 (Final).pdf" → "MD_10190__FINAL_"
 *
 * Real integration: the actual document_id will come from the parser's
 * metadata extraction (header, RBI circular number, etc.).
 */
export function deriveDocumentId(filename) {
  return filename.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_").toUpperCase();
}

/**
 * PIPELINE_STAGE_DEFS
 * Canonical ordered list of all pipeline stages.
 * Used by the orchestrator and the UI stage list.
 * Each entry defines the stage id, display label, and base animation duration.
 */
export const PIPELINE_STAGE_DEFS = [
  { id: "upload",          label: "Upload",                       base_ms: 400  },
  { id: "parsing",         label: "Parsing",                      base_ms: 1200 },
  { id: "metadata",        label: "Metadata Extraction",          base_ms: 600  },
  { id: "cleaning",        label: "Text Cleaning",                base_ms: 900  },
  { id: "segmentation",    label: "Document Segmentation",        base_ms: 1100 },
  { id: "extraction",      label: "Requirement Extraction",       base_ms: 1800 },
  { id: "map_generation",  label: "MAP Generation",               base_ms: 2200 },
  { id: "dept_assignment", label: "Department Assignment",        base_ms: 700  },
  { id: "priority",        label: "Priority Classification",      base_ms: 600  },
  { id: "verification",    label: "Verification Plan Generation", base_ms: 1500 },
  { id: "graph",           label: "Knowledge Graph Construction", base_ms: 1000 },
  { id: "dashboard",       label: "Dashboard Aggregation",        base_ms: 500  },
  { id: "completed",       label: "Completed",                    base_ms: 200  },
];
