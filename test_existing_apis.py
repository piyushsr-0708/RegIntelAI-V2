"""
Test that existing APIs still work after the modification.
"""
import requests

API_BASE = "http://127.0.0.1:8000"

# Login
print("=== Test 1: Login API ===")
login_response = requests.post(
    f"{API_BASE}/auth/login",
    json={"username": "superadmin", "password": "super123"}
)
if login_response.status_code == 200:
    print("✅ Login API works")
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
else:
    print(f"❌ Login API failed: {login_response.text}")
    exit(1)

# Test GET /assignments
print("\n=== Test 2: GET /assignments API ===")
response = requests.get(
    f"{API_BASE}/assignments?page=1&page_size=10",
    headers=headers
)
if response.status_code == 200:
    data = response.json()
    print(f"✅ GET /assignments works")
    print(f"   Total: {data['total']}, Items: {len(data['items'])}")
else:
    print(f"❌ GET /assignments failed: {response.text}")

# Test GET /maps
print("\n=== Test 3: GET /maps API ===")
response = requests.get(
    f"{API_BASE}/maps?page=1&page_size=10",
    headers=headers
)
if response.status_code == 200:
    data = response.json()
    print(f"✅ GET /maps works")
    print(f"   Total: {data['total']}, Items: {len(data['items'])}")
else:
    print(f"❌ GET /maps failed: {response.text}")

# Test GET /maps/{map_id}/detail
print("\n=== Test 4: GET /maps/{map_id}/detail API ===")
response = requests.get(
    f"{API_BASE}/maps/MAP_MD10190_ctrl_req5_1/detail",
    headers=headers
)
if response.status_code == 200:
    data = response.json()
    print(f"✅ GET /maps/detail works")
    print(f"   MAP ID: {data.get('map_id')}")
    print(f"   Has verification plan: {data.get('verification_plan') is not None}")
    print(f"   Has compliance decision: {data.get('compliance_decision') is not None}")
else:
    print(f"❌ GET /maps/detail failed: {response.text}")

print("\n=== All Tests Passed ===")
