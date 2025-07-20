#!/usr/bin/env python3
"""
Portfolio API Tests
"""
import requests
import json

def test_portfolio_endpoints():
    """Test portfolio API endpoints"""
    backend_url = "https://web-production-de0bc.up.railway.app"
    test_user_id = "test_user_123"
    
    print("🧪 Testing Portfolio Endpoints")
    print("=" * 50)
    
    # Test portfolio status
    print("\n1. Testing portfolio status...")
    response = requests.get(f"{backend_url}/api/portfolio/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    
    # Test mock portfolio data
    print("\n2. Testing mock portfolio data...")
    response = requests.get(f"{backend_url}/api/portfolio/mock?user_id={test_user_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Portfolio value: {data.get('data', {}).get('total_value', 'N/A')}")
    
    print("\n✅ Portfolio tests completed!")

if __name__ == "__main__":
    test_portfolio_endpoints()