import os
import sys
import csv
import time
import hashlib
import logging
import urllib.parse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

# Ensure pipeline is in python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pipeline.acquisition.downloaders.base_downloader import BaseDownloader
from pipeline.acquisition.utils.domain_tagger import DomainTagger

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Please install requirements: pip install playwright pymupdf && playwright install chromium")
    sys.exit(1)


@dataclass
class DownloadMetadata:
    """Structure for document metadata to be saved to CSV."""
    document_id: str
    title: str
    domain: str
    pdf_url: str
    file_path: str
    sha256_hash: str
    download_timestamp: float


class RBIMasterDirectionsDownloader(BaseDownloader):
    """Playwright-based downloader for RBI Master Directions."""
    
    BASE_URL = "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx"
    
    def __init__(self, base_dir: Path):
        super().__init__(base_dir)
        self.pdf_dir = self.base_dir / "pdfs"
        self.metadata_file = self.base_dir / "master_directions_metadata.csv"
        self.log_file = self.base_dir / "downloader.log"
        self.ensure_directories()
        self.configure_logging()
        
    def ensure_directories(self) -> None:
        """Creates the necessary directories if they don't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        
    def configure_logging(self) -> None:
        """Sets up robust logging pointing to downloader.log and console."""
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            filename=str(self.log_file),
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
        """Computes the SHA256 hash of a file for integrity."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def _verify_pdf(self, filepath: Path) -> bool:
        """Verifies if the downloaded file is a valid PDF using PyMuPDF."""
        try:
            doc = fitz.open(filepath)
            if len(doc) == 0:
                self.logger.warning(f"PDF {filepath} has 0 pages.")
                doc.close()
                return False
            doc.close()
            return True
        except Exception as e:
            self.logger.warning(f"Failed to open PDF {filepath} with PyMuPDF: {e}")
            return False

    def _load_existing_metadata(self) -> List[str]:
        """Loads existing document IDs to facilitate resume capability."""
        downloaded_ids = []
        if self.metadata_file.exists():
            with open(self.metadata_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    downloaded_ids.append(row.get("document_id", ""))
        return downloaded_ids

    def _save_metadata(self, metadata: DownloadMetadata) -> None:
        """Appends a single new metadata record to the CSV file."""
        file_exists = self.metadata_file.exists()
        with open(self.metadata_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(metadata).keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(asdict(metadata))

    def _get_pdf_url_from_detail_page(self, page: Page, detail_url: str) -> Optional[str]:
        """Navigates to the detail page and extracts the real PDF URL."""
        try:
            if not detail_url.startswith("http"):
                if detail_url.startswith("/"):
                    detail_url = "https://www.rbi.org.in" + detail_url
                else:
                    detail_url = "https://www.rbi.org.in/Scripts/" + detail_url
                
            page.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
            
            # The actual PDF links frequently end with .PDF
            links = page.locator("a").element_handles()
            for link in links:
                href = link.get_attribute("href")
                if href and href.lower().endswith(".pdf"):
                    if not href.startswith("http"):
                        # Most rbidocs links are absolute, but resolving if relative
                        href = urllib.parse.urljoin("https://rbidocs.rbi.org.in/rdocs/notification/PDFs/", href.split("/")[-1])
                    return href
            
            self.logger.warning(f"No PDF link found on {detail_url}")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting PDF URL from {detail_url}: {e}")
            return None

    def run(self) -> None:
        """Main execution workflow for downloading RBI Master Directions."""
        self.logger.info("Starting Playwright Downloader for RBI Master Directions...")
        downloaded_ids = self._load_existing_metadata()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Create a realistic context that bypasses typical bot checks
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                accept_downloads=True
            )
            page = context.new_page()
            
            try:
                self.logger.info(f"Navigating to {self.BASE_URL}")
                page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
                
                # The RBI site uses a two-level navigation:
                # 1. Categories have links like BS_ViewMasterDirections.aspx?did=XXX
                # 2. Master Directions are inside those categories with links like BS_ViewMasDirections.aspx?id=YYY
                category_elements = page.locator("a[href*='BS_ViewMasterDirections.aspx?did=']").element_handles()
                category_urls = set()
                for el in category_elements:
                    href = el.get_attribute("href")
                    if href:
                        category_urls.add(urllib.parse.urljoin(self.BASE_URL, href))
                
                self.logger.info(f"Discovered {len(category_urls)} categories. Fetching Master Directions...")
                
                documents_dict = {}
                for cat_url in category_urls:
                    try:
                        page.goto(cat_url, wait_until="domcontentloaded", timeout=60000)
                        doc_elements = page.locator("a[href*='BS_ViewMasDirections.aspx?id=']").element_handles()
                        for el in doc_elements:
                            title = el.inner_text().strip()
                            href = el.get_attribute("href")
                            if title and href:
                                parsed_url = urllib.parse.urlparse(href)
                                qs = urllib.parse.parse_qs(parsed_url.query)
                                doc_id_val = qs.get("id", [""])[0]
                                if not doc_id_val:
                                    continue
                                    
                                # Standardize ID prefix and padding
                                doc_id = f"MD{doc_id_val.zfill(5)}"
                                if doc_id not in documents_dict:
                                    documents_dict[doc_id] = {
                                        "document_id": doc_id,
                                        "title": title,
                                        "href": urllib.parse.urljoin(cat_url, href)
                                    }
                    except Exception as e:
                        self.logger.warning(f"Error fetching category {cat_url}: {e}")
                        
                documents_to_process = list(documents_dict.values())
                self.logger.info(f"Discovered {len(documents_to_process)} unique Master Directions.")
                
                for doc in documents_to_process:
                    doc_id = doc["document_id"]
                    title = doc["title"]
                    href = doc["href"]
                    
                    if doc_id in downloaded_ids:
                        self.logger.info(f"Skipping already downloaded document: {doc_id}")
                        continue
                        
                    self.logger.info(f"Processing {doc_id}: {title}")
                    pdf_url = self._get_pdf_url_from_detail_page(page, href)
                    
                    if not pdf_url:
                        self.logger.warning(f"Failed to find PDF URL for {doc_id}. Skipping.")
                        continue
                        
                    pdf_path = self.pdf_dir / f"{doc_id}.pdf"
                    
                    self.logger.info(f"Downloading PDF from {pdf_url}")
                    try:
                        # Fetch the document directly using the context request API (shares cookies/headers)
                        response = context.request.get(pdf_url, timeout=60000)
                        
                        content_type = response.headers.get("content-type", "").lower()
                        if "application/pdf" not in content_type:
                            self.logger.warning(f"Invalid Content-Type for {doc_id}: {content_type}. Rejecting.")
                            continue
                            
                        with open(pdf_path, "wb") as f:
                            f.write(response.body())
                            
                        # Verify integrity
                        if not self._verify_pdf(pdf_path):
                            self.logger.warning(f"PDF Verification failed for {doc_id}. Removing file.")
                            if pdf_path.exists():
                                pdf_path.unlink()
                            continue
                            
                        sha256 = self._compute_sha256(pdf_path)
                        domain = DomainTagger.get_domain(title)
                        
                        metadata = DownloadMetadata(
                            document_id=doc_id,
                            title=title,
                            domain=domain,
                            pdf_url=pdf_url,
                            file_path=str(pdf_path.relative_to(self.base_dir)),
                            sha256_hash=sha256,
                            download_timestamp=time.time()
                        )
                        
                        self._save_metadata(metadata)
                        downloaded_ids.append(doc_id)
                        self.logger.info(f"Successfully processed and verified {doc_id} as domain '{domain}'.")
                        
                    except Exception as e:
                        self.logger.error(f"Error downloading/processing {doc_id}: {e}")
                        
            except Exception as e:
                self.logger.error(f"Critical error during execution: {e}")
            finally:
                browser.close()


if __name__ == "__main__":
    dataset_dir = project_root / "datasets" / "raw" / "master_directions"
    downloader = RBIMasterDirectionsDownloader(dataset_dir)
    downloader.run()
