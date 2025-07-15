#!/usr/bin/env python3
"""
Test script for deployed QuantumLeap Trading API
Tests all endpoints to ensure deployment is working correctly
"""

import requests
import json
from datetime import datetime

# API base URL
API_BASE_URL = "https://web-production-de0bc.up.railway.app"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint passed: {data}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_api_docs():
    """Test if API documentation is accessible"""
    print("\n🔍 Testing API documentation...")
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API documentation is accessible")
            return True
        else:
            print(f"❌ API docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API docs error: {e}")
        return False

def test_openapi_schema():
    """Test if OpenAPI schema is accessible"""
    print("\n🔍 Testing OpenAPI schema...")
    try:
        response = requests.get(f"{API_BASE_URL}/openapi.json")
        if response.status_code == 200:
            schema = response.json()
            print("✅ OpenAPI schema is accessible")
            print(f"   Title: {schema.get('info', {}).get('title', 'N/A')}")
            print(f"   Version: {schema.get('info', {}).get('version', 'N/A')}")
            return True
        else:
            print(f"❌ OpenAPI schema failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ OpenAPI schema error: {e}")
        return False

def test_broker_session_endpoint():
    """Test broker session endpoint (should fail without proper data)"""
    print("\n🔍 Testing broker session endpoint...")
    try:
        # This should fail with validation error (expected behavior)
        response = requests.post(
            f"{API_BASE_URL}/api/broker/generate-session",
            json={}
        )
        if response.status_code == 422:  # Validation error expected
            print("✅ Broker session endpoint is accessible (validation working)")
            return True
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Broker session endpoint error: {e}")
        return False

def test_portfolio_endpoints():
    """Test portfolio endpoints (should fail without user_id)"""
    print("\n🔍 Testing portfolio endpoints...")
    
    endpoints = [
        "/api/portfolio/summary",
        "/api/portfolio/holdings", 
        "/api/portfolio/positions"
    ]
    
    all_passed = True
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_BASE_URL}{endpoint}")
            if response.status_code == 422:  # Validation error expected
                print(f"✅ {endpoint} is accessible (validation working)")
            else:
                print(f"⚠️  {endpoint} unexpected response: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {endpoint} error: {e}")
            all_passed = False
    
    return all_passed

def test_cors_headers():
    """Test CORS headers are present"""
    print("\n🔍 Testing CORS headers...")
    try:
        response = requests.options(f"{API_BASE_URL}/health")
        headers = response.headers
        
        cors_headers = [
            'access-control-allow-origin',
            'access-control-allow-methods',
            'access-control-allow-headers'
        ]
        
        cors_present = all(header in headers for header in cors_headers)
        
        if cors_present:
            print("✅ CORS headers are present")
            return True
        else:
            print("⚠️  Some CORS headers missing")
            return False
    except Exception as e:
        print(f"❌ CORS test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing QuantumLeap Trading API Deployment")
    print(f"📍 API URL: {API_BASE_URL}")
    print(f"🕐 Test Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("API Documentation", test_api_docs),
        ("OpenAPI Schema", test_openapi_schema),
        ("Broker Session Endpoint", test_broker_session_endpoint),
        ("Portfolio Endpoints", test_portfolio_endpoints),
        ("CORS Headers", test_cors_headers),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API deployment is successful!")
        print(f"\n🔗 API Documentation: {API_BASE_URL}/docs")
        print(f"🔗 Health Check: {API_BASE_URL}/health")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 