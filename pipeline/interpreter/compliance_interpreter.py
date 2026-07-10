"""
Compliance Interpretation Engine V1 — RegIntel AI (SuRaksha-v2)

Transforms enriched regulatory requirements into semantically meaningful,
enterprise-grade Compliance Controls. Controls are modelled after real GRC
platform artefacts (RSA Archer, ServiceNow GRC, MetricStream, IBM OpenPages).

This engine sits between the Requirement Enrichment stage and the downstream
MAP generation stage. It replaces syntactic control names derived from
regulatory fragments with business-capability-oriented controls.

Interpretation uses deterministic, rule-based reasoning over the enriched
requirement's semantic signals: compliance_domain, risk_domain, requirement_type,
implementation_category, actor, action, conditions, regulatory_entities, and
regulatory_keywords.
"""

import json
import logging
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# ---------------------------------------------------------------------------
# Output Data Class
# ---------------------------------------------------------------------------

@dataclass
class InterpretedControl:
    requirement_id: str
    document_id: str
    logical_unit_id: str

    # Core interpretation outputs
    business_capability: str
    control_name: str
    control_objective: str
    control_scope: str
    control_category: str
    control_owner: str
    implementation_pattern: str
    verification_pattern: str
    automation_feasibility: str
    automation_rationale: str
    business_rationale: str
    control_summary: str

    # Preserved provenance
    requirement_type: str
    criticality: str
    compliance_domain: List[str]
    risk_domain: List[str]
    candidate_departments: List[str]
    page_numbers: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]
    confidence: float


# ---------------------------------------------------------------------------
# Business Capability Knowledge Base
# ---------------------------------------------------------------------------
# Each entry: (match_signals, capability_name)
# Signals are tuples of (field, value) — all values are matched case-insensitively
# The first matching rule wins.

CAPABILITY_RULES: List[Tuple[Dict[str, Any], str]] = [
    # Cyber Security
    ({"compliance_domain": "Cyber Security", "implementation_category": "Access Control"}, "Identity & Access Management"),
    ({"compliance_domain": "Cyber Security", "implementation_category": "Encryption"}, "Data Encryption & Cryptography Governance"),
    ({"compliance_domain": "Cyber Security", "implementation_category": "Logging"}, "Audit Logging & Security Monitoring"),
    ({"compliance_domain": "Cyber Security", "implementation_category": "Monitoring"}, "Cyber Threat Monitoring"),
    ({"compliance_domain": "Cyber Security", "implementation_category": "System Control"}, "Cyber Security Technical Controls"),
    ({"compliance_domain": "Cyber Security", "implementation_category": "Policy"}, "Cyber Security Governance"),
    ({"compliance_domain": "Cyber Security"}, "Cyber Security Governance"),
    ({"compliance_domain": "IT Governance", "implementation_category": "Policy"}, "IT Governance Framework"),
    ({"compliance_domain": "IT Governance", "implementation_category": "Monitoring"}, "IT Infrastructure Monitoring"),
    ({"compliance_domain": "IT Governance"}, "IT Governance Framework"),
    # KYC / AML
    ({"compliance_domain": "KYC", "requirement_type": "OBLIGATION"}, "Customer Due Diligence"),
    ({"compliance_domain": "KYC", "requirement_type": "REPORTING"}, "KYC Regulatory Reporting"),
    ({"compliance_domain": "KYC"}, "Know Your Customer (KYC) Compliance"),
    ({"compliance_domain": "AML", "requirement_type": "REPORTING"}, "Suspicious Transaction Reporting"),
    ({"compliance_domain": "AML", "requirement_type": "OBLIGATION"}, "Anti-Money Laundering Controls"),
    ({"compliance_domain": "AML"}, "Anti-Money Laundering Governance"),
    # Fraud
    ({"compliance_domain": "Fraud Risk", "requirement_type": "PROHIBITION"}, "Fraud Prevention Control"),
    ({"compliance_domain": "Fraud Risk", "requirement_type": "MONITORING"}, "Fraud Detection & Monitoring"),
    ({"compliance_domain": "Fraud Risk"}, "Fraud Risk Management"),
    # Foreign Exchange
    ({"compliance_domain": "Foreign Exchange", "requirement_type": "REPORTING"}, "Foreign Exchange Regulatory Reporting"),
    ({"compliance_domain": "Foreign Exchange", "requirement_type": "OBLIGATION"}, "FEMA Compliance Control"),
    ({"compliance_domain": "Foreign Exchange", "requirement_type": "PROHIBITION"}, "Foreign Exchange Restriction Enforcement"),
    ({"compliance_domain": "Foreign Exchange"}, "Foreign Exchange Compliance"),
    # Reporting
    ({"compliance_domain": "Reporting", "requirement_type": "REPORTING"}, "Regulatory Return Submission"),
    ({"compliance_domain": "Reporting", "requirement_type": "OBLIGATION"}, "Regulatory Disclosure Obligation"),
    ({"compliance_domain": "Reporting"}, "Regulatory Reporting Governance"),
    # Prudential / Capital / Liquidity
    ({"compliance_domain": "Capital Adequacy"}, "Capital Adequacy Management"),
    ({"compliance_domain": "Prudential Regulation", "requirement_type": "OBLIGATION"}, "Prudential Norm Compliance"),
    ({"compliance_domain": "Prudential Regulation"}, "Prudential Risk Framework"),
    ({"compliance_domain": "Liquidity"}, "Liquidity Risk Management"),
    # Outsourcing
    ({"compliance_domain": "Outsourcing", "requirement_type": "OBLIGATION"}, "Third-Party Risk Management"),
    ({"compliance_domain": "Outsourcing"}, "Vendor & Outsourcing Governance"),
    # Digital Payments
    ({"compliance_domain": "Digital Payments", "requirement_type": "OBLIGATION"}, "Payment System Compliance"),
    ({"compliance_domain": "Digital Payments"}, "Digital Payments Governance"),
    # Customer Protection
    ({"compliance_domain": "Customer Protection", "requirement_type": "OBLIGATION"}, "Customer Rights & Protection"),
    ({"compliance_domain": "Customer Protection"}, "Customer Grievance & Protection Governance"),
    # Treasury
    ({"compliance_domain": "Treasury"}, "Treasury & Investment Control"),
    # Governance
    ({"compliance_domain": "Governance", "implementation_category": "Policy"}, "Corporate Governance Policy"),
    ({"compliance_domain": "Governance", "requirement_type": "OBLIGATION"}, "Governance Obligation Compliance"),
    ({"compliance_domain": "Governance"}, "Corporate Governance Framework"),
    # Audit
    ({"compliance_domain": "Audit", "requirement_type": "OBLIGATION"}, "Internal Audit Compliance"),
    ({"compliance_domain": "Audit"}, "Audit Governance"),
    # Risk Management
    ({"compliance_domain": "Risk Management", "requirement_type": "OBLIGATION"}, "Enterprise Risk Management Control"),
    ({"compliance_domain": "Risk Management"}, "Risk Management Framework"),
    # Risk domains fallback
    ({"risk_domain": "Operational Risk"}, "Operational Risk Control"),
    ({"risk_domain": "Technology Risk"}, "Technology Risk Management"),
    ({"risk_domain": "Reputational Risk"}, "Reputational Risk Governance"),
    # Type fallbacks
    ({"requirement_type": "REPORTING"}, "Regulatory Reporting Obligation"),
    ({"requirement_type": "PROHIBITION"}, "Regulatory Prohibition Enforcement"),
    ({"requirement_type": "OBLIGATION"}, "Regulatory Compliance Obligation"),
    ({"requirement_type": "PERMISSION"}, "Regulatory Permission Governance"),
    ({"requirement_type": "DEFINITION"}, "Regulatory Definition & Scope"),
    ({"requirement_type": "EXCEPTION"}, "Regulatory Exception Management"),
    ({"requirement_type": "RECOMMENDATION"}, "Regulatory Best Practice Advisory"),
]


CONTROL_CATEGORY_MAP: Dict[str, str] = {
    "OBLIGATION": "Operational",
    "PROHIBITION": "Preventive",
    "REPORTING": "Reporting",
    "RECOMMENDATION": "Advisory",
    "PERMISSION": "Governance",
    "DEFINITION": "Governance",
    "EXCEPTION": "Corrective",
    "MONITORING": "Monitoring",
}

IMPL_CAT_TO_CONTROL_CATEGORY: Dict[str, str] = {
    "Policy": "Policy",
    "Technical Control": "Technical",
    "Configuration": "Technical",
    "System Control": "Technical",
    "Monitoring": "Monitoring",
    "Reporting": "Reporting",
    "Access Control": "Security",
    "Encryption": "Security",
    "Logging": "Monitoring",
    "Audit": "Governance",
    "Training": "Operational",
    "Documentation": "Operational",
    "Approval": "Governance",
    "Backup": "Technical",
}

IMPL_PATTERN_MAP: Dict[str, str] = {
    "Policy": "Policy Update",
    "Technical Control": "System Deployment",
    "Configuration": "Configuration Change",
    "System Control": "System Deployment",
    "Monitoring": "Monitoring",
    "Reporting": "Periodic Review",
    "Access Control": "Access Review",
    "Encryption": "Configuration Change",
    "Logging": "System Deployment",
    "Audit": "Evidence Collection",
    "Training": "Employee Training",
    "Documentation": "Evidence Collection",
    "Approval": "Approval Workflow",
    "Backup": "Configuration Change",
}

VERIFICATION_PATTERN_MAP: Dict[str, str] = {
    "Policy": "Document Review",
    "Technical Control": "Configuration Export",
    "Configuration": "Configuration Export",
    "System Control": "Configuration Export",
    "Monitoring": "Log Review",
    "Reporting": "Evidence Review",
    "Access Control": "PowerShell",
    "Encryption": "Configuration Export",
    "Logging": "Log Review",
    "Audit": "Manual Audit",
    "Training": "Evidence Review",
    "Documentation": "Document Review",
    "Approval": "Document Review",
    "Backup": "CMD",
}

AUTOMATION_RULES: Dict[str, Tuple[str, str]] = {
    "Access Control": ("High", "Access control policies can be verified programmatically via PowerShell, Active Directory queries, or LDAP inspection without human intervention."),
    "Configuration": ("High", "System configuration parameters can be exported and validated against baselines using scripted configuration parsers or GPO audit tools."),
    "System Control": ("High", "Technical controls are inherently system-state assertions that can be verified by querying system APIs, registries, or command-line tooling."),
    "Encryption": ("High", "Encryption settings are machine-readable and can be verified through certificate inspection, cipher suite enumeration, or system configuration audit."),
    "Logging": ("High", "Log pipeline configurations are observable and testable through log aggregation queries or SIEM rule validation."),
    "Monitoring": ("Medium", "Monitoring controls can be partially automated by validating alerting configurations, but human review of alert triage quality remains necessary."),
    "Technical Control": ("High", "Technical controls produce machine-readable system state that can be queried through automated scripts."),
    "Policy": ("Low", "Policy controls require human judgment to evaluate completeness, appropriateness, and board-level approval status. Existence checks can be automated."),
    "Reporting": ("Medium", "Report generation and submission can be automated, but regulatory data quality validation requires human review."),
    "Audit": ("Low", "Audit quality assessment requires professional judgment. Automated pre-checks can verify audit coverage but cannot replace auditor opinion."),
    "Training": ("Low", "Training effectiveness is measured through assessment scores and attendance, which can be tracked, but content quality requires human evaluation."),
    "Documentation": ("Low", "Documentation completeness can be verified programmatically, but adequacy and accuracy require human review."),
    "Approval": ("Low", "Approval workflows can be tracked in workflow systems, but approval quality and appropriateness require human governance."),
}


# ---------------------------------------------------------------------------
# Core Interpretation Functions
# ---------------------------------------------------------------------------

def _first_item(lst: Any, default: str = "") -> str:
    if isinstance(lst, list) and lst:
        return lst[0]
    if isinstance(lst, str):
        return lst
    return default


def _contains(lst: Any, value: str) -> bool:
    if isinstance(lst, list):
        return any(value.lower() in str(v).lower() for v in lst)
    if isinstance(lst, str):
        return value.lower() in lst.lower()
    return False


def _match_capability(req: Dict[str, Any]) -> str:
    """Apply capability rules in priority order, return first match."""
    compliance_domains = req.get("compliance_domain", [])
    risk_domains = req.get("risk_domain", [])
    req_type = req.get("requirement_type", "")
    impl_cats = req.get("implementation_category", [])
    impl_cat = _first_item(impl_cats)

    for rule_signals, capability in CAPABILITY_RULES:
        matched = True
        for field, value in rule_signals.items():
            if field == "compliance_domain":
                if not _contains(compliance_domains, value):
                    matched = False
                    break
            elif field == "risk_domain":
                if not _contains(risk_domains, value):
                    matched = False
                    break
            elif field == "requirement_type":
                if req_type.upper() != value.upper():
                    matched = False
                    break
            elif field == "implementation_category":
                if not _contains(impl_cats, value):
                    matched = False
                    break
        if matched:
            return capability

    return "Regulatory Compliance Control"


def _derive_control_name(req: Dict[str, Any], capability: str) -> str:
    """Generate a concise, business-oriented control name."""
    req_type = req.get("requirement_type", "")
    compliance_domains = req.get("compliance_domain", [])
    actor = req.get("actor", "").strip()
    impl_cat = _first_item(req.get("implementation_category", []))

    # Type suffix
    type_suffixes = {
        "OBLIGATION": "Compliance Control",
        "PROHIBITION": "Restriction Control",
        "REPORTING": "Reporting Control",
        "MONITORING": "Monitoring Control",
        "RECOMMENDATION": "Advisory Control",
        "PERMISSION": "Authorisation Control",
        "DEFINITION": "Scope Definition",
        "EXCEPTION": "Exception Control",
    }
    suffix = type_suffixes.get(req_type, "Control")

    # Domain prefix
    domain = _first_item(compliance_domains, "Regulatory")
    if domain == "General":
        # Fall back to risk domain
        risk = _first_item(req.get("risk_domain", []))
        if risk and risk != "Unknown":
            domain = risk.replace(" Risk", "")

    # Combine: avoid repeating the same word
    cap_words = set(capability.lower().split())
    domain_words = domain.lower().split()
    domain_prefix = " ".join(w.capitalize() for w in domain_words if w not in cap_words)

    if domain_prefix:
        name = f"{domain_prefix} {suffix}"
    else:
        name = f"{capability} — {suffix}"

    return name


def _derive_control_category(req: Dict[str, Any]) -> str:
    impl_cats = req.get("implementation_category", [])
    req_type = req.get("requirement_type", "")

    for cat in (impl_cats if isinstance(impl_cats, list) else [impl_cats]):
        if cat in IMPL_CAT_TO_CONTROL_CATEGORY:
            return IMPL_CAT_TO_CONTROL_CATEGORY[cat]

    return CONTROL_CATEGORY_MAP.get(req_type, "Operational")


def _derive_control_owner(req: Dict[str, Any]) -> str:
    depts = req.get("candidate_departments", [])
    if depts and depts[0] != "Unknown":
        return depts[0]
    compliance_domains = req.get("compliance_domain", [])
    if _contains(compliance_domains, "Cyber Security") or _contains(compliance_domains, "IT Governance"):
        return "IT / Cyber Security"
    if _contains(compliance_domains, "AML") or _contains(compliance_domains, "KYC"):
        return "Compliance"
    if _contains(compliance_domains, "Reporting"):
        return "Compliance"
    if _contains(compliance_domains, "Treasury"):
        return "Treasury"
    return "Compliance"


def _derive_implementation_pattern(req: Dict[str, Any]) -> str:
    impl_cats = req.get("implementation_category", [])
    for cat in (impl_cats if isinstance(impl_cats, list) else [impl_cats]):
        if cat in IMPL_PATTERN_MAP:
            return IMPL_PATTERN_MAP[cat]
    req_type = req.get("requirement_type", "")
    if req_type == "REPORTING":
        return "Periodic Review"
    if req_type == "PROHIBITION":
        return "Policy Update"
    if req_type == "MONITORING":
        return "Monitoring"
    return "Workflow Creation"


def _derive_verification_pattern(req: Dict[str, Any]) -> str:
    impl_cats = req.get("implementation_category", [])
    vstrat = req.get("verification_strategy", [])
    if vstrat and isinstance(vstrat, list) and vstrat[0] not in ("Unknown", "Document Review"):
        return vstrat[0]
    for cat in (impl_cats if isinstance(impl_cats, list) else [impl_cats]):
        if cat in VERIFICATION_PATTERN_MAP:
            return VERIFICATION_PATTERN_MAP[cat]
    return "Manual Audit"


def _derive_automation(req: Dict[str, Any]) -> Tuple[str, str]:
    impl_cats = req.get("implementation_category", [])
    for cat in (impl_cats if isinstance(impl_cats, list) else [impl_cats]):
        if cat in AUTOMATION_RULES:
            return AUTOMATION_RULES[cat]
    req_type = req.get("requirement_type", "")
    if req_type == "REPORTING":
        return ("Medium", "Regulatory report generation can be scripted, but data quality validation and signatory approval require human oversight.")
    if req_type == "OBLIGATION":
        return ("Low", "Obligation fulfilment involves organisational processes and human decisions that cannot be fully automated.")
    if req_type == "PROHIBITION":
        return ("Medium", "Prohibition enforcement can leverage automated system guardrails, but exception handling and investigation require human review.")
    return ("Low", "This control type relies primarily on human judgment and process adherence, limiting automation applicability.")


def _derive_control_objective(req: Dict[str, Any], capability: str) -> str:
    req_type = req.get("requirement_type", "OBLIGATION")
    compliance_domains = req.get("compliance_domain", [])
    domain = _first_item(compliance_domains, "regulatory")
    actor = req.get("actor", "the institution").strip() or "the institution"

    verbs = {
        "OBLIGATION": "ensure that",
        "PROHIBITION": "prevent",
        "REPORTING": "ensure timely submission of",
        "MONITORING": "continuously monitor",
        "RECOMMENDATION": "promote adoption of",
        "PERMISSION": "establish authorised procedures for",
        "DEFINITION": "formally establish the scope of",
        "EXCEPTION": "govern permissible exceptions to",
    }
    verb = verbs.get(req_type, "ensure compliance with")

    return (
        f"To {verb} all applicable {domain} requirements relating to "
        f"'{capability}', thereby enabling {actor} to demonstrate full "
        f"regulatory adherence and reduce {_first_item(req.get('risk_domain', ['compliance']), 'compliance')} exposure."
    )


def _derive_control_scope(req: Dict[str, Any]) -> str:
    actor = req.get("actor", "").strip()
    compliance_domains = req.get("compliance_domain", [])
    entities = req.get("regulatory_entities", [])
    depts = req.get("candidate_departments", [])

    scope_parts = []
    if entities:
        scope_parts.append("Applicable entities: " + ", ".join(entities[:4]))
    if depts and depts[0] != "Unknown":
        scope_parts.append("Responsible departments: " + ", ".join(depts[:3]))
    if compliance_domains:
        scope_parts.append("Regulatory domain: " + ", ".join(compliance_domains[:2]))

    if scope_parts:
        return ". ".join(scope_parts) + "."
    return f"Applies to all business units and functions engaged in {_first_item(compliance_domains, 'regulatory')} activities."


def _derive_business_rationale(req: Dict[str, Any], capability: str) -> str:
    """Generate a bank-oriented business rationale distinct from regulatory text."""
    compliance_domains = req.get("compliance_domain", [])
    risk_domains = req.get("risk_domain", [])
    criticality = req.get("criticality", "MEDIUM")
    req_type = req.get("requirement_type", "OBLIGATION")
    domain = _first_item(compliance_domains, "regulatory")
    risk = _first_item(risk_domains, "compliance")

    rationale_templates = {
        "Cyber Security": (
            "Financial institutions are prime targets for cyber attacks. Without robust cyber controls, "
            "the bank faces operational disruption, customer data breaches, and potential regulatory sanctions "
            "including licence revocation. Implementing '{cap}' reduces the attack surface and demonstrates "
            "security maturity to regulators and customers alike."
        ),
        "KYC": (
            "Inadequate customer due diligence exposes the institution to exploitation by financial criminals. "
            "'{cap}' ensures that customer identities are verified and risk-profiled before account opening, "
            "protecting the institution from being used as a conduit for money laundering, terrorist financing, "
            "or fraud — all of which carry severe regulatory and reputational consequences."
        ),
        "AML": (
            "Anti-money laundering failures result in some of the largest regulatory fines globally. "
            "'{cap}' ensures that suspicious activity is detected, reported, and investigated in a timely manner, "
            "protecting the institution from complicity in financial crime and from regulatory enforcement action."
        ),
        "Foreign Exchange": (
            "FEMA violations attract compounding penalties and adverse regulatory attention. "
            "'{cap}' ensures that all foreign exchange transactions are authorised, documented, and reported "
            "in accordance with RBI Master Directions, protecting the institution from financial and legal liability."
        ),
        "Reporting": (
            "Late, inaccurate, or missing regulatory returns invite regulatory scrutiny and can trigger supervisory action. "
            "'{cap}' ensures that reporting obligations are met accurately and on time, maintaining the "
            "institution's supervisory standing and avoiding penalties."
        ),
        "Capital Adequacy": (
            "Maintaining adequate capital is a fundamental prudential requirement. Breaching capital norms "
            "can trigger prompt corrective action, restrict the institution's business activities, and "
            "undermine depositor and investor confidence. '{cap}' ensures capital positions are continuously "
            "monitored and maintained above regulatory minima."
        ),
        "Liquidity": (
            "Liquidity shortfalls can result in the inability to meet depositor obligations, triggering bank runs "
            "and systemic risk. '{cap}' ensures that liquidity buffers are maintained and stress scenarios are "
            "regularly tested to avoid funding crises."
        ),
        "Outsourcing": (
            "Third-party failures can directly impact the institution's own regulatory obligations. "
            "'{cap}' ensures that vendors and outsourced service providers are subject to appropriate due diligence, "
            "contractual safeguards, and ongoing monitoring, preventing operational and reputational failures "
            "from propagating through the supply chain."
        ),
        "Customer Protection": (
            "Failure to protect customer interests invites regulatory intervention and reputational damage. "
            "'{cap}' ensures that customer rights are respected, grievances are addressed promptly, and "
            "the institution maintains public trust."
        ),
        "Governance": (
            "Strong governance is the foundation of sustainable regulatory compliance. "
            "'{cap}' ensures that decision-making structures, oversight mechanisms, and accountability "
            "frameworks are in place to manage regulatory obligations proactively, reducing the risk of "
            "systemic compliance failures."
        ),
    }

    for key, template in rationale_templates.items():
        if _contains(compliance_domains, key):
            return template.format(cap=capability)

    # Generic fallback
    return (
        f"Failure to implement '{capability}' creates uncontrolled {risk} exposure for the institution. "
        f"Under RBI's supervisory framework, non-compliance with {domain} requirements can result in "
        f"regulatory censure, financial penalties, and reputational harm. "
        f"This control operationalises the institution's commitment to regulatory adherence and risk management."
    )


def _derive_control_summary(req: Dict[str, Any], capability: str, control_name: str, category: str) -> str:
    req_type = req.get("requirement_type", "OBLIGATION")
    impl_pattern = _derive_implementation_pattern(req)
    verify_pattern = _derive_verification_pattern(req)
    owner = _derive_control_owner(req)
    criticality = req.get("criticality", "MEDIUM")

    return (
        f"[{criticality}] {control_name} is a {category.lower()} control supporting the "
        f"'{capability}' business capability. Implementation follows the '{impl_pattern}' pattern "
        f"and is owned by the {owner} function. "
        f"Compliance is verified through {verify_pattern.lower()}."
    )


# ---------------------------------------------------------------------------
# Interpretation Orchestrator
# ---------------------------------------------------------------------------

def interpret_requirement(req: Dict[str, Any]) -> InterpretedControl:
    """Interpret a single enriched requirement into a business-grade control."""
    capability = _match_capability(req)
    control_name = _derive_control_name(req, capability)
    control_category = _derive_control_category(req)
    control_owner = _derive_control_owner(req)
    impl_pattern = _derive_implementation_pattern(req)
    verify_pattern = _derive_verification_pattern(req)
    auto_feas, auto_rationale = _derive_automation(req)
    control_objective = _derive_control_objective(req, capability)
    control_scope = _derive_control_scope(req)
    business_rationale = _derive_business_rationale(req, capability)
    control_summary = _derive_control_summary(req, capability, control_name, control_category)

    return InterpretedControl(
        requirement_id=req.get("requirement_id", ""),
        document_id=req.get("document_id", ""),
        logical_unit_id=req.get("logical_unit_id", ""),
        business_capability=capability,
        control_name=control_name,
        control_objective=control_objective,
        control_scope=control_scope,
        control_category=control_category,
        control_owner=control_owner,
        implementation_pattern=impl_pattern,
        verification_pattern=verify_pattern,
        automation_feasibility=auto_feas,
        automation_rationale=auto_rationale,
        business_rationale=business_rationale,
        control_summary=control_summary,
        requirement_type=req.get("requirement_type", ""),
        criticality=req.get("criticality", "UNKNOWN"),
        compliance_domain=req.get("compliance_domain", []),
        risk_domain=req.get("risk_domain", []),
        candidate_departments=req.get("candidate_departments", []),
        page_numbers=req.get("page_numbers", []),
        hierarchy_node_ids=req.get("hierarchy_node_ids", []),
        block_ids=req.get("block_ids", []),
        confidence=req.get("confidence", 1.0),
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ComplianceInterpretationEngine:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        self._ensure_directories()
        self._setup_logging()

        self.stats = {
            "documents_processed": 0,
            "requirements_interpreted": 0,
            "capabilities": Counter(),
            "control_categories": Counter(),
            "implementation_patterns": Counter(),
            "verification_patterns": Counter(),
            "automation_feasibility": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_file = self.log_dir / "compliance_interpreter.log"
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

    def _update_stats(self, ctrl: InterpretedControl) -> None:
        self.stats["requirements_interpreted"] += 1
        self.stats["capabilities"][ctrl.business_capability] += 1
        self.stats["control_categories"][ctrl.control_category] += 1
        self.stats["implementation_patterns"][ctrl.implementation_pattern] += 1
        self.stats["verification_patterns"][ctrl.verification_pattern] += 1
        self.stats["automation_feasibility"][ctrl.automation_feasibility] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — already interpreted.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        requirements = doc.get("enriched_requirements", [])
        interpreted_controls = []

        for req in requirements:
            try:
                ctrl = interpret_requirement(req)
                self._update_stats(ctrl)
                interpreted_controls.append(asdict(ctrl))
            except Exception as e:
                self.logger.error(f"Interpretation failed for {req.get('requirement_id')}: {e}")

        output = {
            "document_id": doc_id,
            "title": doc.get("title", doc_id),
            "document_status": doc.get("document_status", "ACTIVE"),
            "interpreted_control_count": len(interpreted_controls),
            "interpreted_controls": interpreted_controls,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.stats["documents_processed"] += 1
            self.logger.info(f"Interpreted {len(interpreted_controls)} controls for {doc_id}")
        except Exception as e:
            self.logger.error(f"Cannot write {output_file}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory not found: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} enriched requirement documents to interpret.")

        for json_path in tqdm(json_files, desc="Interpreting requirements"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        total = self.stats["requirements_interpreted"]
        unique_caps = len(self.stats["capabilities"])

        def fmt(c: Counter, top: int = 8) -> str:
            return "\n".join(f"  {k:<45} {v}" for k, v in c.most_common(top)) or "  (none)"

        summary = (
            f"\n{'='*65}\n"
            f" COMPLIANCE INTERPRETATION ENGINE SUMMARY\n"
            f"{'='*65}\n"
            f"Documents processed:             {self.stats['documents_processed']}\n"
            f"Requirements interpreted:        {total}\n"
            f"Unique business capabilities:    {unique_caps}\n"
            f"\nTop Business Capabilities:\n{fmt(self.stats['capabilities'])}\n"
            f"\nControl Category Distribution:\n{fmt(self.stats['control_categories'])}\n"
            f"\nImplementation Pattern Distribution:\n{fmt(self.stats['implementation_patterns'])}\n"
            f"\nVerification Pattern Distribution:\n{fmt(self.stats['verification_patterns'])}\n"
            f"\nAutomation Feasibility:\n{fmt(self.stats['automation_feasibility'])}\n"
            f"\nOutput directory:                {self.output_dir}\n"
            f"{'='*65}\n"
        )
        print(summary)
        self.logger.info("Compliance interpretation complete.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    engine = ComplianceInterpretationEngine(
        input_dir=project_root / "datasets" / "enriched_requirements",
        output_dir=project_root / "datasets" / "interpreted_controls",
        log_dir=project_root / "logs",
    )
    engine.run()
