"""
Trace page_number field corruption through the pipeline.

For UP20260717_0001, trace page_number at every stage to find where values > 19 appear.
"""

import json
from pathlib import Path

project_root = Path(__file__).resolve().parent
document_id = "UP20260717_0001"

stages = [
    "parsed",
    "normalized", 
    "hierarchy",
    "logical_units",
    "requirements",
    "enriched_requirements",
    "interpreted_controls",
    "reasoned_controls",
    "controls",
    "verification_rules",
    "verification_plans",
    "maps"
]

def extract_page_numbers(data, path="root"):
    """Recursively extract all page_number values from nested structure."""
    page_numbers = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "page_number":
                page_numbers.append((path, value))
            else:
                page_numbers.extend(extract_page_numbers(value, f"{path}.{key}"))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            page_numbers.extend(extract_page_numbers(item, f"{path}[{idx}]"))
    
    return page_numbers

print("="*100)
print(f"PAGE_NUMBER CORRUPTION TRACE: {document_id}")
print("="*100)
print()

for stage in stages:
    file_path = project_root / "datasets" / stage / f"{document_id}.json"
    
    if not file_path.exists():
        print(f"{stage:30s} | FILE NOT FOUND")
        continue
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract all page_number occurrences
        page_numbers = extract_page_numbers(data)
        
        if not page_numbers:
            print(f"{stage:30s} | NO page_number FIELD FOUND")
            continue
        
        # Get just the values
        values = [pn[1] for pn in page_numbers]
        
        # Check for corruption (values > 19)
        corrupted = [v for v in values if isinstance(v, int) and v > 19]
        
        min_val = min(values) if values else None
        max_val = max(values) if values else None
        count = len(values)
        
        status = "✓ CLEAN" if not corrupted else f"✗ CORRUPTED ({len(corrupted)} values > 19)"
        
        print(f"{stage:30s} | Min: {min_val:>3}, Max: {max_val:>3}, Count: {count:>4} | {status}")
        
        # If corruption detected, show first few examples
        if corrupted:
            print(f"{'':30s} | First corrupted values: {sorted(set(corrupted))[:10]}")
            
            # Show sample paths where corruption occurs
            corrupted_paths = [(path, val) for path, val in page_numbers if isinstance(val, int) and val > 19]
            print(f"{'':30s} | Sample locations:")
            for path, val in corrupted_paths[:3]:
                print(f"{'':30s} |   {path} = {val}")
    
    except Exception as e:
        print(f"{stage:30s} | ERROR: {e}")

print()
print("="*100)
print("CHECKING frontend_state.json")
print("="*100)

frontend_file = project_root / "datasets" / "frontend" / "frontend_state.json"
if frontend_file.exists():
    with open(frontend_file, 'r', encoding='utf-8') as f:
        frontend_data = json.load(f)
    
    # Check documents array
    if "documents" in frontend_data:
        for doc in frontend_data["documents"]:
            if doc.get("document_id") == document_id:
                print(f"\nDocument found in frontend_state:")
                print(f"  document_id: {doc.get('document_id')}")
                print(f"  total_pages: {doc.get('total_pages')}")
                
                # Check requirements
                if "requirements" in doc:
                    req_page_numbers = [r.get("page_number") for r in doc["requirements"] if "page_number" in r]
                    if req_page_numbers:
                        print(f"  requirements page_numbers: min={min(req_page_numbers)}, max={max(req_page_numbers)}, count={len(req_page_numbers)}")
                        corrupted = [p for p in req_page_numbers if p > 19]
                        if corrupted:
                            print(f"    ✗ CORRUPTED: {len(corrupted)} values > 19")
                            print(f"    Corrupted values: {sorted(set(corrupted))[:10]}")
                
                # Check controls
                if "controls" in doc:
                    ctrl_page_numbers = []
                    for ctrl in doc["controls"]:
                        if "page_number" in ctrl:
                            ctrl_page_numbers.append(ctrl["page_number"])
                        if "source_requirements" in ctrl:
                            for req in ctrl["source_requirements"]:
                                if "page_number" in req:
                                    ctrl_page_numbers.append(req["page_number"])
                    
                    if ctrl_page_numbers:
                        print(f"  controls page_numbers: min={min(ctrl_page_numbers)}, max={max(ctrl_page_numbers)}, count={len(ctrl_page_numbers)}")
                        corrupted = [p for p in ctrl_page_numbers if p > 19]
                        if corrupted:
                            print(f"    ✗ CORRUPTED: {len(corrupted)} values > 19")
                            print(f"    Corrupted values: {sorted(set(corrupted))[:10]}")
