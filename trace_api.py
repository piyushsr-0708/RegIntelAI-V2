"""
Test if API returns UP20260715_0001 records
Requires backend running: uvicorn backend.main:app
"""
import requests

BASE_URL = "http://localhost:8000"

print("="*70)
print("PART 3: API LAYER")
print("="*70)

# Check if backend is running
try:
    response = requests.get(f"{BASE_URL}/auth/me", timeout=2)
    print("\n❌ Backend is running but requires authentication")
    print("   Cannot test API endpoints without login token")
    print("\n   To test manually:")
    print("   1. Start backend: uvicorn backend.main:app")
    print("   2. Login to get token")
    print("   3. Test endpoints:")
    print("      GET /maps?search=UP20260715_0001")
    print("      GET /assignments")
    exit(0)
except requests.exceptions.ConnectionError:
    print("\n❌ Backend not running")
    print("   Start with: uvicorn backend.main:app")
    print("\n   Then run this script again")
    exit(1)
except Exception as e:
    print(f"\n⚠️  Unexpected error: {e}")
    exit(1)
