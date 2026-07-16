import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

MAPS_DIR = project_root / "datasets" / "maps"
PLANS_DIR = project_root / "datasets" / "verification_plans"
RESULTS_DIR = project_root / "datasets" / "verification_results"
DECISIONS_DIR = project_root / "datasets" / "compliance_decisions"
OUTPUT_DIR = project_root / "datasets" / "frontend"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Loading upstream datasets...")
    
    maps_by_doc = {}
    for p in MAPS_DIR.glob("*.json"):
        maps_by_doc[p.stem] = json.loads(p.read_text(encoding="utf-8"))
        
    plans_by_doc = {}
    for p in PLANS_DIR.glob("*.json"):
        plans_by_doc[p.stem] = json.loads(p.read_text(encoding="utf-8"))

    results_by_doc = {}
    for p in RESULTS_DIR.glob("*.json"):
        results_by_doc[p.stem] = json.loads(p.read_text(encoding="utf-8"))

    decisions_by_doc = {}
    decision_files = sorted(DECISIONS_DIR.glob("*.json"))
    for p in decision_files:
        parts = p.stem.split('_')
        doc_id = f"{parts[0]}_{parts[1]}" if p.name.startswith("UP") and len(parts) >= 2 else parts[0]
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            decisions_by_doc[doc_id] = d
        except Exception:
            pass

    logger.info("Aggregating dashboard state...")

    # Executive KPIs
    kpis = {
        "total_documents": len(maps_by_doc),
        "total_maps": 0,
        "total_plans": 0,
        "total_checks": 0,
        "compliant_documents": 0,
        "partially_compliant_documents": 0,
        "non_compliant_documents": 0,
        "pending_documents": 0,
        "automation_percentage": 0.0
    }

    # Department Summary
    dept_summary = defaultdict(lambda: {"total_maps": 0, "compliant": 0, "partial": 0, "non_compliant": 0, "pending": 0})
    
    # Verification Summary
    verify_summary = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIPPED": 0, "MANUAL": 0}

    compliance_register = []
    documents_table = []
    
    global_machine_checks = 0
    global_total_checks = 0

    for doc_id, doc_maps in maps_by_doc.items():
        doc_title = doc_maps.get("title", doc_id)
        doc_status = doc_maps.get("document_status", "UNKNOWN")
        
        dec = decisions_by_doc.get(doc_id, {})
        doc_verdict = dec.get("overall_document_verdict", "UNKNOWN")
        stats = dec.get("document_statistics", {})
        exec_sum = dec.get("execution_summary", {})
        
        # Document KPI aggregation
        if doc_verdict == "COMPLIANT": kpis["compliant_documents"] += 1
        elif doc_verdict == "PARTIALLY_COMPLIANT": kpis["partially_compliant_documents"] += 1
        elif doc_verdict == "NON_COMPLIANT": kpis["non_compliant_documents"] += 1
        else: kpis["pending_documents"] += 1

        kpis["total_plans"] += stats.get("plans", 0)
        kpis["total_checks"] += stats.get("checks", 0)
        
        global_machine_checks += stats.get("machine_checks", 0)
        global_total_checks += stats.get("checks", 0)
        
        verify_summary["PASS"] += exec_sum.get("machine_passed", 0)
        verify_summary["FAIL"] += exec_sum.get("machine_failed", 0)
        verify_summary["ERROR"] += exec_sum.get("machine_errored", 0)
        verify_summary["SKIPPED"] += exec_sum.get("machine_skipped", 0)
        verify_summary["MANUAL"] += exec_sum.get("manual_pending", 0)

        # Plan dictionary for fast lookup
        plan_verdicts = {pv["plan_id"]: pv for pv in dec.get("plan_verdicts", [])}
        
        for m in doc_maps.get("maps", []):
            kpis["total_maps"] += 1
            dept = m.get("owner_department", "Unknown")
            dept_summary[dept]["total_maps"] += 1
            
            # Map rule logic: match by extracting req_id
            ctrl_id = m.get("control_id", "")
            req_id = ctrl_id.replace("_ctrl", "") if "_ctrl" in ctrl_id else None
            
            map_status = "PENDING"
            map_rationale = "No verification plan found."
            map_blockers = 0
            map_automation = 0.0
            
            if req_id:
                # Find the plan
                matching_plan_id = f"CVP_VR_{req_id}"
                pv = plan_verdicts.get(matching_plan_id)
                if pv:
                    map_status = pv.get("verdict", "PENDING")
                    map_rationale = pv.get("rationale", "")
                    # For simplicity, count blockers globally for now, or if possible per plan
                    # We can fetch the specific plan to calculate map_blockers and automation
                    doc_plans = plans_by_doc.get(doc_id, {}).get("verification_plans", [])
                    specific_plan = next((p for p in doc_plans if p.get("plan_id") == matching_plan_id), None)
                    if specific_plan:
                        map_automation = specific_plan.get("automation_percentage", 0.0)
                        # Count failed blockers by intersection of failed_blocker_list and checks in plan
                        failed_blks = dec.get("failed_blocker_list", [])
                        plan_check_ids = {c["check_id"] for c in specific_plan.get("checks", [])}
                        map_blockers = len(set(failed_blks).intersection(plan_check_ids))

            if map_status == "COMPLIANT": dept_summary[dept]["compliant"] += 1
            elif map_status == "PARTIALLY_COMPLIANT": dept_summary[dept]["partial"] += 1
            elif map_status == "NON_COMPLIANT": dept_summary[dept]["non_compliant"] += 1
            else: dept_summary[dept]["pending"] += 1

            compliance_register.append({
                "map_id": m.get("map_id"),
                "document_id": doc_id,
                "title": m.get("title"),
                "department": dept,
                "priority": m.get("priority", "MEDIUM"),
                "business_capability": m.get("compliance_domain", "Unknown"),
                "compliance_status": map_status,
                "decision_rationale": map_rationale,
                "failed_blocker_count": map_blockers,
                "automation_percentage": map_automation
            })

        documents_table.append({
            "document_id": doc_id,
            "title": doc_title,
            "status": doc_status,
            "plans": stats.get("plans", 0),
            "checks": stats.get("checks", 0),
            "verdict": doc_verdict,
            "automation_percentage": stats.get("automation_percentage", 0.0)
        })

    if global_total_checks > 0:
        kpis["automation_percentage"] = round((global_machine_checks / global_total_checks) * 100, 2)

    departments_list = []
    for dept_name, stats in dept_summary.items():
        stats["department"] = dept_name
        departments_list.append(stats)

    ts = datetime.now(timezone.utc).isoformat()
    frontend_state = {
        "metadata": {
            "generated_timestamp": ts,
            "pipeline_version": "2.0.0",
            "total_documents": len(maps_by_doc)
        },
        "executive_kpis": kpis,
        "department_summary": departments_list,
        "compliance_register": compliance_register,
        "verification_summary": verify_summary,
        "documents_table": documents_table,
        "timeline_metadata": {
            "last_pipeline_run": ts
        }
    }

    out_file = OUTPUT_DIR / "frontend_state.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(frontend_state, f, indent=2)

    logger.info(f"Dashboard Aggregator completed successfully. Output saved to {out_file}")

if __name__ == "__main__":
    main()
