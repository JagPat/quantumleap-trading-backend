#!/usr/bin/env python3
"""
Create Test User for Authentication Testing
"""

import requests
import json

def create_test_user():
    """Create a test user for authentication testing"""
    
    backend_url = "https://web-production-de0bc.up.railway.app"
    
    # Test user data
    test_user = {
        "email": "test@quantumleap.com",
        "password": "test123",
        "full_name": "Test User"
    }
    
    print("🔧 Creating test user for authentication...")
    print(f"Email: {test_user['email']}")
    print(f"Password: {test_user['password']}")
    
    # Try to create user via registration endpoint
    try:
        response = requests.post(
            f"{backend_url}/api/auth/register",
            json=test_user,
            timeout=10
        )
        
        print(f"Registration response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test user created successfully!")
            return True
        else:
            print(f"⚠️  Registration returned: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
    
    # Try to login with the test credentials
    print("\n🧪 Testing login with test credentials...")
    
    login_data = {
        "email": "test@quantumleap.com", 
        "password": "test123"
    }
    
    try:
        login_response = requests.post(
            f"{backend_url}/api/auth/login",
            json=login_data,
            timeout=10
        )
        
        print(f"Login response: {login_response.status_code}")
        print(f"Response body: {login_response.text}")
        
        if login_response.status_code == 200:
            print("✅ Login successful!")
            return True
        else:
            print(f"⚠️  Login failed: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
    
    return False

if __name__ == "__main__":
    create_test_user()