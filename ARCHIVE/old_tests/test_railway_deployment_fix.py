#!/usr/bin/env python3
"""
Test Railway Deployment Fix
Verifies that the PORT environment variable fix is working correctly
"""
import requests
import json
import sys
from datetime import datetime

def test_railway_deployment(base_url):
    """Test Railway deployment endpoints"""
    print("🧪 Testing Railway Deployment Fix...")
    print("=" * 60)
    print(f"🌐 Base URL: {base_url}")
    print(f"🕐 Test Time: {datetime.now().isoformat()}")
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test cases
    test_cases = [
        {
            "name": "Health Check",
            "endpoint": "/health",
            "method": "GET",
            "expected_keys": ["status", "port", "timestamp"]
        },
        {
            "name": "Root Endpoint",
            "endpoint": "/",
            "method": "GET", 
            "expected_keys": ["message", "version", "status", "environment", "port"]
        },
        {
            "name": "Database Performance",
            "endpoint": "/api/database/performance",
            "method": "GET",
            "expected_keys": ["success", "data"]
        },
        {
            "name": "Database Dashboard",
            "endpoint": "/api/database/dashboard", 
            "method": "GET",
            "expected_keys": ["success", "data"]
        },
        {
            "name": "Database Health",
            "endpoint": "/api/database/health",
            "method": "GET",
            "expected_keys": ["success", "data"]
        }
    ]
    
    for test in test_cases:
        try:
            print(f"🔍 Testing: {test['name']}")
            url = f"{base_url}{test['endpoint']}"
            
            if test['method'] == 'GET':
                response = requests.get(url, timeout=10)
            elif test['method'] == 'POST':
                response = requests.post(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check expected keys
                missing_keys = []
                for key in test['expected_keys']:
                    if key not in data:
                        missing_keys.append(key)
                
                if not missing_keys:
                    print(f"  ✅ PASS - Status: {response.status_code}")
                    if test['name'] == 'Root Endpoint':
                        print(f"     📍 Environment: {data.get('environment', 'unknown')}")
                        print(f"     🚪 Port: {data.get('port', 'unknown')}")
                    elif test['name'] == 'Health Check':
                        print(f"     💚 Status: {data.get('status', 'unknown')}")
                        print(f"     🚪 Port: {data.get('port', 'unknown')}")
                    tests_passed += 1
                else:
                    print(f"  ❌ FAIL - Missing keys: {missing_keys}")
                    tests_failed += 1
            else:
                print(f"  ❌ FAIL - Status: {response.status_code}")
                print(f"     Response: {response.text[:200]}...")
                tests_failed += 1
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ FAIL - Connection Error: {str(e)}")
            tests_failed += 1
        except json.JSONDecodeError as e:
            print(f"  ❌ FAIL - JSON Parse Error: {str(e)}")
            tests_failed += 1
        except Exception as e:
            print(f"  ❌ FAIL - Unexpected Error: {str(e)}")
            tests_failed += 1
        
        print()
    
    # Test specific PORT fix validation
    print("🔧 Testing PORT Environment Variable Fix...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            port_value = data.get('port', 'unknown')
            
            if port_value != 'unknown' and str(port_value).isdigit():
                print(f"  ✅ PORT Fix Verified - Port: {port_value}")
                print(f"  ✅ Port is valid integer (not '$PORT' string)")
                tests_passed += 1
            else:
                print(f"  ❌ PORT Fix Failed - Port: {port_value}")
                tests_failed += 1
        else:
            print(f"  ❌ Cannot verify PORT fix - Status: {response.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"  ❌ PORT Fix Test Failed: {str(e)}")
        tests_failed += 1
    
    print()
    print("=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"✅ Tests Passed: {tests_passed}")
    print(f"❌ Tests Failed: {tests_failed}")
    print(f"📈 Success Rate: {(tests_passed/(tests_passed+tests_failed)*100):.1f}%")
    
    if tests_failed == 0:
        print("\n🎉 All Tests Passed! Railway deployment fix is working correctly.")
        print("✅ PORT environment variable issue has been resolved.")
        return True
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Please check the deployment.")
        return False

def main():
    """Main test function"""
    if len(sys.argv) != 2:
        print("Usage: python3 test_railway_deployment_fix.py <railway_url>")
        print("Example: python3 test_railway_deployment_fix.py https://your-app.railway.app")
        sys.exit(1)
    
    railway_url = sys.argv[1].rstrip('/')
    success = test_railway_deployment(railway_url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()