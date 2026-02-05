#!/usr/bin/env python3
"""Test core endpoints to identify issues"""
import requests
import time
import sys

BASE_URL = "http://localhost:8000"
RUNS = 50

def test_login():
    """Test login endpoint"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"username": "admin", "password": "admin123"},
            timeout=5)
        return response.status_code == 200, response.json().get('access_token') if response.status_code == 200 else None
    except Exception as e:
        return False, None

def test_get_leads(token):
    """Test GET /api/leads"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def test_post_leads(token):
    """Test POST /api/leads"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "email": f"test-{time.time()}@example.com",
            "first_name": "Test",
            "last_name": "User"
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=data, headers=headers, timeout=5)
        return response.status_code in [200, 201]
    except:
        return False

def test_put_leads(token, lead_id="lead-1"):
    """Test PUT /api/leads/{id}"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "email": f"updated-{time.time()}@example.com",
             "first_name": "Updated",
            "last_name": "User"
        }
        response = requests.put(f"{BASE_URL}/api/leads/{lead_id}", json=data, headers=headers, timeout=5)
        print(f"PUT Response Status: {response.status_code}")
        if response.status_code >= 400:
            print(f"PUT Response Body: {response.text[:200]}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"PUT Exception: {e}")
        return False

print(f"Testing {RUNS} requests to core endpoints...")
print("=" * 60)

# Test results
results = {
    "login": {"success": 0, "fail": 0},
    "get_leads": {"success": 0, "fail": 0},
    "post_leads": {"success": 0, "fail": 0},
    "put_leads": {"success": 0, "fail": 0},
}

for i in range(RUNS):
    # Test login
    success, token = test_login()
    if success:
        results["login"]["success"] += 1
    else:
        results["login"]["fail"] += 1
        continue
    
    # Only test other endpoints if login succeeds
    if test_get_leads(token):
        results["get_leads"]["success"] += 1
    else:
        results["get_leads"]["fail"] += 1
    
    if test_post_leads(token):
        results["post_leads"]["success"] += 1
    else:
        results["post_leads"]["fail"] += 1
    
    if test_put_leads(token):
        results["put_leads"]["success"] += 1
    else:
        results["put_leads"]["fail"] += 1
    
    if (i + 1) % 10 == 0:
        print(f"Progress: {i + 1}/{RUNS}")

print("\n" + "=" * 60)
print("TEST RESULTS")
print("=" * 60)

for endpoint, counts in results.items():
    total = counts["success"] + counts["fail"]
    rate = (counts["success"] / total * 100) if total > 0 else 0
    print(f"{endpoint:15} Success: {counts['success']:3} / {total:3} ({rate:5.1f}%)")

print("\n" + "=" * 60)
overall_success = sum(v["success"] for v in results.values())
overall_total = sum(v["success"] + v["fail"] for v in results.values())
overall_rate = (overall_success / overall_total * 100) if overall_total > 0 else 0
print(f"OVERALL:        Success: {overall_success:3} / {overall_total:3} ({overall_rate:5.1f}%)")
print("=" * 60)
