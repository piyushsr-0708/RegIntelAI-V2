"""
Document Processing Orchestrator V1 — RegIntel AI (SuRaksha-v2)

Coordinates the end-to-end execution of one RBI regulatory document through
all 14 pipeline stages, from PDF parsing to dashboard aggregation.

This orchestrator DOES NOT implement any business logic. It only:
1. Invokes existing pipeline stage implementations in the correct order
2. Validates that each stage produces expected output
3. Stops immediately if any stage fails
4. Returns structured execution results

All pipeline stages remain unchanged. This is purely a coordination layer.
"""

import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure pipeline is in python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Result of a single pipeline stage execution."""
    stage_name: str
    status: str  # SUCCESS | FAILED | SKIPPED
    duration_seconds: float
    error_message: Optional[str] = None
    output_path: Optional[Path] = None


@dataclass
class OrchestrationResult:
    """Complete pipeline execution result."""
    document_id: str
    status: str  # SUCCESS | FAILED
    current_stage: Optional[str] = None
    completed_stages: List[StageResult] = field(default_factory=list)
    failed_stage: Optional[str] = None
    error_message: Optional[str] = None
    total_duration_seconds: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "completed_stage_count": len(self.completed_stages),
            "failed_stage": self.failed_stage,
            "error_message": self.error_message,
            "execution_time": self.total_duration_seconds,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "stages": [
                {
                    "stage": s.stage_name,
                    "status": s.status,
                    "duration": s.duration_seconds,
                    "error": s.error_message,
                    "output": str(s.output_path) if s.output_path else None
                }
                for s in self.completed_stages
            ]
        }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class DocumentPipelineOrchestrator:
    """
    Orchestrates the complete document processing pipeline.
    
    Execution order:
    1. PDF Parser
    2. Document Normalizer
    3. Hierarchy Builder
    4. Logical Unit Builder
    5. Requirement Extractor
    6. Requirement Enricher
    7. Compliance Interpreter
    8. Compliance Reasoning Engine
    9. Control Deriver
    10. Verification Rule Generator
    11. Verification Planner
    12. MAP Generator
    13. Database Ingest
    14. Dashboard Aggregator
    """

    def __init__(self, project_root: Path, pdf_source_dir: Optional[Path] = None):
        self.project_root = project_root
        self._setup_logging()
        
        # Allow PDF source override for uploaded documents, default to master_directions for backward compatibility
        pdf_dir = pdf_source_dir if pdf_source_dir else (project_root / "datasets" / "raw" / "master_directions" / "pdfs")
        
        # Define dataset paths
        self.paths = {
            "raw_pdf": pdf_dir,
            "parsed": project_root / "datasets" / "parsed",
            "normalized": project_root / "datasets" / "normalized",
            "hierarchy": project_root / "datasets" / "hierarchy",
            "logical_units": project_root / "datasets" / "logical_units",
            "requirements": project_root / "datasets" / "requirements",
            "enriched_requirements": project_root / "datasets" / "enriched_requirements",
            "interpreted_controls": project_root / "datasets" / "interpreted_controls",
            "reasoned_controls": project_root / "datasets" / "reasoned_controls",
            "controls": project_root / "datasets" / "controls",
            "verification_rules": project_root / "datasets" / "verification_rules",
            "verification_plans": project_root / "datasets" / "verification_plans",
            "maps": project_root / "datasets" / "maps",
            "frontend": project_root / "datasets" / "frontend",
            "logs": project_root / "logs"
        }

    def _setup_logging(self) -> None:
        """Configures orchestrator logging."""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True, parents=True)
        
        log_file = log_dir / "orchestrator.log"
        
        # Remove existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, mode="a", encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _validate_document_exists(self, document_id: str) -> bool:
        """Validates that the source PDF exists."""
        pdf_path = self.paths["raw_pdf"] / f"{document_id}.pdf"
        return pdf_path.exists()

    def _validate_stage_output(self, document_id: str, output_dir: Path) -> bool:
        """Validates that a stage produced output."""
        output_file = output_dir / f"{document_id}.json"
        return output_file.exists()

    def _run_stage(
        self, 
        stage_name: str,
        stage_function: callable,
        document_id: str,
        expected_output_dir: Optional[Path] = None
    ) -> StageResult:
        """
        Executes a single pipeline stage.
        
        Args:
            stage_name: Human-readable stage name for logging
            stage_function: Callable that executes the stage
            document_id: Document being processed
            expected_output_dir: Directory where output should appear (for validation)
            
        Returns:
            StageResult with execution details
        """
        self.logger.info(f"━━━ Stage Started: {stage_name} ━━━")
        start_time = time.time()
        
        try:
            # Execute the stage
            stage_function()
            
            duration = time.time() - start_time
            
            # Validate output if path provided
            if expected_output_dir:
                if not self._validate_stage_output(document_id, expected_output_dir):
                    raise FileNotFoundError(
                        f"Expected output not found: {expected_output_dir}/{document_id}.json"
                    )
                output_path = expected_output_dir / f"{document_id}.json"
            else:
                output_path = None
            
            self.logger.info(
                f"✓ Stage Finished: {stage_name} | Duration: {duration:.2f}s | Status: SUCCESS"
            )
            
            return StageResult(
                stage_name=stage_name,
                status="SUCCESS",
                duration_seconds=round(duration, 2),
                output_path=output_path
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            error_trace = traceback.format_exc()
            
            self.logger.error(f"✗ Stage Failed: {stage_name} | Duration: {duration:.2f}s")
            self.logger.error(f"Error: {error_msg}")
            self.logger.error(f"Traceback:\n{error_trace}")
            
            return StageResult(
                stage_name=stage_name,
                status="FAILED",
                duration_seconds=round(duration, 2),
                error_message=error_msg
            )

    def process_document(self, document_id: str) -> OrchestrationResult:
        """
        Processes a single document through the complete pipeline.
        
        Args:
            document_id: The document identifier (e.g., "MD10190")
            
        Returns:
            OrchestrationResult with complete execution details
        """
        start_time = datetime.now()
        pipeline_start = time.time()
        
        result = OrchestrationResult(
            document_id=document_id,
            status="SUCCESS",
            start_time=start_time.isoformat()
        )
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info(f"PIPELINE ORCHESTRATION STARTED: {document_id}")
        self.logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)
        
        # ───────────────────────────────────────────────────────────────────
        # PRE-FLIGHT VALIDATION
        # ───────────────────────────────────────────────────────────────────
        
        if not self._validate_document_exists(document_id):
            result.status = "FAILED"
            result.failed_stage = "PRE_FLIGHT_CHECK"
            result.error_message = f"Source PDF not found: {self.paths['raw_pdf']}/{document_id}.pdf"
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            
            self.logger.error(f"✗ Pre-flight check failed: {result.error_message}")
            return result
        
        self.logger.info(f"✓ Pre-flight check passed: PDF exists")

        # ───────────────────────────────────────────────────────────────────
        # STAGE 1: PDF PARSER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "PDF_PARSER"
        
        def run_parser():
            from pipeline.parser.pdf_parser import PDFParser
            parser = PDFParser(
                self.paths["raw_pdf"],
                self.paths["parsed"],
                self.paths["logs"]
            )
            # Process only this document
            pdf_path = self.paths["raw_pdf"] / f"{document_id}.pdf"
            parser.parse_document(pdf_path)
        
        stage_result = self._run_stage(
            "PDF Parser",
            run_parser,
            document_id,
            self.paths["parsed"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "PDF_PARSER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 2: DOCUMENT NORMALIZER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "NORMALIZER"
        
        def run_normalizer():
            from pipeline.normalizer.document_normalizer import DocumentNormalizer
            normalizer = DocumentNormalizer(
                self.paths["parsed"],
                self.paths["normalized"],
                self.paths["logs"]
            )
            json_path = self.paths["parsed"] / f"{document_id}.json"
            normalizer.normalize_document(json_path)
        
        stage_result = self._run_stage(
            "Document Normalizer",
            run_normalizer,
            document_id,
            self.paths["normalized"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "NORMALIZER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 3: HIERARCHY BUILDER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "HIERARCHY_BUILDER"
        
        def run_hierarchy_builder():
            from pipeline.hierarchy.hierarchy_builder import HierarchyBuilder
            builder = HierarchyBuilder(
                self.paths["normalized"],
                self.paths["hierarchy"],
                self.paths["logs"]
            )
            json_path = self.paths["normalized"] / f"{document_id}.json"
            builder.process_document(json_path)
        
        stage_result = self._run_stage(
            "Hierarchy Builder",
            run_hierarchy_builder,
            document_id,
            self.paths["hierarchy"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "HIERARCHY_BUILDER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 4: LOGICAL UNIT BUILDER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "LOGICAL_UNIT_BUILDER"
        
        def run_logical_unit_builder():
            from pipeline.logical_units.logical_unit_builder import LogicalUnitBuilder
            builder = LogicalUnitBuilder(
                self.paths["hierarchy"],
                self.paths["logical_units"],
                self.paths["logs"]
            )
            json_path = self.paths["hierarchy"] / f"{document_id}.json"
            builder.process_document(json_path)
        
        stage_result = self._run_stage(
            "Logical Unit Builder",
            run_logical_unit_builder,
            document_id,
            self.paths["logical_units"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "LOGICAL_UNIT_BUILDER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # Continue in next chunk...

        # ───────────────────────────────────────────────────────────────────
        # STAGE 5: REQUIREMENT EXTRACTOR
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "REQUIREMENT_EXTRACTOR"
        
        def run_requirement_extractor():
            from pipeline.extractor.requirement_extractor import RequirementExtractor
            extractor = RequirementExtractor(
                self.paths["logical_units"],
                self.paths["requirements"],
                self.paths["logs"]
            )
            json_path = self.paths["logical_units"] / f"{document_id}.json"
            extractor.process_document(json_path)
        
        stage_result = self._run_stage(
            "Requirement Extractor",
            run_requirement_extractor,
            document_id,
            self.paths["requirements"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "REQUIREMENT_EXTRACTOR"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 6: REQUIREMENT ENRICHER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "REQUIREMENT_ENRICHER"
        
        def run_requirement_enricher():
            from pipeline.enrichment.requirement_enricher import RequirementEnricher
            enricher = RequirementEnricher(
                self.paths["requirements"],
                self.paths["enriched_requirements"],
                self.paths["logs"]
            )
            json_path = self.paths["requirements"] / f"{document_id}.json"
            enricher.process_document(json_path)
        
        stage_result = self._run_stage(
            "Requirement Enricher",
            run_requirement_enricher,
            document_id,
            self.paths["enriched_requirements"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "REQUIREMENT_ENRICHER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 7: COMPLIANCE INTERPRETER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "COMPLIANCE_INTERPRETER"
        
        def run_compliance_interpreter():
            from pipeline.interpreter.compliance_interpreter import ComplianceInterpretationEngine
            engine = ComplianceInterpretationEngine(
                self.paths["enriched_requirements"],
                self.paths["interpreted_controls"],
                self.paths["logs"]
            )
            json_path = self.paths["enriched_requirements"] / f"{document_id}.json"
            engine.process_document(json_path)
        
        stage_result = self._run_stage(
            "Compliance Interpreter",
            run_compliance_interpreter,
            document_id,
            self.paths["interpreted_controls"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "COMPLIANCE_INTERPRETER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 8: COMPLIANCE REASONING ENGINE
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "COMPLIANCE_REASONING"
        
        def run_compliance_reasoning():
            from pipeline.reasoning.compliance_reasoning_engine import ComplianceReasoningEngine
            engine = ComplianceReasoningEngine(
                self.paths["interpreted_controls"],
                self.paths["reasoned_controls"],
                self.paths["logs"]
            )
            json_path = self.paths["interpreted_controls"] / f"{document_id}.json"
            engine.process_document(json_path)
        
        stage_result = self._run_stage(
            "Compliance Reasoning Engine",
            run_compliance_reasoning,
            document_id,
            self.paths["reasoned_controls"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "COMPLIANCE_REASONING"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 9: CONTROL DERIVER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "CONTROL_DERIVER"
        
        def run_control_deriver():
            from pipeline.derivation.control_deriver import ControlDerivationEngine
            engine = ControlDerivationEngine(
                self.paths["reasoned_controls"],
                self.paths["controls"],
                self.paths["logs"]
            )
            json_path = self.paths["reasoned_controls"] / f"{document_id}.json"
            engine.process_document(json_path)
        
        stage_result = self._run_stage(
            "Control Deriver",
            run_control_deriver,
            document_id,
            self.paths["controls"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "CONTROL_DERIVER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 10: VERIFICATION RULE GENERATOR
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "VERIFICATION_RULE_GENERATOR"
        
        def run_verification_rule_generator():
            from pipeline.verification.verification_rule_generator import VerificationRuleGenerator
            generator = VerificationRuleGenerator(
                self.paths["interpreted_controls"],
                self.paths["verification_rules"],
                self.paths["logs"]
            )
            json_path = self.paths["interpreted_controls"] / f"{document_id}.json"
            generator.process_document(json_path)
        
        stage_result = self._run_stage(
            "Verification Rule Generator",
            run_verification_rule_generator,
            document_id,
            self.paths["verification_rules"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "VERIFICATION_RULE_GENERATOR"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 11: VERIFICATION PLANNER
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "VERIFICATION_PLANNER"
        
        def run_verification_planner():
            from pipeline.verification_planner.compliance_verification_planner import ComplianceVerificationPlanner
            planner = ComplianceVerificationPlanner(
                self.paths["verification_rules"],
                self.paths["verification_plans"],
                self.paths["logs"]
            )
            json_path = self.paths["verification_rules"] / f"{document_id}.json"
            planner.process_document(json_path)
        
        stage_result = self._run_stage(
            "Verification Planner",
            run_verification_planner,
            document_id,
            self.paths["verification_plans"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "VERIFICATION_PLANNER"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 12: MAP GENERATOR
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "MAP_GENERATOR"
        
        def run_map_generator():
            from pipeline.map_generator.map_generator import MAPGenerationEngine
            engine = MAPGenerationEngine(
                self.paths["controls"],
                self.paths["maps"],
                self.paths["logs"]
            )
            # MAP generator only needs controls JSON
            controls_path = self.paths["controls"] / f"{document_id}.json"
            engine.process_document(controls_path)
        
        stage_result = self._run_stage(
            "MAP Generator",
            run_map_generator,
            document_id,
            self.paths["maps"]
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "MAP_GENERATOR"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 13: DATABASE INGEST
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "DATABASE_INGEST"
        
        def run_database_ingest():
            from backend.database.ingest import ingest
            # Document-scoped ingest: only process the current document
            ingest(document_id=document_id)
        
        stage_result = self._run_stage(
            "Database Ingest",
            run_database_ingest,
            document_id,
            expected_output_dir=None  # Database write, no JSON output
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "DATABASE_INGEST"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # STAGE 14: DASHBOARD AGGREGATOR
        # ───────────────────────────────────────────────────────────────────
        
        result.current_stage = "DASHBOARD_AGGREGATOR"
        
        def run_dashboard_aggregator():
            from pipeline.aggregator.dashboard_aggregator import main as aggregate_dashboard
            aggregate_dashboard()
        
        stage_result = self._run_stage(
            "Dashboard Aggregator",
            run_dashboard_aggregator,
            document_id,
            expected_output_dir=None  # Outputs to frontend_state.json
        )
        result.completed_stages.append(stage_result)
        
        if stage_result.status == "FAILED":
            result.status = "FAILED"
            result.failed_stage = "DASHBOARD_AGGREGATOR"
            result.error_message = stage_result.error_message
            result.end_time = datetime.now().isoformat()
            result.total_duration_seconds = time.time() - pipeline_start
            return result

        # ───────────────────────────────────────────────────────────────────
        # PIPELINE COMPLETE
        # ───────────────────────────────────────────────────────────────────
        
        end_time = datetime.now()
        result.status = "SUCCESS"
        result.current_stage = None
        result.end_time = end_time.isoformat()
        result.total_duration_seconds = round(time.time() - pipeline_start, 2)
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info(f"✓ PIPELINE ORCHESTRATION COMPLETED: {document_id}")
        self.logger.info(f"Status: {result.status}")
        self.logger.info(f"Total Duration: {result.total_duration_seconds:.2f}s")
        self.logger.info(f"Stages Completed: {len(result.completed_stages)}/14")
        self.logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)
        self.logger.info("")
        
        return result


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    """Command-line interface for the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Document Processing Orchestrator - Processes RBI regulatory documents end-to-end"
    )
    parser.add_argument(
        "document_id",
        type=str,
        help="Document ID to process (e.g., MD10190)"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output result as JSON instead of human-readable format"
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parents[2]
    orchestrator = DocumentPipelineOrchestrator(project_root)
    
    result = orchestrator.process_document(args.document_id)
    
    if args.json_output:
        import json
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"\n{'='*80}")
        print(f"PIPELINE EXECUTION RESULT")
        print(f"{'='*80}")
        print(f"Document ID:         {result.document_id}")
        print(f"Status:              {result.status}")
        print(f"Completed Stages:    {len(result.completed_stages)}/14")
        print(f"Total Duration:      {result.total_duration_seconds:.2f}s")
        if result.failed_stage:
            print(f"Failed Stage:        {result.failed_stage}")
            print(f"Error:               {result.error_message}")
        print(f"{'='*80}\n")
    
    # Exit with appropriate code
    sys.exit(0 if result.status == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
