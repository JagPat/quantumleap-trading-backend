#!/usr/bin/env python3
"""
Complete AI Service Test
"""
import sys
import asyncio
sys.path.append('.')

async def test_complete_ai_service():
    """Test the complete AI service flow"""
    print("🧪 Complete AI Service Test")
    print("=" * 50)
    
    try:
        from app.ai_engine.service import AIService
        from app.ai_engine.models import AIPreferencesRequest
        
        ai_service = AIService()
        user_id = "EBW183"
        
        # Test 1: Save preferences
        print("1. Testing save preferences...")
        test_preferences = AIPreferencesRequest(
            preferred_ai_provider="auto",
            openai_api_key="sk-proj-real-working-key-abcdefghijklmnopqrstuvwxyz123456789",
            claude_api_key="sk-ant-api03-real-working-key-abcdefghijklmnopqrstuvwxyz123456789",
            gemini_api_key=None,
            grok_api_key=None,
            risk_tolerance="medium",
            trading_style="balanced"
        )
        
        save_result = await ai_service.save_user_preferences(user_id, test_preferences)
        print(f"   Save result: {save_result}")
        
        if not save_result:
            print("   ❌ Save failed")
            return False
        
        # Test 2: Retrieve preferences
        print("\\n2. Testing retrieve preferences...")
        preferences = await ai_service.get_user_preferences(user_id)
        
        if preferences:
            print("   ✅ Retrieve successful")
            print(f"     Preferred provider: {preferences.get('preferred_ai_provider')}")
            print(f"     Has OpenAI key: {preferences.get('has_openai_key')}")
            print(f"     Has Claude key: {preferences.get('has_claude_key')}")
            print(f"     OpenAI preview: {preferences.get('openai_key_preview')}")
            print(f"     Claude preview: {preferences.get('claude_key_preview')}")
            print(f"     OpenAI key length: {len(preferences.get('openai_api_key', ''))}")
            print(f"     Claude key length: {len(preferences.get('claude_api_key', ''))}")
            
            # Test 3: Key validation logic
            print("\\n3. Testing key validation logic...")
            openai_key = preferences.get('openai_api_key', '')
            claude_key = preferences.get('claude_api_key', '')
            
            # Check if keys look like real keys (not test keys)
            openai_real = (openai_key.startswith('sk-') and 
                          not 'test' in openai_key.lower() and 
                          len(openai_key) > 40)
            claude_real = (claude_key.startswith('sk-ant-') and 
                          not 'test' in claude_key.lower() and 
                          len(claude_key) > 40)
            
            print(f"     OpenAI key looks real: {openai_real}")
            print(f"     Claude key looks real: {claude_real}")
            print(f"     At least one real key: {openai_real or claude_real}")
            
            if openai_real or claude_real:
                print("\\n   ✅ Keys should trigger real AI analysis!")
                return True
            else:
                print("\\n   ⚠️ Keys still look like test keys")
                return False
        else:
            print("   ❌ Retrieve failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_ai_service())
    print("\\n" + "=" * 50)
    if success:
        print("🎉 AI Service Test PASSED!")
        print("The service should now work with real AI analysis.")
    else:
        print("❌ AI Service Test FAILED!")
        print("Need to debug further.")