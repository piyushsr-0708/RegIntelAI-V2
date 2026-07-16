from backend.database.session import get_db
from backend.database.models.control import ComplianceControl, RequirementControlMapping
from backend.database.models.map import ManagementActionPlan
from backend.database.models.document import Document
from backend.database.models.logical_unit import LogicalUnit
from backend.database.models.requirement import Requirement
from backend.database.ingest import ingest

db = next(get_db())

print("Clearing uploaded document data...")
# Delete in correct order (respect foreign keys)
db.query(RequirementControlMapping).delete()
db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == "UP20260715_0001").delete()
db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).delete()
db.query(Requirement).filter(Requirement.requirement_id.like("UP20260715_0001%")).delete()
db.query(LogicalUnit).filter(LogicalUnit.logical_unit_id.like("UP20260715_0001%")).delete()
db.query(Document).filter(Document.document_id == "UP20260715_0001").delete()
db.commit()
print("Cleared.")

print("\nRe-ingesting UP20260715_0001...")
ingest(document_id="UP20260715_0001")

print("\nVerifying results...")
up_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).count()
up_maps = db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == "UP20260715_0001").count()
up_doc = db.query(Document).filter(Document.document_id == "UP20260715_0001").first()

print(f"UP20260715_0001 controls: {up_controls}")
print(f"UP20260715_0001 MAPs: {up_maps}")
print(f"UP20260715_0001 document exists: {up_doc is not None}")

if up_controls > 0:
    print("\n✅ SUCCESS - Controls ingested correctly!")
    # Show first 3 control IDs
    sample_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).limit(3).all()
    for ctrl in sample_controls:
        print(f"  - {ctrl.control_id}: {ctrl.name[:50]}")
else:
    print("\n❌ FAILED - Controls still not ingested")
