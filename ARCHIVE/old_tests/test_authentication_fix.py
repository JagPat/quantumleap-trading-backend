#!/usr/bin/env python3
"""
Test Authentication Fix for AI Endpoints
Validates that the authentication token fix resolves the 403 Forbidden errors
"""

import requests
import json
import time
from datetime import datetime

def test_authentication_fix():
    """Test the authentication fix for AI endpoints"""
    
    print("🧪 Testing Authentication Fix for AI Endpoints")
    print("=" * 60)
    
    backend_url = "https://web-production-de0bc.up.railway.app"
    test_credentials = {
        "email": "test@quantumleap.com",
        "password": "testpassword123"
    }
    
    # Step 1: Login to get JWT token
    print("\n1️⃣ Testing Login to Get JWT Token")
    try:
        login_response = requests.post(
            f"{backend_url}/api/auth/login",
            json=test_credentials,
            timeout=10
        )
        
        print(f"   Login response status: {login_response.status_code}")
        print(f"   Login response: {login_response.text[:200]}...")
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            token = login_data.get('access_token')
            user_id = login_data.get('user_id')
            
            print(f"✅ Login successful!")
            print(f"   User ID: {user_id}")
            print(f"   Token: {token[:20]}..." if token else "   Token: None")
            
            if not token:
                print("❌ No access token received from login")
                return False
                
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False
    
    # Step 2: Test AI endpoints with authentication
    print("\n2️⃣ Testing AI Endpoints with Authentication")
    
    auth_headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    ai_endpoints = [
        {
            'name': 'AI Strategy Templates',
            'method': 'GET',
            'url': f'{backend_url}/api/ai/strategy-templates',
            'expected_status': [200, 401]
        },
        {
            'name': 'AI Risk Metrics',
            'method': 'GET', 
            'url': f'{backend_url}/api/ai/risk-metrics',
            'expected_status': [200, 401]
        },
        {
            'name': 'AI Chat',
            'method': 'POST',
            'url': f'{backend_url}/api/ai/chat',
            'data': {'message': 'Hello, test message'},
            'expected_status': [200, 401, 422]
        },
        {
            'name': 'AI Performance Analytics',
            'method': 'POST',
            'url': f'{backend_url}/api/ai/performance-analytics',
            'data': {'timeframe': '1M'},
            'expected_status': [200, 401, 422]
        },
        {
            'name': 'AI Market Intelligence',
            'method': 'POST',
            'url': f'{backend_url}/api/ai/market-intelligence',
            'data': {'symbol': 'NIFTY50'},
            'expected_status': [200, 401, 422]
        }
    ]
    
    results = []
    
    for endpoint in ai_endpoints:
        try:
            print(f"\n   Testing {endpoint['name']}...")
            
            if endpoint['method'] == 'GET':
                response = requests.get(
                    endpoint['url'],
                    headers=auth_headers,
                    timeout=10
                )
            else:
                response = requests.post(
                    endpoint['url'],
                    headers=auth_headers,
                    json=endpoint.get('data', {}),
                    timeout=10
                )
            
            status_code = response.status_code
            
            if status_code in endpoint['expected_status']:
                if status_code == 403:
                    print(f"   ❌ Still getting 403 Forbidden (auth not working)")
                    results.append({'name': endpoint['name'], 'status': 'failed', 'code': status_code})
                else:
                    print(f"   ✅ Success: {status_code}")
                    results.append({'name': endpoint['name'], 'status': 'passed', 'code': status_code})
            else:
                print(f"   ⚠️  Unexpected status: {status_code}")
                results.append({'name': endpoint['name'], 'status': 'unexpected', 'code': status_code})
                
            # Show response preview
            try:
                response_data = response.json()
                if isinstance(response_data, dict):
                    preview = str(response_data)[:100] + "..." if len(str(response_data)) > 100 else str(response_data)
                    print(f"   Response: {preview}")
            except:
                print(f"   Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results.append({'name': endpoint['name'], 'status': 'error', 'error': str(e)})
    
    # Step 3: Test without authentication (should get 403)
    print("\n3️⃣ Testing AI Endpoints WITHOUT Authentication (Should Get 403)")
    
    try:
        no_auth_response = requests.get(
            f"{backend_url}/api/ai/strategy-templates",
            timeout=10
        )
        
        if no_auth_response.status_code == 403:
            print("   ✅ Correctly returns 403 without authentication")
        else:
            print(f"   ⚠️  Unexpected status without auth: {no_auth_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing without auth: {str(e)}")
    
    # Step 4: Summary
    print("\n4️⃣ Test Results Summary")
    print("=" * 40)
    
    passed = len([r for r in results if r['status'] == 'passed'])
    failed = len([r for r in results if r['status'] == 'failed'])
    errors = len([r for r in results if r['status'] == 'error'])
    unexpected = len([r for r in results if r['status'] == 'unexpected'])
    
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed (403): {failed}")
    print(f"⚠️  Unexpected: {unexpected}")
    print(f"🔥 Errors: {errors}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if failed == 0:
        print("\n🎉 Authentication fix successful! No more 403 errors.")
        return True
    else:
        print(f"\n⚠️  Authentication fix partially successful. {failed} endpoints still return 403.")
        return False

if __name__ == "__main__":
    success = test_authentication_fix()
    exit(0 if success else 1)