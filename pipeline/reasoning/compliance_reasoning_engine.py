"""
Compliance Reasoning Engine V1 — RegIntel AI (SuRaksha-v2)

Provides the reasoning layer between Interpreted Controls and Verification Rule Generation.
This deterministic engine infers the regulatory intent, business process, evidence hypothesis,
and telemetry vector for each control based on its semantic attributes.

Input:  datasets/interpreted_controls/   (one JSON per document)
Output: datasets/reasoned_controls/      (one JSON per document)
"""

import json
import logging
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ---------------------------------------------------------------------------
# Output Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RegulatoryIntent:
    primary_objective: str
    mitigated_risk: str

@dataclass
class ComplianceCapability:
    capability_name: str
    capability_domain: str

@dataclass
class BusinessProcess:
    primary_process: str
    process_description: str
    operational_owner: str

@dataclass
class EvidenceHypothesis:
    ideal_evidence_description: str
    evidence_format: str

@dataclass
class EvidenceTrustAssessment:
    trust_level: str
    tamper_resistance: str

@dataclass
class TelemetryVector:
    target_system_class: str
    data_modality: str

@dataclass
class AutonomyAssessment:
    machine_verifiable: bool
    human_in_the_loop_required: bool

@dataclass
class ConfidenceMetrics:
    semantic_confidence: float
    ontology_confidence: float
    evidence_confidence: float
    automation_confidence: float
    overall_confidence: float
    reasoning_summary: str
    confidence_explanation: str

@dataclass
class ReasonedComplianceControl:
    document_id: str
    requirement_id: str
    logical_unit_id: str
    
    regulatory_intent: RegulatoryIntent
    compliance_capability: ComplianceCapability
    business_process: BusinessProcess
    evidence_hypothesis: EvidenceHypothesis
    evidence_trust_assessment: EvidenceTrustAssessment
    telemetry_vector: TelemetryVector
    autonomy_assessment: AutonomyAssessment
    confidence_metrics: ConfidenceMetrics

    # Provenance
    page_numbers: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]

    # Pass-through semantic fields from InterpretedControl
    control_name: str
    control_objective: str
    control_category: str
    candidate_departments: List[str]
    criticality: str
    risk_domain: List[str]
    compliance_domain: List[str]
    implementation_category: List[str]


# ---------------------------------------------------------------------------
# Reasoning Knowledge Base (Deterministic Ontologies)
# ---------------------------------------------------------------------------# ---------------------------------------------------------------------------
# Semantic Inference Ontologies
# ---------------------------------------------------------------------------

def _first(lst: Any, default: str = "") -> str:
    if isinstance(lst, list) and lst:
        return lst[0]
    if isinstance(lst, str):
        return lst
    return default

def _contains(text_or_list: Any, val: str) -> bool:
    if not text_or_list: return False
    target = val.lower()
    if isinstance(text_or_list, list):
        return any(target in str(i).lower() for i in text_or_list)
    return target in str(text_or_list).lower()

DOMAIN_INTENT_MAP = {
    "foreign exchange": {"obj": "Monitor cross-border capital flows and enforce limits", "risk": "Macro-Prudential Risk"},
    "treasury": {"obj": "Manage liquidity, market risk, and capital adequacy", "risk": "Market & Liquidity Risk"},
    "cyber": {"obj": "Protect information assets and ensure system resilience", "risk": "Cyber Security Risk"},
    "aml": {"obj": "Prevent money laundering and terrorism financing", "risk": "Financial Crime Risk"},
    "kyc": {"obj": "Ensure accurate customer identification and due diligence", "risk": "Financial Crime Risk"},
    "payment": {"obj": "Ensure secure, timely, and reliable fund transfers", "risk": "Operational Risk"},
    "credit": {"obj": "Manage credit exposure and ensure proper provisioning", "risk": "Credit Risk"},
    "audit": {"obj": "Provide independent assurance of compliance and controls", "risk": "Control Failure Risk"},
    "governance": {"obj": "Establish board oversight and strategic direction", "risk": "Systemic Governance Risk"},
    "customer": {"obj": "Ensure fair treatment and protect consumer rights", "risk": "Reputational Risk"},
    "risk": {"obj": "Identify, measure, and mitigate enterprise risks", "risk": "Enterprise Risk"},
    "capital": {"obj": "Maintain adequate capital buffers against shocks", "risk": "Capital Risk"},
    "liquidity": {"obj": "Ensure sufficient high-quality liquid assets", "risk": "Liquidity Risk"},
    "vendor": {"obj": "Manage third-party and outsourcing risks", "risk": "Third-Party Risk"},
    "hr": {"obj": "Ensure staff competence and ethical conduct", "risk": "Conduct Risk"},
}

CAPABILITY_PROCESS_MAP = {
    "identity": {"proc": "User Lifecycle Management", "desc": "Provisioning and de-provisioning of access rights", "owner": "IT Security"},
    "access": {"proc": "Access Control Administration", "desc": "Managing logical access to IT systems", "owner": "IT Security"},
    "encryption": {"proc": "Cryptographic Key Management", "desc": "Configuring cryptographic standards on servers", "owner": "CISO Office"},
    "audit logging": {"proc": "Security Event Monitoring", "desc": "Forwarding events to a centralized SIEM", "owner": "Security Operations Center (SOC)"},
    "transaction monitoring": {"proc": "Suspicious Activity Monitoring", "desc": "Investigating alerts and filing STRs", "owner": "AML Compliance"},
    "due diligence": {"proc": "Account Opening & KYC Updating", "desc": "Collection and verification of customer identity documents", "owner": "Retail Operations"},
    "kyc": {"proc": "Periodic KYC Updation", "desc": "Refreshing customer documentation based on risk profile", "owner": "Retail Operations"},
    "remittance": {"proc": "Cross-Border Fund Transfer", "desc": "Processing inward/outward remittances with LRS checks", "owner": "Treasury Operations"},
    "nostro": {"proc": "Nostro/Vostro Reconciliation", "desc": "Reconciling accounts with correspondent banks", "owner": "Treasury Operations"},
    "swift": {"proc": "SWIFT Messaging & Reconciliation", "desc": "Managing SWIFT gateway configurations and message flows", "owner": "Payments Team"},
    "stress test": {"proc": "Liquidity & Capital Stress Testing", "desc": "Running stress scenarios and calculating LCR/NSFR", "owner": "Risk Management"},
    "provisioning": {"proc": "NPA Classification and Provisioning", "desc": "Tagging non-performing assets and calculating provisions", "owner": "Credit Administration"},
    "board": {"proc": "Board & Committee Reporting", "desc": "Drafting, reviewing, and approving organizational policies", "owner": "Company Secretariat"},
    "grievance": {"proc": "Customer Complaint Resolution", "desc": "Tracking and resolving customer grievances within TAT", "owner": "Customer Service"},
    "vendor": {"proc": "Third-Party Risk Assessment", "desc": "Conducting due diligence on outsourced service providers", "owner": "Vendor Management"},
    "incident": {"proc": "Security Incident Response", "desc": "Detecting, analyzing, and responding to cyber incidents", "owner": "Incident Response Team"},
    "reporting": {"proc": "Regulatory Reporting", "desc": "Data aggregation and portal submission", "owner": "Compliance"}
}

EVIDENCE_TELEMETRY_MAP = {
    "Configuration_Export": {"sys": "IT Infrastructure", "modality": "API/CLI", "trust": "HIGH_IMMUTABLE"},
    "System_Log": {"sys": "SIEM / Central Log Server", "modality": "Log_Query", "trust": "HIGH_IMMUTABLE"},
    "Database_Record": {"sys": "Core Banking System (CBS)", "modality": "SQL", "trust": "MEDIUM_SYSTEM_GENERATED"},
    "Transaction_Record": {"sys": "Payment Gateway / Switch", "modality": "SQL/API", "trust": "HIGH_IMMUTABLE"},
    "Trade_Record": {"sys": "Treasury Management System (TMS)", "modality": "SQL", "trust": "MEDIUM_SYSTEM_GENERATED"},
    "Portal_Acknowledgement": {"sys": "Regulatory Portal", "modality": "Browser_Automation", "trust": "HIGH_IMMUTABLE"},
    "Digital_Document": {"sys": "Document Management System (DMS)", "modality": "NLP_Document_Analysis", "trust": "LOW_HUMAN_ATTESTED"},
    "Workflow_Ticket": {"sys": "Workflow Engine / Jira", "modality": "REST_API", "trust": "MEDIUM_SYSTEM_GENERATED"}
}


def reason_control(ctrl: Dict[str, Any]) -> ReasonedComplianceControl:
    cap_raw = ctrl.get("business_capability", "")
    domain_raw = _first(ctrl.get("compliance_domain", []), "General")
    impl_pat = ctrl.get("implementation_pattern", "")
    veri_pat = ctrl.get("verification_pattern", "")
    ctrl_cat = ctrl.get("control_category", "")

    # 1. Regulatory Intent Inference
    intent_obj = "Fulfill regulatory operational mandate"
    mit_risk = "Compliance Risk"
    sem_conf = 0.5
    for k, v in DOMAIN_INTENT_MAP.items():
        if _contains(domain_raw, k) or _contains(cap_raw, k):
            intent_obj = v["obj"]
            mit_risk = v["risk"]
            sem_conf = 0.95
            break
    
    if sem_conf == 0.5 and "Reporting" in ctrl_cat:
        intent_obj = "Ensure regulator visibility into bank operations"
        mit_risk = "Supervisory Blindness Risk"
        sem_conf = 0.8

    # 2. Business Process Inference
    proc_name = "Standard Operating Procedure"
    proc_desc = "Executing required operational workflows"
    owner = "Business Operations"
    ont_conf = 0.5
    for k, v in CAPABILITY_PROCESS_MAP.items():
        if _contains(cap_raw, k):
            proc_name = v["proc"]
            proc_desc = v["desc"]
            owner = v["owner"]
            ont_conf = 0.95
            break

    # 3. Evidence Hypothesis Inference
    ev_desc = f"Execution artifacts confirming '{cap_raw}' compliance"
    ev_fmt = "Digital_Document"
    if veri_pat == "Database Verification":
        ev_fmt = "Database_Record"
        ev_desc = f"Database record reflecting '{cap_raw}' execution state"
    elif veri_pat == "Log Analysis":
        ev_fmt = "System_Log"
        ev_desc = f"System audit logs demonstrating '{cap_raw}' activity"
    elif veri_pat == "Configuration Check":
        ev_fmt = "Configuration_Export"
        ev_desc = f"Exported system configuration enforcing '{cap_raw}'"
    elif "Reporting" in cap_raw or "Reporting" in ctrl_cat:
        ev_fmt = "Portal_Acknowledgement"
        ev_desc = "Signed submission acknowledgement receipt"
    elif impl_pat == "Workflow Creation":
        ev_fmt = "Workflow_Ticket"
        ev_desc = "Auditable workflow or ticketing system record"
    
    # 4. Telemetry Vector & Trust Computation
    tele = EVIDENCE_TELEMETRY_MAP.get(ev_fmt, EVIDENCE_TELEMETRY_MAP["Digital_Document"])
    sys_class = tele["sys"]
    modality = tele["modality"]
    trust_lvl = tele["trust"]
    ev_conf = 0.85

    # Contextual Telemetry Refinement
    if ev_fmt == "Database_Record":
        if owner == "Treasury Operations":
            sys_class = "Treasury Management System (TMS)"
        elif owner == "Payments Team":
            sys_class = "Payment Switch / Gateway"
        elif owner == "AML Compliance":
            sys_class = "AML Transaction Monitoring System"
        elif owner == "IT Security":
            sys_class = "Identity & Access Management (IAM) Database"
            
    if ev_fmt == "Configuration_Export":
        if owner == "IT Security" and (_contains(cap_raw, "identity") or _contains(cap_raw, "access")):
            sys_class = "Active Directory"
            modality = "PowerShell/LDAP"
        elif "network" in cap_raw.lower() or "firewall" in cap_raw.lower():
            sys_class = "Network Firewalls / WAF"

    # Trust Characteristics
    if trust_lvl == "HIGH_IMMUTABLE":
        tamper = "System state/logs are machine-generated and immutable by end-users."
    elif trust_lvl == "MEDIUM_SYSTEM_GENERATED":
        tamper = "System-generated but relies on mutable database states or workflows."
    else:
        tamper = "Relies on manual human attestation; highly susceptible to modification."

    # 5. Autonomy Assessment
    mv = trust_lvl in ("HIGH_IMMUTABLE", "MEDIUM_SYSTEM_GENERATED")
    hitl = not mv
    auto_conf = 0.95 if mv else 0.40

    # 6. Confidence Metrics Computation
    overall_c = round((sem_conf + ont_conf + ev_conf + auto_conf) / 4.0, 2)
    auto_expl = "High confidence in automation due to deterministic machine-readable telemetry." if mv else "Requires human-in-the-loop for document or process assessment."
    
    metrics = ConfidenceMetrics(
        semantic_confidence=sem_conf,
        ontology_confidence=ont_conf,
        evidence_confidence=ev_conf,
        automation_confidence=auto_conf,
        overall_confidence=overall_c,
        reasoning_summary=f"Inferred {sys_class} telemetry mapping for '{cap_raw}' based on '{domain_raw}' signals.",
        confidence_explanation=auto_expl
    )

    return ReasonedComplianceControl(
        document_id=ctrl.get("document_id", ""),
        requirement_id=ctrl.get("requirement_id", ""),
        logical_unit_id=ctrl.get("logical_unit_id", ""),
        regulatory_intent=RegulatoryIntent(intent_obj, mit_risk),
        compliance_capability=ComplianceCapability(cap_raw, domain_raw),
        business_process=BusinessProcess(proc_name, proc_desc, owner),
        evidence_hypothesis=EvidenceHypothesis(ev_desc, ev_fmt),
        evidence_trust_assessment=EvidenceTrustAssessment(trust_lvl, tamper),
        telemetry_vector=TelemetryVector(sys_class, modality),
        autonomy_assessment=AutonomyAssessment(mv, hitl),
        confidence_metrics=metrics,
        page_numbers=ctrl.get("page_numbers", []),
        hierarchy_node_ids=ctrl.get("hierarchy_node_ids", []),
        block_ids=ctrl.get("block_ids", []),
        control_name=ctrl.get("control_name", ""),
        control_objective=ctrl.get("control_objective", ""),
        control_category=ctrl.get("control_category", ""),
        candidate_departments=ctrl.get("candidate_departments", []),
        criticality=ctrl.get("criticality", "UNKNOWN"),
        risk_domain=ctrl.get("risk_domain", []),
        compliance_domain=ctrl.get("compliance_domain", []),
        implementation_category=ctrl.get("implementation_category", []),
    )


# ---------------------------------------------------------------------------
# Engine Orchestrator
# ---------------------------------------------------------------------------

class ComplianceReasoningEngine:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        self._ensure_directories()
        self._setup_logging()

        self.stats = {
            "documents_processed": 0,
            "controls_reasoned": 0,
            "capabilities": Counter(),
            "telemetry_systems": Counter(),
            "trust_levels": Counter(),
            "confidence_buckets": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_file = self.log_dir / "compliance_reasoning_engine.log"
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

    def _update_stats(self, rcc: ReasonedComplianceControl) -> None:
        self.stats["controls_reasoned"] += 1
        self.stats["capabilities"][rcc.compliance_capability.capability_name] += 1
        self.stats["telemetry_systems"][rcc.telemetry_vector.target_system_class] += 1
        self.stats["trust_levels"][rcc.evidence_trust_assessment.trust_level] += 1
        
        conf = rcc.confidence_metrics.overall_confidence
        if conf >= 0.9: bucket = ">= 0.9 (High)"
        elif conf >= 0.7: bucket = "0.7 - 0.89 (Medium)"
        else: bucket = "< 0.7 (Low)"
        self.stats["confidence_buckets"][bucket] += 1

    def _dataclass_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Custom converter to handle nested dataclasses easily."""
        return asdict(obj)

    def process_document(self, json_path: Path) -> None:
        import os
        import traceback
        
        print(f"1.\n{os.getcwd()}")
        print(f"2.\n{json_path}")
        print(f"3.\n{json_path.resolve()}")
        print(f"4.\n{json_path.exists()}")
        
        doc_id = json_path.stem
        print(f"5.\n{doc_id}")
        print(f"6.\n{self.output_dir}")
        print(f"7.\n{self.output_dir.resolve()}")
        
        output_file = self.output_dir / f"{doc_id}.json"
        print(f"8.\n{output_file}")
        print(f"9.\n{output_file.resolve()}")
        print(f"10.\n{output_file.exists()}")

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — reasoned controls already generated.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
            print("11.\nSuccessfully opened JSON")
        except Exception as e:
            print(f"exact exception class\n{e.__class__.__name__}")
            print(f"exact exception message\n{str(e)}")
            print(f"full traceback\n{traceback.format_exc()}")
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        interpreted_control_count = doc.get("interpreted_control_count", -1)
        print(f"12.\n{interpreted_control_count}")
        
        interpreted = doc.get("interpreted_controls", [])
        print(f"13.\n{len(interpreted)}")
        
        reasoned: List[Dict[str, Any]] = []

        print("14.\nEntering processing loop")
        for idx, ctrl in enumerate(interpreted):
            if idx == 0:
                print(f"15.\n{ctrl.get('requirement_id')}")
            try:
                rcc = reason_control(ctrl)
                if idx == 0: print("16.\nAfter reason_control()")
                self._update_stats(rcc)
                rcc_dict = self._dataclass_to_dict(rcc)
                if idx == 0: print("17.\nAfter _dataclass_to_dict()")
                reasoned.append(rcc_dict)
                if idx == 0: print("18.\nAfter appending to reasoned list")
            except Exception as e:
                print(f"exact exception class\n{e.__class__.__name__}")
                print(f"exact exception message\n{str(e)}")
                print(f"full traceback\n{traceback.format_exc()}")
                self.logger.error(f"Reasoning failed for {ctrl.get('requirement_id')}: {e}")

        print(f"19.\n{len(reasoned)}")

        output = {
            "document_id": doc_id,
            "title": doc.get("title", doc_id),
            "document_status": doc.get("document_status", "ACTIVE"),
            "reasoned_control_count": len(reasoned),
            "reasoned_controls": reasoned,
        }

        print("20.\nImmediately before opening output file")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                print("21.\nImmediately after opening output file")
                json.dump(output, f, indent=2, ensure_ascii=False)
                print("22.\nImmediately after json.dump()")
            print("23.\nImmediately after closing output file")
            self.stats["documents_processed"] += 1
            self.logger.info(f"Generated {len(reasoned)} reasoned controls for {doc_id}")
            print("23.1")
            print(output_file.exists())
            if output_file.exists():
                print(output_file.stat().st_size)
            print("23.2")
            print(list(self.output_dir.glob("*.json"))[-5:])
            print(f"24.\n{output_file.resolve()}")
        except Exception as e:
            print(f"exact exception class\n{e.__class__.__name__}")
            print(f"exact exception message\n{str(e)}")
            print(f"full traceback\n{traceback.format_exc()}")
            self.logger.error(f"Cannot write {output_file}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory not found: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} interpreted control documents to process.")

        for json_path in tqdm(json_files, desc="Reasoning controls"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        total = self.stats["controls_reasoned"]

        def fmt(c: Counter, top: int = 8) -> str:
            return "\n".join(f"  {k:<45} {v}" for k, v in c.most_common(top)) or "  (none)"

        summary = (
            f"\n{'='*70}\n"
            f" COMPLIANCE REASONING ENGINE SUMMARY\n"
            f"{'='*70}\n"
            f"Documents processed:             {self.stats['documents_processed']}\n"
            f"Reasoned controls generated:     {total}\n"
            f"\nTelemetry System Distribution:\n{fmt(self.stats['telemetry_systems'])}\n"
            f"\nEvidence Trust Distribution:\n{fmt(self.stats['trust_levels'])}\n"
            f"\nOverall Confidence Buckets:\n{fmt(self.stats['confidence_buckets'])}\n"
            f"\nOutput directory:                {self.output_dir}\n"
            f"{'='*70}\n"
        )
        print(summary)
        self.logger.info("Compliance reasoning complete.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    engine = ComplianceReasoningEngine(
        input_dir=project_root / "datasets" / "interpreted_controls",
        output_dir=project_root / "datasets" / "reasoned_controls",
        log_dir=project_root / "logs",
    )
    engine.run()
