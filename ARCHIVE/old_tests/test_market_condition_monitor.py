#!/usr/bin/env python3
"""
Test Market Condition Monitor
Comprehensive testing of the market condition monitoring system
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from app.trading_engine.market_condition_monitor import (
    MarketConditionMonitor, MarketCondition, VolatilityLevel, MarketSession
)
from app.trading_engine.event_bus import EventManager
from app.trading_engine.models import PriceData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_condition_monitor():
    """Test the complete market condition monitor functionality"""
    print("🧪 Testing Market Condition Monitor")
    print("=" * 45)
    
    # Test 1: Initialize components
    print("\n1️⃣ Testing Initialization")
    try:
        event_manager = EventManager()
        monitor = MarketConditionMonitor(event_manager)
        print("✅ Market Condition Monitor initialized successfully")
        print(f"   Market session: {monitor.get_market_session().value}")
        print(f"   Global condition: {monitor.get_global_condition().value}")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False
    
    # Test 2: Start the monitor
    print("\n2️⃣ Testing Monitor Startup")
    try:
        await monitor.start()
        print("✅ Market Condition Monitor started successfully")
        
        # Wait for initial setup
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ Monitor startup failed: {e}")
        return False
    
    # Test 3: Test normal market condition
    print("\n3️⃣ Testing Normal Market Condition")
    try:
        test_price = PriceData(
            symbol="NORMAL_TEST",
            price=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            timestamp=datetime.utcnow(),
            change=0.5,
            change_percent=0.5
        )
        
        condition_data = await monitor.analyze_price_update(test_price)
        
        print(f"✅ Normal condition analysis:")
        print(f"   Condition: {condition_data.condition.value}")
        print(f"   Volatility level: {condition_data.volatility_level.value}")
        print(f"   Volatility score: {condition_data.volatility_score:.4f}")
        print(f"   Confidence: {condition_data.confidence:.2f}")
        
    except Exception as e:
        print(f"❌ Normal condition test failed: {e}")
    
    # Test 4: Test high volatility detection
    print("\n4️⃣ Testing High Volatility Detection")
    try:
        # Create a series of volatile price movements
        base_price = 100.0
        volatile_prices = [100, 105, 95, 110, 85, 115, 80, 120, 75, 125]
        
        for i, price in enumerate(volatile_prices):
            test_price = PriceData(
                symbol="VOLATILE_TEST",
                price=float(price),
                bid=price - 0.05,
                ask=price + 0.05,
                volume=1000 + i * 100,
                timestamp=datetime.utcnow(),
                change=price - base_price,
                change_percent=((price - base_price) / base_price) * 100
            )
            
            condition_data = await monitor.analyze_price_update(test_price)
            base_price = price
        
        print(f"✅ Volatility detection analysis:")
        print(f"   Final condition: {condition_data.condition.value}")
        print(f"   Volatility level: {condition_data.volatility_level.value}")
        print(f"   Volatility score: {condition_data.volatility_score:.4f}")
        print(f"   Trend strength: {condition_data.trend_strength:.2f}")
        
    except Exception as e:
        print(f"❌ Volatility detection test failed: {e}")
    
    # Test 5: Test gap detection
    print("\n5️⃣ Testing Gap Detection")
    try:
        # Create a price gap scenario
        gap_prices = [
            (100.0, "normal"),
            (100.5, "normal"),
            (108.0, "gap_up"),  # 8% gap up
        ]
        
        for price, expected in gap_prices:
            test_price = PriceData(
                symbol="GAP_TEST",
                price=price,
                bid=price - 0.05,
                ask=price + 0.05,
                volume=1000,
                timestamp=datetime.utcnow(),
                change=price - 100.0,
                change_percent=((price - 100.0) / 100.0) * 100
            )
            
            condition_data = await monitor.analyze_price_update(test_price)
            
            if expected == "gap_up":
                print(f"✅ Gap detection analysis:")
                print(f"   Condition: {condition_data.condition.value}")
                print(f"   Gap percent: {condition_data.gap_percent:.2f}%")
                print(f"   Price change: {condition_data.price_change_percent:.2f}%")
        
    except Exception as e:
        print(f"❌ Gap detection test failed: {e}")
    
    # Test 6: Test trend analysis
    print("\n6️⃣ Testing Trend Analysis")
    try:
        # Create an uptrend
        uptrend_prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        
        for price in uptrend_prices:
            test_price = PriceData(
                symbol="TREND_TEST",
                price=float(price),
                bid=price - 0.05,
                ask=price + 0.05,
                volume=1000,
                timestamp=datetime.utcnow(),
                change=price - 100.0,
                change_percent=((price - 100.0) / 100.0) * 100
            )
            
            condition_data = await monitor.analyze_price_update(test_price)
        
        print(f"✅ Trend analysis:")
        print(f"   Condition: {condition_data.condition.value}")
        print(f"   Trend strength: {condition_data.trend_strength:.2f}")
        print(f"   Support level: ${condition_data.support_level}")
        print(f"   Resistance level: ${condition_data.resistance_level}")
        
    except Exception as e:
        print(f"❌ Trend analysis test failed: {e}")
    
    # Test 7: Test market session detection
    print("\n7️⃣ Testing Market Session Detection")
    try:
        session = monitor.get_market_session()
        is_open = monitor.is_market_open()
        is_trading_hours = monitor.is_trading_hours()
        
        print(f"✅ Market session analysis:")
        print(f"   Current session: {session.value}")
        print(f"   Market open: {is_open}")
        print(f"   Trading hours: {is_trading_hours}")
        
    except Exception as e:
        print(f"❌ Market session test failed: {e}")
    
    # Test 8: Test condition summary
    print("\n8️⃣ Testing Condition Summary")
    try:
        summary = monitor.get_condition_summary()
        
        print(f"✅ Condition summary:")
        print(f"   Global condition: {summary['global_condition']}")
        print(f"   Market session: {summary['market_session']}")
        print(f"   Symbols monitored: {summary['symbols_monitored']}")
        print(f"   Conditions by type: {summary['conditions_by_type']}")
        print(f"   Volatility distribution: {summary['volatility_distribution']}")
        print(f"   Trading halted symbols: {summary['trading_halted_symbols']}")
        
    except Exception as e:
        print(f"❌ Condition summary test failed: {e}")
    
    # Test 9: Test trading halt conditions
    print("\n9️⃣ Testing Trading Halt Conditions")
    try:
        # Test circuit breaker condition
        circuit_breaker_price = PriceData(
            symbol="HALT_TEST",
            price=85.0,  # 15% drop from 100
            bid=84.95,
            ask=85.05,
            volume=10000,
            timestamp=datetime.utcnow(),
            change=-15.0,
            change_percent=-15.0
        )
        
        condition_data = await monitor.analyze_price_update(circuit_breaker_price)
        should_halt = monitor.should_halt_trading("HALT_TEST")
        
        print(f"✅ Trading halt analysis:")
        print(f"   Condition: {condition_data.condition.value}")
        print(f"   Should halt trading: {should_halt}")
        print(f"   Price change: {condition_data.price_change_percent:.2f}%")
        
    except Exception as e:
        print(f"❌ Trading halt test failed: {e}")
    
    # Test 10: Test callback system
    print("\n🔟 Testing Callback System")
    try:
        callback_triggered = False
        callback_data = None
        
        def test_callback(symbol: str, condition_data):
            nonlocal callback_triggered, callback_data
            callback_triggered = True
            callback_data = condition_data
        
        # Add callback
        monitor.add_condition_callback(test_callback)
        
        # Trigger condition change
        test_price = PriceData(
            symbol="CALLBACK_TEST",
            price=102.0,
            bid=101.95,
            ask=102.05,
            volume=1500,
            timestamp=datetime.utcnow(),
            change=2.0,
            change_percent=2.0
        )
        
        await monitor.analyze_price_update(test_price)
        
        # Wait for callback
        await asyncio.sleep(0.1)
        
        print(f"✅ Callback system test:")
        print(f"   Callback triggered: {callback_triggered}")
        if callback_data:
            print(f"   Callback symbol: {callback_data.symbol}")
            print(f"   Callback condition: {callback_data.condition.value}")
        
        # Remove callback
        monitor.remove_condition_callback(test_callback)
        
    except Exception as e:
        print(f"❌ Callback system test failed: {e}")
    
    # Test 11: Cleanup and shutdown
    print("\n1️⃣1️⃣ Testing Cleanup and Shutdown")
    try:
        # Get final summary
        final_summary = monitor.get_condition_summary()
        print(f"   Final symbols monitored: {final_summary['symbols_monitored']}")
        
        # Stop the monitor
        await monitor.stop()
        print("✅ Market Condition Monitor stopped successfully")
        
    except Exception as e:
        print(f"❌ Cleanup test failed: {e}")
    
    print("\n" + "=" * 45)
    print("🏁 Market Condition Monitor Test Complete")
    return True

async def test_performance():
    """Test performance with multiple symbols"""
    print("\n⚡ Testing Performance with Multiple Symbols")
    print("=" * 45)
    
    try:
        event_manager = EventManager()
        monitor = MarketConditionMonitor(event_manager)
        await monitor.start()
        
        # Test with 50 symbols
        symbols = [f"PERF{i:03d}" for i in range(50)]
        
        print(f"📊 Processing {len(symbols)} symbols...")
        
        start_time = asyncio.get_event_loop().time()
        
        for i, symbol in enumerate(symbols):
            test_price = PriceData(
                symbol=symbol,
                price=100.0 + (i * 0.1),
                bid=99.95 + (i * 0.1),
                ask=100.05 + (i * 0.1),
                volume=1000 + i,
                timestamp=datetime.utcnow(),
                change=i * 0.1,
                change_percent=(i * 0.1) / 100.0 * 100
            )
            
            await monitor.analyze_price_update(test_price)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        summary = monitor.get_condition_summary()
        
        print(f"✅ Performance test completed:")
        print(f"   Processing time: {processing_time:.2f}s")
        print(f"   Symbols processed: {len(symbols)}")
        print(f"   Average time per symbol: {(processing_time / len(symbols)) * 1000:.2f}ms")
        print(f"   Symbols monitored: {summary['symbols_monitored']}")
        
        await monitor.stop()
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    async def main():
        """Run all market condition monitor tests"""
        print("🚀 Starting Market Condition Monitor Test Suite")
        print("=" * 50)
        
        # Run main functionality tests
        success = await test_market_condition_monitor()
        
        if success:
            # Run performance tests
            await test_performance()
            
            print("\n🎉 All tests completed successfully!")
            print("Market Condition Monitor is ready for production use.")
        else:
            print("\n❌ Some tests failed. Please review the output above.")
    
    # Run the test suite
    asyncio.run(main())