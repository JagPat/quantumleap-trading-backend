#!/usr/bin/env python3
"""
Test the endpoints that should be available based on loaded routers
"""

import requests
import json
import time

def test_endpoint(base_url, endpoint, method='GET', data=None):
    """Test a single endpoint"""
    url = f"{base_url}{endpoint}"
    
    try:
        start_time = time.time()
        
        if method.upper() == 'GET':
            response = requests.get(url, params=data, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=30)
        else:
            return None
            
        response_time = (time.time() - start_time) * 1000
        
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': response.status_code,
            'response_time': round(response_time, 2),
            'success': response.status_code in [200, 201],
            'response': response.text[:200] if response.status_code != 200 else "OK"
        }
        
    except Exception as e:
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': None,
            'response_time': None,
            'success': False,
            'response': str(e)
        }

def test_available_endpoints():
    """Test endpoints based on loaded routers"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    
    print("🧪 Testing Available Endpoints on Live Railway Deployment")
    print("=" * 70)
    print(f"📍 Base URL: {base_url}")
    print()
    
    # Based on the loaded routers, test these endpoints
    endpoints_to_test = [
        # AI Components Router
        ("/api/ai/copilot/analyze", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/copilot/chat", "POST", {"message": "Hello"}),
        ("/api/ai/copilot/status", "GET", None),
        
        # AI Analysis Router  
        ("/api/ai/analysis/portfolio", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/analysis/market", "GET", None),
        ("/api/ai/analysis/signals", "GET", None),
        
        # Broker Router
        ("/api/broker/status", "GET", {"user_id": "test_user"}),
        ("/api/broker/connect", "POST", {"api_key": "test", "api_secret": "test"}),
        ("/api/broker/positions", "GET", {"user_id": "test_user"}),
        
        # Trading Engine Router
        ("/api/trading/status", "GET", None),
        ("/api/trading/strategies", "GET", None),
        ("/api/trading/positions", "GET", None),
        ("/api/trading/orders", "GET", None),
        ("/api/trading/engine/status", "GET", None),
        ("/api/trading/engine/start", "POST", {"strategy": "test"}),
        ("/api/trading/engine/stop", "POST", None),
    ]
    
    results = []
    
    for endpoint, method, data in endpoints_to_test:
        print(f"Testing {method} {endpoint}...")
        result = test_endpoint(base_url, endpoint, method, data)
        results.append(result)
        
        if result['success']:
            print(f"  ✅ PASS - {result['status_code']} ({result['response_time']}ms)")
        else:
            print(f"  ❌ FAIL - {result['status_code']} ({result['response_time']}ms)")
            if result['status_code'] == 404:
                print(f"     Route not found")
            elif result['status_code'] == 422:
                print(f"     Validation error (expected for test data)")
            elif result['status_code'] == 500:
                print(f"     Server error")
            else:
                print(f"     {result['response'][:100]}...")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 ENDPOINT TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Pass Rate: {(passed_tests/total_tests*100):.1f}%")
    
    # Group by router
    ai_components = [r for r in results if '/api/ai/copilot/' in r['endpoint']]
    ai_analysis = [r for r in results if '/api/ai/analysis/' in r['endpoint']]
    broker = [r for r in results if '/api/broker/' in r['endpoint']]
    trading = [r for r in results if '/api/trading/' in r['endpoint']]
    
    print(f"\n📋 Results by Router:")
    print(f"   AI Components: {sum(1 for r in ai_components if r['success'])}/{len(ai_components)} working")
    print(f"   AI Analysis: {sum(1 for r in ai_analysis if r['success'])}/{len(ai_analysis)} working")
    print(f"   Broker: {sum(1 for r in broker if r['success'])}/{len(broker)} working")
    print(f"   Trading Engine: {sum(1 for r in trading if r['success'])}/{len(trading)} working")
    
    return passed_tests > 0

if __name__ == "__main__":
    success = test_available_endpoints()
    exit(0 if success else 1)