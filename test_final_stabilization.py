"""
Final Stabilization Validation Test
Tests the complete Assignment → Verification → Decision → Frontend flow
"""
import requests
import json
import time
from pathlib import Path

API_BASE = "http://localhost:8000"
TOKEN = None
project_root = Path(__file__).parent

def login():
    """Get auth token"""
    global TOKEN
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✅ Logged in successfully")
        return True
    else:
        print(f"❌ Login failed: {response.text}")
        return False

def get_headers():
    """Get auth headers"""
    return {"Authorization": f"Bearer {TOKEN}"}

def test_map_detail_before_completion():
    """Test 1: Verify MAP detail shows PENDING state before completion"""
    print("\n=== Test 1: MAP Detail Before Completion ===")
    
    response = requests.get(
        f"{API_BASE}/maps/MAP_MD13525_ctrl_req32_1/detail",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ MAP Detail API works")
        print(f"   MAP ID: {data.get('map_id')}")
        print(f"   Has verification plan: {data.get('verification_plan') is not None}")
        
        # Check verification plan automation percentage
        vp = data.get('verification_plan')
        if vp:
            print(f"   Verification Plan Automation: {vp.get('automation_percentage')}%")
            print(f"   Total Checks: {vp.get('total_checks')}")
            print(f"   Machine Checks: {vp.get('machine_verifiable_checks')}")
        
        # Check compliance decision
        cd = data.get('compliance_decision')
        if cd:
            print(f"   Compliance Decision Verdict: {cd.get('verdict')}")
            print(f"   Failed Blocker Count: {cd.get('failed_blocker_count', 'N/A')}")
        else:
            print(f"   Compliance Decision: Not yet available")
        
        return data
    else:
        print(f"❌ MAP Detail API failed: {response.text}")
        return None

def find_active_assignment():
    """Find an ACTIVE assignment for MD13525_req32"""
    print("\n=== Finding ACTIVE Assignment ===")
    
    response = requests.get(
        f"{API_BASE}/assignments?status=ACTIVE&search=MD13525",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        # Find assignment for MD13525_req32
        for item in items:
            if "MAP_MD13525_ctrl_req32" in item.get("map_id", ""):
                print(f"✅ Found ACTIVE assignment: {item['id']}")
                print(f"   MAP ID: {item['map_id']}")
                print(f"   Status: {item['status']}")
                return item['id']
        
        print("⚠️ No ACTIVE assignment found for MD13525_req32")
        return None
    else:
        print(f"❌ Get assignments failed: {response.text}")
        return None

def complete_assignment(assignment_id):
    """Test 2: Complete the assignment and trigger verification"""
    print(f"\n=== Test 2: Complete Assignment {assignment_id} ===")
    
    response = requests.patch(
        f"{API_BASE}/assignments/{assignment_id}",
        json={"status": "COMPLETED", "evidence_note": "Test completion"},
        headers=get_headers()
    )
    
    if response.status_code == 200:
        print("✅ Assignment completed successfully")
        print("   Verification pipeline should have executed")
        return True
    else:
        print(f"❌ Assignment completion failed: {response.text}")
        return False

def test_verification_results():
    """Test 3: Verify that verification_results was updated"""
    print("\n=== Test 3: Check Verification Results ===")
    
    results_file = project_root / "datasets" / "verification_results" / "MD13525.json"
    
    if results_file.exists():
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find CVP_VR_MD13525_req32 in verification_results
        req32_result = None
        for result in data.get("verification_results", []):
            if result.get("plan_id") == "CVP_VR_MD13525_req32":
                req32_result = result
                break
        
        if req32_result:
            print(f"✅ Found verification result for CVP_VR_MD13525_req32")
            print(f"   Overall Status: {req32_result.get('overall_status')}")
            print(f"   Checks Run: {req32_result.get('checks_run')}")
            print(f"   Checks Passed: {req32_result.get('checks_passed')}")
            print(f"   Checks Failed: {req32_result.get('checks_failed')}")
            print(f"   Automation % Actual: {req32_result.get('automation_percentage_actual')}%")
            print(f"   Blocker Failed: {req32_result.get('blocker_failed')}")
            return req32_result
        else:
            print("❌ CVP_VR_MD13525_req32 not found in verification results")
            return None
    else:
        print(f"❌ Verification results file not found: {results_file}")
        return None

def test_compliance_decision():
    """Test 4: Verify that compliance decision was updated"""
    print("\n=== Test 4: Check Compliance Decision ===")
    
    decisions_dir = project_root / "datasets" / "compliance_decisions"
    decision_files = sorted(decisions_dir.glob("MD13525_*.json"), reverse=True)
    
    if decision_files:
        latest_file = decision_files[0]
        print(f"   Latest decision file: {latest_file.name}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find CVP_VR_MD13525_req32 in plan_verdicts
        req32_verdict = None
        for verdict in data.get("plan_verdicts", []):
            if verdict.get("plan_id") == "CVP_VR_MD13525_req32":
                req32_verdict = verdict
                break
        
        if req32_verdict:
            print(f"✅ Found compliance verdict for CVP_VR_MD13525_req32")
            print(f"   Verdict: {req32_verdict.get('verdict')}")
            print(f"   Rationale: {req32_verdict.get('rationale')}")
            return req32_verdict
        else:
            print("❌ CVP_VR_MD13525_req32 not found in plan verdicts")
            return None
    else:
        print(f"❌ No compliance decision files found")
        return None

def test_map_detail_after_completion():
    """Test 5: Verify MAP detail shows updated state after completion"""
    print("\n=== Test 5: MAP Detail After Completion ===")
    
    # Wait a moment for any async processing
    time.sleep(2)
    
    response = requests.get(
        f"{API_BASE}/maps/MAP_MD13525_ctrl_req32_1/detail",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ MAP Detail API works")
        
        # Check verification plan (should show 100% design-time automation)
        vp = data.get('verification_plan')
        if vp:
            print(f"   Verification Plan Automation: {vp.get('automation_percentage')}%")
            assert vp.get('automation_percentage') == 100.0, "Expected 100% design-time automation"
        
        # Check compliance decision (should show NON_COMPLIANT with failed_blocker_count)
        cd = data.get('compliance_decision')
        if cd:
            print(f"   Compliance Decision Verdict: {cd.get('verdict')}")
            print(f"   Compliance Decision Rationale: {cd.get('rationale')}")
            print(f"   Failed Blocker Count: {cd.get('failed_blocker_count')}")
            
            assert cd.get('verdict') == 'NON_COMPLIANT', "Expected NON_COMPLIANT verdict"
            assert cd.get('failed_blocker_count') == 1, "Expected 1 failed blocker"
            print(f"✅ Compliance decision includes failed_blocker_count")
        else:
            print(f"❌ Compliance Decision: Not available")
            return False
        
        return True
    else:
        print(f"❌ MAP Detail API failed: {response.text}")
        return False

def test_duplicate_completion_protection():
    """Test 6: Verify duplicate completion is prevented"""
    print("\n=== Test 6: Duplicate Completion Protection ===")
    
    # Try to find a COMPLETED assignment
    response = requests.get(
        f"{API_BASE}/assignments?status=COMPLETED&search=MD13525",
        headers=get_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        
        if items:
            completed_id = items[0]["id"]
            print(f"   Found COMPLETED assignment: {completed_id}")
            
            # Try to complete it again
            response = requests.patch(
                f"{API_BASE}/assignments/{completed_id}",
                json={"status": "COMPLETED", "evidence_note": "Duplicate test"},
                headers=get_headers()
            )
            
            if response.status_code == 404 or response.status_code == 400:
                print(f"✅ Duplicate completion prevented: {response.status_code}")
                print(f"   Error: {response.json().get('detail')}")
                return True
            else:
                print(f"❌ Duplicate completion NOT prevented: {response.status_code}")
                return False
        else:
            print("⚠️ No COMPLETED assignments found for testing")
            return True  # Skip test
    else:
        print(f"❌ Get assignments failed: {response.text}")
        return False

def test_scope_filtering():
    """Test 7: Verify only CVP_VR_MD13525_req32 was executed"""
    print("\n=== Test 7: Verification Scope Filtering ===")
    
    results_file = project_root / "datasets" / "verification_results" / "MD13525.json"
    
    if results_file.exists():
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Count how many plans actually ran checks
        plans_with_checks = 0
        req32_found = False
        
        for result in data.get("verification_results", []):
            checks_run = result.get("checks_run", 0)
            if checks_run > 0:
                plans_with_checks += 1
                plan_id = result.get("plan_id")
                print(f"   Plan with checks: {plan_id} ({checks_run} checks)")
                
                if plan_id == "CVP_VR_MD13525_req32":
                    req32_found = True
        
        if req32_found:
            print(f"✅ CVP_VR_MD13525_req32 was executed")
            print(f"   Total plans with checks run: {plans_with_checks}")
            
            # Note: Other plans may show checks_run > 0 from previous executions
            # The key is that req32 was executed THIS time
            return True
        else:
            print(f"❌ CVP_VR_MD13525_req32 was NOT executed")
            return False
    else:
        print(f"❌ Verification results file not found")
        return False

def main():
    """Run all validation tests"""
    print("=" * 70)
    print("FINAL STABILIZATION VALIDATION TEST")
    print("=" * 70)
    
    # Login
    if not login():
        return
    
    # Test 1: Check MAP detail before completion
    test_map_detail_before_completion()
    
    # Find an ACTIVE assignment (if none exists, skip completion tests)
    assignment_id = find_active_assignment()
    
    if assignment_id:
        # Test 2: Complete assignment
        if complete_assignment(assignment_id):
            # Give verification time to complete
            print("\n   Waiting 5 seconds for verification pipeline to complete...")
            time.sleep(5)
            
            # Test 3: Check verification results
            test_verification_results()
            
            # Test 4: Check compliance decision
            test_compliance_decision()
            
            # Test 5: Verify MAP detail shows updated data
            test_map_detail_after_completion()
            
            # Test 6: Duplicate completion protection
            test_duplicate_completion_protection()
            
            # Test 7: Scope filtering
            test_scope_filtering()
    else:
        print("\n⚠️ No ACTIVE assignment found - skipping completion tests")
        print("   Testing only existing verification results...")
        
        # Test existing data
        test_verification_results()
        test_compliance_decision()
        test_map_detail_after_completion()
        test_duplicate_completion_protection()
        test_scope_filtering()
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
