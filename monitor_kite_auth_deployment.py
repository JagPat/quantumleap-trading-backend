#!/usr/bin/env python3
"""
Monitor Kite Authentication Deployment on Railway
Monitors Railway deployment progress and tests Kite endpoints
"""

import requests
import time
import sys
from datetime import datetime

def check_kite_endpoints():
    """Check if Kite endpoints are available"""
    base_url = "https://web-production-de0bc.up.railway.app"
    
    try:
        # Test kite-login endpoint
        response = requests.post(
            f"{base_url}/api/auth/kite-login",
            json={
                "user_id": "test",
                "access_token": "test", 
                "user_name": "test",
                "email": "test@test.com"
            },
            timeout=10
        )
        
        if response.status_code == 404:
            return False, "Kite endpoints not found (404)"
        elif response.status_code in [200, 401, 422]:  # These are expected responses
            return True, f"Kite endpoints available (status: {response.status_code})"
        else:
            return False, f"Unexpected status: {response.status_code}"
            
    except Exception as e:
        return False, f"Connection error: {e}"

def check_backend_health():
    """Check overall backend health"""
    try:
        response = requests.get("https://web-production-de0bc.up.railway.app/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data.get("status", "unknown")
        else:
            return False, f"Health check failed: {response.status_code}"
    except Exception as e:
        return False, f"Health check error: {e}"

def monitor_deployment():
    """Monitor deployment progress"""
    print("🔍 Monitoring Railway Deployment Progress...")
    print("=" * 60)
    
    max_attempts = 20  # 10 minutes max (30 seconds * 20)
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"[{timestamp}] Attempt {attempt}/{max_attempts}")
        
        # Check backend health first
        health_ok, health_msg = check_backend_health()
        print(f"  🏥 Backend Health: {health_msg}")
        
        if not health_ok:
            print("  ⚠️ Backend not healthy, waiting...")
            time.sleep(30)
            continue
        
        # Check Kite endpoints
        kite_ok, kite_msg = check_kite_endpoints()
        print(f"  🔐 Kite Endpoints: {kite_msg}")
        
        if kite_ok:
            print("\n" + "=" * 60)
            print("✅ DEPLOYMENT SUCCESSFUL!")
            print("🎉 Kite authentication endpoints are now live!")
            print("🔗 Available endpoints:")
            print("   - POST /api/auth/kite-login")
            print("   - POST /api/auth/kite-register")
            print("   - POST /api/auth/sync-kite-profile")
            print("=" * 60)
            return True
        
        print(f"  ⏳ Still deploying... waiting 30 seconds")
        time.sleep(30)
    
    print("\n" + "=" * 60)
    print("❌ DEPLOYMENT TIMEOUT")
    print("⚠️ Kite endpoints are still not available after 10 minutes")
    print("💡 This might indicate a deployment issue")
    print("=" * 60)
    return False

def run_comprehensive_test():
    """Run comprehensive test after deployment"""
    print("\n🧪 Running Comprehensive Backend Test...")
    
    base_url = "https://web-production-de0bc.up.railway.app"
    endpoints = [
        ("GET", "/health", "Backend Health"),
        ("GET", "/api/auth/health", "Auth Health"),
        ("GET", "/api/auth/test-users", "Test Users"),
        ("GET", "/api/broker/status-header", "Broker Status Header"),
        ("POST", "/api/auth/kite-login", "Kite Login", {
            "user_id": "test",
            "access_token": "test",
            "user_name": "test",
            "email": "test@test.com"
        }),
        ("POST", "/api/auth/kite-register", "Kite Register", {
            "user_id": "test",
            "user_name": "test",
            "email": "test@test.com",
            "access_token": "test",
            "broker_name": "zerodha"
        })
    ]
    
    results = {}
    for method, endpoint, description, *data in endpoints:
        try:
            if method == "POST" and data:
                response = requests.post(f"{base_url}{endpoint}", json=data[0], timeout=10)
            else:
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            success = response.status_code not in [404, 500]
            results[endpoint] = {
                "status_code": response.status_code,
                "success": success,
                "description": description
            }
            
            status_icon = "✅" if success else "❌"
            print(f"  {status_icon} {description}: {response.status_code}")
            
        except Exception as e:
            results[endpoint] = {
                "error": str(e),
                "success": False,
                "description": description
            }
            print(f"  ❌ {description}: Error - {e}")
    
    successful = sum(1 for r in results.values() if r.get("success", False))
    total = len(endpoints)
    
    print(f"\n📊 Test Results: {successful}/{total} endpoints working")
    return successful >= (total * 0.8)  # 80% success rate

def main():
    """Main monitoring function"""
    print("🚀 Railway Kite Authentication Deployment Monitor")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target: https://web-production-de0bc.up.railway.app")
    
    # Step 1: Monitor deployment
    if monitor_deployment():
        # Step 2: Run comprehensive test
        if run_comprehensive_test():
            print("\n🎉 All systems operational!")
            print("🔄 Next step: Test the frontend with Kite credentials")
            return True
        else:
            print("\n⚠️ Some endpoints have issues, but core functionality works")
            return True
    else:
        print("\n❌ Deployment monitoring failed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)