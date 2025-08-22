#!/usr/bin/env python3
"""
Test the health endpoint on the live Railway deployment
"""

import requests
import json

def test_health_endpoint():
    """Test the health endpoint to confirm deployment is working"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    health_url = f"{base_url}/health"
    
    print("🏥 Testing Health Endpoint on Live Railway Deployment")
    print("=" * 60)
    print(f"📍 Base URL: {base_url}")
    print(f"🔍 Health URL: {health_url}")
    print()
    
    try:
        print("Making request to /health endpoint...")
        response = requests.get(health_url, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response.elapsed.total_seconds() * 1000:.2f}ms")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS - Health endpoint is working!")
            try:
                data = response.json()
                print("Response Data:")
                print(json.dumps(data, indent=2))
            except:
                print("Response Text:")
                print(response.text)
        else:
            print(f"❌ FAILED - Status code: {response.status_code}")
            print("Response:")
            print(response.text)
            
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT - Request took too long")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR - Could not connect to server")
        return False
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        return False

if __name__ == "__main__":
    success = test_health_endpoint()
    exit(0 if success else 1)