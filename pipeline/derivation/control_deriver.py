"""
Compliance Control Derivation Engine V1 — RegIntel AI (SuRaksha-v2)

Transforms enriched regulatory requirements into structured Compliance Controls.
A Compliance Control represents HOW an organization should implement and verify
compliance with a requirement.

Uses a deterministic, rule-based approach with an extensible strategy architecture.
Future offline AI models can seamlessly replace these derivation strategies.
"""

import json
import logging
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tqdm import tqdm

# Ensure pipeline is in python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ---------------------------------------------------------------------------
# Base Interfaces
# ---------------------------------------------------------------------------

class BaseDeriver(ABC):
    """Abstract base class for all control derivation strategies."""
    
    @abstractmethod
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        """
        Analyzes the requirement and mutates the `control_data` dict
        with derived control fields.
        """
        pass

# ---------------------------------------------------------------------------
# Specific Derivers
# ---------------------------------------------------------------------------

class ControlObjectiveDeriver(BaseDeriver):
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        preserved_name = requirement.get("control_name", "")
        preserved_objective = requirement.get("control_objective", "")

        if preserved_name:
            control_data["control_name"] = preserved_name
        if preserved_objective:
            control_data["control_objective"] = preserved_objective

        if not preserved_name or not preserved_objective:
            action = requirement.get("action", "")
            object_ = requirement.get("object", "")
            req_type = requirement.get("requirement_type", "")

            if not preserved_objective:
                obj = f"To ensure {action} {object_}".strip()
                obj = re.sub(r'\s+', ' ', obj)
                if obj.endswith((".", ",", ";")):
                    obj = obj[:-1]
                control_data["control_objective"] = obj.capitalize()

            if not preserved_name:
                name_base = action.split()[0] if action else req_type
                if object_:
                    words = object_.split()
                    name_suffix = " ".join(words[:min(4, len(words))])
                    control_data["control_name"] = f"{name_base.capitalize()} {name_suffix}".strip()
                else:
                    control_data["control_name"] = f"{name_base.capitalize()} Control"

        control_data["control_description"] = requirement.get("full_sentence", "")


class ControlTypeDeriver(BaseDeriver):
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        icats = requirement.get("implementation_category", [])
        text = requirement.get("full_sentence", "").lower()
        req_type = requirement.get("requirement_type", "")
        
        # Control Type (Administrative, Technical, Operational)
        ctype = "Operational"
        if "Technical Control" in icats or "Configuration" in icats:
            ctype = "Technical"
        elif "Policy" in icats or "Governance" in icats or "Documentation" in icats:
            ctype = "Administrative"
        control_data["control_type"] = ctype
        
        # Preventive vs Detective vs Corrective
        p_d = "Preventive"
        if "Monitor" in icats or "Audit" in icats or "Reporting" in icats or req_type == "REPORTING":
            p_d = "Detective"
        elif re.search(r"\b(rectify|correct|remediate|restore|recover)\b", text):
            p_d = "Corrective"
        elif req_type == "PROHIBITION":
            p_d = "Preventive"
        control_data["preventive_or_detective"] = p_d


class ControlFrequencyDeriver(BaseDeriver):
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        text = requirement.get("full_sentence", "").lower()
        timeline = requirement.get("timeline", "").lower()
        
        freq = "Unknown"
        combined = f"{text} {timeline}"
        
        if re.search(r"\b(annual|annually|yearly|once a year)\b", combined):
            freq = "Annual"
        elif re.search(r"\b(quarterly|every quarter)\b", combined):
            freq = "Quarterly"
        elif re.search(r"\b(monthly|every month)\b", combined):
            freq = "Monthly"
        elif re.search(r"\b(weekly|every week)\b", combined):
            freq = "Weekly"
        elif re.search(r"\b(daily|every day)\b", combined):
            freq = "Daily"
        elif re.search(r"\b(continuous|continuously|real-time|real time|ongoing)\b", combined):
            freq = "Continuous"
        elif re.search(r"\b(event|upon|in case of|incident|breach|when)\b", combined) or timeline:
            # If there's a timeline like 'within 30 days', it's usually event-driven
            freq = "Event Driven"
        elif "Policy" in requirement.get("implementation_category", []):
            freq = "Annual"  # Policy reviews are typically annual
            
        control_data["control_frequency"] = freq


class ImplementationMethodDeriver(BaseDeriver):
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        action = requirement.get("action", "")
        object_ = requirement.get("object", "")
        icats = requirement.get("implementation_category", [])
        
        # Determine specific implementation category from broad ones
        mapped_cat = "Procedure"
        if "Policy" in icats:
            mapped_cat = "Policy"
        elif "Technical Control" in icats or "Configuration" in icats:
            if re.search(r"\b(access|password|authenticate)\b", object_.lower()):
                mapped_cat = "Access Control"
            elif re.search(r"\b(encrypt|cryptography)\b", object_.lower()):
                mapped_cat = "Encryption"
            elif re.search(r"\b(backup|restore)\b", object_.lower()):
                mapped_cat = "Backup"
            elif re.search(r"\b(log|audit trail)\b", object_.lower()):
                mapped_cat = "Logging"
            else:
                mapped_cat = "System Control"
        elif "Reporting" in icats:
            mapped_cat = "Reporting"
        elif "Monitoring" in icats:
            mapped_cat = "Monitoring"
        elif "Training" in icats:
            mapped_cat = "Training"
        elif "Audit" in icats:
            mapped_cat = "Audit"
            
        control_data["implementation_category"] = mapped_cat
        
        # Construct method description
        if mapped_cat == "Policy":
            method = f"Establish and maintain policy to {action} {object_}"
        elif mapped_cat in ["System Control", "Access Control", "Encryption", "Configuration"]:
            method = f"Implement technical controls to configure system to {action} {object_}"
        elif mapped_cat == "Reporting":
            method = f"Implement reporting procedure to {action} {object_}"
        else:
            method = f"Implement operational procedure to {action} {object_}"
            
        method = re.sub(r'\s+', ' ', method).strip()
        if method.endswith((".", ",", ";")):
            method = method[:-1]
            
        control_data["implementation_method"] = method.capitalize()


class EvidenceAndVerificationDeriver(BaseDeriver):
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        mapped_cat = control_data.get("implementation_category", "")
        ctype = control_data.get("control_type", "")
        text = requirement.get("full_sentence", "").lower()
        
        v_methods = []
        evidence = []
        is_automated = False
        automation_possible = False
        automation_candidate = ""
        
        if mapped_cat == "Policy":
            v_methods.append("Policy Review")
            evidence.append("Approved Policy Document")
            
        elif ctype == "Technical" or mapped_cat in ["System Control", "Access Control", "Encryption", "Logging", "Backup"]:
            v_methods.append("Configuration Review")
            automation_possible = True
            is_automated = True
            
            if "windows" in text or "active directory" in text:
                v_methods.append("PowerShell")
                evidence.append("PowerShell Output")
                automation_candidate = "PowerShell"
            elif "database" in text or "sql" in text:
                v_methods.append("SQL Query")
                evidence.append("Query Result Set")
                automation_candidate = "SQL"
            elif "registry" in text:
                v_methods.append("Registry Check")
                evidence.append("Registry Key Value")
                automation_candidate = "Windows Registry"
            elif "api" in text or "interface" in text:
                v_methods.append("API Validation")
                evidence.append("API Response JSON")
                automation_candidate = "API"
            else:
                v_methods.append("System Validation")
                evidence.append("System Configuration Screenshot")
                automation_candidate = "Configuration Parser"
                
        elif mapped_cat == "Audit":
            v_methods.append("Manual Audit")
            evidence.append("Audit Report")
            
        elif mapped_cat == "Training":
            v_methods.append("Document Review")
            evidence.append("Training Records")
            
        elif mapped_cat == "Reporting":
            v_methods.append("Document Review")
            evidence.append("Submitted Report Copy")
            evidence.append("Submission Acknowledgement")
            
        elif mapped_cat == "Logging" or "log" in text:
            v_methods.append("Log Review")
            evidence.append("System Access/Audit Logs")
            
        else:
            v_methods.append("Document Review")
            evidence.append("Standard Operating Procedure (SOP)")
            
        if not v_methods:
            v_methods.append("Unknown")
            evidence.append("Unknown Evidence")
            
        control_data["verification_method"] = v_methods
        control_data["expected_evidence"] = evidence
        control_data["manual_or_automated"] = "Automated" if is_automated else "Manual"
        control_data["automation_possible"] = automation_possible
        if automation_possible and automation_candidate:
            control_data["automation_candidate"] = automation_candidate
        

class PassThroughDeriver(BaseDeriver):
    """Passes through relevant context from the requirement directly to the control."""
    def derive(self, requirement: Dict[str, Any], control_data: Dict[str, Any]) -> None:
        control_data["requirement_id"] = requirement.get("requirement_id")
        control_data["document_id"] = requirement.get("document_id")
        control_data["logical_unit_id"] = requirement.get("logical_unit_id")
        
        control_data["criticality"] = requirement.get("criticality", "UNKNOWN")
        control_data["candidate_departments"] = requirement.get("candidate_departments", [])
        
        control_data["related_risk_domain"] = requirement.get("risk_domain", [])
        control_data["related_compliance_domain"] = requirement.get("compliance_domain", [])
        control_data["related_keywords"] = requirement.get("regulatory_keywords", [])
        
        # Controls inherent uncertainty from requirement
        control_data["confidence"] = requirement.get("confidence", 0.5)
        
        # Provenance mapping
        control_data["page_numbers"] = requirement.get("page_numbers", [])
        control_data["hierarchy_node_ids"] = requirement.get("hierarchy_node_ids", [])
        control_data["block_ids"] = requirement.get("block_ids", [])


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ControlDerivationEngine:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        
        self._ensure_directories()
        self._setup_logging()
        
        self.derivers: List[BaseDeriver] = [
            ControlObjectiveDeriver(),
            ControlTypeDeriver(),
            ControlFrequencyDeriver(),
            ImplementationMethodDeriver(),
            EvidenceAndVerificationDeriver(),
            PassThroughDeriver(),
        ]
        
        self.stats = {
            "documents_processed": 0,
            "requirements_processed": 0,
            "controls_generated": 0,
            "control_types": Counter(),
            "implementation_categories": Counter(),
            "verification_methods": Counter(),
            "evidences": Counter(),
            "automation_candidates": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        log_file = self.log_dir / "control_deriver.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger("").addHandler(console)
        self.logger = logging.getLogger(__name__)

    def _derive_control(self, requirement: Dict[str, Any], seq: int) -> Dict[str, Any]:
        """Applies all derivation strategies to produce one control."""
        doc_id = requirement.get("document_id")
        req_id = requirement.get("requirement_id", "reqX").split("_")[-1]
        control_data: Dict[str, Any] = {
            "control_id": f"{doc_id}_ctrl_{req_id}_{seq}"
        }
        
        for deriver in self.derivers:
            try:
                deriver.derive(requirement, control_data)
            except Exception as e:
                self.logger.warning(f"Deriver {deriver.__class__.__name__} failed on {requirement.get('requirement_id')}: {e}")
                
        return control_data

    def _update_stats(self, control: Dict[str, Any]) -> None:
        self.stats["controls_generated"] += 1
        self.stats["control_types"][control.get("control_type", "Unknown")] += 1
        self.stats["implementation_categories"][control.get("implementation_category", "Unknown")] += 1
        
        for vm in control.get("verification_method", []):
            self.stats["verification_methods"][vm] += 1
            
        for ev in control.get("expected_evidence", []):
            self.stats["evidences"][ev] += 1
            
        if control.get("automation_possible"):
            cand = control.get("automation_candidate", "Unknown Platform")
            self.stats["automation_candidates"][cand] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"
        
        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — controls already derived.")
            return

        self.logger.info(f"Deriving controls for: {json_path.name}")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return
            
        try:
            requirements = doc.get("reasoned_controls") or []
            controls = []
            
            for req in requirements:
                self.stats["requirements_processed"] += 1
                try:
                    # In V1, 1 requirement -> 1 primary control.
                    # Architecture allows 1-to-many logic here in the future.
                    ctrl = self._derive_control(req, 1)
                    controls.append(ctrl)
                    self._update_stats(ctrl)
                except Exception as e:
                    self.logger.error(f"Error deriving control for req {req.get('requirement_id')}: {e}")
                    
            output = {
                "document_id": doc_id,
                "title": doc.get("title", doc_id),
                "document_status": doc.get("document_status", "ACTIVE"),
                "control_count": len(controls),
                "controls": controls
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
                
            self.stats["documents_processed"] += 1
            
        except Exception as e:
            self.logger.error(f"Critical error deriving controls for {doc_id}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} enriched requirement documents to process.")

        for json_path in tqdm(json_files, desc="Deriving controls"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        reqs = self.stats["requirements_processed"]
        ctrls = self.stats["controls_generated"]
        avg_ctrls = ctrls / reqs if reqs > 0 else 0.0
        
        def format_counter(c: Counter) -> str:
            return "\n".join(f"  {k:<28} {v}" for k, v in c.most_common(6)) or "  (none)"
            
        summary = (
            f"\n{'='*55}\n"
            f" COMPLIANCE CONTROL DERIVATION ENGINE SUMMARY\n"
            f"{'='*55}\n"
            f"Documents processed:           {self.stats['documents_processed']}\n"
            f"Requirements processed:        {reqs}\n"
            f"Controls generated:            {ctrls}\n"
            f"Average controls/requirement:  {avg_ctrls:.2f}\n"
            f"\nControl Type Distribution:\n{format_counter(self.stats['control_types'])}\n"
            f"\nImplementation Category Distribution:\n{format_counter(self.stats['implementation_categories'])}\n"
            f"\nAutomation Candidates:\n{format_counter(self.stats['automation_candidates'])}\n"
            f"\nVerification Method Distribution:\n{format_counter(self.stats['verification_methods'])}\n"
            f"\nExpected Evidence Distribution:\n{format_counter(self.stats['evidences'])}\n"
            f"\nOutput directory:              {self.output_dir}\n"
            f"{'='*55}\n"
        )
        print(summary)
        self.logger.info("Control derivation pipeline completed.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "enriched_requirements"
    output_directory = project_root / "datasets" / "controls"
    log_directory = project_root / "logs"

    deriver = ControlDerivationEngine(input_directory, output_directory, log_directory)
    deriver.run()
