#!/usr/bin/env python3
"""
Force Railway Redeploy with Kite Authentication Updates
This script will force Railway to redeploy with the latest backend changes
"""

import requests
import json
import time
import sys
from datetime import datetime

def check_kite_endpoints():
    """Check if Kite endpoints are available"""
    base_url = "https://web-production-de0bc.up.railway.app"
    
    print("🔍 Checking Kite authentication endpoints...")
    
    # Test kite-login endpoint
    try:
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
            print("❌ Kite endpoints not found - Railway needs redeploy")
            return False
        else:
            print(f"✅ Kite login endpoint responding (status: {response.status_code})")
            return True
            
    except Exception as e:
        print(f"❌ Error checking Kite endpoints: {e}")
        return False

def trigger_railway_redeploy():
    """Trigger Railway redeploy by making a dummy change"""
    print("🚀 Triggering Railway redeploy...")
    
    # Since we can't directly trigger Railway redeploy via API without tokens,
    # we'll create a timestamp file that can be used to trigger redeploy
    timestamp = datetime.now().isoformat()
    
    # Create a deployment trigger file
    with open("railway_deploy_trigger.txt", "w") as f:
        f.write(f"Kite Auth Deployment Trigger: {timestamp}\n")
        f.write("This file triggers Railway redeploy with Kite authentication endpoints\n")
        f.write("New endpoints added:\n")
        f.write("- /api/auth/kite-login\n")
        f.write("- /api/auth/kite-register\n") 
        f.write("- /api/auth/sync-kite-profile\n")
    
    print("✅ Deployment trigger file created")
    print("📝 Manual step required: Push changes to trigger Railway redeploy")
    
    return True

def wait_for_deployment():
    """Wait for Railway deployment to complete"""
    print("⏳ Waiting for Railway deployment...")
    
    max_attempts = 30  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Check if Kite endpoints are now available
            if check_kite_endpoints():
                print("✅ Kite endpoints are now available!")
                return True
            
            print(f"⏳ Attempt {attempt + 1}/{max_attempts} - Still waiting...")
            time.sleep(10)
            attempt += 1
            
        except KeyboardInterrupt:
            print("\n⚠️ Waiting interrupted by user")
            return False
    
    print("❌ Timeout waiting for deployment")
    return False

def test_complete_backend():
    """Test complete backend functionality"""
    base_url = "https://web-production-de0bc.up.railway.app"
    
    print("🧪 Testing complete backend functionality...")
    
    endpoints_to_test = [
        ("/health", "Backend health"),
        ("/api/auth/health", "Auth health"),
        ("/api/auth/test-users", "Test users"),
        ("/api/broker/status-header", "Broker status header"),
        ("/api/auth/kite-login", "Kite login (should exist now)"),
    ]
    
    results = {}
    
    for endpoint, description in endpoints_to_test:
        try:
            if endpoint == "/api/auth/kite-login":
                # POST request for kite-login
                response = requests.post(
                    f"{base_url}{endpoint}",
                    json={
                        "user_id": "test",
                        "access_token": "test",
                        "user_name": "test", 
                        "email": "test@test.com"
                    },
                    timeout=10
                )
            else:
                # GET request for others
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            success = response.status_code != 404
            results[endpoint] = {
                "status_code": response.status_code,
                "success": success,
                "description": description
            }
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {description}: {response.status_code}")
            
        except Exception as e:
            results[endpoint] = {
                "error": str(e),
                "success": False,
                "description": description
            }
            print(f"❌ {description}: Error - {e}")
    
    # Count successful endpoints
    successful = sum(1 for r in results.values() if r.get("success", False))
    total = len(endpoints_to_test)
    
    print(f"\n📊 Backend Test Results: {successful}/{total} endpoints working")
    
    return successful >= 4  # At least 4 out of 5 should work

def main():
    """Main function"""
    print("🚀 Force Railway Redeploy with Kite Authentication")
    print("=" * 60)
    
    # Step 1: Check current status
    if check_kite_endpoints():
        print("✅ Kite endpoints are already available!")
        print("🧪 Running complete backend test...")
        if test_complete_backend():
            print("🎉 Backend is fully functional!")
            return True
        else:
            print("⚠️ Some backend issues detected")
    
    # Step 2: Trigger redeploy
    print("\n🔄 Railway redeploy required...")
    trigger_railway_redeploy()
    
    print("\n" + "=" * 60)
    print("📋 MANUAL STEPS REQUIRED:")
    print("1. The backend code changes are ready in app/auth/auth_router.py")
    print("2. Railway needs to redeploy to pick up the new Kite endpoints")
    print("3. If you have Railway CLI, run: railway up")
    print("4. Or push changes to trigger automatic redeploy")
    print("=" * 60)
    
    # Step 3: Wait for user to trigger redeploy
    input("\n⏸️  Press Enter after triggering Railway redeploy...")
    
    # Step 4: Wait for deployment
    if wait_for_deployment():
        print("✅ Deployment successful!")
        
        # Step 5: Final test
        if test_complete_backend():
            print("🎉 All systems operational!")
            return True
        else:
            print("⚠️ Some issues remain")
            return False
    else:
        print("❌ Deployment verification failed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)