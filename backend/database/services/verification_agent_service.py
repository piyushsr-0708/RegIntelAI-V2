"""
Verification Agent Service — Phase 1 (Refined Deterministic Reasoning)

The Verification Agent acts as an AI Compliance Officer that analyzes
verification context and provides intelligent recommendations based on:
- Verification plans
- Reasoned controls
- Interpreted controls
- MAP metadata
- Assignment context

This is NOT:
- A verification executor (that's compliance_verification_executor.py)
- A decision engine (that's compliance_decision_engine.py)
- A pipeline stage (this is runtime reasoning)
- A dataset generator (decisions are ephemeral unless logging needed)

Phase 1: Deterministic rule-based reasoning only
Phase 2 (future): Ollama-enhanced semantic reasoning
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class AgentDecision:
    """
    Decision output from the Verification Agent
    
    Represents AI reasoning result with rich context about verification strategy
    """
    verdict: str  # GO | ESCALATE | NO_GO
    reasoning: str  # Detailed explanation incorporating control context
    confidence_score: float  # Derived from pipeline metadata
    
    # Verification execution status
    automated_checks_available: int  # Count of machine-verifiable checks
    manual_checks_required: int  # Count of manual verification checks
    total_checks: int  # Total checks in plan
    
    # Execution recommendation
    execute_automated: bool  # Should automated verification proceed?
    requires_manual_review: bool  # Does this need human oversight?
    recommended_action: str  # Next step guidance
    
    # Context information
    control_objective: Optional[str] = None  # What this control protects
    regulatory_intent: Optional[str] = None  # Why regulator requires this
    automation_feasibility: Optional[str] = None  # Automation assessment
    
    # Internal diagnostics (for logging/debugging)
    gates_evaluated: Dict[str, str] = field(default_factory=dict)


class VerificationAgentService:
    """
    Verification Agent Service - Phase 1 Refined Implementation
    
    Responsibilities:
    - Observe: Load MAP, plans, controls, reasoned controls
    - Understand: Analyze control objectives, machine verifiability, confidence
    - Decide: Produce intelligent verification strategy recommendation
    - Explain: Provide audit-trail-ready reasoning using repository knowledge
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.verification_plans_dir = project_root / "datasets" / "verification_plans"
        self.reasoned_controls_dir = project_root / "datasets" / "reasoned_controls"
        self.interpreted_controls_dir = project_root / "datasets" / "interpreted_controls"
    
    def decide_verification_strategy(
        self,
        document_id: str,
        requirement_id: Optional[str] = None,
        criticality: Optional[str] = None,
        department: Optional[str] = None
    ) -> AgentDecision:
        """
        Core agent reasoning: Analyze verification context and recommend strategy.
        
        Args:
            document_id: Source document ID (e.g., "MD10190")
            requirement_id: Specific requirement ID if known
            criticality: MAP criticality level (CRITICAL, HIGH, MEDIUM, LOW)
            department: Assigned department
            
        Returns:
            AgentDecision with verdict, reasoning, and execution recommendations
        """
        gates = {}
        
        # ─── Gate 1: Load Verification Plan ───
        verification_plan = self._load_verification_plan(document_id)
        if not verification_plan:
            return AgentDecision(
                verdict="NO_GO",
                reasoning=f"Verification plan not found for document {document_id}. Cannot proceed without plan.",
                confidence_score=0.0,
                automated_checks_available=0,
                manual_checks_required=0,
                total_checks=0,
                execute_automated=False,
                requires_manual_review=False,
                recommended_action="Contact compliance administrator to regenerate verification plan",
                gates_evaluated={"plan_exists": "FAIL"}
            )
        gates["plan_exists"] = "PASS"
        
        # ─── Gate 2: Load Reasoned Control ───
        reasoned_control = self._load_reasoned_control(document_id, requirement_id)
        if not reasoned_control:
            logger.warning(f"No reasoned control found for {document_id}/{requirement_id}")
            gates["reasoned_control_exists"] = "WARN"
        else:
            gates["reasoned_control_exists"] = "PASS"
        
        # ─── Gate 3: Load Interpreted Control ───
        interpreted_control = self._load_interpreted_control(document_id, requirement_id)
        if not interpreted_control:
            logger.warning(f"No interpreted control found for {document_id}/{requirement_id}")
            gates["interpreted_control_exists"] = "WARN"
        else:
            gates["interpreted_control_exists"] = "PASS"
        
        # ─── Extract Context for Rich Reasoning ───
        control_objective = None
        regulatory_intent = None
        automation_feasibility = None
        control_name = "Unknown Control"
        
        if interpreted_control:
            control_objective = interpreted_control.get("control_objective")
            control_name = interpreted_control.get("control_name", "Unknown Control")
            automation_feasibility = interpreted_control.get("automation_feasibility")
        
        if reasoned_control:
            reg_intent = reasoned_control.get("regulatory_intent", {})
            regulatory_intent = reg_intent.get("primary_objective")
        
        # ─── Analyze Verification Plan ───
        plan_checks = verification_plan.get("verification_plans", [])
        if not plan_checks:
            return AgentDecision(
                verdict="NO_GO",
                reasoning=f"Verification plan for {control_name} contains no checks. Plan may be corrupted.",
                confidence_score=0.0,
                automated_checks_available=0,
                manual_checks_required=0,
                total_checks=0,
                execute_automated=False,
                requires_manual_review=False,
                recommended_action="Regenerate verification plan through pipeline",
                control_objective=control_objective,
                regulatory_intent=regulatory_intent,
                gates_evaluated={**gates, "has_checks": "FAIL"}
            )
        gates["has_checks"] = "PASS"
        
        # Find the relevant plan for this requirement
        relevant_plan = None
        for plan in plan_checks:
            if requirement_id and plan.get("requirement_id") == requirement_id:
                relevant_plan = plan
                break
        
        if not relevant_plan and len(plan_checks) > 0:
            relevant_plan = plan_checks[0]
        
        if not relevant_plan:
            return AgentDecision(
                verdict="NO_GO",
                reasoning=f"Cannot locate verification plan for requirement {requirement_id}",
                confidence_score=0.0,
                automated_checks_available=0,
                manual_checks_required=0,
                total_checks=0,
                execute_automated=False,
                requires_manual_review=False,
                recommended_action="Verify requirement ID and regenerate plan if needed",
                gates_evaluated={**gates, "plan_found": "FAIL"}
            )
        
        # ─── Analyze Checks ───
        checks = relevant_plan.get("checks", [])
        total_checks = len(checks)
        machine_verifiable_checks = sum(1 for c in checks if c.get("machine_verifiable", False))
        manual_checks = total_checks - machine_verifiable_checks
        
        gates["checks_analyzed"] = "PASS"
        
        # ─── Derive Confidence from Pipeline Metadata ───
        # Use existing pipeline confidence rather than arbitrary thresholds
        confidence_score = self._derive_confidence(
            reasoned_control=reasoned_control,
            relevant_plan=relevant_plan,
            criticality=criticality
        )
        
        # ─── Determine Verdict Based on Check Mix ───
        if machine_verifiable_checks > 0 and manual_checks == 0:
            # Fully automated - GO
            verdict = "GO"
            execute_automated = True
            requires_manual_review = False
            reasoning = self._build_reasoning_go(
                control_name=control_name,
                control_objective=control_objective,
                regulatory_intent=regulatory_intent,
                automation_feasibility=automation_feasibility,
                machine_verifiable_checks=machine_verifiable_checks,
                total_checks=total_checks,
                confidence_score=confidence_score,
                criticality=criticality
            )
            recommended_action = "Proceed with automated verification execution"
            
        elif machine_verifiable_checks > 0 and manual_checks > 0:
            # Mixed automation - ESCALATE but continue automated portion
            verdict = "ESCALATE"
            execute_automated = True  # KEY CHANGE: Execute automated portion
            requires_manual_review = True
            reasoning = self._build_reasoning_escalate_mixed(
                control_name=control_name,
                control_objective=control_objective,
                regulatory_intent=regulatory_intent,
                machine_verifiable_checks=machine_verifiable_checks,
                manual_checks=manual_checks,
                total_checks=total_checks,
                confidence_score=confidence_score
            )
            recommended_action = f"Execute {machine_verifiable_checks} automated checks, then route {manual_checks} manual checks to compliance officer"
            
        else:
            # No automated checks - ESCALATE for full manual review
            verdict = "ESCALATE"
            execute_automated = False  # Nothing to automate
            requires_manual_review = True
            reasoning = self._build_reasoning_escalate_manual(
                control_name=control_name,
                control_objective=control_objective,
                regulatory_intent=regulatory_intent,
                automation_feasibility=automation_feasibility,
                total_checks=total_checks,
                confidence_score=confidence_score
            )
            recommended_action = f"Route all {total_checks} checks to compliance officer for manual verification"
        
        return AgentDecision(
            verdict=verdict,
            reasoning=reasoning,
            confidence_score=confidence_score,
            automated_checks_available=machine_verifiable_checks,
            manual_checks_required=manual_checks,
            total_checks=total_checks,
            execute_automated=execute_automated,
            requires_manual_review=requires_manual_review,
            recommended_action=recommended_action,
            control_objective=control_objective,
            regulatory_intent=regulatory_intent,
            automation_feasibility=automation_feasibility,
            gates_evaluated=gates
        )
    
    def _derive_confidence(
        self,
        reasoned_control: Optional[Dict[str, Any]],
        relevant_plan: Dict[str, Any],
        criticality: Optional[str]
    ) -> float:
        """
        Derive confidence from existing pipeline metadata rather than arbitrary thresholds.
        
        Uses:
        - Reasoned control overall_confidence (primary)
        - Plan confidence (secondary)
        - Automation percentage (tertiary)
        - Criticality adjustment (if needed)
        """
        confidence = 0.5  # Default fallback
        
        # Primary: Use reasoned control confidence (already calculated by reasoning engine)
        if reasoned_control:
            confidence_metrics = reasoned_control.get("confidence_metrics", {})
            overall_confidence = confidence_metrics.get("overall_confidence")
            if overall_confidence is not None:
                confidence = overall_confidence
        
        # Secondary: Use plan confidence if reasoned control not available
        if confidence == 0.5 and relevant_plan:
            plan_confidence = relevant_plan.get("confidence")
            if plan_confidence is not None:
                confidence = plan_confidence
        
        # Tertiary: Consider automation percentage as confidence indicator
        if relevant_plan:
            automation_pct = relevant_plan.get("automation_percentage", 0)
            # High automation suggests higher execution confidence
            if automation_pct > 80:
                confidence = max(confidence, 0.75)
            elif automation_pct > 50:
                confidence = max(confidence, 0.65)
        
        return confidence
    
    def _build_reasoning_go(
        self,
        control_name: str,
        control_objective: Optional[str],
        regulatory_intent: Optional[str],
        automation_feasibility: Optional[str],
        machine_verifiable_checks: int,
        total_checks: int,
        confidence_score: float,
        criticality: Optional[str]
    ) -> str:
        """Build rich reasoning for GO verdict incorporating repository knowledge"""
        parts = []
        
        # What we're verifying
        parts.append(f"Verifying '{control_name}'")
        
        # Why it matters (regulatory intent)
        if regulatory_intent:
            parts.append(f"which addresses {regulatory_intent.lower()}")
        elif control_objective:
            # Fallback to control objective if regulatory intent not available
            obj_summary = control_objective[:80] + "..." if len(control_objective) > 80 else control_objective
            parts.append(f"which ensures {obj_summary.lower()}")
        
        # Automation capability
        parts.append(f"All {total_checks} checks are machine-verifiable")
        
        if automation_feasibility and automation_feasibility != "Low":
            parts.append(f"Control automation feasibility assessed as {automation_feasibility}")
        
        # Confidence context
        if confidence_score >= 0.8:
            parts.append(f"Pipeline confidence is high ({confidence_score:.2f})")
        elif confidence_score >= 0.6:
            parts.append(f"Pipeline confidence is moderate ({confidence_score:.2f})")
        
        # Criticality context
        if criticality in ["CRITICAL", "HIGH"]:
            parts.append(f"Control criticality: {criticality}")
        
        parts.append("Proceeding with fully automated verification")
        
        return ". ".join(parts) + "."
    
    def _build_reasoning_escalate_mixed(
        self,
        control_name: str,
        control_objective: Optional[str],
        regulatory_intent: Optional[str],
        machine_verifiable_checks: int,
        manual_checks: int,
        total_checks: int,
        confidence_score: float
    ) -> str:
        """Build rich reasoning for ESCALATE verdict with mixed automation"""
        parts = []
        
        # What we're verifying
        parts.append(f"Verifying '{control_name}'")
        
        # Why it matters
        if regulatory_intent:
            parts.append(f"addressing {regulatory_intent.lower()}")
        elif control_objective:
            obj_summary = control_objective[:60] + "..." if len(control_objective) > 60 else control_objective
            parts.append(f"ensuring {obj_summary.lower()}")
        
        # Check mix analysis
        parts.append(f"Plan contains {total_checks} checks: {machine_verifiable_checks} automated, {manual_checks} manual")
        
        # Strategy
        parts.append(f"Executing automated portion ({machine_verifiable_checks} checks) while flagging {manual_checks} checks for compliance officer review")
        
        # Confidence context
        if confidence_score >= 0.7:
            parts.append(f"Automated checks have {int(confidence_score * 100)}% confidence")
        
        parts.append("Partial automation with manual oversight")
        
        return ". ".join(parts) + "."
    
    def _build_reasoning_escalate_manual(
        self,
        control_name: str,
        control_objective: Optional[str],
        regulatory_intent: Optional[str],
        automation_feasibility: Optional[str],
        total_checks: int,
        confidence_score: float
    ) -> str:
        """Build rich reasoning for ESCALATE verdict requiring full manual review"""
        parts = []
        
        # What we're verifying
        parts.append(f"Verifying '{control_name}'")
        
        # Why it matters
        if regulatory_intent:
            parts.append(f"which addresses {regulatory_intent.lower()}")
        elif control_objective:
            obj_summary = control_objective[:60] + "..." if len(control_objective) > 60 else control_objective
            parts.append(f"which ensures {obj_summary.lower()}")
        
        # Why manual is needed
        parts.append(f"All {total_checks} checks require manual verification")
        
        if automation_feasibility == "Low":
            parts.append("Control type requires human judgment and process adherence")
        else:
            parts.append("No machine-verifiable checks available in current plan")
        
        # Confidence note
        if confidence_score < 0.6:
            parts.append(f"Low automation confidence ({confidence_score:.2f}) indicates manual review is appropriate")
        
        parts.append("Routing to compliance officer for manual verification")
        
        return ". ".join(parts) + "."
    
    def _load_verification_plan(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Load verification plan JSON for document"""
        plan_file = self.verification_plans_dir / f"{document_id}.json"
        if not plan_file.exists():
            logger.warning(f"Verification plan not found: {plan_file}")
            return None
        
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load verification plan {plan_file}: {e}")
            return None
    
    def _load_reasoned_control(self, document_id: str, requirement_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Load reasoned control for specific requirement"""
        reasoned_file = self.reasoned_controls_dir / f"{document_id}.json"
        if not reasoned_file.exists():
            return None
        
        try:
            with open(reasoned_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                controls = data.get("reasoned_controls", [])
                
                if requirement_id:
                    for control in controls:
                        if control.get("requirement_id") == requirement_id:
                            return control
                
                # Return first control if requirement_id not specified or not found
                return controls[0] if controls else None
                
        except Exception as e:
            logger.error(f"Failed to load reasoned control {reasoned_file}: {e}")
            return None
    
    def _load_interpreted_control(self, document_id: str, requirement_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Load interpreted control for specific requirement"""
        interpreted_file = self.interpreted_controls_dir / f"{document_id}.json"
        if not interpreted_file.exists():
            return None
        
        try:
            with open(interpreted_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                controls = data.get("interpreted_controls", [])
                
                if requirement_id:
                    for control in controls:
                        if control.get("requirement_id") == requirement_id:
                            return control
                
                # Return first control if requirement_id not specified or not found
                return controls[0] if controls else None
                
        except Exception as e:
            logger.error(f"Failed to load interpreted control {interpreted_file}: {e}")
            return None
