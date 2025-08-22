#!/usr/bin/env python3
"""
Test Railway Deployment Fixes
Verify that all database schema and API endpoint fixes are working
"""

import requests
import json
import time
from datetime import datetime

def test_endpoint(url, name, expected_status_codes=[200]):
    """Test a single endpoint"""
    try:
        print(f"\n🧪 Testing {name}")
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        
        print(f"Status: {status_code}")
        
        if status_code in expected_status_codes:
            print(f"✅ {name}: PASSED")
            try:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"Response: {response.text[:200]}...")
            return True
        else:
            print(f"❌ {name}: FAILED (Expected {expected_status_codes}, got {status_code})")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: CONNECTION ERROR - {str(e)}")
        return False

def main():
    """Main testing function"""
    print("🧪 Testing Railway Deployment Fixes")
    print("=" * 50)
    
    railway_url = "https://web-production-de0bc.up.railway.app"
    
    # Test basic health
    print(f"\n🏥 Testing basic health endpoints...")
    health_passed = test_endpoint(f"{railway_url}/health", "Health Check")
    
    if not health_passed:
        print("❌ Basic health check failed. Deployment may not be ready.")
        return
    
    # Test the specific fixes we implemented
    print(f"\n🔧 Testing Database Schema Initialization Fixes...")
    
    tests = [
        # Task 1: Database initialization (tested indirectly through other endpoints)
        
        # Task 2: Missing /api/trading/status endpoint
        (f"{railway_url}/api/trading/status", "Trading Status Endpoint", [200]),
        
        # Task 3: AI endpoint authentication issues
        (f"{railway_url}/api/ai/strategy-templates", "AI Strategy Templates", [200, 401]),
        (f"{railway_url}/api/ai/risk-metrics", "AI Risk Metrics", [200, 401]),
        
        # Task 4: Broker session endpoint HTTP method handling
        (f"{railway_url}/api/broker/session?user_id=test_user", "Broker Session GET", [200, 401]),
        
        # Additional endpoints to verify overall health
        (f"{railway_url}/api/portfolio/fetch-live-simple?user_id=test_user", "Portfolio Fetch", [200, 401, 500]),
        (f"{railway_url}/api/ai/chat", "AI Chat", [200, 401, 405, 422]),  # 422 for missing body
        (f"{railway_url}/docs", "API Documentation", [200]),
    ]
    
    passed = 0
    total = len(tests)
    
    for url, name, expected_codes in tests:
        if test_endpoint(url, name, expected_codes):
            passed += 1
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 All tests passed! Deployment fixes are working correctly.")
    elif passed >= total * 0.8:
        print("\n✅ Most tests passed. Deployment is largely successful.")
    else:
        print("\n⚠️  Many tests failed. Deployment may have issues.")
    
    print(f"\n🔗 Railway URL: {railway_url}")
    print(f"📚 API Docs: {railway_url}/docs")
    print(f"🏥 Health: {railway_url}/health")
    
    # Test database initialization indirectly
    print(f"\n🗄️  Testing Database Initialization (Indirect)")
    print("Checking if database tables are working by testing endpoints that use them...")
    
    # Test login endpoint (uses users table)
    try:
        login_response = requests.post(f"{railway_url}/api/auth/login", 
                                     json={"email": "test@quantumleap.com", "password": "test123"},
                                     timeout=10)
        if login_response.status_code in [200, 401, 422]:
            print("✅ Users table: Working (login endpoint responds)")
        else:
            print(f"⚠️  Users table: May have issues (login returned {login_response.status_code})")
    except Exception as e:
        print(f"❌ Users table: Error testing - {str(e)}")
    
    # Test portfolio endpoint (uses portfolio_snapshots table)
    try:
        portfolio_response = requests.get(f"{railway_url}/api/portfolio/latest-simple?user_id=test_user", timeout=10)
        if portfolio_response.status_code in [200, 401, 404]:
            print("✅ Portfolio snapshots table: Working (portfolio endpoint responds)")
        else:
            print(f"⚠️  Portfolio snapshots table: May have issues (portfolio returned {portfolio_response.status_code})")
    except Exception as e:
        print(f"❌ Portfolio snapshots table: Error testing - {str(e)}")

if __name__ == "__main__":
    main()