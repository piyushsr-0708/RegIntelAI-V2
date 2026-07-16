import sys
import json
from pathlib import Path
from typing import Optional

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.session import SessionLocal
from backend.database.services.pipeline_ingestion_service import PipelineIngestionService

def ingest(document_id: Optional[str] = None):
    """
    Ingest controls and MAPs into the database.
    
    Args:
        document_id: Optional document ID to ingest. If provided, only ingests that document.
                    If None, ingests all documents in the directories (bulk mode).
    """
    db = SessionLocal()
    try:
        service = PipelineIngestionService(db)
        controls_dir = project_root / "datasets" / "controls"
        maps_dir = project_root / "datasets" / "maps"
        
        # Document-scoped ingestion
        if document_id:
            # Ingest single document's controls
            controls_file = controls_dir / f"{document_id}.json"
            if controls_file.exists():
                print(f"Ingesting controls for {document_id}...")
                with open(controls_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    service.ingest_document(data)
                print(f"Control ingestion complete for {document_id}.")
            else:
                print(f"Controls file not found: {controls_file}")
            
            # Ingest single document's MAPs
            maps_file = maps_dir / f"{document_id}.json"
            if maps_file.exists():
                print(f"Ingesting MAPs for {document_id}...")
                with open(maps_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    service.ingest_maps(data)
                print(f"MAP ingestion complete for {document_id}.")
            else:
                print(f"MAPs file not found: {maps_file}")
        
        # Bulk ingestion (original behavior)
        else:
            if controls_dir.exists():
                print(f"Ingesting controls from {controls_dir}...")
                service.ingest_directory(controls_dir)
                print("Control ingestion complete.")
            else:
                print(f"Directory {controls_dir} not found.")

            if maps_dir.exists():
                print(f"Ingesting MAPs from {maps_dir}...")
                service.ingest_maps_directory(maps_dir)
                print("MAP ingestion complete.")
            else:
                print(f"Directory {maps_dir} not found.")
    finally:
        db.close()

if __name__ == "__main__":
    ingest()
