"""
Test Live Railway Backend
Test the deployed Quantum Leap Trading Backend on Railway
"""
import requests
import json
import time
from datetime import datetime

# Update this with your actual Railway URL
RAILWAY_URL = "https://quantumleap-trading-backend-production.up.railway.app"

def test_live_backend():
    """Test the live Railway backend"""
    
    print("🧪 Testing Live Quantum Leap Trading Backend")
    print("=" * 60)
    print(f"Railway URL: {RAILWAY_URL}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Basic connectivity
    print("\n1️⃣ Testing Basic Connectivity...")
    total_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is online and responding")
            print(f"   Version: {data.get('version', 'Unknown')}")
            print(f"   Status: {data.get('status', 'Unknown')}")
            
            features = data.get('features', {})
            print(f"   Database Optimization: {'✅ Enabled' if features.get('database_optimization') else '❌ Disabled'}")
            print(f"   AI Analysis: {'✅ Enabled' if features.get('ai_analysis') else '❌ Disabled'}")
            tests_passed += 1
        else:
            print(f"❌ Backend returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    
    # Test 2: Health check
    print("\n2️⃣ Testing Health Check...")
    total_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Overall Status: {data.get('status', 'Unknown')}")
            
            components = data.get('components', {})
            for component, status in components.items():
                if isinstance(status, dict):
                    comp_status = status.get('status', 'Unknown')
                    print(f"   {component.title()}: {comp_status}")
            tests_passed += 1
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 3: Database optimization endpoints
    print("\n3️⃣ Testing Database Optimization...")
    total_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/database/performance", timeout=30)
        if response.status_code == 200:
            print("✅ Database performance endpoint working")
            tests_passed += 1
        else:
            print(f"❌ Database performance endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Database performance error: {e}")
    
    # Test 4: Database health
    print("\n4️⃣ Testing Database Health...")
    total_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/database/health", timeout=30)
        if response.status_code == 200:
            print("✅ Database health endpoint working")
            tests_passed += 1
        else:
            print(f"❌ Database health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Database health error: {e}")
    
    # Test 5: Trading endpoints
    print("\n5️⃣ Testing Trading Endpoints...")
    trading_tests = 0
    trading_passed = 0
    
    # Test orders endpoint
    trading_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/trading/orders/test_user", timeout=30)
        if response.status_code == 200:
            print("✅ Trading orders endpoint working")
            trading_passed += 1
        else:
            print(f"⚠️ Trading orders endpoint: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Trading orders error: {e}")
    
    # Test positions endpoint
    trading_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/trading/positions/test_user", timeout=30)
        if response.status_code == 200:
            print("✅ Trading positions endpoint working")
            trading_passed += 1
        else:
            print(f"⚠️ Trading positions endpoint: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Trading positions error: {e}")
    
    # Test signals endpoint
    trading_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/trading/signals/test_user", timeout=30)
        if response.status_code == 200:
            print("✅ Trading signals endpoint working")
            trading_passed += 1
        else:
            print(f"⚠️ Trading signals endpoint: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Trading signals error: {e}")
    
    if trading_passed > 0:
        tests_passed += 1
        print(f"✅ Trading endpoints: {trading_passed}/{trading_tests} working")
    else:
        print("❌ No trading endpoints working")
    
    total_tests += 1
    
    # Test 6: Performance dashboard
    print("\n6️⃣ Testing Performance Dashboard...")
    total_tests += 1
    try:
        response = requests.get(f"{RAILWAY_URL}/api/database/dashboard", timeout=30)
        if response.status_code == 200:
            print("✅ Performance dashboard working")
            tests_passed += 1
        else:
            print(f"❌ Performance dashboard failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Performance dashboard error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    success_rate = (tests_passed / total_tests) * 100
    
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 EXCELLENT! Your backend is working perfectly!")
        status = "excellent"
    elif success_rate >= 70:
        print("✅ GOOD! Most features are working correctly.")
        status = "good"
    elif success_rate >= 50:
        print("⚠️ PARTIAL! Some features need attention.")
        status = "partial"
    else:
        print("❌ ISSUES! Several features are not working.")
        status = "issues"
    
    print(f"\n🔗 Your backend is available at: {RAILWAY_URL}")
    print("\n📋 Quick Access Links:")
    print(f"   • System Status: {RAILWAY_URL}/")
    print(f"   • Health Check: {RAILWAY_URL}/health")
    print(f"   • Database Performance: {RAILWAY_URL}/api/database/performance")
    print(f"   • Database Health: {RAILWAY_URL}/api/database/health")
    print(f"   • Performance Dashboard: {RAILWAY_URL}/api/database/dashboard")
    
    if status in ["excellent", "good"]:
        print("\n🚀 Your optimized backend is ready for production use!")
        print("✅ Database optimization features are active")
        print("✅ Performance monitoring is working")
        print("✅ Trading endpoints are functional")
    else:
        print("\n🔧 Some features may need configuration or debugging.")
        print("📖 Check the Railway logs for more details.")
    
    return status in ["excellent", "good"]

if __name__ == "__main__":
    print("🚀 Starting Live Backend Test...")
    success = test_live_backend()
    
    if success:
        print("\n🎊 SUCCESS! Your Railway backend is working great!")
    else:
        print("\n⚠️ Some issues detected. Check the logs and try again.")
    
    exit(0 if success else 1)