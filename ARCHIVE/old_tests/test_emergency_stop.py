"""
Test Emergency Stop System
Comprehensive tests for emergency stop functionality
"""
import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Import the emergency stop system
from app.trading_engine.emergency_stop import (
    EmergencyStopSystem,
    EmergencyStopRequest,
    EmergencyStopReason,
    EmergencyStopScope,
    emergency_stop_system
)
from app.trading_engine.models import StrategyStatus, OrderStatus

class TestEmergencyStopSystem:
    """Test cases for emergency stop system"""
    
    def setup_method(self):
        """Setup test environment"""
        self.stop_system = EmergencyStopSystem()
        self.test_user_id = "test_user_123"
        self.test_strategy_id = "test_strategy_456"
        self.test_symbol = "RELIANCE"
    
    @pytest.mark.asyncio
    async def test_user_emergency_stop_basic(self):
        """Test basic user emergency stop functionality"""
        
        # Mock dependencies
        with patch('app.trading_engine.emergency_stop.order_service') as mock_order_service, \
             patch('app.trading_engine.emergency_stop.strategy_manager') as mock_strategy_manager, \
             patch('app.trading_engine.emergency_stop.position_manager') as mock_position_manager:
            
            # Setup mocks
            mock_order_service.get_active_orders = AsyncMock(return_value=[
                {'id': 'order1', 'symbol': 'RELIANCE', 'status': 'SUBMITTED'},
                {'id': 'order2', 'symbol': 'TCS', 'status': 'PENDING'}
            ])
            mock_order_service.cancel_order = AsyncMock(return_value=True)
            
            mock_strategy_manager.get_user_strategies = AsyncMock(return_value=[
                {'strategy_id': 'strategy1', 'status': 'ACTIVE', 'symbols': ['RELIANCE']},
                {'strategy_id': 'strategy2', 'status': 'ACTIVE', 'symbols': ['TCS']}
            ])
            mock_strategy_manager.pause_strategy = AsyncMock(return_value=True)
            
            # Create emergency stop request
            request = EmergencyStopRequest(
                user_id=self.test_user_id,
                reason=EmergencyStopReason.USER_INITIATED,
                scope=EmergencyStopScope.USER,
                message="Test emergency stop"
            )
            
            # Execute emergency stop
            result = await self.stop_system.execute_emergency_stop(request)
            
            # Verify results
            assert result.success == True
            assert result.orders_cancelled == 2
            assert result.strategies_paused == 2
            assert result.positions_closed == 0
            assert len(result.errors) == 0
            assert result.execution_time_ms > 0
            
            # Verify mock calls
            mock_order_service.get_active_orders.assert_called_once_with(self.test_user_id)
            assert mock_order_service.cancel_order.call_count == 2
            mock_strategy_manager.get_user_strategies.assert_called_once_with(self.test_user_id)
            assert mock_strategy_manager.pause_strategy.call_count == 2
    
    @pytest.mark.asyncio
    async def test_strategy_emergency_stop(self):
        """Test strategy-specific emergency stop"""
        
        with patch('app.trading_engine.emergency_stop.order_service') as mock_order_service, \
             patch('app.trading_engine.emergency_stop.strategy_manager') as mock_strategy_manager:
            
            # Setup mocks
            mock_order_service.get_active_orders = AsyncMock(return_value=[
                {'id': 'order1', 'symbol': 'RELIANCE', 'strategy_id': self.test_strategy_id},
                {'id': 'order2', 'symbol': 'TCS', 'strategy_id': 'other_strategy'}
            ])
            mock_order_service.cancel_order = AsyncMock(return_value=True)
            mock_strategy_manager.pause_strategy = AsyncMock(return_value=True)
            mock_strategy_manager.get_strategy_status = AsyncMock(return_value={
                'strategy_id': self.test_strategy_id,
                'symbols': ['RELIANCE']
            })
            
            # Create strategy emergency stop request
            request = EmergencyStopRequest(
                user_id=self.test_user_id,
                reason=EmergencyStopReason.USER_INITIATED,
                scope=EmergencyStopScope.STRATEGY,
                target_id=self.test_strategy_id,
                message="Test strategy stop"
            )
            
            # Execute emergency stop
            result = await self.stop_system.execute_emergency_stop(request)
            
            # Verify results
            assert result.success == True
            assert result.orders_cancelled == 1  # Only orders for this strategy
            assert result.strategies_paused == 1  # Only this strategy
            assert len(result.errors) == 0
            
            # Verify strategy was paused
            mock_strategy_manager.pause_strategy.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_panic_button_functionality(self):
        """Test panic button (close positions)"""
        
        with patch('app.trading_engine.emergency_stop.order_service') as mock_order_service, \
             patch('app.trading_engine.emergency_stop.strategy_manager') as mock_strategy_manager, \
             patch('app.trading_engine.emergency_stop.position_manager') as mock_position_manager:
            
            # Setup mocks
            mock_order_service.get_active_orders = AsyncMock(return_value=[])
            mock_strategy_manager.get_user_strategies = AsyncMock(return_value=[])
            mock_position_manager.get_user_positions = AsyncMock(return_value=[
                {'symbol': 'RELIANCE', 'is_closed': False},
                {'symbol': 'TCS', 'is_closed': False}
            ])
            mock_position_manager.close_position = AsyncMock(return_value=True)
            
            # Execute panic button
            result = await self.stop_system.user_emergency_stop(
                user_id=self.test_user_id,
                reason="PANIC BUTTON",
                close_positions=True
            )
            
            # Verify results
            assert result.success == True
            assert result.positions_closed == 2
            
            # Verify positions were closed
            assert mock_position_manager.close_position.call_count == 2
    
    @pytest.mark.asyncio
    async def test_emergency_stop_with_errors(self):
        """Test emergency stop handling when some operations fail"""
        
        with patch('app.trading_engine.emergency_stop.order_service') as mock_order_service, \
             patch('app.trading_engine.emergency_stop.strategy_manager') as mock_strategy_manager:
            
            # Setup mocks with some failures
            mock_order_service.get_active_orders = AsyncMock(return_value=[
                {'id': 'order1', 'symbol': 'RELIANCE'},
                {'id': 'order2', 'symbol': 'TCS'}
            ])
            # First order cancellation succeeds, second fails
            mock_order_service.cancel_order = AsyncMock(side_effect=[True, False])
            
            mock_strategy_manager.get_user_strategies = AsyncMock(return_value=[
                {'strategy_id': 'strategy1', 'status': 'ACTIVE'}
            ])
            mock_strategy_manager.pause_strategy = AsyncMock(return_value=True)
            
            # Create emergency stop request
            request = EmergencyStopRequest(
                user_id=self.test_user_id,
                reason=EmergencyStopReason.USER_INITIATED,
                scope=EmergencyStopScope.USER
            )
            
            # Execute emergency stop
            result = await self.stop_system.execute_emergency_stop(request)
            
            # Verify partial success
            assert result.orders_cancelled == 1  # Only one order cancelled successfully
            assert result.strategies_paused == 1  # Strategy paused successfully
    
    @pytest.mark.asyncio
    async def test_risk_violation_emergency_stop(self):
        """Test emergency stop triggered by risk violation"""
        
        with patch('app.trading_engine.emergency_stop.order_service') as mock_order_service, \
             patch('app.trading_engine.emergency_stop.strategy_manager') as mock_strategy_manager, \
             patch('app.trading_engine.emergency_stop.position_manager') as mock_position_manager:
            
            # Setup mocks
            mock_order_service.get_active_orders = AsyncMock(return_value=[])
            mock_strategy_manager.get_user_strategies = AsyncMock(return_value=[])
            mock_position_manager.get_user_positions = AsyncMock(return_value=[
                {'symbol': 'RELIANCE', 'is_closed': False}
            ])
            mock_position_manager.close_position = AsyncMock(return_value=True)
            
            # Execute risk-based emergency stop
            result = await self.stop_system.risk_emergency_stop(
                user_id=self.test_user_id,
                risk_violation="Maximum drawdown exceeded"
            )
            
            # Verify results
            assert result.success == True
            assert result.request.reason == EmergencyStopReason.RISK_VIOLATION
            assert result.request.close_positions == True  # Risk violations should close positions
            assert result.positions_closed == 1
    
    def test_emergency_stop_history(self):
        """Test emergency stop history tracking"""
        
        # Create some mock history
        from app.trading_engine.emergency_stop import EmergencyStopResult
        
        mock_result = EmergencyStopResult(
            success=True,
            request=EmergencyStopRequest(
                user_id=self.test_user_id,
                reason=EmergencyStopReason.USER_INITIATED,
                scope=EmergencyStopScope.USER,
                message="Test stop"
            ),
            orders_cancelled=2,
            strategies_paused=1,
            execution_time_ms=150.5
        )
        
        # Add to history
        self.stop_system.stop_history.append(mock_result)
        
        # Get history
        history = self.stop_system.get_stop_history(user_id=self.test_user_id)
        
        # Verify history
        assert len(history) == 1
        assert history[0]['user_id'] == self.test_user_id
        assert history[0]['success'] == True
        assert history[0]['orders_cancelled'] == 2
        assert history[0]['strategies_paused'] == 1
    
    def test_active_stops_tracking(self):
        """Test active emergency stops tracking"""
        
        # Initially no active stops
        active_stops = self.stop_system.get_active_stops()
        assert len(active_stops) == 0
        
        # Add a mock active stop
        from app.trading_engine.emergency_stop import EmergencyStopResult
        
        mock_result = EmergencyStopResult(
            success=False,  # Still in progress
            request=EmergencyStopRequest(
                user_id=self.test_user_id,
                reason=EmergencyStopReason.USER_INITIATED,
                scope=EmergencyStopScope.USER
            )
        )
        
        stop_id = f"{self.test_user_id}_USER_{datetime.now().timestamp()}"
        self.stop_system.active_stops[stop_id] = mock_result
        
        # Get active stops
        active_stops = self.stop_system.get_active_stops()
        
        # Verify active stop
        assert len(active_stops) == 1
        assert active_stops[0]['user_id'] == self.test_user_id
        assert active_stops[0]['scope'] == 'USER'

# Integration test
@pytest.mark.asyncio
async def test_emergency_stop_integration():
    """Integration test for emergency stop system"""
    
    print("Testing Emergency Stop System Integration...")
    
    # Test user emergency stop
    result = await emergency_stop_system.user_emergency_stop(
        user_id="integration_test_user",
        reason="Integration test",
        close_positions=False
    )
    
    print(f"Emergency stop result: {result.success}")
    print(f"Orders cancelled: {result.orders_cancelled}")
    print(f"Strategies paused: {result.strategies_paused}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"Errors: {result.errors}")
    
    # Test history retrieval
    history = emergency_stop_system.get_stop_history(user_id="integration_test_user", limit=5)
    print(f"History entries: {len(history)}")
    
    # Test active stops
    active_stops = emergency_stop_system.get_active_stops()
    print(f"Active stops: {len(active_stops)}")
    
    print("Integration test completed successfully!")

if __name__ == "__main__":
    # Run integration test
    asyncio.run(test_emergency_stop_integration())