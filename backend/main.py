"""
main.py — RegIntel AI V2 Backend
FastAPI application with offline JWT authentication, RBAC, paginated endpoints.
Run: .venv/Scripts/python.exe -m uvicorn backend.main:app --port 8000 --reload
"""
import uvicorn
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.session import get_db
from backend.database.models import (
    User, Role, Department, ManagementActionPlan,
    ControlAssignment, AuditLog
)
from backend.database.services.assignment_service import AssignmentService
from backend.database.services.audit_service import AuditService
from backend.auth import (
    create_token, verify_password, get_current_user,
    require_permission, CurrentUser
)
from backend.permissions import Perm

app = FastAPI(title="RegIntel AI V2 Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _serialize_map(m: ManagementActionPlan) -> dict:
    return {
        "id": m.id,
        "control_id": m.control_id,
        "control_name": m.control.name if m.control else None,
        "control_objective": m.control.objective if m.control else None,
        "control_description": m.control.description if m.control else None,
        "department_id": m.department_id,
        "department_name": m.department.name if m.department else None,
        "status": m.status,
        "description": m.description,
        # Priority & metrics
        "priority": m.priority,
        "risk_score": m.risk_score,
        "automation_percent": m.automation_percent,
        # AI-generated content
        "ai_rationale": m.ai_rationale,
        "verification_plan": m.verification_plan,
        # Source provenance
        "source_document_id": m.source_document_id,
        "source_document_title": m.source_document_title,
        "source_requirement_id": m.source_requirement_id,
        "source_requirement_text": m.source_requirement_text,
        # Reviewer annotations
        "due_date": m.due_date.isoformat() if m.due_date else None,
        "comments": m.comments,
        "reject_reason": m.reject_reason,
        # Timestamps
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


def _serialize_assignment(a: ControlAssignment) -> dict:
    return {
        "id": a.id,
        "control_id": a.control_id,
        "control_name": a.control.name if a.control else None,
        "department_id": a.department_id,
        "department_name": a.department.name if hasattr(a, "department") and a.department else None,
        "map_id": a.map_id,
        "title": a.title,
        "priority": a.priority,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "comments": a.comments,
        "evidence_note": a.evidence_note,
        "status": a.status,
        "assigned_user_id": a.assigned_user_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_user(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name,
        "is_active": u.is_active,
        "role": u.role.role_name if u.role else None,
        "permissions": u.role.permissions if u.role else [],
        "department_id": u.department_id,
        "department_name": u.department.name if u.department else None,
    }


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class MapUpdateSchema(BaseModel):
    department_id: Optional[str] = None
    priority: Optional[str] = None
    verification_plan: Optional[str] = None
    due_date: Optional[str] = None          # ISO date string e.g. "2025-12-31"
    comments: Optional[str] = None
    reject_reason: Optional[str] = None
    status: Optional[str] = None

class MapRejectSchema(BaseModel):
    reason: Optional[str] = None

class AssignmentUpdateSchema(BaseModel):
    status: Optional[str] = None
    evidence_path: Optional[str] = None
    evidence_note: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/login", tags=["Auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=payload.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Support both hashed and legacy plain-text (for demo fallback)
    password_ok = False
    if user.password_hash:
        password_ok = verify_password(payload.password, user.password_hash)
    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role.role_name if user.role else None,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@app.get("/auth/me", tags=["Auth"])
def me(current: CurrentUser = Depends(get_current_user)):
    return {
        "id": current.id,
        "username": current.username,
        "role": current.role_name,
        "permissions": current.permissions,
        "department_id": current.department_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAP ENDPOINTS  — server-side pagination + filtering
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/maps", tags=["MAPs"])
def list_maps(
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, APPROVED"),
    department_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
    db: Session = Depends(get_db),
):
    # Department users only see their own dept's MAPs
    if current.department_id and not current.can(Perm.WILDCARD) and not current.can(Perm.MAP_APPROVE):
        department_id = current.department_id

    svc = AssignmentService(db)
    result = svc.get_maps(status=status, department_id=department_id, search=search, page=page, page_size=page_size)
    return {**result, "items": [_serialize_map(m) for m in result["items"]]}


@app.get("/maps/{map_id}", tags=["MAPs"])
def get_map(
    map_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
    db: Session = Depends(get_db),
):
    svc = AssignmentService(db)
    m = svc.get_map_by_id(map_id)
    if not m:
        raise HTTPException(status_code=404, detail="MAP not found")
    return _serialize_map(m)


@app.patch("/maps/{map_id}", tags=["MAPs"])
def update_map(
    map_id: str,
    payload: MapUpdateSchema,
    current: CurrentUser = Depends(require_permission(Perm.MAP_WRITE)),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    svc = AssignmentService(db)
    try:
        due_date_parsed = None
        if payload.due_date:
            try:
                due_date_parsed = datetime.fromisoformat(payload.due_date)
            except ValueError:
                pass
        updated = svc.update_map_metadata(
            map_id=map_id,
            department_id=payload.department_id,
            priority=payload.priority,
            verification_plan=payload.verification_plan,
            due_date=due_date_parsed,
            comments=payload.comments,
            reject_reason=payload.reject_reason,
            status=payload.status,
            actor_id=current.id,
        )
        return {"message": "MAP updated", "id": updated.id, "map": _serialize_map(updated)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/maps/{map_id}/approve", tags=["MAPs"])
def approve_map(
    map_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_APPROVE)),
    db: Session = Depends(get_db),
):
    svc = AssignmentService(db)
    try:
        action_plan, assignment = svc.approve_map(map_id, actor_id=current.id)
        return {
            "message": "MAP approved and assignment created",
            "map_id": action_plan.id,
            "assignment_id": assignment.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/maps/{map_id}/reject", tags=["MAPs"])
def reject_map(
    map_id: str,
    payload: Optional[MapRejectSchema] = None,
    current: CurrentUser = Depends(require_permission(Perm.MAP_APPROVE)),
    db: Session = Depends(get_db),
):
    svc = AssignmentService(db)
    try:
        action_plan = svc.reject_map(map_id, reject_reason=payload.reason if payload else None, actor_id=current.id)
        return {"message": "MAP rejected", "map_id": action_plan.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/maps/stats/summary", tags=["MAPs"])
def map_stats(
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
    db: Session = Depends(get_db),
):
    svc = AssignmentService(db)
    return svc.get_map_status_summary()


# ═══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/assignments", tags=["Assignments"])
def list_assignments(
    department_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_READ)),
    db: Session = Depends(get_db),
):
    # Department-scoped users only see their own assignments
    if current.department_id and not current.can(Perm.WILDCARD) and not current.can(Perm.DEPT_WRITE):
        department_id = current.department_id

    svc = AssignmentService(db)
    result = svc.get_assignments(department_id=department_id, status=status, search=search, page=page, page_size=page_size)
    return {**result, "items": [_serialize_assignment(a) for a in result["items"]]}


@app.patch("/assignments/{assignment_id}", tags=["Assignments"])
def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdateSchema,
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_COMPLETE)),
    db: Session = Depends(get_db),
):
    svc = AssignmentService(db)
    if payload.status == "COMPLETED":
        try:
            completed = svc.mark_assignment_complete(
                assignment_id,
                actor_id=current.id,
                evidence_note=payload.evidence_note,
            )
            return {"message": "Assignment completed", "id": completed.id}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    raise HTTPException(status_code=400, detail="Unsupported status")


@app.get("/assignments/stats/summary", tags=["Assignments"])
def assignment_stats(
    department_id: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_READ)),
    db: Session = Depends(get_db),
):
    if current.department_id and not current.can(Perm.WILDCARD):
        department_id = current.department_id
    svc = AssignmentService(db)
    return svc.get_assignment_status_summary(department_id=department_id)


# ═══════════════════════════════════════════════════════════════════════════════
# DEPARTMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/departments", tags=["Departments"])
def list_departments(
    current: CurrentUser = Depends(require_permission(Perm.DEPT_READ)),
    db: Session = Depends(get_db),
):
    depts = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "description": d.description} for d in depts]


# ═══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/users", tags=["Users"])
def list_users(
    current: CurrentUser = Depends(require_permission(Perm.USER_READ)),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    return [_serialize_user(u) for u in users]


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/audit", tags=["Audit"])
def recent_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    current: CurrentUser = Depends(require_permission(Perm.AUDIT_READ)),
    db: Session = Depends(get_db),
):
    svc = AuditService(db)
    logs = svc.get_recent(limit=limit)
    return [
        {
            "id": log.id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "action": log.action,
            "user_id": log.user_id,
            "timestamp": log.timestamp.isoformat(),
            "changes": log.changes,
        }
        for log in logs
    ]


@app.get("/audit/{entity_type}/{entity_id}", tags=["Audit"])
def entity_audit_log(
    entity_type: str,
    entity_id: str,
    current: CurrentUser = Depends(require_permission(Perm.AUDIT_READ)),
    db: Session = Depends(get_db),
):
    svc = AuditService(db)
    logs = svc.get_for_entity(entity_type.upper(), entity_id)
    return [
        {
            "id": log.id,
            "action": log.action,
            "user_id": log.user_id,
            "timestamp": log.timestamp.isoformat(),
            "changes": log.changes,
        }
        for log in logs
    ]


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
