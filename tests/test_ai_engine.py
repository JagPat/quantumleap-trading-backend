#!/usr/bin/env python3
"""
Test script for AI Key Validation Endpoint
Tests the new live validation functionality
"""

import requests
import json

# Backend URL
BACKEND_URL = "https://web-production-de0bc.up.railway.app"

def test_ai_validation():
    """Test the AI key validation endpoint"""
    
    print("🧪 Testing AI Key Validation Endpoint")
    print("=" * 50)
    
    # Test 1: Empty API key
    print("\n1. Testing empty API key...")
    response = requests.post(
        f"{BACKEND_URL}/api/ai/validate-key",
        json={"provider": "openai", "api_key": ""},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test 2: Invalid provider
    print("\n2. Testing invalid provider...")
    response = requests.post(
        f"{BACKEND_URL}/api/ai/validate-key",
        json={"provider": "invalid", "api_key": "test123"},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test 3: Test OpenAI format (should fail with invalid key)
    print("\n3. Testing OpenAI with invalid key...")
    response = requests.post(
        f"{BACKEND_URL}/api/ai/validate-key",
        json={"provider": "openai", "api_key": "sk-test123456789012345678901234567890"},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test 4: Test Claude format (should fail with invalid key)
    print("\n4. Testing Claude with invalid key...")
    response = requests.post(
        f"{BACKEND_URL}/api/ai/validate-key",
        json={"provider": "claude", "api_key": "sk-ant-test123456789012345678901234567890"},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    test_ai_validation() 