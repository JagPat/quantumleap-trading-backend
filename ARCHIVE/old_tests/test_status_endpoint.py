#!/usr/bin/env python3
"""
Test the status endpoint to see what routers are loaded
"""

import requests
import json

def test_status_endpoint():
    """Test the status endpoint to see loaded routers"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    status_url = f"{base_url}/status"
    
    print("📊 Testing Status Endpoint on Live Railway Deployment")
    print("=" * 60)
    print(f"📍 Status URL: {status_url}")
    print()
    
    try:
        print("Making request to /status endpoint...")
        response = requests.get(status_url, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response.elapsed.total_seconds() * 1000:.2f}ms")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS - Status endpoint is working!")
            try:
                data = response.json()
                print("Loaded Routers:")
                print(json.dumps(data, indent=2))
                
                if 'routers_loaded' in data:
                    print(f"\n📋 Router Summary:")
                    for router in data['routers_loaded']:
                        print(f"   ✅ {router}")
                    print(f"\n📊 Total Routers Loaded: {len(data['routers_loaded'])}")
                
            except:
                print("Response Text:")
                print(response.text)
        else:
            print(f"❌ FAILED - Status code: {response.status_code}")
            print("Response:")
            print(response.text)
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        return False

if __name__ == "__main__":
    success = test_status_endpoint()
    exit(0 if success else 1)