"""
Verification Intelligence Engine V1 — RegIntel AI (SuRaksha-v2)

Generates independently executable verification rules for every Compliance Control.

Core principle: DO NOT TRUST THE IMPLEMENTING DEPARTMENT.
Every verification rule must represent a procedure that can be executed independently
of the department that implemented the control — via CMD, PowerShell, Registry,
SQL queries, API calls, log analysis, or manual inspection with a structured checklist.

Input:  datasets/interpreted_controls/   (one JSON per document)
Output: datasets/verification_rules/     (one JSON per document)

Each verification rule preserves full provenance back to document, requirement,
logical unit, page, hierarchy node, and block IDs.
"""

import json
import logging
import re
import sys
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import asdict, dataclass, field
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
class VerificationRule:
    rule_id: str
    requirement_id: str
    document_id: str
    logical_unit_id: str
    control_name: str
    business_capability: str
    control_category: str

    # Core verification fields
    verification_type: str
    verification_platform: str
    verification_mechanism: str
    executable_command: str           # Blank when no deterministic command exists
    command_parameters: str           # Any parameterisation notes
    expected_result: str
    evidence_required: List[str]
    machine_verifiable: bool
    automation_candidate: bool
    confidence: float
    reasoning: str

    # Contextual
    criticality: str
    compliance_domain: List[str]
    risk_domain: List[str]
    candidate_departments: List[str]
    implementation_pattern: str
    verification_pattern: str

    # Full provenance
    page_numbers: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]


# ---------------------------------------------------------------------------
# Verification Rule Knowledge Base
# ---------------------------------------------------------------------------
# Each VerificationStrategy is matched by a set of signals and produces a
# complete, self-contained verification specification.

class VerificationStrategy(ABC):
    """Abstract base for all verification rule strategies."""

    @abstractmethod
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        pass

    def _base(self, ctrl: Dict[str, Any], rule_id: str) -> Dict[str, Any]:
        """Common fields shared by all rules."""
        return {
            "rule_id": rule_id,
            "requirement_id": ctrl.get("requirement_id", ""),
            "document_id": ctrl.get("document_id", ""),
            "logical_unit_id": ctrl.get("logical_unit_id", ""),
            "control_name": ctrl.get("control_name", ""),
            "business_capability": ctrl.get("business_capability", ""),
            "control_category": ctrl.get("control_category", ""),
            "criticality": ctrl.get("criticality", "MEDIUM"),
            "compliance_domain": ctrl.get("compliance_domain", []),
            "risk_domain": ctrl.get("risk_domain", []),
            "candidate_departments": ctrl.get("candidate_departments", []),
            "implementation_pattern": ctrl.get("implementation_pattern", ""),
            "verification_pattern": ctrl.get("verification_pattern", ""),
            "page_numbers": ctrl.get("page_numbers", []),
            "hierarchy_node_ids": ctrl.get("hierarchy_node_ids", []),
            "block_ids": ctrl.get("block_ids", []),
        }


# ---------------------------------------------------------------------------
# Strategy: Password / IAM — Active Directory
# ---------------------------------------------------------------------------

class ADPasswordPolicyStrategy(VerificationStrategy):
    SIGNALS = {"Identity & Access Management", "password", "Password Governance"}

    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return (
            "identity" in cap
            or "access management" in cap
            or "password" in cap
            or "password" in name
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="PowerShell",
            verification_platform="Windows",
            verification_mechanism="Get-ADDefaultDomainPasswordPolicy",
            executable_command="Get-ADDefaultDomainPasswordPolicy | Select-Object MinPasswordLength, PasswordHistoryCount, MaxPasswordAge, MinPasswordAge, LockoutThreshold, LockoutDuration",
            command_parameters="Run on Domain Controller or any AD-joined machine with RSAT tools installed.",
            expected_result="MinPasswordLength >= 10; PasswordHistoryCount >= 12; LockoutThreshold <= 5; MaxPasswordAge <= 90 days.",
            evidence_required=["PowerShell Console Output (screenshot or text export)", "Group Policy Result (gpresult /r)"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.92,
            reasoning="Active Directory domain password policies are machine-readable and can be independently queried using PowerShell without relying on the IT department's self-assessment.",
        )


# ---------------------------------------------------------------------------
# Strategy: BitLocker / Disk Encryption
# ---------------------------------------------------------------------------

class DiskEncryptionStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return "encrypt" in cap or "cryptograph" in cap or "bitlocker" in name

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="PowerShell",
            verification_platform="Windows",
            verification_mechanism="Get-BitLockerVolume",
            executable_command="Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, EncryptionMethod, ProtectionStatus",
            command_parameters="Must be run with Administrator privileges on each endpoint or via Endpoint Management tooling.",
            expected_result="VolumeStatus = FullyEncrypted; ProtectionStatus = On; EncryptionMethod != None.",
            evidence_required=["PowerShell Output Export", "BitLocker Recovery Key Presence Confirmation"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.95,
            reasoning="BitLocker encryption status is directly queryable through PowerShell. The protection status and encryption method are machine-readable assertions that require no departmental input.",
        )


# ---------------------------------------------------------------------------
# Strategy: Windows Firewall
# ---------------------------------------------------------------------------

class WindowsFirewallStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return "firewall" in cap or "firewall" in name or "network security" in cap

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="CMD",
            verification_platform="Windows",
            verification_mechanism="netsh advfirewall",
            executable_command="netsh advfirewall show allprofiles state",
            command_parameters="Run on target host with Administrator privileges.",
            expected_result="Domain Profile State: ON; Private Profile State: ON; Public Profile State: ON.",
            evidence_required=["CMD Output Screenshot", "Firewall Policy Export"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.93,
            reasoning="Windows Firewall state is directly observable through the netsh command without relying on the implementing team's assertions.",
        )


# ---------------------------------------------------------------------------
# Strategy: Audit Logging / SIEM
# ---------------------------------------------------------------------------

class AuditLoggingStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        cat = ctrl.get("control_category", "").lower()
        return (
            "audit log" in cap
            or "logging" in cap
            or "audit log" in name
            or "log" in name
            or cat == "monitoring"
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="PowerShell",
            verification_platform="Windows",
            verification_mechanism="auditpol / Get-WinEvent",
            executable_command='auditpol /get /category:* | findstr /i "success failure"',
            command_parameters="Run on each server with Administrator privileges. Use Get-WinEvent for log retrieval.",
            expected_result="All critical audit categories enabled for both Success and Failure events. Event logs present in Security channel.",
            evidence_required=["auditpol /get output", "Get-WinEvent sample log extract", "SIEM dashboard screenshot"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.88,
            reasoning="Windows audit policy configuration is directly machine-readable. Log existence can be independently verified by querying the Security event log without asking the security team.",
        )


# ---------------------------------------------------------------------------
# Strategy: Services / Processes Running
# ---------------------------------------------------------------------------

class ServiceStatusStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        name = ctrl.get("control_name", "").lower()
        cap = ctrl.get("business_capability", "").lower()
        return "service" in name or "antivirus" in cap or "endpoint protection" in cap or "dlp" in cap

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="PowerShell",
            verification_platform="Windows",
            verification_mechanism="Get-Service",
            executable_command='Get-Service | Where-Object { $_.Status -eq "Running" } | Select-Object Name, Status, StartType',
            command_parameters="Run on target host. Identify relevant service names from asset inventory.",
            expected_result="All required security services (AV, EDR, DLP, logging agent) show Status=Running and StartType=Automatic.",
            evidence_required=["PowerShell Service List Output", "Screenshot of Service Control Manager"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.87,
            reasoning="Service status is independently queryable through PowerShell. No departmental cooperation is required to verify whether a security service is running.",
        )


# ---------------------------------------------------------------------------
# Strategy: Windows Registry Configuration
# ---------------------------------------------------------------------------

class RegistryVerificationStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        vp = ctrl.get("verification_pattern", "").lower()
        name = ctrl.get("control_name", "").lower()
        return "registry" in vp or "registry" in name or "configuration change" in ctrl.get("implementation_pattern", "").lower()

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Registry Check",
            verification_platform="Windows",
            verification_mechanism="reg query",
            executable_command='reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"',
            command_parameters="Adapt registry key path to the specific control being verified. Run with Administrator privileges.",
            expected_result="Relevant registry keys exist and contain compliant values as specified by the control policy.",
            evidence_required=["Registry Export (.reg file)", "reg query CMD Output"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.85,
            reasoning="Windows Registry keys are directly queryable and exportable without departmental involvement. Registry state reflects actual system configuration.",
        )


# ---------------------------------------------------------------------------
# Strategy: Active Directory User / Group Review
# ---------------------------------------------------------------------------

class ADUserGroupStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return (
            "identity" in cap
            or "access management" in cap
            or "privileged" in cap
            or "user" in name
            or "access review" in ctrl.get("implementation_pattern", "").lower()
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Active Directory Query",
            verification_platform="Windows",
            verification_mechanism="Get-ADUser / Get-ADGroupMember",
            executable_command='Get-ADGroupMember -Identity "Domain Admins" | Select-Object Name, SamAccountName, DistinguishedName',
            command_parameters="Replace 'Domain Admins' with the relevant privileged group name. Run on Domain Controller.",
            expected_result="Only authorised personnel in privileged groups. No service accounts or dormant accounts. Count within approved limit.",
            evidence_required=["Exported AD Group Membership List", "Approved Access Matrix Document"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.90,
            reasoning="Active Directory group membership is directly queryable through RSAT PowerShell cmdlets without requiring the implementing team to provide any data.",
        )


# ---------------------------------------------------------------------------
# Strategy: TLS / Certificate Validation
# ---------------------------------------------------------------------------

class TLSCertificateStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return "tls" in cap or "ssl" in cap or "certificate" in cap or "certificate" in name or "tls" in name

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Certificate Validation",
            verification_platform="Application",
            verification_mechanism="OpenSSL / PowerShell Invoke-WebRequest",
            executable_command="openssl s_client -connect <hostname>:443 -tls1_2 2>&1 | grep -E 'Protocol|Cipher|Verify'",
            command_parameters="Replace <hostname> with the target system FQDN. Run from a network-adjacent host.",
            expected_result="Protocol TLSv1.2 or TLSv1.3; Strong cipher suite; Verify return code 0 (certificate valid).",
            evidence_required=["OpenSSL Connection Output", "Certificate Expiry Screenshot", "Cipher Suite List"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.91,
            reasoning="TLS configuration is independently testable by initiating a connection and inspecting the negotiated protocol and cipher suite. No input from the implementing team is required.",
        )


# ---------------------------------------------------------------------------
# Strategy: SQL Database Security Configuration
# ---------------------------------------------------------------------------

class SQLDatabaseStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        vp = ctrl.get("verification_pattern", "").lower()
        cap = ctrl.get("business_capability", "").lower()
        name = ctrl.get("control_name", "").lower()
        return (
            "sql" in vp
            or "database" in cap
            or "data retention" in cap
            or "database" in name
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="SQL Query",
            verification_platform="SQL Server",
            verification_mechanism="T-SQL / sys catalog views",
            executable_command="SELECT name, is_broker_enabled, is_encrypted, compatibility_level FROM sys.databases;",
            command_parameters="Run against the target SQL Server instance with READ access to sys catalog. Adapt query to specific control.",
            expected_result="is_encrypted = 1 for production databases; compatibility_level >= 140; appropriate audit settings enabled.",
            evidence_required=["SQL Query Output Export", "Database Audit Specification Configuration"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.86,
            reasoning="SQL Server database configuration is directly queryable through system catalog views. Encryption status and configuration parameters are machine-readable without departmental disclosure.",
        )


# ---------------------------------------------------------------------------
# Strategy: Regulatory Reporting — Document + Submission Verification
# ---------------------------------------------------------------------------

class RegulatoryReportingStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        req_type = ctrl.get("requirement_type", "")
        return (
            "reporting" in cap
            or "reporting" in ctrl.get("control_category", "").lower()
            or req_type == "REPORTING"
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Document Review",
            verification_platform="Browser",
            verification_mechanism="RBI CIMS / Regulatory Portal Login",
            executable_command="",
            command_parameters="Log in to RBI CIMS / regulatory submission portal. Retrieve submission history for the relevant return type and verify submission timestamps.",
            expected_result="All regulatory returns submitted within stipulated timelines. Submission acknowledgements present. No outstanding or overdue returns.",
            evidence_required=["Portal Submission History Screenshot", "Acknowledgement Receipt PDF", "Sign-off from Authorised Signatory"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.80,
            reasoning="Regulatory return submission is verifiable through the RBI portal's submission history, which is independent of the submitting department. A reviewer can log in and confirm submission without asking the department.",
        )


# ---------------------------------------------------------------------------
# Strategy: KYC / AML — Transaction Monitoring
# ---------------------------------------------------------------------------

class KYCAMLStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        domain = ctrl.get("compliance_domain", [])
        return (
            "kyc" in cap
            or "aml" in cap
            or "due diligence" in cap
            or "transaction monitoring" in cap
            or "kyc" in [str(d).lower() for d in domain]
            or "aml" in [str(d).lower() for d in domain]
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Database Validation",
            verification_platform="Core Banking",
            verification_mechanism="Core Banking SQL / Report Query",
            executable_command="SELECT COUNT(*) FROM customer_master WHERE kyc_status NOT IN ('VERIFIED','COMPLIANT') AND account_status = 'ACTIVE';",
            command_parameters="Adapt table and column names to the specific core banking system schema. Run with READ-ONLY credentials on the production database replica.",
            expected_result="COUNT = 0. No active accounts with non-compliant KYC status. All customer records have verified KYC documentation.",
            evidence_required=["Database Query Output", "KYC Register Extract", "Sample Customer File Review (redacted)"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.82,
            reasoning="KYC status is stored in the core banking database and is independently queryable by the Compliance or Audit team without relying on the KYC implementation team's representation.",
        )


# ---------------------------------------------------------------------------
# Strategy: Foreign Exchange / FEMA
# ---------------------------------------------------------------------------

class ForeignExchangeStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        domain = ctrl.get("compliance_domain", [])
        return (
            "foreign exchange" in cap
            or "fema" in cap
            or "forex" in cap
            or "foreign exchange" in [str(d).lower() for d in domain]
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Document Review",
            verification_platform="Core Banking",
            verification_mechanism="FEMA Transaction Register Review",
            executable_command="",
            command_parameters="Access the Treasury Management System or Core Banking FX module. Review transaction registers for the applicable period.",
            expected_result="All FX transactions have: valid authorisation, A2/LRS declarations where applicable, correspondent bank confirmation, RBI reporting (Form A-2, FCGPR, etc.) filed within prescribed timelines.",
            evidence_required=["FX Transaction Register", "A-2 Form Copies", "RBI Return Submission Acknowledgement", "Authorisation Records"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.78,
            reasoning="FEMA compliance requires reviewing transaction-level documentation. An independent auditor can access TMS records without relying on the implementing team's self-certification.",
        )


# ---------------------------------------------------------------------------
# Strategy: Cyber Security Governance — Policy
# ---------------------------------------------------------------------------

class CyberGovernanceStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        cat = ctrl.get("control_category", "").lower()
        return (
            "cyber security governance" in cap
            or "it governance" in cap
            or (cat == "policy" and "cyber" in cap)
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Policy Review",
            verification_platform="Application",
            verification_mechanism="Policy Repository Inspection",
            executable_command="",
            command_parameters="Access the organisation's policy management system or SharePoint policy library. Retrieve the relevant policy document.",
            expected_result="Policy exists, is Board-approved, current version within 12 months, covers all required domains (IS, Cyber, Data Privacy), references applicable RBI Master Direction.",
            evidence_required=["Board-Approved Policy Document (PDF)", "Board Approval Minutes", "Policy Version History"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.83,
            reasoning="Policy governance verification requires document inspection, which an independent reviewer (Internal Audit / Compliance Officer) can perform by directly accessing the policy repository — without asking the IT/CISO team.",
        )


# ---------------------------------------------------------------------------
# Strategy: Third-Party / Vendor Risk
# ---------------------------------------------------------------------------

class VendorRiskStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        return "vendor" in cap or "third-party" in cap or "outsourc" in cap

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Document Review",
            verification_platform="Application",
            verification_mechanism="Vendor Register & Contract Review",
            executable_command="",
            command_parameters="Access vendor management system or procurement register. Review all active outsourcing arrangements.",
            expected_result="All critical vendors have: current due diligence on file, signed agreements with RBI-compliant clauses, SLA monitoring in place, annual review completed, exit plan documented.",
            evidence_required=["Vendor Risk Register", "Sample Vendor Contracts", "Due Diligence Report", "SLA Monitoring Dashboard"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.79,
            reasoning="Vendor risk compliance is verifiable through the vendor management register, which an independent reviewer can access. Contracts and due diligence reports exist as auditable documents.",
        )


# ---------------------------------------------------------------------------
# Strategy: Capital Adequacy / Liquidity
# ---------------------------------------------------------------------------

class CapitalLiquidityStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        return "capital" in cap or "liquidity" in cap or "crar" in cap or "lcr" in cap

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Database Validation",
            verification_platform="Core Banking",
            verification_mechanism="Capital / Liquidity Return Data Query",
            executable_command="",
            command_parameters="Query the Risk Management / ALM system for CRAR or LCR computation data. Cross-reference with RBI offsite returns.",
            expected_result="CRAR >= minimum prescribed by RBI (currently 9% + applicable buffers). LCR >= 100%. Returns submitted to RBI match internal computation.",
            evidence_required=["CRAR / LCR Computation Sheet", "Risk Management System Extract", "RBI Return Submission"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.82,
            reasoning="Capital and liquidity ratios are computed from core banking and risk system data. An independent reviewer can recompute ratios or query the risk system directly.",
        )


# ---------------------------------------------------------------------------
# Strategy: Business Continuity / Incident Response
# ---------------------------------------------------------------------------

class BCPIncidentStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        return "continuity" in cap or "incident" in cap or "disaster" in cap or "recovery" in cap

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Hybrid",
            verification_platform="Application",
            verification_mechanism="BCP/DR Test Record Review + RTO/RPO Validation",
            executable_command="",
            command_parameters="Review the most recent BCP/DR test report. Check RTO and RPO results against stated targets.",
            expected_result="BCP tested within past 12 months. RTO <= prescribed target. RPO <= prescribed target. All critical systems covered. Lessons learned documented.",
            evidence_required=["BCP Test Report", "RTO/RPO Evidence", "Incident Register", "Board Approval of BCP"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.77,
            reasoning="BCP effectiveness requires reviewing documented test results and incident logs. An independent auditor can access these records without relying on the BCP team's representation.",
        )


# ---------------------------------------------------------------------------
# Strategy: Digital Payments / Payment System Compliance
# ---------------------------------------------------------------------------

class PaymentSystemStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        domain = ctrl.get("compliance_domain", [])
        return (
            "payment" in cap
            or "digital payments" in cap
            or "digital payments" in [str(d).lower() for d in domain]
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        req_type = ctrl.get("requirement_type", "")
        if req_type == "REPORTING":
            return VerificationRule(
                **b,
                verification_type="Document Review",
                verification_platform="Browser",
                verification_mechanism="RBI Payment System Return Verification",
                executable_command="",
                command_parameters="Access RBI CPSS / payment system portal. Verify submission records for the relevant return period.",
                expected_result="All payment system returns submitted within prescribed timelines. No outstanding returns.",
                evidence_required=["Portal Submission Acknowledgement", "Return Submission Log"],
                machine_verifiable=False,
                automation_candidate=False,
                confidence=0.78,
                reasoning="Payment system reporting compliance can be independently verified through the regulator's submission portal without asking the submitting team.",
            )
        return VerificationRule(
            **b,
            verification_type="Log Analysis",
            verification_platform="Application",
            verification_mechanism="Payment Switch / Gateway Log Review",
            executable_command="",
            command_parameters="Access payment switch or gateway logs via SIEM or application logging system. Filter for transaction failure and exception events.",
            expected_result="No unauthorised payment transactions. Success/failure ratios within threshold. All declined transactions appropriately logged and investigated.",
            evidence_required=["Payment Gateway Transaction Log Extract", "Exception Report", "Reconciliation Statement"],
            machine_verifiable=False,
            automation_candidate=True,
            confidence=0.80,
            reasoning="Payment system logs are independently accessible via the SIEM or log management platform without requiring the payments team to provide data.",
        )


# ---------------------------------------------------------------------------
# Strategy: Customer Protection / Grievance
# ---------------------------------------------------------------------------

class CustomerProtectionStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        domain = ctrl.get("compliance_domain", [])
        return (
            "customer" in cap
            or "grievance" in cap
            or "customer protection" in [str(d).lower() for d in domain]
        )

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Database Validation",
            verification_platform="Core Banking",
            verification_mechanism="CRM / Grievance Register Query",
            executable_command="SELECT COUNT(*), AVG(DATEDIFF(day, created_date, resolved_date)) FROM grievances WHERE created_date >= DATEADD(month, -3, GETDATE());",
            command_parameters="Adapt to the CRM or grievance tracking system database schema. Run with READ-ONLY credentials.",
            expected_result="Average resolution time <= 30 days (or applicable RBI limit). Escalation rate within acceptable threshold. No unresolved grievances beyond 60 days.",
            evidence_required=["Grievance Register Extract", "TAT Analysis Report", "Escalated Case Summary"],
            machine_verifiable=True,
            automation_candidate=True,
            confidence=0.83,
            reasoning="Grievance statistics are stored in CRM systems and are directly queryable. An independent reviewer can compute resolution times without asking the customer service team.",
        )


# ---------------------------------------------------------------------------
# Strategy: Corporate Governance / Board Approval
# ---------------------------------------------------------------------------

class GovernanceStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        cap = ctrl.get("business_capability", "").lower()
        cat = ctrl.get("control_category", "").lower()
        return "governance" in cap or ("governance" in cat and "cyber" not in cap)

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        return VerificationRule(
            **b,
            verification_type="Document Review",
            verification_platform="Application",
            verification_mechanism="Board / Committee Minutes Review",
            executable_command="",
            command_parameters="Access the Board Secretariat or corporate secretarial records system. Retrieve Board and Risk Committee meeting minutes for the relevant period.",
            expected_result="Board has discussed and minuted relevant regulatory agenda items. Risk oversight Committee meeting held at prescribed frequency. Quorum requirements met.",
            evidence_required=["Board Meeting Minutes", "Risk Committee Minutes", "Board Attendance Register"],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.82,
            reasoning="Board and committee governance is verifiable through minutes, which are maintained by the Company Secretary independently of the implementing department.",
        )


# ---------------------------------------------------------------------------
# Fallback Strategy: Manual Audit / Structured Inspection
# ---------------------------------------------------------------------------

class FallbackManualAuditStrategy(VerificationStrategy):
    def matches(self, ctrl: Dict[str, Any]) -> bool:
        return True  # Always matches — used as final fallback

    def build(self, ctrl: Dict[str, Any], rule_id: str) -> VerificationRule:
        b = self._base(ctrl, rule_id)
        req_type = ctrl.get("requirement_type", "OBLIGATION")
        cap = ctrl.get("business_capability", "Regulatory Compliance")
        cat = ctrl.get("control_category", "Operational")

        return VerificationRule(
            **b,
            verification_type="Manual Inspection",
            verification_platform="Unknown",
            verification_mechanism="Structured Compliance Walkthrough",
            executable_command="",
            command_parameters=(
                f"Internal Audit or Compliance Officer to conduct a structured walkthrough of "
                f"the '{cap}' control implementation. Inspect documentation, interview relevant "
                f"staff, and observe process execution. Do NOT rely solely on the implementing "
                f"department's assertions."
            ),
            expected_result=(
                f"Evidence of implementation consistent with the control objective. "
                f"Documentary proof of {req_type.lower()} fulfilment. "
                f"No contradictory evidence found during walkthrough."
            ),
            evidence_required=[
                "Compliance Walkthrough Checklist (completed)",
                "Supporting Documentation",
                "Interview Notes",
                "Auditor Sign-Off",
            ],
            machine_verifiable=False,
            automation_candidate=False,
            confidence=0.65,
            reasoning=(
                f"No deterministic machine-executable command is available for this "
                f"'{cat}' control. A structured manual inspection by an independent "
                f"reviewer (Internal Audit or Compliance Officer) provides the best "
                f"independent verification outside the implementing department."
            ),
        )


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: List[VerificationStrategy] = [
    # Technical — most specific first
    ADPasswordPolicyStrategy(),
    DiskEncryptionStrategy(),
    WindowsFirewallStrategy(),
    AuditLoggingStrategy(),
    RegistryVerificationStrategy(),
    ADUserGroupStrategy(),
    TLSCertificateStrategy(),
    SQLDatabaseStrategy(),
    ServiceStatusStrategy(),
    # Domain-specific
    RegulatoryReportingStrategy(),
    KYCAMLStrategy(),
    ForeignExchangeStrategy(),
    CyberGovernanceStrategy(),
    VendorRiskStrategy(),
    CapitalLiquidityStrategy(),
    BCPIncidentStrategy(),
    PaymentSystemStrategy(),
    CustomerProtectionStrategy(),
    GovernanceStrategy(),
    # Fallback — always last
    FallbackManualAuditStrategy(),
]


def select_strategy(ctrl: Dict[str, Any]) -> VerificationStrategy:
    """Return the first matching strategy from the registry."""
    for strategy in STRATEGY_REGISTRY:
        if strategy.matches(ctrl):
            return strategy
    return STRATEGY_REGISTRY[-1]  # Guaranteed fallback


# ---------------------------------------------------------------------------
# Rule ID generation
# ---------------------------------------------------------------------------

def _make_rule_id(req_id: str) -> str:
    return f"VR_{req_id}"


# ---------------------------------------------------------------------------
# Engine Orchestrator
# ---------------------------------------------------------------------------

class VerificationRuleGenerator:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        self._ensure_directories()
        self._setup_logging()

        self.stats = {
            "documents_processed": 0,
            "rules_generated": 0,
            "machine_verifiable": 0,
            "automation_candidates": 0,
            "verification_types": Counter(),
            "platforms": Counter(),
            "mechanisms": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_file = self.log_dir / "verification_rule_generator.log"
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

    def _update_stats(self, rule: VerificationRule) -> None:
        self.stats["rules_generated"] += 1
        if rule.machine_verifiable:
            self.stats["machine_verifiable"] += 1
        if rule.automation_candidate:
            self.stats["automation_candidates"] += 1
        self.stats["verification_types"][rule.verification_type] += 1
        self.stats["platforms"][rule.verification_platform] += 1
        if rule.verification_mechanism:
            mech = rule.verification_mechanism.split("/")[0].strip()
            self.stats["mechanisms"][mech] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — verification rules already generated.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        controls = doc.get("interpreted_controls", [])
        rules: List[Dict[str, Any]] = []

        for ctrl in controls:
            try:
                req_id = ctrl.get("requirement_id", "")
                rule_id = _make_rule_id(req_id)
                strategy = select_strategy(ctrl)
                rule = strategy.build(ctrl, rule_id)
                self._update_stats(rule)
                rules.append(asdict(rule))
            except Exception as e:
                self.logger.error(f"Rule generation failed for {ctrl.get('requirement_id')}: {e}")

        output = {
            "document_id": doc_id,
            "title": doc.get("title", doc_id),
            "document_status": doc.get("document_status", "ACTIVE"),
            "rule_count": len(rules),
            "verification_rules": rules,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.stats["documents_processed"] += 1
            self.logger.info(f"Generated {len(rules)} verification rules for {doc_id}")
        except Exception as e:
            self.logger.error(f"Cannot write {output_file}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory not found: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} interpreted control documents to process.")

        for json_path in tqdm(json_files, desc="Generating verification rules"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        total = self.stats["rules_generated"]

        def fmt(c: Counter, top: int = 10) -> str:
            return "\n".join(f"  {k:<40} {v}" for k, v in c.most_common(top)) or "  (none)"

        summary = (
            f"\n{'='*65}\n"
            f" VERIFICATION INTELLIGENCE ENGINE SUMMARY\n"
            f"{'='*65}\n"
            f"Documents processed:             {self.stats['documents_processed']}\n"
            f"Verification rules generated:    {total}\n"
            f"Machine-verifiable rules:        {self.stats['machine_verifiable']}\n"
            f"Automation candidates:           {self.stats['automation_candidates']}\n"
            f"\nVerification Type Distribution:\n{fmt(self.stats['verification_types'])}\n"
            f"\nPlatform Distribution:\n{fmt(self.stats['platforms'])}\n"
            f"\nTop Verification Mechanisms:\n{fmt(self.stats['mechanisms'])}\n"
            f"\nOutput directory:                {self.output_dir}\n"
            f"{'='*65}\n"
        )
        print(summary)
        self.logger.info("Verification rule generation complete.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    engine = VerificationRuleGenerator(
        input_dir=project_root / "datasets" / "interpreted_controls",
        output_dir=project_root / "datasets" / "verification_rules",
        log_dir=project_root / "logs",
    )
    engine.run()
