#!/usr/bin/env python3
"""
Test basic endpoints to see what's actually working
"""

import requests
import json

def test_basic_endpoints():
    base_url = "https://quantumleap-trading-backend-production.up.railway.app"
    
    endpoints_to_test = [
        "/",
        "/health", 
        "/status",
        "/docs",
        "/api"
    ]
    
    print("Testing basic endpoints...")
    print("=" * 50)
    
    for endpoint in endpoints_to_test:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            
            print(f"GET {endpoint}")
            print(f"  Status: {response.status_code}")
            print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)}")
                except:
                    print(f"  Response: {response.text[:200]}...")
            else:
                print(f"  Error: {response.text[:100]}...")
            
            print()
            
        except Exception as e:
            print(f"GET {endpoint}")
            print(f"  Error: {str(e)}")
            print()

if __name__ == "__main__":
    test_basic_endpoints()