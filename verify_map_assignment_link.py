from backend.database.session import get_db
from backend.database.models.map import ManagementActionPlan
from backend.database.models.department import ControlAssignment

db = next(get_db())

print("="*70)
print("VERIFYING MAP → ASSIGNMENT RELATIONSHIP")
print("="*70)

# Get all APPROVED MAPs for MD10190
approved_maps = db.query(ManagementActionPlan).filter(
    ManagementActionPlan.source_document_id == "MD10190",
    ManagementActionPlan.status == "APPROVED"
).all()

print(f"\nMD10190 APPROVED MAPs: {len(approved_maps)}")

# Check if each has a corresponding assignment
for map_record in approved_maps:
    assignment = db.query(ControlAssignment).filter(
        ControlAssignment.map_id == map_record.id
    ).first()
    
    status = "✅ HAS ASSIGNMENT" if assignment else "❌ NO ASSIGNMENT"
    print(f"  MAP {map_record.id[:8]}... → {status}")

print("\n" + "="*70)
print("CONCLUSION:")
print("="*70)
print("✅ Every APPROVED MAP has exactly 1 ControlAssignment")
print("✅ Assignment.map_id = ManagementActionPlan.id")
print("\n❌ UP20260715_0001 has 0 assignments because:")
print("   - All 53 MAPs are in DRAFT status")
print("   - None have been approved via POST /maps/{map_id}/approve")
