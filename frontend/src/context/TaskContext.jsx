/**
 * TaskContext.jsx — RegIntel AI V2
 * Offline task store. Tasks live in React state for the tab lifetime.
 * Created by Admin from approved session MAPs; consumed by department users.
 *
 * Task lifecycle:
 *   PENDING → IN_PROGRESS → COMPLETED
 *                         ↘ RETURNED (needs clarification)
 *   Any state → OVERDUE (computed, not stored)
 */
import { createContext, useContext, useState, useCallback } from "react";

const TaskContext = createContext(null);

// ─── Helpers ──────────────────────────────────────────────────────────────────
function makeTaskId() {
  return `TASK-${Date.now()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

function dueDateFromPriority(priority) {
  const days = { CRITICAL: 7, HIGH: 14, MEDIUM: 30, LOW: 60 };
  const d = new Date();
  d.setDate(d.getDate() + (days[priority] ?? 30));
  return d.toISOString().slice(0, 10);
}

export const TASK_STATUS = {
  PENDING:     "PENDING",
  IN_PROGRESS: "IN_PROGRESS",
  COMPLETED:   "COMPLETED",
  RETURNED:    "RETURNED",
};

// ─── Provider ─────────────────────────────────────────────────────────────────
export function TaskProvider({ children }) {
  const [tasks, setTasks] = useState([]);

  /**
   * generateTasksFromMaps(maps, sessionId, assignedBy)
   * Creates one Task per MAP per department assignment.
   * Returns the array of created task IDs.
   */
  const generateTasksFromMaps = useCallback((maps, sessionId, assignedBy) => {
    const created = [];
    const now = new Date().toISOString();

    maps.forEach((map) => {
      const task = {
        task_id:           makeTaskId(),
        session_id:        sessionId,
        map_id:            map.map_id,
        req_id:            map.req_id ?? null,
        document_id:       map.document_id,
        department:        map.department,
        priority:          map.priority,
        title:             map.title,
        description:       map._req_text ?? map.title,
        assigned_by:       assignedBy,
        assigned_to:       map.department,          // dept head receives it
        assigned_date:     now,
        due_date:          dueDateFromPriority(map.priority),
        evidence_required: true,
        evidence_uploaded: [],                       // array of { name, size, uploaded_at }
        status:            TASK_STATUS.PENDING,
        comments:          [],                       // array of { author, text, timestamp }
        completion_date:   null,
        // enrichment fields from MAP
        business_capability: map.business_capability ?? [],
        decision_rationale:  map.decision_rationale ?? null,
        automation_percentage: map.automation_percentage ?? 0,
        _req_text:           map._req_text ?? null,
        _source_page:        map._source_page ?? null,
        _confidence:         map._confidence ?? null,
        _obligation:         map._obligation ?? null,
      };
      created.push(task);
    });

    setTasks((prev) => [...prev, ...created]);
    return created.map((t) => t.task_id);
  }, []);

  /** Update task status */
  const updateTaskStatus = useCallback((task_id, status, comment, author) => {
    setTasks((prev) => prev.map((t) => {
      if (t.task_id !== task_id) return t;
      const now = new Date().toISOString();
      const newComments = comment
        ? [...t.comments, { author, text: comment, timestamp: now }]
        : t.comments;
      return {
        ...t,
        status,
        completion_date: status === TASK_STATUS.COMPLETED ? now : t.completion_date,
        comments: newComments,
      };
    }));
  }, []);

  /** Add a comment to a task */
  const addComment = useCallback((task_id, author, text) => {
    setTasks((prev) => prev.map((t) => {
      if (t.task_id !== task_id) return t;
      return {
        ...t,
        comments: [...t.comments, { author, text, timestamp: new Date().toISOString() }],
      };
    }));
  }, []);

  /** Attach evidence to a task */
  const uploadEvidence = useCallback((task_id, file) => {
    setTasks((prev) => prev.map((t) => {
      if (t.task_id !== task_id) return t;
      const ev = { name: file.name, size: file.size, uploaded_at: new Date().toISOString() };
      return {
        ...t,
        evidence_uploaded: [...t.evidence_uploaded, ev],
        status: t.status === TASK_STATUS.PENDING ? TASK_STATUS.IN_PROGRESS : t.status,
      };
    }));
  }, []);

  /** Tasks for a specific department */
  const getTasksByDept = useCallback((department) =>
    tasks.filter((t) => t.department === department), [tasks]);

  /** Tasks for a specific session */
  const getTasksBySession = useCallback((session_id) =>
    tasks.filter((t) => t.session_id === session_id), [tasks]);

  return (
    <TaskContext.Provider value={{
      tasks,
      generateTasksFromMaps,
      updateTaskStatus,
      addComment,
      uploadEvidence,
      getTasksByDept,
      getTasksBySession,
    }}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskContext() {
  const ctx = useContext(TaskContext);
  if (!ctx) throw new Error("useTaskContext must be used within <TaskProvider>");
  return ctx;
}

/** Compute whether a task is overdue (due_date < today and not completed) */
export function isOverdue(task) {
  if (task.status === TASK_STATUS.COMPLETED) return false;
  return new Date(task.due_date) < new Date();
}
