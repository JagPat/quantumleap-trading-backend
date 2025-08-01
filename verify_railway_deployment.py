#!/usr/bin/env python3
"""
Railway Deployment Verification Script
"""

import requests
import time
import sys
from datetime import datetime

def verify_deployment(base_url, max_retries=10, retry_delay=30):
    """Verify Railway deployment is working"""
    print(f"🔍 Verifying deployment at {base_url}")
    
    for attempt in range(max_retries):
        try:
            # Test health endpoint
            response = requests.get(f"{base_url}/health", timeout=30)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data.get('status', 'unknown')}")
                
                # Test trading engine status
                response = requests.get(f"{base_url}/api/trading-engine/status", timeout=30)
                if response.status_code == 200:
                    print("✅ Trading engine endpoint accessible")
                    
                    # Test metrics endpoint
                    response = requests.get(f"{base_url}/metrics", timeout=30)
                    if response.status_code == 200:
                        print("✅ Metrics endpoint accessible")
                        print("🎉 Deployment verification successful!")
                        return True
                    else:
                        print(f"⚠️ Metrics endpoint returned {response.status_code}")
                else:
                    print(f"⚠️ Trading engine endpoint returned {response.status_code}")
            else:
                print(f"❌ Health check failed: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            print(f"⏳ Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
    
    print("❌ Deployment verification failed after all retries")
    return False

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "https://quantum-leap-backend-production.up.railway.app"
    success = verify_deployment(base_url)
    sys.exit(0 if success else 1)
