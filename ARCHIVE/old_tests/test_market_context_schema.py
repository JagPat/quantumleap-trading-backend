#!/usr/bin/env python3
"""
Test script for market context database schema
"""
import sys
import os
import sqlite3
import tempfile
from datetime import datetime, date
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

from app.database.service import (
    init_database,
    store_market_context,
    get_market_context,
    store_sector_performance,
    get_sector_performance,
    store_stock_market_data,
    get_stock_market_data,
    store_market_event,
    get_market_events,
    get_market_context_for_ai_prompt
)

def test_market_context_schema():
    """Test the market context database schema"""
    
    print("=" * 60)
    print("TESTING MARKET CONTEXT DATABASE SCHEMA")
    print("=" * 60)
    
    # Initialize database
    print("Step 1: Initializing database...")
    init_database()
    
    # Check if tables were created
    conn = sqlite3.connect(db_service.settings.database_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = ['market_context', 'sector_performance', 'stock_market_data', 'market_events']
    for table in required_tables:
        if table in tables:
            print(f"✓ Table '{table}' created successfully")
        else:
            print(f"✗ Table '{table}' NOT found")
    
    # Check table structures
    for table in required_tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"✓ {table} table has {len(columns)} columns")
    
    conn.close()

def test_market_context_storage():
    """Test storing and retrieving market context"""
    
    print("\n" + "=" * 60)
    print("TESTING MARKET CONTEXT STORAGE")
    print("=" * 60)
    
    test_date = "2024-01-15"
    
    # Sample market context data
    sample_market_data = {
        "nifty_value": 21500.50,
        "nifty_change": 125.30,
        "nifty_change_percent": 0.58,
        "nifty_trend": "bullish",
        "sensex_value": 71200.25,
        "sensex_change": 420.15,
        "sensex_change_percent": 0.59,
        "market_sentiment": "bullish",
        "volatility_index": 15.25,
        "market_volume": 4500000000,
        "advances_count": 1850,
        "declines_count": 1200,
        "unchanged_count": 150,
        "sector_performance": {
            "IT": 1.2,
            "Banking": 0.8,
            "Pharma": -0.5
        },
        "top_gainers": [
            {"symbol": "TCS", "change": 2.5},
            {"symbol": "INFY", "change": 2.1}
        ],
        "top_losers": [
            {"symbol": "HDFC", "change": -1.8},
            {"symbol": "ICICI", "change": -1.2}
        ],
        "key_events": [
            "RBI policy meeting scheduled",
            "Q3 earnings season begins"
        ],
        "market_breadth_ratio": 1.54,
        "fear_greed_index": 65,
        "analyst_sentiment": "Cautiously optimistic",
        "news_sentiment_score": 0.3,
        "trading_session": "regular",
        "market_status": "open",
        "data_source": "test_data",
        "data_quality_score": 95
    }
    
    # Test storing market context
    print("Step 1: Storing market context...")
    success = store_market_context(test_date, sample_market_data)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Test retrieving market context
    print("\nStep 2: Retrieving market context...")
    retrieved_context = get_market_context(test_date)
    
    if retrieved_context:
        print(f"✓ Market context retrieved successfully")
        print(f"✓ Date: {retrieved_context['date']}")
        print(f"✓ Nifty value: {retrieved_context['nifty_value']}")
        print(f"✓ Nifty trend: {retrieved_context['nifty_trend']}")
        print(f"✓ Market sentiment: {retrieved_context['market_sentiment']}")
        print(f"✓ Fear & Greed Index: {retrieved_context['fear_greed_index']}")
        print(f"✓ Top gainers: {len(retrieved_context['top_gainers'])}")
    else:
        print("✗ Market context retrieval FAILED")
    
    return retrieved_context

def test_sector_performance():
    """Test sector performance functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING SECTOR PERFORMANCE")
    print("=" * 60)
    
    test_date = "2024-01-15"
    
    # Sample sector data
    sample_sectors = [
        {
            "sector_name": "Information Technology",
            "sector_index_value": 35200.50,
            "sector_change": 425.30,
            "sector_change_percent": 1.22,
            "sector_trend": "bullish",
            "market_cap": 15000000000000,
            "volume": 850000000,
            "pe_ratio": 28.5,
            "pb_ratio": 4.2,
            "dividend_yield": 1.8,
            "top_performers": ["TCS", "INFY", "WIPRO"],
            "worst_performers": ["TECHM"],
            "analyst_rating": "buy",
            "risk_level": "medium",
            "growth_potential": "high",
            "correlation_with_nifty": 0.85,
            "volatility_30d": 18.5,
            "momentum_score": 75
        },
        {
            "sector_name": "Banking",
            "sector_index_value": 42800.25,
            "sector_change": -125.80,
            "sector_change_percent": -0.29,
            "sector_trend": "bearish",
            "market_cap": 12000000000000,
            "volume": 1200000000,
            "pe_ratio": 15.2,
            "pb_ratio": 1.8,
            "dividend_yield": 3.2,
            "top_performers": ["KOTAKBANK"],
            "worst_performers": ["HDFCBANK", "ICICIBANK"],
            "analyst_rating": "hold",
            "risk_level": "medium",
            "growth_potential": "medium",
            "correlation_with_nifty": 0.92,
            "volatility_30d": 22.1,
            "momentum_score": 45
        }
    ]
    
    # Store sector performance
    print("Step 1: Storing sector performance...")
    success = store_sector_performance(test_date, sample_sectors)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Retrieve sector performance
    print("\nStep 2: Retrieving sector performance...")
    retrieved_sectors = get_sector_performance(test_date)
    print(f"✓ Retrieved {len(retrieved_sectors)} sectors")
    
    for sector in retrieved_sectors:
        print(f"✓ Sector: {sector['sector_name']} - {sector['sector_change_percent']:.2f}% - {sector['sector_trend']}")
    
    # Test specific sector retrieval
    print("\nStep 3: Testing specific sector retrieval...")
    it_sector = get_sector_performance(test_date, "Information Technology")
    print(f"✓ IT sector data: {'Found' if it_sector else 'Not found'}")
    
    return retrieved_sectors

def test_stock_market_data():
    """Test stock market data functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING STOCK MARKET DATA")
    print("=" * 60)
    
    test_date = "2024-01-15"
    
    # Sample stock data
    sample_stocks = [
        {
            "symbol": "RELIANCE",
            "open_price": 2480.00,
            "high_price": 2520.50,
            "low_price": 2475.25,
            "close_price": 2510.75,
            "volume": 15000000,
            "price_change": 30.75,
            "price_change_percent": 1.24,
            "market_cap": 1700000000000,
            "pe_ratio": 25.8,
            "pb_ratio": 2.1,
            "dividend_yield": 0.8,
            "beta": 1.15,
            "volatility_30d": 20.5,
            "rsi": 65.2,
            "moving_avg_50d": 2450.30,
            "moving_avg_200d": 2380.75,
            "support_level": 2400.00,
            "resistance_level": 2550.00,
            "analyst_target_price": 2650.00,
            "analyst_rating": "buy",
            "news_sentiment_score": 0.2,
            "social_sentiment_score": 0.15,
            "institutional_holding_percent": 65.5,
            "promoter_holding_percent": 50.2,
            "recent_news": [
                "Q3 earnings beat expectations",
                "New refinery project announced"
            ],
            "stock_events": [
                "Earnings announcement on Jan 20"
            ],
            "sector": "Energy",
            "industry": "Oil & Gas"
        },
        {
            "symbol": "TCS",
            "open_price": 3980.00,
            "high_price": 4020.25,
            "low_price": 3975.50,
            "close_price": 4010.75,
            "volume": 8500000,
            "price_change": 30.75,
            "price_change_percent": 0.77,
            "market_cap": 1450000000000,
            "pe_ratio": 28.2,
            "pb_ratio": 12.5,
            "dividend_yield": 3.2,
            "beta": 0.85,
            "volatility_30d": 15.8,
            "rsi": 58.7,
            "moving_avg_50d": 3950.20,
            "moving_avg_200d": 3800.45,
            "support_level": 3900.00,
            "resistance_level": 4100.00,
            "analyst_target_price": 4200.00,
            "analyst_rating": "strong_buy",
            "news_sentiment_score": 0.4,
            "social_sentiment_score": 0.3,
            "institutional_holding_percent": 72.8,
            "promoter_holding_percent": 72.0,
            "recent_news": [
                "Large deal wins in Q3",
                "AI initiatives showing progress"
            ],
            "stock_events": [
                "Board meeting on Jan 18"
            ],
            "sector": "Information Technology",
            "industry": "IT Services"
        }
    ]
    
    # Store stock data
    print("Step 1: Storing stock market data...")
    success = store_stock_market_data(test_date, sample_stocks)
    print(f"✓ Storage result: {'SUCCESS' if success else 'FAILED'}")
    
    # Retrieve stock data
    print("\nStep 2: Retrieving stock market data...")
    reliance_data = get_stock_market_data("RELIANCE", test_date)
    print(f"✓ RELIANCE data: {'Found' if reliance_data else 'Not found'}")
    
    if reliance_data:
        stock = reliance_data[0]
        print(f"✓ Close price: ₹{stock['close_price']}")
        print(f"✓ Change: {stock['price_change_percent']:.2f}%")
        print(f"✓ Volume: {stock['volume']:,}")
        print(f"✓ Analyst rating: {stock['analyst_rating']}")
        print(f"✓ Recent news: {len(stock['recent_news'])} items")
    
    return sample_stocks

def test_market_events():
    """Test market events functionality"""
    
    print("\n" + "=" * 60)
    print("TESTING MARKET EVENTS")
    print("=" * 60)
    
    # Sample market events
    sample_events = [
        {
            "event_date": "2024-01-15",
            "event_type": "policy",
            "event_title": "RBI Monetary Policy Meeting",
            "event_description": "Reserve Bank of India announces policy rates and monetary stance",
            "impact_level": "high",
            "affected_sectors": ["Banking", "NBFC", "Real Estate"],
            "affected_stocks": ["HDFCBANK", "ICICIBANK", "SBIN"],
            "market_reaction": "Mixed reaction with banking stocks volatile",
            "price_impact_estimate": 2.5,
            "duration_estimate": "short_term",
            "confidence_score": 85,
            "data_source": "RBI_official",
            "analyst_notes": "Key focus on inflation targeting and liquidity measures",
            "follow_up_required": True
        },
        {
            "event_date": "2024-01-14",
            "event_type": "earnings",
            "event_title": "TCS Q3 Results",
            "event_description": "Tata Consultancy Services announces Q3 FY24 earnings",
            "impact_level": "medium",
            "affected_sectors": ["Information Technology"],
            "affected_stocks": ["TCS", "INFY", "WIPRO"],
            "market_reaction": "Positive response from IT sector",
            "price_impact_estimate": 1.8,
            "duration_estimate": "immediate",
            "confidence_score": 90,
            "data_source": "company_announcement",
            "analyst_notes": "Strong revenue growth and margin expansion",
            "follow_up_required": False
        }
    ]
    
    # Store events
    print("Step 1: Storing market events...")
    event_ids = []
    for event in sample_events:
        event_id = store_market_event(event)
        if event_id:
            event_ids.append(event_id)
            print(f"✓ Stored event '{event['event_title']}' with ID {event_id}")
        else:
            print(f"✗ Failed to store event '{event['event_title']}'")
    
    # Retrieve events
    print("\nStep 2: Retrieving market events...")
    retrieved_events = get_market_events(days_back=7)
    print(f"✓ Retrieved {len(retrieved_events)} events")
    
    for event in retrieved_events:
        print(f"✓ Event: {event['event_title']} - {event['impact_level']} impact - {event['event_type']}")
    
    # Test high impact events
    print("\nStep 3: Testing high impact events filter...")
    high_impact_events = get_market_events(days_back=7, impact_level="high")
    print(f"✓ High impact events: {len(high_impact_events)}")
    
    return retrieved_events

def test_ai_prompt_context():
    """Test market context for AI prompts"""
    
    print("\n" + "=" * 60)
    print("TESTING AI PROMPT CONTEXT")
    print("=" * 60)
    
    print("Step 1: Getting market context for AI prompt...")
    ai_context = get_market_context_for_ai_prompt(days_back=3)
    
    print(f"✓ Market data available: {ai_context['market_available']}")
    
    if ai_context['market_available']:
        print(f"✓ Current date: {ai_context['current_date']}")
        print(f"✓ Nifty trend: {ai_context['nifty_trend']}")
        print(f"✓ Market sentiment: {ai_context['market_sentiment']}")
        print(f"✓ Fear & Greed Index: {ai_context['fear_greed_index']}")
        print(f"✓ Top performing sectors: {len(ai_context['top_performing_sectors'])}")
        print(f"✓ Recent high impact events: {len(ai_context['recent_high_impact_events'])}")
        print(f"✓ Data quality: {ai_context['data_quality']}")
    else:
        print(f"✗ Market context not available: {ai_context.get('message', 'Unknown error')}")
    
    return ai_context

def run_all_tests():
    """Run all market context database tests"""
    
    try:
        test_market_context_schema()
        market_context = test_market_context_storage()
        sectors = test_sector_performance()
        stocks = test_stock_market_data()
        events = test_market_events()
        ai_context = test_ai_prompt_context()
        
        print("\n" + "=" * 60)
        print("ALL MARKET CONTEXT TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Summary
        print(f"\nTest Summary:")
        print(f"- Market context stored and retrieved: {'✓' if market_context else '✗'}")
        print(f"- Sector performance data: {len(sectors) if sectors else 0} sectors")
        print(f"- Stock market data: {len(stocks) if stocks else 0} stocks")
        print(f"- Market events: {len(events) if events else 0} events")
        print(f"- AI context available: {'✓' if ai_context['market_available'] else '✗'}")
        
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
    run_all_tests()