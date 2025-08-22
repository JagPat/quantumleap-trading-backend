#!/usr/bin/env python3
"""
Simple import test to isolate issues
"""

def test_basic_imports():
    """Test basic imports step by step"""
    try:
        print("Testing basic trading engine imports...")
        
        # Test models
        from app.trading_engine.models import TradingSignal, SignalType, OrderType, OrderSide, OrderStatus, StrategyStatus
        print("✅ Basic models imported")
        
        # Test Order specifically
        from app.trading_engine.models import Order
        print("✅ Order model imported")
        
        # Test market data components
        from app.trading_engine.market_data_manager import MarketDataManager
        print("✅ MarketDataManager imported")
        
        from app.trading_engine.market_data_processor import MarketDataProcessor
        print("✅ MarketDataProcessor imported")
        
        from app.trading_engine.market_condition_monitor import MarketConditionMonitor
        print("✅ MarketConditionMonitor imported")
        
        # Test routers
        from app.trading_engine.market_data_router import router as market_data_router
        print("✅ Market data router imported")
        
        from app.trading_engine.market_condition_router import router as market_condition_router
        print("✅ Market condition router imported")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_basic_imports()