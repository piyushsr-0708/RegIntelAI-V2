from backend.database.session import get_db
from backend.database.models.document import Document
from backend.database.models.requirement import Requirement
from backend.database.models.control import ComplianceControl
from backend.database.models.map import ManagementActionPlan
from backend.database.models.department import ControlAssignment

db = next(get_db())

docs = ['MD10190', 'UP20260715_0001']

print("="*70)
print("PART 2: DATABASE INGEST")
print("="*70)

for doc_id in docs:
    print(f"\n{doc_id}:")
    
    # Document table
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    print(f"  Document table: {'✅ YES' if doc else '❌ NO'}")
    if doc:
        print(f"    status: {doc.status}")
    
    # Requirement table  
    reqs = db.query(Requirement).filter(Requirement.requirement_id.like(f"{doc_id}%")).count()
    print(f"  Requirement table: {'✅ YES' if reqs > 0 else '❌ NO'} ({reqs} records)")
    
    # Control table (by control_id prefix)
    ctrls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like(f"{doc_id}%")).count()
    print(f"  Control table (prefix): {'✅ YES' if ctrls > 0 else '❌ NO'} ({ctrls} records)")
    
    # MAP table (by source_document_id)
    maps = db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == doc_id).count()
    print(f"  MAP table: {'✅ YES' if maps > 0 else '❌ NO'} ({maps} records)")
    
    # Assignment table
    if doc:
        assignments = db.query(ControlAssignment).join(
            ManagementActionPlan, ControlAssignment.map_id == ManagementActionPlan.id
        ).filter(ManagementActionPlan.source_document_id == doc_id).count()
        print(f"  Assignment table: {'✅ YES' if assignments > 0 else '❌ NO'} ({assignments} records)")

# Check for hashed controls
print("\n" + "="*70)
print("HASHED CONTROL CHECK:")
hashed = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("CTRL_%")).count()
print(f"  Hashed controls (CTRL_* prefix): {hashed} records")

if hashed > 0:
    sample = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("CTRL_%")).first()
    print(f"  Sample hashed control_id: {sample.control_id}")
    print(f"  Sample control name: {sample.name[:60]}")
