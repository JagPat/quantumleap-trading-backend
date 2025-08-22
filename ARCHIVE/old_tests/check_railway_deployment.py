#!/usr/bin/env python3
"""
Check Railway deployment status and trigger redeploy if needed
"""

import requests
import time
import json

def check_deployment_status():
    """Check if the Railway deployment is working"""
    
    base_url = "https://quantumleap-trading-backend-production.up.railway.app"
    
    print("🔍 Checking Railway Deployment Status...")
    print(f"📍 URL: {base_url}")
    print("=" * 60)
    
    # Test basic connectivity
    try:
        print("1. Testing basic connectivity...")
        response = requests.get(base_url, timeout=30)
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        print(f"   Content: {response.text[:500]}...")
        
        if "Application not found" in response.text:
            print("   ❌ Railway deployment is not running or failed")
            return False
        elif response.status_code == 200:
            print("   ✅ Application is responding")
            return True
        else:
            print(f"   ⚠️  Application returned status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out - application may be starting up")
        return False
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection failed - deployment may be down")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def wait_for_deployment(max_wait_minutes=10):
    """Wait for deployment to become available"""
    
    print(f"\n⏳ Waiting for deployment (max {max_wait_minutes} minutes)...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while time.time() - start_time < max_wait_seconds:
        if check_deployment_status():
            elapsed = int(time.time() - start_time)
            print(f"✅ Deployment is ready! (took {elapsed} seconds)")
            return True
        
        print("   ⏳ Still waiting... (checking again in 30 seconds)")
        time.sleep(30)
    
    print(f"❌ Deployment did not become ready within {max_wait_minutes} minutes")
    return False

def main():
    """Main function"""
    
    print("🚀 Railway Deployment Checker")
    print("=" * 60)
    
    # Check current status
    if check_deployment_status():
        print("\n✅ Deployment is already working!")
        return 0
    
    print("\n📝 Deployment Status Analysis:")
    print("   The deployment appears to be down or failed.")
    print("   This could be due to:")
    print("   1. Recent code changes that broke the deployment")
    print("   2. Environment variable issues (like the CORS_ORIGINS fix)")
    print("   3. Railway platform issues")
    print("   4. Application startup errors")
    
    print("\n🔧 Recommended Actions:")
    print("   1. Check Railway dashboard for deployment logs")
    print("   2. Verify environment variables are set correctly")
    print("   3. Trigger a manual redeploy if needed")
    print("   4. Check for any startup errors in the logs")
    
    # Wait for deployment to come back up
    if wait_for_deployment():
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())