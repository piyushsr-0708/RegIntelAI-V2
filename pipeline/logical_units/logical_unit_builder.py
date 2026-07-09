"""
Logical Unit Builder V1 — RegIntel AI (SuRaksha-v2)

Transforms a hierarchy JSON (from the Hierarchy Builder pipeline) into
coherent Logical Units suitable for downstream AI reasoning.

A Logical Unit represents the smallest complete regulatory statement:
a heading node together with its direct children (continuation paragraphs,
notes, explanations, exceptions, illustrations, tables, bullet lists)
that belong to the same legal statement.

No text is invented, summarised, or modified — only reorganised.
"""

import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Node types that act as "container" nodes — i.e., they open a new logical
# unit that may absorb child content.
STRUCTURAL_TYPES = {
    "part", "chapter", "section", "subsection",
    "clause", "subclause", "schedule",
}

# Node types that are absorbed into the current open logical unit rather than
# starting a new one.
ABSORBABLE_TYPES = {
    "bullet_list", "note", "explanation", "definition",
    "unknown", "table", "image",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LogicalUnit:
    logical_unit_id: str
    document_id: str
    title: str
    text: str
    node_type: str
    level: int
    page_range: List[int]
    hierarchy_node_ids: List[str]
    block_ids: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _collect_all_blocks(node: Dict[str, Any]) -> List[str]:
    """Recursively collects all block_ids from a node and its children."""
    ids: List[str] = list(node.get("block_ids") or [])
    for child in node.get("children") or []:
        ids.extend(_collect_all_blocks(child))
    return ids


def _collect_all_node_ids(node: Dict[str, Any]) -> List[str]:
    """Recursively collects all node_ids from a node and its children."""
    ids = [node["node_id"]]
    for child in node.get("children") or []:
        ids.extend(_collect_all_node_ids(child))
    return ids


def _collect_text(node: Dict[str, Any]) -> str:
    """Returns the full text of a node including all descendant nodes."""
    parts: List[str] = []
    text = (node.get("text") or "").strip()
    if text:
        parts.append(text)
    for child in node.get("children") or []:
        child_text = _collect_text(child)
        if child_text:
            parts.append(child_text)
    return "\n".join(parts)


def _page_range(node: Dict[str, Any]) -> List[int]:
    """Returns the set of page numbers touched by a node and its children."""
    pages: set = set()
    pg = node.get("page_number")
    if pg is not None:
        pages.add(pg)
    for child in node.get("children") or []:
        pages.update(_page_range(child))
    return sorted(pages)


def _unique_ordered(seq: List[str]) -> List[str]:
    """Removes duplicates from a list while preserving insertion order."""
    seen: set = set()
    out: List[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Logical unit assembly
# ---------------------------------------------------------------------------

class LogicalUnitAssembler:
    """
    Converts a flat or nested hierarchy node list into Logical Units.

    Strategy:
    - Walk hierarchy nodes in order (DFS pre-order).
    - When a STRUCTURAL node is encountered, it opens a new Logical Unit.
    - Its immediate ABSORBABLE children are merged into that same unit.
    - Nested STRUCTURAL children each start their own Logical Unit.
    - Structural nodes with no meaningful text but with structural children
      are still emitted as their own unit (parent reference preserved).
    """

    def __init__(self, doc_id: str, doc_metadata: Dict[str, Any]):
        self.doc_id = doc_id
        self.doc_metadata = doc_metadata
        self._seq = 0
        self.units: List[LogicalUnit] = []

    def _next_id(self) -> str:
        self._seq += 1
        return f"{self.doc_id}_lu{self._seq}"

    def _make_unit(
        self,
        node: Dict[str, Any],
        extra_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> LogicalUnit:
        """
        Creates a LogicalUnit from a primary node and optional sibling
        absorbable nodes that belong to the same legal statement.
        """
        extra_nodes = extra_nodes or []

        # Collect text: node + its own absorbable children + extra siblings
        text_parts: List[str] = []
        node_ids: List[str] = []
        block_ids: List[str] = []
        pages: set = set()

        def _absorb(n: Dict[str, Any]) -> None:
            t = (n.get("text") or "").strip()
            if t:
                text_parts.append(t)
            node_ids.extend(_collect_all_node_ids(n))
            block_ids.extend(_collect_all_blocks(n))
            for pg in _page_range(n):
                pages.add(pg)

        _absorb(node)

        # Absorb ABSORBABLE children directly owned by this node
        for child in node.get("children") or []:
            if child.get("node_type") in ABSORBABLE_TYPES:
                _absorb(child)

        # Absorb sibling absorbable nodes passed in
        for extra in extra_nodes:
            _absorb(extra)

        return LogicalUnit(
            logical_unit_id=self._next_id(),
            document_id=self.doc_id,
            title=node.get("title") or "",
            text="\n".join(text_parts),
            node_type=node.get("node_type", "unknown"),
            level=node.get("level", 0),
            page_range=sorted(pages),
            hierarchy_node_ids=_unique_ordered(node_ids),
            block_ids=_unique_ordered(block_ids),
            metadata={
                "document_status": self.doc_metadata.get("document_status", "ACTIVE"),
                "source_doc_metadata": self.doc_metadata.get("doc_metadata", {}),
            },
        )

    def _process_node(self, node: Dict[str, Any]) -> None:
        """Recursively processes a hierarchy node."""
        node_type = node.get("node_type", "unknown")
        children = node.get("children") or []

        if node_type in STRUCTURAL_TYPES:
            # Separate children into absorbable siblings and structural sub-nodes
            absorbable: List[Dict[str, Any]] = []
            structural_children: List[Dict[str, Any]] = []

            for child in children:
                ct = child.get("node_type", "unknown")
                if ct in ABSORBABLE_TYPES:
                    absorbable.append(child)
                else:
                    structural_children.append(child)

            # Emit this node as a logical unit (absorbing its absorbable children)
            unit = self._make_unit(node, extra_nodes=[])
            # Note: _make_unit already absorbs ABSORBABLE children of node itself.
            # absorbable list only contains top-level siblings collected above —
            # they're already captured inside _absorb(node) for children.
            self.units.append(unit)

            # Recurse into structural children — each becomes its own unit
            for child in structural_children:
                self._process_node(child)

        elif node_type in ABSORBABLE_TYPES:
            # A top-level absorbable node with no structural parent — emit as-is
            unit = self._make_unit(node)
            self.units.append(unit)

        else:
            # Fallback: emit as unknown
            unit = self._make_unit(node)
            self.units.append(unit)

    def build(self, hierarchy: List[Dict[str, Any]]) -> List[LogicalUnit]:
        """Entry point: processes a list of top-level hierarchy nodes."""
        for node in hierarchy:
            try:
                self._process_node(node)
            except Exception as e:
                logging.getLogger(__name__).error(
                    f"Error processing node {node.get('node_id')}: {e}"
                )
        return self.units


# ---------------------------------------------------------------------------
# Document processor
# ---------------------------------------------------------------------------

class LogicalUnitBuilder:
    """
    Orchestrates the Logical Unit building pipeline across all hierarchy JSONs.
    """

    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        self._ensure_directories()
        self._setup_logging()

        self.stats: Dict[str, Any] = {
            "documents_processed": 0,
            "units_created": 0,
            "total_text_length": 0,
            "largest_unit_chars": 0,
            "largest_unit_id": "",
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

        log_file = self.log_dir / "logical_unit_builder.log"
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
    # Processing
    # ------------------------------------------------------------------

    def process_document(self, json_path: Path) -> None:
        """Processes a single hierarchy JSON and writes the logical units JSON."""
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} — logical units already exist.")
            return

        self.logger.info(f"Building logical units for: {json_path.name}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        try:
            hierarchy = doc.get("hierarchy") or []
            doc_metadata = {
                "document_status": doc.get("document_status", "ACTIVE"),
                "doc_metadata": doc.get("metadata", {}),
            }

            assembler = LogicalUnitAssembler(doc_id, doc_metadata)
            units = assembler.build(hierarchy)

            # Update stats
            for unit in units:
                text_len = len(unit.text)
                self.stats["total_text_length"] += text_len
                self.stats["units_created"] += 1
                if text_len > self.stats["largest_unit_chars"]:
                    self.stats["largest_unit_chars"] = text_len
                    self.stats["largest_unit_id"] = unit.logical_unit_id

            output = {
                "document_id": doc_id,
                "title": doc.get("title", doc_id),
                "document_status": doc.get("document_status", "ACTIVE"),
                "page_count": doc.get("page_count", 0),
                "logical_unit_count": len(units),
                "logical_units": [u.to_dict() for u in units],
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            self.stats["documents_processed"] += 1

        except Exception as e:
            self.logger.error(f"Critical error for {doc_id}: {e}")

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Processes all hierarchy JSONs in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} hierarchy documents to process.")

        for json_path in tqdm(json_files, desc="Building logical units"):
            self.process_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        """Prints verification summary."""
        docs = self.stats["documents_processed"]
        units = self.stats["units_created"]
        avg_units = units / docs if docs > 0 else 0.0
        avg_text = self.stats["total_text_length"] / units if units > 0 else 0.0

        summary = (
            f"\n{'='*48}\n"
            f" LOGICAL UNIT BUILDER VERIFICATION SUMMARY\n"
            f"{'='*48}\n"
            f"Documents processed:    {docs}\n"
            f"Logical units created:  {units}\n"
            f"Average units/document: {avg_units:.1f}\n"
            f"Average text length:    {avg_text:.0f} chars\n"
            f"Largest logical unit:   {self.stats['largest_unit_chars']} chars\n"
            f"  (id: {self.stats['largest_unit_id']})\n"
            f"Output directory:       {self.output_dir}\n"
            f"{'='*48}\n"
        )
        print(summary)
        self.logger.info("Logical Unit Builder pipeline completed.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "hierarchy"
    output_directory = project_root / "datasets" / "logical_units"
    log_directory = project_root / "logs"

    builder = LogicalUnitBuilder(input_directory, output_directory, log_directory)
    builder.run()
