#!/usr/bin/env python3
"""
Test AI Keys and Analysis
Tests if AI API keys are available and working for portfolio analysis
"""
import os
import sys
import asyncio
import json
from datetime import datetime

# Add the app directory to the path
sys.path.append('.')

async def test_ai_keys():
    """Test if AI API keys are available"""
    print("🔍 Testing AI API Key Availability")
    print("=" * 50)
    
    # Check environment variables
    openai_key = os.getenv('OPENAI_API_KEY')
    claude_key = os.getenv('ANTHROPIC_API_KEY')
    gemini_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    
    print(f"OpenAI Key: {'✅ Available' if openai_key and openai_key != 'your_openai_api_key_here' else '❌ Not configured'}")
    print(f"Claude Key: {'✅ Available' if claude_key and claude_key != 'your_claude_api_key_here' else '❌ Not configured'}")
    print(f"Gemini Key: {'✅ Available' if gemini_key and gemini_key != 'your_google_api_key_here' else '❌ Not configured'}")
    
    # Check if any key is available
    has_any_key = any([
        openai_key and openai_key != 'your_openai_api_key_here',
        claude_key and claude_key != 'your_claude_api_key_here',
        gemini_key and gemini_key != 'your_google_api_key_here'
    ])
    
    print(f"\nOverall Status: {'✅ At least one AI provider available' if has_any_key else '❌ No AI providers configured'}")
    
    return has_any_key

async def test_user_preferences():
    """Test user preferences from database"""
    print("\n🔍 Testing User Preferences")
    print("=" * 50)
    
    try:
        from app.ai_engine.service import AIService
        ai_service = AIService()
        
        # Test with default user
        user_id = "frontend_test_user"
        preferences = await ai_service.get_user_preferences(user_id)
        
        if preferences:
            print(f"User preferences found for {user_id}")
            print(f"Has OpenAI key: {preferences.get('has_openai_key', False)}")
            print(f"Has Claude key: {preferences.get('has_claude_key', False)}")
            print(f"Has Gemini key: {preferences.get('has_gemini_key', False)}")
        else:
            print(f"No user preferences found for {user_id}")
            
        return preferences
        
    except Exception as e:
        print(f"Error testing user preferences: {e}")
        return None

async def test_portfolio_analysis():
    """Test portfolio analysis with sample data"""
    print("\n🔍 Testing Portfolio Analysis")
    print("=" * 50)
    
    try:
        # Sample portfolio data
        portfolio_data = {
            "total_value": 1500000,
            "holdings": [
                {
                    "tradingsymbol": "RELIANCE",
                    "current_value": 300000,
                    "quantity": 120,
                    "average_price": 2400,
                    "last_price": 2500,
                    "pnl": 12000,
                    "pnl_percentage": 4.17
                },
                {
                    "tradingsymbol": "TCS",
                    "current_value": 400000,
                    "quantity": 133,
                    "average_price": 2800,
                    "last_price": 3000,
                    "pnl": 26600,
                    "pnl_percentage": 7.14
                },
                {
                    "tradingsymbol": "HDFCBANK",
                    "current_value": 250000,
                    "quantity": 167,
                    "average_price": 1450,
                    "last_price": 1500,
                    "pnl": 8350,
                    "pnl_percentage": 3.45
                }
            ],
            "positions": []
        }
        
        # Import the analysis function
        from app.ai_engine.simple_analysis_router import simple_portfolio_analysis
        
        # Test analysis
        user_id = "frontend_test_user"
        print(f"Testing analysis for user: {user_id}")
        
        result = await simple_portfolio_analysis(portfolio_data, user_id)
        
        if result:
            print("✅ Portfolio analysis completed successfully!")
            print(f"Analysis type: {'Enhanced AI' if result.get('analysis_type') == 'enhanced' else 'Fallback'}")
            print(f"Provider used: {result.get('provider_used', 'fallback')}")
            print(f"Analysis ID: {result.get('analysis_id', 'N/A')}")
            
            # Check if we have recommendations
            recommendations = result.get('recommendations', {})
            if recommendations:
                print(f"Recommendations generated: {len(recommendations.get('stock_specific', []))}")
            
            return result
        else:
            print("❌ Portfolio analysis failed")
            return None
            
    except Exception as e:
        print(f"Error testing portfolio analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_ai_provider_direct():
    """Test AI providers directly"""
    print("\n🔍 Testing AI Providers Directly")
    print("=" * 50)
    
    try:
        # Test OpenAI if available
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai_key != 'your_openai_api_key_here':
            print("Testing OpenAI...")
            try:
                from app.ai_engine.providers.openai_client import OpenAIProvider
                provider = OpenAIProvider(openai_key)
                
                # Simple test
                response = await provider.generate_completion(
                    "Test message: What is 2+2?",
                    max_tokens=50
                )
                print(f"✅ OpenAI working: {response[:50]}...")
            except Exception as e:
                print(f"❌ OpenAI error: {e}")
        
        # Test Claude if available
        claude_key = os.getenv('ANTHROPIC_API_KEY')
        if claude_key and claude_key != 'your_claude_api_key_here':
            print("Testing Claude...")
            try:
                from app.ai_engine.providers.claude_client import ClaudeProvider
                provider = ClaudeProvider(claude_key)
                
                # Simple test
                response = await provider.generate_completion(
                    "Test message: What is 2+2?",
                    max_tokens=50
                )
                print(f"✅ Claude working: {response[:50]}...")
            except Exception as e:
                print(f"❌ Claude error: {e}")
        
        # Test Gemini if available
        gemini_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if gemini_key and gemini_key != 'your_google_api_key_here':
            print("Testing Gemini...")
            try:
                from app.ai_engine.providers.gemini_client import GeminiProvider
                provider = GeminiProvider(gemini_key)
                
                # Simple test
                response = await provider.generate_completion(
                    "Test message: What is 2+2?",
                    max_tokens=50
                )
                print(f"✅ Gemini working: {response[:50]}...")
            except Exception as e:
                print(f"❌ Gemini error: {e}")
                
    except Exception as e:
        print(f"Error testing AI providers: {e}")

async def main():
    """Main test function"""
    print("🚀 AI Analysis System Test")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Test 1: Check API keys
    has_keys = await test_ai_keys()
    
    # Test 2: Check user preferences
    preferences = await test_user_preferences()
    
    # Test 3: Test AI providers directly (if keys available)
    if has_keys:
        await test_ai_provider_direct()
    
    # Test 4: Test portfolio analysis
    analysis_result = await test_portfolio_analysis()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"API Keys Available: {'✅' if has_keys else '❌'}")
    print(f"User Preferences: {'✅' if preferences else '❌'}")
    print(f"Portfolio Analysis: {'✅' if analysis_result else '❌'}")
    
    if analysis_result:
        analysis_type = analysis_result.get('analysis_type', 'unknown')
        print(f"Analysis Type: {analysis_type}")
        if analysis_type == 'fallback':
            print("⚠️  System is using fallback analysis instead of AI")
            print("   This means either:")
            print("   1. No AI API keys are configured")
            print("   2. AI API keys are invalid")
            print("   3. AI providers are not responding")
    
    print(f"\nTest completed at: {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())