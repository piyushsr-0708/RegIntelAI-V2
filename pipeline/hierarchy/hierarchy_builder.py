"""
Hierarchy Builder V1 — RegIntel AI (SuRaksha-v2)

Transforms a normalized document JSON (from the Normalizer pipeline) into a
logical document hierarchy: Parts → Chapters → Sections → Subsections →
Clauses → Subclauses → Schedules / Annexures / Appendices, Bullet Lists,
Tables, Notes, Definitions, and unknown leaf nodes.

Every hierarchy node preserves full traceability back to the original parser
blocks (block_ids, page_number, bbox).
"""

import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Minimum font-size ratio relative to the document body size for a block to be
# treated as a section heading when it has no recognisable numbering pattern.
HEADING_SIZE_RATIO: float = 1.10

# Numbering patterns — ordered from the most specific / deepest to the most
# general so that the first match wins.
# Each tuple: (regex, level, node_type_key)
#
# Levels (lower = higher in the hierarchy):
#   1  Part
#   2  Chapter
#   3  Section
#   4  Subsection
#   5  Clause
#   6  Subclause
#   7  Sub-subclause

_PATTERNS: List[Tuple[re.Pattern, int, str]] = [
    # "Part I", "PART II", "Part One"
    (re.compile(r"^part\s+([IVXLCDM]+|\d+|[A-Z][a-z]+)\b", re.I), 1, "part"),
    # "Chapter 1", "CHAPTER I"
    (re.compile(r"^chapter\s+([IVXLCDM]+|\d+)\b", re.I), 2, "chapter"),
    # "Schedule I", "Annexure A", "Appendix 1"
    (re.compile(r"^(schedule|annexure|annex|appendix)\s*([\w\-]*)\b", re.I), 3, "schedule"),
    # Top-level arabic: "1." or "1 " (not "1.2" — that's a subsection)
    (re.compile(r"^(\d+)\.\s+\S"), 3, "section"),
    # "1.1" / "1.1." second-level numeric
    (re.compile(r"^(\d+\.\d+)\.?\s+\S"), 4, "subsection"),
    # "1.1.1" third-level numeric
    (re.compile(r"^(\d+\.\d+\.\d+)\.?\s+\S"), 5, "clause"),
    # "1.1.1.1" fourth-level numeric
    (re.compile(r"^(\d+\.\d+\.\d+\.\d+)\.?\s+\S"), 6, "subclause"),
    # "(a)", "(b)" … alphabetic parenthetical
    (re.compile(r"^\([a-z]\)\s+\S", re.I), 5, "clause"),
    # "(i)", "(ii)" … roman-numeral parenthetical
    (re.compile(r"^\(([ivxlcdm]+)\)\s+\S", re.I), 6, "subclause"),
    # "(A)", "(B)" … uppercase alphabetic parenthetical
    (re.compile(r"^\([A-Z]\)\s+\S"), 6, "subclause"),
    # Roman numerals: "I.", "II.", "III."
    (re.compile(r"^([IVXLCDM]+)\.\s+\S"), 3, "section"),
    # Alphabetic: "A.", "B."
    (re.compile(r"^([A-Z])\.\s+\S"), 4, "subsection"),
]

_STRUCTURAL_KEYWORDS: Dict[str, str] = {
    "definition": "definition",
    "definitions": "definition",
    "note": "note",
    "notes": "note",
    "explanation": "explanation",
    "explanations": "explanation",
    "table": "table",
}

_BULLET_RE = re.compile(r"^[\u2022\u2023\u25aa\u25cf\u25e6\u2013\u2014\-\*]\s+")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class HierarchyNode:
    node_id: str
    parent_id: Optional[str]
    level: int
    node_type: str                # part | chapter | section | subsection |
                                  # clause | subclause | schedule | table |
                                  # bullet_list | note | explanation |
                                  # definition | unknown
    title: str
    text: str
    page_number: int
    block_ids: List[str]
    bbox: List[float]
    children: List["HierarchyNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["children"] = [c.to_dict() for c in self.children]
        return d


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _union_bbox(bboxes: List[List[float]]) -> List[float]:
    """Returns the bounding box that encloses all supplied bboxes."""
    if not bboxes:
        return [0.0, 0.0, 0.0, 0.0]
    x0 = min(b[0] for b in bboxes)
    y0 = min(b[1] for b in bboxes)
    x1 = max(b[2] for b in bboxes)
    y1 = max(b[3] for b in bboxes)
    return [x0, y0, x1, y1]


def _first_line(text: str) -> str:
    """Returns the first non-empty line of a text string."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


def _match_numbering(text: str) -> Tuple[Optional[int], str]:
    """
    Attempts to match the text against known numbering patterns.

    Returns:
        (level, node_type) if a match is found, else (None, "unknown").
    """
    first = _first_line(text)
    for pattern, level, node_type in _PATTERNS:
        if pattern.match(first):
            return level, node_type
    return None, "unknown"


def _classify_block(
    block: Dict[str, Any],
    body_font_size: float,
) -> Tuple[Optional[int], str]:
    """
    Classifies a text block into a hierarchy level and node type.

    Returns:
        (level, node_type) — level is None for leaf / continuation blocks.
    """
    text = block.get("text", "").strip()
    if not text or block.get("type") == "image":
        return None, "unknown"

    # Structural keyword match on the first line
    first = _first_line(text).lower()
    for keyword, node_type in _STRUCTURAL_KEYWORDS.items():
        if first.startswith(keyword):
            return 4, node_type  # treat structural keywords as subsection-level

    # Bullet list
    if _BULLET_RE.match(text):
        return None, "bullet_list"

    # Numeric / alpha / roman numbering
    level, node_type = _match_numbering(text)
    if level is not None:
        return level, node_type

    # Font-size heuristic for headings (only when no numbering is found)
    font = block.get("font_info") or {}
    size = font.get("size", 0.0)
    if size >= body_font_size * HEADING_SIZE_RATIO:
        return 3, "section"

    return None, "unknown"


def _estimate_body_font_size(pages: List[Dict[str, Any]]) -> float:
    """Estimates the body (modal) font size across the document."""
    size_chars: Dict[float, int] = {}
    for page in pages:
        for block in page.get("blocks") or []:
            font = block.get("font_info") or {}
            size = font.get("size")
            if size:
                text_len = len(block.get("text", ""))
                size_chars[size] = size_chars.get(size, 0) + text_len
    if not size_chars:
        return 11.0
    return max(size_chars, key=lambda s: size_chars[s])


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

class HierarchyBuilder:
    """
    Builds a logical document hierarchy from normalized parser output.
    """

    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        self._ensure_directories()
        self._setup_logging()

        self.stats: Dict[str, int] = {
            "documents_processed": 0,
            "nodes_created": 0,
            "unknown_nodes": 0,
            "max_depth": 0,
        }

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        log_file = self.log_dir / "hierarchy_builder.log"
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

    # ------------------------------------------------------------------
    # Node helpers
    # ------------------------------------------------------------------

    def _make_node(
        self,
        node_id: str,
        parent_id: Optional[str],
        level: int,
        node_type: str,
        block: Dict[str, Any],
        page_number: int,
    ) -> HierarchyNode:
        text = block.get("text", "").strip()
        return HierarchyNode(
            node_id=node_id,
            parent_id=parent_id,
            level=level,
            node_type=node_type,
            title=_first_line(text),
            text=text,
            page_number=page_number,
            block_ids=[block["block_id"]],
            bbox=list(block.get("bbox") or [0.0, 0.0, 0.0, 0.0]),
        )

    def _update_stats(self, nodes: List[HierarchyNode]) -> None:
        """Recursively updates global stats counters."""
        def _recurse(n: HierarchyNode, depth: int) -> None:
            self.stats["nodes_created"] += 1
            if n.node_type == "unknown":
                self.stats["unknown_nodes"] += 1
            if depth > self.stats["max_depth"]:
                self.stats["max_depth"] = depth
            for child in n.children:
                _recurse(child, depth + 1)

        for node in nodes:
            _recurse(node, 1)

    # ------------------------------------------------------------------
    # Hierarchy assembly
    # ------------------------------------------------------------------

    def _build_hierarchy(
        self,
        doc_id: str,
        pages: List[Dict[str, Any]],
        body_font_size: float,
    ) -> List[HierarchyNode]:
        """
        Converts a flat sequence of blocks into a hierarchy of nodes.

        Strategy:
        - Walk all blocks in reading order (page → block).
        - For each block, determine (level, node_type).
        - If the block opens a new structural level, create a new node and
          push it onto the ancestor stack.
        - If the block is a continuation (level is None), accumulate its text
          into the current open leaf node.
        - Ensures no level is skipped: a block at level 5 without a level-4
          ancestor gets attached to the nearest shallower ancestor.
        """
        root_nodes: List[HierarchyNode] = []
        # stack[i] = the currently open node at logical depth i+1
        ancestor_stack: List[HierarchyNode] = []
        seq = [0]  # mutable counter for node IDs

        def next_id() -> str:
            seq[0] += 1
            return f"{doc_id}_n{seq[0]}"

        def _parent_id_for_level(target_level: int) -> Optional[str]:
            """Returns the node_id of the closest ancestor shallower than target_level."""
            for node in reversed(ancestor_stack):
                if node.level < target_level:
                    return node.node_id
            return None

        def _prune_stack_to(target_level: int) -> None:
            """Removes deeper ancestors from the stack."""
            while ancestor_stack and ancestor_stack[-1].level >= target_level:
                ancestor_stack.pop()

        def _attach(node: HierarchyNode) -> None:
            """Attaches a node to its parent or to the root list."""
            if ancestor_stack:
                # Find the correct parent (last ancestor with lower level)
                for anc in reversed(ancestor_stack):
                    if anc.level < node.level:
                        anc.children.append(node)
                        return
            root_nodes.append(node)

        # Keep a reference to the last created leaf so continuations can be
        # appended to it.
        current_leaf: Optional[HierarchyNode] = None

        for page in pages:
            if "error" in page:
                continue
            page_number = page.get("page_number", 0)
            for block in (page.get("blocks") or []):
                block_type = block.get("type", "")

                # ── Image blocks: always a leaf node, never structural ──
                if block_type == "image":
                    node = HierarchyNode(
                        node_id=next_id(),
                        parent_id=_parent_id_for_level(99),
                        level=99,
                        node_type="image",
                        title="<image>",
                        text="<image>",
                        page_number=page_number,
                        block_ids=[block["block_id"]],
                        bbox=list(block.get("bbox") or [0.0, 0.0, 0.0, 0.0]),
                    )
                    _attach(node)
                    current_leaf = node
                    continue

                # ── Text / list blocks ──
                level, node_type = _classify_block(block, body_font_size)

                if level is not None:
                    # Structural node — starts a new branch
                    _prune_stack_to(level)
                    parent_id = _parent_id_for_level(level)
                    node = self._make_node(
                        next_id(), parent_id, level, node_type, block, page_number
                    )
                    _attach(node)
                    ancestor_stack.append(node)
                    current_leaf = node

                else:
                    # Leaf / continuation block
                    if node_type == "bullet_list":
                        # Each bullet is its own leaf but shares the current parent level
                        effective_level = (ancestor_stack[-1].level + 1) if ancestor_stack else 5
                        parent_id = _parent_id_for_level(effective_level)
                        node = self._make_node(
                            next_id(), parent_id, effective_level, "bullet_list",
                            block, page_number
                        )
                        _attach(node)
                        current_leaf = node

                    elif current_leaf is not None:
                        # Append to the current open leaf (paragraph continuation)
                        continuation_text = block.get("text", "").strip()
                        if continuation_text:
                            if current_leaf.text:
                                current_leaf.text += "\n" + continuation_text
                            else:
                                current_leaf.text = continuation_text
                            current_leaf.block_ids.append(block["block_id"])
                            # Expand the bounding box
                            current_leaf.bbox = _union_bbox(
                                [current_leaf.bbox, list(block.get("bbox") or [])]
                            )
                    else:
                        # No open node yet — create a root unknown node
                        node = self._make_node(
                            next_id(), None, 3, "unknown", block, page_number
                        )
                        root_nodes.append(node)
                        ancestor_stack.append(node)
                        current_leaf = node

        return root_nodes

    # ------------------------------------------------------------------
    # Document processing
    # ------------------------------------------------------------------

    def process_document(self, json_path: Path) -> None:
        """Processes a single normalized JSON and writes the hierarchy JSON."""
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — hierarchy already exists.")
            return

        self.logger.info(f"Building hierarchy for: {json_path.name}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        try:
            pages = doc.get("pages") or []
            body_font_size = _estimate_body_font_size(pages)
            hierarchy = self._build_hierarchy(doc_id, pages, body_font_size)

            output = {
                "document_id": doc_id,
                "title": doc.get("title", doc_id),
                "document_status": doc.get("document_status", "ACTIVE"),
                "metadata": doc.get("metadata", {}),
                "page_count": doc.get("page_count", 0),
                "body_font_size": body_font_size,
                "hierarchy": [node.to_dict() for node in hierarchy],
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            self._update_stats(hierarchy)
            self.stats["documents_processed"] += 1

        except Exception as e:
            self.logger.error(f"Critical error building hierarchy for {doc_id}: {e}")

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Processes all normalized JSON files in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} normalized documents to process.")

        for json_path in tqdm(json_files, desc="Building hierarchies"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        """Prints verification summary."""
        docs = self.stats["documents_processed"]
        avg_nodes = (
            self.stats["nodes_created"] / docs if docs > 0 else 0.0
        )
        summary = (
            f"\n{'='*46}\n"
            f" HIERARCHY BUILDER VERIFICATION SUMMARY\n"
            f"{'='*46}\n"
            f"Documents processed:    {docs}\n"
            f"Hierarchy nodes created:{self.stats['nodes_created']}\n"
            f"Unknown nodes:          {self.stats['unknown_nodes']}\n"
            f"Maximum hierarchy depth:{self.stats['max_depth']}\n"
            f"Average nodes/document: {avg_nodes:.1f}\n"
            f"Output directory:       {self.output_dir}\n"
            f"{'='*46}\n"
        )
        print(summary)
        self.logger.info("Hierarchy builder pipeline completed.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "normalized"
    output_directory = project_root / "datasets" / "hierarchy"
    log_directory = project_root / "logs"

    builder = HierarchyBuilder(input_directory, output_directory, log_directory)
    builder.run()
