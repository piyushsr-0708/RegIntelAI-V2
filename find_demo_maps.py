"""
Find MAPs suitable for demonstrating Verification Agent automated reasoning.
Inspection only - no modifications.
"""

import json
import os
from pathlib import Path

def load_json(filepath):
    """Load JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def verify_map_exists(document_id, requirement_id, controls_dir):
    """Verify that a control exists for this requirement in the controls dataset."""
    control_file = controls_dir / f"{document_id}.json"
    if not control_file.exists():
        return False
    
    data = load_json(control_file)
    if not data:
        return False
    
    # Check if any control matches this requirement_id
    controls = data.get('controls', [])
    for control in controls:
        if control.get('requirement_id') == requirement_id:
            return True
    return False

def find_demo_maps():
    """Find MAPs suitable for Verification Agent demonstration."""
    
    base_dir = Path('.')
    vp_dir = base_dir / 'datasets' / 'verification_plans'
    controls_dir = base_dir / 'datasets' / 'controls'
    
    # Categories
    fully_automated = []  # automation_percentage = 100, machine_verifiable_checks = total_checks
    mixed_automation = []  # machine_verifiable_checks > 0 AND manual_checks > 0
    fully_manual = []  # machine_verifiable_checks = 0
    
    # Sample from multiple documents
    sample_docs = ['MD12927', 'MD12969', 'MD13525', 'MD13526']
    
    for doc_id in sample_docs:
        vp_file = vp_dir / f"{doc_id}.json"
        if not vp_file.exists():
            continue
        
        data = load_json(vp_file)
        if not data:
            continue
        
        plans = data.get('verification_plans', [])
        
        for plan in plans[:15]:  # Limit per document
            req_id = plan.get('requirement_id')
            
            # Verify MAP exists in controls
            if not verify_map_exists(doc_id, req_id, controls_dir):
                continue
            
            total = plan.get('total_checks', 0)
            machine = plan.get('machine_verifiable_checks', 0)
            manual = total - machine
            auto_pct = plan.get('automation_percentage', 0)
            
            map_entry = {
                'map_id': f"{doc_id}_{req_id}",
                'document_id': doc_id,
                'requirement_id': req_id,
                'control_name': plan.get('control_name', 'Unknown'),
                'plan_id': plan.get('plan_id'),
                'automation_percentage': auto_pct,
                'total_checks': total,
                'machine_verifiable_checks': machine,
                'manual_checks': manual,
                'criticality': plan.get('criticality', 'UNKNOWN')
            }
            
            # Categorize
            if machine > 0 and manual == 0:
                map_entry['expected_verdict'] = 'GO'
                if len(fully_automated) < 5:  # Limit samples
                    fully_automated.append(map_entry)
            elif machine > 0 and manual > 0:
                map_entry['expected_verdict'] = 'ESCALATE (mixed)'
                if len(mixed_automation) < 5:
                    mixed_automation.append(map_entry)
            elif machine == 0 and total > 0:
                map_entry['expected_verdict'] = 'ESCALATE (manual)'
                if len(fully_manual) < 5:
                    fully_manual.append(map_entry)
    
    # Output results
    print("="*80)
    print("VERIFICATION AGENT DEMONSTRATION MAPS")
    print("="*80)
    print()
    
    print("A. FULLY AUTOMATED (Expected Verdict: GO)")
    print("-" * 80)
    for i, m in enumerate(fully_automated, 1):
        print(f"\n{i}. MAP ID: {m['map_id']}")
        print(f"   Document ID: {m['document_id']}")
        print(f"   Requirement ID: {m['requirement_id']}")
        print(f"   Control Name: {m['control_name']}")
        print(f"   Verification Plan ID: {m['plan_id']}")
        print(f"   Automation Percentage: {m['automation_percentage']}%")
        print(f"   Total Checks: {m['total_checks']}")
        print(f"   Machine-Verifiable Checks: {m['machine_verifiable_checks']}")
        print(f"   Manual Checks: {m['manual_checks']}")
        print(f"   Criticality: {m['criticality']}")
        print(f"   Expected Verdict: {m['expected_verdict']}")
    
    print("\n" + "="*80)
    print("B. MIXED AUTOMATION (Expected Verdict: ESCALATE)")
    print("-" * 80)
    for i, m in enumerate(mixed_automation, 1):
        print(f"\n{i}. MAP ID: {m['map_id']}")
        print(f"   Document ID: {m['document_id']}")
        print(f"   Requirement ID: {m['requirement_id']}")
        print(f"   Control Name: {m['control_name']}")
        print(f"   Verification Plan ID: {m['plan_id']}")
        print(f"   Automation Percentage: {m['automation_percentage']}%")
        print(f"   Total Checks: {m['total_checks']}")
        print(f"   Machine-Verifiable Checks: {m['machine_verifiable_checks']}")
        print(f"   Manual Checks: {m['manual_checks']}")
        print(f"   Criticality: {m['criticality']}")
        print(f"   Expected Verdict: {m['expected_verdict']}")
    
    print("\n" + "="*80)
    print("C. FULLY MANUAL (Expected Verdict: ESCALATE)")
    print("-" * 80)
    for i, m in enumerate(fully_manual, 1):
        print(f"\n{i}. MAP ID: {m['map_id']}")
        print(f"   Document ID: {m['document_id']}")
        print(f"   Requirement ID: {m['requirement_id']}")
        print(f"   Control Name: {m['control_name']}")
        print(f"   Verification Plan ID: {m['plan_id']}")
        print(f"   Automation Percentage: {m['automation_percentage']}%")
        print(f"   Total Checks: {m['total_checks']}")
        print(f"   Machine-Verifiable Checks: {m['machine_verifiable_checks']}")
        print(f"   Manual Checks: {m['manual_checks']}")
        print(f"   Criticality: {m['criticality']}")
        print(f"   Expected Verdict: {m['expected_verdict']}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Fully Automated MAPs Found: {len(fully_automated)}")
    print(f"Mixed Automation MAPs Found: {len(mixed_automation)}")
    print(f"Fully Manual MAPs Found: {len(fully_manual)}")
    print(f"Total Demonstration MAPs: {len(fully_automated) + len(mixed_automation) + len(fully_manual)}")
    print()
    print("All MAPs verified to exist in:")
    print("  - datasets/verification_plans/")
    print("  - datasets/controls/")
    print()
    print("Assignment Workflow:")
    print("  - All MAPs can be assigned through normal Assignment Center workflow")
    print("  - Verification Agent will process them automatically upon completion")
    print("="*80)

if __name__ == "__main__":
    find_demo_maps()
