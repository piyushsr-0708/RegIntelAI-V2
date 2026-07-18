"""
Comprehensive trace of all page-related metadata fields through the pipeline.
Finds where "Source Page" shown in Session Dashboard originates.
"""

import json
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).resolve().parent
document_id = "UP20260717_0001"

# All possible page field names
PAGE_FIELD_PATTERNS = [
    "page_number", "page_numbers", "page", "pages",
    "source_page", "source_page_number", "source_pages",
    "page_index", "page_indices", 
    "page_reference", "page_references",
    "source_location", "location"
]

def find_page_fields(data, path="root", depth=0, max_depth=5):
    """Recursively find all page-related fields."""
    results = []
    
    if depth > max_depth:
        return results
    
    if isinstance(data, dict):
        for key, value in data.items():
            # Check if key matches any page pattern
            key_lower = key.lower()
            for pattern in PAGE_FIELD_PATTERNS:
                if pattern in key_lower:
                    results.append({
                        "path": f"{path}.{key}",
                        "field": key,
                        "value": value if not isinstance(value, (dict, list)) or len(str(value)) < 100 else f"{type(value).__name__}(...)",
                        "type": type(value).__name__
                    })
                    break
            
            # Recurse into nested structures
            results.extend(find_page_fields(value, f"{path}.{key}", depth + 1, max_depth))
    
    elif isinstance(data, list):
        # Sample first few items
        for idx in range(min(3, len(data))):
            results.extend(find_page_fields(data[idx], f"{path}[{idx}]", depth + 1, max_depth))
    
    return results

print("="*100)
print(f"PAGE METADATA TRACE: {document_id}")
print("="*100)
print()

stages = [
    ("parsed", "datasets/parsed"),
    ("normalized", "datasets/normalized"),
    ("hierarchy", "datasets/hierarchy"),
    ("logical_units", "datasets/logical_units"),
    ("requirements", "datasets/requirements"),
    ("enriched_requirements", "datasets/enriched_requirements"),
    ("interpreted_controls", "datasets/interpreted_controls"),
    ("reasoned_controls", "datasets/reasoned_controls"),
    ("controls", "datasets/controls"),
    ("verification_rules", "datasets/verification_rules"),
    ("verification_plans", "datasets/verification_plans"),
    ("maps", "datasets/maps"),
]

field_evolution = defaultdict(list)

for stage_name, stage_dir in stages:
    file_path = project_root / stage_dir / f"{document_id}.json"
    
    print(f"\n{'='*100}")
    print(f"STAGE: {stage_name}")
    print(f"{'='*100}")
    
    if not file_path.exists():
        print(f"  FILE NOT FOUND: {file_path}")
        continue
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find all page-related fields
        page_fields = find_page_fields(data)
        
        if not page_fields:
            print(f"  NO PAGE FIELDS FOUND")
            continue
        
        # Group by field name
        by_field = defaultdict(list)
        for pf in page_fields:
            by_field[pf["field"]].append(pf)
        
        print(f"\n  Found {len(page_fields)} page field occurrences ({len(by_field)} unique field names):")
        
        for field_name, occurrences in sorted(by_field.items()):
            print(f"\n    Field: '{field_name}' ({len(occurrences)} occurrences)")
            
            # Track evolution
            field_evolution[field_name].append(stage_name)
            
            # Show sample values
            for i, occ in enumerate(occurrences[:3]):
                print(f"      [{i+1}] {occ['path']}")
                print(f"          Type: {occ['type']}")
                print(f"          Value: {occ['value']}")
            
            if len(occurrences) > 3:
                print(f"      ... and {len(occurrences) - 3} more occurrences")
    
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n\n" + "="*100)
print("FIELD EVOLUTION SUMMARY")
print("="*100)

for field_name, stages_present in sorted(field_evolution.items()):
    print(f"\n'{field_name}':")
    print(f"  Present in stages: {' → '.join(stages_present)}")
    print(f"  First appears: {stages_present[0]}")
    print(f"  Last seen: {stages_present[-1]}")

print("\n\n" + "="*100)
print("FRONTEND STATE ANALYSIS")
print("="*100)

frontend_file = project_root / "datasets" / "frontend" / "frontend_state.json"
if frontend_file.exists():
    with open(frontend_file, 'r', encoding='utf-8') as f:
        frontend_data = json.load(f)
    
    # Find page fields in frontend
    page_fields_frontend = find_page_fields(frontend_data, max_depth=6)
    
    if page_fields_frontend:
        print(f"\nFound {len(page_fields_frontend)} page field occurrences in frontend_state.json:")
        
        by_field = defaultdict(list)
        for pf in page_fields_frontend:
            by_field[pf["field"]].append(pf)
        
        for field_name, occurrences in sorted(by_field.items()):
            print(f"\n  Field: '{field_name}' ({len(occurrences)} occurrences)")
            for i, occ in enumerate(occurrences[:5]):
                print(f"    [{i+1}] {occ['path']}")
                print(f"        Value: {occ['value']}")
    else:
        print("\nNo page fields found in frontend_state.json")
else:
    print("\nfrontend_state.json does not exist")

print("\n\n" + "="*100)
print("DATABASE MODELS ANALYSIS")
print("="*100)

# Check database models for page fields
models_dir = project_root / "backend" / "database" / "models"
if models_dir.exists():
    print("\nSearching for page-related columns in database models...")
    
    for model_file in models_dir.glob("*.py"):
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Search for page field definitions
        found_fields = []
        for pattern in PAGE_FIELD_PATTERNS:
            if pattern in content.lower():
                # Extract lines containing the pattern
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line.lower() and ('Column' in line or '=' in line):
                        found_fields.append((pattern, line.strip()))
        
        if found_fields:
            print(f"\n  {model_file.name}:")
            for pattern, line in found_fields:
                print(f"    {line}")

print("\n" + "="*100)
