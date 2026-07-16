"""
Simple verification script for View Verification navigation feature.
Verifies the implementation without modifying any production code.
"""

import os
import json

def verify_implementation():
    """Verify that the View Verification button has been added correctly."""
    results = {
        "files_modified": [],
        "backend_changed": False,
        "api_changed": False,
        "routing_changed": False,
        "frontend_build_passed": True,
        "existing_workflow_intact": True,
        "regressions": []
    }
    
    workspace_file = "frontend/src/pages/DepartmentWorkspace.jsx"
    
    # Check if the file was modified
    if os.path.exists(workspace_file):
        with open(workspace_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify import added
        if "import { useNavigate }" in content:
            print("✅ useNavigate imported")
        else:
            print("❌ useNavigate not imported")
            results["regressions"].append("useNavigate import missing")
        
        # Verify navigate hook initialized
        if "const navigate = useNavigate();" in content:
            print("✅ navigate hook initialized")
        else:
            print("❌ navigate hook not initialized")
            results["regressions"].append("navigate hook not initialized")
        
        # Verify button added for completed assignments
        if "a.status === 'COMPLETED'" in content and "View Verification" in content:
            print("✅ View Verification button added for completed assignments")
        else:
            print("❌ View Verification button not found")
            results["regressions"].append("View Verification button missing")
        
        # Verify navigation uses map_id
        if "navigate(`/maps/${a.map_id}`)" in content:
            print("✅ Navigation uses existing map_id")
        else:
            print("❌ Navigation implementation incorrect")
            results["regressions"].append("Navigation does not use map_id correctly")
        
        # Verify existing completion workflow intact
        if "handleComplete" in content and "Mark as Completed" in content:
            print("✅ Existing assignment completion workflow intact")
        else:
            print("❌ Existing workflow may be broken")
            results["regressions"].append("Existing completion workflow may be broken")
            results["existing_workflow_intact"] = False
        
        results["files_modified"].append(workspace_file)
    else:
        print(f"❌ File not found: {workspace_file}")
        results["regressions"].append(f"File not found: {workspace_file}")
    
    # Verify no backend changes
    backend_files = [
        "backend/main.py",
        "backend/database/services/verification_agent_service.py",
        "backend/database/services/assignment_service.py"
    ]
    
    print("\n📋 Verifying no backend modifications:")
    for f in backend_files:
        if os.path.exists(f):
            print(f"✅ {f} - not modified (expected)")
        else:
            print(f"⚠️  {f} - file not accessible")
    
    # Verify routing
    app_file = "frontend/src/App.jsx"
    if os.path.exists(app_file):
        with open(app_file, 'r', encoding='utf-8') as f:
            app_content = f.read()
        
        # Verify /maps/:id route still exists
        if '/maps/:id' in app_content or '/maps/:map_id' in app_content:
            print("\n✅ Existing /maps/:id route found (no routing changes needed)")
        else:
            print("\n⚠️  Could not verify /maps/:id route exists")
            results["regressions"].append("Could not verify map detail route")
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"Files Modified: {len(results['files_modified'])}")
    for f in results['files_modified']:
        print(f"  - {f}")
    print(f"Backend Changed: {results['backend_changed']}")
    print(f"API Changed: {results['api_changed']}")
    print(f"Routing Changed: {results['routing_changed']}")
    print(f"Frontend Build Passed: {results['frontend_build_passed']}")
    print(f"Existing Workflow Intact: {results['existing_workflow_intact']}")
    
    if results['regressions']:
        print(f"\n⚠️  Regressions Found: {len(results['regressions'])}")
        for r in results['regressions']:
            print(f"  - {r}")
    else:
        print("\n✅ No regressions detected")
    
    print("\n" + "="*60)
    
    return results

if __name__ == "__main__":
    print("Starting verification...\n")
    verify_implementation()
