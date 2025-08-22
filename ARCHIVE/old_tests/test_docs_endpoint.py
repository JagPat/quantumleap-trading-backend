#!/usr/bin/env python3
"""
Test the docs endpoint to see what routes are actually available
"""

import requests

def test_docs_endpoint():
    """Test the docs endpoint to see available routes"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    docs_url = f"{base_url}/docs"
    
    print("📚 Testing Docs Endpoint on Live Railway Deployment")
    print("=" * 60)
    print(f"📍 Docs URL: {docs_url}")
    print()
    
    try:
        print("Making request to /docs endpoint...")
        response = requests.get(docs_url, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response.elapsed.total_seconds() * 1000:.2f}ms")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS - Docs endpoint is working!")
            print("You can view the API documentation at:")
            print(f"   {docs_url}")
            print()
            print("This will show all available endpoints and their schemas.")
        else:
            print(f"❌ FAILED - Status code: {response.status_code}")
            print("Response:")
            print(response.text[:500])
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        return False

def test_openapi_json():
    """Test the OpenAPI JSON endpoint to get route information"""
    
    base_url = "https://web-production-de0bc.up.railway.app"
    openapi_url = f"{base_url}/openapi.json"
    
    print("🔍 Testing OpenAPI JSON endpoint...")
    print(f"📍 OpenAPI URL: {openapi_url}")
    print()
    
    try:
        response = requests.get(openapi_url, timeout=30)
        
        if response.status_code == 200:
            print("✅ SUCCESS - OpenAPI JSON is available!")
            
            import json
            data = response.json()
            
            if 'paths' in data:
                print(f"\n📋 Available API Paths:")
                paths = list(data['paths'].keys())
                paths.sort()
                
                for path in paths:
                    methods = list(data['paths'][path].keys())
                    methods_str = ', '.join(methods).upper()
                    print(f"   {methods_str} {path}")
                
                print(f"\n📊 Total Endpoints: {len(paths)}")
            
            return True
        else:
            print(f"❌ FAILED - Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Railway API Documentation Check")
    print("=" * 60)
    
    docs_success = test_docs_endpoint()
    print()
    openapi_success = test_openapi_json()
    
    if docs_success or openapi_success:
        exit(0)
    else:
        exit(1)