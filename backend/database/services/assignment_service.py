import logging
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from backend.database.models import ManagementActionPlan, Department, ControlAssignment
from backend.database.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self._audit = AuditService(db)

    # ─── MAP Queries ───────────────────────────────────────────────────────────

    def get_maps(
        self,
        status: Optional[str] = None,
        department_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Paginated, filterable MAP query — never returns tens of thousands at once."""
        q = self.db.query(ManagementActionPlan).options(
            joinedload(ManagementActionPlan.department),
            joinedload(ManagementActionPlan.control),
        )

        if status:
            q = q.filter(ManagementActionPlan.status == status.upper())
        if department_id:
            q = q.filter(ManagementActionPlan.department_id == department_id)
        if search:
            term = f"%{search}%"
            q = q.filter(
                or_(
                    ManagementActionPlan.id.ilike(term),
                    ManagementActionPlan.description.ilike(term),
                )
            )

        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
            "items": items,
        }

    def get_draft_maps(self):
        return self.db.query(ManagementActionPlan).options(
            joinedload(ManagementActionPlan.department),
            joinedload(ManagementActionPlan.control)
        ).filter(ManagementActionPlan.status == "DRAFT").all()

    def get_map_by_id(self, map_id: str) -> Optional[ManagementActionPlan]:
        return self.db.query(ManagementActionPlan).options(
            joinedload(ManagementActionPlan.department),
            joinedload(ManagementActionPlan.control),
        ).filter_by(id=map_id).first()

    # ─── MAP Mutations ─────────────────────────────────────────────────────────

    def update_map_metadata(
        self,
        map_id: str,
        department_id: Optional[str] = None,
        priority: Optional[str] = None,
        verification_plan: Optional[str] = None,
        due_date=None,
        comments: Optional[str] = None,
        reject_reason: Optional[str] = None,
        status: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> ManagementActionPlan:
        action_plan = self.db.query(ManagementActionPlan).filter_by(id=map_id).first()
        if not action_plan:
            raise ValueError(f"ManagementActionPlan '{map_id}' not found")

        changes = []
        if department_id and department_id != action_plan.department_id:
            department = self.db.query(Department).filter_by(id=department_id).first()
            if not department:
                raise ValueError(f"Department '{department_id}' not found")
            changes.append({"field": "department_id", "old": action_plan.department_id, "new": department_id})
            action_plan.department_id = department_id
        if priority and priority != action_plan.priority:
            changes.append({"field": "priority", "old": action_plan.priority, "new": priority})
            action_plan.priority = priority.upper()
        if verification_plan is not None:
            changes.append({"field": "verification_plan", "old": "[previous]", "new": "[updated]"})
            action_plan.verification_plan = verification_plan
        if due_date is not None:
            changes.append({"field": "due_date", "old": str(action_plan.due_date), "new": str(due_date)})
            action_plan.due_date = due_date
        if comments is not None:
            changes.append({"field": "comments", "old": "[previous]", "new": "[updated]"})
            action_plan.comments = comments
        if reject_reason is not None:
            changes.append({"field": "reject_reason", "old": None, "new": "[set]"})
            action_plan.reject_reason = reject_reason
        if status and status != action_plan.status:
            changes.append({"field": "status", "old": action_plan.status, "new": status})
            action_plan.status = status

        if changes:
            self._audit.record("MAP", map_id, "UPDATED", user_id=actor_id, changes=changes)

        self.db.commit()
        self.db.refresh(action_plan)
        return action_plan

    def approve_map(self, map_id: str, actor_id: Optional[str] = None):
        action_plan = self.db.query(ManagementActionPlan).filter_by(id=map_id).first()
        if not action_plan:
            raise ValueError(f"ManagementActionPlan '{map_id}' not found")
        if action_plan.status != "DRAFT":
            raise ValueError(f"MAP is not DRAFT. Current status: {action_plan.status}")

        action_plan.status = "APPROVED"

        # Generate ControlAssignment, carrying over all reviewer-set metadata
        assignment = ControlAssignment(
            control_id=action_plan.control_id,
            department_id=action_plan.department_id,
            map_id=action_plan.id,
            title=action_plan.description,
            priority=action_plan.priority,
            due_date=action_plan.due_date,
            comments=action_plan.comments,
            status="ACTIVE",
        )
        self.db.add(assignment)
        self.db.flush()

        self._audit.record("MAP", map_id, "APPROVED", user_id=actor_id,
                           changes=[{"field": "status", "old": "DRAFT", "new": "APPROVED"}])
        self._audit.record("ASSIGNMENT", assignment.id, "CREATED", user_id=actor_id,
                           changes=[{
                               "field": "source_map_id", "old": None, "new": map_id,
                               "department_id": action_plan.department_id,
                               "priority": action_plan.priority,
                           }])

        self.db.commit()
        return action_plan, assignment

    def reject_map(self, map_id: str, reject_reason: Optional[str] = None, actor_id: Optional[str] = None):
        """Reject a DRAFT MAP. Rejected MAPs never create assignments."""
        action_plan = self.db.query(ManagementActionPlan).filter_by(id=map_id).first()
        if not action_plan:
            raise ValueError(f"ManagementActionPlan '{map_id}' not found")
        if action_plan.status != "DRAFT":
            raise ValueError(f"MAP is not DRAFT. Current status: {action_plan.status}")

        action_plan.status = "REJECTED"
        action_plan.reject_reason = reject_reason

        self._audit.record("MAP", map_id, "REJECTED", user_id=actor_id,
                           changes=[{
                               "field": "status", "old": "DRAFT", "new": "REJECTED",
                               "reason": reject_reason,
                           }])
        self.db.commit()
        return action_plan

    # ─── Assignment Queries ────────────────────────────────────────────────────

    def get_assignments(
        self,
        department_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        q = self.db.query(ControlAssignment).options(
            joinedload(ControlAssignment.control),
            joinedload(ControlAssignment.department),
        )

        if department_id:
            q = q.filter(ControlAssignment.department_id == department_id)
        if status:
            q = q.filter(ControlAssignment.status == status.upper())
        if search:
            term = f"%{search}%"
            q = q.join(ControlAssignment.control).filter(
                ControlAssignment.control.has(ControlAssignment.control.property.mapper.class_.name.ilike(term))
            )

        total = q.count()
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
            "items": items,
        }

    def get_assignments_by_department(self, department_id: str):
        return self.db.query(ControlAssignment).options(
            joinedload(ControlAssignment.control)
        ).filter(ControlAssignment.department_id == department_id).all()

    # ─── Assignment Mutations ──────────────────────────────────────────────────

    def mark_assignment_complete(
        self,
        assignment_id: str,
        actor_id: Optional[str] = None,
        evidence_note: Optional[str] = None,
    ) -> ControlAssignment:
        assignment = self.db.query(ControlAssignment).filter_by(id=assignment_id).first()
        if not assignment:
            raise ValueError(f"ControlAssignment '{assignment_id}' not found")

        old_status = assignment.status
        assignment.status = "COMPLETED"
        if evidence_note:
            assignment.evidence_note = evidence_note

        changes = [{"field": "status", "old": old_status, "new": "COMPLETED"}]
        if evidence_note:
            changes.append({"field": "evidence_note", "old": None, "new": evidence_note[:100]})

        self._audit.record("ASSIGNMENT", assignment_id, "COMPLETED",
                           user_id=actor_id, changes=changes)
        self.db.commit()
        return assignment


    # ─── Stats ────────────────────────────────────────────────────────────────

    def get_map_status_summary(self) -> dict:
        rows = self.db.query(ManagementActionPlan.status, func.count()).group_by(ManagementActionPlan.status).all()
        return {row[0]: row[1] for row in rows}

    def get_assignment_status_summary(self, department_id: Optional[str] = None) -> dict:
        q = self.db.query(ControlAssignment.status, func.count()).group_by(ControlAssignment.status)
        if department_id:
            q = q.filter(ControlAssignment.department_id == department_id)
        rows = q.all()
        return {row[0]: row[1] for row in rows}
