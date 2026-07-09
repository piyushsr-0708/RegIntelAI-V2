import os
import sys
import json
import time
import hashlib
import logging
import traceback
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Missing dependency: PyMuPDF. Please install using: pip install pymupdf")
    sys.exit(1)
    
from tqdm import tqdm

# Ensure pipeline is in python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@dataclass
class FontInfo:
    size: float
    name: str
    flags: int
    is_bold: bool
    is_italic: bool


@dataclass
class BlockModel:
    block_id: str
    type: str  # "text", "image", etc.
    bbox: List[float]
    text: str
    font_info: Optional[Dict[str, Any]] = None


@dataclass
class PageModel:
    page_number: int
    width: Optional[float] = None
    height: Optional[float] = None
    blocks: Optional[List[BlockModel]] = None
    links: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


@dataclass
class DocumentModel:
    document_id: str
    title: str
    metadata: Dict[str, Any]
    page_count: int
    pages: List[PageModel]


class PDFParser:
    """
    Parser V1 - Document Structure Extractor.
    Extracts purely structural information (pages, text blocks, images, links, metadata).
    No semantic interpretation or table extraction is performed.
    """

    def __init__(self, input_dir: Path, output_dir: Path, log_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.log_dir = log_dir
        
        self._ensure_directories()
        self._setup_logging()
        
        self.stats = {
            "documents_parsed": 0,
            "pages_parsed": 0,
            "blocks_extracted": 0,
            "images_detected": 0,
            "errors": 0
        }

    def _ensure_directories(self) -> None:
        """Creates the parsed and logs directories if they do not exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        """Configures the logger."""
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        log_file = self.log_dir / "parser.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        logging.getLogger("").addHandler(console)
        self.logger = logging.getLogger(__name__)

    def _compute_sha256(self, filepath: Path) -> str:
        """Computes SHA256 of the file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not compute SHA256 for {filepath}: {e}")
            return ""

    def _get_dominant_font(self, block_dict: Dict[str, Any]) -> Optional[FontInfo]:
        """Extracts the dominant font information from a text block."""
        fonts = {}
        for line in block_dict.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                font = span.get("font", "Unknown")
                flags = span.get("flags", 0)
                text_len = len(span.get("text", ""))
                
                key = (size, font, flags)
                if key not in fonts:
                    fonts[key] = 0
                fonts[key] += text_len
                
        if not fonts:
            return None
            
        dominant = max(fonts.items(), key=lambda x: x[1])[0]
        size, name, flags = dominant
        
        is_bold = bool(flags & 16) or "bold" in name.lower()
        is_italic = bool(flags & 2) or "italic" in name.lower()
        
        return FontInfo(size=round(size, 2), name=name, flags=flags, is_bold=is_bold, is_italic=is_italic)

    def parse_page(self, page: fitz.Page, page_number: int) -> PageModel:
        """Parses a single page into structured blocks."""
        try:
            rect = page.rect
            width, height = rect.width, rect.height
            
            # Extract links
            links_data = []
            for link in page.get_links():
                link_info = {
                    "kind": link.get("kind"),
                    "from": list(link.get("from", [])),
                }
                if "uri" in link:
                    link_info["uri"] = link["uri"]
                elif "page" in link:
                    link_info["page"] = link["page"]
                links_data.append(link_info)
                
            dict_data = page.get_text("dict")
            raw_blocks = dict_data.get("blocks", [])
            
            page_blocks: List[BlockModel] = []
            block_index = 0
            
            for b in raw_blocks:
                bbox = b.get("bbox", [0, 0, 0, 0])
                b_type = b.get("type")
                
                if b_type == 1:  # Image
                    b_model = BlockModel(
                        block_id=f"p{page_number}_b{block_index}",
                        type="image",
                        bbox=list(bbox),
                        text="<image>"
                    )
                    self.stats["images_detected"] += 1
                    page_blocks.append(b_model)
                    block_index += 1
                    self.stats["blocks_extracted"] += 1
                    
                elif b_type == 0:  # Text
                    lines = b.get("lines", [])
                    text = "\n".join([ "".join([span.get("text", "") for span in line.get("spans", [])]) for line in lines ])
                    text = text.strip()
                    
                    if not text:
                        continue
                        
                    font_info = self._get_dominant_font(b)
                    
                    b_model = BlockModel(
                        block_id=f"p{page_number}_b{block_index}",
                        type="text",
                        bbox=list(bbox),
                        text=text,
                        font_info=asdict(font_info) if font_info else None
                    )
                    page_blocks.append(b_model)
                    block_index += 1
                    self.stats["blocks_extracted"] += 1

            page_blocks.sort(key=lambda x: (x.bbox[1], x.bbox[0]))
            
            return PageModel(
                page_number=page_number,
                width=width,
                height=height,
                blocks=page_blocks,
                links=links_data
            )
        except Exception as e:
            self.logger.error(f"Error parsing page {page_number}: {e}")
            self.stats["errors"] += 1
            return PageModel(
                page_number=page_number,
                error=str(e)
            )

    def parse_document(self, pdf_path: Path) -> None:
        """Parses a single PDF document and writes the JSON output."""
        doc_id = pdf_path.stem
        output_file = self.output_dir / f"{doc_id}.json"
        
        if output_file.exists():
            self.logger.info(f"Skipping {doc_id} - parsed file already exists.")
            return
            
        self.logger.info(f"Parsing document: {pdf_path.name}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            self.logger.error(f"Failed to open document {pdf_path}: {e}")
            self.stats["errors"] += 1
            return
            
        try:
            file_size = pdf_path.stat().st_size
            sha256 = self._compute_sha256(pdf_path)
            meta = doc.metadata or {}
            
            try:
                toc = doc.get_toc()
            except Exception:
                toc = []
                
            metadata = {
                "author": meta.get("author", ""),
                "creator": meta.get("creator", ""),
                "producer": meta.get("producer", ""),
                "creation_date": meta.get("creationDate", ""),
                "modification_date": meta.get("modDate", ""),
                "bookmarks_count": len(toc),
                "file_size_bytes": file_size,
                "sha256": sha256,
                "toc": toc
            }
            
            page_models = []
            page_count = len(doc)
            
            for i in range(page_count):
                p_model = self.parse_page(doc[i], i + 1)
                page_models.append(p_model)
                self.stats["pages_parsed"] += 1
            
            document_model = DocumentModel(
                document_id=doc_id,
                title=meta.get("title", "") or doc_id,
                metadata=metadata,
                page_count=page_count,
                pages=page_models
            )
            
            # Serialize removing None fields to keep JSON clean
            def filter_none(d):
                if isinstance(d, dict):
                    return {k: filter_none(v) for k, v in d.items() if v is not None}
                elif isinstance(d, list):
                    return [filter_none(v) for v in d if v is not None]
                else:
                    return d
                    
            json_data = filter_none(asdict(document_model))
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            self.stats["documents_parsed"] += 1
            
        except Exception as e:
            self.logger.error(f"Critical error parsing document {doc_id}: {e}")
            self.stats["errors"] += 1
        finally:
            doc.close()

    def run(self) -> None:
        """Executes the parsing pipeline across all PDFs in the input directory."""
        if not self.input_dir.exists():
            self.logger.error(f"Input directory does not exist: {self.input_dir}")
            return
            
        pdf_files = list(self.input_dir.glob("*.pdf"))
        self.logger.info(f"Found {len(pdf_files)} PDF documents to parse.")
        
        for pdf_path in tqdm(pdf_files, desc="Parsing PDFs"):
            self.parse_document(pdf_path)
            
        self.print_summary()

    def print_summary(self) -> None:
        """Prints verification summary metrics."""
        avg_blocks = 0
        if self.stats["pages_parsed"] > 0:
            avg_blocks = self.stats["blocks_extracted"] / self.stats["pages_parsed"]
            
        summary = (
            f"\n{'='*40}\n"
            f"PARSER PIPELINE VERIFICATION SUMMARY\n"
            f"{'='*40}\n"
            f"Documents parsed:    {self.stats['documents_parsed']}\n"
            f"Pages parsed:        {self.stats['pages_parsed']}\n"
            f"Blocks extracted:    {self.stats['blocks_extracted']}\n"
            f"Images detected:     {self.stats['images_detected']}\n"
            f"Average blocks/page: {avg_blocks:.2f}\n"
            f"Errors encountered:  {self.stats['errors']}\n"
            f"Output directory:    {self.output_dir}\n"
            f"{'='*40}\n"
        )
        print(summary)
        self.logger.info("Parsing pipeline completed.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    
    input_directory = project_root / "datasets" / "raw" / "master_directions" / "pdfs"
    output_directory = project_root / "datasets" / "parsed"
    log_directory = project_root / "logs"
    
    parser = PDFParser(input_directory, output_directory, log_directory)
    parser.run()
