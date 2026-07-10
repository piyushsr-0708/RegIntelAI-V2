"""
Mitigation Action Plan (MAP) Generation Engine V1 — RegIntel AI (SuRaksha-v2)

Transforms Compliance Controls into granular, executable Mitigation Action Plans.
Each MAP contains 2–8 ordered, dependency-aware, verifiable tasks designed for
realistic enterprise compliance execution.

All task generation is deterministic and rule-based.
Future LLM strategies can replace individual task templates without changing the
orchestration layer.
"""

import json
import logging
import sys
import uuid
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
class MitigationTask:
    task_id: str
    map_id: str
    task_number: int
    title: str
    description: str
    task_type: str
    assigned_department: str
    assigned_user: Optional[str]
    priority: str
    estimated_effort_hours: int
    status: str
    dependencies: List[str]          # list of task_id values this task depends on
    deliverable: str
    verification_method: str
    verification_rule_reference: str
    expected_evidence: str
    machine_verifiable: bool
    automation_candidate: bool
    automation_platform: str
    approval_required: bool
    approval_role: str
    implementation_notes: str


@dataclass
class MitigationActionPlan:
    map_id: str
    control_id: str
    document_id: str
    title: str
    objective: str
    priority: str
    criticality: str
    status: str
    owner_department: str
    compliance_domain: List[str]
    risk_domain: List[str]
    estimated_total_effort_hours: int
    task_count: int
    generated_timestamp: str
    tasks: List[MitigationTask]


# ---------------------------------------------------------------------------
# Task Template Library
# ---------------------------------------------------------------------------
# Each template is a callable that takes the control dict and returns task fields.

class TaskTemplateBase(ABC):
    @abstractmethod
    def build(self, control: Dict[str, Any], map_id: str, task_number: int,
              prev_task_id: Optional[str]) -> MitigationTask:
        pass

    def _make_id(self, map_id: str, task_number: int) -> str:
        return f"{map_id}_T{task_number:02d}"

    def _dep(self, map_id: str, task_number: int) -> List[str]:
        if task_number <= 1:
            return []
        return [f"{map_id}_T{(task_number - 1):02d}"]

    def _priority(self, control: Dict[str, Any]) -> str:
        return control.get("criticality", "MEDIUM")


# ---- Specific templates ---- #

class GapAssessmentTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        impl_cat = control.get("implementation_category", "")
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Assess current state against: {ctrl_name[:60]}",
            description=(
                f"Conduct a current-state gap assessment to determine the extent to which "
                f"the organisation currently satisfies the requirement for '{ctrl_name}'. "
                f"Document the existing {impl_cat or 'operational'} posture, identify gaps, "
                f"and record findings as a Gap Assessment Report."
            ),
            task_type="Review",
            assigned_department=_lead_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Review"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Gap Assessment Report",
            verification_method="Document Review",
            verification_rule_reference="",
            expected_evidence="Completed Gap Assessment Report signed by Department Head",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=False,
            approval_role="",
            implementation_notes=f"Review control description: {control.get('control_description', '')[:200]}"
        )


class PolicyDraftingTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Draft or update policy for: {ctrl_name[:55]}",
            description=(
                f"Draft or update the internal policy document to formally mandate "
                f"'{ctrl_name}'. The policy must reference the applicable RBI Master Direction, "
                f"define scope, roles & responsibilities, and set measurable compliance thresholds. "
                f"Circulate draft to all candidate departments for review comments."
            ),
            task_type="Design",
            assigned_department=_lead_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Design"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Draft Policy Document",
            verification_method="Policy Review",
            verification_rule_reference="",
            expected_evidence="Draft policy document in PDF format with version number and author",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=False,
            approval_role="",
            implementation_notes="Include specific RBI circular reference and effective date clause."
        )


class PolicyApprovalTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Obtain Board/Management approval for policy: {ctrl_name[:40]}",
            description=(
                f"Present the drafted policy for '{ctrl_name}' to the Board or Senior Management "
                f"for formal ratification. Record approval in the Board/Committee meeting minutes. "
                f"Ensure the approved policy is version-controlled and stored in the policy repository."
            ),
            task_type="Approve",
            assigned_department="Board",
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Approve"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Approved Policy with Board/Committee Minutes",
            verification_method="Document Review",
            verification_rule_reference="",
            expected_evidence="Board resolution or Committee minutes referencing policy approval",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=True,
            approval_role="Board / CISO / CRO",
            implementation_notes="Approval must be captured in formal minutes, not email."
        )


class TechnicalImplementationTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        impl_method = control.get("implementation_method", "")
        automation_possible = control.get("automation_possible", False)
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Implement technical control: {ctrl_name[:55]}",
            description=(
                f"Execute the technical implementation as specified: {impl_method[:300] or ctrl_name}. "
                f"Configuration changes must be applied on all applicable systems in the environment "
                f"(development, staging, and production). "
                f"All changes must be tracked in the Change Management Register with a Change Ticket."
            ),
            task_type="Implement",
            assigned_department=_tech_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Implement"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Change Ticket and Configuration Screenshot",
            verification_method=_best_verification_method(control),
            verification_rule_reference="",
            expected_evidence="Change Management Record with system configuration screenshot or export",
            machine_verifiable=automation_possible,
            automation_candidate=automation_possible,
            automation_platform=_automation_platform(control),
            approval_required=True,
            approval_role="IT Manager / CISO",
            implementation_notes=(
                f"Before applying, take a baseline snapshot of current configuration. "
                f"Apply change during a pre-approved maintenance window."
            )
        )


class ConfigureSystemTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        impl_cat = control.get("implementation_category", "")
        automation_possible = control.get("automation_possible", False)
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Configure system parameters: {ctrl_name[:50]}",
            description=(
                f"Apply specific configuration parameters for '{ctrl_name}'. "
                f"Refer to applicable vendor documentation or Group Policy / Registry / OS settings "
                f"for the exact parameter names and values required. "
                f"Validate changes do not conflict with existing business configurations. "
                f"Document pre-change and post-change configuration states."
            ),
            task_type="Configure",
            assigned_department=_tech_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Configure"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Configuration Export or Registry/Policy Dump",
            verification_method=_best_verification_method(control),
            verification_rule_reference="",
            expected_evidence="PowerShell output, Registry export, or system configuration dump",
            machine_verifiable=True,
            automation_candidate=automation_possible,
            automation_platform=_automation_platform(control),
            approval_required=False,
            approval_role="",
            implementation_notes="Ensure rollback script is prepared prior to making changes."
        )


class TestingAndValidationTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        automation_possible = control.get("automation_possible", False)
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Test and validate implementation: {ctrl_name[:45]}",
            description=(
                f"Execute functional and compliance testing to confirm that '{ctrl_name}' "
                f"has been implemented correctly. "
                f"Tests must cover positive scenarios (compliant behaviour is accepted) "
                f"and negative scenarios (non-compliant behaviour is rejected). "
                f"Record all test cases, inputs, outputs, and pass/fail results in a Test Report."
            ),
            task_type="Test",
            assigned_department=_tech_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Test"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Test Report with Pass/Fail Matrix",
            verification_method=_best_verification_method(control),
            verification_rule_reference="",
            expected_evidence="Test report PDF with test case results and system output evidence",
            machine_verifiable=automation_possible,
            automation_candidate=automation_possible,
            automation_platform=_automation_platform(control),
            approval_required=False,
            approval_role="",
            implementation_notes="All tests must pass before proceeding to the next task."
        )


class EvidenceCollectionTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        expected_evs = control.get("expected_evidence", ["Evidence"])
        ev_str = expected_evs[0] if expected_evs else "Evidence"
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Collect and archive compliance evidence: {ctrl_name[:40]}",
            description=(
                f"Formally collect all evidence artifacts generated during the implementation "
                f"of '{ctrl_name}'. Required evidence types: {', '.join(expected_evs[:3])}. "
                f"Evidence must be labelled with document name, version, date, and responsible officer. "
                f"Upload to the compliance evidence management system with a retention label."
            ),
            task_type="Collect Evidence",
            assigned_department=_lead_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Collect Evidence"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable=ev_str,
            verification_method="Evidence Review",
            verification_rule_reference="",
            expected_evidence=f"All required evidence items: {', '.join(expected_evs[:3])}",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=False,
            approval_role="",
            implementation_notes="Evidence must be stored with minimum 5-year retention."
        )


class InternalAuditVerificationTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        verification_method = _best_verification_method(control)
        automation_possible = control.get("automation_possible", False)
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Independent verification by Internal Audit: {ctrl_name[:35]}",
            description=(
                f"Internal Audit must independently verify that '{ctrl_name}' is effectively "
                f"implemented and that the evidence provided is authentic and sufficient. "
                f"Verification method: {verification_method}. "
                f"Internal Audit must NOT rely solely on evidence submitted by the implementing department. "
                f"Perform independent spot-checks or automated configuration queries. "
                f"Issue an Audit Verification Certificate upon satisfactory completion."
            ),
            task_type="Verify",
            assigned_department="Internal Audit",
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Verify"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Audit Verification Certificate",
            verification_method=verification_method,
            verification_rule_reference="",
            expected_evidence="Independent Audit Verification Certificate signed by Chief Audit Officer",
            machine_verifiable=automation_possible,
            automation_candidate=automation_possible,
            automation_platform=_automation_platform(control),
            approval_required=True,
            approval_role="Chief Audit Officer",
            implementation_notes=(
                "This is an independent gate task. The MAP cannot close until this task is COMPLETED. "
                "Auditors should not accept evidence uploaded by the same team that implemented the control."
            )
        )


class ComplianceOfficerSignOffTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Compliance Officer sign-off and MAP closure: {ctrl_name[:30]}",
            description=(
                f"The Compliance Officer must review all completed tasks, evidence artifacts, "
                f"and the Internal Audit Verification Certificate for '{ctrl_name}'. "
                f"If all tasks pass review, the Compliance Officer formally attests "
                f"that the control is operationally satisfied. "
                f"Update the Compliance Register. Mark the MAP as COMPLETED. "
                f"Notify RBI-liaison team if a regulatory reporting obligation is attached."
            ),
            task_type="Approve",
            assigned_department="Compliance",
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Approve"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Signed Compliance Attestation and Updated Compliance Register",
            verification_method="Document Review",
            verification_rule_reference="",
            expected_evidence="Signed Compliance Attestation letter and Compliance Register entry",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=True,
            approval_role="Chief Compliance Officer",
            implementation_notes="This is the final gate task. MAP status becomes COMPLETED after this task closes."
        )


class ReportingSubmissionTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Prepare and submit regulatory report: {ctrl_name[:40]}",
            description=(
                f"Prepare the regulatory report required under '{ctrl_name}'. "
                f"Ensure the report format complies with RBI prescribed templates "
                f"(XBRL, CIMS, or prescribed return format as applicable). "
                f"Have the report reviewed and signed by the authorised signatory before submission. "
                f"Retain a copy of the submitted report and the submission acknowledgement receipt."
            ),
            task_type="Submit",
            assigned_department="Compliance",
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Submit"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Submitted Report and Acknowledgement Receipt",
            verification_method="Document Review",
            verification_rule_reference="",
            expected_evidence="Signed submission copy and RBI/regulator acknowledgement receipt",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=True,
            approval_role="MD / CEO / Authorized Signatory",
            implementation_notes="Late submission attracts regulatory penalty. Set submission reminder 7 days before deadline."
        )


class MonitoringSetupTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        freq = control.get("control_frequency", "Event Driven")
        automation_possible = control.get("automation_possible", False)
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Set up ongoing monitoring for: {ctrl_name[:45]}",
            description=(
                f"Establish a continuous or periodic monitoring mechanism for '{ctrl_name}'. "
                f"Monitoring frequency: {freq}. "
                f"Configure automated alerts or manual review schedules as appropriate. "
                f"Define threshold breaches that trigger escalation and document the monitoring SOP. "
                f"Integrate monitoring output into the Compliance Dashboard."
            ),
            task_type="Monitor",
            assigned_department=_tech_department(control),
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Monitor"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Monitoring SOP and Dashboard Configuration",
            verification_method="Log Review",
            verification_rule_reference="",
            expected_evidence="Monitoring configuration screenshot and sample alert/log",
            machine_verifiable=automation_possible,
            automation_candidate=automation_possible,
            automation_platform=_automation_platform(control),
            approval_required=False,
            approval_role="",
            implementation_notes=f"Monitoring frequency set to: {freq}. Review thresholds quarterly."
        )


class TrainingDeliveryTask(TaskTemplateBase):
    def build(self, control, map_id, task_number, prev_task_id):
        crit = self._priority(control)
        ctrl_name = control.get("control_name", "Control")
        departments = control.get("candidate_departments", ["All Departments"])
        return MitigationTask(
            task_id=self._make_id(map_id, task_number),
            map_id=map_id,
            task_number=task_number,
            title=f"Conduct staff training on: {ctrl_name[:50]}",
            description=(
                f"Design and deliver a mandatory training programme on '{ctrl_name}' "
                f"for all relevant staff in: {', '.join(departments[:4])}. "
                f"Training content must cover the regulatory background, internal policy, "
                f"responsibilities, and reporting obligations. "
                f"Capture attendance records. Administer a post-training assessment. "
                f"Retain training records for a minimum of 3 years."
            ),
            task_type="Train",
            assigned_department="HR",
            assigned_user=None,
            priority=crit,
            estimated_effort_hours=_effort_hours(crit, "Train"),
            status="PENDING",
            dependencies=self._dep(map_id, task_number),
            deliverable="Training Completion Records and Assessment Results",
            verification_method="Document Review",
            verification_rule_reference="",
            expected_evidence="Signed attendance register and post-training assessment scores",
            machine_verifiable=False,
            automation_candidate=False,
            automation_platform="",
            approval_required=False,
            approval_role="",
            implementation_notes="Training must be refreshed annually or when the policy is materially updated."
        )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _lead_department(control: Dict[str, Any]) -> str:
    depts = control.get("candidate_departments", [])
    if depts and depts[0] != "Unknown":
        return depts[0]
    domains = control.get("related_compliance_domain", [])
    if "Cyber Security" in domains or "IT Governance" in domains:
        return "IT"
    if "AML" in domains or "KYC" in domains or "Reporting" in domains:
        return "Compliance"
    return "Compliance"


def _tech_department(control: Dict[str, Any]) -> str:
    depts = control.get("candidate_departments", [])
    if "IT" in depts:
        return "IT"
    if "Cyber Security" in depts:
        return "Cyber Security"
    impl_cat = control.get("implementation_category", "")
    if impl_cat in ("System Control", "Technical Control", "Configuration", "Access Control", "Encryption", "Logging"):
        return "IT"
    return _lead_department(control)


def _best_verification_method(control: Dict[str, Any]) -> str:
    impl_cat = control.get("implementation_category", "")
    auto = control.get("automation_possible", False)
    verification_methods = control.get("verification_method", [])
    if verification_methods:
        vm = verification_methods[0]
        if vm not in ("Document Review", "Unknown"):
            return vm
    if auto:
        return "Configuration Review"
    if impl_cat in ("System Control", "Access Control", "Encryption"):
        return "Configuration Review"
    if impl_cat == "Logging":
        return "Log Review"
    if impl_cat == "Policy":
        return "Policy Review"
    if impl_cat == "Reporting":
        return "Document Review"
    return "Manual Audit"


def _automation_platform(control: Dict[str, Any]) -> str:
    cat = control.get("automation_candidate", "")
    if cat:
        return cat
    impl_cat = control.get("implementation_category", "")
    desc = (control.get("control_description", "") + " " + control.get("implementation_method", "")).lower()
    if "windows" in desc or "active directory" in desc or "group policy" in desc:
        return "PowerShell"
    if "registry" in desc:
        return "Windows Registry"
    if "sql" in desc or "database" in desc:
        return "SQL"
    if "linux" in desc or "bash" in desc:
        return "Linux Command"
    if "api" in desc or "rest" in desc:
        return "API"
    if impl_cat in ("System Control", "Configuration", "Access Control", "Encryption"):
        return "Configuration Parser"
    return ""


def _effort_hours(criticality: str, task_type: str) -> int:
    base = {
        "Review": 4, "Design": 8, "Implement": 8, "Configure": 4,
        "Test": 6, "Verify": 4, "Approve": 2, "Submit": 3,
        "Collect Evidence": 2, "Monitor": 4, "Train": 8,
    }.get(task_type, 4)
    mult = {"CRITICAL": 2.0, "HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.75}.get(criticality, 1.0)
    return max(1, int(base * mult))


def _gen_map_id(control_id: str) -> str:
    return f"MAP_{control_id}"


def _criticality_to_priority(crit: str) -> str:
    return {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}.get(crit, "MEDIUM")


# ---------------------------------------------------------------------------
# Task Sequence Selector
# ---------------------------------------------------------------------------

POLICY_SEQUENCE = [
    GapAssessmentTask(),
    PolicyDraftingTask(),
    PolicyApprovalTask(),
    EvidenceCollectionTask(),
    InternalAuditVerificationTask(),
    ComplianceOfficerSignOffTask(),
]

TECHNICAL_SEQUENCE = [
    GapAssessmentTask(),
    TechnicalImplementationTask(),
    ConfigureSystemTask(),
    TestingAndValidationTask(),
    EvidenceCollectionTask(),
    InternalAuditVerificationTask(),
    ComplianceOfficerSignOffTask(),
]

REPORTING_SEQUENCE = [
    GapAssessmentTask(),
    PolicyDraftingTask(),
    ReportingSubmissionTask(),
    EvidenceCollectionTask(),
    ComplianceOfficerSignOffTask(),
]

AUDIT_SEQUENCE = [
    GapAssessmentTask(),
    EvidenceCollectionTask(),
    InternalAuditVerificationTask(),
    ComplianceOfficerSignOffTask(),
]

MONITORING_SEQUENCE = [
    GapAssessmentTask(),
    TechnicalImplementationTask(),
    MonitoringSetupTask(),
    EvidenceCollectionTask(),
    InternalAuditVerificationTask(),
    ComplianceOfficerSignOffTask(),
]

TRAINING_SEQUENCE = [
    GapAssessmentTask(),
    PolicyDraftingTask(),
    PolicyApprovalTask(),
    TrainingDeliveryTask(),
    EvidenceCollectionTask(),
    ComplianceOfficerSignOffTask(),
]

GENERAL_SEQUENCE = [
    GapAssessmentTask(),
    TechnicalImplementationTask(),
    EvidenceCollectionTask(),
    InternalAuditVerificationTask(),
    ComplianceOfficerSignOffTask(),
]


def select_task_sequence(control: Dict[str, Any]) -> List[TaskTemplateBase]:
    impl_cat = control.get("implementation_category", "")
    ctrl_type = control.get("control_type", "")

    if impl_cat == "Policy":
        return POLICY_SEQUENCE
    if impl_cat == "Reporting":
        return REPORTING_SEQUENCE
    if impl_cat == "Audit":
        return AUDIT_SEQUENCE
    if impl_cat == "Training":
        return TRAINING_SEQUENCE
    if impl_cat == "Monitoring":
        return MONITORING_SEQUENCE
    if ctrl_type == "Technical" or impl_cat in (
        "System Control", "Access Control", "Encryption", "Logging",
        "Backup", "Configuration"
    ):
        return TECHNICAL_SEQUENCE
    return GENERAL_SEQUENCE


# ---------------------------------------------------------------------------
# MAP Builder
# ---------------------------------------------------------------------------

def build_map(control: Dict[str, Any]) -> MitigationActionPlan:
    from datetime import datetime, timezone

    control_id = control.get("control_id", str(uuid.uuid4()))
    doc_id = control.get("document_id", "UNKNOWN")
    map_id = _gen_map_id(control_id)

    sequence = select_task_sequence(control)
    tasks: List[MitigationTask] = []
    prev_id = None
    for i, template in enumerate(sequence, start=1):
        task = template.build(control=control, map_id=map_id, task_number=i, prev_task_id=prev_id)
        prev_id = task.task_id
        tasks.append(task)

    total_effort = sum(t.estimated_effort_hours for t in tasks)
    crit = control.get("criticality", "MEDIUM")

    return MitigationActionPlan(
        map_id=map_id,
        control_id=control_id,
        document_id=doc_id,
        title=f"MAP: {control.get('control_name', 'Unnamed Control')[:120]}",
        objective=control.get("control_objective", ""),
        priority=_criticality_to_priority(crit),
        criticality=crit,
        status="DRAFT",
        owner_department=_lead_department(control),
        compliance_domain=control.get("related_compliance_domain", ["General"]),
        risk_domain=control.get("related_risk_domain", ["Unknown"]),
        estimated_total_effort_hours=total_effort,
        task_count=len(tasks),
        generated_timestamp=datetime.now(timezone.utc).isoformat(),
        tasks=tasks,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class MAPGenerationEngine:
    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        self._ensure_directories()
        self._setup_logging()

        self.stats = {
            "documents_processed": 0,
            "controls_processed": 0,
            "maps_generated": 0,
            "tasks_generated": 0,
            "machine_verifiable": 0,
            "automation_candidates": 0,
            "verification_methods": Counter(),
            "departments": Counter(),
        }

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_file = self.log_dir / "map_generator.log"
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

    def _update_stats(self, map_obj: MitigationActionPlan) -> None:
        self.stats["maps_generated"] += 1
        self.stats["tasks_generated"] += len(map_obj.tasks)
        for task in map_obj.tasks:
            if task.machine_verifiable:
                self.stats["machine_verifiable"] += 1
            if task.automation_candidate:
                self.stats["automation_candidates"] += 1
            self.stats["verification_methods"][task.verification_method] += 1
            self.stats["departments"][task.assigned_department] += 1

    def process_document(self, json_path: Path) -> None:
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"
        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — MAPs already generated.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        controls = doc.get("controls", [])
        maps: List[Dict] = []

        for ctrl in controls:
            self.stats["controls_processed"] += 1
            try:
                map_obj = build_map(ctrl)
                self._update_stats(map_obj)
                maps.append(asdict(map_obj))
            except Exception as e:
                self.logger.error(f"MAP generation failed for control {ctrl.get('control_id')}: {e}")

        output = {
            "document_id": doc_id,
            "title": doc.get("title", doc_id),
            "map_count": len(maps),
            "maps": maps,
        }

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            self.stats["documents_processed"] += 1
            self.logger.info(f"Generated {len(maps)} MAPs for {doc_id}")
        except Exception as e:
            self.logger.error(f"Cannot write {output_file}: {e}")

    def run(self) -> None:
        if not self.input_dir.exists():
            self.logger.error(f"Input directory not found: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} control documents to process.")

        for json_path in tqdm(json_files, desc="Generating MAPs"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        tasks = self.stats["tasks_generated"]
        maps = self.stats["maps_generated"]
        avg_tasks = tasks / maps if maps > 0 else 0.0

        def fmt(c: Counter) -> str:
            return "\n".join(f"  {k:<35} {v}" for k, v in c.most_common(8)) or "  (none)"

        summary = (
            f"\n{'='*60}\n"
            f" MITIGATION ACTION PLAN GENERATION SUMMARY\n"
            f"{'='*60}\n"
            f"Documents processed:         {self.stats['documents_processed']}\n"
            f"Controls processed:          {self.stats['controls_processed']}\n"
            f"MAPs generated:              {maps}\n"
            f"Tasks generated:             {tasks}\n"
            f"Average tasks per MAP:       {avg_tasks:.2f}\n"
            f"Machine-verifiable tasks:    {self.stats['machine_verifiable']}\n"
            f"Automation candidates:       {self.stats['automation_candidates']}\n"
            f"\nVerification Method Distribution:\n{fmt(self.stats['verification_methods'])}\n"
            f"\nDepartment Distribution:\n{fmt(self.stats['departments'])}\n"
            f"\nOutput directory:            {self.output_dir}\n"
            f"{'='*60}\n"
        )
        print(summary)
        self.logger.info("MAP generation complete.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    engine = MAPGenerationEngine(
        input_dir=project_root / "datasets" / "controls",
        output_dir=project_root / "datasets" / "maps",
        log_dir=project_root / "logs",
    )
    engine.run()
