#!/usr/bin/env python3
"""
Debug AI Service Issue
"""
import sys
import os
sys.path.append('.')

def debug_ai_service():
    """Debug the AI service issue"""
    print("🔍 Debugging AI Service Issue")
    print("=" * 50)
    
    try:
        # Test 1: Check if we can import the service
        print("1. Testing AI service import...")
        try:
            from app.ai_engine.service import AIService, AIEngineService
            print("   ✅ AIService import successful")
            print("   ✅ AIEngineService import successful")
        except ImportError as e:
            print(f"   ❌ Import failed: {e}")
            return False
        
        # Test 2: Check if we can create an instance
        print("\\n2. Testing AI service instantiation...")
        try:
            ai_service = AIService()
            print("   ✅ AIService instance created")
        except Exception as e:
            print(f"   ❌ Instantiation failed: {e}")
            return False
        
        # Test 3: Check encryption setup
        print("\\n3. Testing encryption setup...")
        try:
            from app.core.config import settings
            print(f"   Encryption key configured: {bool(settings.encryption_key)}")
            
            # Test encryption/decryption
            test_key = "sk-test-key-123"
            encrypted = ai_service.encrypt_api_key(test_key)
            decrypted = ai_service.decrypt_api_key(encrypted)
            print(f"   Encryption test: {test_key} -> {encrypted[:20]}... -> {decrypted}")
            print(f"   Encryption working: {test_key == decrypted}")
        except Exception as e:
            print(f"   ❌ Encryption test failed: {e}")
        
        # Test 4: Check database connection
        print("\\n4. Testing database operations...")
        try:
            import asyncio
            
            async def test_db_ops():
                # Test get preferences
                prefs = await ai_service.get_user_preferences("EBW183")
                print(f"   Retrieved preferences: {bool(prefs)}")
                if prefs:
                    print(f"     Has OpenAI: {prefs.get('has_openai_key')}")
                    print(f"     Has Claude: {prefs.get('has_claude_key')}")
                    print(f"     OpenAI key length: {len(prefs.get('openai_api_key', ''))}")
                    print(f"     Claude key length: {len(prefs.get('claude_api_key', ''))}")
                
                return prefs
            
            prefs = asyncio.run(test_db_ops())
            
        except Exception as e:
            print(f"   ❌ Database test failed: {e}")
        
        # Test 5: Check key validation logic
        print("\\n5. Testing key validation logic...")
        try:
            if prefs:
                openai_key = prefs.get('openai_api_key', '')
                claude_key = prefs.get('claude_api_key', '')
                
                # Check if keys look like real keys
                openai_real = openai_key.startswith('sk-') and not 'test' in openai_key.lower() and len(openai_key) > 40
                claude_real = claude_key.startswith('sk-ant-') and not 'test' in claude_key.lower() and len(claude_key) > 40
                
                print(f"   OpenAI key looks real: {openai_real}")
                print(f"   Claude key looks real: {claude_real}")
                print(f"   At least one real key: {openai_real or claude_real}")
        except Exception as e:
            print(f"   ❌ Key validation test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        return False

if __name__ == "__main__":
    debug_ai_service()