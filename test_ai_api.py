#!/usr/bin/env python3
"""
Test script for AI preferences API endpoints
"""
import requests
import json
import time

# Railway deployment URL
BASE_URL = "https://web-production-de0bc.up.railway.app"

def test_ai_preferences_api():
    """Test AI preferences API endpoints"""
    print("🧪 Testing AI Preferences API Endpoints")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    
    # Test user ID
    test_user_id = "EBW183"
    headers = {"X-User-ID": test_user_id, "Content-Type": "application/json"}
    
    # Test 1: Get preferences (should return no_key initially)
    print(f"\n1. Getting AI preferences for user {test_user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/preferences", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Save preferences
    print(f"\n2. Saving AI preferences for user {test_user_id}...")
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
    
    # Test 3: Get preferences again (should return saved data)
    print(f"\n3. Getting AI preferences again for user {test_user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/preferences", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 4: Update preferences
    print(f"\n4. Updating AI preferences for user {test_user_id}...")
    update_data = {
        "openai_api_key": "sk-updated-openai-key-999",
        "claude_api_key": "",  # Remove Claude key
        "gemini_api_key": "AIza-updated-gemini-key-888",
        "preferred_ai_provider": "gemini"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/preferences", 
            headers=headers,
            json=update_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 5: Get preferences after update
    print(f"\n5. Getting AI preferences after update for user {test_user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/preferences", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 6: Test without user ID header
    print(f"\n6. Testing without X-User-ID header...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/preferences", headers={"Content-Type": "application/json"})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 7: Test AI status endpoint
    print(f"\n7. Testing AI status endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/ai/status")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Preferences API Test Complete!")

if __name__ == "__main__":
    test_ai_preferences_api() 