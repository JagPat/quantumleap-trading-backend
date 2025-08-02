"""
Test Railway Backend Deployment
Simple test script to verify the optimized backend is working on Railway
"""
import requests
import json
import time
from datetime import datetime

# Railway URL - Update this with your actual Railway URL
RAILWAY_URL = "https://quantumleap-trading-backend-production.up.railway.app"

def test_endpoint(url, endpoint_name, expected_status=200):
    """Test a single endpoint"""
    try:
        print(f"🧪 Testing {endpoint_name}...")
        response = requests.get(url, timeout=30)
        
        if response.status_code == expected_status:
            print(f"✅ {endpoint_name}: SUCCESS ({response.status_code})")
            return True, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        else:
            print(f"❌ {endpoint_name}: FAILED ({response.status_code})")
            return False, response.text
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name}: ERROR - {e}")
        return False, str(e)

def test_railway_backend():
    """Test the Railway backend deployment"""
    
    print("🚀 Testing Quantum Leap Trading Backend on Railway")
    print("=" * 60)
    print(f"Railway URL: {RAILWAY_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = []
    
    # Test 1: Root endpoint
    success, data = test_endpoint(f"{RAILWAY_URL}/", "Root Endpoint")
    test_results.append(("Root Endpoint", success))
    if success and isinstance(data, dict):
        print(f"   Version: {data.get('version', 'Unknown')}")
        print(f"   Status: {data.get('status', 'Unknown')}")
        features = data.get('features', {})
        print(f"   Database Optimization: {'✅' if features.get('database_optimization') else '❌'}")
        print(f"   AI Analysis: {'✅' if features.get('ai_analysis') else '❌'}")
    
    # Test 2: Health check
    success, data = test_endpoint(f"{RAILWAY_URL}/health", "Health Check")
    test_results.append(("Health Check", success))
    if success and isinstance(data, dict):
        print(f"   Overall Status: {data.get('status', 'Unknown')}")
        components = data.get('components', {})
        for component, status in components.items():
            if isinstance(status, dict):
                comp_status = status.get('status', 'Unknown')
                print(f"   {component.title()}: {comp_status}")
    
    # Test 3: Database performance (if optimization available)
    success, data = test_endpoint(f"{RAILWAY_URL}/api/database/performance", "Database Performance")
    test_results.append(("Database Performance", success))
    if success:
        print("   ✅ Database optimization endpoints are working")
    
    # Test 4: Database health
    success, data = test_endpoint(f"{RAILWAY_URL}/api/database/health", "Database Health")
    test_results.append(("Database Health", success))
    
    # Test 5: Trading endpoints
    success, data = test_endpoint(f"{RAILWAY_URL}/api/trading/orders/test_user", "Trading Orders")
    test_results.append(("Trading Orders", success))
    
    success, data = test_endpoint(f"{RAILWAY_URL}/api/trading/positions/test_user", "Trading Positions")
    test_results.append(("Trading Positions", success))
    
    success, data = test_endpoint(f"{RAILWAY_URL}/api/trading/signals/test_user", "Trading Signals")
    test_results.append(("Trading Signals", success))
    
    # Test 6: Database dashboard
    success, data = test_endpoint(f"{RAILWAY_URL}/api/database/dashboard", "Performance Dashboard")
    test_results.append(("Performance Dashboard", success))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for _, success in test_results if success)
    total_tests = len(test_results)
    
    for test_name, success in test_results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Your Railway backend is working perfectly!")
    elif passed_tests >= total_tests * 0.7:
        print("⚠️ Most tests passed. Some advanced features may need configuration.")
    else:
        print("❌ Several tests failed. Please check your deployment.")
    
    print(f"\n🔗 Your backend is available at: {RAILWAY_URL}")
    print("📊 Try these endpoints in your browser:")
    print(f"   • Health Check: {RAILWAY_URL}/health")
    print(f"   • System Status: {RAILWAY_URL}/")
    print(f"   • API Docs: {RAILWAY_URL}/docs (if available)")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = test_railway_backend()
    exit(0 if success else 1)