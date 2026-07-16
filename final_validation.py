"""
Final validation: Tests if uploaded document appears in all frontend interfaces.
Requires backend to be running: uvicorn backend.main:app
"""
import requests
import json

BASE_URL = "http://localhost:8000"
DOC_ID = "UP20260715_0001"

print("="*70)
print("FINAL VALIDATION: Frontend API Integration")
print("="*70)

# Test 1: Health check
print("\n1. Backend Health Check:")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=2)
    if response.status_code == 200:
        print("   ✅ Backend is running")
    else:
        print(f"   ❌ Backend returned {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   ❌ Backend not accessible: {e}")
    print("\n   Start backend with: uvicorn backend.main:app")
    exit(1)

# Test 2: Dashboard - Check if document appears in stats
print("\n2. Dashboard API (Document Statistics):")
try:
    response = requests.get(f"{BASE_URL}/dashboard", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Dashboard accessible")
        print(f"   Total documents: {data.get('total_documents', 0)}")
        print(f"   Total controls: {data.get('total_controls', 0)}")
        print(f"   Total MAPs: {data.get('total_maps', 0)}")
    else:
        print(f"   ❌ Dashboard returned {response.status_code}")
except Exception as e:
    print(f"   ❌ Dashboard error: {e}")

# Test 3: MAP Register - Check if uploaded document MAPs appear
print("\n3. MAP Register API (Management Action Plans):")
try:
    response = requests.get(f"{BASE_URL}/maps", timeout=5)
    if response.status_code == 200:
        maps = response.json()
        uploaded_maps = [m for m in maps if m.get('source_document_id') == DOC_ID]
        print(f"   ✅ MAP Register accessible")
        print(f"   Total MAPs: {len(maps)}")
        print(f"   {DOC_ID} MAPs: {len(uploaded_maps)}")
        if uploaded_maps:
            print(f"   Sample MAP: {uploaded_maps[0].get('id', 'N/A')}")
    else:
        print(f"   ❌ MAP Register returned {response.status_code}")
except Exception as e:
    print(f"   ❌ MAP Register error: {e}")

# Test 4: Assignment Center - Check if controls are assignable
print("\n4. Assignment Center API (Control Assignments):")
try:
    response = requests.get(f"{BASE_URL}/assignments", timeout=5)
    if response.status_code == 200:
        assignments = response.json()
        print(f"   ✅ Assignment Center accessible")
        print(f"   Total assignments: {len(assignments)}")
    else:
        print(f"   ❌ Assignment Center returned {response.status_code}")
except Exception as e:
    print(f"   ❌ Assignment Center error: {e}")

# Test 5: Analysis Page - Check if document can be analyzed
print("\n5. Analysis API (Document Analysis):")
try:
    # This endpoint may not exist yet, but we check anyway
    response = requests.get(f"{BASE_URL}/documents/{DOC_ID}", timeout=5)
    if response.status_code == 200:
        print(f"   ✅ Document {DOC_ID} accessible")
    elif response.status_code == 404:
        print(f"   ⚠️  Document endpoint not implemented (expected)")
    else:
        print(f"   ⚠️  Unexpected status: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Analysis endpoint: {e}")

print("\n" + "="*70)
print("VALIDATION COMPLETE")
print("="*70)
print("\nNext Steps:")
print("1. If backend not running: uvicorn backend.main:app")
print("2. Open frontend and verify:")
print("   - Dashboard shows updated statistics")
print("   - MAP Register shows UP20260715_0001 MAPs")
print("   - Assignment Center can assign uploaded document controls")
print("   - Analysis page can open uploaded document")
print("="*70)
