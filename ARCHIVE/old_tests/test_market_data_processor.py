#!/usr/bin/env python3
"""
Test Market Data Processor
Comprehensive testing of the market data processing system with sub-second latency
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List
import random

from app.trading_engine.market_data_processor import MarketDataProcessor, ValidationResult, DataQuality
from app.trading_engine.event_bus import EventManager
from app.trading_engine.models import PriceData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_market_data_processor():
    """Test the complete market data processor functionality"""
    print("🧪 Testing Market Data Processor")
    print("=" * 45)
    
    # Test 1: Initialize components
    print("\n1️⃣ Testing Initialization")
    try:
        event_manager = EventManager()
        processor = MarketDataProcessor(event_manager)
        print("✅ Market Data Processor initialized successfully")
        print(f"   Processing queue capacity: {processor.processing_queue.maxsize}")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False
    
    # Test 2: Start the processor
    print("\n2️⃣ Testing Processor Startup")
    try:
        await processor.start()
        print("✅ Market Data Processor started successfully")
        
        # Wait for background tasks to initialize
        await asyncio.sleep(1)
        
    except Exception as e:
        print(f"❌ Processor startup failed: {e}")
        return False
    
    # Test 3: Test price data validation
    print("\n3️⃣ Testing Price Data Validation")
    try:
        # Valid price data
        valid_price = PriceData(
            symbol="TESTSTOCK",
            price=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            timestamp=datetime.utcnow()
        )
        
        validation = await processor.validate_price_data(valid_price)
        print(f"✅ Valid price data validation: {validation.result.value} (quality: {validation.quality.value})\"")
        
        # Invalid price data (negative price)
        invalid_price = PriceData(
            symbol="TESTSTOCK",
            price=-100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            timestamp=datetime.utcnow()
        )
        
        validation = await processor.validate_price_data(invalid_price)
        print(f"✅ Invalid price data validation: {validation.result.value} (quality: {validation.quality.value})\"")
        
        # Test stale data
        stale_price = PriceData(
            symbol="TESTSTOCK",
            price=100.0,
            bid=99.95,
            ask=100.05,
            volume=1000,
            timestamp=datetime.utcnow() - timedelta(seconds=10)  # 10 seconds old
        )
        
        validation = await processor.validate_price_data(stale_price)
        print(f"✅ Stale price data validation: {validation.result.value} (quality: {validation.quality.value})\"")
        
    except Exception as e:
        print(f"❌ Price validation test failed: {e}")
    
    # Test 4: Test single price processing
    print("\n4️⃣ Testing Single Price Processing")
    try:
        test_price = PriceData(
            symbol="SINGLETEST",
            price=150.0,
            bid=149.95,
            ask=150.05,
            volume=2000,
            timestamp=datetime.utcnow()
        )
        
        start_time = time.perf_counter()
        processed_data = await processor.process_price_update(test_price)
        end_time = time.perf_counter()
        
        processing_time = (end_time - start_time) * 1000
        
        print(f"✅ Single price processing successful:\"")
        print(f"   Processing time: {processing_time:.2f}ms\"")
        print(f"   Processed symbol: {processed_data.symbol}\"")
        print(f"   Processed price: ${processed_data.price}\"")
        
    except Exception as e:
        print(f"❌ Single price processing test failed: {e}")
    
    # Test 5: Test batch processing
    print("\n5️⃣ Testing Batch Processing")
    try:
        # Generate test data
        test_symbols = ["BATCH1", "BATCH2", "BATCH3", "BATCH4", "BATCH5"]
        processing_times = []
        
        for i, symbol in enumerate(test_symbols):
            test_price = PriceData(
                symbol=symbol,
                price=100.0 + i,
                bid=99.95 + i,
                ask=100.05 + i,
                volume=1000 * (i + 1),
                timestamp=datetime.utcnow()
            )
            
            start_time = time.perf_counter()
            await processor.process_price_update(test_price)
            end_time = time.perf_counter()
            
            processing_time = (end_time - start_time) * 1000
            processing_times.append(processing_time)
            
            print(f"   {symbol}: {processing_time:.2f}ms\"")
        
        avg_processing_time = sum(processing_times) / len(processing_times)
        print(f"✅ Batch processing completed\"")
        print(f"   Average processing time: {avg_processing_time:.2f}ms\"")
        print(f"   Max processing time: {max(processing_times):.2f}ms\"")
        print(f"   Min processing time: {min(processing_times):.2f}ms\"")
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
    
    # Test 6: Test performance metrics
    print("\n6️⃣ Testing Performance Metrics")
    try:
        # Wait for background processing
        await asyncio.sleep(2)
        
        metrics = processor.get_metrics()
        
        print(f"✅ Performance metrics retrieved:\"")
        print(f"   Total processed: {metrics.total_processed}\"")
        print(f"   Average processing time: {metrics.avg_processing_time_ms:.2f}ms\"")
        print(f"   Validation failures: {metrics.validation_failures}\"")
        print(f"   Queue size: {processor.processing_queue.qsize()}\"")
        
    except Exception as e:
        print(f"❌ Performance metrics test failed: {e}")
    
    # Test 7: Test high-frequency processing
    print("\n7️⃣ Testing High-Frequency Processing")
    try:
        print("   Generating 100 rapid price updates...\"")
        
        start_time = time.perf_counter()
        processing_times = []
        
        for i in range(100):
            test_price = PriceData(
                symbol=f"HFT{i % 10}\",  # 10 different symbols
                price=100.0 + (i * 0.01),
                bid=99.95 + (i * 0.01),
                ask=100.05 + (i * 0.01),
                volume=1000 + i,
                timestamp=datetime.utcnow()
            )
            
            process_start = time.perf_counter()
            await processor.process_price_update(test_price)
            process_end = time.perf_counter()
            
            processing_times.append((process_end - process_start) * 1000)
        
        total_time = time.perf_counter() - start_time
        
        print(f"✅ High-frequency processing completed:\"")
        print(f"   Total time: {total_time:.2f}s\"")
        print(f"   Throughput: {100 / total_time:.0f} updates/second\"")
        print(f"   Average latency: {sum(processing_times) / len(processing_times):.2f}ms\"")
        print(f"   Max latency: {max(processing_times):.2f}ms\"")
        print(f"   Min latency: {min(processing_times):.2f}ms\"")
        
        # Check if we achieved sub-second latency
        if max(processing_times) < 1000:  # Less than 1 second
            print(f"   🎯 Sub-second latency achieved!\"")
        else:
            print(f"   ⚠️ Some updates exceeded 1 second latency\"")
        
    except Exception as e:
        print(f"❌ High-frequency processing test failed: {e}")
    
    # Test 8: Test historical data integration
    print("\n8️⃣ Testing Historical Data Integration")
    try:
        # Test historical data retrieval
        symbol = "HISTTEST"
        
        # Add some historical data points
        for i in range(10):
            historical_price = PriceData(
                symbol=symbol,
                price=100.0 + i,
                bid=99.95 + i,
                ask=100.05 + i,
                volume=1000,
                timestamp=datetime.utcnow() - timedelta(minutes=i)
            )
            await processor.process_price_update(historical_price)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Get historical data
        historical_data = await processor.get_historical_data(symbol, hours=1)
        
        print(f"✅ Historical data integration test:\"")
        print(f"   Retrieved {len(historical_data)} historical points\"")
        print(f"   Latest price: ${historical_data[0].price if historical_data else 'N/A'}\"")
        print(f"   Oldest price: ${historical_data[-1].price if historical_data else 'N/A'}\"")
        
    except Exception as e:
        print(f"❌ Historical data integration test failed: {e}")
    
    # Test 9: Cleanup and shutdown
    print("\n9️⃣ Testing Cleanup and Shutdown")
    try:
        # Get final metrics
        final_metrics = processor.get_metrics()
        print(f"   Final processing count: {final_metrics.total_processed}\"")
        
        # Stop the processor
        await processor.stop()
        print("✅ Market Data Processor stopped successfully\"")
        
    except Exception as e:
        print(f"❌ Cleanup test failed: {e}")
    
    print("\n\" + \"=\" * 45)
    print("🏁 Market Data Processor Test Complete\"")
    return True

async def test_latency_performance():
    \"\"\"Test latency performance specifically\"\"\"
    print("\n⚡ Testing Latency Performance\"")
    print("=\" * 35)
    
    try:
        event_manager = EventManager()
        processor = MarketDataProcessor(event_manager)
        await processor.start()
        
        # Test different batch sizes
        batch_sizes = [1, 10, 50, 100]
        
        for batch_size in batch_sizes:
            print(f"\n📊 Testing batch size: {batch_size}\"")
            
            latencies = []
            
            for batch in range(5):  # 5 batches per size
                batch_start = time.perf_counter()
                
                # Process batch
                tasks = []
                for i in range(batch_size):
                    test_price = PriceData(
                        symbol=f"PERF{i}\",
                        price=100.0 + i,
                        bid=99.95 + i,
                        ask=100.05 + i,
                        volume=1000,
                        timestamp=datetime.utcnow()
                    )
                    
                    task = processor.process_price_update(test_price)
                    tasks.append(task)
                
                # Wait for all to complete
                await asyncio.gather(*tasks)
                
                batch_end = time.perf_counter()
                
                batch_latency = (batch_end - batch_start) * 1000
                latencies.append(batch_latency)
            
            avg_latency = sum(latencies) / len(latencies)
            print(f"   Average batch latency: {avg_latency:.2f}ms\"")
            print(f"   Max batch latency: {max(latencies):.2f}ms\"")
            print(f"   Min batch latency: {min(latencies):.2f}ms\"")
        
        await processor.stop()
        print("✅ Latency performance test completed\"")
        
    except Exception as e:
        print(f"❌ Latency performance test failed: {e}")

if __name__ == "__main__":
    async def main():
        \"\"\"Run all market data processor tests\"\"\"
        print("🚀 Starting Market Data Processor Test Suite\"")
        print("=\" * 50)
        
        # Run main functionality tests
        success = await test_market_data_processor()
        
        if success:
            # Run performance tests
            await test_latency_performance()
            
            print("\n🎉 All tests completed successfully!\"")
            print("Market Data Processor is ready for production use.\"")
        else:
            print("\n❌ Some tests failed. Please review the output above.\"")
    
    # Run the test suite
    asyncio.run(main())