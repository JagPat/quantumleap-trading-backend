#!/usr/bin/env python3
"""
Test Trading Engine API Endpoints
Simple test to verify the trading engine API is working
"""
import requests
import json
import sys

def test_trading_engine_api(base_url="http://localhost:8000"):
    """Test trading engine API endpoints"""
    
    print("🚀 Testing Trading Engine API")
    print("=" * 50)
    
    # Test endpoints
    endpoints_to_test = [
        ("/api/trading-engine/health", "GET", "Health Check"),
        ("/api/trading-engine/metrics", "GET", "Metrics"),
        ("/api/trading-engine/config", "GET", "Configuration"),
        ("/api/trading-engine/system/status", "GET", "System Status"),
        ("/api/trading-engine/test/backend-integration", "POST", "Backend Integration Test"),
        ("/api/trading-engine/test/endpoints", "GET", "Endpoint Test"),
        ("/api/trading-engine/fallback/status", "GET", "Fallback Status")
    ]
    
    results = {}
    
    for endpoint, method, description in endpoints_to_test:
        print(f"\n🔍 Testing: {description}")
        print(f"   Endpoint: {method} {endpoint}")
        
        try:
            url = f"{base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json={}, timeout=10)
            else:
                response = requests.request(method, url, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code}")
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'status' in data:
                        print(f"   📊 Response Status: {data['status']}")
                    print(f"   📝 Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict response'}")
                except:
                    print(f"   📝 Response: {response.text[:100]}...")
                
                results[endpoint] = {"status": "success", "code": response.status_code}
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   📝 Error: {response.text[:200]}")
                results[endpoint] = {"status": "failed", "code": response.status_code}
                
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Connection Error: Server not running at {base_url}")
            results[endpoint] = {"status": "connection_error"}
        except requests.exceptions.Timeout:
            print(f"   ⏰ Timeout: Request took too long")
            results[endpoint] = {"status": "timeout"}
        except Exception as e:
            print(f"   💥 Exception: {e}")
            results[endpoint] = {"status": "exception", "error": str(e)}
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 API TEST SUMMARY")
    print("=" * 50)
    
    total_tests = len(results)
    successful_tests = len([r for r in results.values() if r["status"] == "success"])
    failed_tests = total_tests - successful_tests
    
    print(f"Total Endpoints: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 All API endpoints are working!")
        print("✅ Trading Engine API is ready for frontend integration")
        return True
    else:
        print(f"\n⚠️  {failed_tests} endpoints need attention")
        print("❌ Some API endpoints are not working")
        
        # Show failed endpoints
        print("\n❌ Failed Endpoints:")
        for endpoint, result in results.items():
            if result["status"] != "success":
                print(f"   • {endpoint}: {result['status']}")
        
        return False

def test_local_server():
    """Test against local development server"""
    print("Testing against local server (http://localhost:8000)")
    return test_trading_engine_api("http://localhost:8000")

def test_railway_server():
    """Test against Railway deployment"""
    # You would replace this with your actual Railway URL
    railway_url = "https://your-app.railway.app"
    print(f"Testing against Railway server ({railway_url})")
    return test_trading_engine_api(railway_url)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "railway":
        success = test_railway_server()
    else:
        success = test_local_server()
    
    sys.exit(0 if success else 1)