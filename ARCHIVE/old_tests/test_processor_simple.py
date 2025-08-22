#!/usr/bin/env python3
"""
Simple Market Data Processor Test
Quick test to verify the market data processor is working correctly
"""
import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_processor_basic():
    """Basic test of market data processor"""
    try:
        print("🧪 Testing Market Data Processor - Basic Functionality")
        print("=" * 55)
        
        # Import components
        from app.trading_engine.event_bus import EventManager
        from app.trading_engine.market_data_processor import MarketDataProcessor
        from app.trading_engine.models import PriceData
        
        # Initialize components
        print("\n1️⃣ Initializing components...")
        event_manager = EventManager()
        processor = MarketDataProcessor(event_manager)
        print("✅ Components initialized successfully")
        
        # Start processor
        print("\n2️⃣ Starting processor...")
        await processor.start()
        print("✅ Processor started successfully")
        
        # Test price processing
        print("\n3️⃣ Testing price processing...")
        test_price = PriceData(
            symbol="TESTSTOCK",
            price=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            timestamp=datetime.utcnow()
        )
        
        # Process the price
        processed_data = await processor.process_price_data(test_price)
        print(f"✅ Price processed successfully: {processed_data.symbol} @ ${processed_data.price}")
        
        # Test validation
        print("\n4️⃣ Testing price validation...")
        validation = await processor.validate_price_data(test_price)
        print(f"✅ Price validation: {validation.result.value} (quality: {validation.quality.value})")
        
        # Get metrics
        print("\n5️⃣ Getting metrics...")
        metrics = processor.get_metrics()
        print(f"✅ Metrics retrieved: {metrics.total_updates} processed")
        
        # Stop processor
        print("\n6️⃣ Stopping processor...")
        await processor.stop()
        print("✅ Processor stopped successfully")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed with exception")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_processor_basic())
    if success:
        print("\n✅ Market Data Processor is working correctly!")
    else:
        print("\n❌ Market Data Processor has issues that need to be fixed.")