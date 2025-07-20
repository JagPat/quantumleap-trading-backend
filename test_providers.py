#!/usr/bin/env python3
"""
Test script to verify Phase 2 and Phase 3 implementations
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_phase2_database():
    """Test Phase 2: Database schema and models"""
    print("🔍 Testing Phase 2: Database Schema and Models")
    print("=" * 50)
    
    try:
        # Test database service import
        from app.database.service import init_database
        print("✅ Database service import successful")
        
        # Test enhanced models import
        from app.ai_engine.models import (
            AIPreferences, AIPreferencesRequest, AIPreferencesResponse,
            ChatMessage, ChatRequest, ChatResponse,
            TradingStrategy, StrategyParameters, StrategyResponse,
            TradingSignal, SignalsRequest, SignalsResponse,
            AnalysisRequest, AnalysisResponse,
            AssistantMessageRequest, AssistantMessageResponse, AssistantStatusResponse
        )
        print("✅ Enhanced Pydantic models import successful")
        
        # Test model instantiation
        preferences = AIPreferencesRequest(
            preferred_ai_provider="openai",
            openai_api_key="test_key",
            grok_api_key="test_grok_key"
        )
        print("✅ Model instantiation successful")
        print(f"   - Preferred provider: {preferences.preferred_ai_provider}")
        print(f"   - Has Grok support: {preferences.grok_api_key is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_phase3_providers():
    """Test Phase 3: AI Provider Infrastructure"""
    print("\n🔍 Testing Phase 3: AI Provider Infrastructure")
    print("=" * 50)
    
    try:
        # Test base provider import
        from app.ai_engine.providers.base_provider import BaseAIProvider, ValidationResult, UsageStats
        print("✅ Base provider import successful")
        
        # Test all provider imports
        from app.ai_engine.providers.openai_provider import OpenAIProvider
        from app.ai_engine.providers.claude_provider import ClaudeProvider
        from app.ai_engine.providers.gemini_provider import GeminiProvider
        from app.ai_engine.providers.grok_provider import GrokProvider
        print("✅ All provider imports successful")
        
        # Test orchestrator import
        from app.ai_engine.orchestrator import AIOrchestrator
        print("✅ AI Orchestrator import successful")
        
        # Test provider instantiation (with dummy keys)
        providers = {}
        
        try:
            providers['openai'] = OpenAIProvider("test_key")
            print("✅ OpenAI provider instantiation successful")
        except Exception as e:
            print(f"⚠️  OpenAI provider instantiation failed: {e}")
        
        try:
            providers['claude'] = ClaudeProvider("test_key")
            print("✅ Claude provider instantiation successful")
        except Exception as e:
            print(f"⚠️  Claude provider instantiation failed: {e}")
        
        try:
            providers['gemini'] = GeminiProvider("test_key")
            print("✅ Gemini provider instantiation successful")
        except Exception as e:
            print(f"⚠️  Gemini provider instantiation failed: {e}")
        
        try:
            providers['grok'] = GrokProvider("test_key")
            print("✅ Grok provider instantiation successful")
        except Exception as e:
            print(f"⚠️  Grok provider instantiation failed: {e}")
        
        # Test orchestrator instantiation
        orchestrator = AIOrchestrator()
        print("✅ AI Orchestrator instantiation successful")
        
        # Test provider selection logic
        provider_prefs = orchestrator.PROVIDER_PREFERENCES
        print(f"✅ Provider preferences loaded: {len(provider_prefs)} task types")
        print(f"   - Chat preferences: {provider_prefs.get('chat', [])}")
        print(f"   - Analysis preferences: {provider_prefs.get('technical_analysis', [])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integration():
    """Test integration between Phase 2 and Phase 3"""
    print("\n🔍 Testing Phase 2 + Phase 3 Integration")
    print("=" * 50)
    
    try:
        from app.ai_engine.models import AIPreferences
        from app.ai_engine.orchestrator import AIOrchestrator
        
        # Create test preferences
        preferences = AIPreferences(
            user_id="test_user",
            preferred_ai_provider="auto",
            openai_api_key="test_openai_key",
            claude_api_key="test_claude_key",
            gemini_api_key="test_gemini_key",
            grok_api_key="test_grok_key"
        )
        print("✅ Test preferences created with all providers")
        
        # Test orchestrator with preferences
        orchestrator = AIOrchestrator()
        
        # Test provider selection without initialization (should handle gracefully)
        provider = await orchestrator.select_optimal_provider("chat")
        print(f"✅ Provider selection works (returned: {provider})")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 BYOAI Enhancement Verification")
    print("Testing Phase 2 and Phase 3 implementations")
    print("=" * 60)
    
    # Run tests
    phase2_ok = await test_phase2_database()
    phase3_ok = await test_phase3_providers()
    integration_ok = await test_integration()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"Phase 2 (Database & Models): {'✅ PASS' if phase2_ok else '❌ FAIL'}")
    print(f"Phase 3 (AI Providers): {'✅ PASS' if phase3_ok else '❌ FAIL'}")
    print(f"Integration Test: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    
    if phase2_ok and phase3_ok and integration_ok:
        print("\n🎉 All tests passed! Ready for Phase 4.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Issues need to be resolved before Phase 4.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)