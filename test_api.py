#!/usr/bin/env python3
"""
Simple test script for QuantumLeap Trading Backend API
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ Health endpoint is working")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Health endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health endpoint error: {str(e)}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✓ Root endpoint is working")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"✗ Root endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Root endpoint error: {str(e)}")
        return False

def test_api_documentation():
    """Test if API documentation is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✓ API documentation is accessible")
            return True
        else:
            print(f"✗ API documentation failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API documentation error: {str(e)}")
        return False

def test_openapi_schema():
    """Test if OpenAPI schema is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            print("✓ OpenAPI schema is accessible")
            schema = response.json()
            print(f"  API Title: {schema.get('info', {}).get('title', 'N/A')}")
            print(f"  API Version: {schema.get('info', {}).get('version', 'N/A')}")
            return True
        else:
            print(f"✗ OpenAPI schema failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ OpenAPI schema error: {str(e)}")
        return False

def test_portfolio_endpoints_unauthorized():
    """Test portfolio endpoints without authentication (should return 401)"""
    endpoints = [
        "/api/portfolio/summary?user_id=test_user",
        "/api/portfolio/holdings?user_id=test_user",
        "/api/portfolio/positions?user_id=test_user"
    ]
    
    all_passed = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            if response.status_code == 401:
                print(f"✓ {endpoint} correctly returns 401 (Unauthorized)")
            else:
                print(f"✗ {endpoint} should return 401 but returned {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"✗ {endpoint} error: {str(e)}")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("Testing QuantumLeap Trading Backend API...")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("API Documentation", test_api_documentation),
        ("OpenAPI Schema", test_openapi_schema),
        ("Portfolio Endpoints (Unauthorized)", test_portfolio_endpoints_unauthorized)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"  Failed: {test_name}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the API server.")
        sys.exit(1)

if __name__ == "__main__":
    main() 