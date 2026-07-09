import os
import csv
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

import fitz  # PyMuPDF
from tqdm import tqdm


@dataclass
class PDFInventory:
    """Data class to store inventory metadata for a single PDF document."""
    document_id: str
    title: str
    filename: str
    pages: int
    file_size_kb: float
    searchable: bool
    searchable_pages: int
    total_text_characters: int
    average_text_per_page: float
    images: int
    bookmarks_count: int
    encrypted: bool
    author: str
    creator: str
    producer: str
    creation_date: str
    modification_date: str
    processing_recommendation: str


class InventoryManager:
    """
    Manages the PDF inventory process for the RegIntel AI project.
    Analyzes PDFs and generates an inventory report.
    """

    def __init__(self, base_dir: Path) -> None:
        """
        Initializes the InventoryManager.
        
        Args:
            base_dir (Path): The base directory containing the 'pdfs' folder.
        """
        self.base_dir = base_dir
        self.pdf_dir = base_dir / "pdfs"
        self.output_csv = base_dir / "inventory_report.csv"
        self.log_file = base_dir / "inventory.log"
        
        self._ensure_directories()
        self._setup_logging()
        
    def _ensure_directories(self) -> None:
        """Ensures all necessary directories exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        
    def _setup_logging(self) -> None:
        """Sets up the logging configuration to write to inventory.log."""
        # Remove any existing handlers to prevent duplicate logging
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            filename=str(self.log_file),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def _determine_recommendation(
        self, 
        encrypted: bool, 
        pages: int, 
        avg_text: float, 
        searchable_pages: int
    ) -> str:
        """
        Determines the processing recommendation based on document statistics.
        
        Args:
            encrypted (bool): Whether the document is encrypted.
            pages (int): Total number of pages.
            avg_text (float): Average text characters per page.
            searchable_pages (int): Number of pages with significant text.
            
        Returns:
            str: The processing recommendation category.
        """
        if encrypted:
            return "ENCRYPTED"
        if pages >= 500:
            return "LARGE_DOCUMENT"
        
        # Heuristics for OCR and text processing
        if avg_text < 50:
            return "OCR_REQUIRED"
        elif searchable_pages / max(pages, 1) > 0.8 and avg_text > 200:
            return "TEXT_READY"
        else:
            return "LOW_TEXT"

    def analyze_pdf(self, pdf_path: Path) -> Optional[PDFInventory]:
        """
        Analyzes a single PDF file and extracts its metadata.
        
        Args:
            pdf_path (Path): Path to the PDF file.
            
        Returns:
            Optional[PDFInventory]: The inventory data, or None if extraction failed.
        """
        file_size_kb = pdf_path.stat().st_size / 1024.0
        filename = pdf_path.name
        document_id = pdf_path.stem

        try:
            # fitz.open will raise an exception if it's not a valid file
            doc = fitz.open(pdf_path)
        except Exception as e:
            self.logger.error(f"Failed to open PDF {filename}: {e}")
            return None

        try:
            encrypted = doc.is_encrypted
            if encrypted:
                # Attempt to authenticate with an empty password
                # Some PDFs are encrypted but don't require a user password to read
                doc.authenticate("")

            pages = len(doc)
            metadata = doc.metadata or {}
            
            title = metadata.get("title", "") or ""
            author = metadata.get("author", "") or ""
            creator = metadata.get("creator", "") or ""
            producer = metadata.get("producer", "") or ""
            creation_date = metadata.get("creationDate", "") or ""
            modification_date = metadata.get("modDate", "") or ""
            
            # get_toc() returns the Table of Contents/Bookmarks list
            bookmarks_count = len(doc.get_toc())
            
            total_text_characters = 0
            searchable_pages = 0
            total_images = 0
            
            for page_num in range(pages):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                char_count = len(text.strip())
                total_text_characters += char_count
                
                # Consider a page searchable if it has a reasonable amount of text
                if char_count > 50:
                    searchable_pages += 1
                    
                # Extract image counts
                try:
                    images = page.get_images()
                    total_images += len(images)
                except Exception as e:
                    self.logger.warning(f"Could not read images on page {page_num} of {filename}: {e}")

            average_text_per_page = total_text_characters / pages if pages > 0 else 0.0
            searchable = searchable_pages > (pages * 0.5) if pages > 0 else False
            
            recommendation = self._determine_recommendation(
                encrypted, pages, average_text_per_page, searchable_pages
            )

            return PDFInventory(
                document_id=document_id,
                title=title,
                filename=filename,
                pages=pages,
                file_size_kb=round(file_size_kb, 2),
                searchable=searchable,
                searchable_pages=searchable_pages,
                total_text_characters=total_text_characters,
                average_text_per_page=round(average_text_per_page, 2),
                images=total_images,
                bookmarks_count=bookmarks_count,
                encrypted=encrypted,
                author=author,
                creator=creator,
                producer=producer,
                creation_date=creation_date,
                modification_date=modification_date,
                processing_recommendation=recommendation
            )
        except Exception as e:
            self.logger.error(f"Error processing PDF {filename}: {e}")
            return None
        finally:
            doc.close()

    def run(self) -> None:
        """Runs the inventory process on all PDFs in the designated directory."""
        if not self.pdf_dir.exists():
            msg = f"PDF directory does not exist: {self.pdf_dir}"
            self.logger.error(msg)
            print(msg)
            return

        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            msg = f"No PDFs found in {self.pdf_dir}"
            self.logger.warning(msg)
            print(msg)
            return

        self.logger.info(f"Starting inventory of {len(pdf_files)} PDFs.")
        print(f"Analyzing {len(pdf_files)} PDFs from {self.pdf_dir}...")

        inventory_results: List[PDFInventory] = []
        
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            result = self.analyze_pdf(pdf_path)
            if result:
                inventory_results.append(result)

        if not inventory_results:
            msg = "No PDFs were successfully processed."
            self.logger.error(msg)
            print(msg)
            return

        self._save_report(inventory_results)
        self._print_summary(inventory_results)

    def _save_report(self, results: List[PDFInventory]) -> None:
        """
        Saves the inventory results to a CSV file.
        
        Args:
            results (List[PDFInventory]): The list of analyzed PDF data.
        """
        try:
            with open(self.output_csv, mode="w", newline="", encoding="utf-8") as f:
                if not results:
                    return
                writer = csv.DictWriter(f, fieldnames=asdict(results[0]).keys())
                writer.writeheader()
                for result in results:
                    writer.writerow(asdict(result))
            self.logger.info(f"Successfully saved report to {self.output_csv}")
        except Exception as e:
            self.logger.error(f"Failed to save CSV report: {e}")

    def _print_summary(self, results: List[PDFInventory]) -> None:
        """
        Prints a summary of the dataset to the console.
        
        Args:
            results (List[PDFInventory]): The list of analyzed PDF data.
        """
        total_pdfs = len(results)
        total_pages = sum(r.pages for r in results)
        total_images = sum(r.images for r in results)
        avg_pages = total_pages / total_pdfs if total_pdfs > 0 else 0
        avg_text_per_page = sum(r.average_text_per_page for r in results) / total_pdfs if total_pdfs > 0 else 0

        categories: Dict[str, int] = {
            "TEXT_READY": 0,
            "OCR_REQUIRED": 0,
            "LOW_TEXT": 0,
            "LARGE_DOCUMENT": 0,
            "ENCRYPTED": 0
        }
        
        for r in results:
            cat = r.processing_recommendation
            if cat in categories:
                categories[cat] += 1
            else:
                categories[cat] = 1

        summary = (
            f"\n--- Dataset Summary ---\n"
            f"Total PDFs processed successfully: {total_pdfs}\n"
            f"Average Pages per PDF: {avg_pages:.2f}\n"
            f"Average Text per Page: {avg_text_per_page:.2f} chars\n"
            f"Total Images Extracted: {total_images}\n\n"
            f"Processing Recommendations:\n"
        )
        for cat, count in categories.items():
            summary += f"  - {cat}: {count}\n"

        print(summary)
        self.logger.info("Inventory complete. Summary generated.")


if __name__ == "__main__":
    # Point directly to the requested folder
    base_directory = Path(r"D:\SuRaksha-v2\datasets\raw\master_directions")
    manager = InventoryManager(base_directory)
    manager.run()