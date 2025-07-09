#!/usr/bin/env python3
"""
Test script to diagnose Railway deployment issues
"""
import requests
import json
import time

RAILWAY_URL = "https://web-production-de0bc.up.railway.app"

def test_endpoints():
    """Test various endpoints to diagnose deployment issues"""
    
    print("🔍 Testing Railway Deployment Endpoints")
    print("=" * 50)
    
    # Test 1: Root endpoint
    print("\n1️⃣ Testing root endpoint...")
    try:
        response = requests.get(f"{RAILWAY_URL}/", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 2: Health endpoint
    print("\n2️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 3: New auth endpoint
    print("\n3️⃣ Testing new auth endpoint...")
    try:
        response = requests.post(
            f"{RAILWAY_URL}/api/auth/broker/generate-session",
            headers={"Content-Type": "application/json"},
            json={"request_token": "test", "api_key": "test", "api_secret": "test"},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 4: Legacy endpoint (should redirect)
    print("\n4️⃣ Testing legacy endpoint...")
    try:
        response = requests.post(
            f"{RAILWAY_URL}/api/broker/generate-session",
            headers={"Content-Type": "application/json"},
            json={"request_token": "test", "api_key": "test", "api_secret": "test"},
            timeout=10,
            allow_redirects=False
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code in [301, 302, 307, 308]:
            print(f"   Redirect Location: {response.headers.get('Location', 'None')}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 5: OpenAPI docs
    print("\n5️⃣ Testing OpenAPI docs...")
    try:
        response = requests.get(f"{RAILWAY_URL}/docs", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Has docs: {'swagger' in response.text.lower()}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

if __name__ == "__main__":
    test_endpoints() 