#!/usr/bin/env python3
"""
Test the correct endpoints based on the OpenAPI documentation
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
        elif method.upper() == 'DELETE':
            response = requests.delete(url, timeout=30)
        else:
            return None
            
        response_time = (time.time() - start_time) * 1000
        
        return {
            'endpoint': endpoint,
            'method': method,
            'status_code': response.status_code,
            'response_time': round(response_time, 2),
            'success': response.status_code in [200, 201, 422],  # 422 is validation error, which means endpoint exists
            'response': response.text[:200] if response.status_code not in [200, 201] else "OK"
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

def test_correct_endpoints():
    """Test endpoints using the correct paths from OpenAPI"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    
    print("🎯 Testing Correct Endpoints from OpenAPI Documentation")
    print("=" * 70)
    print(f"📍 Base URL: {base_url}")
    print()
    
    # Test endpoints based on the actual OpenAPI paths
    endpoints_to_test = [
        # Health and Status
        ("/", "GET", None),
        ("/health", "GET", None),
        ("/status", "GET", None),
        
        # AI Components (single /api/ prefix)
        ("/api/ai/copilot/analyze", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/copilot/recommendations", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/chat", "POST", {"message": "Hello"}),
        ("/api/ai/health", "GET", None),
        ("/api/ai/analysis/comprehensive", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/market-intelligence", "POST", {"query": "market analysis"}),
        ("/api/ai/performance-analytics", "POST", {"portfolio_data": {"test": "data"}}),
        ("/api/ai/learning-insights", "GET", None),
        ("/api/ai/optimization-recommendations", "GET", None),
        ("/api/ai/risk-metrics", "GET", None),
        ("/api/ai/strategy-templates", "GET", None),
        ("/api/ai/emergency-stop", "POST", {"reason": "test"}),
        
        # AI Analysis (double /api/api/ prefix - as shown in OpenAPI)
        ("/api/api/ai/simple-analysis/portfolio", "POST", {"portfolio_data": {"test": "data"}}),
        
        # Broker (double /api/api/ prefix - as shown in OpenAPI)
        ("/api/api/broker/status", "GET", None),
        ("/api/api/broker/profile", "GET", None),
        ("/api/api/broker/holdings", "GET", None),
        ("/api/api/broker/positions", "GET", None),
        ("/api/api/broker/orders", "GET", None),
        ("/api/api/broker/margins", "GET", None),
        ("/api/api/broker/status-header", "GET", None),
        
        # Trading Engine (double /api/api/ prefix - as shown in OpenAPI)
        ("/api/api/trading-engine/status", "GET", None),
        ("/api/api/trading-engine/health", "GET", None),
        ("/api/api/trading-engine/metrics", "GET", None),
        ("/api/api/trading-engine/alerts", "GET", None),
        ("/api/api/trading-engine/config", "GET", None),
    ]
    
    results = []
    
    for endpoint, method, data in endpoints_to_test:
        print(f"Testing {method} {endpoint}...")
        result = test_endpoint(base_url, endpoint, method, data)
        results.append(result)
        
        if result['success']:
            status_icon = "✅" if result['status_code'] in [200, 201] else "⚠️"
            print(f"  {status_icon} {result['status_code']} ({result['response_time']}ms)")
            if result['status_code'] == 422:
                print(f"     Validation error (endpoint exists but needs proper data)")
        else:
            print(f"  ❌ FAIL - {result['status_code']} ({result['response_time']}ms)")
            if result['status_code'] == 404:
                print(f"     Route not found")
            elif result['status_code'] == 500:
                print(f"     Server error")
            else:
                print(f"     {result['response'][:100]}...")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 CORRECT ENDPOINT TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    working_tests = sum(1 for r in results if r['status_code'] in [200, 201])
    validation_errors = sum(1 for r in results if r['status_code'] == 422)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Working (200/201): {working_tests} ✅")
    print(f"Validation Errors (422): {validation_errors} ⚠️")
    print(f"Failed (404/500): {failed_tests} ❌")
    print(f"Overall Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    # Group by category
    health = [r for r in results if r['endpoint'] in ['/', '/health', '/status']]
    ai_single = [r for r in results if r['endpoint'].startswith('/api/ai/')]
    ai_double = [r for r in results if r['endpoint'].startswith('/api/api/ai/')]
    broker = [r for r in results if r['endpoint'].startswith('/api/api/broker/')]
    trading = [r for r in results if r['endpoint'].startswith('/api/api/trading-engine/')]
    
    print(f"\n📋 Results by Category:")
    print(f"   Health/Status: {sum(1 for r in health if r['success'])}/{len(health)} working")
    print(f"   AI Components: {sum(1 for r in ai_single if r['success'])}/{len(ai_single)} working")
    print(f"   AI Analysis: {sum(1 for r in ai_double if r['success'])}/{len(ai_double)} working")
    print(f"   Broker: {sum(1 for r in broker if r['success'])}/{len(broker)} working")
    print(f"   Trading Engine: {sum(1 for r in trading if r['success'])}/{len(trading)} working")
    
    # Show working endpoints
    working_endpoints = [r for r in results if r['status_code'] in [200, 201]]
    if working_endpoints:
        print(f"\n✅ Fully Working Endpoints ({len(working_endpoints)}):")
        for r in working_endpoints:
            print(f"   {r['method']} {r['endpoint']}")
    
    # Show endpoints with validation errors (these exist but need proper data)
    validation_endpoints = [r for r in results if r['status_code'] == 422]
    if validation_endpoints:
        print(f"\n⚠️  Endpoints Needing Proper Data ({len(validation_endpoints)}):")
        for r in validation_endpoints:
            print(f"   {r['method']} {r['endpoint']}")
    
    return passed_tests > 0

if __name__ == "__main__":
    success = test_correct_endpoints()
    exit(0 if success else 1)