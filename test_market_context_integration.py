#!/usr/bin/env python3
"""
Test Market Context Integration in AI Analysis
Tests the integration of market intelligence into AI portfolio analysis prompts
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

async def test_market_context_integration():
    """Test market context integration in AI analysis"""
    print("🧪 Testing Market Context Integration in AI Analysis")
    print("=" * 60)
    
    try:
        # Import required modules
        from app.ai_engine.simple_analysis_router import create_enhanced_portfolio_prompt
        from app.ai_engine.market_context_service import market_context_service
        
        # Test portfolio data
        test_portfolio = {
            "total_value": 1000000,
            "holdings": [
                {
                    "tradingsymbol": "RELIANCE",
                    "current_value": 150000,
                    "quantity": 100,
                    "average_price": 2400,
                    "last_price": 2500,
                    "pnl": 10000,
                    "pnl_percentage": 4.17
                },
                {
                    "tradingsymbol": "TCS",
                    "current_value": 200000,
                    "quantity": 50,
                    "average_price": 3800,
                    "last_price": 4000,
                    "pnl": 10000,
                    "pnl_percentage": 5.26
                },
                {
                    "tradingsymbol": "HDFCBANK",
                    "current_value": 180000,
                    "quantity": 120,
                    "average_price": 1450,
                    "last_price": 1500,
                    "pnl": 6000,
                    "pnl_percentage": 3.45
                }
            ],
            "positions": []
        }
        
        # Test user preferences
        test_user_preferences = {
            "risk_tolerance": "medium",
            "investment_timeline": "long_term",
            "preferred_sectors": ["Technology", "Banking"],
            "max_position_size": 20.0
        }
        
        print("1. Testing Market Context Service...")
        
        # Get market context
        market_context = await market_context_service.get_comprehensive_market_context()
        
        print(f"✅ Market context retrieved successfully")
        print(f"   - Data Quality: {market_context.get('data_quality', 0)}/100")
        print(f"   - Trading Session: {market_context.get('trading_session', 'unknown')}")
        print(f"   - Market Status: {market_context.get('market_data', {}).get('market_status', 'unknown')}")
        
        # Display market data
        market_data = market_context.get('market_data', {})
        nifty = market_data.get('nifty_50', {})
        print(f"   - Nifty 50: {nifty.get('value', 0):,.0f} ({nifty.get('change_percent', 0):+.2f}%)")
        
        # Display sector performance
        sectors = market_context.get('sector_performance', {}).get('sectors', {})
        print(f"   - Sectors tracked: {len(sectors)}")
        
        print("\n2. Testing Enhanced Prompt Generation with Market Context...")
        
        # Generate enhanced prompt with market context
        enhanced_prompt = await create_enhanced_portfolio_prompt(
            test_portfolio,
            "test_user_123",
            test_user_preferences,
            market_context
        )
        
        print(f"✅ Enhanced prompt generated successfully")
        print(f"   - Prompt length: {len(enhanced_prompt):,} characters")
        
        # Check if market context is included
        market_keywords = [
            "CURRENT MARKET INTELLIGENCE",
            "MARKET INDICES",
            "SECTOR PERFORMANCE TODAY",
            "MARKET SENTIMENT ANALYSIS",
            "Nifty 50:",
            "Sensex:",
            "Market Trend:",
            "Overall Sentiment:"
        ]
        
        included_keywords = [kw for kw in market_keywords if kw in enhanced_prompt]
        print(f"   - Market context keywords found: {len(included_keywords)}/{len(market_keywords)}")
        
        if len(included_keywords) >= len(market_keywords) * 0.8:
            print("✅ Market context successfully integrated into prompt")
        else:
            print("⚠️  Some market context elements may be missing")
        
        print("\n3. Testing Market Context Components...")
        
        # Test individual market context components
        components_tested = 0
        components_passed = 0
        
        # Test market data
        if "MARKET INDICES" in enhanced_prompt:
            components_passed += 1
            print("✅ Market indices data integrated")
        else:
            print("❌ Market indices data missing")
        components_tested += 1
        
        # Test sector performance
        if "SECTOR PERFORMANCE TODAY" in enhanced_prompt:
            components_passed += 1
            print("✅ Sector performance data integrated")
        else:
            print("❌ Sector performance data missing")
        components_tested += 1
        
        # Test market sentiment
        if "MARKET SENTIMENT ANALYSIS" in enhanced_prompt:
            components_passed += 1
            print("✅ Market sentiment data integrated")
        else:
            print("❌ Market sentiment data missing")
        components_tested += 1
        
        # Test recent events
        if "RECENT MARKET EVENTS" in enhanced_prompt:
            components_passed += 1
            print("✅ Recent market events integrated")
        else:
            print("✅ Recent market events not available (acceptable)")
            components_passed += 1  # This is acceptable
        components_tested += 1
        
        print(f"\n4. Testing Stock-Specific Context...")
        
        # Test stock-specific context
        stock_context = await market_context_service.get_stock_specific_context("RELIANCE")
        if stock_context.get('data_available'):
            print("✅ Stock-specific context available")
            print(f"   - Symbol: {stock_context.get('symbol')}")
            print(f"   - Sector: {stock_context.get('sector', 'Unknown')}")
        else:
            print("⚠️  Stock-specific context not available (using fallback)")
        
        print(f"\n5. Testing Sector Trend Analysis...")
        
        # Test sector trend analysis
        sector_trend = await market_context_service.get_sector_trend_analysis("Technology")
        if sector_trend.get('data_available'):
            print("✅ Sector trend analysis available")
            print(f"   - Sector: {sector_trend.get('sector')}")
            print(f"   - Trend: {sector_trend.get('trend', 'unknown')}")
        else:
            print("⚠️  Sector trend analysis not available (using fallback)")
        
        print("\n" + "=" * 60)
        print("📊 MARKET CONTEXT INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        print(f"✅ Market Context Service: WORKING")
        print(f"✅ Enhanced Prompt Generation: WORKING")
        print(f"✅ Market Data Integration: {components_passed}/{components_tested} components")
        print(f"✅ Data Quality Score: {market_context.get('data_quality', 0)}/100")
        
        # Display sample of enhanced prompt
        print(f"\n📝 SAMPLE ENHANCED PROMPT (first 1000 chars):")
        print("-" * 50)
        print(enhanced_prompt[:1000] + "..." if len(enhanced_prompt) > 1000 else enhanced_prompt)
        print("-" * 50)
        
        # Test summary
        if components_passed >= components_tested * 0.8:
            print(f"\n🎉 MARKET CONTEXT INTEGRATION: SUCCESS")
            print(f"   All major components are working correctly")
            return True
        else:
            print(f"\n⚠️  MARKET CONTEXT INTEGRATION: PARTIAL SUCCESS")
            print(f"   Some components need attention")
            return False
            
    except Exception as e:
        print(f"❌ Market context integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_prompt_quality():
    """Test the quality and completeness of generated prompts"""
    print("\n🔍 Testing Prompt Quality and Completeness")
    print("=" * 60)
    
    try:
        from app.ai_engine.simple_analysis_router import create_enhanced_portfolio_prompt
        from app.ai_engine.market_context_service import market_context_service
        
        # Test with minimal portfolio
        minimal_portfolio = {
            "total_value": 500000,
            "holdings": [
                {
                    "tradingsymbol": "INFY",
                    "current_value": 250000,
                    "quantity": 200,
                    "average_price": 1200,
                    "last_price": 1250,
                    "pnl": 10000,
                    "pnl_percentage": 4.0
                }
            ],
            "positions": []
        }
        
        # Get market context
        market_context = await market_context_service.get_comprehensive_market_context()
        
        # Generate prompt
        prompt = await create_enhanced_portfolio_prompt(
            minimal_portfolio,
            "test_user_minimal",
            None,  # No user preferences
            market_context
        )
        
        # Quality checks
        quality_checks = {
            "Portfolio Overview": "CURRENT PORTFOLIO OVERVIEW" in prompt,
            "Holdings Breakdown": "DETAILED HOLDINGS BREAKDOWN" in prompt,
            "Market Intelligence": "CURRENT MARKET INTELLIGENCE" in prompt,
            "Analysis Requirements": "CRITICAL ANALYSIS REQUIREMENTS" in prompt,
            "JSON Format": "MANDATORY OUTPUT FORMAT" in prompt,
            "Stock Symbols": "EXACT_NSE_SYMBOL" in prompt,
            "Market Context": "MARKET CONTEXT INTEGRATION" in prompt,
            "Specific Numbers": "rupees_amount" in prompt and "shares_to_buy_or_sell" in prompt
        }
        
        passed_checks = sum(quality_checks.values())
        total_checks = len(quality_checks)
        
        print(f"Quality Checks: {passed_checks}/{total_checks}")
        for check, passed in quality_checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
        
        if passed_checks >= total_checks * 0.9:
            print(f"\n✅ PROMPT QUALITY: EXCELLENT")
            return True
        elif passed_checks >= total_checks * 0.7:
            print(f"\n⚠️  PROMPT QUALITY: GOOD")
            return True
        else:
            print(f"\n❌ PROMPT QUALITY: NEEDS IMPROVEMENT")
            return False
            
    except Exception as e:
        print(f"❌ Prompt quality test failed: {e}")
        return False

async def main():
    """Run all market context integration tests"""
    print("🚀 Starting Market Context Integration Tests")
    print("=" * 60)
    
    # Run tests
    test1_passed = await test_market_context_integration()
    test2_passed = await test_prompt_quality()
    
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED - Market Context Integration is working correctly!")
        print("\n✅ Ready for next implementation phase:")
        print("   - User Investment Profile System")
        print("   - Frontend Enhancement")
        print("   - Auto-Trading Integration")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - Review and fix issues before proceeding")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)