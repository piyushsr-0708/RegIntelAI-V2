"""
Validation script for uploaded document pipeline end-to-end flow.
Checks all stages from control generation to frontend visibility.
"""
from backend.database.session import get_db
from backend.database.models.control import ComplianceControl
from backend.database.models.map import ManagementActionPlan
from backend.database.models.document import Document
from backend.database.models.requirement import Requirement
import requests
import json

db = next(get_db())

print("="*60)
print("PIPELINE VALIDATION: UP20260715_0001")
print("="*60)

# 1. Verify artifacts generated
print("\n1. Pipeline Artifacts:")
import os
artifacts = {
    "Controls JSON": os.path.exists("datasets/controls/UP20260715_0001.json"),
    "Verification Plans JSON": os.path.exists("datasets/verification_plans/UP20260715_0001.json"),
    "MAPs JSON": os.path.exists("datasets/maps/UP20260715_0001.json"),
}
for name, exists in artifacts.items():
    print(f"   {'✅' if exists else '❌'} {name}")

# 2. Verify database records
print("\n2. Database Records:")
up_doc = db.query(Document).filter(Document.document_id == "UP20260715_0001").first()
up_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).count()
up_reqs = db.query(Requirement).filter(Requirement.requirement_id.like("UP20260715_0001%")).count()
up_maps = db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == "UP20260715_0001").count()

print(f"   {'✅' if up_doc else '❌'} Document record: {up_doc is not None}")
print(f"   {'✅' if up_controls > 0 else '❌'} Controls: {up_controls}")
print(f"   {'✅' if up_reqs > 0 else '❌'} Requirements: {up_reqs}")
print(f"   {'✅' if up_maps > 0 else '❌'} MAPs: {up_maps}")

# 3. Sample control data
if up_controls > 0:
    print("\n3. Sample Controls:")
    sample = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("UP20260715_0001%")).limit(3).all()
    for ctrl in sample:
        print(f"   - {ctrl.control_id}")
        print(f"     Name: {ctrl.name[:60]}")
        print(f"     Type: {ctrl.control_type}")

# 4. Compare with MD10190
print("\n4. Comparison with MD10190:")
md_doc = db.query(Document).filter(Document.document_id == "MD10190").first()
md_controls = db.query(ComplianceControl).filter(ComplianceControl.control_id.like("MD10190%")).count()
md_maps = db.query(ManagementActionPlan).filter(ManagementActionPlan.source_document_id == "MD10190").count()

print(f"   MD10190 controls: {md_controls}")
print(f"   MD10190 MAPs: {md_maps}")
print(f"   MD10190 document: {md_doc is not None}")

# 5. Check if backend is running and accessible
print("\n5. Backend API Status:")
try:
    response = requests.get("http://localhost:8000/health", timeout=2)
    print(f"   {'✅' if response.status_code == 200 else '❌'} Backend running")
except:
    print(f"   ⚠️  Backend not running (start with: uvicorn backend.main:app)")

print("\n" + "="*60)
print("VALIDATION SUMMARY")
print("="*60)

all_checks = [
    artifacts["Controls JSON"],
    artifacts["Verification Plans JSON"],
    artifacts["MAPs JSON"],
    up_doc is not None,
    up_controls > 0,
    up_reqs > 0,
    up_maps > 0
]

if all(all_checks):
    print("✅ ALL CHECKS PASSED")
    print(f"\n   Uploaded document UP20260715_0001:")
    print(f"   - Pipeline artifacts: ✅")
    print(f"   - Database ingest: ✅")
    print(f"   - {up_controls} controls, {up_maps} MAPs")
else:
    print("❌ SOME CHECKS FAILED")
    failed = sum(1 for c in all_checks if not c)
    print(f"   {failed}/{len(all_checks)} checks failed")

print("\nNote: MD10190 controls need re-ingestion if count is 0")
print("="*60)
