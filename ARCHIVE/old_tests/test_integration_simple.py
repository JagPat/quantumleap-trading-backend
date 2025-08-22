"""
Simple Integration Test for Trading Engine Database
Tests the integration without external dependencies
"""
import os
import sys
import asyncio
import tempfile
import shutil
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.database.trading_engine_integration import TradingDatabaseIntegration
    from app.trading_engine.optimized_order_db import OptimizedOrderDatabase
    from app.trading_engine.models import (
        Order, Position, Execution, TradingSignal,
        OrderType, OrderSide, OrderStatus
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required modules are available")
    sys.exit(1)

async def test_basic_integration():
    """Test basic integration functionality"""
    print("🧪 Testing Trading Engine Database Integration...")
    
    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_integration.db")
    
    try:
        print(f"📁 Using temporary database: {test_db_path}")
        
        # Initialize integration
        print("🔧 Initializing database integration...")
        integration = TradingDatabaseIntegration(test_db_path)
        await integration.initialize()
        print("✅ Database integration initialized")
        
        # Initialize optimized database
        print("🔧 Initializing optimized order database...")
        optimized_db = OptimizedOrderDatabase()
        optimized_db.integration = integration
        await optimized_db.initialize()
        print("✅ Optimized order database initialized")
        
        # Test 1: Order Operations
        print("\n📋 Testing Order Operations...")
        
        test_order = Order(
            id="test_order_001",
            user_id="test_user_001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100,
            price=150.00
        )
        
        # Create order
        success = await optimized_db.create_order(test_order)
        assert success, "❌ Order creation failed"
        print("✅ Order created successfully")
        
        # Retrieve order
        retrieved_order = await optimized_db.get_order(test_order.id)
        assert retrieved_order is not None, "❌ Order retrieval failed"
        assert retrieved_order.id == test_order.id, "❌ Order ID mismatch"
        print("✅ Order retrieved successfully")
        
        # Update order
        test_order.status = OrderStatus.FILLED
        test_order.filled_quantity = 100
        success = await optimized_db.update_order(test_order)
        assert success, "❌ Order update failed"
        print("✅ Order updated successfully")
        
        # Test 2: Position Operations
        print("\n📊 Testing Position Operations...")
        
        test_position = Position(
            id="test_position_001",
            user_id="test_user_001",
            symbol="AAPL",
            quantity=100,
            average_price=150.00,
            current_price=155.00
        )
        
        # Create position
        success = await optimized_db.create_position(test_position)
        assert success, "❌ Position creation failed"
        print("✅ Position created successfully")
        
        # Retrieve position
        retrieved_position = await optimized_db.get_position(
            test_position.user_id, test_position.symbol
        )
        assert retrieved_position is not None, "❌ Position retrieval failed"
        print("✅ Position retrieved successfully")
        
        # Test 3: Execution Operations
        print("\n⚡ Testing Execution Operations...")
        
        test_execution = Execution(
            id="test_execution_001",
            order_id=test_order.id,
            user_id="test_user_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=150.00,
            commission=1.00
        )
        
        # Record execution
        success = await optimized_db.record_execution(test_execution)
        assert success, "❌ Execution recording failed"
        print("✅ Execution recorded successfully")
        
        # Retrieve executions
        executions = await optimized_db.get_executions_by_order(test_order.id)
        assert len(executions) == 1, "❌ Execution retrieval failed"
        print("✅ Execution retrieved successfully")
        
        # Test 4: Signal Operations
        print("\n📡 Testing Signal Operations...")
        
        test_signal = TradingSignal(
            id="test_signal_001",
            user_id="test_user_001",
            symbol="AAPL",
            signal_type="BUY",
            confidence_score=0.85,
            reasoning="Strong technical indicators"
        )
        
        # Create signal
        success = await optimized_db.create_trading_signal(test_signal)
        assert success, "❌ Signal creation failed"
        print("✅ Signal created successfully")
        
        # Retrieve active signals
        signals = await optimized_db.get_active_signals("test_user_001")
        assert len(signals) == 1, "❌ Signal retrieval failed"
        print("✅ Signal retrieved successfully")
        
        # Test 5: Performance Metrics
        print("\n📈 Testing Performance Metrics...")
        
        metrics = await optimized_db.get_performance_metrics()
        assert isinstance(metrics, dict), "❌ Performance metrics retrieval failed"
        print("✅ Performance metrics retrieved successfully")
        
        # Test 6: Health Status
        print("\n🏥 Testing Health Status...")
        
        health = await optimized_db.get_health_status()
        assert isinstance(health, dict), "❌ Health status retrieval failed"
        assert health.get('initialized') is True, "❌ Database not properly initialized"
        print("✅ Health status retrieved successfully")
        
        # Test 7: Transaction Operations
        print("\n🔄 Testing Transaction Operations...")
        
        async with integration.optimized_transaction() as transaction_id:
            assert transaction_id is not None, "❌ Transaction creation failed"
            
            # Execute a test query within transaction
            result = await integration.db_manager.execute_query(
                "SELECT COUNT(*) FROM orders WHERE user_id = ?",
                ("test_user_001",),
                transaction_id=transaction_id
            )
            assert result is not None, "❌ Transaction query failed"
        
        print("✅ Transaction operations successful")
        
        # Test 8: Bulk Operations
        print("\n📦 Testing Bulk Operations...")
        
        # Create multiple orders
        bulk_orders = []
        for i in range(5):
            order = Order(
                id=f"bulk_order_{i:03d}",
                user_id="test_user_001",
                symbol=f"STOCK{i}",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=100 * (i + 1)
            )
            bulk_orders.append(order)
            success = await optimized_db.create_order(order)
            assert success, f"❌ Bulk order {i} creation failed"
        
        # Retrieve user orders
        user_orders = await optimized_db.get_orders_by_user("test_user_001")
        assert len(user_orders) >= 5, "❌ Bulk order retrieval failed"
        print("✅ Bulk operations successful")
        
        print("\n🎉 All integration tests passed successfully!")
        
        # Cleanup
        await integration.shutdown()
        print("✅ Database integration shutdown completed")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"🧹 Cleaned up temporary directory: {temp_dir}")

async def test_performance_monitoring():
    """Test performance monitoring functionality"""
    print("\n📊 Testing Performance Monitoring...")
    
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_performance.db")
    
    try:
        # Initialize integration
        integration = TradingDatabaseIntegration(test_db_path)
        await integration.initialize()
        
        # Test performance dashboard
        from app.database.trading_performance_dashboard import TradingPerformanceDashboard
        
        dashboard = TradingPerformanceDashboard()
        dashboard.integration = integration
        
        # Test dashboard data retrieval
        dashboard_data = await dashboard.get_dashboard_data()
        assert isinstance(dashboard_data, dict), "❌ Dashboard data retrieval failed"
        print("✅ Performance dashboard data retrieved")
        
        # Test metrics collection
        current_metrics = await dashboard.get_current_metrics()
        assert isinstance(current_metrics, list), "❌ Current metrics retrieval failed"
        print("✅ Current metrics retrieved")
        
        # Test performance summary
        summary = await dashboard.get_performance_summary()
        assert isinstance(summary, dict), "❌ Performance summary retrieval failed"
        assert 'health_score' in summary, "❌ Health score missing from summary"
        print("✅ Performance summary retrieved")
        
        # Test trading-specific metrics
        trading_metrics = await dashboard.get_trading_specific_metrics()
        assert isinstance(trading_metrics, dict), "❌ Trading metrics retrieval failed"
        print("✅ Trading-specific metrics retrieved")
        
        print("✅ Performance monitoring tests passed")
        
        await integration.shutdown()
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

async def main():
    """Run all integration tests"""
    print("🚀 Starting Trading Engine Database Integration Tests")
    print("=" * 60)
    
    # Test basic integration
    basic_success = await test_basic_integration()
    
    # Test performance monitoring
    performance_success = await test_performance_monitoring()
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"Basic Integration: {'✅ PASSED' if basic_success else '❌ FAILED'}")
    print(f"Performance Monitoring: {'✅ PASSED' if performance_success else '❌ FAILED'}")
    
    overall_success = basic_success and performance_success
    
    if overall_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("The trading engine database integration is working correctly.")
        print("\nNext steps:")
        print("1. Run the migration script: python app/database/migrate_trading_engine.py")
        print("2. Update your trading engine components to use the optimized database")
        print("3. Monitor performance using the dashboard")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Please check the error messages above and fix any issues.")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)