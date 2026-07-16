import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.database.ingest import ingest

print("Testing ingest for UP20260715_0001...")
ingest(document_id="UP20260715_0001")

# Check database
from backend.database.session import get_db
from backend.database.models.control import ComplianceControl
from backend.database.models.map import ManagementActionPlan

db = next(get_db())
up_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).count()
up_maps = db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == "UP20260715_0001").count()

print(f"UP20260715_0001 controls after ingest: {up_controls}")
print(f"UP20260715_0001 MAPs after ingest: {up_maps}")
