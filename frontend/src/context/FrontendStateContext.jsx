/**
 * FrontendStateContext.jsx
 * RegIntel AI V2 — Single Source of Truth for all frontend data.
 *
 * Architecture:
 * - Fetches /frontend_state.json ONCE on app load.
 * - The JSON is produced by the Dashboard Aggregator (Python backend pipeline).
 * - All pages read from this context — no API calls, no Axios, no websockets.
 * - Pages are responsible for filtering/deriving their own views from the raw state.
 *
 * Data shape (as produced by Dashboard Aggregator):
 * {
 *   metadata:          { generated_timestamp, pipeline_version, total_documents }
 *   executive_kpis:    { total_documents, total_maps, total_plans, total_checks,
 *                        compliant_documents, partially_compliant_documents,
 *                        non_compliant_documents, pending_documents, automation_percentage }
 *   department_summary: Array<{ department, total_maps, compliant, partial, non_compliant, pending }>
 *   compliance_register: Array<{ map_id, document_id, title, department, priority,
 *                                business_capability, compliance_status, decision_rationale,
 *                                failed_blocker_count, automation_percentage }>
 *   -- Future keys (added by Aggregator in later milestones) --
 *   detailed_maps?:      Dict<map_id, MapDetail>
 *   graph_data?:         { nodes: Node[], edges: Edge[] }
 *   requirements_taxonomy?: Requirement[]
 * }
 */

import { createContext, useContext, useState, useEffect } from 'react';

const FRONTEND_STATE_URL = '/frontend_state.json';

// ─── Context ───────────────────────────────────────────────────────────────────
const FrontendStateContext = createContext(null);

export function FrontendStateProvider({ children }) {
  const [state, setState]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadState() {
      try {
        const res = await fetch(FRONTEND_STATE_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`);
        const json = await res.json();
        if (!cancelled) {
          setState(json);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    }

    loadState();
    return () => { cancelled = true; };
  }, []);

  return (
    <FrontendStateContext.Provider value={{ state, loading, error }}>
      {children}
    </FrontendStateContext.Provider>
  );
}

/**
 * useFrontendState()
 * Hook that returns { state, loading, error }
 * state is null while loading.
 */
export function useFrontendState() {
  const ctx = useContext(FrontendStateContext);
  if (!ctx) throw new Error('useFrontendState must be used within <FrontendStateProvider>');
  return ctx;
}

/**
 * Convenience selectors — derived from the full state.
 * These avoid requiring every page to know the JSON schema.
 */
export function useExecutiveKpis() {
  const { state } = useFrontendState();
  return state?.executive_kpis ?? null;
}

export function useDepartmentSummary() {
  const { state } = useFrontendState();
  return state?.department_summary ?? [];
}

export function useComplianceRegister() {
  const { state } = useFrontendState();
  return state?.compliance_register ?? [];
}

export function useMapDetail(mapId) {
  const { state } = useFrontendState();
  return state?.detailed_maps?.[mapId] ?? null;
}

export function useGraphData() {
  const { state } = useFrontendState();
  return state?.graph_data ?? { nodes: [], edges: [] };
}

export function useRequirementsTaxonomy() {
  const { state } = useFrontendState();
  return state?.requirements_taxonomy ?? [];
}

export function useMetadata() {
  const { state } = useFrontendState();
  return state?.metadata ?? null;
}
