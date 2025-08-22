#!/usr/bin/env python3
"""
Check Railway Deployment Status

Monitor the Railway deployment and test when it's ready.
"""

import requests
import time
from datetime import datetime

def check_deployment_status():
    """Check if the Railway deployment is healthy"""
    url = "https://quantum-leap-backend-production.up.railway.app/health"
    
    print(f"🔍 Checking deployment status at: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print("✅ Deployment is healthy!")
                return True
            else:
                print(f"⚠️  Deployment responded but not healthy: {data}")
                return False
        else:
            print(f"❌ Deployment not ready (Status: {response.status_code})")
            if response.status_code == 404:
                print("   This usually means the deployment is still starting up")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def wait_for_deployment(max_wait_minutes=10):
    """Wait for deployment to be ready"""
    print(f"⏳ Waiting for Railway deployment (max {max_wait_minutes} minutes)...")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while time.time() - start_time < max_wait_seconds:
        if check_deployment_status():
            elapsed = int(time.time() - start_time)
            print(f"🎉 Deployment ready after {elapsed} seconds!")
            return True
        
        print("   Waiting 30 seconds before next check...")
        time.sleep(30)
    
    print(f"⏰ Timeout: Deployment not ready after {max_wait_minutes} minutes")
    return False

def test_ai_endpoints():
    """Test a few AI endpoints to verify they're working"""
    base_url = "https://quantum-leap-backend-production.up.railway.app/api/ai"
    
    endpoints_to_test = [
        "/health",
        "/chat",
        "/strategy-templates"
    ]
    
    print("\n🧪 Testing AI endpoints...")
    
    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        print(f"\n   Testing: {endpoint}")
        
        try:
            if endpoint == "/chat":
                # POST request for chat
                response = requests.post(url, json={
                    "message": "Test message",
                    "context": "trading"
                }, timeout=10)
            else:
                # GET request for others
                response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ {endpoint} - Working")
            else:
                print(f"   ❌ {endpoint} - Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {endpoint} - Error: {str(e)}")

def main():
    """Main function"""
    print("🚀 RAILWAY DEPLOYMENT STATUS CHECK")
    print("=" * 50)
    print(f"   Timestamp: {datetime.now()}")
    print("=" * 50)
    
    # Wait for deployment to be ready
    if wait_for_deployment():
        # Test AI endpoints
        test_ai_endpoints()
        
        print("\n✅ Deployment is ready! You can now run:")
        print("   python3 test_ai_features_integration.py")
        
        return True
    else:
        print("\n❌ Deployment is not ready. Check Railway logs for issues.")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check Railway dashboard for deployment logs")
        print("   2. Verify Dockerfile and start.sh are correct")
        print("   3. Ensure health endpoint returns 200 OK")
        print("   4. Check if all dependencies are installed")
        
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)