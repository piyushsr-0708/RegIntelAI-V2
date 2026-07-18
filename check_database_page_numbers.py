"""
Check page_number field in database for UP20260717_0001.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup database connection
db_path = project_root / "backend" / "database.db"
engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)
session = Session()

document_id = "UP20260717_0001"

print("="*100)
print(f"DATABASE PAGE_NUMBER CHECK: {document_id}")
print("="*100)
print()

# Check requirements table
print("REQUIREMENTS TABLE:")
result = session.execute(
    text("SELECT requirement_id, page_number FROM requirements WHERE document_id = :doc_id ORDER BY requirement_id"),
    {"doc_id": document_id}
)
rows = result.fetchall()
if rows:
    page_numbers = [r[1] for r in rows if r[1] is not None]
    if page_numbers:
        print(f"  Found {len(page_numbers)} requirements with page_number")
        print(f"  Min: {min(page_numbers)}, Max: {max(page_numbers)}")
        corrupted = [p for p in page_numbers if p > 19]
        if corrupted:
            print(f"  ✗ CORRUPTED: {len(corrupted)} values > 19")
            print(f"  Corrupted values: {sorted(set(corrupted))[:20]}")
            # Show sample requirement_ids
            print(f"  Sample corrupted requirements:")
            for req_id, page_num in rows:
                if page_num and page_num > 19:
                    print(f"    {req_id}: page_number={page_num}")
                    if len([r for r in rows if r[1] and r[1] > 19 and rows.index(r) <= rows.index((req_id, page_num))]) >= 5:
                        break
        else:
            print(f"  ✓ CLEAN")
    else:
        print(f"  No page_number values found")
else:
    print(f"  No requirements found for {document_id}")

print()

# Check controls table
print("CONTROLS TABLE:")
result = session.execute(
    text("SELECT control_id, page_number FROM controls WHERE document_id = :doc_id ORDER BY control_id"),
    {"doc_id": document_id}
)
rows = result.fetchall()
if rows:
    page_numbers = [r[1] for r in rows if r[1] is not None]
    if page_numbers:
        print(f"  Found {len(page_numbers)} controls with page_number")
        print(f"  Min: {min(page_numbers)}, Max: {max(page_numbers)}")
        corrupted = [p for p in page_numbers if p > 19]
        if corrupted:
            print(f"  ✗ CORRUPTED: {len(corrupted)} values > 19")
            print(f"  Corrupted values: {sorted(set(corrupted))[:20]}")
            print(f"  Sample corrupted controls:")
            for ctrl_id, page_num in rows:
                if page_num and page_num > 19:
                    print(f"    {ctrl_id}: page_number={page_num}")
                    if len([r for r in rows if r[1] and r[1] > 19 and rows.index(r) <= rows.index((ctrl_id, page_num))]) >= 5:
                        break
        else:
            print(f"  ✓ CLEAN")
    else:
        print(f"  No page_number values found")
else:
    print(f"  No controls found for {document_id}")

print()

# Check requirement_control_map table
print("REQUIREMENT_CONTROL_MAP TABLE:")
result = session.execute(
    text("SELECT id, requirement_id, control_id FROM requirement_control_map WHERE document_id = :doc_id LIMIT 10"),
    {"doc_id": document_id}
)
rows = result.fetchall()
if rows:
    print(f"  Found {len(rows)} mappings (showing first 10)")
    for row in rows[:5]:
        print(f"    Map ID: {row[0]}, Requirement: {row[1]}, Control: {row[2]}")
else:
    print(f"  No mappings found for {document_id}")

session.close()

print()
print("="*100)
