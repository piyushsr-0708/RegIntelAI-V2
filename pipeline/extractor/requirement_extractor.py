"""
Requirement Extraction Engine V1 — RegIntel AI (SuRaksha-v2)

Deterministic, rule-based extraction of structured regulatory requirements
from logical unit JSONs produced by the Logical Unit Builder pipeline.

Architecture is LLM-ready: the RuleEngine and Validator are independent
of the orchestrator. Future integration only needs to replace or augment
the RuleEngine with an LLM-backed engine implementing the same interface.

Supported requirement types:
    OBLIGATION    PROHIBITION    PERMISSION    REPORTING
    DEFINITION    EXCEPTION      RECOMMENDATION
"""

import hashlib
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Rule-set constants
# ---------------------------------------------------------------------------

# ── Modality trigger word groups ──────────────────────────────────────────
# Each group maps to a (requirement_type, modality) pair.
# Rules are evaluated in order; first match wins.

_TRIGGER_RULES: List[Tuple[re.Pattern, str, str]] = [
    # PROHIBITION
    (re.compile(r"\b(shall not|must not|is not permitted|are not permitted|"
                r"not allowed|prohibited|no .{1,30} shall)\b", re.I),
     "PROHIBITION", "shall not"),

    # OBLIGATION – strong
    (re.compile(r"\b(shall|must|is required to|are required to|"
                r"is mandated|are mandated|it is mandatory|"
                r"has to|have to)\b", re.I),
     "OBLIGATION", "shall"),

    # REPORTING
    (re.compile(r"\b(shall submit|must submit|shall report|must report|"
                r"shall furnish|must furnish|shall file|must file|"
                r"shall disclose|must disclose|shall notify|must notify|"
                r"shall intimate|must intimate)\b", re.I),
     "REPORTING", "shall submit"),

    # EXCEPTION
    (re.compile(r"\b(provided that|except where|except in cases|"
                r"subject to|notwithstanding|unless|except as|"
                r"save as)\b", re.I),
     "EXCEPTION", "provided that"),

    # PERMISSION
    (re.compile(r"\b(may|is permitted|are permitted|is allowed|are allowed|"
                r"has the option|have the option)\b", re.I),
     "PERMISSION", "may"),

    # RECOMMENDATION
    (re.compile(r"\b(should|it is recommended|is advisable|are advised|"
                r"it is suggested|may consider)\b", re.I),
     "RECOMMENDATION", "should"),

    # DEFINITION
    (re.compile(r"\b(means|is defined as|shall mean|shall include|"
                r"for the purpose of this|for purposes of)\b", re.I),
     "DEFINITION", "means"),
]

# ── Known actor patterns for RBI regulatory context ───────────────────────
_ACTOR_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(banks?|banking companies|banking company)\b", re.I),
    re.compile(r"\b(NBFCs?|non-banking financial companies?)\b", re.I),
    re.compile(r"\b(regulated entit(?:y|ies))\b", re.I),
    re.compile(r"\b(authorised dealers?|AD Category[- ]I|AD banks?)\b", re.I),
    re.compile(r"\b(payment (system )?operators?|PSOs?)\b", re.I),
    re.compile(r"\b(credit information companies?|CICs?)\b", re.I),
    re.compile(r"\b(asset reconstruction companies?|ARCs?)\b", re.I),
    re.compile(r"\b(primary (urban )?co-operative banks?|UCBs?)\b", re.I),
    re.compile(r"\b(all entities|every entity|each entity)\b", re.I),
    re.compile(r"\b(the (entity|institution|company|person|applicant))\b", re.I),
    re.compile(r"\b(Reserve Bank|RBI)\b", re.I),
    re.compile(r"\b(small finance banks?)\b", re.I),
    re.compile(r"\b(payment banks?)\b", re.I),
    re.compile(r"\b(regional rural banks?|RRBs?)\b", re.I),
    re.compile(r"\b(foreign banks?)\b", re.I),
]

# ── Timeline / deadline indicators ───────────────────────────────────────
_TIMELINE_RE = re.compile(
    r"\b(\d+\s*(days?|months?|years?|weeks?|hours?|quarters?))\b"
    r"|\b(by [A-Z][a-z]+ \d{1,2},?\s*\d{4})\b"
    r"|\b(within \d[\w\s]*)\b"
    r"|\b(on or before [A-Z][a-z]+ \d{1,2},?\s*\d{4})\b"
    r"|\b(annually|quarterly|monthly|weekly|daily|immediately)\b",
    re.I,
)

# ── Condition / exception clause extractors ───────────────────────────────
_CONDITION_RE = re.compile(
    r"(if .{5,120}?[,;]|where .{5,120}?[,;]|in case .{5,120}?[,;]|"
    r"when .{5,120}?[,;]|provided that .{5,80}?[,;.])",
    re.I | re.DOTALL,
)

# Minimum text length to attempt requirement extraction
MIN_TEXT_LENGTH = 30


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Requirement:
    requirement_id: str
    document_id: str
    logical_unit_id: str
    requirement_type: str      # OBLIGATION | PROHIBITION | PERMISSION | …
    modality: str              # The trigger phrase detected
    actor: str                 # Who must comply
    action: str                # What must be done
    object_: str               # What the action applies to
    conditions: List[str]
    exceptions: List[str]
    timeline: str
    full_sentence: str         # Original sentence as evidence
    page_numbers: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]
    confidence: float          # 0.0 – 1.0
    validation_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["object"] = d.pop("object_")
        return d


# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(
    r"(?<!\b[A-Z][a-z]\b)"   # negative look-behind: abbreviation
    r"(?<!\b[A-Z]{2}\b)"     # negative look-behind: acronym
    r"(?<=[.!?;])\s+",
    re.UNICODE,
)


def split_sentences(text: str) -> List[str]:
    """Splits text into sentences, keeping them reasonably short."""
    raw = _SENT_RE.split(text)
    out: List[str] = []
    for s in raw:
        s = s.strip()
        if s:
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class RuleEngine:
    """
    Deterministic rule-based requirement detector.

    For each sentence:
    1. Detect the trigger word → requirement type + modality.
    2. Extract actor using pattern matching.
    3. Extract the action phrase (verb + object after the trigger word).
    4. Extract conditions and timelines with regex.
    5. Compute a confidence score from completeness.

    Designed as a replaceable component: future LLM engines should expose
    the same ``extract(sentence, provenance)`` interface.
    """

    def extract(
        self,
        sentence: str,
        logical_unit_id: str,
        document_id: str,
        page_numbers: List[int],
        hierarchy_node_ids: List[str],
        block_ids: List[str],
        seq: int,
    ) -> Optional[Requirement]:
        """
        Attempt to extract a single Requirement from one sentence.
        Returns None if no trigger word is found.
        """
        # 1. Trigger detection
        req_type, modality = self._detect_trigger(sentence)
        if req_type is None:
            return None

        # 2. Actor extraction
        actor = self._extract_actor(sentence)

        # 3. Action + object extraction
        action, object_ = self._extract_action_object(sentence, modality)

        # 4. Conditions
        conditions = self._extract_conditions(sentence)

        # 5. Timeline
        timeline = self._extract_timeline(sentence)

        # 6. Confidence
        confidence = self._compute_confidence(actor, action, object_, conditions)

        req_id = f"{document_id}_req{seq}"

        return Requirement(
            requirement_id=req_id,
            document_id=document_id,
            logical_unit_id=logical_unit_id,
            requirement_type=req_type,
            modality=modality,
            actor=actor,
            action=action,
            object_=object_,
            conditions=conditions,
            exceptions=[],
            timeline=timeline,
            full_sentence=sentence.strip(),
            page_numbers=page_numbers,
            hierarchy_node_ids=hierarchy_node_ids,
            block_ids=block_ids,
            confidence=confidence,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _detect_trigger(self, sentence: str) -> Tuple[Optional[str], str]:
        for pattern, req_type, modality in _TRIGGER_RULES:
            if pattern.search(sentence):
                return req_type, modality
        return None, ""

    def _extract_actor(self, sentence: str) -> str:
        for pattern in _ACTOR_PATTERNS:
            m = pattern.search(sentence)
            if m:
                return m.group(0).strip()
        return ""

    def _extract_action_object(self, sentence: str, modality: str) -> Tuple[str, str]:
        """
        Extracts the action verb phrase and the object phrase that follow the
        trigger word.
        Uses a simple heuristic: take the clause after the trigger word,
        split at the first comma / 'to' / 'that', and return verb + rest.
        """
        # Locate the trigger in the sentence
        trigger_search = re.search(re.escape(modality), sentence, re.I)
        if not trigger_search:
            # Fall back to generic modal search
            trigger_search = re.search(
                r"\b(shall|must|may|should|prohibited|required)\b", sentence, re.I
            )

        if not trigger_search:
            return "", ""

        after = sentence[trigger_search.end():].strip()
        # Remove leading "not" for prohibitions (already captured in req_type)
        after = re.sub(r"^not\s+", "", after, flags=re.I)

        # Clip at the first subordinating comma
        clip_match = re.search(r",\s*(if|where|when|provided|subject|unless|except)", after, re.I)
        if clip_match:
            core = after[:clip_match.start()].strip()
        else:
            # Clip at sentence-terminal punctuation or 150 chars
            core = after[:150].split(".")[0].split(";")[0].strip()

        # Split action (first verb phrase ~5 words) from object (rest)
        words = core.split()
        if len(words) >= 2:
            action = " ".join(words[:min(4, len(words))])
            object_ = " ".join(words[min(4, len(words)):]).strip()
        else:
            action = core
            object_ = ""

        return action, object_

    def _extract_conditions(self, sentence: str) -> List[str]:
        matches = _CONDITION_RE.findall(sentence)
        out: List[str] = []
        for m in matches:
            cond = m.strip().rstrip(",;.")
            if cond and len(cond) > 8:
                out.append(cond)
        return out

    def _extract_timeline(self, sentence: str) -> str:
        m = _TIMELINE_RE.search(sentence)
        if m:
            return m.group(0).strip()
        return ""

    def _compute_confidence(
        self,
        actor: str,
        action: str,
        object_: str,
        conditions: List[str],
    ) -> float:
        score = 0.4  # base: trigger word matched
        if actor:
            score += 0.25
        if action:
            score += 0.20
        if object_:
            score += 0.10
        if conditions:
            score += 0.05
        return round(min(score, 1.0), 2)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RequirementValidator:
    """
    Post-extraction validator.

    Rejects duplicates, empty requirements, and requirements without an
    action. Adds validation warnings to requirements that lack an actor
    when one cannot be inferred.
    """

    def __init__(self) -> None:
        self._seen_hashes: set = set()
        self.rejected = 0

    def validate(self, req: Requirement) -> bool:
        """
        Returns True if the requirement passes validation.
        Mutates req.validation_warnings for soft failures.
        """
        # Reject if full_sentence is empty or too short
        if not req.full_sentence or len(req.full_sentence) < MIN_TEXT_LENGTH:
            self.rejected += 1
            return False

        # Reject if action is completely empty
        if not req.action:
            self.rejected += 1
            return False

        # Soft warning: no actor
        if not req.actor:
            req.validation_warnings.append("NO_ACTOR_DETECTED")

        # Reject duplicate sentences (same document, same sentence text)
        fingerprint = hashlib.md5(
            f"{req.document_id}|{req.full_sentence}".encode()
        ).hexdigest()
        if fingerprint in self._seen_hashes:
            self.rejected += 1
            return False
        self._seen_hashes.add(fingerprint)

        return True


# ---------------------------------------------------------------------------
# Document processor
# ---------------------------------------------------------------------------

class RequirementExtractor:
    """
    Orchestrates the full extraction pipeline per document.
    """

    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        self._ensure_directories()
        self._setup_logging()

        self.engine = RuleEngine()

        self.stats: Dict[str, Any] = {
            "documents_processed": 0,
            "logical_units_processed": 0,
            "candidates_detected": 0,
            "requirements_extracted": 0,
            "requirements_rejected": 0,
            "type_counts": Counter(),
        }

    # ── Setup ─────────────────────────────────────────────────────────────

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        log_file = self.log_dir / "requirement_extractor.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger("").addHandler(console)
        self.logger = logging.getLogger(__name__)

    # ── Processing ────────────────────────────────────────────────────────

    def _process_logical_unit(
        self,
        lu: Dict[str, Any],
        validator: RequirementValidator,
        seq_counter: List[int],
    ) -> List[Requirement]:
        """Extracts all requirements from a single logical unit."""
        text = (lu.get("text") or "").strip()
        if not text or lu.get("node_type") in {"image"}:
            return []

        doc_id = lu["document_id"]
        lu_id = lu["logical_unit_id"]
        page_numbers = lu.get("page_range") or []
        node_ids = lu.get("hierarchy_node_ids") or []
        block_ids = lu.get("block_ids") or []

        sentences = split_sentences(text)
        results: List[Requirement] = []

        for sentence in sentences:
            if len(sentence.strip()) < MIN_TEXT_LENGTH:
                continue

            self.stats["candidates_detected"] += 1
            seq_counter[0] += 1

            try:
                req = self.engine.extract(
                    sentence,
                    logical_unit_id=lu_id,
                    document_id=doc_id,
                    page_numbers=page_numbers,
                    hierarchy_node_ids=node_ids,
                    block_ids=block_ids,
                    seq=seq_counter[0],
                )
            except Exception as e:
                self.logger.error(f"Engine error on LU {lu_id}: {e}")
                req = None

            if req is None:
                continue

            if validator.validate(req):
                results.append(req)
                self.stats["requirements_extracted"] += 1
                self.stats["type_counts"][req.requirement_type] += 1
            else:
                self.stats["requirements_rejected"] += validator.rejected - sum(
                    v.rejected for v in []
                )

        return results

    def process_document(self, json_path: Path) -> None:
        """Processes a single logical-units JSON and writes requirements JSON."""
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — requirements already extracted.")
            return

        self.logger.info(f"Extracting requirements from: {json_path.name}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        try:
            logical_units = doc.get("logical_units") or []
            validator = RequirementValidator()
            all_requirements: List[Requirement] = []
            seq_counter = [0]  # mutable shared counter

            for lu in logical_units:
                try:
                    reqs = self._process_logical_unit(lu, validator, seq_counter)
                    all_requirements.extend(reqs)
                    self.stats["logical_units_processed"] += 1
                except Exception as e:
                    self.logger.error(
                        f"Error processing LU {lu.get('logical_unit_id')}: {e}"
                    )

            self.stats["requirements_rejected"] += validator.rejected

            output = {
                "document_id": doc_id,
                "title": doc.get("title", doc_id),
                "document_status": doc.get("document_status", "ACTIVE"),
                "page_count": doc.get("page_count", 0),
                "requirement_count": len(all_requirements),
                "requirements": [r.to_dict() for r in all_requirements],
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            self.stats["documents_processed"] += 1

        except Exception as e:
            self.logger.error(f"Critical error for {doc_id}: {e}")

    # ── Runner ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Processes all logical unit JSONs in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} logical unit documents to process.")

        for json_path in tqdm(json_files, desc="Extracting requirements"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        """Prints verification summary."""
        docs = self.stats["documents_processed"]
        reqs = self.stats["requirements_extracted"]
        avg_reqs = reqs / docs if docs > 0 else 0.0

        type_lines = "\n".join(
            f"  {rtype:<18} {count}"
            for rtype, count in sorted(
                self.stats["type_counts"].items(), key=lambda x: -x[1]
            )
        )

        summary = (
            f"\n{'='*52}\n"
            f" REQUIREMENT EXTRACTOR VERIFICATION SUMMARY\n"
            f"{'='*52}\n"
            f"Documents processed:       {docs}\n"
            f"Logical units processed:   {self.stats['logical_units_processed']}\n"
            f"Requirement candidates:    {self.stats['candidates_detected']}\n"
            f"Requirements extracted:    {reqs}\n"
            f"Requirements rejected:     {self.stats['requirements_rejected']}\n"
            f"Average reqs/document:     {avg_reqs:.1f}\n"
            f"\nRequirement type breakdown:\n{type_lines if type_lines else '  (none)'}\n"
            f"\nOutput directory:          {self.output_dir}\n"
            f"{'='*52}\n"
        )
        print(summary)
        self.logger.info("Requirement extraction pipeline completed.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "logical_units"
    output_directory = project_root / "datasets" / "requirements"
    log_directory = project_root / "logs"

    extractor = RequirementExtractor(input_directory, output_directory, log_directory)
    extractor.run()
