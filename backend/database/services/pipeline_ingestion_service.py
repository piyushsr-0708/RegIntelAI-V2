import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database.models import Document, Requirement, ComplianceControl, RequirementControlMapping, RequirementProvenance

logger = logging.getLogger(__name__)

class PipelineIngestionService:
    def __init__(self, db: Session):
        self.db = db

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
                # Upsert Control
                ctrl_id = ctrl_data.get("control_id")
                control = self.db.query(ComplianceControl).filter_by(control_id=ctrl_id).first()
                if not control:
                    control = ComplianceControl(
                        control_id=ctrl_id,
                        name=ctrl_data.get("control_name", ""),
                        objective=ctrl_data.get("control_objective", ""),
                        description=ctrl_data.get("control_description", ""),
                        control_type=ctrl_data.get("control_type", ""),
                        implementation_category=ctrl_data.get("implementation_category", ""),
                        frequency=ctrl_data.get("control_frequency", ""),
                        automation_possible=ctrl_data.get("automation_possible", False)
                    )
                    self.db.add(control)
                    self.db.flush()
                    
                # Upsert Requirement
                req_id = ctrl_data.get("requirement_id")
                if req_id:
                    req = self.db.query(Requirement).filter_by(requirement_id=req_id).first()
                    if not req:
                        req = Requirement(
                            requirement_id=req_id,
                            document_id=doc.id,
                            requirement_type="UNKNOWN",
                            action="UNKNOWN",
                            criticality=ctrl_data.get("criticality", "UNKNOWN")
                        )
                        self.db.add(req)
                        self.db.flush()
                        
                        # Add Provenance
                        prov = RequirementProvenance(
                            requirement_id=req.id,
                            logical_unit_id=ctrl_data.get("logical_unit_id", ""),
                            page_numbers=ctrl_data.get("page_numbers", []),
                            hierarchy_node_ids=ctrl_data.get("hierarchy_node_ids", []),
                            block_ids=ctrl_data.get("block_ids", [])
                        )
                        self.db.add(prov)
                        
                    # Map
                    mapping = self.db.query(RequirementControlMapping).filter_by(
                        requirement_id=req.id, control_id=control.id
                    ).first()
                    if not mapping:
                        self.db.add(RequirementControlMapping(requirement_id=req.id, control_id=control.id))
                        
            self.db.commit()
            logger.info(f"Ingested document {doc_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to ingest document: {e}")

    def ingest_directory(self, controls_dir: Path) -> None:
        for json_file in controls_dir.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.ingest_document(data)
