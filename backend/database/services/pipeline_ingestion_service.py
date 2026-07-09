import json
import logging
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database.models import Document, Requirement, ComplianceControl, RequirementControlMapping, LogicalUnit

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

                # 2. Upsert Requirement
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
