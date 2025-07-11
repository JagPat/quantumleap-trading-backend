#!/usr/bin/env python3
"""
Complete Deployment Test for QuantumLeap Trading Backend
Tests all critical endpoints and OAuth flow functionality
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://web-production-de0bc.up.railway.app"
FRONTEND_URL = "http://localhost:5173"
API_KEY = "f9s0gfyeu35adwul"
API_SECRET = "qf6a5l90mtf3nm4us3xpnoo4tk9kdbi7"

def test_endpoint(name, url, method="GET", data=None, headers=None, expected_status=200):
    """Test an endpoint and return the result"""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        status_ok = response.status_code == expected_status
        
        print(f"{'✅' if status_ok else '❌'} {name}")
        print(f"   URL: {url}")
        print(f"   Status: {response.status_code} (expected {expected_status})")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        elif response.status_code in [307, 302]:
            print(f"   Redirect to: {response.headers.get('Location', 'N/A')}")
        else:
            print(f"   Error: {response.text[:200]}...")
        
        print()
        return status_ok, response
        
    except Exception as e:
        print(f"❌ {name}")
        print(f"   URL: {url}")
        print(f"   Error: {str(e)}")
        print()
        return False, None

def main():
    """Run all deployment tests"""
    print("🚀 QuantumLeap Trading Backend - Complete Deployment Test")
    print("=" * 60)
    print(f"Testing deployment at: {BASE_URL}")
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    results = []
    
    # 1. Basic Health Checks
    print("📊 BASIC HEALTH CHECKS")
    print("-" * 30)
    
    results.append(test_endpoint(
        "Health Check",
        f"{BASE_URL}/health"
    ))
    
    results.append(test_endpoint(
        "Root Endpoint",
        f"{BASE_URL}/"
    ))
    
    # 2. Authentication Endpoints
    print("🔐 AUTHENTICATION ENDPOINTS")
    print("-" * 30)
    
    # Test OAuth callback redirect
    results.append(test_endpoint(
        "OAuth Callback (Redirect)",
        f"{BASE_URL}/api/auth/broker/callback?request_token=test_token&action=login",
        expected_status=307
    ))
    
    # Test session endpoint (should return unauthorized)
    results.append(test_endpoint(
        "Session Endpoint (Unauthorized)",
        f"{BASE_URL}/api/auth/broker/session?user_id=test_user",
        expected_status=401
    ))
    
    # Test OAuth setup endpoint
    results.append(test_endpoint(
        "OAuth Test Setup",
        f"{BASE_URL}/api/auth/broker/test-oauth?api_key={API_KEY}&api_secret={API_SECRET}",
        method="POST"
    ))
    
    # 3. Portfolio Endpoints (should return unauthorized)
    print("📈 PORTFOLIO ENDPOINTS")
    print("-" * 30)
    
    results.append(test_endpoint(
        "Portfolio Data (Unauthorized)",
        f"{BASE_URL}/api/portfolio/data",
        expected_status=401
    ))
    
    results.append(test_endpoint(
        "Portfolio Summary (Unauthorized)",
        f"{BASE_URL}/api/portfolio/summary",
        expected_status=401
    ))
    
    results.append(test_endpoint(
        "Holdings (Unauthorized)",
        f"{BASE_URL}/api/portfolio/holdings",
        expected_status=401
    ))
    
    results.append(test_endpoint(
        "Positions (Unauthorized)",
        f"{BASE_URL}/api/portfolio/positions",
        expected_status=401
    ))
    
    # 4. Test with Authorization Header
    print("🔑 AUTHORIZED ENDPOINTS")
    print("-" * 30)
    
    auth_headers = {
        "Authorization": f"token {API_KEY}:dummy_access_token",
        "X-User-ID": "test_user"
    }
    
    results.append(test_endpoint(
        "Portfolio Data (With Auth Header)",
        f"{BASE_URL}/api/portfolio/data",
        headers=auth_headers,
        expected_status=401  # Should still be unauthorized without valid session
    ))
    
    # 5. Summary
    print("📋 TEST SUMMARY")
    print("-" * 30)
    
    passed = sum(1 for result, _ in results if result)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total} tests")
    print(f"❌ Failed: {total - passed}/{total} tests")
    print()
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Deployment is fully functional!")
        print()
        print("🔗 OAuth Flow Test:")
        print(f"   1. Visit: https://kite.zerodha.com/connect/login?api_key={API_KEY}&v=3")
        print(f"   2. Login with Zerodha credentials")
        print(f"   3. Authorize the app")
        print(f"   4. Check if redirected to: {FRONTEND_URL}/broker/callback")
        print(f"   5. Verify OAuth completion in browser console")
        
    else:
        print("⚠️  Some tests failed - check the logs above for details")
        
        # Show failed tests
        failed_tests = []
        for i, (result, _) in enumerate(results):
            if not result:
                failed_tests.append(i + 1)
        
        print(f"Failed test numbers: {failed_tests}")
    
    print()
    print(f"Test completed at: {datetime.now().isoformat()}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 