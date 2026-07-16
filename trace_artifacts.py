import json
from pathlib import Path

stages = ['reasoned_controls', 'controls', 'verification_plans', 'maps']
docs = ['MD10190', 'UP20260715_0001']

print("="*70)
print("PART 1: PIPELINE ARTIFACTS")
print("="*70)

for stage in stages:
    print(f"\n{stage.upper()}:")
    for doc in docs:
        path = Path(f"datasets/{stage}/{doc}.json")
        if path.exists():
            data = json.load(open(path))
            
            # Determine count field name
            if stage == 'reasoned_controls':
                count = data.get('reasoned_control_count', 0)
            elif stage == 'controls':
                count = data.get('control_count', 0)
            elif stage == 'verification_plans':
                count = data.get('plan_count', 0)
            elif stage == 'maps':
                count = data.get('map_count', 0)
            
            # Check key fields exist
            doc_id = data.get('document_id')
            title = data.get('title')
            status = data.get('document_status', 'N/A')
            
            print(f"  {doc}:")
            print(f"    ✅ Exists | Count: {count} | Status: {status}")
            print(f"    document_id: {doc_id} | title: {title}")
        else:
            print(f"  {doc}: ❌ NOT FOUND")
