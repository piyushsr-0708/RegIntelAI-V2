"""
Requirement Enrichment Engine V1 — RegIntel AI (SuRaksha-v2)

Converts extracted requirements into rich Compliance Objects.
Uses a deterministic, rule-based approach with an extensible architecture
where each enrichment task is handled by a separate strategy class.
Future offline AI models can seamlessly replace these enricher classes.

Enrichment tasks:
1. Compliance Domain
2. Risk Domain
3. Implementation Category
4. Criticality
5. Candidate Departments
6. Verification Strategy
7. Regulatory Keywords
8. Regulatory Entities
9. Confidence tuning
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

class BaseEnricher(ABC):
    """Abstract base class for all requirement enrichers."""
    
    @abstractmethod
    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        """
        Analyzes the original requirement and mutates the `enriched_data` dict
        with new fields.
        """
        pass

# ---------------------------------------------------------------------------
# Specific Enrichers
# ---------------------------------------------------------------------------

class ComplianceDomainEnricher(BaseEnricher):
    DOMAIN_RULES = {
        "Cyber Security": [r"cyber", r"security", r"information security", r"data breach", r"encryption", r"vulnerability"],
        "KYC": [r"kyc", r"know your customer", r"customer identification", r"cdl", r"beneficial owner", r"cdd"],
        "AML": [r"aml", r"anti money laundering", r"money laundering", r"suspicious transaction", r"fatf", r"cft", r"terrorist financing"],
        "Fraud Risk": [r"fraud", r"forgery", r"embezzlement", r"misappropriation"],
        "IT Governance": [r"it governance", r"technology governance", r"it infrastructure", r"software", r"hardware", r"system audit"],
        "Risk Management": [r"risk management", r"risk assessment", r"mitigation", r"risk profile"],
        "Audit": [r"audit", r"internal audit", r"statutory audit", r"concurrent audit", r"auditor"],
        "Treasury": [r"treasury", r"investment", r"securities", r"derivatives", r"market risk"],
        "Digital Payments": [r"payment", r"upi", r"neft", r"rtgs", r"cards", r"wallets", r"pos", r"atm"],
        "Customer Protection": [r"customer protection", r"grievance", r"ombudsman", r"complaint", r"compensation", r"consumer"],
        "Reporting": [r"reporting", r"returns", r"submission", r"xbrl", r"cims", r"regulatory return"],
        "Foreign Exchange": [r"foreign exchange", r"fema", r"forex", r"fdi", r"ecb", r"nri", r"remittance", r"export", r"import"],
        "Prudential Regulation": [r"prudential", r"npa", r"provisioning", r"asset classification", r"exposure norm"],
        "Capital Adequacy": [r"capital adequacy", r"crar", r"basel", r"tier 1", r"tier 2"],
        "Liquidity": [r"liquidity", r"lcr", r"nsfr", r"alm", r"asset liability"],
        "Outsourcing": [r"outsourcing", r"vendor", r"third party", r"service provider"],
        "Governance": [r"governance", r"board of directors", r"committee", r"management", r"director", r"shareholder"],
    }

    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        text = requirement.get("full_sentence", "").lower()
        title = requirement.get("title", "").lower() if "title" in requirement else ""
        combined = f"{text} {title}"
        
        detected_domains = set()
        for domain, patterns in self.DOMAIN_RULES.items():
            if any(re.search(p, combined) for p in patterns):
                detected_domains.add(domain)
                
        enriched_data["compliance_domain"] = list(detected_domains) if detected_domains else ["General"]


class RiskDomainEnricher(BaseEnricher):
    DOMAIN_MAPPING = {
        "Operational Risk": ["Fraud Risk", "IT Governance", "Outsourcing", "Digital Payments"],
        "Cyber Risk": ["Cyber Security", "IT Governance"],
        "Financial Risk": ["Treasury", "Prudential Regulation", "Capital Adequacy", "Liquidity", "Foreign Exchange"],
        "Compliance Risk": ["KYC", "AML", "Reporting", "Governance", "General"],
        "Legal Risk": ["Customer Protection"],
    }
    
    KEYWORD_RULES = {
        "Reputational Risk": [r"reputation", r"public confidence", r"adverse publicity"],
        "Strategic Risk": [r"business model", r"strategy", r"strategic"],
        "Technology Risk": [r"technology", r"system failure", r"downtime", r"software"],
    }

    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        comp_domains = enriched_data.get("compliance_domain", [])
        risk_domains = set()
        
        # Map from compliance domains
        for c_domain in comp_domains:
            for r_domain, triggers in self.DOMAIN_MAPPING.items():
                if c_domain in triggers:
                    risk_domains.add(r_domain)
                    
        # Check explicit keywords
        text = requirement.get("full_sentence", "").lower()
        for r_domain, patterns in self.KEYWORD_RULES.items():
            if any(re.search(p, text) for p in patterns):
                risk_domains.add(r_domain)
                
        enriched_data["risk_domain"] = list(risk_domains) if risk_domains else ["Unknown"]


class ImplementationCategoryEnricher(BaseEnricher):
    RULES = {
        "Policy": [r"policy", r"framework", r"guidelines", r"strategy", r"charter"],
        "Process": [r"process", r"procedure", r"mechanism", r"system", r"methodology", r"undertake", r"ensure"],
        "Technical Control": [r"configure", r"install", r"encrypt", r"authenticate", r"firewall", r"software", r"hardware", r"access control"],
        "Monitoring": [r"monitor", r"review", r"track", r"observe", r"surveillance"],
        "Reporting": [r"report", r"submit", r"file", r"furnish", r"intimate", r"disclose", r"notify"],
        "Documentation": [r"document", r"record", r"register", r"maintain", r"retain", r"preserve"],
        "Training": [r"train", r"educate", r"awareness", r"sensitize"],
        "Audit": [r"audit", r"inspect", r"examine", r"verify", r"assess"],
        "Approval": [r"approve", r"authorize", r"sanction", r"clearance"],
        "Configuration": [r"parameter", r"limit", r"threshold", r"configure"],
    }

    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        action = requirement.get("action", "").lower()
        object_ = requirement.get("object", "").lower()
        text = f"{action} {object_}"
        
        categories = set()
        for cat, patterns in self.RULES.items():
            if any(re.search(r"\b" + p + r"\b", text) for p in patterns):
                categories.add(cat)
                
        # Fallbacks based on requirement type
        req_type = requirement.get("requirement_type", "")
        if not categories:
            if req_type == "REPORTING":
                categories.add("Reporting")
            else:
                categories.add("Other")
                
        enriched_data["implementation_category"] = list(categories)


class CriticalityEnricher(BaseEnricher):
    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        req_type = requirement.get("requirement_type", "")
        text = requirement.get("full_sentence", "").lower()
        timeline = requirement.get("timeline", "")
        
        criticality = "LOW"
        
        # Base criticality from type
        if req_type in ["PROHIBITION"]:
            criticality = "HIGH"
        elif req_type in ["OBLIGATION", "REPORTING"]:
            criticality = "MEDIUM"
            
        # Modifiers
        if re.search(r"\b(penalty|immediate|urgent|critical|severe|strict|revoke|cancel)\b", text):
            criticality = "CRITICAL"
        elif timeline and re.search(r"\b(immediately|within \d+ hours|within \d+ days)\b", timeline):
            if criticality in ["LOW", "MEDIUM"]:
                criticality = "HIGH"
        elif req_type in ["RECOMMENDATION", "PERMISSION", "DEFINITION", "EXCEPTION"]:
            criticality = "LOW"
            
        enriched_data["criticality"] = criticality


class CandidateDepartmentsEnricher(BaseEnricher):
    MAPPING = {
        "Compliance": ["AML", "KYC", "Reporting", "Compliance Risk", "Regulatory Return", "Customer Protection"],
        "IT": ["Cyber Security", "IT Governance", "Cyber Risk", "Technology Risk", "Technical Control", "Configuration"],
        "Cyber Security": ["Cyber Security", "Cyber Risk", "Technical Control"],
        "Risk": ["Risk Management", "Operational Risk", "Financial Risk", "Credit Risk", "Market Risk", "Prudential Regulation"],
        "Legal": ["Legal Risk", "Customer Protection", "Contract", "Agreement"],
        "Treasury": ["Treasury", "Liquidity", "Capital Adequacy", "Foreign Exchange"],
        "Operations": ["Process", "Outsourcing", "Digital Payments"],
        "HR": ["Training", "Employee", "Staff"],
        "Internal Audit": ["Audit"],
        "Board": ["Governance", "Board", "Director", "Policy", "Strategy"],
    }

    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        cdomains = enriched_data.get("compliance_domain", [])
        rdomains = enriched_data.get("risk_domain", [])
        icats = enriched_data.get("implementation_category", [])
        actor = requirement.get("actor", "").lower()
        
        combined_tags = set(cdomains + rdomains + icats)
        depts = set()
        
        for dept, tags in self.MAPPING.items():
            if any(t in combined_tags for t in tags):
                depts.add(dept)
                
        # Direct actor matching
        if "board" in actor:
            depts.add("Board")
        if "management" in actor or "committee" in actor:
            depts.add("Management")
        if "auditor" in actor:
            depts.add("Internal Audit")
            
        enriched_data["candidate_departments"] = list(depts) if depts else ["Unknown"]


class VerificationStrategyEnricher(BaseEnricher):
    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        icats = enriched_data.get("implementation_category", [])
        text = requirement.get("full_sentence", "").lower()
        
        strategies = set()
        
        if "Policy" in icats:
            strategies.add("Policy Review")
        if "Process" in icats:
            strategies.add("Document Review")
            strategies.add("Interview")
        if "Technical Control" in icats or "Configuration" in icats:
            strategies.add("Configuration Verification")
            if "log" in text or "monitor" in text:
                strategies.add("Log Review")
            else:
                strategies.add("Command Line")
                strategies.add("PowerShell")
        if "Reporting" in icats or "Documentation" in icats:
            strategies.add("Evidence Upload")
            strategies.add("Document Review")
        if "Audit" in icats:
            strategies.add("Manual Audit")
            
        if "database" in text or "system" in text:
            strategies.add("Database Verification")
            
        enriched_data["verification_strategy"] = list(strategies) if strategies else ["Unknown"]


class RegulatoryEntitiesEnricher(BaseEnricher):
    ENTITIES = [
        "Bank", "NBFC", "Board", "Customer", "Reserve Bank", "RBI",
        "Authorised Dealer", "AD Category-I", "Regulated Entity", "RE",
        "Payment System Provider", "PSP", "Credit Information Company", "CIC",
        "Director", "Auditor", "Senior Management", "Vendor", "Third Party"
    ]
    
    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        text = requirement.get("full_sentence", "")
        found = set()
        for entity in self.ENTITIES:
            # Word boundary regex
            if re.search(r"\b" + re.escape(entity) + r"\b", text, re.I):
                found.add(entity)
        enriched_data["regulatory_entities"] = list(found)


class RegulatoryKeywordsEnricher(BaseEnricher):
    # A small deterministic list of important regulatory keywords
    KEYWORDS = {
        "penalty", "fine", "compliance", "non-compliance", "breach",
        "guideline", "directive", "act", "rule", "framework", "standard",
        "limit", "threshold", "capital", "exposure", "provision",
        "authentication", "encryption", "confidentiality", "integrity",
        "consent", "grievance", "redressal", "audit trail", "logs",
        "mandatory", "statutory", "regulatory"
    }

    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        text = requirement.get("full_sentence", "").lower()
        found = set()
        for kw in self.KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                found.add(kw)
        enriched_data["regulatory_keywords"] = list(found)


class ConfidenceEnricher(BaseEnricher):
    def enrich(self, requirement: Dict[str, Any], enriched_data: Dict[str, Any]) -> None:
        # Base confidence from the extractor
        conf = requirement.get("confidence", 0.5)
        
        # Tune confidence based on enrichment success
        if "General" not in enriched_data.get("compliance_domain", []):
            conf += 0.05
        if "Unknown" not in enriched_data.get("risk_domain", []):
            conf += 0.05
        if "Unknown" not in enriched_data.get("candidate_departments", []):
            conf += 0.05
        if "Unknown" not in enriched_data.get("verification_strategy", []):
            conf += 0.05
            
        enriched_data["confidence"] = round(min(conf, 1.0), 2)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class RequirementEnricher:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        
        self._ensure_directories()
        self._setup_logging()
        
        # Instantiate enrichers in order (order matters for dependent enrichments)
        self.enrichers: List[BaseEnricher] = [
            ComplianceDomainEnricher(),
            RiskDomainEnricher(),
            ImplementationCategoryEnricher(),
            CriticalityEnricher(),
            CandidateDepartmentsEnricher(),
            VerificationStrategyEnricher(),
            RegulatoryEntitiesEnricher(),
            RegulatoryKeywordsEnricher(),
            ConfidenceEnricher(),
        ]
        
        self.stats = {
            "documents_processed": 0,
            "requirements_enriched": 0,
            "compliance_domains": Counter(),
            "risk_domains": Counter(),
            "implementation_categories": Counter(),
            "criticality": Counter(),
            "verification_strategies": Counter(),
            "total_departments": 0,
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        log_file = self.log_dir / "requirement_enricher.log"
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

    def _enrich_single(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Applies all enrichers to a single requirement object."""
        enriched_data: Dict[str, Any] = {}
        
        for enricher in self.enrichers:
            try:
                enricher.enrich(requirement, enriched_data)
            except Exception as e:
                self.logger.warning(f"Enricher {enricher.__class__.__name__} failed on {requirement.get('requirement_id')}: {e}")
                
        # Merge original with enriched (enriched overrides if conflict, though keys are distinct)
        final_req = requirement.copy()
        final_req.update(enriched_data)
        return final_req

    def _update_stats(self, enriched: Dict[str, Any]) -> None:
        for cd in enriched.get("compliance_domain", []):
            self.stats["compliance_domains"][cd] += 1
        for rd in enriched.get("risk_domain", []):
            self.stats["risk_domains"][rd] += 1
        for ic in enriched.get("implementation_category", []):
            self.stats["implementation_categories"][ic] += 1
        crit = enriched.get("criticality", "UNKNOWN")
        self.stats["criticality"][crit] += 1
        for vs in enriched.get("verification_strategy", []):
            self.stats["verification_strategies"][vs] += 1
        self.stats["total_departments"] += len(enriched.get("candidate_departments", []))
        self.stats["requirements_enriched"] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"
        
        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — requirements already enriched.")
            return

        self.logger.info(f"Enriching requirements for: {json_path.name}")
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return
            
        try:
            requirements = doc.get("requirements") or []
            enriched_requirements = []
            
            for req in requirements:
                try:
                    enriched = self._enrich_single(req)
                    enriched_requirements.append(enriched)
                    self._update_stats(enriched)
                except Exception as e:
                    self.logger.error(f"Error enriching requirement {req.get('requirement_id')}: {e}")
                    # Keep original if enrichment totally fails
                    enriched_requirements.append(req)
                    
            output = {
                "document_id": doc_id,
                "title": doc.get("title", doc_id),
                "document_status": doc.get("document_status", "ACTIVE"),
                "requirement_count": len(enriched_requirements),
                "enriched_requirements": enriched_requirements
            }
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
                
            self.stats["documents_processed"] += 1
            
        except Exception as e:
            self.logger.error(f"Critical error enriching {doc_id}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} requirement documents to process.")

        for json_path in tqdm(json_files, desc="Enriching requirements"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        reqs = self.stats["requirements_enriched"]
        avg_depts = self.stats["total_departments"] / reqs if reqs > 0 else 0.0
        
        def format_counter(c: Counter) -> str:
            return "\n".join(f"  {k:<20} {v}" for k, v in c.most_common(5)) or "  (none)"
            
        summary = (
            f"\n{'='*50}\n"
            f" ENRICHMENT ENGINE VERIFICATION SUMMARY\n"
            f"{'='*50}\n"
            f"Documents processed:       {self.stats['documents_processed']}\n"
            f"Requirements enriched:     {reqs}\n"
            f"\nTop Compliance Domains:\n{format_counter(self.stats['compliance_domains'])}\n"
            f"\nTop Risk Domains:\n{format_counter(self.stats['risk_domains'])}\n"
            f"\nImplementation Categories:\n{format_counter(self.stats['implementation_categories'])}\n"
            f"\nCriticality Distribution:\n{format_counter(self.stats['criticality'])}\n"
            f"\nVerification Strategies:\n{format_counter(self.stats['verification_strategies'])}\n"
            f"\nAverage candidate depts:   {avg_depts:.1f}\n"
            f"Output directory:          {self.output_dir}\n"
            f"{'='*50}\n"
        )
        print(summary)
        self.logger.info("Enrichment pipeline completed.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "requirements"
    output_directory = project_root / "datasets" / "enriched_requirements"
    log_directory = project_root / "logs"

    enricher = RequirementEnricher(input_directory, output_directory, log_directory)
    enricher.run()
