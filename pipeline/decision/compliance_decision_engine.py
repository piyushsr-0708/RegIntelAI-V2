import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

PLANS_DIR = project_root / "datasets" / "verification_plans"
RESULTS_DIR = project_root / "datasets" / "verification_results"
OUTPUT_DIR = project_root / "datasets" / "compliance_decisions"

def process_document(doc_id: str, plan_file: Path):
    with open(plan_file, "r", encoding="utf-8") as f:
        plans_data = json.load(f).get("verification_plans", [])
        
    results_file = RESULTS_DIR / f"{doc_id}.json"
    results_dict = {}
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            r_data = json.load(f)
            for r in r_data.get("verification_results", []):
                results_dict[r.get("plan_id")] = r

    plan_verdicts = []
    
    # Document-level stats
    doc_stats = {
        "plans": len(plans_data),
        "checks": 0,
        "machine_checks": 0,
        "manual_checks": 0,
        "passed": 0,
        "failed": 0,
        "errored": 0,
        "skipped": 0,
        "pending": 0,
        "automation_percentage": 0.0
    }
    
    failed_blockers = []
    pending_manuals = []
    
    for plan in plans_data:
        plan_id = plan.get("plan_id")
        checks = plan.get("checks", [])
        
        plan_result = results_dict.get(plan_id, {})
        evidence_list = plan_result.get("evidence", [])
        evidence_by_check = {e.get("check_id"): e for e in evidence_list}
        
        has_blocker_fail = False
        has_mandatory_fail = False
        has_optional_fail = False
        
        has_pending_manual = False
        has_skipped_env = False
        
        for check in checks:
            check_id = check.get("check_id")
            is_mandatory = check.get("mandatory", False)
            impact = check.get("failure_impact", "MINOR")
            is_machine = check.get("machine_verifiable", False)
            
            doc_stats["checks"] += 1
            if is_machine: doc_stats["machine_checks"] += 1
            else: doc_stats["manual_checks"] += 1
            
            ev = evidence_by_check.get(check_id)
            
            # Logic branch: Manual checks
            if not is_machine:
                doc_stats["pending"] += 1
                has_pending_manual = True
                pending_manuals.append(check_id)
                continue
                
            # Logic branch: Unexecuted or skipped machine checks
            if not ev:
                doc_stats["pending"] += 1
                has_pending_manual = True
                pending_manuals.append(check_id)
                continue
                
            verdict = ev.get("verdict")
            
            if verdict == "SKIPPED":
                doc_stats["skipped"] += 1
                has_skipped_env = True
                continue
                
            if verdict == "PASS":
                doc_stats["passed"] += 1
                continue
                
            # Logic branch: Failed or Errored
            if verdict == "FAIL": doc_stats["failed"] += 1
            elif verdict == "ERROR": doc_stats["errored"] += 1
            
            if impact == "BLOCKER":
                has_blocker_fail = True
                failed_blockers.append(check_id)
            if is_mandatory:
                has_mandatory_fail = True
            else:
                has_optional_fail = True
                
        # Plan decision derivation based on check properties
        if has_blocker_fail or has_mandatory_fail:
            verdict = "NON_COMPLIANT"
            rationale = "One or more blocker or mandatory checks failed execution."
        elif has_skipped_env:
            verdict = "PENDING"
            rationale = "Machine checks require environment unavailable during execution."
        elif has_pending_manual:
            verdict = "PENDING"
            rationale = "Manual review required. Machine checks passed or were not applicable."
        elif has_optional_fail:
            verdict = "PARTIALLY_COMPLIANT"
            rationale = "All mandatory checks passed, but some optional checks failed."
        else:
            verdict = "COMPLIANT"
            rationale = "All checks passed successfully."
            
        plan_verdicts.append({
            "plan_id": plan_id,
            "verdict": verdict,
            "rationale": rationale,
            "department": plan.get("department", "Unknown"),
            "control_name": plan.get("control_name")
        })

    # Overall document verdict
    v_set = {pv["verdict"] for pv in plan_verdicts}
    if "NON_COMPLIANT" in v_set:
        overall = "NON_COMPLIANT"
    elif "PENDING" in v_set:
        overall = "PENDING"
    elif "PARTIALLY_COMPLIANT" in v_set:
        overall = "PARTIALLY_COMPLIANT"
    elif "COMPLIANT" in v_set:
        overall = "COMPLIANT"
    else:
        overall = "PENDING"

    # Statistics Calculations
    if doc_stats["checks"] > 0:
        doc_stats["automation_percentage"] = round((doc_stats["machine_checks"] / doc_stats["checks"]) * 100, 2)
        # Compliance percentage is strictly proven passes vs total required.
        compliance_pct = round((doc_stats["passed"] / doc_stats["checks"]) * 100, 2)
    else:
        doc_stats["automation_percentage"] = 0.0
        compliance_pct = 0.0

    execution_summary = {
        "machine_passed": doc_stats["passed"],
        "machine_failed": doc_stats["failed"],
        "machine_errored": doc_stats["errored"],
        "machine_skipped": doc_stats["skipped"],
        "manual_pending": doc_stats["pending"],
        "blocker_failures": len(failed_blockers),
        "overall_verdict": overall
    }
    
    ts = datetime.now(timezone.utc)
    
    decision = {
        "document_id": doc_id,
        "execution_timestamp": ts.isoformat(),
        "overall_document_verdict": overall,
        "compliance_percentage": compliance_pct,
        "failed_blocker_list": failed_blockers,
        "pending_manual_checks": pending_manuals,
        "document_statistics": doc_stats,
        "execution_summary": execution_summary,
        "plan_verdicts": plan_verdicts
    }
    
    ts_file = ts.strftime("%Y%m%dT%H%M%S")
    out_file = OUTPUT_DIR / f"{doc_id}_{ts_file}.json"
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
        
    logger.debug(f"Generated decision for {doc_id}: {overall} -> {out_file.name}")
    return True

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    plan_files = list(PLANS_DIR.glob("*.json"))
    
    if not plan_files:
        logger.warning("No verification plans found.")
        sys.exit(0)
        
    logger.info(f"Starting Compliance Decision Engine v2 for {len(plan_files)} documents...")
    
    processed = 0
    for plan_file in plan_files:
        doc_id = plan_file.stem
        try:
            if process_document(doc_id, plan_file):
                processed += 1
        except Exception as e:
            logger.error(f"Failed to process {doc_id}: {e}", exc_info=True)
            
    logger.info(f"Completed Compliance Decision Engine. Processed {processed} documents.")

if __name__ == "__main__":
    main()
