import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Lightweight retrieval component for RegulAI1 Mitra.

    Retrieval strategy:
      Stage 1 (Verified Context):
        1. Compliance Decisions  – final verdicts and rationale.
        2. Verification Results  – per-plan status and compressed check evidence.
        
      Stage 2 (Pre-verification Fallback):
        If Stage 1 is empty (e.g., newly uploaded document), use:
        1. Verification Plans    – controls and checks to be performed.
        2. Requirements          – raw regulatory obligations.

    Excluded entirely:
      Maps, Logical Units, Parsed document, Implementation Tasks.

    Aggressive summarization keeps context under ~3000 characters to
    cut LLM prefill time on CPU from several minutes to a few seconds.
    """

    # Maximum characters in the final context string.
    # Set conservatively so CPU models finish in a reasonable time.
    MAX_CONTEXT_CHARS = 3000

    # Raw evidence lines longer than this are truncated.
    EVIDENCE_TRUNCATE = 100

    def __init__(
        self,
        project_root: Path,
        max_context_chars: int = MAX_CONTEXT_CHARS,
    ):
        self.project_root = Path(project_root)
        self.datasets_dir = self.project_root / "datasets"
        self.max_context_chars = max_context_chars

    # ============================================================
    # PUBLIC API  (signature unchanged)
    # ============================================================

    def build_context(
        self,
        document_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a compact context string for a document.

        Returns
        -------
        context : str
            Natural language context to send to Ollama.
        metadata : dict
            Keys: document_id, sources_used, files_processed,
                  characters, max_context_characters.
        """
        logger.info("Building context for %s", document_id)

        # Stage 1: Try Verified Context
        context, metadata = self._build_verified_context(document_id)
        
        # Stage 2: Fallback to Pre-verification Context if empty
        if not context.strip():
            logger.info("No verified artifacts found for %s. Falling back to pre-verification context.", document_id)
            context, metadata = self._build_pre_verification_context(document_id)
            
        return context, metadata

    def _build_verified_context(self, document_id: str) -> Tuple[str, Dict[str, Any]]:
        return self._build_context_from_sources(
            document_id,
            [
                ("compliance_decisions", self._format_compliance_decisions),
                ("verification_results", self._format_verification_results),
            ]
        )

    def _build_pre_verification_context(self, document_id: str) -> Tuple[str, Dict[str, Any]]:
        return self._build_context_from_sources(
            document_id,
            [
                ("verification_plans", self._format_verification_plans),
                ("requirements", self._format_requirements),
            ]
        )

    def _build_context_from_sources(
        self, document_id: str, sources_config: List[Tuple[str, Callable]]
    ) -> Tuple[str, Dict[str, Any]]:
        sections: List[str] = []
        sources_used: List[str] = []
        files_processed = 0

        for source_name, formatter in sources_config:
            artifact = self._find_artifact(source_name, document_id)

            if artifact is None:
                logger.debug("No artifact found in %s", source_name)
                continue

            data = self._load_json(artifact)

            if data is None:
                continue

            try:
                text = formatter(data)
            except Exception as exc:
                logger.warning("Formatter failed for %s: %s", source_name, exc)
                continue

            if not text.strip():
                continue

            section = f"--- {source_name.upper()} ---\n{text.strip()}\n"

            # Hard-stop if budget is full.
            remaining = self.max_context_chars - sum(len(s) for s in sections)
            if remaining <= 0:
                break

            if len(section) > remaining:
                section = section[:remaining]

            sections.append(section)
            sources_used.append(source_name)
            files_processed += 1

        context = "\n".join(sections).strip()

        metadata = {
            "document_id": document_id,
            "sources_used": sources_used,
            "files_processed": files_processed,
            "characters": len(context),
            "max_context_characters": self.max_context_chars,
        }

        logger.info(
            "Context built from sources=%s characters=%d",
            sources_used,
            len(context),
        )

        return context, metadata

    # ============================================================
    # FILE DISCOVERY
    # ============================================================

    def _find_artifact(
        self,
        source_name: str,
        document_id: str,
    ) -> Optional[Path]:
        """
        Return the most recent artifact file for document_id in source_name.
        Files are named <document_id>_<timestamp>.json or <document_id>.json.
        """

        directory = self.datasets_dir / source_name

        if not directory.exists():
            return None

        # Prefer exact-prefix matches (sorted newest-first by name).
        matches = sorted(
            directory.glob(f"{document_id}*.json"),
            reverse=True,
        )

        if matches:
            return matches[0]

        # Fallback: scan for files that contain the document_id string.
        for path in directory.glob("*.json"):
            try:
                if document_id in path.read_text(encoding="utf-8"):
                    return path
            except Exception:
                continue

        return None

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Unable to read %s: %s", path, exc)
            return None

    # ============================================================
    # FORMATTERS
    # ============================================================

    def _format_compliance_decisions(self, data: Dict[str, Any]) -> str:
        """
        Emit one line per plan verdict plus its rationale.

        Example output:
            Document: MD10191 | Verdict: NON_COMPLIANT | 33.33% compliant
            Plan CVP_VR_MD10191_req55 [Foreign Exchange Compliance Control]: NON_COMPLIANT
            Rationale: One or more blocker or mandatory checks failed execution.
            Failed blockers: CVP_VR_MD10191_req55_C02
        """

        lines: List[str] = []

        doc_id = data.get("document_id", "")
        overall = data.get("overall_document_verdict", "Unknown")
        pct = data.get("compliance_percentage", "")

        summary = f"Document: {doc_id} | Verdict: {overall}"
        if pct != "":
            summary += f" | {pct}% compliant"
        lines.append(summary)

        for verdict in data.get("plan_verdicts", []):
            plan_id = verdict.get("plan_id", "Unknown")
            v = verdict.get("verdict", "Unknown")
            control = verdict.get("control_name", "")
            rationale = verdict.get("rationale", "")

            label = f"Plan {plan_id}"
            if control:
                label += f" [{control}]"
            lines.append(f"{label}: {v}")

            if rationale:
                lines.append(f"Rationale: {rationale}")

        blockers: List[str] = data.get("failed_blocker_list", [])
        if blockers:
            lines.append(f"Failed blockers: {', '.join(blockers)}")

        return "\n".join(lines)

    def _format_verification_plans(self, data: Dict[str, Any]) -> str:
        """
        Emit a high-level summary of verification plans.
        Example output:
            Control: Foreign Exchange Compliance Control
            Checks:
            • Verify existence of implementation evidence
            • Assess Adequacy of Evidence Against Control Objective
        """
        lines: List[str] = []
        
        for plan in data.get("verification_plans", []):
            control = plan.get("control_name", "")
            if control:
                lines.append(f"Control: {control}")
            else:
                lines.append(f"Plan: {plan.get('plan_id', 'Unknown')}")
            
            checks = plan.get("checks", [])
            if checks:
                lines.append("Checks:")
                for c in checks:
                    title = c.get("title", "")
                    if title:
                        lines.append(f"• {title}")
            
            lines.append("")  # blank line separator
            
        return "\n".join(lines).strip()

    def _format_requirements(self, data: Dict[str, Any]) -> str:
        """
        Emit the raw text of regulatory requirements.
        Example output:
            Requirement UP20260717_0001_req3: These Directions shall be called...
        """
        lines: List[str] = []
        
        for req in data.get("requirements", []):
            req_id = req.get("requirement_id", "Unknown")
            sentence = req.get("full_sentence", "").replace("\n", " ")
            if sentence:
                lines.append(f"Requirement {req_id}: {sentence}")
                
        return "\n".join(lines).strip()
    def _format_verification_results(self, data: Dict[str, Any]) -> str:
        """
        Emit overall status then one compressed block per plan.

        Evidence lines are truncated to EVIDENCE_TRUNCATE characters to
        avoid flooding the context with raw registry dumps or command output.

        Example output:
            Overall: NON_COMPLIANT | Plans: 1 | Checks: 3 (1P 1F 1E)
            Plan CVP_VR_MD10191_req55 [Foreign Exchange]: NON_COMPLIANT 1/3 passed
              Check 1: PASS
              Check 2: FAIL | EnableLUA    REG_DWORD    0x1
              Check 3: ERROR
        """

        lines: List[str] = []

        overall = data.get("overall_document_status", "Unknown")
        total_plans = data.get("total_plans", "")
        passed = data.get("total_checks_passed", "")
        failed = data.get("total_checks_failed", "")
        errored = data.get("total_checks_errored", "")
        total_checks = data.get("total_checks_run", "")

        summary = f"Overall: {overall}"
        if total_plans != "":
            summary += f" | Plans: {total_plans}"
        if total_checks != "":
            summary += f" | Checks: {total_checks} ({passed}P {failed}F {errored}E)"
        lines.append(summary)

        for result in data.get("verification_results", []):
            plan_id = result.get("plan_id", "Unknown")
            status = result.get("overall_status", "Unknown")
            control = result.get("control_name", "")
            checks_passed = result.get("checks_passed", 0)
            checks_run = result.get("checks_run", 0)

            label = f"Plan {plan_id}"
            if control:
                label += f" [{control}]"
            lines.append(
                f"{label}: {status} {checks_passed}/{checks_run} passed"
            )

            for check in result.get("evidence", []):
                seq = check.get("sequence_number", "?")
                verdict = check.get("verdict", "Unknown")

                raw = (
                    check.get("raw_output", "")
                    .replace("\n", " ")
                    .replace("\r", "")
                    .strip()
                )

                line = f"  Check {seq}: {verdict}"

                if raw:
                    # Truncate long registry dumps / command output.
                    if len(raw) > self.EVIDENCE_TRUNCATE:
                        raw = raw[: self.EVIDENCE_TRUNCATE] + "..."
                    line += f" | {raw}"

                lines.append(line)

        return "\n".join(lines)