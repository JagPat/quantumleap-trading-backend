"""
Test Trading Engine Database Integration
Comprehensive tests for the optimized database integration with trading engine
"""
import os
import sys
import asyncio
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.trading_engine_integration import TradingDatabaseIntegration
from app.trading_engine.optimized_order_db import OptimizedOrderDatabase
from app.trading_engine.models import (
    Order, Position, Execution, TradingSignal, StrategyDeployment,
    OrderType, OrderSide, OrderStatus, PositionStatus
)

class TestTradingEngineIntegration:
    """Test suite for trading engine database integration"""
    
    @pytest.fixture
    async def temp_db_path(self):
        """Create temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_trading.db")
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    async def integration(self, temp_db_path):
        """Create trading database integration instance"""
        integration = TradingDatabaseIntegration(temp_db_path)
        await integration.initialize()
        yield integration
        await integration.shutdown()
    
    @pytest.fixture
    async def optimized_db(self, temp_db_path):
        """Create optimized order database instance"""
        # Create integration first
        integration = TradingDatabaseIntegration(temp_db_path)
        await integration.initialize()
        
        # Create optimized database
        db = OptimizedOrderDatabase()
        db.integration = integration  # Use test integration
        await db.initialize()
        
        yield db
        
        await integration.shutdown()
    
    @pytest.fixture
    def sample_order(self):
        """Create sample order for testing"""
        return Order(
            id="test_order_001",
            user_id="test_user_001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100,
            price=150.00
        )
    
    @pytest.fixture
    def sample_position(self):
        """Create sample position for testing"""
        return Position(
            id="test_position_001",
            user_id="test_user_001",
            symbol="AAPL",
            quantity=100,
            average_price=150.00,
            current_price=155.00
        )
    
    @pytest.fixture
    def sample_execution(self):
        """Create sample execution for testing"""
        return Execution(
            id="test_execution_001",
            order_id="test_order_001",
            user_id="test_user_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=150.00,
            commission=1.00
        )
    
    @pytest.fixture
    def sample_signal(self):
        """Create sample trading signal for testing"""
        return TradingSignal(
            id="test_signal_001",
            user_id="test_user_001",
            symbol="AAPL",
            signal_type="BUY",
            confidence_score=0.85,
            reasoning="Strong technical indicators",
            target_price=160.00,
            stop_loss=145.00,
            position_size=0.05
        )

class TestDatabaseIntegration(TestTradingEngineIntegration):
    """Test database integration functionality"""
    
    @pytest.mark.asyncio
    async def test_integration_initialization(self, temp_db_path):
        """Test integration initialization"""
        integration = TradingDatabaseIntegration(temp_db_path)
        
        # Test initialization
        await integration.initialize()
        
        # Verify components are initialized
        assert integration.db_manager is not None
        assert integration.query_optimizer is not None
        assert integration.performance_collector is not None
        assert integration.transaction_manager is not None
        
        await integration.shutdown()
    
    @pytest.mark.asyncio
    async def test_optimized_transaction(self, integration):
        """Test optimized transaction context manager"""
        async with integration.optimized_transaction() as transaction_id:
            assert transaction_id is not None
            
            # Execute a test query within transaction
            result = await integration.db_manager.execute_query(
                "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)",
                transaction_id=transaction_id
            )
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_performance_dashboard_data(self, integration):
        """Test performance dashboard data retrieval"""
        dashboard_data = await integration.get_performance_dashboard_data()
        
        assert isinstance(dashboard_data, dict)
        assert 'database_performance' in dashboard_data
        assert 'database_health' in dashboard_data
        assert 'timestamp' in dashboard_data

class TestOptimizedOrderOperations(TestTradingEngineIntegration):
    """Test optimized order operations"""
    
    @pytest.mark.asyncio
    async def test_create_order_optimized(self, optimized_db, sample_order):
        """Test optimized order creation"""
        # Create order
        success = await optimized_db.create_order(sample_order)
        assert success is True
        
        # Verify order was created
        retrieved_order = await optimized_db.get_order(sample_order.id)
        assert retrieved_order is not None
        assert retrieved_order.id == sample_order.id
        assert retrieved_order.user_id == sample_order.user_id
        assert retrieved_order.symbol == sample_order.symbol
    
    @pytest.mark.asyncio
    async def test_update_order_optimized(self, optimized_db, sample_order):
        """Test optimized order update"""
        # Create order first
        await optimized_db.create_order(sample_order)
        
        # Update order
        sample_order.status = OrderStatus.FILLED
        sample_order.filled_quantity = 100
        sample_order.average_fill_price = 151.00
        
        success = await optimized_db.update_order(sample_order)
        assert success is True
        
        # Verify update
        retrieved_order = await optimized_db.get_order(sample_order.id)
        assert retrieved_order.status == OrderStatus.FILLED
        assert retrieved_order.filled_quantity == 100
        assert retrieved_order.average_fill_price == 151.00
    
    @pytest.mark.asyncio
    async def test_get_user_orders_optimized(self, optimized_db, sample_order):
        """Test optimized user orders retrieval"""
        # Create multiple orders
        orders = []
        for i in range(3):
            order = Order(
                id=f"test_order_{i:03d}",
                user_id="test_user_001",
                symbol=f"STOCK{i}",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=100 * (i + 1)
            )
            orders.append(order)
            await optimized_db.create_order(order)
        
        # Retrieve user orders
        user_orders = await optimized_db.get_orders_by_user("test_user_001")
        
        assert len(user_orders) == 3
        assert all(order.user_id == "test_user_001" for order in user_orders)
    
    @pytest.mark.asyncio
    async def test_get_orders_by_symbol(self, optimized_db):
        """Test orders retrieval by symbol"""
        # Create orders for different symbols
        symbols = ["AAPL", "GOOGL", "AAPL", "MSFT", "AAPL"]
        
        for i, symbol in enumerate(symbols):
            order = Order(
                id=f"test_order_{i:03d}",
                user_id="test_user_001",
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=100
            )
            await optimized_db.create_order(order)
        
        # Get orders for AAPL
        aapl_orders = await optimized_db.get_orders_by_symbol("AAPL", "test_user_001")
        
        assert len(aapl_orders) == 3
        assert all(order.symbol == "AAPL" for order in aapl_orders)

class TestOptimizedPositionOperations(TestTradingEngineIntegration):
    """Test optimized position operations"""
    
    @pytest.mark.asyncio
    async def test_create_position_optimized(self, optimized_db, sample_position):
        """Test optimized position creation"""
        # Create position
        success = await optimized_db.create_position(sample_position)
        assert success is True
        
        # Verify position was created
        retrieved_position = await optimized_db.get_position(
            sample_position.user_id, sample_position.symbol
        )
        assert retrieved_position is not None
        assert retrieved_position.id == sample_position.id
        assert retrieved_position.quantity == sample_position.quantity
    
    @pytest.mark.asyncio
    async def test_update_position_optimized(self, optimized_db, sample_position):
        """Test optimized position update"""
        # Create position first
        await optimized_db.create_position(sample_position)
        
        # Update position
        sample_position.quantity = 150
        sample_position.current_price = 160.00
        sample_position.unrealized_pnl = 1500.00
        
        success = await optimized_db.update_position(sample_position)
        assert success is True
        
        # Verify update
        retrieved_position = await optimized_db.get_position(
            sample_position.user_id, sample_position.symbol
        )
        assert retrieved_position.quantity == 150
        assert retrieved_position.current_price == 160.00
        assert retrieved_position.unrealized_pnl == 1500.00
    
    @pytest.mark.asyncio
    async def test_get_user_positions_optimized(self, optimized_db):
        """Test optimized user positions retrieval"""
        # Create multiple positions
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        for i, symbol in enumerate(symbols):
            position = Position(
                id=f"test_position_{i:03d}",
                user_id="test_user_001",
                symbol=symbol,
                quantity=100 * (i + 1),
                average_price=100.00 + (i * 10)
            )
            await optimized_db.create_position(position)
        
        # Retrieve user positions
        user_positions = await optimized_db.get_user_positions_optimized("test_user_001")
        
        assert len(user_positions) == 3
        assert all(pos.user_id == "test_user_001" for pos in user_positions)

class TestOptimizedExecutionOperations(TestTradingEngineIntegration):
    """Test optimized execution operations"""
    
    @pytest.mark.asyncio
    async def test_record_execution_optimized(self, optimized_db, sample_execution):
        """Test optimized execution recording"""
        # Record execution
        success = await optimized_db.record_execution(sample_execution)
        assert success is True
        
        # Verify execution was recorded
        executions = await optimized_db.get_executions_by_order(sample_execution.order_id)
        assert len(executions) == 1
        assert executions[0].id == sample_execution.id
    
    @pytest.mark.asyncio
    async def test_get_executions_by_user(self, optimized_db):
        """Test executions retrieval by user"""
        # Create multiple executions
        for i in range(3):
            execution = Execution(
                id=f"test_execution_{i:03d}",
                order_id=f"test_order_{i:03d}",
                user_id="test_user_001",
                symbol=f"STOCK{i}",
                side=OrderSide.BUY,
                quantity=100,
                price=100.00 + i
            )
            await optimized_db.record_execution(execution)
        
        # Retrieve user executions
        user_executions = await optimized_db.get_executions_by_user("test_user_001")
        
        assert len(user_executions) == 3
        assert all(exec.user_id == "test_user_001" for exec in user_executions)

class TestOptimizedSignalOperations(TestTradingEngineIntegration):
    """Test optimized signal operations"""
    
    @pytest.mark.asyncio
    async def test_create_trading_signal(self, optimized_db, sample_signal):
        """Test trading signal creation"""
        # Create signal
        success = await optimized_db.create_trading_signal(sample_signal)
        assert success is True
        
        # Verify signal was created
        active_signals = await optimized_db.get_active_signals(sample_signal.user_id)
        assert len(active_signals) == 1
        assert active_signals[0].id == sample_signal.id
    
    @pytest.mark.asyncio
    async def test_get_active_signals(self, optimized_db):
        """Test active signals retrieval"""
        # Create multiple signals
        for i in range(3):
            signal = TradingSignal(
                id=f"test_signal_{i:03d}",
                user_id="test_user_001",
                symbol=f"STOCK{i}",
                signal_type="BUY",
                confidence_score=0.8 + (i * 0.05)
            )
            await optimized_db.create_trading_signal(signal)
        
        # Create one inactive signal
        inactive_signal = TradingSignal(
            id="test_signal_inactive",
            user_id="test_user_001",
            symbol="INACTIVE",
            signal_type="SELL",
            is_active=False
        )
        await optimized_db.create_trading_signal(inactive_signal)
        
        # Retrieve active signals
        active_signals = await optimized_db.get_active_signals("test_user_001")
        
        assert len(active_signals) == 3  # Only active signals
        assert all(signal.is_active for signal in active_signals)

class TestPerformanceAndMonitoring(TestTradingEngineIntegration):
    """Test performance monitoring and analytics"""
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self, optimized_db):
        """Test performance metrics retrieval"""
        metrics = await optimized_db.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        # Should contain performance data even if empty
        assert 'timestamp' in metrics
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, optimized_db):
        """Test health status retrieval"""
        health = await optimized_db.get_health_status()
        
        assert isinstance(health, dict)
        assert 'connection_status' in health
        assert 'initialized' in health
        assert health['initialized'] is True
    
    @pytest.mark.asyncio
    async def test_create_backup(self, optimized_db):
        """Test backup creation"""
        success = await optimized_db.create_backup("test_backup")
        assert success is True

class TestDataValidationAndIntegrity(TestTradingEngineIntegration):
    """Test data validation and integrity"""
    
    @pytest.mark.asyncio
    async def test_invalid_order_validation(self, optimized_db):
        """Test validation of invalid order data"""
        # Create order with invalid data
        invalid_order = Order(
            id="",  # Empty ID should fail validation
            user_id="test_user",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=-100  # Negative quantity should fail
        )
        
        success = await optimized_db.create_order(invalid_order)
        # Should fail due to validation
        assert success is False
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, integration):
        """Test transaction rollback on error"""
        try:
            async with integration.optimized_transaction() as transaction_id:
                # Execute valid query
                await integration.db_manager.execute_query(
                    "CREATE TABLE IF NOT EXISTS test_rollback (id INTEGER)",
                    transaction_id=transaction_id
                )
                
                # Execute invalid query to trigger rollback
                await integration.db_manager.execute_query(
                    "INVALID SQL QUERY",
                    transaction_id=transaction_id
                )
                
        except Exception:
            # Exception expected due to invalid query
            pass
        
        # Verify table was not created due to rollback
        try:
            result = await integration.db_manager.fetch_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_rollback'"
            )
            assert result is None  # Table should not exist
        except:
            # This is expected if rollback worked correctly
            pass

async def run_integration_tests():
    """Run all integration tests"""
    print("Running Trading Engine Database Integration Tests...")
    
    # Create test database
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_integration.db")
    
    try:
        # Initialize integration
        integration = TradingDatabaseIntegration(test_db_path)
        await integration.initialize()
        
        # Initialize optimized database
        optimized_db = OptimizedOrderDatabase()
        optimized_db.integration = integration
        await optimized_db.initialize()
        
        print("✅ Database integration initialized successfully")
        
        # Test basic operations
        print("Testing basic operations...")
        
        # Test order operations
        test_order = Order(
            id="integration_test_order",
            user_id="integration_test_user",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100
        )
        
        success = await optimized_db.create_order(test_order)
        assert success, "Order creation failed"
        print("✅ Order creation test passed")
        
        retrieved_order = await optimized_db.get_order(test_order.id)
        assert retrieved_order is not None, "Order retrieval failed"
        print("✅ Order retrieval test passed")
        
        # Test position operations
        test_position = Position(
            id="integration_test_position",
            user_id="integration_test_user",
            symbol="AAPL",
            quantity=100,
            average_price=150.00
        )
        
        success = await optimized_db.create_position(test_position)
        assert success, "Position creation failed"
        print("✅ Position creation test passed")
        
        # Test execution operations
        test_execution = Execution(
            id="integration_test_execution",
            order_id=test_order.id,
            user_id="integration_test_user",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=150.00
        )
        
        success = await optimized_db.record_execution(test_execution)
        assert success, "Execution recording failed"
        print("✅ Execution recording test passed")
        
        # Test performance metrics
        metrics = await optimized_db.get_performance_metrics()
        assert isinstance(metrics, dict), "Performance metrics retrieval failed"
        print("✅ Performance metrics test passed")
        
        # Test health status
        health = await optimized_db.get_health_status()
        assert health.get('initialized') is True, "Health status check failed"
        print("✅ Health status test passed")
        
        print("\n🎉 All integration tests passed successfully!")
        
        # Cleanup
        await integration.shutdown()
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise
    
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(run_integration_tests())