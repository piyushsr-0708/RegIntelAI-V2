import json
import logging
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database.models import (
    Document, Requirement, ComplianceControl, RequirementControlMapping,
    LogicalUnit, ManagementActionPlan, Department
)
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineIngestionService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_control_hash(self, ctrl_data: dict) -> str:
        """Deterministically generates a control hash based on key properties to allow deduplication."""
        sig = "|".join([
            str(ctrl_data.get("control_name", "")).strip().lower(),
            str(ctrl_data.get("implementation_category", "")).strip().lower(),
            str(ctrl_data.get("control_type", "")).strip().lower(),
            str(ctrl_data.get("implementation_method", "")).strip().lower()
        ])
        return f"CTRL_{hashlib.sha256(sig.encode()).hexdigest()[:16]}"

    def ingest_document(self, doc_json: dict) -> None:
        try:
            doc_id = doc_json.get("document_id")
            if not doc_id:
                return

            # Upsert document
            doc = self.db.query(Document).filter_by(document_id=doc_id).first()
            if not doc:
                doc = Document(
                    document_id=doc_id,
                    title=doc_json.get("title", doc_id),
                    status=doc_json.get("document_status", "ACTIVE")
                )
                self.db.add(doc)
                self.db.flush()

            controls_data = doc_json.get("controls", [])
            for ctrl_data in controls_data:
                # 1. Upsert LogicalUnit for Provenance
                lu_ext_id = ctrl_data.get("logical_unit_id", "")
                logical_unit = None
                if lu_ext_id:
                    logical_unit = self.db.query(LogicalUnit).filter_by(logical_unit_id=lu_ext_id).first()
                    if not logical_unit:
                        logical_unit = LogicalUnit(
                            logical_unit_id=lu_ext_id,
                            document_id=doc.id,
                            page_numbers=ctrl_data.get("page_numbers", []),
                            hierarchy_node_ids=ctrl_data.get("hierarchy_node_ids", []),
                            block_ids=ctrl_data.get("block_ids", [])
                        )
                        self.db.add(logical_unit)
                        self.db.flush()

                # 2. Upsert Requirement (capture requirement text for provenance)
                req_ext_id = ctrl_data.get("requirement_id")
                req = None
                if req_ext_id:
                    req = self.db.query(Requirement).filter_by(requirement_id=req_ext_id).first()
                    if not req:
                        req = Requirement(
                            requirement_id=req_ext_id,
                            document_id=doc.id,
                            logical_unit_id=logical_unit.id if logical_unit else None,
                            requirement_type="UNKNOWN",
                            action="UNKNOWN",
                            criticality=ctrl_data.get("criticality", "UNKNOWN")
                        )
                        self.db.add(req)
                        self.db.flush()

                # 3. Upsert Deduplicated Control
                deterministic_ctrl_id = self._generate_control_hash(ctrl_data)
                control = self.db.query(ComplianceControl).filter_by(control_id=deterministic_ctrl_id).first()
                if not control:
                    control = ComplianceControl(
                        control_id=deterministic_ctrl_id,
                        name=ctrl_data.get("control_name", "Unnamed Control"),
                        objective=ctrl_data.get("control_objective", ""),
                        description=ctrl_data.get("control_description", ""),
                        control_type=ctrl_data.get("control_type", ""),
                        implementation_category=ctrl_data.get("implementation_category", ""),
                        frequency=ctrl_data.get("control_frequency", ""),
                        automation_possible=ctrl_data.get("automation_possible", False)
                    )
                    self.db.add(control)
                    self.db.flush()

                # 4. Map Requirement to Control
                if req and control:
                    mapping = self.db.query(RequirementControlMapping).filter_by(
                        requirement_id=req.id, control_id=control.id
                    ).first()
                    if not mapping:
                        self.db.add(RequirementControlMapping(requirement_id=req.id, control_id=control.id))

            self.db.commit()
            logger.info(f"Ingested document {doc_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to ingest document {doc_id}: {e}")

    def ingest_directory(self, controls_dir: Path) -> None:
        for json_file in controls_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.ingest_document(data)

    def ingest_maps(self, maps_json: dict) -> None:
        """
        Ingest MAP JSON, extracting rich AI-generated metadata including:
        - priority, objective, automation %, risk score
        - AI rationale (from objective + compliance domains)
        - Verification plan summary (from tasks)
        - Source document and requirement provenance
        """
        try:
            doc_id = maps_json.get("document_id")
            doc_title = maps_json.get("title", doc_id)
            if not doc_id:
                return

            maps_data = maps_json.get("maps", [])
            for map_data in maps_data:
                # ── Resolve Department ────────────────────────────────────────
                dept_name = map_data.get("owner_department", "Unknown")
                dept = self.db.query(Department).filter_by(name=dept_name).first()
                if not dept:
                    dept = Department(name=dept_name, description=f"{dept_name} Department")
                    self.db.add(dept)
                    self.db.flush()

                # ── Resolve Control ───────────────────────────────────────────
                ctrl_id_str = map_data.get("control_id", "")
                import re
                m = re.match(r"(.*)_ctrl_(req\d+)(?:_\d+)?", ctrl_id_str)
                if m:
                    req_id = f"{m.group(1)}_{m.group(2)}"
                else:
                    req_id = ctrl_id_str.replace("_ctrl", "") if "_ctrl" in ctrl_id_str else None

                resolved_control_uuid = None
                req_text = None
                if req_id:
                    req = self.db.query(Requirement).filter_by(requirement_id=req_id).first()
                    if req:
                        mapping = self.db.query(RequirementControlMapping).filter_by(
                            requirement_id=req.id
                        ).first()
                        if mapping:
                            resolved_control_uuid = mapping.control_id

                if not resolved_control_uuid:
                    logger.warning(f"Could not resolve control for MAP {map_data.get('map_id')} in {doc_id}")
                    continue

                # ── Derive AI-generated fields from MAP JSON ──────────────────
                priority = map_data.get("priority") or map_data.get("criticality") or "MEDIUM"

                # AI Rationale: compose from objective and compliance/risk domains
                objective = map_data.get("objective", "")
                compliance_domains = map_data.get("compliance_domain", [])
                risk_domains = map_data.get("risk_domain", [])
                ai_rationale_parts = []
                if objective:
                    ai_rationale_parts.append(f"Objective: {objective}")
                if compliance_domains:
                    ai_rationale_parts.append(f"Compliance domains: {', '.join(compliance_domains)}")
                if risk_domains:
                    ai_rationale_parts.append(f"Risk domains: {', '.join(risk_domains)}")
                ai_rationale = " | ".join(ai_rationale_parts) if ai_rationale_parts else None

                # Verification plan: summarise tasks
                tasks = map_data.get("tasks", [])
                task_count = map_data.get("task_count", len(tasks))
                effort_hours = map_data.get("estimated_total_effort_hours", 0)
                vp_lines = [f"Total tasks: {task_count} | Estimated effort: {effort_hours}h"]
                for t in tasks[:5]:  # limit to first 5 tasks in summary
                    vp_lines.append(f"• [{t.get('task_type','Task')}] {t.get('title','')}")
                verification_plan = "\n".join(vp_lines) if tasks else None

                # Automation percent: estimate from machine_verifiable tasks
                machine_verifiable = sum(1 for t in tasks if t.get("machine_verifiable", False))
                automation_percent = int((machine_verifiable / len(tasks) * 100)) if tasks else 0

                # Risk score: map priority to numeric (for sorting/display)
                RISK_MAP = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}
                risk_score = RISK_MAP.get(priority.upper(), 50)

                # ── Upsert MAP ────────────────────────────────────────────────
                map_id = map_data.get("map_id")
                action_plan = self.db.query(ManagementActionPlan).filter_by(id=map_id).first()
                if not action_plan:
                    action_plan = ManagementActionPlan(
                        id=map_id,
                        control_id=resolved_control_uuid,
                        department_id=dept.id,
                        status="DRAFT",
                        description=map_data.get("title", ""),
                        # Priority & metrics
                        priority=priority.upper(),
                        risk_score=risk_score,
                        automation_percent=automation_percent,
                        # AI-generated content
                        ai_rationale=ai_rationale,
                        verification_plan=verification_plan,
                        # Source provenance
                        source_document_id=doc_id,
                        source_document_title=doc_title,
                        source_requirement_id=req_id,
                        source_requirement_text=req_text,
                        target_date=None,
                        due_date=None,
                    )
                    self.db.add(action_plan)
                else:
                    # Update AI-generated fields on re-ingest, but preserve reviewer annotations
                    action_plan.priority = action_plan.priority or priority.upper()
                    action_plan.risk_score = action_plan.risk_score or risk_score
                    action_plan.automation_percent = action_plan.automation_percent or automation_percent
                    action_plan.ai_rationale = action_plan.ai_rationale or ai_rationale
                    action_plan.verification_plan = action_plan.verification_plan or verification_plan
                    action_plan.source_document_id = action_plan.source_document_id or doc_id
                    action_plan.source_document_title = action_plan.source_document_title or doc_title
                    action_plan.source_requirement_id = action_plan.source_requirement_id or req_id

            self.db.commit()
            logger.info(f"Ingested MAPs for document {doc_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to ingest MAPs for document {doc_id}: {e}", exc_info=True)

    def ingest_maps_directory(self, maps_dir: Path) -> None:
        for json_file in maps_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.ingest_maps(data)

