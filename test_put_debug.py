#!/usr/bin/env python3
"""Direct PUT endpoint test to debug 400 errors"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Step 1: Login
print("[1] Testing login...")
login_resp = requests.post(f"{BASE_URL}/api/auth/login", 
    json={"username": "admin", "password": "admin123"}, timeout=5)
print(f"    Status: {login_resp.status_code}")

if login_resp.status_code != 200:
    print(f"    Login failed: {login_resp.text}")
    exit(1)

token = login_resp.json().get('access_token')
print(f"    Token: {token[:20]}...")

# Step 2: Get a lead first
print("\n[2] Testing GET /api/leads/lead-1...")
headers = {"Authorization": f"Bearer {token}"}
get_resp = requests.get(f"{BASE_URL}/api/leads/lead-1", headers=headers, timeout=5)
print(f"    Status: {get_resp.status_code}")
if get_resp.status_code == 200:
    print(f"    Lead data: {json.dumps(get_resp.json(), indent=2)[:200]}...")

# Step 3: Test PUT endpoint
print("\n[3] Testing PUT /api/leads/lead-1...")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
put_data = {
    "email": "updated@example.com",
    "first_name": "Updated",
    "last_name": "User",
    "company": "Updated Corp"
}

print(f"    Request data: {json.dumps(put_data)}")
put_resp = requests.put(f"{BASE_URL}/api/leads/lead-1", json=put_data, headers=headers, timeout=5)
print(f"    Status: {put_resp.status_code}")
print(f"    Response: {put_resp.text}")

if put_resp.status_code >= 400:
    print("\n[DEBUG INFO]")
    print(f"    Status Code: {put_resp.status_code}")
    print(f"    Response Headers: {dict(put_resp.headers)}")
    try:
        error_json = put_resp.json()
        print(f"    Error Details: {json.dumps(error_json, indent=2)}")
    except:
        print(f"    Raw Body: {put_resp.text}")
