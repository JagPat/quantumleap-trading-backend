#!/usr/bin/env python3
"""
Test AI Portfolio Analysis Complete Flow
"""
import requests
import json
import time

BASE_URL = "https://web-production-de0bc.up.railway.app"
USER_ID = "EBW183"

def test_ai_preferences_flow():
    """Test the complete AI preferences flow"""
    print("🧪 Testing AI Preferences Flow")
    print("=" * 50)
    
    # Test 1: Get current preferences
    print("1. Getting current AI preferences...")
    response = requests.get(
        f"{BASE_URL}/api/ai/preferences",
        headers={"X-User-ID": USER_ID}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        prefs = response.json()
        print(f"   Current preferences: {prefs.get('preferences', {})}")
    
    # Test 2: Save new preferences
    print("\n2. Saving new AI preferences...")
    test_preferences = {
        "preferred_ai_provider": "auto",
        "openai_api_key": "sk-test-key-12345",
        "claude_api_key": None,
        "gemini_api_key": None
    }
    
    response = requests.post(
        f"{BASE_URL}/api/ai/preferences",
        headers={
            "X-User-ID": USER_ID,
            "Content-Type": "application/json"
        },
        json=test_preferences
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Save result: {result}")
    
    # Test 3: Verify preferences were saved
    print("\n3. Verifying preferences were saved...")
    time.sleep(1)  # Small delay
    response = requests.get(
        f"{BASE_URL}/api/ai/preferences",
        headers={"X-User-ID": USER_ID}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        prefs = response.json()
        saved_prefs = prefs.get('preferences', {})
        print(f"   Saved preferences: {saved_prefs}")
        
        # Check if OpenAI key was saved
        if saved_prefs.get('has_openai_key'):
            print("   ✅ OpenAI key was saved successfully")
        else:
            print("   ❌ OpenAI key was not saved")
    
    return True

def test_portfolio_analysis_flow():
    """Test the portfolio analysis flow"""
    print("\n🧪 Testing Portfolio Analysis Flow")
    print("=" * 50)
    
    # Sample portfolio data
    portfolio_data = {
        "total_value": 1000000,
        "holdings": [
            {
                "symbol": "RELIANCE",
                "quantity": 100,
                "current_value": 250000,
                "allocation_percentage": 25.0
            },
            {
                "symbol": "TCS",
                "quantity": 50,
                "current_value": 200000,
                "allocation_percentage": 20.0
            },
            {
                "symbol": "HDFCBANK",
                "quantity": 150,
                "current_value": 300000,
                "allocation_percentage": 30.0
            }
        ]
    }
    
    # Test portfolio analysis
    print("1. Running portfolio analysis...")
    response = requests.post(
        f"{BASE_URL}/api/ai/analysis/portfolio",
        headers={
            "X-User-ID": USER_ID,
            "Content-Type": "application/json"
        },
        json=portfolio_data
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Analysis status: {result.get('status')}")
        print(f"   Fallback mode: {result.get('fallback_mode', False)}")
        
        if result.get('analysis'):
            analysis = result['analysis']
            print(f"   Health score: {analysis.get('health_score', 'N/A')}")
            print(f"   Risk level: {analysis.get('risk_level', 'N/A')}")
            print(f"   Recommendations: {len(analysis.get('recommendations', []))}")
        
        if not result.get('fallback_mode'):
            print("   ✅ Real AI analysis working")
        else:
            print("   ⚠️ Using fallback mode")
    else:
        print(f"   ❌ Analysis failed: {response.text}")
    
    return True

def test_ai_status():
    """Test AI status endpoint"""
    print("\n🧪 Testing AI Status")
    print("=" * 50)
    
    response = requests.get(
        f"{BASE_URL}/api/ai/status",
        headers={"X-User-ID": USER_ID}
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        status = response.json()
        print(f"   AI Status: {status.get('status')}")
        print(f"   Engine: {status.get('engine')}")
        print(f"   Configured providers: {status.get('configured_providers', [])}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 AI Portfolio Analysis Complete Flow Test")
    print("=" * 60)
    
    try:
        # Test AI preferences
        test_ai_preferences_flow()
        
        # Test AI status
        test_ai_status()
        
        # Test portfolio analysis
        test_portfolio_analysis_flow()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        print("\nNext steps:")
        print("1. Refresh your frontend")
        print("2. Go to Settings → AI Settings")
        print("3. Add your real API keys")
        print("4. Test portfolio analysis")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()