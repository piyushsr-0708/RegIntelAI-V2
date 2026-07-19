"""
main.py — RegIntel AI V2 Backend
FastAPI application with offline JWT authentication, RBAC, paginated endpoints.
Run: .venv/Scripts/python.exe -m uvicorn backend.main:app --port 8000 --reload
"""
import uvicorn
import json
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile, BackgroundTasks
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

# Get project root for upload handling
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent

logger = logging.getLogger(__name__)

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


@app.get("/maps/{map_id}/detail", tags=["MAPs"])
def get_map_detail(
    map_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
    db: Session = Depends(get_db),
):
    """Get complete MAP detail including tasks and verification plan from pipeline JSONs."""
    svc = AssignmentService(db)
    detail = svc.get_map_detail(map_id)
    if not detail:
        raise HTTPException(status_code=404, detail="MAP detail not found")
    return detail


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

    # Filter out stale assignments whose source document artifacts no longer exist.
    # Build a set of document_ids that have MAP files to avoid N+1 queries.
    maps_dir = project_root / "datasets" / "maps"
    # Collect all source_document_ids referenced by the returned assignments in one query
    map_ids = [a.map_id for a in result["items"] if a.map_id]
    if map_ids:
        source_docs = {
            row[0]: row[1]
            for row in db.query(ManagementActionPlan.id, ManagementActionPlan.source_document_id)
            .filter(ManagementActionPlan.id.in_(map_ids))
            .all()
        }
        valid_items = [
            a for a in result["items"]
            if not a.map_id
            or not source_docs.get(a.map_id)
            or (maps_dir / f"{source_docs[a.map_id]}.json").exists()
        ]
    else:
        valid_items = result["items"]

    return {
        **result,
        "total": len(valid_items),
        "items": [_serialize_assignment(a) for a in valid_items],
    }


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


@app.post("/assignments/{assignment_id}/reset", tags=["Assignments"])
def reset_assignment(
    assignment_id: str,
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_WRITE)),
    db: Session = Depends(get_db),
):
    """Reset a COMPLETED assignment back to ACTIVE (dev/test only)."""
    svc = AssignmentService(db)
    try:
        reset = svc.reset_assignment_to_active(assignment_id, actor_id=current.id)
        return {"message": "Assignment reset to ACTIVE", "id": reset.id, "status": reset.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/assignments/stats/summary", tags=["Assignments"])
def assignment_stats(
    department_id: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_permission(Perm.ASSIGN_READ)),
    db: Session = Depends(get_db),
):
    if current.department_id and not current.can(Perm.WILDCARD):
        department_id = current.department_id
    svc = AssignmentService(db)

    # Apply the same orphan filter as list_assignments so stats match visible rows.
    maps_dir = project_root / "datasets" / "maps"
    all_assignments = db.query(ControlAssignment).all()
    map_ids = [a.map_id for a in all_assignments if a.map_id]
    if map_ids:
        source_docs = {
            row[0]: row[1]
            for row in db.query(ManagementActionPlan.id, ManagementActionPlan.source_document_id)
            .filter(ManagementActionPlan.id.in_(map_ids))
            .all()
        }
        valid = [
            a for a in all_assignments
            if (not a.map_id
                or not source_docs.get(a.map_id)
                or (maps_dir / f"{source_docs[a.map_id]}.json").exists())
            and (not department_id or a.department_id == department_id)
        ]
    else:
        valid = [
            a for a in all_assignments
            if not department_id or a.department_id == department_id
        ]

    summary = {}
    for a in valid:
        summary[a.status] = summary.get(a.status, 0) + 1
    return summary


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


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT SESSION ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/documents/{document_id}/session", tags=["Documents"])
def get_document_session(
    document_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
    db: Session = Depends(get_db),
):
    """
    Get complete session data for a processed document.
    Returns parsed data, requirements, MAPs, verification plans, and processing metrics.
    MAPs are normalized using DB records (same source as Compliance Register).
    """
    import json
    from pathlib import Path
    from sqlalchemy.orm import joinedload

    # Read parsed document metadata
    parsed_path = project_root / "datasets" / "parsed" / f"{document_id}.json"
    if not parsed_path.exists():
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found or not yet processed")

    with open(parsed_path, "r", encoding="utf-8") as f:
        parsed_data = json.load(f)

    # Read requirements
    requirements = []
    requirements_path = project_root / "datasets" / "requirements" / f"{document_id}.json"
    if requirements_path.exists():
        with open(requirements_path, "r", encoding="utf-8") as f:
            req_data = json.load(f)
            requirements = req_data.get("requirements", [])

    # Read verification plans
    verification_plans = []
    vp_path = project_root / "datasets" / "verification_plans" / f"{document_id}.json"
    if vp_path.exists():
        with open(vp_path, "r", encoding="utf-8") as f:
            vp_data = json.load(f)
            verification_plans = vp_data.get("verification_plans", vp_data.get("plans", []))

    # Build normalized MAP list from DB (same source as Compliance Register)
    # Falls back to raw JSON if DB records are not yet ingested.
    db_maps = db.query(ManagementActionPlan).options(
        joinedload(ManagementActionPlan.department),
        joinedload(ManagementActionPlan.control),
    ).filter(ManagementActionPlan.source_document_id == document_id).all()

    if db_maps:
        maps_list = [
            {
                "map_id": m.id,
                "control_id": m.control_id,
                "title": m.control.name if m.control else m.description or m.id,
                "department": m.department.name if m.department else "",
                "priority": m.priority or "MEDIUM",
                "automation_percentage": float(m.automation_percent or 0),
                "compliance_status": m.status,
                "status": m.status,
                "owner_department": m.department.name if m.department else "",
                "source_document_id": m.source_document_id,
                "ai_rationale": m.ai_rationale,
                "verification_plan": m.verification_plan,
                "control_objective": m.control.objective if m.control else None,
                "control_description": m.control.description if m.control else None,
                "source_requirement_text": m.source_requirement_text,
            }
            for m in db_maps
        ]
    else:
        # Fallback: raw JSON with field normalization
        maps_path = project_root / "datasets" / "maps" / f"{document_id}.json"
        raw_maps = []
        if maps_path.exists():
            with open(maps_path, "r", encoding="utf-8") as f:
                raw_maps = json.load(f).get("maps", [])
        maps_list = [
            {
                **m,
                "department": m.get("owner_department") or m.get("department") or "",
                "automation_percentage": float(m.get("automation_percentage") or m.get("automation_percent") or 0),
                "compliance_status": m.get("compliance_status") or m.get("status") or "DRAFT",
            }
            for m in raw_maps
        ]

    departments = {m["department"] for m in maps_list if m.get("department")}

    # Build department impact summary
    department_impact = [
        {"department": dept, "map_count": sum(1 for m in maps_list if m.get("department") == dept)}
        for dept in departments
    ]

    # Read pipeline stage durations from status file
    stages = []
    status_path = project_root / "datasets" / "processed" / f"{document_id}_status.json"
    if status_path.exists():
        with open(status_path, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        stages = status_data.get("stages", [])

    page_count = parsed_data.get("page_count", 0)
    word_count = parsed_data.get("word_count") or page_count * 350

    return {
        "document_id": document_id,
        "filename": parsed_data.get("metadata", {}).get("filename") or f"{document_id}.pdf",
        "page_count": page_count,
        "word_count": word_count,
        "requirements_count": len(requirements),
        "maps_count": len(maps_list),
        "departments_count": len(departments),
        "processing_complete": True,
        "metadata": parsed_data.get("metadata", {}),
        "requirements": requirements,
        "maps": maps_list,
        "verification_plans": verification_plans,
        "department_impact": department_impact,
        "graph": {"nodes": [], "edges": []},
        "stages": stages,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT STATUS HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _status_path(document_id: str) -> Path:
    return project_root / "datasets" / "processed" / f"{document_id}_status.json"


def _write_status(document_id: str, status: str, current_stage: str, progress: int, message: str, error=None):
    path = _status_path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "status": status,
            "current_stage": current_stage,
            "progress": progress,
            "message": message,
            "error": error,
        }, f)


@app.get("/documents/{document_id}/status", tags=["Documents"])
def get_document_status(
    document_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
):
    """
    Returns the current processing status of a document.
    """
    path = _status_path(document_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No status found for document {document_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT UPLOAD ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_upload_document_id() -> str:
    """
    Generates a deterministic upload document ID in format: UPYYYYMMDD_NNNN
    Example: UP20260715_0001
    """
    today = datetime.now().strftime("%Y%m%d")
    upload_dir = project_root / "datasets" / "raw" / "uploaded_documents" / "pdfs"
    
    # Find existing uploads for today
    if upload_dir.exists():
        existing_files = list(upload_dir.glob(f"UP{today}_*.pdf"))
        if existing_files:
            # Extract sequence numbers
            sequences = []
            for f in existing_files:
                try:
                    seq = int(f.stem.split("_")[-1])
                    sequences.append(seq)
                except (ValueError, IndexError):
                    continue
            next_seq = max(sequences) + 1 if sequences else 1
        else:
            next_seq = 1
    else:
        next_seq = 1
    
    return f"UP{today}_{next_seq:04d}"


# Stage name → (progress %, human message) for status updates
# Keys are stage_name.upper().replace(" ", "_") from the orchestrator's _run_stage calls
_STAGE_PROGRESS = {
    "PDF_PARSER":                    (10,  "Parsing PDF document"),
    "DOCUMENT_NORMALIZER":           (20,  "Normalizing document text"),
    "HIERARCHY_BUILDER":             (28,  "Building document hierarchy"),
    "LOGICAL_UNIT_BUILDER":          (36,  "Building logical units"),
    "REQUIREMENT_EXTRACTOR":         (45,  "Extracting requirements"),
    "REQUIREMENT_ENRICHER":          (54,  "Enriching requirements"),
    "COMPLIANCE_INTERPRETER":        (62,  "Interpreting compliance controls"),
    "COMPLIANCE_REASONING_ENGINE":   (70,  "Running compliance reasoning engine"),
    "CONTROL_DERIVER":               (76,  "Deriving controls"),
    "VERIFICATION_RULE_GENERATOR":   (82,  "Generating verification rules"),
    "VERIFICATION_PLANNER":          (87,  "Planning verification"),
    "MAP_GENERATOR":                 (92,  "Generating MAPs"),
    "DATABASE_INGEST":               (96,  "Ingesting into database"),
    "DASHBOARD_AGGREGATOR":          (99,  "Aggregating dashboard"),
}


def _write_status_with_stages(document_id: str, status: str, current_stage: str, progress: int, message: str, stages: list, error=None):
    """Write status JSON including accumulated stage records."""
    path = _status_path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "status": status,
            "current_stage": current_stage,
            "progress": progress,
            "message": message,
            "error": error,
            "stages": stages,
        }, f)


def _run_uploaded_document_pipeline(document_id: str, pdf_source_dir: Path):
    """
    Background task wrapper that executes the pipeline for an uploaded document.
    Writes status JSON at each stage transition so the frontend can poll it.
    Persists completed stage records so the session endpoint can return them.
    """
    import time
    import traceback

    completed_stages = []
    _write_status_with_stages(document_id, "processing", "STARTING", 2, "Pipeline initialising", completed_stages)
    logger.info(f"[BACKGROUND] Background task started for document: {document_id}")

    try:
        from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator

        # Monkey-patch _run_stage to emit live status updates AND accumulate stage records.
        original_run_stage = DocumentPipelineOrchestrator._run_stage

        def _patched_run_stage(self, stage_name, stage_function, doc_id, expected_output_dir=None):
            stage_key = stage_name.upper().replace(" ", "_")
            progress, message = _STAGE_PROGRESS.get(stage_key, (50, f"Running {stage_name}"))
            _write_status_with_stages(document_id, "processing", stage_key, progress, message, completed_stages)
            stage_start = time.time()
            result = original_run_stage(self, stage_name, stage_function, doc_id, expected_output_dir)
            duration_ms = int((time.time() - stage_start) * 1000)
            completed_stages.append({
                "id": stage_key,
                "label": stage_name,
                "records": "—",
                "duration_ms": duration_ms,
                "status": result.status,
            })
            return result

        DocumentPipelineOrchestrator._run_stage = _patched_run_stage

        orchestrator = DocumentPipelineOrchestrator(
            project_root=project_root,
            pdf_source_dir=pdf_source_dir
        )

        result = orchestrator.process_document(document_id)

        if result.status == "SUCCESS":
            _write_status_with_stages(document_id, "completed", "COMPLETED", 100,
                                      "Pipeline completed successfully", completed_stages)
            logger.info(f"[BACKGROUND] ✓ Pipeline completed for {document_id} in {result.total_duration_seconds:.2f}s")
        else:
            _write_status_with_stages(document_id, "failed", result.failed_stage or "UNKNOWN", 0,
                                      f"Pipeline failed at {result.failed_stage}", completed_stages,
                                      error=result.error_message)
            logger.error(f"[BACKGROUND] ✗ Pipeline failed for {document_id} at {result.failed_stage}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        _write_status_with_stages(document_id, "failed", "EXCEPTION", 0,
                                  "Pipeline encountered an unexpected error", completed_stages, error=error_msg)
        logger.error(f"[BACKGROUND] ✗ Critical error for {document_id}: {e}", exc_info=True)
        traceback.print_exc()


@app.post("/documents/upload", tags=["Documents"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current: CurrentUser = Depends(require_permission(Perm.DOC_UPLOAD)),
):
    """
    Upload a new RBI circular PDF for processing.
    Returns immediately with document_id. Processing happens in background.
    Poll GET /documents/{document_id}/status for progress.
    """
    logger.info(f"[UPLOAD] Upload request from {current.username}: {file.filename}")

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    MAX_SIZE = 50 * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")

    import hashlib
    file_hash = hashlib.sha256(file_content).hexdigest()

    # Duplicate detection
    parsed_dir = project_root / "datasets" / "parsed"
    if parsed_dir.exists():
        for parsed_file in parsed_dir.glob("*.json"):
            try:
                with open(parsed_file, "r", encoding="utf-8") as f:
                    parsed_data = json.load(f)
                    if parsed_data.get("metadata", {}).get("sha256") == file_hash:
                        existing_doc_id = parsed_data.get("document_id")
                        logger.info(f"[UPLOAD] Duplicate detected: {existing_doc_id}")
                        return {
                            "document_id": existing_doc_id,
                            "filename": file.filename,
                            "status": "completed",
                            "message": f"Document already processed as {existing_doc_id}.",
                            "duplicate": True,
                        }
            except Exception:
                continue

    document_id = _generate_upload_document_id()
    logger.info(f"[UPLOAD] Generated document ID: {document_id}")

    upload_dir = project_root / "datasets" / "raw" / "uploaded_documents" / "pdfs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = upload_dir / f"{document_id}.pdf"
    try:
        with open(pdf_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        logger.error(f"[UPLOAD] Failed to save PDF: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded document")

    # Write initial status before queuing background task
    _write_status_with_stages(document_id, "processing", "QUEUED", 1, "Document queued for processing", [])

    background_tasks.add_task(_run_uploaded_document_pipeline, document_id, upload_dir)
    logger.info(f"[UPLOAD] Background task queued for {document_id}")

    return {
        "document_id": document_id,
        "filename": file.filename,
        "status": "processing",
        "message": "Document uploaded successfully. Processing in background.",
    }




if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)


# ─── Compliance Report PDF ─────────────────────────────────────────────────────

from fastapi.responses import FileResponse

@app.get("/reports/{document_id}/pdf", tags=["Reports"])
def get_compliance_report_pdf(
    document_id: str,
    current: CurrentUser = Depends(require_permission(Perm.MAP_READ)),
):
    """
    Generate (or regenerate) a professional Compliance Assessment PDF for *document_id*.
    Returns the PDF file as a download.

    READ-ONLY: only reads existing pipeline artifacts. Never modifies compliance data.
    """
    from backend.reports.compliance_pdf_generator import generate_compliance_pdf

    try:
        pdf_path = generate_compliance_pdf(document_id, project_root)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"PDF generation failed for {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f'attachment; filename="{pdf_path.name}"'},
    )
