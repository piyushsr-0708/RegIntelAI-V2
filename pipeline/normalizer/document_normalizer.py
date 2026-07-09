import json
import logging
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Minimum times a header/footer string must appear across pages to be
# considered a repeated header or footer.
REPEATED_THRESHOLD: int = 3

# A block whose text matches this pattern and has no other content is treated
# as an isolated page-number block.
PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,4}\s*$")

# Status keywords indicating a document's regulatory status.
STATUS_KEYWORDS: Dict[str, str] = {
    "withdrawn": "WITHDRAWN",
    "superseded": "SUPERSEDED",
    "repealed": "REPEALED",
}

# Common Unicode mojibake sequences and their replacements.
ENCODING_FIXES: List[tuple] = [
    ("\u00e2\u0080\u0093", "\u2013"),   # â€" → –
    ("\u00e2\u0080\u0094", "\u2014"),   # â€" → —
    ("\u00e2\u0080\u0099", "\u2019"),   # â€™ → '
    ("\u00e2\u0080\u009c", "\u201c"),   # â€œ → "
    ("\u00e2\u0080\u009d", "\u201d"),   # â€ → "
    ("\u00e2\u0080\u00a2", "\u2022"),   # â€¢ → •
    ("\u00e2\u0080\u00a6", "\u2026"),   # â€¦ → …
    ("\u00c2\u00a0", "\u00a0"),         # Â  → NBSP
    ("\u00e2\u0082\u00b9", "\u20b9"),   # â‚¹ → ₹
    ("\ufffd", ""),                      # Replacement character → remove
    ("\u00e2\u0080\u008b", ""),         # Zero-width space → remove
    # Curly apostrophe fallback
    ("\u2018", "'"),
    ("\u2019", "'"),
    # Curly quotes fallback
    ("\u201c", '"'),
    ("\u201d", '"'),
    # En/em dash fallback normalization
    ("\u2013", "-"),
    ("\u2014", "--"),
]


class TextCleaner:
    """
    Stateless text-level normalizer.
    All methods are pure: they take text and return text.
    """

    @staticmethod
    def fix_encoding(text: str) -> str:
        """Applies known mojibake fixes and strips control characters."""
        for bad, good in ENCODING_FIXES:
            text = text.replace(bad, good)
        # Remove non-printable ASCII control characters (keep newlines/tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalizes spaces and collapses internal blank lines."""
        # Replace non-breaking space with regular space
        text = text.replace("\u00a0", " ")
        # Collapse multiple spaces on the same line to one
        text = re.sub(r"[ \t]+", " ", text)
        # Strip trailing whitespace per line
        lines = [line.rstrip() for line in text.split("\n")]
        # Collapse 3+ consecutive blank lines to 2
        collapsed: List[str] = []
        blank_run = 0
        for line in lines:
            if line == "":
                blank_run += 1
                if blank_run <= 2:
                    collapsed.append(line)
            else:
                blank_run = 0
                collapsed.append(line)
        return "\n".join(collapsed)

    @staticmethod
    def merge_wrapped_lines(text: str) -> str:
        """
        Merges soft-wrapped paragraph lines.

        A line is considered a continuation of the previous if:
        - The previous line does NOT end with '.', ':', ';', '!', '?'
        - The current line does NOT start with a digit, bullet, or capital
          letter that appears to begin a new sentence/clause.
        - Neither line is blank.

        List items, numbered clauses, and headings are preserved.
        """
        lines = text.split("\n")
        merged: List[str] = []
        i = 0
        while i < len(lines):
            current = lines[i]
            # If the current line is blank, pass through
            if current.strip() == "":
                merged.append(current)
                i += 1
                continue

            # Look ahead and decide whether to merge
            while i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() == "":
                    break  # Gap between paragraphs – stop merging
                # Do not merge if current ends with sentence-terminating punct
                if re.search(r"[.!?:;]\s*$", current):
                    break
                # Do not merge if next starts with list marker or digit
                if re.match(r"^\s*[\-\*\u2022\u2023\u25aa]", next_line):
                    break
                if re.match(r"^\s*\d+[\.\)]\s", next_line):
                    break
                # Merge
                current = current.rstrip() + " " + next_line.strip()
                i += 1

            merged.append(current)
            i += 1
        return "\n".join(merged)

    @staticmethod
    def is_page_number(text: str) -> bool:
        """Returns True if the block contains only an isolated page number."""
        return bool(PAGE_NUMBER_RE.match(text))


class RepeatedBlockDetector:
    """
    Detects repeated headers and footers across pages.
    """

    def __init__(self, threshold: int = REPEATED_THRESHOLD):
        self.threshold = threshold

    def _block_texts(self, pages: List[Dict[str, Any]]) -> List[List[str]]:
        """Extracts first-block and last-block text per page."""
        first_texts: List[str] = []
        last_texts: List[str] = []
        for page in pages:
            blocks = page.get("blocks") or []
            text_blocks = [b for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
            if len(text_blocks) >= 1:
                first_texts.append(text_blocks[0]["text"].strip())
                last_texts.append(text_blocks[-1]["text"].strip())
            else:
                first_texts.append("")
                last_texts.append("")
        return [first_texts, last_texts]

    def find_repeated_headers(self, pages: List[Dict[str, Any]]) -> set:
        """Returns the set of text strings that appear as repeated headers."""
        first_texts, _ = self._block_texts(pages)
        counts = Counter(t for t in first_texts if t)
        return {t for t, c in counts.items() if c >= self.threshold}

    def find_repeated_footers(self, pages: List[Dict[str, Any]]) -> set:
        """Returns the set of text strings that appear as repeated footers."""
        _, last_texts = self._block_texts(pages)
        counts = Counter(t for t in last_texts if t)
        return {t for t, c in counts.items() if c >= self.threshold}


class DocumentNormalizer:
    """
    Normalizer V1.

    Reads parser-output JSON files from `input_dir`, applies text
    normalization, removes repeated headers/footers and isolated page
    numbers, detects document status from watermark text, and writes
    normalized JSON to `output_dir`.

    Schema is identical to the parser output.
    """

    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir

        self._ensure_directories()
        self._setup_logging()
        self.cleaner = TextCleaner()
        self.detector = RepeatedBlockDetector()

        self.stats: Dict[str, int] = {
            "documents_normalized": 0,
            "blocks_merged": 0,
            "headers_removed": 0,
            "footers_removed": 0,
            "encoding_fixes": 0,
            "statuses_detected": 0,
        }

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _ensure_directories(self) -> None:
        """Creates output and log directories if absent."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        """Configures root logger to write to normalizer.log and stdout."""
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        log_file = self.log_dir / "normalizer.log"
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

    # ------------------------------------------------------------------
    # Text-level helpers
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Applies all text-level normalization steps in order."""
        before = text
        text = self.cleaner.fix_encoding(text)
        if text != before:
            self.stats["encoding_fixes"] += 1
        text = self.cleaner.normalize_whitespace(text)
        text = self.cleaner.merge_wrapped_lines(text)
        return text

    def _detect_status(self, doc_text: str) -> Optional[str]:
        """
        Scans the full document text for regulatory-status watermarks.
        Returns the status string if found, else None.
        """
        lower = doc_text.lower()
        for keyword, status in STATUS_KEYWORDS.items():
            if keyword in lower:
                return status
        return None

    # ------------------------------------------------------------------
    # Page-level normalization
    # ------------------------------------------------------------------

    def _normalize_page(
        self,
        page: Dict[str, Any],
        repeated_headers: set,
        repeated_footers: set,
    ) -> Dict[str, Any]:
        """
        Normalizes a single page dict in-place (copy returned).

        Modifies:
        - Cleans text in each block.
        - Removes repeated header blocks.
        - Removes repeated footer blocks.
        - Removes isolated page-number blocks.
        """
        if "error" in page:
            # Pass error pages through unchanged.
            return dict(page)

        page = dict(page)  # shallow copy to avoid mutating input
        blocks: List[Dict[str, Any]] = page.get("blocks") or []
        text_blocks = [b for b in blocks if b.get("type") == "text"]

        to_remove: set = set()

        # Identify header block
        if text_blocks:
            first_text = text_blocks[0].get("text", "").strip()
            if first_text in repeated_headers:
                to_remove.add(text_blocks[0]["block_id"])
                self.stats["headers_removed"] += 1

        # Identify footer block
        if text_blocks and len(text_blocks) > 1:
            last_text = text_blocks[-1].get("text", "").strip()
            if last_text in repeated_footers:
                to_remove.add(text_blocks[-1]["block_id"])
                self.stats["footers_removed"] += 1

        # Identify isolated page-number blocks
        for b in text_blocks:
            if self.cleaner.is_page_number(b.get("text", "")):
                to_remove.add(b["block_id"])
                self.stats["footers_removed"] += 1

        # Apply cleaning and filtering
        normalized_blocks: List[Dict[str, Any]] = []
        for b in blocks:
            if b.get("block_id") in to_remove:
                continue
            b = dict(b)  # copy
            if b.get("type") == "text" and b.get("text"):
                b["text"] = self._clean_text(b["text"])
            normalized_blocks.append(b)

        page["blocks"] = normalized_blocks
        return page

    # ------------------------------------------------------------------
    # Document-level normalization
    # ------------------------------------------------------------------

    def normalize_document(self, json_path: Path) -> None:
        """Reads one parsed JSON, normalizes it, and writes to output_dir."""
        doc_id = json_path.stem
        output_file = self.output_dir / f"{doc_id}.json"

        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} – normalized file already exists.")
            return

        self.logger.info(f"Normalizing: {json_path.name}")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            self.logger.error(f"Cannot read {json_path}: {e}")
            return

        try:
            pages: List[Dict[str, Any]] = doc.get("pages") or []

            # Pre-scan for repeated headers/footers
            repeated_headers = self.detector.find_repeated_headers(pages)
            repeated_footers = self.detector.find_repeated_footers(pages)

            # Normalize each page independently
            normalized_pages: List[Dict[str, Any]] = []
            for page in pages:
                try:
                    normalized_pages.append(
                        self._normalize_page(page, repeated_headers, repeated_footers)
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error normalizing page {page.get('page_number', '?')} of {doc_id}: {e}"
                    )
                    # Preserve original page on failure
                    normalized_pages.append(dict(page))

            # Detect document status from full text
            full_text = " ".join(
                b.get("text", "")
                for page in normalized_pages
                for b in (page.get("blocks") or [])
                if b.get("type") == "text"
            )
            status = self._detect_status(full_text)
            if status:
                self.stats["statuses_detected"] += 1

            # Build normalized document
            normalized_doc: Dict[str, Any] = {
                **doc,
                "pages": normalized_pages,
                "document_status": status or "ACTIVE",
                "normalized": True,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(normalized_doc, f, indent=2, ensure_ascii=False)

            self.stats["documents_normalized"] += 1

        except Exception as e:
            self.logger.error(f"Critical error normalizing document {doc_id}: {e}")

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Processes all JSON files in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        json_files = sorted(self.input_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} parsed documents to normalize.")

        for json_path in tqdm(json_files, desc="Normalizing documents"):
            self.normalize_document(json_path)

        self.print_summary()

    def print_summary(self) -> None:
        """Prints verification summary."""
        summary = (
            f"\n{'='*44}\n"
            f" NORMALIZER PIPELINE VERIFICATION SUMMARY\n"
            f"{'='*44}\n"
            f"Documents normalized:    {self.stats['documents_normalized']}\n"
            f"Blocks merged:           {self.stats['blocks_merged']}\n"
            f"Headers removed:         {self.stats['headers_removed']}\n"
            f"Footers removed:         {self.stats['footers_removed']}\n"
            f"Encoding fixes applied:  {self.stats['encoding_fixes']}\n"
            f"Document statuses found: {self.stats['statuses_detected']}\n"
            f"Output directory:        {self.output_dir}\n"
            f"{'='*44}\n"
        )
        print(summary)
        self.logger.info("Normalizer pipeline completed.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    input_directory = project_root / "datasets" / "parsed"
    output_directory = project_root / "datasets" / "normalized"
    log_directory = project_root / "logs"

    normalizer = DocumentNormalizer(input_directory, output_directory, log_directory)
    normalizer.run()
