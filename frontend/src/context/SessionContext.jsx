/**
 * SessionContext.jsx — RegIntel AI V2
 * Holds Analysis Sessions in React state only.
 * Sessions are created by the Pipeline page and consumed by SessionDashboard.
 * No backend. No file I/O. Sessions persist for the lifetime of the browser tab.
 */
import { createContext, useContext, useState, useCallback } from "react";

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [sessions, setSessions] = useState([]);

  /** Create a new session shell and return its id. */
  const createSession = useCallback((filename) => {
    const session_id = `SES-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
    const shell = {
      session_id,
      filename,
      document_id: deriveDocumentId(filename),
      upload_timestamp: new Date().toISOString(),
      status: "processing",
      // All numeric fields start null; filled by updateSession after simulation.
      processing_timestamp: null,
      processing_duration: null,
      pages: null,
      words: null,
      requirements_found: null,
      maps_generated: null,
      departments_impacted: null,
      knowledge_graph_nodes: null,
      knowledge_graph_edges: null,
      automation_percentage: null,
      overall_risk: null,
      stages: [],
      maps: [],
      department_impact: [],
      verification_plans: [],
      graph: { nodes: [], edges: [] },
    };
    setSessions((prev) => [shell, ...prev]);
    return session_id;
  }, []);

  /** Merge completed simulation data into an existing session. */
  const updateSession = useCallback((session_id, data) => {
    setSessions((prev) =>
      prev.map((s) => (s.session_id === session_id ? { ...s, ...data, status: "completed" } : s))
    );
  }, []);

  return (
    <SessionContext.Provider value={{ sessions, createSession, updateSession }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSessionContext() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSessionContext must be used within <SessionProvider>");
  return ctx;
}

/** Return a single session by id, or null. */
export function useSession(session_id) {
  const { sessions } = useSessionContext();
  return sessions.find((s) => s.session_id === session_id) ?? null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Derive a document_id from a filename (e.g. "MD10190.pdf" → "MD10190"). */
function deriveDocumentId(filename) {
  return filename.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_-]/g, "_").toUpperCase();
}
