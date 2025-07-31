#!/usr/bin/env python3
"""
Test AI Save and Analyze Flow
"""
import requests
import json
import time

def test_ai_flow():
    """Test the complete AI save and analyze flow"""
    print("🧪 Testing AI Save and Analyze Flow")
    print("=" * 60)
    
    base_url = "https://web-production-de0bc.up.railway.app"
    user_id = "EBW183"
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": user_id
    }
    
    try:
        # Step 1: Save real API keys
        print("1. Saving real API keys...")
        save_data = {
            "preferred_ai_provider": "auto",
            "openai_api_key": "sk-proj-real-working-key-123456789",  # Fake but realistic format
            "claude_api_key": "sk-ant-api03-real-working-key-123456789"  # Fake but realistic format
        }
        
        response = requests.post(
            f"{base_url}/api/ai/preferences",
            headers=headers,
            json=save_data,
            timeout=10
        )
        
        print(f"   Save response: {response.status_code}")
        save_result = response.json()
        print(f"   Save result: {save_result}")
        
        if save_result.get('status') != 'success':
            print("❌ Failed to save preferences")
            return False
        
        # Step 2: Wait a moment for database to update
        print("\\n2. Waiting for database update...")
        time.sleep(2)
        
        # Step 3: Retrieve preferences to verify save
        print("\\n3. Retrieving saved preferences...")
        response = requests.get(
            f"{base_url}/api/ai/preferences",
            headers=headers,
            timeout=10
        )
        
        print(f"   Get response: {response.status_code}")
        get_result = response.json()
        print(f"   Retrieved preferences:")
        if get_result.get('status') == 'success' and get_result.get('preferences'):
            prefs = get_result['preferences']
            print(f"     OpenAI key: {prefs.get('openai_key_preview', 'None')}")
            print(f"     Claude key: {prefs.get('claude_key_preview', 'None')}")
            print(f"     Has OpenAI: {prefs.get('has_openai_key', False)}")
            print(f"     Has Claude: {prefs.get('has_claude_key', False)}")
        else:
            print("     ❌ Failed to retrieve preferences")
            return False
        
        # Step 4: Test portfolio analysis
        print("\\n4. Testing portfolio analysis...")
        portfolio_data = {
            "total_value": 1000000,
            "holdings": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 100,
                    "current_value": 250000
                },
                {
                    "symbol": "TCS",
                    "quantity": 50,
                    "current_value": 200000
                }
            ]
        }
        
        response = requests.post(
            f"{base_url}/api/ai/simple-analysis/portfolio",
            headers=headers,
            json=portfolio_data,
            timeout=30
        )
        
        print(f"   Analysis response: {response.status_code}")
        analysis_result = response.json()
        print(f"   Analysis status: {analysis_result.get('status')}")
        print(f"   Fallback mode: {analysis_result.get('fallback_mode')}")
        print(f"   Provider used: {analysis_result.get('provider_used')}")
        print(f"   Message: {analysis_result.get('message')}")
        
        if analysis_result.get('fallback_mode') == False:
            print("   ✅ Real AI analysis working!")
            return True
        else:
            print("   ⚠️ Still using fallback mode")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ai_flow()
    print("\\n" + "=" * 60)
    if success:
        print("🎉 AI flow test PASSED - Real AI analysis working!")
    else:
        print("❌ AI flow test FAILED - Still using fallback mode")