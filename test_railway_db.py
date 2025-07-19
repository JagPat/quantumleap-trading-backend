#!/usr/bin/env python3
"""
Test script to verify database functions work on Railway
"""
import requests
import json

# Railway deployment URL
BASE_URL = "https://web-production-de0bc.up.railway.app"

def test_railway_database():
    """Test database functions on Railway"""
    print("🧪 Testing Railway Database Functions")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    
    # Test user ID
    test_user_id = "EBW183"
    headers = {"X-User-ID": test_user_id, "Content-Type": "application/json"}
    
    # Test 1: Check if database is accessible via health endpoint
    print(f"\n1. Checking database health...")
    try:
        response = requests.get(f"{BASE_URL}/readyz")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Try to save preferences with valid data
    print(f"\n2. Saving AI preferences with valid data...")
    preferences_data = {
        "openai_api_key": "sk-test-openai-key-123",
        "claude_api_key": "sk-ant-test-claude-key-456",
        "gemini_api_key": "AIza-test-gemini-key-789",
        "preferred_ai_provider": "openai"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/preferences", 
            headers=headers,
            json=preferences_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 3: Try to save preferences with empty keys (should fail)
    print(f"\n3. Saving AI preferences with empty keys (should fail)...")
    empty_preferences = {
        "openai_api_key": "",
        "claude_api_key": "",
        "gemini_api_key": "",
        "preferred_ai_provider": "auto"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/preferences", 
            headers=headers,
            json=empty_preferences
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 4: Try to save preferences with partial data
    print(f"\n4. Saving AI preferences with partial data...")
    partial_preferences = {
        "openai_api_key": "sk-test-openai-key-123",
        "claude_api_key": "",
        "gemini_api_key": "",
        "preferred_ai_provider": "openai"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/preferences", 
            headers=headers,
            json=partial_preferences
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Railway Database Test Complete!")

if __name__ == "__main__":
    test_railway_database() 