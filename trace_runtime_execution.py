"""
Runtime Execution Tracer for UP20260716_0007

Instruments DocumentPipelineOrchestrator to trace:
1. Which stages are entered
2. Which stages complete successfully
3. Which stages produce output files
4. Which stages are skipped and why
5. Exact conditional evaluations

Does NOT modify pipeline logic - only adds logging.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Configure detailed logging
log_file = project_root / "logs" / f"runtime_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_file.parent.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - TRACE - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Monkey-patch the orchestrator to add instrumentation
from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator

original_run_stage = DocumentPipelineOrchestrator._run_stage

def instrumented_run_stage(self, stage_name, stage_function, document_id, expected_output_dir=None):
    """Instrumented version of _run_stage with detailed logging."""
    
    logger.info(f"\n{'='*80}")
    logger.info(f"STAGE ENTRY: {stage_name}")
    logger.info(f"Document ID: {document_id}")
    logger.info(f"Expected Output Dir: {expected_output_dir}")
    
    if expected_output_dir:
        output_file = expected_output_dir / f"{document_id}.json"
        logger.info(f"Expected Output File: {output_file}")
        logger.info(f"Output File Exists Before Stage: {output_file.exists()}")
    
    # Call original stage
    result = original_run_stage(self, stage_name, stage_function, document_id, expected_output_dir)
    
    logger.info(f"Stage Status: {result.status}")
    logger.info(f"Stage Duration: {result.duration_seconds}s")
    
    if result.error_message:
        logger.error(f"Stage Error: {result.error_message}")
    
    if expected_output_dir:
        output_file = expected_output_dir / f"{document_id}.json"
        exists_after = output_file.exists()
        logger.info(f"Output File Exists After Stage: {exists_after}")
        
        if exists_after:
            size = output_file.stat().st_size
            logger.info(f"Output File Size: {size} bytes")
            
            # Quick validation - is it valid JSON?
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Output File Valid JSON: True")
                    if isinstance(data, dict):
                        logger.info(f"Output Top-Level Keys: {list(data.keys())}")
            except Exception as e:
                logger.error(f"Output File JSON Validation Failed: {e}")
    
    logger.info(f"STAGE EXIT: {stage_name}")
    logger.info(f"{'='*80}\n")
    
    return result

# Apply monkey patch
DocumentPipelineOrchestrator._run_stage = instrumented_run_stage

# Also instrument the process_document method to log conditionals
original_process_document = DocumentPipelineOrchestrator.process_document

def instrumented_process_document(self, document_id):
    """Instrumented version that logs document processing."""
    
    logger.info(f"\n{'#'*80}")
    logger.info(f"PIPELINE ORCHESTRATION START")
    logger.info(f"Document ID: {document_id}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"{'#'*80}\n")
    
    # Log all expected paths
    logger.info("EXPECTED OUTPUT PATHS:")
    for stage_name, path in self.paths.items():
        if stage_name not in ["raw_pdf", "logs"]:
            output_file = path / f"{document_id}.json"
            exists = output_file.exists()
            logger.info(f"  {stage_name:30s} -> {output_file} (exists: {exists})")
    logger.info("")
    
    result = original_process_document(self, document_id)
    
    logger.info(f"\n{'#'*80}")
    logger.info(f"PIPELINE ORCHESTRATION COMPLETE")
    logger.info(f"Document ID: {document_id}")
    logger.info(f"Final Status: {result.status}")
    logger.info(f"Total Duration: {result.total_duration_seconds}s")
    logger.info(f"Stages Completed: {len(result.completed_stages)}")
    logger.info(f"{'#'*80}\n")
    
    # Summary table
    logger.info("\nEXECUTION SUMMARY:")
    logger.info(f"{'Stage':<40} {'Status':<10} {'Duration':<10} {'Output Exists':<15}")
    logger.info("-" * 85)
    
    for stage in result.completed_stages:
        output_exists = "N/A"
        if stage.output_path:
            output_exists = "YES" if stage.output_path.exists() else "NO"
        
        logger.info(
            f"{stage.stage_name:<40} {stage.status:<10} {stage.duration_seconds:<10.2f} {output_exists:<15}"
        )
    
    return result

DocumentPipelineOrchestrator.process_document = instrumented_process_document

# Run the pipeline for UP20260716_0007
if __name__ == "__main__":
    document_id = "UP20260716_0007"
    
    logger.info(f"Starting runtime trace for document: {document_id}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Check if source PDF exists
    orchestrator = DocumentPipelineOrchestrator(
        project_root=project_root,
        pdf_source_dir=project_root / "datasets" / "raw" / "user_uploads"
    )
    
    pdf_path = orchestrator.paths["raw_pdf"] / f"{document_id}.pdf"
    logger.info(f"Source PDF Path: {pdf_path}")
    logger.info(f"Source PDF Exists: {pdf_path.exists()}")
    
    if not pdf_path.exists():
        logger.error(f"ERROR: Source PDF not found. Cannot trace execution.")
        sys.exit(1)
    
    # Execute with full instrumentation
    result = orchestrator.process_document(document_id)
    
    # Write structured result
    result_file = project_root / "logs" / f"runtime_result_{document_id}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, indent=2)
    
    logger.info(f"\nStructured result written to: {result_file}")
    logger.info(f"Full trace written to: {log_file}")
    
    print("\n" + "="*80)
    print("RUNTIME TRACE COMPLETE")
    print(f"Log file: {log_file}")
    print(f"Result file: {result_file}")
    print("="*80)
