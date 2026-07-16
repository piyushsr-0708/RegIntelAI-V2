from backend.database.session import get_db
from backend.database.models.control import ComplianceControl

db = next(get_db())

# Check all controls
all_controls = db.query(ComplianceControl).all()
print(f"Total controls in database: {len(all_controls)}")

# Show first 5 control_ids
for ctrl in all_controls[:5]:
    print(f"  - {ctrl.control_id}: {ctrl.name}")

# Count controls by prefix pattern
hashed_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("CTRL_%")).count()
md_prefix_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("MD10190%")).count()
up_prefix_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).count()

print(f"\nControls with CTRL_ prefix: {hashed_controls}")
print(f"Controls with MD10190 prefix: {md_prefix_controls}")
print(f"Controls with UP20260715_0001 prefix: {up_prefix_controls}")
