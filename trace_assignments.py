from backend.database.session import get_db
from backend.database.models.map import ManagementActionPlan
from backend.database.models.department import ControlAssignment

db = next(get_db())

docs = ['MD10190', 'UP20260715_0001']

print("="*70)
print("ASSIGNMENT CREATION INVESTIGATION")
print("="*70)

for doc_id in docs:
    print(f"\n{doc_id}:")
    
    # Get MAPs for this document
    maps = db.query(ManagementActionPlan).filter(
        ManagementActionPlan.source_document_id == doc_id
    ).all()
    
    print(f"  Total MAPs: {len(maps)}")
    
    # Count by status
    draft = sum(1 for m in maps if m.status == "DRAFT")
    approved = sum(1 for m in maps if m.status == "APPROVED")
    rejected = sum(1 for m in maps if m.status == "REJECTED")
    
    print(f"    DRAFT: {draft}")
    print(f"    APPROVED: {approved}")
    print(f"    REJECTED: {rejected}")
    
    # Get assignments
    assignments = db.query(ControlAssignment).join(
        ManagementActionPlan, ControlAssignment.map_id == ManagementActionPlan.id
    ).filter(ManagementActionPlan.source_document_id == doc_id).all()
    
    print(f"  Total Assignments: {len(assignments)}")
    
    if assignments:
        print(f"    Sample assignment IDs:")
        for a in assignments[:3]:
            map_status = db.query(ManagementActionPlan).filter_by(id=a.map_id).first().status
            print(f"      {a.id} (MAP status: {map_status})")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("Assignments are created when MAPs are APPROVED via:")
print("  POST /maps/{map_id}/approve")
print("\nWorkflow:")
print("  1. MAP ingested with status='DRAFT'")
print("  2. User reviews MAP in frontend")
print("  3. User clicks 'Approve'")
print("  4. API calls AssignmentService.approve_map()")
print("  5. ControlAssignment created automatically")
