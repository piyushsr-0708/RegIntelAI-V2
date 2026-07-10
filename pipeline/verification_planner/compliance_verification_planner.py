"""
Compliance Verification Planner (CVP) V1 — RegIntel AI (SuRaksha-v2)

Decomposes every Verification Rule into an executable Verification Plan containing
one or more atomic Verification Checks, an execution DAG, and a final assessment gate.

Pipeline position:
    Verification Rule  →  Verification Plan  →  [future] Verification Executor

Key design principles:
  - Each check is atomic, independently executable, and platform-specific.
  - Every check has a precise comparison operator and expected data type.
  - The DAG encodes sequential / parallel execution order and mandatory gates.
  - No check trusts departmental self-reporting; all are independently executable.
  - Full provenance is preserved on every output object.

Input:  datasets/verification_rules/    (one JSON per document)
Output: datasets/verification_plans/    (one JSON per document)
"""

import json
import logging
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
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CheckDependency:
    depends_on_check_id: str
    dependency_type: str   # FINISH_TO_START | PASS_GATE | EVIDENCE_GATE


@dataclass
class VerificationCheck:
    check_id: str
    plan_id: str
    sequence_number: int
    title: str
    description: str
    verification_platform: str
    verification_mechanism: str
    command: str
    command_type: str          # PowerShell | CMD | SQL | Registry | API | Browser | Linux | Manual
    command_parameters: str
    expected_result: str
    comparison_operator: str   # == | != | > | < | >= | <= | contains | regex | exists | not_exists | manual
    expected_data_type: str    # Boolean | Integer | String | JSON | List | Date
    evidence_required: List[str]
    machine_verifiable: bool
    automation_candidate: bool
    mandatory: bool
    failure_impact: str        # BLOCKER | MAJOR | MINOR | INFORMATIONAL
    retry_count: int
    timeout_seconds: int
    confidence: float
    reasoning: str
    dependencies: List[CheckDependency]
    parallel_eligible: bool


@dataclass
class DAGNode:
    check_id: str
    sequence_number: int
    depends_on: List[str]      # list of check_ids
    parallel_eligible: bool
    is_gate: bool              # if True, downstream checks cannot proceed until this PASSES


@dataclass
class ExecutionDAG:
    nodes: List[DAGNode]
    total_sequential_steps: int
    parallelisable_groups: int
    critical_path_length: int
    has_mandatory_gates: bool


@dataclass
class VerificationPlan:
    plan_id: str
    rule_id: str
    requirement_id: str
    document_id: str
    logical_unit_id: str
    control_name: str
    business_capability: str
    control_category: str
    criticality: str

    # Strategy summary
    verification_strategy: str
    estimated_execution_minutes: int
    estimated_manual_effort_hours: float
    automation_percentage: float
    parallel_execution_possible: bool

    # Checks
    checks: List[VerificationCheck]
    total_checks: int
    mandatory_checks: int
    machine_verifiable_checks: int

    # DAG
    execution_dag: ExecutionDAG

    # Final assessment rule
    pass_condition: str    # ALL_MANDATORY | ALL_CHECKS | MAJORITY
    final_decision_rule: str

    # Provenance
    compliance_domain: List[str]
    risk_domain: List[str]
    candidate_departments: List[str]
    page_numbers: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]
    confidence: float


# ---------------------------------------------------------------------------
# Check Builder Helpers
# ---------------------------------------------------------------------------

def _check_id(plan_id: str, seq: int) -> str:
    return f"{plan_id}_C{seq:02d}"


def _dep(plan_id: str, seq: int) -> List[CheckDependency]:
    """Standard sequential dependency on previous check."""
    if seq <= 1:
        return []
    return [CheckDependency(
        depends_on_check_id=_check_id(plan_id, seq - 1),
        dependency_type="FINISH_TO_START"
    )]


def _gate_dep(plan_id: str, seq: int) -> List[CheckDependency]:
    """Hard PASS_GATE dependency — next check blocked unless previous PASSES."""
    if seq <= 1:
        return []
    return [CheckDependency(
        depends_on_check_id=_check_id(plan_id, seq - 1),
        dependency_type="PASS_GATE"
    )]


# ---------------------------------------------------------------------------
# Plan Strategy Base + Implementations
# ---------------------------------------------------------------------------

class PlanStrategy(ABC):
    """Abstract base for all verification plan strategies."""

    @abstractmethod
    def matches(self, rule: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        pass

    def strategy_name(self) -> str:
        return self.__class__.__name__.replace("Strategy", "")

    def _base_check(self, plan_id: str, seq: int) -> Dict[str, Any]:
        return {
            "check_id": _check_id(plan_id, seq),
            "plan_id": plan_id,
            "sequence_number": seq,
            "retry_count": 2,
            "timeout_seconds": 60,
        }


# ---- AD Password Policy Plan ---- #

class ADPasswordPolicyPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        mech = rule.get("verification_mechanism", "").lower()
        return "addefaultdomainpassword" in mech or "password policy" in rule.get("control_name", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        crit = rule.get("criticality", "MEDIUM")
        b = self._base_check

        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Minimum Password Length",
                description="Query Active Directory Default Domain Password Policy to confirm MinimumPasswordLength meets or exceeds the required threshold.",
                verification_platform="Windows",
                verification_mechanism="Get-ADDefaultDomainPasswordPolicy",
                command="(Get-ADDefaultDomainPasswordPolicy).MinPasswordLength",
                command_type="PowerShell",
                command_parameters="Run on Domain Controller or RSAT-enabled host.",
                expected_result="Value >= 10",
                comparison_operator=">=",
                expected_data_type="Integer",
                evidence_required=["PowerShell Console Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.95,
                reasoning="MinPasswordLength is a directly readable integer property.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Password History Count",
                description="Confirm that password history prevents reuse of previously used passwords.",
                verification_platform="Windows",
                verification_mechanism="Get-ADDefaultDomainPasswordPolicy",
                command="(Get-ADDefaultDomainPasswordPolicy).PasswordHistoryCount",
                command_type="PowerShell",
                command_parameters="Run on Domain Controller or RSAT-enabled host.",
                expected_result="Value >= 12",
                comparison_operator=">=",
                expected_data_type="Integer",
                evidence_required=["PowerShell Console Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.93,
                reasoning="PasswordHistoryCount is a directly readable integer property.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify Account Lockout Threshold",
                description="Confirm lockout policy is configured to block brute force attempts.",
                verification_platform="Windows",
                verification_mechanism="Get-ADDefaultDomainPasswordPolicy",
                command="(Get-ADDefaultDomainPasswordPolicy).LockoutThreshold",
                command_type="PowerShell",
                command_parameters="Run on Domain Controller. A value of 0 means lockout is disabled.",
                expected_result="0 < Value <= 5",
                comparison_operator="<=",
                expected_data_type="Integer",
                evidence_required=["PowerShell Console Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.93,
                reasoning="LockoutThreshold is a directly readable integer. A value of 0 (disabled) is non-compliant.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 4),
                title="Verify Maximum Password Age",
                description="Confirm passwords are forced to change within the prescribed period.",
                verification_platform="Windows",
                verification_mechanism="Get-ADDefaultDomainPasswordPolicy",
                command="(Get-ADDefaultDomainPasswordPolicy).MaxPasswordAge.Days",
                command_type="PowerShell",
                command_parameters="Run on Domain Controller.",
                expected_result="0 < Value <= 90",
                comparison_operator="<=",
                expected_data_type="Integer",
                evidence_required=["PowerShell Console Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=False,
                failure_impact="MINOR",
                confidence=0.90,
                reasoning="MaxPasswordAge.Days is a directly readable numeric property.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 5),
                title="Export Full Password Policy as Evidence",
                description="Export the complete domain password policy configuration as archived evidence.",
                verification_platform="Windows",
                verification_mechanism="Get-ADDefaultDomainPasswordPolicy | Export-Csv",
                command='Get-ADDefaultDomainPasswordPolicy | Select-Object * | Export-Csv -Path "PasswordPolicy_Evidence.csv" -NoTypeInformation',
                command_type="PowerShell",
                command_parameters="Run on Domain Controller. Upload output CSV as evidence artefact.",
                expected_result="CSV file generated with all policy properties populated.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["CSV Export File", "Timestamp of Execution"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.95,
                reasoning="Evidence export is fully automated via PowerShell.",
                dependencies=_gate_dep(plan_id, 4),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Windows Firewall Plan ---- #

class FirewallPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        return "netsh" in rule.get("verification_mechanism", "").lower() or "firewall" in rule.get("control_name", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Firewall Enabled on All Profiles",
                description="Confirm Windows Firewall is active on Domain, Private, and Public network profiles.",
                verification_platform="Windows",
                verification_mechanism="netsh advfirewall",
                command="netsh advfirewall show allprofiles state",
                command_type="CMD",
                command_parameters="Run as Administrator on target host.",
                expected_result="Domain Profile State: ON; Private Profile State: ON; Public Profile State: ON.",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["CMD Output Screenshot"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.95,
                reasoning="netsh returns a plain-text status that is directly parseable.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Default Inbound Action is Block",
                description="Confirm that firewall default action for inbound traffic is BLOCK on all profiles.",
                verification_platform="Windows",
                verification_mechanism="netsh advfirewall",
                command='netsh advfirewall show allprofiles | findstr /i "Inbound"',
                command_type="CMD",
                command_parameters="Run as Administrator.",
                expected_result="Inbound connections: Block (for each profile).",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["CMD Output Screenshot"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.93,
                reasoning="Inbound default action is a readable string in netsh output.",
                dependencies=_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Export Firewall Configuration as Evidence",
                description="Export complete firewall policy configuration to a file for archival.",
                verification_platform="Windows",
                verification_mechanism="netsh advfirewall export",
                command='netsh advfirewall export "FirewallPolicy_Evidence.wfw"',
                command_type="CMD",
                command_parameters="Run as Administrator. Upload .wfw file as evidence.",
                expected_result=".wfw file created in current directory.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["Exported .wfw Policy File", "File Timestamp"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.95,
                reasoning="Policy export is a single-command, fully automated operation.",
                dependencies=_gate_dep(plan_id, 2),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- BitLocker / Disk Encryption Plan ---- #

class DiskEncryptionPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        mech = rule.get("verification_mechanism", "").lower()
        return "bitlocker" in mech or "encrypt" in rule.get("business_capability", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Volume Encryption Status",
                description="Confirm all local volumes are fully encrypted.",
                verification_platform="Windows",
                verification_mechanism="Get-BitLockerVolume",
                command="Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, EncryptionMethod, ProtectionStatus",
                command_type="PowerShell",
                command_parameters="Run as Administrator on each target endpoint.",
                expected_result="VolumeStatus = FullyEncrypted for all drives.",
                comparison_operator="==",
                expected_data_type="String",
                evidence_required=["PowerShell Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.95,
                reasoning="BitLocker VolumeStatus is a directly readable enum.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify BitLocker Protection Status is ON",
                description="Confirm BitLocker protection is actively enforced (not suspended).",
                verification_platform="Windows",
                verification_mechanism="Get-BitLockerVolume",
                command="(Get-BitLockerVolume -MountPoint 'C:').ProtectionStatus",
                command_type="PowerShell",
                command_parameters="Repeat for each drive letter on the system.",
                expected_result="On",
                comparison_operator="==",
                expected_data_type="String",
                evidence_required=["PowerShell Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.95,
                reasoning="ProtectionStatus returns 'On' or 'Off' — directly comparable.",
                dependencies=_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify Recovery Key is Escrowed to AD",
                description="Confirm BitLocker recovery keys are backed up to Active Directory.",
                verification_platform="Windows",
                verification_mechanism="Get-ADObject",
                command='Get-ADObject -Filter { objectClass -eq "msFVE-RecoveryInformation" } -SearchBase "DC=yourdomain,DC=com" | Measure-Object | Select-Object -ExpandProperty Count',
                command_type="PowerShell",
                command_parameters="Replace DC= with actual domain components. Run on Domain Controller.",
                expected_result="Count > 0 (recovery keys present in AD).",
                comparison_operator=">",
                expected_data_type="Integer",
                evidence_required=["AD Recovery Key Count", "PowerShell Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=False,
                failure_impact="MAJOR",
                confidence=0.85,
                reasoning="Recovery key escrow to AD is queryable via LDAP/PowerShell.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Audit Logging Plan ---- #

class AuditLoggingPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        mech = rule.get("verification_mechanism", "").lower()
        cap = rule.get("business_capability", "").lower()
        return "auditpol" in mech or "audit log" in cap or "logging" in cap

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Audit Policy — Logon Events",
                description="Confirm logon and logoff events are audited for both success and failure.",
                verification_platform="Windows",
                verification_mechanism="auditpol",
                command='auditpol /get /subcategory:"Logon" | findstr /i "success failure"',
                command_type="CMD",
                command_parameters="Run as Administrator.",
                expected_result="Logon: Success and Failure",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["auditpol CMD Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.93,
                reasoning="Audit policy state for specific subcategories is directly machine-readable.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Audit Policy — Object Access",
                description="Confirm object access events (file, registry) are audited.",
                verification_platform="Windows",
                verification_mechanism="auditpol",
                command='auditpol /get /subcategory:"File System" | findstr /i "success failure"',
                command_type="CMD",
                command_parameters="Run as Administrator.",
                expected_result="File System: Success and Failure",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["auditpol CMD Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.90,
                reasoning="File system audit state is readable via auditpol.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify Security Event Log Size and Retention",
                description="Confirm the Security event log is configured with adequate retention.",
                verification_platform="Windows",
                verification_mechanism="Get-WinEvent / wevtutil",
                command='wevtutil gl Security | findstr /i "maxSize retention"',
                command_type="CMD",
                command_parameters="Run as Administrator.",
                expected_result="maxSize >= 104857600 (100MB); retention: 0 (overwrite as needed) or configured.",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["wevtutil CMD Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.88,
                reasoning="Event log configuration is directly queryable without departmental input.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 4),
                title="Verify Recent Security Events Exist",
                description="Confirm that security events are being generated and not suppressed.",
                verification_platform="Windows",
                verification_mechanism="Get-WinEvent",
                command="(Get-WinEvent -LogName Security -MaxEvents 1).TimeCreated",
                command_type="PowerShell",
                command_parameters="Run on target host. Confirm timestamp is recent.",
                expected_result="Timestamp within last 24 hours.",
                comparison_operator=">=",
                expected_data_type="Date",
                evidence_required=["PowerShell Timestamp Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=False,
                failure_impact="MINOR",
                confidence=0.85,
                reasoning="Presence of recent events confirms the logging pipeline is active.",
                dependencies=_dep(plan_id, 4),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Registry Configuration Plan ---- #

class RegistryPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        return "reg query" in rule.get("executable_command", "").lower() or \
               rule.get("verification_type", "") == "Registry Check"

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Query Target Registry Key Existence",
                description="Verify the required registry key exists at the expected path.",
                verification_platform="Windows",
                verification_mechanism="reg query",
                command='reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"',
                command_type="CMD",
                command_parameters="Adapt the registry key path to the specific control. Run as Administrator.",
                expected_result="Key exists and is accessible. Exit code 0.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["reg query CMD Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.90,
                reasoning="Registry key existence is directly queryable. Exit code 0 = key exists.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Registry Value Meets Requirement",
                description="Read the specific registry value and confirm it matches the required setting.",
                verification_platform="Windows",
                verification_mechanism="reg query",
                command='reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA',
                command_type="CMD",
                command_parameters="Replace the value name with the specific setting to verify. Expected: 0x1 (enabled).",
                expected_result="EnableLUA = 0x1",
                comparison_operator="==",
                expected_data_type="String",
                evidence_required=["reg query Output", "Registry Export File"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.88,
                reasoning="Registry value content is machine-readable and directly comparable.",
                dependencies=_gate_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Export Registry Hive as Evidence",
                description="Export the relevant registry key to a .reg file for archival.",
                verification_platform="Windows",
                verification_mechanism="reg export",
                command='reg export "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" "RegistryEvidence.reg"',
                command_type="CMD",
                command_parameters="Run as Administrator. Upload .reg file as evidence artefact.",
                expected_result=".reg file created in working directory.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["Exported .reg File", "File Timestamp"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.95,
                reasoning="Registry export is a fully automated, single-command operation.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- SQL Database Verification Plan ---- #

class SQLDatabasePlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        return rule.get("verification_type", "") == "SQL Query" or \
               "sql" in rule.get("verification_mechanism", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Database Encryption Status",
                description="Query sys.databases to confirm Transparent Data Encryption is enabled on all production databases.",
                verification_platform="SQL Server",
                verification_mechanism="T-SQL",
                command="SELECT name, is_encrypted FROM sys.databases WHERE is_encrypted = 0 AND name NOT IN ('master','tempdb','model','msdb');",
                command_type="SQL",
                command_parameters="Run with READ access on target SQL Server instance. Zero rows = compliant.",
                expected_result="Zero rows returned (all production databases encrypted).",
                comparison_operator="==",
                expected_data_type="Integer",
                evidence_required=["SQL Query Output Export"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.90,
                reasoning="is_encrypted is a binary flag in sys.databases — directly machine-readable.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Database Audit Specification is Active",
                description="Confirm SQL Server Audit Specification is enabled and capturing relevant events.",
                verification_platform="SQL Server",
                verification_mechanism="T-SQL",
                command="SELECT name, is_state_enabled FROM sys.server_audit_specifications WHERE is_state_enabled = 0;",
                command_type="SQL",
                command_parameters="Run with VIEW SERVER STATE permission.",
                expected_result="Zero rows returned (all audit specifications enabled).",
                comparison_operator="==",
                expected_data_type="Integer",
                evidence_required=["SQL Query Output Export"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.87,
                reasoning="Audit specification state is readable from system catalog.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify Principle of Least Privilege — sysadmin Members",
                description="List all accounts in the sysadmin fixed server role to detect over-privileged accounts.",
                verification_platform="SQL Server",
                verification_mechanism="T-SQL",
                command="SELECT l.name, l.type_desc FROM sys.server_role_members rm JOIN sys.server_principals l ON rm.member_principal_id = l.principal_id WHERE rm.role_principal_id = SUSER_ID('sysadmin');",
                command_type="SQL",
                command_parameters="Run with VIEW SERVER STATE permission. Review output against approved admin list.",
                expected_result="Only authorised DBAs listed. No application service accounts in sysadmin role.",
                comparison_operator="manual",
                expected_data_type="List",
                evidence_required=["SQL Query Output", "Approved Admin List"],
                machine_verifiable=False,
                automation_candidate=True,
                mandatory=False,
                failure_impact="MAJOR",
                confidence=0.82,
                reasoning="sysadmin membership is machine-queryable but compliance decision requires comparison against an approved list (manual step).",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Regulatory Reporting Plan ---- #

class RegulatoryReportingPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        return rule.get("verification_type", "") == "Document Review" and \
               "reporting" in rule.get("business_capability", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify Return Submission History via RBI Portal",
                description="Log in to the RBI CIMS / regulatory submission portal and retrieve the submission history for the applicable return type and period.",
                verification_platform="Browser",
                verification_mechanism="RBI CIMS Portal",
                command="",
                command_type="Browser",
                command_parameters="Navigate to rbi.org.in → CIMS login → Submission History. Filter by return type and period.",
                expected_result="All returns for the verification period show status 'Submitted' or 'Accepted'. No overdue or missing submissions.",
                comparison_operator="manual",
                expected_data_type="String",
                evidence_required=["Portal Submission History Screenshot"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.82,
                reasoning="Submission status is independently verifiable via the RBI portal without asking the submitting department.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Submission Acknowledgement Receipt on File",
                description="Confirm the institution holds the RBI/regulator acknowledgement receipt for each submitted return.",
                verification_platform="Application",
                verification_mechanism="Document Management System",
                command="",
                command_type="Manual",
                command_parameters="Access the document management system or shared drive. Locate acknowledgement receipts for each return.",
                expected_result="Acknowledgement receipts present for all submissions within the review period. Receipts match submission dates on portal.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["Acknowledgement Receipt PDF"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.80,
                reasoning="Acknowledgement receipts are documentary evidence independent of the submitting team.",
                dependencies=_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify Authorised Signatory Approval on Submitted Return",
                description="Confirm submitted returns were approved by an authorised signatory before submission.",
                verification_platform="Application",
                verification_mechanism="Document Review",
                command="",
                command_type="Manual",
                command_parameters="Review the submitted return documents for authorised signatory signature or digital approval trail.",
                expected_result="Sign-off from MD/CEO/Principal Officer visible on submitted return.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["Signed Submission Document", "Approval Workflow Screenshot"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.78,
                reasoning="Signatory approval is independently verifiable through the submission document itself.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- KYC / AML Database Plan ---- #

class KYCAMLPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        cap = rule.get("business_capability", "").lower()
        return "kyc" in cap or "aml" in cap or "due diligence" in cap or "transaction monitoring" in cap

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Query Active Accounts Without Verified KYC",
                description="Run a database query to identify active customer accounts that lack verified KYC status.",
                verification_platform="Core Banking",
                verification_mechanism="Core Banking SQL",
                command="SELECT COUNT(*) AS non_compliant FROM customer_master WHERE kyc_status NOT IN ('VERIFIED','COMPLIANT') AND account_status = 'ACTIVE';",
                command_type="SQL",
                command_parameters="Adapt column/table names to the institution's core banking schema. Run with READ-ONLY credentials on production replica.",
                expected_result="COUNT = 0. Zero active accounts with non-compliant KYC status.",
                comparison_operator="==",
                expected_data_type="Integer",
                evidence_required=["SQL Query Output Export"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.85,
                reasoning="KYC status is stored in the core banking database and is queryable without involving the KYC team.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify STR Filing Rate Within Threshold",
                description="Confirm the volume of Suspicious Transaction Reports (STRs) filed in the period is consistent with prior periods and risk profile.",
                verification_platform="Core Banking",
                verification_mechanism="FIU/IND Submission Portal or Transaction Monitoring System",
                command="SELECT COUNT(*) AS strs_filed FROM str_register WHERE filing_date >= DATEADD(month,-3,GETDATE());",
                command_type="SQL",
                command_parameters="Adapt to the institution's STR register table. Cross-reference with FIU-IND portal submissions.",
                expected_result="STR count is non-zero and consistent with risk exposure. All filed STRs have FIU-IND acknowledgement.",
                comparison_operator=">",
                expected_data_type="Integer",
                evidence_required=["STR Register Export", "FIU-IND Acknowledgements"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.80,
                reasoning="STR filing count is queryable from the transaction monitoring or compliance system database.",
                dependencies=_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Review Sample Customer KYC Files",
                description="Independently review a random sample of customer KYC files for completeness and authenticity.",
                verification_platform="Application",
                verification_mechanism="Document Management System Sampling",
                command="",
                command_type="Manual",
                command_parameters="Select a random sample (minimum 30 records) using a random number generator. Access KYC documents in DMS.",
                expected_result="All sampled records have: valid ID proof, address proof, photograph, risk categorisation, and periodic review date.",
                comparison_operator="manual",
                expected_data_type="String",
                evidence_required=["Sampling Methodology Note", "Completed Review Checklist", "Auditor Sign-Off"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=False,
                failure_impact="MAJOR",
                confidence=0.75,
                reasoning="Document completeness requires human review of physical/digital documents. Sampling is independently controlled.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Certificate / TLS Plan ---- #

class TLSPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        mech = rule.get("verification_mechanism", "").lower()
        return "openssl" in mech or "tls" in rule.get("business_capability", "").lower() or \
               "certificate" in rule.get("business_capability", "").lower()

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title="Verify TLS Protocol Version",
                description="Connect to the target endpoint and confirm that TLS 1.2 or higher is negotiated.",
                verification_platform="Application",
                verification_mechanism="OpenSSL",
                command="openssl s_client -connect <hostname>:443 -tls1_2 2>&1 | grep -E 'Protocol|Verify'",
                command_type="Linux",
                command_parameters="Replace <hostname> with the target FQDN. Run from an external or DMZ host.",
                expected_result="Protocol: TLSv1.2 or TLSv1.3. Verify return code: 0 (ok).",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["OpenSSL Connection Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.93,
                reasoning="TLS protocol version is directly observable in the OpenSSL handshake output.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Verify Certificate Expiry Date",
                description="Extract and verify the certificate expiry date is not within 30 days.",
                verification_platform="Application",
                verification_mechanism="OpenSSL",
                command="openssl s_client -connect <hostname>:443 2>/dev/null | openssl x509 -noout -dates",
                command_type="Linux",
                command_parameters="Replace <hostname>. Check notAfter date.",
                expected_result="notAfter date > today + 30 days.",
                comparison_operator=">",
                expected_data_type="Date",
                evidence_required=["OpenSSL Certificate Dates Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.95,
                reasoning="Certificate expiry date is directly readable from the X.509 certificate.",
                dependencies=[],
                parallel_eligible=True,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Verify No Weak Cipher Suites Negotiated",
                description="Confirm that weak or deprecated cipher suites (RC4, DES, 3DES, EXPORT) are not accepted.",
                verification_platform="Application",
                verification_mechanism="OpenSSL",
                command="openssl s_client -connect <hostname>:443 -cipher 'RC4:DES:3DES:EXPORT' 2>&1 | grep 'handshake failure'",
                command_type="Linux",
                command_parameters="A successful handshake failure means weak ciphers are correctly rejected.",
                expected_result="handshake failure (weak ciphers rejected).",
                comparison_operator="contains",
                expected_data_type="String",
                evidence_required=["OpenSSL Cipher Test Output"],
                machine_verifiable=True,
                automation_candidate=True,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.90,
                reasoning="Cipher suite negotiation outcome is directly readable in OpenSSL output.",
                dependencies=_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---- Generic Document Review / Manual Plan ---- #

class GenericManualPlan(PlanStrategy):
    def matches(self, rule: Dict[str, Any]) -> bool:
        return True  # Fallback

    def build_checks(self, rule: Dict[str, Any], plan_id: str) -> List[VerificationCheck]:
        b = self._base_check
        cap = rule.get("business_capability", "this control")
        evidence = rule.get("evidence_required", ["Supporting Documentation"])
        expected = rule.get("expected_result", "Control implementation is evidenced.")
        mech = rule.get("verification_mechanism", "Structured Review")
        params = rule.get("command_parameters", "")

        checks = [
            VerificationCheck(
                **b(plan_id, 1),
                title=f"Verify existence of implementation evidence",
                description=f"Locate and confirm that documentary evidence of '{cap}' implementation exists in the evidence repository.",
                verification_platform=rule.get("verification_platform", "Application"),
                verification_mechanism=mech,
                command="",
                command_type="Manual",
                command_parameters=params or "Access document management system or shared compliance drive.",
                expected_result="Evidence documents are present, dated within the verification period, and signed by the responsible owner.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=evidence[:3],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.70,
                reasoning="Document existence is verifiable by an independent reviewer without requiring departmental cooperation.",
                dependencies=[],
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 2),
                title="Assess Adequacy of Evidence Against Control Objective",
                description=f"Review evidence content to confirm it adequately demonstrates compliance with the control objective for '{cap}'.",
                verification_platform=rule.get("verification_platform", "Application"),
                verification_mechanism="Structured Compliance Walkthrough",
                command="",
                command_type="Manual",
                command_parameters="Apply compliance review checklist. Document findings.",
                expected_result=expected,
                comparison_operator="manual",
                expected_data_type="String",
                evidence_required=["Completed Review Checklist", "Auditor Notes"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="MAJOR",
                confidence=0.65,
                reasoning="Adequacy assessment requires professional judgment from an independent reviewer.",
                dependencies=_gate_dep(plan_id, 2),
                parallel_eligible=False,
            ),
            VerificationCheck(
                **b(plan_id, 3),
                title="Auditor Sign-Off on Verification Outcome",
                description="The reviewing auditor or compliance officer formally records the outcome of verification.",
                verification_platform="Application",
                verification_mechanism="Compliance System Sign-Off",
                command="",
                command_type="Manual",
                command_parameters="Record findings in the compliance management system. Attach evidence references.",
                expected_result="Verification outcome (PASS/FAIL/PARTIAL) recorded with auditor signature and timestamp.",
                comparison_operator="exists",
                expected_data_type="String",
                evidence_required=["Signed Verification Record"],
                machine_verifiable=False,
                automation_candidate=False,
                mandatory=True,
                failure_impact="BLOCKER",
                confidence=0.75,
                reasoning="Formal sign-off creates an immutable audit trail independent of the implementing department.",
                dependencies=_gate_dep(plan_id, 3),
                parallel_eligible=False,
            ),
        ]
        return checks


# ---------------------------------------------------------------------------
# Strategy Registry
# ---------------------------------------------------------------------------

PLAN_REGISTRY: List[PlanStrategy] = [
    ADPasswordPolicyPlan(),
    FirewallPlan(),
    DiskEncryptionPlan(),
    AuditLoggingPlan(),
    RegistryPlan(),
    SQLDatabasePlan(),
    TLSPlan(),
    RegulatoryReportingPlan(),
    KYCAMLPlan(),
    GenericManualPlan(),   # Fallback — always last
]


def _select_strategy(rule: Dict[str, Any]) -> PlanStrategy:
    for strategy in PLAN_REGISTRY:
        if strategy.matches(rule):
            return strategy
    return PLAN_REGISTRY[-1]


# ---------------------------------------------------------------------------
# DAG Builder
# ---------------------------------------------------------------------------

def _build_dag(checks: List[VerificationCheck]) -> ExecutionDAG:
    nodes: List[DAGNode] = []
    parallel_groups = 0
    has_gates = False

    parallel_group_open = False
    for c in checks:
        is_gate = any(d.dependency_type == "PASS_GATE" for d in c.dependencies)
        if is_gate:
            has_gates = True
        if c.parallel_eligible and not parallel_group_open:
            parallel_groups += 1
            parallel_group_open = True
        elif not c.parallel_eligible:
            parallel_group_open = False

        nodes.append(DAGNode(
            check_id=c.check_id,
            sequence_number=c.sequence_number,
            depends_on=[d.depends_on_check_id for d in c.dependencies],
            parallel_eligible=c.parallel_eligible,
            is_gate=is_gate,
        ))

    # Critical path = total sequential mandatory checks
    mandatory_sequential = sum(1 for c in checks if c.mandatory and not c.parallel_eligible)
    critical_path = mandatory_sequential + (1 if parallel_groups else 0)

    return ExecutionDAG(
        nodes=nodes,
        total_sequential_steps=sum(1 for c in checks if not c.parallel_eligible),
        parallelisable_groups=parallel_groups,
        critical_path_length=critical_path,
        has_mandatory_gates=has_gates,
    )


# ---------------------------------------------------------------------------
# Plan Builder
# ---------------------------------------------------------------------------

def _plan_id(rule: Dict[str, Any]) -> str:
    return f"CVP_{rule.get('rule_id', 'unknown')}"


def _estimate_execution(checks: List[VerificationCheck]) -> Tuple[int, float]:
    """Returns (minutes_total, manual_effort_hours)."""
    machine_time = sum(
        max(c.timeout_seconds // 60, 1) for c in checks if c.machine_verifiable
    )
    manual_time_mins = sum(
        15 for c in checks if not c.machine_verifiable
    )
    total_mins = machine_time + manual_time_mins
    manual_hrs = round(manual_time_mins / 60, 2)
    return total_mins, manual_hrs


def _automation_pct(checks: List[VerificationCheck]) -> float:
    if not checks:
        return 0.0
    auto = sum(1 for c in checks if c.automation_candidate)
    return round(auto / len(checks) * 100, 1)


def build_plan(rule: Dict[str, Any]) -> VerificationPlan:
    plan_id = _plan_id(rule)
    strategy = _select_strategy(rule)
    checks = strategy.build_checks(rule, plan_id)

    exec_mins, manual_hrs = _estimate_execution(checks)
    auto_pct = _automation_pct(checks)
    dag = _build_dag(checks)

    parallel_possible = any(c.parallel_eligible for c in checks)
    mandatory_count = sum(1 for c in checks if c.mandatory)
    mv_count = sum(1 for c in checks if c.machine_verifiable)

    avg_conf = round(sum(c.confidence for c in checks) / len(checks), 2) if checks else 0.5
    crit = rule.get("criticality", "MEDIUM")
    pass_condition = "ALL_MANDATORY" if crit in ("CRITICAL", "HIGH") else "ALL_CHECKS"

    return VerificationPlan(
        plan_id=plan_id,
        rule_id=rule.get("rule_id", ""),
        requirement_id=rule.get("requirement_id", ""),
        document_id=rule.get("document_id", ""),
        logical_unit_id=rule.get("logical_unit_id", ""),
        control_name=rule.get("control_name", ""),
        business_capability=rule.get("business_capability", ""),
        control_category=rule.get("control_category", ""),
        criticality=crit,
        verification_strategy=strategy.strategy_name(),
        estimated_execution_minutes=exec_mins,
        estimated_manual_effort_hours=manual_hrs,
        automation_percentage=auto_pct,
        parallel_execution_possible=parallel_possible,
        checks=checks,
        total_checks=len(checks),
        mandatory_checks=mandatory_count,
        machine_verifiable_checks=mv_count,
        execution_dag=dag,
        pass_condition=pass_condition,
        final_decision_rule=(
            f"PASS if all {mandatory_count} mandatory checks produce PASS result. "
            f"FAIL if any BLOCKER check fails. PARTIAL if only MINOR checks fail."
        ),
        compliance_domain=rule.get("compliance_domain", []),
        risk_domain=rule.get("risk_domain", []),
        candidate_departments=rule.get("candidate_departments", []),
        page_numbers=rule.get("page_numbers", []),
        hierarchy_node_ids=rule.get("hierarchy_node_ids", []),
        block_ids=rule.get("block_ids", []),
        confidence=avg_conf,
    )


# ---------------------------------------------------------------------------
# Engine Orchestrator
# ---------------------------------------------------------------------------

class ComplianceVerificationPlanner:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        self._ensure_directories()
        self._setup_logging()

        self.stats = {
            "documents_processed": 0,
            "plans_generated": 0,
            "checks_generated": 0,
            "machine_verifiable_checks": 0,
            "automation_candidates": 0,
            "strategies_used": Counter(),
            "command_types": Counter(),
            "failure_impacts": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_file = self.log_dir / "compliance_verification_planner.log"
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

    def _update_stats(self, plan: VerificationPlan) -> None:
        self.stats["plans_generated"] += 1
        self.stats["checks_generated"] += plan.total_checks
        self.stats["machine_verifiable_checks"] += plan.machine_verifiable_checks
        self.stats["strategies_used"][plan.verification_strategy] += 1
        for c in plan.checks:
            if c.automation_candidate:
                self.stats["automation_candidates"] += 1
            self.stats["command_types"][c.command_type] += 1
            self.stats["failure_impacts"][c.failure_impact] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f_check:
                    existing = json.load(f_check)
                if existing.get("plan_count", 0) > 0:
                    self.logger.info(f"Skipping {doc_id} — verification plans already generated.")
                    return
                else:
                    self.logger.warning(f"Overwriting empty/poisoned output file for {doc_id}.")
            except Exception:
                self.logger.warning(f"Overwriting unreadable output file for {doc_id}.")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        rules = doc.get("verification_rules", [])
        plans: List[Dict[str, Any]] = []

        for rule in rules:
            try:
                plan = build_plan(rule)
                self._update_stats(plan)
                plans.append(asdict(plan))
            except Exception as e:
                self.logger.error(f"Plan build failed for {rule.get('rule_id')}: {e}")

        output = {
            "document_id": doc_id,
            "title": doc.get("title", doc_id),
            "document_status": doc.get("document_status", "ACTIVE"),
            "plan_count": len(plans),
            "verification_plans": plans,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.stats["documents_processed"] += 1
            self.logger.info(f"Generated {len(plans)} verification plans for {doc_id}")
        except Exception as e:
            self.logger.error(f"Cannot write {output_file}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory not found: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} verification rule documents to process.")

        for json_path in tqdm(json_files, desc="Building verification plans"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        plans = self.stats["plans_generated"]
        checks = self.stats["checks_generated"]
        avg_checks = checks / plans if plans else 0.0

        def fmt(c: Counter, top: int = 8) -> str:
            return "\n".join(f"  {k:<40} {v}" for k, v in c.most_common(top)) or "  (none)"

        summary = (
            f"\n{'='*65}\n"
            f" COMPLIANCE VERIFICATION PLANNER SUMMARY\n"
            f"{'='*65}\n"
            f"Documents processed:             {self.stats['documents_processed']}\n"
            f"Verification plans generated:    {plans}\n"
            f"Total checks generated:          {checks}\n"
            f"Average checks per plan:         {avg_checks:.2f}\n"
            f"Machine-verifiable checks:       {self.stats['machine_verifiable_checks']}\n"
            f"Automation candidates:           {self.stats['automation_candidates']}\n"
            f"\nPlan Strategy Distribution:\n{fmt(self.stats['strategies_used'])}\n"
            f"\nCommand Type Distribution:\n{fmt(self.stats['command_types'])}\n"
            f"\nFailure Impact Distribution:\n{fmt(self.stats['failure_impacts'])}\n"
            f"\nOutput directory:                {self.output_dir}\n"
            f"{'='*65}\n"
        )
        print(summary)
        self.logger.info("Compliance Verification Planner complete.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    planner = ComplianceVerificationPlanner(
        input_dir=project_root / "datasets" / "verification_rules",
        output_dir=project_root / "datasets" / "verification_plans",
        log_dir=project_root / "logs",
    )
    planner.run()
