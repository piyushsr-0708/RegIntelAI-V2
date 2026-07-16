/**
 * SessionContext.jsx — RegIntel AI V2
 * Holds Analysis Sessions in React state only.
 * Sessions are created by the Pipeline page and consumed by SessionDashboard.
 * No backend. No file I/O. Sessions persist for the lifetime of the browser tab.
 */
import { createContext, useContext, useState, useCallback } from "react";

const SessionContext = createContext(null);

// ─── Persistence helpers ──────────────────────────────────────────────────────

/** Extract lightweight metadata for localStorage persistence. */
function extractMetadata(session) {
  return {
    session_id: session.session_id,
    filename: session.filename,
    document_id: session.document_id,
    upload_timestamp: session.upload_timestamp,
    status: session.status,
    processing_timestamp: session.processing_timestamp,
    processing_duration: session.processing_duration,
    pages: session.pages,
    words: session.words,
    requirements_found: session.requirements_found,
    maps_generated: session.maps_generated,
    departments_impacted: session.departments_impacted,
    knowledge_graph_nodes: session.knowledge_graph_nodes,
    knowledge_graph_edges: session.knowledge_graph_edges,
    automation_percentage: session.automation_percentage,
    overall_risk: session.overall_risk,
  };
}

/** Restore full session structure from lightweight metadata. */
function hydrateSession(metadata) {
  return {
    ...metadata,
    stages: [],
    maps: [],
    department_impact: [],
    verification_plans: [],
    graph: { nodes: [], edges: [] },
  };
}

/** Safely persist sessions to localStorage (lightweight metadata only). */
function persistSessions(sessions) {
  try {
    const metadata = sessions.map(extractMetadata);
    localStorage.setItem("sessions", JSON.stringify(metadata));
  } catch (err) {
    console.warn("[SessionContext] Failed to persist to localStorage:", err.message);
    // Continue without crashing
  }
}

export function SessionProvider({ children }) {
  const [sessions, setSessions] = useState(() => {
    try {
      const stored = localStorage.getItem("sessions");
      if (stored) {
        const metadata = JSON.parse(stored);
        return metadata.map(hydrateSession);
      }
      return [];
    } catch (err) {
      console.warn("[SessionContext] Failed to load from localStorage:", err.message);
      return [];
    }
  });

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
    setSessions((prev) => {
      const updated = [shell, ...prev];
      persistSessions(updated);
      return updated;
    });
    return session_id;
  }, []);

  /** Merge completed simulation data into an existing session. */
  const updateSession = useCallback((session_id, data) => {
    setSessions((prev) => {
      const updated = prev.map((s) => (s.session_id === session_id ? { ...s, ...data, status: "completed" } : s));
      persistSessions(updated);
      return updated;
    });
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
