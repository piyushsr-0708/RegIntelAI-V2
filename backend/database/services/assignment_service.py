import logging
import json
import argparse
from typing import Optional
from pathlib import Path
from datetime import timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from backend.database.models import ManagementActionPlan, Department, ControlAssignment, ComplianceControl
from backend.database.services.audit_service import AuditService

logger = logging.getLogger(__name__)

# Simple in-memory cache for parsed JSON documents
_document_cache = {}


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
                    ManagementActionPlan.source_document_id.ilike(term),
                    ManagementActionPlan.source_requirement_id.ilike(term),
                    ManagementActionPlan.control.has(ComplianceControl.name.ilike(term)),
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

    def get_map_detail(self, map_id: str) -> Optional[dict]:
        """Get complete MAP detail including tasks and verification plan from pipeline JSONs."""
        # First get base MAP from SQLite
        map_record = self.get_map_by_id(map_id)
        if not map_record:
            return None
        
        document_id = map_record.source_document_id
        if not document_id:
            logger.warning(f"MAP {map_id} has no source_document_id")
            return None
        
        # Get project root
        from pathlib import Path
        import sys
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[3]
        
        # Load MAP JSON (with caching)
        maps_file = project_root / "datasets" / "maps" / f"{document_id}.json"
        if not maps_file.exists():
            logger.warning(f"MAP file not found: {maps_file}")
            return None
        
        cache_key_maps = f"maps_{document_id}"
        if cache_key_maps not in _document_cache:
            with open(maps_file, "r", encoding="utf-8") as f:
                _document_cache[cache_key_maps] = json.load(f)
        
        maps_data = _document_cache[cache_key_maps]
        
        # Find the specific MAP
        map_detail = None
        for m in maps_data.get("maps", []):
            if m.get("map_id") == map_id:
                map_detail = m
                break
        
        if not map_detail:
            logger.warning(f"MAP {map_id} not found in {maps_file}")
            return None
        
        # Load verification plan (with caching)
        plans_file = project_root / "datasets" / "verification_plans" / f"{document_id}.json"
        verification_plan = None
        if plans_file.exists():
            cache_key_plans = f"plans_{document_id}"
            if cache_key_plans not in _document_cache:
                with open(plans_file, "r", encoding="utf-8") as f:
                    _document_cache[cache_key_plans] = json.load(f)
            
            plans_data = _document_cache[cache_key_plans]
            
            # Extract requirement_id from control_id
            # Example: MD10190_ctrl_req5_1 -> MD10190_req5
            control_id = map_detail.get("control_id", "")
            req_id = None
            if "_ctrl_req" in control_id:
                parts = control_id.split("_ctrl_req")
                if len(parts) == 2:
                    doc_part = parts[0]
                    req_num = parts[1].split("_")[0] if "_" in parts[1] else parts[1]
                    req_id = f"{doc_part}_req{req_num}"
            
            # Find matching verification plan
            if req_id:
                matching_plan_id = f"CVP_VR_{req_id}"
                for plan in plans_data.get("verification_plans", []):
                    if plan.get("plan_id") == matching_plan_id:
                        verification_plan = plan
                        break
        
        # Load compliance decision (with caching) - get latest decision file
        decisions_dir = project_root / "datasets" / "compliance_decisions"
        compliance_decision = None
        if decisions_dir.exists():
            decision_files = sorted(decisions_dir.glob(f"{document_id}_*.json"), reverse=True)
            if decision_files:
                latest_decision_file = decision_files[0]
                cache_key_decision = f"decision_{latest_decision_file.stem}"
                if cache_key_decision not in _document_cache:
                    with open(latest_decision_file, "r", encoding="utf-8") as f:
                        _document_cache[cache_key_decision] = json.load(f)
                
                decision_data = _document_cache[cache_key_decision]
                
                # Find plan verdict for this MAP
                if verification_plan:
                    plan_id = verification_plan.get("plan_id")
                    for pv in decision_data.get("plan_verdicts", []):
                        if pv.get("plan_id") == plan_id:
                            compliance_decision = pv
                            
                            # Calculate failed blocker count for this specific plan
                            # Get check IDs from this plan
                            plan_check_ids = {c["check_id"] for c in verification_plan.get("checks", [])}
                            # Intersect with document's failed blocker list
                            failed_blks = decision_data.get("failed_blocker_list", [])
                            failed_blocker_count = len(set(failed_blks).intersection(plan_check_ids))
                            
                            # Add to compliance_decision
                            compliance_decision["failed_blocker_count"] = failed_blocker_count
                            break
        
        # Load agent decision - get latest agent decision for this requirement
        agent_decisions_dir = project_root / "datasets" / "agent_decisions"
        agent_decision = None
        if agent_decisions_dir.exists() and req_id:
            agent_files = sorted(agent_decisions_dir.glob(f"{req_id}_*.json"), reverse=True)
            if agent_files:
                latest_agent_file = agent_files[0]
                cache_key_agent = f"agent_{latest_agent_file.stem}"
                if cache_key_agent not in _document_cache:
                    try:
                        with open(latest_agent_file, "r", encoding="utf-8") as f:
                            _document_cache[cache_key_agent] = json.load(f)
                    except Exception as e:
                        logger.error(f"Failed to load agent decision {latest_agent_file}: {e}")
                
                if cache_key_agent in _document_cache:
                    agent_decision = _document_cache[cache_key_agent]
        
        # Combine all data
        return {
            "map_id": map_detail.get("map_id"),
            "control_id": map_detail.get("control_id"),
            "document_id": map_detail.get("document_id"),
            "title": map_detail.get("title"),
            "objective": map_detail.get("objective"),
            "priority": map_detail.get("priority"),
            "criticality": map_detail.get("criticality"),
            "status": map_detail.get("status"),
            "owner_department": map_detail.get("owner_department"),
            "compliance_domain": map_detail.get("compliance_domain"),
            "risk_domain": map_detail.get("risk_domain"),
            "estimated_total_effort_hours": map_detail.get("estimated_total_effort_hours"),
            "task_count": map_detail.get("task_count"),
            "generated_timestamp": map_detail.get("generated_timestamp"),
            "tasks": map_detail.get("tasks", []),
            "verification_plan": verification_plan,
            "compliance_decision": compliance_decision,
            "agent_decision": agent_decision,
        }

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
            # Search in assignment ID, control name, or control ID
            q = q.outerjoin(ComplianceControl, ControlAssignment.control_id == ComplianceControl.id).filter(
                or_(
                    ControlAssignment.id.ilike(term),
                    ComplianceControl.name.ilike(term),
                    ComplianceControl.control_id.ilike(term)
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

        # TASK 2: Prevent duplicate completion
        if assignment.status == "COMPLETED":
            logger.warning(f"Assignment {assignment_id} already completed, rejecting duplicate request")
            raise ValueError(f"Assignment '{assignment_id}' is already completed")
        
        # Additional safety check for any non-ACTIVE status
        if assignment.status != "ACTIVE":
            logger.warning(f"Assignment {assignment_id} has status {assignment.status}, cannot complete")
            raise ValueError(f"Assignment '{assignment_id}' cannot be completed from status {assignment.status}")

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
        
        # ─── PIPELINE EXECUTION CHAIN ───────────────────────────────────────────
        # After successful database commit, trigger verification and decision.
        # Failures in pipeline execution do NOT rollback assignment completion.
        
        # Extract document_id using existing pattern from get_map_detail()
        document_id = None
        requirement_id = None
        plan_id = None
        if assignment.map_id:
            map_record = self.db.query(ManagementActionPlan).filter_by(id=assignment.map_id).first()
            if map_record:
                document_id = map_record.source_document_id
                requirement_id = map_record.source_requirement_id
                
                # TASK 1: Derive plan_id from requirement_id to filter verification scope
                if requirement_id:
                    plan_id = f"CVP_VR_{requirement_id}"
                    logger.info(f"📋 Scoping verification to plan: {plan_id}")
        
        if not document_id:
            logger.warning(f"Assignment {assignment_id} has no source_document_id, skipping verification")
            return assignment
        
        if not requirement_id:
            logger.warning(f"Assignment {assignment_id} has no source_requirement_id, verification may process entire document")
        
        # Get project root (same pattern as get_map_detail)
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[3]
        
        # Locate verification plan
        plan_file = project_root / "datasets" / "verification_plans" / f"{document_id}.json"
        
        if not plan_file.exists():
            logger.warning(f"Verification plan not found: {plan_file}, skipping verification")
            return assignment
        
        # ─── Stage 0: Verification Agent Decision ───
        agent_decision_data = None  # Store for later persistence
        try:
            from backend.database.services.verification_agent_service import VerificationAgentService
            
            agent = VerificationAgentService(project_root)
            decision = agent.decide_verification_strategy(
                document_id=document_id,
                requirement_id=requirement_id,
                criticality=map_record.priority if map_record else None,
                department=assignment.department.name if assignment.department else None
            )
            
            logger.info(f"🤖 Verification Agent Analysis:")
            logger.info(f"   Verdict: {decision.verdict}")
            logger.info(f"   Reasoning: {decision.reasoning}")
            logger.info(f"   Automated checks: {decision.automated_checks_available}/{decision.total_checks}")
            logger.info(f"   Manual checks: {decision.manual_checks_required}/{decision.total_checks}")
            logger.info(f"   Recommendation: {decision.recommended_action}")
            
            # Persist agent decision for later retrieval
            from datetime import datetime
            agent_decision_data = {
                "document_id": document_id,
                "requirement_id": requirement_id,
                "assignment_id": assignment_id,
                "verdict": decision.verdict,
                "reasoning": decision.reasoning,
                "confidence_score": decision.confidence_score,
                "automated_checks_available": decision.automated_checks_available,
                "manual_checks_required": decision.manual_checks_required,
                "total_checks": decision.total_checks,
                "execute_automated": decision.execute_automated,
                "requires_manual_review": decision.requires_manual_review,
                "recommended_action": decision.recommended_action,
                "control_objective": decision.control_objective,
                "regulatory_intent": decision.regulatory_intent,
                "automation_feasibility": decision.automation_feasibility,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "criticality": map_record.priority if map_record else None,
                "department": assignment.department.name if assignment.department else None
            }
            
            # Save to datasets/agent_decisions/
            agent_decisions_dir = project_root / "datasets" / "agent_decisions"
            agent_decisions_dir.mkdir(exist_ok=True)
            
            # Use requirement_id or document_id for filename
            decision_file = agent_decisions_dir / f"{requirement_id or document_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            with open(decision_file, "w", encoding="utf-8") as f:
                json.dump(agent_decision_data, f, indent=2, ensure_ascii=False)
            
            if decision.verdict == "NO_GO":
                logger.warning(f"⛔ Verification blocked: {decision.reasoning}")
                logger.warning(f"   Action: {decision.recommended_action}")
                return assignment
            
            if decision.verdict == "ESCALATE":
                logger.warning(f"⚠️ Escalated for manual review: {decision.reasoning}")
                logger.warning(f"   Action: {decision.recommended_action}")
                
                # KEY CHANGE: ESCALATE no longer terminates workflow
                # If automated checks are available, execute them
                if not decision.execute_automated:
                    logger.info(f"   No automated checks available - routing to manual review only")
                    # Future: Update assignment status to "ESCALATED" or similar
                    return assignment
                
                logger.info(f"   Continuing with {decision.automated_checks_available} automated checks")
                logger.info(f"   {decision.manual_checks_required} checks flagged for manual review")
                # Fall through to verification execution
            
            if decision.verdict == "GO":
                logger.info(f"✅ Agent approved: {decision.reasoning}")
                logger.info(f"   Action: {decision.recommended_action}")
                # Fall through to verification execution
            
        except Exception as e:
            logger.error(f"❌ Verification agent failed for document {document_id}: {e}", exc_info=True)
            # Fallback: Continue with verification (preserve existing behavior)
            logger.warning("⚠️ Falling back to direct verification execution")
        
        # Stage 1: Execute Verification (independently wrapped)
        try:
            from pipeline.executor.compliance_verification_executor import process_document
            
            # TASK 1: Pass plan_id to filter verification to specific requirement
            # Create args namespace as expected by executor
            args = argparse.Namespace(timeout=300, dry_run=False, document=None, plan=plan_id)
            
            if plan_id:
                logger.info(f"🎯 Executing verification for specific plan: {plan_id}")
            else:
                logger.warning(f"⚠️ No plan_id available, executing all plans for document {document_id}")
            
            # Execute verification for the document
            process_document(plan_file, args)
            logger.info(f"✅ Verification executed successfully for document {document_id}")
            
        except Exception as e:
            logger.error(f"❌ Verification execution failed for document {document_id}: {e}", exc_info=True)
            # Continue to decision engine even if verification fails
        
        # Stage 2: Execute Decision Engine (independently wrapped)
        try:
            from pipeline.decision.compliance_decision_engine import process_document
            
            # Pass plan_id so the decision engine evaluates only the same plan the executor ran
            process_document(document_id, plan_file, plan_id)
            logger.info(f"✅ Compliance decision generated successfully for plan {plan_id or document_id}")

            
        except Exception as e:
            logger.error(f"❌ Decision engine failed for document {document_id}: {e}", exc_info=True)
        
        return assignment

    def reset_assignment_to_active(
        self,
        assignment_id: str,
        actor_id: Optional[str] = None,
    ) -> ControlAssignment:
        """Reset a COMPLETED assignment back to ACTIVE for re-testing."""
        assignment = self.db.query(ControlAssignment).filter_by(id=assignment_id).first()
        if not assignment:
            raise ValueError(f"ControlAssignment '{assignment_id}' not found")

        if assignment.status != "COMPLETED":
            raise ValueError(
                f"Assignment '{assignment_id}' cannot be reset from status '{assignment.status}'. "
                "Only COMPLETED assignments can be reset to ACTIVE."
            )

        assignment.status = "ACTIVE"

        self._audit.record(
            "ASSIGNMENT", assignment_id, "RESET_TO_ACTIVE",
            user_id=actor_id,
            changes=[{"field": "status", "old": "COMPLETED", "new": "ACTIVE"}],
        )
        self.db.commit()
        logger.info(f"Assignment {assignment_id} reset to ACTIVE by {actor_id or 'SYSTEM'}")
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
