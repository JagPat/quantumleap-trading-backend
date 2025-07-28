#!/usr/bin/env python3
"""
Comprehensive CORS Test Script
Tests all frontend-backend endpoints for CORS compatibility
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "https://web-production-de0bc.up.railway.app"
FRONTEND_ORIGIN = "http://localhost:5173"

def test_endpoint(method, endpoint, data=None, params=None):
    """Test a single endpoint for CORS compatibility"""
    url = f"{BASE_URL}{endpoint}"
    
    headers = {
        "Origin": FRONTEND_ORIGIN,
        "Content-Type": "application/json"
    }
    
    try:
        # Test OPTIONS preflight first
        options_response = requests.options(
            url,
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=10
        )
        
        preflight_ok = options_response.status_code == 200
        cors_headers = {
            "allow_origin": options_response.headers.get("access-control-allow-origin"),
            "allow_methods": options_response.headers.get("access-control-allow-methods"),
            "allow_credentials": options_response.headers.get("access-control-allow-credentials")
        }
        
        # Test actual request
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            response = requests.request(method, url, headers=headers, json=data, params=params, timeout=10)
        
        return {
            "endpoint": endpoint,
            "method": method,
            "preflight_status": options_response.status_code,
            "preflight_ok": preflight_ok,
            "cors_headers": cors_headers,
            "actual_status": response.status_code,
            "actual_ok": response.status_code < 400,
            "response_size": len(response.text),
            "error": None
        }
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "preflight_status": None,
            "preflight_ok": False,
            "cors_headers": {},
            "actual_status": None,
            "actual_ok": False,
            "response_size": 0,
            "error": str(e)
        }

def main():
    """Test all endpoints used by the frontend"""
    print("🧪 Comprehensive CORS Endpoint Testing")
    print("=" * 60)
    print(f"Backend URL: {BASE_URL}")
    print(f"Frontend Origin: {FRONTEND_ORIGIN}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    # Define all endpoints that the frontend uses
    endpoints_to_test = [
        # Portfolio endpoints
        ("GET", "/api/portfolio/fetch-live-simple", None, {"user_id": "EBW183"}),
        ("GET", "/api/portfolio/latest-simple", None, {"user_id": "EBW183"}),
        ("GET", "/api/portfolio/mock", None, {"user_id": "EBW183"}),
        ("GET", "/api/portfolio/status", None, None),
        
        # Broker endpoints
        ("GET", "/api/broker/status-header", None, None),
        ("GET", "/api/broker/status", None, None),
        
        # AI Analysis endpoints
        ("POST", "/api/ai/analysis/portfolio", {"total_value": 100000, "holdings": [{"symbol": "RELIANCE", "quantity": 100, "current_value": 50000}]}, None),
        ("GET", "/api/ai/analysis/health", None, None),
        
        # Health endpoints
        ("GET", "/health", None, None),
        ("GET", "/", None, None),
        
        # Trading engine endpoints (if they exist)
        ("GET", "/api/trading/status", None, None),
    ]
    
    results = []
    total_tests = len(endpoints_to_test)
    passed_tests = 0
    
    for i, (method, endpoint, data, params) in enumerate(endpoints_to_test, 1):
        print(f"[{i:2d}/{total_tests}] Testing {method} {endpoint}...")
        
        result = test_endpoint(method, endpoint, data, params)
        results.append(result)
        
        # Print immediate result
        if result["error"]:
            print(f"    ❌ ERROR: {result['error']}")
        elif result["preflight_ok"] and result["actual_ok"]:
            print(f"    ✅ PASS: {result['actual_status']} ({result['response_size']} bytes)")
            passed_tests += 1
        elif result["preflight_ok"] and not result["actual_ok"]:
            print(f"    ⚠️  CORS OK, API ERROR: {result['actual_status']}")
        elif not result["preflight_ok"] and result["actual_ok"]:
            print(f"    ⚠️  API OK, CORS ERROR: preflight {result['preflight_status']}")
        else:
            print(f"    ❌ FAIL: preflight {result['preflight_status']}, actual {result['actual_status']}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    print()
    print("📊 Test Summary")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
    print()
    
    # Detailed results
    print("📋 Detailed Results")
    print("=" * 60)
    
    for result in results:
        status_icon = "✅" if (result["preflight_ok"] and result["actual_ok"]) else "❌"
        print(f"{status_icon} {result['method']} {result['endpoint']}")
        
        if result["error"]:
            print(f"    Error: {result['error']}")
        else:
            print(f"    Preflight: {result['preflight_status']} | Actual: {result['actual_status']}")
            print(f"    CORS Origin: {result['cors_headers'].get('allow_origin', 'None')}")
            
            if not result["preflight_ok"] or not result["actual_ok"]:
                print(f"    ⚠️  Issue detected - needs investigation")
        print()
    
    # CORS Headers Analysis
    print("🔍 CORS Headers Analysis")
    print("=" * 60)
    
    cors_origins = set()
    cors_methods = set()
    
    for result in results:
        if result["cors_headers"].get("allow_origin"):
            cors_origins.add(result["cors_headers"]["allow_origin"])
        if result["cors_headers"].get("allow_methods"):
            cors_methods.add(result["cors_headers"]["allow_methods"])
    
    print(f"Allowed Origins: {list(cors_origins)}")
    print(f"Allowed Methods: {list(cors_methods)}")
    print()
    
    # Recommendations
    print("💡 Recommendations")
    print("=" * 60)
    
    failed_results = [r for r in results if not (r["preflight_ok"] and r["actual_ok"])]
    
    if not failed_results:
        print("🎉 All tests passed! CORS is properly configured.")
    else:
        print("Issues found:")
        for result in failed_results:
            if result["error"]:
                print(f"  - {result['endpoint']}: Connection error - check if backend is running")
            elif not result["preflight_ok"]:
                print(f"  - {result['endpoint']}: CORS preflight failing - check OPTIONS handler")
            elif not result["actual_ok"]:
                print(f"  - {result['endpoint']}: API error {result['actual_status']} - check endpoint implementation")
    
    print()
    print("🚀 Frontend should work properly once all tests pass!")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)