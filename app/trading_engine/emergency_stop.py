"""
Emergency Stop System
Provides immediate order cancellation and strategy pausing functionality
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .models import StrategyStatus, OrderStatus
from .event_bus import event_bus, EventType, publish_emergency_stop, TradingEvent, EventHandler
from .monitoring import trading_monitor, time_async_operation
# Import will be done dynamically to avoid circular imports
# from .strategy_manager import strategy_manager
# from .order_service import order_service
# from .position_manager import position_manager
# from .risk_engine import risk_engine

logger = logging.getLogger(__name__)

class EmergencyStopReason(str, Enum):
    """Reasons for emergency stop"""
    USER_INITIATED = "USER_INITIATED"
    RISK_VIOLATION = "RISK_VIOLATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    MARKET_CONDITION = "MARKET_CONDITION"
    CONNECTIVITY_ISSUE = "CONNECTIVITY_ISSUE"
    REGULATORY_HALT = "REGULATORY_HALT"

class EmergencyStopScope(str, Enum):
    """Scope of emergency stop"""
    USER = "USER"           # Stop for specific user
    STRATEGY = "STRATEGY"   # Stop specific strategy
    SYMBOL = "SYMBOL"       # Stop trading for specific symbol
    SYSTEM = "SYSTEM"       # System-wide stop

@dataclass
class EmergencyStopRequest:
    """Emergency stop request"""
    user_id: str
    reason: EmergencyStopReason
    scope: EmergencyStopScope
    target_id: Optional[str] = None  # Strategy ID, symbol, etc.
    message: str = ""
    initiated_by: str = "system"
    cancel_orders: bool = True
    pause_strategies: bool = True
    close_positions: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class EmergencyStopResult:
    """Result of emergency stop execution"""
    success: bool
    request: EmergencyStopRequest
    orders_cancelled: int = 0
    strategies_paused: int = 0
    positions_closed: int = 0
    errors: List[str] = None
    execution_time_ms: float = 0.0
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.completed_at is None:
            self.completed_at = datetime.now()

class EmergencyStopSystem:
    """
    Emergency stop system for immediate trading halt
    """
    
    def __init__(self):
        self.active_stops: Dict[str, EmergencyStopResult] = {}
        self.stop_history: List[EmergencyStopResult] = []
        self.max_history_size = 1000
        
        # Register event handler for emergency stop events
        self._register_event_handlers()
        
        logger.info("EmergencyStopSystem initialized")
    
    def _register_event_handlers(self):
        """Register event handlers for emergency stop events"""
        class EmergencyStopHandler(EventHandler):
            def __init__(self, stop_system):
                super().__init__("emergency_stop_handler", [EventType.EMERGENCY_STOP])
                self.stop_system = stop_system
            
            async def handle_event(self, event: TradingEvent) -> bool:
                try:
                    await self.stop_system._handle_emergency_stop_event(event)
                    return True
                except Exception as e:
                    logger.error(f"Error handling emergency stop event: {e}")
                    return False
        
        # Register the handler
        handler = EmergencyStopHandler(self)
        event_bus.register_handler(handler)
    
    async def _handle_emergency_stop_event(self, event: TradingEvent):
        """Handle emergency stop event from event bus"""
        try:
            data = event.data
            request = EmergencyStopRequest(
                user_id=event.user_id,
                reason=EmergencyStopReason(data.get('reason', 'SYSTEM_ERROR')),
                scope=EmergencyStopScope(data.get('scope', 'USER')),
                target_id=data.get('target_id'),
                message=data.get('message', ''),
                initiated_by=data.get('initiated_by', 'system'),
                cancel_orders=data.get('cancel_orders', True),
                pause_strategies=data.get('pause_strategies', True),
                close_positions=data.get('close_positions', False)
            )
            
            await self.execute_emergency_stop(request)
            
        except Exception as e:
            logger.error(f"Error handling emergency stop event: {e}")
    
    @time_async_operation("emergency_stop")
    async def execute_emergency_stop(self, request: EmergencyStopRequest) -> EmergencyStopResult:
        """
        Execute emergency stop based on request
        
        Args:
            request: Emergency stop request
            
        Returns:
            EmergencyStopResult with execution details
        """
        start_time = datetime.now()
        
        try:
            logger.critical(f"EMERGENCY STOP initiated for user {request.user_id}: {request.reason.value}")
            
            # Create result object
            result = EmergencyStopResult(
                success=False,
                request=request
            )
            
            # Store active stop
            stop_id = f"{request.user_id}_{request.scope.value}_{start_time.timestamp()}"
            self.active_stops[stop_id] = result
            
            # Execute stop actions based on scope
            if request.scope == EmergencyStopScope.USER:
                await self._execute_user_emergency_stop(request, result)
            elif request.scope == EmergencyStopScope.STRATEGY:
                await self._execute_strategy_emergency_stop(request, result)
            elif request.scope == EmergencyStopScope.SYMBOL:
                await self._execute_symbol_emergency_stop(request, result)
            elif request.scope == EmergencyStopScope.SYSTEM:
                await self._execute_system_emergency_stop(request, result)
            
            # Calculate execution time
            end_time = datetime.now()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
            result.completed_at = end_time
            result.success = len(result.errors) == 0
            
            # Publish emergency stop completion event
            await self._publish_stop_completion(result)
            
            # Move to history
            self.stop_history.append(result)
            if len(self.stop_history) > self.max_history_size:
                self.stop_history.pop(0)
            
            # Remove from active stops
            if stop_id in self.active_stops:
                del self.active_stops[stop_id]
            
            # Update monitoring
            trading_monitor.increment_counter("emergency_stops_executed")
            if result.success:
                trading_monitor.increment_counter("emergency_stops_successful")
            else:
                trading_monitor.increment_counter("emergency_stops_failed")
            
            logger.critical(f"Emergency stop completed for user {request.user_id} in {result.execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            error_msg = f"Critical error in emergency stop execution: {str(e)}"
            logger.critical(error_msg)
            
            result = EmergencyStopResult(
                success=False,
                request=request,
                errors=[error_msg]
            )
            
            trading_monitor.increment_counter("emergency_stops_failed")
            return result
    
    async def _execute_user_emergency_stop(self, request: EmergencyStopRequest, result: EmergencyStopResult):
        """Execute emergency stop for a specific user"""
        try:
            # Cancel all active orders for the user
            if request.cancel_orders:
                cancelled_orders = await self._cancel_user_orders(request.user_id)
                result.orders_cancelled = cancelled_orders
                logger.info(f"Cancelled {cancelled_orders} orders for user {request.user_id}")
            
            # Pause all active strategies for the user
            if request.pause_strategies:
                paused_strategies = await self._pause_user_strategies(request.user_id, request.reason.value)
                result.strategies_paused = paused_strategies
                logger.info(f"Paused {paused_strategies} strategies for user {request.user_id}")
            
            # Close all positions if requested
            if request.close_positions:
                closed_positions = await self._close_user_positions(request.user_id)
                result.positions_closed = closed_positions
                logger.info(f"Closed {closed_positions} positions for user {request.user_id}")
            
        except Exception as e:
            error_msg = f"Error in user emergency stop: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_strategy_emergency_stop(self, request: EmergencyStopRequest, result: EmergencyStopResult):
        """Execute emergency stop for a specific strategy"""
        try:
            if not request.target_id:
                result.errors.append("Strategy ID required for strategy emergency stop")
                return
            
            strategy_id = request.target_id
            
            # Cancel orders for this strategy
            if request.cancel_orders:
                cancelled_orders = await self._cancel_strategy_orders(request.user_id, strategy_id)
                result.orders_cancelled = cancelled_orders
            
            # Pause the strategy
            if request.pause_strategies:
                success = await strategy_manager.pause_strategy(strategy_id, f"Emergency stop: {request.reason.value}")
                result.strategies_paused = 1 if success else 0
                if not success:
                    result.errors.append(f"Failed to pause strategy {strategy_id}")
            
            # Close strategy positions if requested
            if request.close_positions:
                closed_positions = await self._close_strategy_positions(request.user_id, strategy_id)
                result.positions_closed = closed_positions
            
        except Exception as e:
            error_msg = f"Error in strategy emergency stop: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_symbol_emergency_stop(self, request: EmergencyStopRequest, result: EmergencyStopResult):
        """Execute emergency stop for a specific symbol"""
        try:
            if not request.target_id:
                result.errors.append("Symbol required for symbol emergency stop")
                return
            
            symbol = request.target_id
            
            # Cancel orders for this symbol
            if request.cancel_orders:
                cancelled_orders = await self._cancel_symbol_orders(request.user_id, symbol)
                result.orders_cancelled = cancelled_orders
            
            # Pause strategies trading this symbol
            if request.pause_strategies:
                paused_strategies = await self._pause_symbol_strategies(request.user_id, symbol, request.reason.value)
                result.strategies_paused = paused_strategies
            
            # Close positions for this symbol if requested
            if request.close_positions:
                closed_positions = await self._close_symbol_positions(request.user_id, symbol)
                result.positions_closed = closed_positions
            
        except Exception as e:
            error_msg = f"Error in symbol emergency stop: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_system_emergency_stop(self, request: EmergencyStopRequest, result: EmergencyStopResult):
        """Execute system-wide emergency stop"""
        try:
            # This would be implemented for system-wide stops
            # For now, treat as user stop
            await self._execute_user_emergency_stop(request, result)
            
        except Exception as e:
            error_msg = f"Error in system emergency stop: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _cancel_user_orders(self, user_id: str) -> int:
        """Cancel all active orders for a user"""
        try:
            # Dynamic import to avoid circular imports
            from .order_service import order_service
            
            active_orders = await order_service.get_active_orders(user_id)
            cancelled_count = 0
            
            # Cancel orders concurrently for speed
            cancel_tasks = []
            for order in active_orders:
                task = asyncio.create_task(order_service.cancel_order(order['id'], user_id))
                cancel_tasks.append(task)
            
            # Wait for all cancellations
            if cancel_tasks:
                results = await asyncio.gather(*cancel_tasks, return_exceptions=True)
                cancelled_count = sum(1 for result in results if result is True)
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling user orders: {e}")
            return 0
    
    async def _pause_user_strategies(self, user_id: str, reason: str) -> int:
        """Pause all active strategies for a user"""
        try:
            # Dynamic import to avoid circular imports
            from .strategy_manager import strategy_manager
            
            user_strategies = await strategy_manager.get_user_strategies(user_id)
            paused_count = 0
            
            # Pause strategies concurrently
            pause_tasks = []
            for strategy in user_strategies:
                if strategy['status'] == StrategyStatus.ACTIVE.value:
                    task = asyncio.create_task(
                        strategy_manager.pause_strategy(strategy['strategy_id'], f"Emergency stop: {reason}")
                    )
                    pause_tasks.append(task)
            
            # Wait for all pauses
            if pause_tasks:
                results = await asyncio.gather(*pause_tasks, return_exceptions=True)
                paused_count = sum(1 for result in results if result is True)
            
            return paused_count
            
        except Exception as e:
            logger.error(f"Error pausing user strategies: {e}")
            return 0
    
    async def _close_user_positions(self, user_id: str) -> int:
        """Close all open positions for a user"""
        try:
            # Dynamic import to avoid circular imports
            from .position_manager import position_manager
            
            positions = await position_manager.get_user_positions(user_id)
            closed_count = 0
            
            # Close positions concurrently
            close_tasks = []
            for position in positions:
                if not position.get('is_closed', False):
                    task = asyncio.create_task(
                        position_manager.close_position(user_id, position['symbol'])
                    )
                    close_tasks.append(task)
            
            # Wait for all closures
            if close_tasks:
                results = await asyncio.gather(*close_tasks, return_exceptions=True)
                closed_count = sum(1 for result in results if result is True)
            
            return closed_count
            
        except Exception as e:
            logger.error(f"Error closing user positions: {e}")
            return 0
    
    async def _cancel_strategy_orders(self, user_id: str, strategy_id: str) -> int:
        """Cancel orders for a specific strategy"""
        try:
            # Dynamic import to avoid circular imports
            from .order_service import order_service
            
            active_orders = await order_service.get_active_orders(user_id)
            strategy_orders = [
                order for order in active_orders 
                if order.get('strategy_id') == strategy_id
            ]
            
            cancelled_count = 0
            for order in strategy_orders:
                success = await order_service.cancel_order(order['id'], user_id)
                if success:
                    cancelled_count += 1
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling strategy orders: {e}")
            return 0
    
    async def _close_strategy_positions(self, user_id: str, strategy_id: str) -> int:
        """Close positions for a specific strategy"""
        try:
            # Dynamic import to avoid circular imports
            from .strategy_manager import strategy_manager
            from .position_manager import position_manager
            
            # Get strategy configuration to find symbols
            strategy_status = await strategy_manager.get_strategy_status(strategy_id)
            if not strategy_status:
                return 0
            
            symbols = strategy_status.get('symbols', [])
            closed_count = 0
            
            for symbol in symbols:
                success = await position_manager.close_position(user_id, symbol)
                if success:
                    closed_count += 1
            
            return closed_count
            
        except Exception as e:
            logger.error(f"Error closing strategy positions: {e}")
            return 0
    
    async def _cancel_symbol_orders(self, user_id: str, symbol: str) -> int:
        """Cancel orders for a specific symbol"""
        try:
            # Dynamic import to avoid circular imports
            from .order_service import order_service
            
            active_orders = await order_service.get_active_orders(user_id)
            symbol_orders = [
                order for order in active_orders 
                if order.get('symbol') == symbol
            ]
            
            cancelled_count = 0
            for order in symbol_orders:
                success = await order_service.cancel_order(order['id'], user_id)
                if success:
                    cancelled_count += 1
            
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling symbol orders: {e}")
            return 0
    
    async def _pause_symbol_strategies(self, user_id: str, symbol: str, reason: str) -> int:
        """Pause strategies that trade a specific symbol"""
        try:
            # Dynamic import to avoid circular imports
            from .strategy_manager import strategy_manager
            
            user_strategies = await strategy_manager.get_user_strategies(user_id)
            paused_count = 0
            
            for strategy in user_strategies:
                if (strategy['status'] == StrategyStatus.ACTIVE.value and 
                    symbol in strategy.get('symbols', [])):
                    
                    success = await strategy_manager.pause_strategy(
                        strategy['strategy_id'], 
                        f"Emergency stop for {symbol}: {reason}"
                    )
                    if success:
                        paused_count += 1
            
            return paused_count
            
        except Exception as e:
            logger.error(f"Error pausing symbol strategies: {e}")
            return 0
    
    async def _close_symbol_positions(self, user_id: str, symbol: str) -> int:
        """Close positions for a specific symbol"""
        try:
            # Dynamic import to avoid circular imports
            from .position_manager import position_manager
            
            success = await position_manager.close_position(user_id, symbol)
            return 1 if success else 0
            
        except Exception as e:
            logger.error(f"Error closing symbol position: {e}")
            return 0
    
    async def _publish_stop_completion(self, result: EmergencyStopResult):
        """Publish emergency stop completion event"""
        try:
            completion_data = {
                'user_id': result.request.user_id,
                'reason': result.request.reason.value,
                'scope': result.request.scope.value,
                'success': result.success,
                'orders_cancelled': result.orders_cancelled,
                'strategies_paused': result.strategies_paused,
                'positions_closed': result.positions_closed,
                'execution_time_ms': result.execution_time_ms,
                'errors': result.errors,
                'completed_at': result.completed_at.isoformat()
            }
            
            # Publish to event bus
            completion_event = TradingEvent(
                id=f"emergency_stop_complete_{result.request.user_id}_{result.completed_at.timestamp()}",
                event_type=EventType.USER_ACTION,
                user_id=result.request.user_id,
                data=completion_data,
                priority=event_bus.EventPriority.CRITICAL
            )
            
            await event_bus.publish_event(completion_event)
            
        except Exception as e:
            logger.error(f"Error publishing stop completion: {e}")
    
    # Public API methods
    
    async def user_emergency_stop(self, user_id: str, reason: str = "User initiated", 
                                 close_positions: bool = False) -> EmergencyStopResult:
        """
        Execute emergency stop for a user (convenience method)
        
        Args:
            user_id: User ID
            reason: Reason for emergency stop
            close_positions: Whether to close positions
            
        Returns:
            EmergencyStopResult
        """
        request = EmergencyStopRequest(
            user_id=user_id,
            reason=EmergencyStopReason.USER_INITIATED,
            scope=EmergencyStopScope.USER,
            message=reason,
            initiated_by=user_id,
            close_positions=close_positions
        )
        
        return await self.execute_emergency_stop(request)
    
    async def strategy_emergency_stop(self, user_id: str, strategy_id: str, 
                                    reason: str = "Strategy emergency stop") -> EmergencyStopResult:
        """
        Execute emergency stop for a specific strategy
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            reason: Reason for emergency stop
            
        Returns:
            EmergencyStopResult
        """
        request = EmergencyStopRequest(
            user_id=user_id,
            reason=EmergencyStopReason.USER_INITIATED,
            scope=EmergencyStopScope.STRATEGY,
            target_id=strategy_id,
            message=reason,
            initiated_by=user_id
        )
        
        return await self.execute_emergency_stop(request)
    
    async def risk_emergency_stop(self, user_id: str, risk_violation: str) -> EmergencyStopResult:
        """
        Execute emergency stop due to risk violation
        
        Args:
            user_id: User ID
            risk_violation: Description of risk violation
            
        Returns:
            EmergencyStopResult
        """
        request = EmergencyStopRequest(
            user_id=user_id,
            reason=EmergencyStopReason.RISK_VIOLATION,
            scope=EmergencyStopScope.USER,
            message=risk_violation,
            initiated_by="risk_engine",
            close_positions=True  # Close positions on risk violations
        )
        
        return await self.execute_emergency_stop(request)
    
    def get_stop_history(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get emergency stop history
        
        Args:
            user_id: Optional user ID filter
            limit: Maximum number of results
            
        Returns:
            List of emergency stop results
        """
        try:
            history = self.stop_history
            
            if user_id:
                history = [stop for stop in history if stop.request.user_id == user_id]
            
            # Sort by completion time (most recent first)
            history = sorted(history, key=lambda x: x.completed_at, reverse=True)
            
            # Convert to dictionaries
            return [
                {
                    'user_id': stop.request.user_id,
                    'reason': stop.request.reason.value,
                    'scope': stop.request.scope.value,
                    'target_id': stop.request.target_id,
                    'message': stop.request.message,
                    'initiated_by': stop.request.initiated_by,
                    'success': stop.success,
                    'orders_cancelled': stop.orders_cancelled,
                    'strategies_paused': stop.strategies_paused,
                    'positions_closed': stop.positions_closed,
                    'execution_time_ms': stop.execution_time_ms,
                    'errors': stop.errors,
                    'created_at': stop.request.created_at.isoformat(),
                    'completed_at': stop.completed_at.isoformat()
                }
                for stop in history[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Error getting stop history: {e}")
            return []
    
    def get_active_stops(self) -> List[Dict[str, Any]]:
        """Get currently active emergency stops"""
        try:
            return [
                {
                    'stop_id': stop_id,
                    'user_id': result.request.user_id,
                    'reason': result.request.reason.value,
                    'scope': result.request.scope.value,
                    'started_at': result.request.created_at.isoformat()
                }
                for stop_id, result in self.active_stops.items()
            ]
            
        except Exception as e:
            logger.error(f"Error getting active stops: {e}")
            return []

# Global emergency stop system instance
emergency_stop_system = EmergencyStopSystem()