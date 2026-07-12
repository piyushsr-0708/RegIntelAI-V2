import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database.session import SessionLocal
from backend.database.services.pipeline_ingestion_service import PipelineIngestionService

def ingest():
    db = SessionLocal()
    try:
        service = PipelineIngestionService(db)
        controls_dir = project_root / "datasets" / "controls"
        if controls_dir.exists():
            print(f"Ingesting controls from {controls_dir}...")
            service.ingest_directory(controls_dir)
            print("Control ingestion complete.")
        else:
            print(f"Directory {controls_dir} not found.")

        maps_dir = project_root / "datasets" / "maps"
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
