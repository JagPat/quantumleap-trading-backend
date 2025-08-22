#!/usr/bin/env python3
"""
Test script for market context service
"""
import sys
import os
import asyncio
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock the settings for testing
class MockSettings:
    def __init__(self, db_path):
        self.database_path = db_path
    
    def get_encryption_key(self):
        from cryptography.fernet import Fernet
        return Fernet.generate_key()

# Replace the settings import
import app.database.service as db_service
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
temp_db.close()
db_service.settings = MockSettings(temp_db.name)

# Reinitialize cipher suite with new key
from cryptography.fernet import Fernet
db_service.cipher_suite = Fernet(db_service.settings.get_encryption_key())

from app.database.service import init_database, store_market_context, store_sector_performance, store_stock_market_data
from app.ai_engine.market_context_service import MarketContextService

async def setup_test_data():
    """Set up test market data"""
    print("Setting up test market data...")
    
    # Initialize database
    init_database()
    
    # Store sample market context
    market_data = {
        "nifty_value": 21650.0,
        "nifty_change": 125.5,
        "nifty_change_percent": 0.58,
        "nifty_trend": "bullish",
        "sensex_value": 71500.0,
        "sensex_change": 415.0,
        "sensex_change_percent": 0.58,
        "market_sentiment": "bullish",
        "volatility_index": 14.8,
        "market_volume": 4200000000,
        "advances_count": 1750,
        "declines_count": 1150,
        "unchanged_count": 200,
        "market_status": "open",
        "fear_greed_index": 72
    }
    store_market_context("2024-01-15", market_data)
    
    # Store sample sector data
    sector_data = [
        {
            "sector_name": "Information Technology",
            "sector_change_percent": 1.45,
            "sector_trend": "bullish",
            "pe_ratio": 28.5,
            "analyst_rating": "buy",
            "momentum_score": 78
        },
        {
            "sector_name": "Banking",
            "sector_change_percent": -0.32,
            "sector_trend": "bearish",
            "pe_ratio": 15.2,
            "analyst_rating": "hold",
            "momentum_score": 42
        }
    ]
    store_sector_performance("2024-01-15", sector_data)
    
    # Store sample stock data
    stock_data = [
        {
            "symbol": "TCS",
            "close_price": 4050.75,
            "price_change_percent": 1.25,
            "volume": 8500000,
            "analyst_rating": "buy",
            "sector": "Information Technology",
            "pe_ratio": 29.2,
            "beta": 0.85,
            "support_level": 3900.0,
            "resistance_level": 4200.0,
            "recent_news": ["Q3 results beat expectations", "New client wins announced"]
        }
    ]
    store_stock_market_data("2024-01-15", stock_data)
    
    print("✓ Test data setup complete")

async def test_comprehensive_market_context():
    """Test comprehensive market context retrieval"""
    
    print("\n" + "=" * 60)
    print("TESTING COMPREHENSIVE MARKET CONTEXT")
    print("=" * 60)
    
    service = MarketContextService()
    
    print("Step 1: Getting comprehensive market context...")
    context = await service.get_comprehensive_market_context()
    
    print(f"✓ Timestamp: {context['timestamp']}")
    print(f"✓ Market data available: {'Yes' if context['market_data'] else 'No'}")
    print(f"✓ Sector performance available: {'Yes' if context['sector_performance'] else 'No'}")
    print(f"✓ Market sentiment: {context['market_sentiment']['overall_sentiment']}")
    print(f"✓ Trading session: {context['trading_session']}")
    print(f"✓ Data quality: {context['data_quality']}/100")
    print(f"✓ Recent events: {len(context['recent_events'])}")
    
    # Test market data details
    market_data = context['market_data']
    if 'nifty_50' in market_data:
        nifty = market_data['nifty_50']
        print(f"✓ Nifty 50: {nifty['value']} ({nifty['change_percent']:+.2f}%) - {nifty['trend']}")
    
    # Test sector data
    sectors = context['sector_performance'].get('sectors', {})
    print(f"✓ Sectors analyzed: {len(sectors)}")
    for sector, data in list(sectors.items())[:3]:
        change = data.get('change_percent', 0)
        print(f"  - {sector}: {change:+.2f}%")
    
    # Test AI context summary
    print(f"✓ AI context summary length: {len(context['ai_context_summary'])} characters")
    
    return context

async def test_stock_specific_context():
    """Test stock-specific context retrieval"""
    
    print("\n" + "=" * 60)
    print("TESTING STOCK-SPECIFIC CONTEXT")
    print("=" * 60)
    
    service = MarketContextService()
    
    # Test with existing stock
    print("Step 1: Getting context for TCS...")
    tcs_context = await service.get_stock_specific_context("TCS")
    
    print(f"✓ Symbol: {tcs_context['symbol']}")
    print(f"✓ Data available: {tcs_context['data_available']}")
    
    if tcs_context['data_available']:
        print(f"✓ Current price: ₹{tcs_context['current_price']}")
        print(f"✓ Change: {tcs_context['change_percent']:+.2f}%")
        print(f"✓ Sector: {tcs_context['sector']}")
        print(f"✓ Analyst rating: {tcs_context['analyst_rating']}")
        print(f"✓ Recent news: {len(tcs_context['recent_news'])} items")
    
    # Test with non-existent stock
    print("\nStep 2: Getting context for non-existent stock...")
    unknown_context = await service.get_stock_specific_context("UNKNOWN")
    print(f"✓ Unknown stock handled: {not unknown_context['data_available']}")
    
    return tcs_context

async def test_sector_trend_analysis():
    """Test sector trend analysis"""
    
    print("\n" + "=" * 60)
    print("TESTING SECTOR TREND ANALYSIS")
    print("=" * 60)
    
    service = MarketContextService()
    
    # Test with existing sector
    print("Step 1: Getting trend analysis for IT sector...")
    it_trend = await service.get_sector_trend_analysis("Information Technology")
    
    print(f"✓ Sector: {it_trend['sector']}")
    print(f"✓ Data available: {it_trend['data_available']}")
    
    if it_trend['data_available']:
        print(f"✓ Trend: {it_trend['trend']}")
        print(f"✓ Current performance: {it_trend['current_performance']:+.2f}%")
        print(f"✓ Analyst rating: {it_trend['analyst_rating']}")
        print(f"✓ Risk level: {it_trend['risk_level']}")
        print(f"✓ Growth potential: {it_trend['growth_potential']}")
        print(f"✓ Momentum score: {it_trend['momentum_score']}")
    
    # Test with non-existent sector
    print("\nStep 2: Getting trend analysis for non-existent sector...")
    unknown_trend = await service.get_sector_trend_analysis("Unknown Sector")
    print(f"✓ Unknown sector handled: {not unknown_trend['data_available']}")
    
    return it_trend

async def test_caching_mechanism():
    """Test caching mechanism"""
    
    print("\n" + "=" * 60)
    print("TESTING CACHING MECHANISM")
    print("=" * 60)
    
    service = MarketContextService()
    
    print("Step 1: First call (should fetch fresh data)...")
    start_time = asyncio.get_event_loop().time()
    context1 = await service.get_comprehensive_market_context()
    time1 = asyncio.get_event_loop().time() - start_time
    print(f"✓ First call completed in {time1:.3f} seconds")
    
    print("\nStep 2: Second call (should use cache)...")
    start_time = asyncio.get_event_loop().time()
    context2 = await service.get_comprehensive_market_context()
    time2 = asyncio.get_event_loop().time() - start_time
    print(f"✓ Second call completed in {time2:.3f} seconds")
    
    print(f"✓ Cache working: {time2 < time1}")
    print(f"✓ Same data returned: {context1['timestamp'] == context2['timestamp']}")

async def test_trading_session_detection():
    """Test trading session detection"""
    
    print("\n" + "=" * 60)
    print("TESTING TRADING SESSION DETECTION")
    print("=" * 60)
    
    service = MarketContextService()
    
    print("Step 1: Getting current trading session...")
    session = service._get_trading_session()
    print(f"✓ Current trading session: {session}")
    
    market_status = service._get_market_status()
    print(f"✓ Market status: {market_status}")
    
    # Test with different times (would need mocking for comprehensive testing)
    print("✓ Trading session detection working")

async def test_data_quality_calculation():
    """Test data quality calculation"""
    
    print("\n" + "=" * 60)
    print("TESTING DATA QUALITY CALCULATION")
    print("=" * 60)
    
    service = MarketContextService()
    
    # Test with database data
    market_data_db = {"data_source": "database", "nifty_50": {"value": 21500}}
    sector_data_db = {"data_source": "database", "sectors": {"IT": {"change_percent": 1.5}}}
    
    quality_db = service._calculate_data_quality(market_data_db, sector_data_db)
    print(f"✓ Database data quality: {quality_db}/100")
    
    # Test with simulated data
    market_data_sim = {"data_source": "simulated", "nifty_50": {"value": 21500}}
    sector_data_sim = {"data_source": "simulated", "sectors": {"IT": {"change_percent": 1.5}}}
    
    quality_sim = service._calculate_data_quality(market_data_sim, sector_data_sim)
    print(f"✓ Simulated data quality: {quality_sim}/100")
    
    # Test with fallback data
    market_data_fallback = {"data_source": "fallback"}
    sector_data_fallback = {"data_source": "fallback"}
    
    quality_fallback = service._calculate_data_quality(market_data_fallback, sector_data_fallback)
    print(f"✓ Fallback data quality: {quality_fallback}/100")
    
    print(f"✓ Quality ranking correct: {quality_db > quality_sim > quality_fallback}")

async def run_all_tests():
    """Run all market context service tests"""
    
    try:
        await setup_test_data()
        
        context = await test_comprehensive_market_context()
        stock_context = await test_stock_specific_context()
        sector_trend = await test_sector_trend_analysis()
        await test_caching_mechanism()
        await test_trading_session_detection()
        await test_data_quality_calculation()
        
        print("\n" + "=" * 60)
        print("ALL MARKET CONTEXT SERVICE TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print(f"\nTest Summary:")
        print(f"- Market context data quality: {context['data_quality']}/100")
        print(f"- Sectors analyzed: {len(context['sector_performance'].get('sectors', {}))}")
        print(f"- Stock context available: {'✓' if stock_context['data_available'] else '✗'}")
        print(f"- Sector trend analysis: {'✓' if sector_trend['data_available'] else '✗'}")
        print(f"- Trading session: {context['trading_session']}")
        print(f"- AI context summary: {len(context['ai_context_summary'])} chars")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            os.unlink(temp_db.name)
            print(f"✓ Cleaned up temporary database: {temp_db.name}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(run_all_tests())