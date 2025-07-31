#!/usr/bin/env python3
"""
Test with Real API Key Formats
"""
import requests
import json
import time

def test_with_real_formats():
    """Test with realistic API key formats"""
    print("🧪 Testing with Realistic API Key Formats")
    print("=" * 60)
    
    base_url = "https://web-production-de0bc.up.railway.app"
    user_id = "EBW183"
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": user_id
    }
    
    try:
        # Step 1: Save realistic API keys (longer, more realistic format)
        print("1. Saving realistic API keys...")
        save_data = {
            "preferred_ai_provider": "auto",
            "openai_api_key": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ",  # 62 chars
            "claude_api_key": "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 70+ chars
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
        
        # Step 2: Wait for database update
        print("\\n2. Waiting for database update...")
        time.sleep(2)
        
        # Step 3: Retrieve preferences to verify save
        print("\\n3. Retrieving saved preferences...")
        response = requests.get(
            f"{base_url}/api/ai/preferences",
            headers=headers,
            timeout=10
        )
        
        get_result = response.json()
        if get_result.get('status') == 'success' and get_result.get('preferences'):
            prefs = get_result['preferences']
            print(f"     OpenAI key: {prefs.get('openai_key_preview', 'None')}")
            print(f"     Claude key: {prefs.get('claude_key_preview', 'None')}")
            print(f"     Has OpenAI: {prefs.get('has_openai_key', False)}")
            print(f"     Has Claude: {prefs.get('has_claude_key', False)}")
            
            # Check key lengths (should be longer now)
            openai_key = prefs.get('openai_api_key', '')
            claude_key = prefs.get('claude_api_key', '')
            print(f"     OpenAI key length: {len(openai_key)}")
            print(f"     Claude key length: {len(claude_key)}")
            
            # Check if keys look like test keys
            openai_is_test = 'test' in openai_key.lower() if openai_key else True
            claude_is_test = 'test' in claude_key.lower() if claude_key else True
            print(f"     OpenAI appears to be test key: {openai_is_test}")
            print(f"     Claude appears to be test key: {claude_is_test}")
        
        # Step 4: Test portfolio analysis
        print("\\n4. Testing portfolio analysis...")
        portfolio_data = {
            "total_value": 1000000,
            "holdings": [
                {
                    "symbol": "RELIANCE",
                    "quantity": 100,
                    "current_value": 250000
                }
            ]
        }
        
        response = requests.post(
            f"{base_url}/api/ai/simple-analysis/portfolio",
            headers=headers,
            json=portfolio_data,
            timeout=30
        )
        
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
            
            # Let's check what the backend thinks about the keys
            print("\\n5. Debugging key validation...")
            # The issue might be in the key validation logic
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_with_real_formats()
    print("\\n" + "=" * 60)
    if success:
        print("🎉 Test PASSED - Real AI analysis working!")
    else:
        print("❌ Test FAILED - Need to debug key validation logic")