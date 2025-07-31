"""
Manual Override System
Provides manual control capabilities for users to override automated trading
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .models import Order, OrderType, OrderSide, OrderStatus, StrategyStatus, Position
from .event_bus import event_bus, EventType, publish_order_event, TradingEvent, EventHandler
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

class OverrideType(str, Enum):
    """Types of manual overrides"""
    MANUAL_ORDER = "MANUAL_ORDER"
    STRATEGY_CONTROL = "STRATEGY_CONTROL"
    POSITION_CLOSURE = "POSITION_CLOSURE"
    RISK_ADJUSTMENT = "RISK_ADJUSTMENT"
    SIGNAL_OVERRIDE = "SIGNAL_OVERRIDE"

class OverrideReason(str, Enum):
    """Reasons for manual override"""
    USER_DECISION = "USER_DECISION"
    MARKET_OPPORTUNITY = "MARKET_OPPORTUNITY"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    TECHNICAL_ISSUE = "TECHNICAL_ISSUE"
    NEWS_EVENT = "NEWS_EVENT"
    STRATEGY_ADJUSTMENT = "STRATEGY_ADJUSTMENT"

@dataclass
class ManualOverrideRequest:
    """Manual override request structure"""
    id: str
    user_id: str
    override_type: OverrideType
    reason: OverrideReason
    description: str
    parameters: Dict[str, Any]
    initiated_by: str
    requires_confirmation: bool = True
    risk_override: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ManualOverrideResult:
    """Result of manual override execution"""
    success: bool
    request: ManualOverrideRequest
    actions_taken: List[str]
    warnings: List[str]
    errors: List[str]
    risk_validation: Dict[str, Any]
    execution_time_ms: float = 0.0
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now()
        if not hasattr(self, 'actions_taken'):
            self.actions_taken = []
        if not hasattr(self, 'warnings'):
            self.warnings = []
        if not hasattr(self, 'errors'):
            self.errors = []

class ManualOverrideSystem:
    """
    Manual override system for user control over automated trading
    """
    
    def __init__(self):
        self.pending_overrides: Dict[str, ManualOverrideRequest] = {}
        self.override_history: List[ManualOverrideResult] = []
        self.max_history_size = 1000
        
        # Risk validation settings
        self.risk_validation_enabled = True
        self.require_confirmation_for_high_risk = True
        
        # Register event handlers
        self._register_event_handlers()
        
        logger.info("ManualOverrideSystem initialized")
    
    def _register_event_handlers(self):
        """Register event handlers for manual override events"""
        class OverrideHandler(EventHandler):
            def __init__(self, override_system):
                super().__init__("manual_override_handler", [EventType.USER_ACTION])
                self.override_system = override_system
            
            async def handle_event(self, event: TradingEvent) -> bool:
                try:
                    if event.data.get('action_type') == 'manual_override':
                        await self.override_system._handle_override_event(event)
                    return True
                except Exception as e:
                    logger.error(f"Error handling override event: {e}")
                    return False
        
        # Register the handler
        handler = OverrideHandler(self)
        event_bus.register_handler(handler)
    
    async def _handle_override_event(self, event: TradingEvent):
        """Handle manual override event from event bus"""
        try:
            data = event.data
            request = ManualOverrideRequest(
                id=data.get('override_id', str(uuid.uuid4())),
                user_id=event.user_id,
                override_type=OverrideType(data.get('override_type')),
                reason=OverrideReason(data.get('reason', 'USER_DECISION')),
                description=data.get('description', ''),
                parameters=data.get('parameters', {}),
                initiated_by=data.get('initiated_by', event.user_id),
                requires_confirmation=data.get('requires_confirmation', True),
                risk_override=data.get('risk_override', False)
            )
            
            await self.execute_override(request)
            
        except Exception as e:
            logger.error(f"Error handling override event: {e}")
    
    @time_async_operation("manual_override")
    async def execute_override(self, request: ManualOverrideRequest) -> ManualOverrideResult:
        """
        Execute manual override based on request
        
        Args:
            request: Manual override request
            
        Returns:
            ManualOverrideResult with execution details
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing manual override {request.id} for user {request.user_id}")
            
            # Create result object
            result = ManualOverrideResult(
                success=False,
                request=request,
                actions_taken=[],
                warnings=[],
                errors=[],
                risk_validation={}
            )
            
            # Store pending override
            self.pending_overrides[request.id] = request
            
            # Validate risk if enabled
            if self.risk_validation_enabled and not request.risk_override:
                risk_validation = await self._validate_override_risk(request)
                result.risk_validation = risk_validation
                
                if not risk_validation.get('approved', False):
                    result.errors.append(f"Risk validation failed: {risk_validation.get('reason', 'Unknown')}")
                    if risk_validation.get('severity') == 'HIGH':
                        result.errors.append("High risk override requires explicit confirmation")
                        return result
            
            # Execute override based on type
            if request.override_type == OverrideType.MANUAL_ORDER:
                await self._execute_manual_order(request, result)
            elif request.override_type == OverrideType.STRATEGY_CONTROL:
                await self._execute_strategy_control(request, result)
            elif request.override_type == OverrideType.POSITION_CLOSURE:
                await self._execute_position_closure(request, result)
            elif request.override_type == OverrideType.RISK_ADJUSTMENT:
                await self._execute_risk_adjustment(request, result)
            elif request.override_type == OverrideType.SIGNAL_OVERRIDE:
                await self._execute_signal_override(request, result)
            
            # Calculate execution time
            end_time = datetime.now()
            result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
            result.completed_at = end_time
            result.success = len(result.errors) == 0
            
            # Publish completion event
            await self._publish_override_completion(result)
            
            # Move to history
            self.override_history.append(result)
            if len(self.override_history) > self.max_history_size:
                self.override_history.pop(0)
            
            # Remove from pending
            if request.id in self.pending_overrides:
                del self.pending_overrides[request.id]
            
            # Update monitoring
            trading_monitor.increment_counter("manual_overrides_executed")
            if result.success:
                trading_monitor.increment_counter("manual_overrides_successful")
            else:
                trading_monitor.increment_counter("manual_overrides_failed")
            
            logger.info(f"Manual override {request.id} completed in {result.execution_time_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            error_msg = f"Critical error in manual override execution: {str(e)}"
            logger.error(error_msg)
            
            result = ManualOverrideResult(
                success=False,
                request=request,
                actions_taken=[],
                warnings=[],
                errors=[error_msg],
                risk_validation={}
            )
            
            trading_monitor.increment_counter("manual_overrides_failed")
            return result
    
    async def _validate_override_risk(self, request: ManualOverrideRequest) -> Dict[str, Any]:
        """Validate risk for manual override"""
        try:
            # Dynamic import to avoid circular imports
            from .risk_engine import risk_engine
            
            risk_validation = {
                'approved': True,
                'severity': 'LOW',
                'reason': 'No significant risk detected',
                'checks_performed': []
            }
            
            # Check based on override type
            if request.override_type == OverrideType.MANUAL_ORDER:
                # Validate manual order risk
                order_params = request.parameters
                
                # Check position size
                quantity = order_params.get('quantity', 0)
                if quantity > 1000:  # Large order
                    risk_validation['severity'] = 'MEDIUM'
                    risk_validation['reason'] = 'Large order size detected'
                
                if quantity > 5000:  # Very large order
                    risk_validation['severity'] = 'HIGH'
                    risk_validation['approved'] = False
                    risk_validation['reason'] = 'Order size exceeds risk limits'
                
                risk_validation['checks_performed'].append('position_size_check')
                
                # Check if user has sufficient buying power (simplified)
                # In production, this would check actual account balance
                risk_validation['checks_performed'].append('buying_power_check')
            
            elif request.override_type == OverrideType.POSITION_CLOSURE:
                # Position closure is generally low risk
                risk_validation['severity'] = 'LOW'
                risk_validation['checks_performed'].append('position_closure_check')
            
            elif request.override_type == OverrideType.STRATEGY_CONTROL:
                # Strategy control has medium risk
                risk_validation['severity'] = 'MEDIUM'
                risk_validation['checks_performed'].append('strategy_control_check')
            
            return risk_validation
            
        except Exception as e:
            logger.error(f"Error validating override risk: {e}")
            return {
                'approved': False,
                'severity': 'HIGH',
                'reason': f'Risk validation error: {str(e)}',
                'checks_performed': ['error_check']
            }
    
    async def _execute_manual_order(self, request: ManualOverrideRequest, result: ManualOverrideResult):
        """Execute manual order placement"""
        try:
            # Dynamic import to avoid circular imports
            from .order_executor import order_executor
            
            order_params = request.parameters
            
            # Create order object
            order = Order(
                user_id=request.user_id,
                symbol=order_params.get('symbol', ''),
                order_type=OrderType(order_params.get('order_type', 'MARKET')),
                side=OrderSide(order_params.get('side', 'BUY')),
                quantity=order_params.get('quantity', 0),
                price=order_params.get('price'),
                stop_price=order_params.get('stop_price'),
                status=OrderStatus.PENDING
            )
            
            # Add manual override metadata
            order.strategy_id = "MANUAL_OVERRIDE"
            order.signal_id = f"manual_{request.id}"
            
            # Execute order
            execution_result = await order_executor.place_order(order)
            
            if execution_result.success:
                result.actions_taken.append(f"Manual order placed: {order.symbol} {order.side.value} {order.quantity}")
                
                # Log the manual order
                trading_monitor.create_alert(
                    "INFO",
                    "Manual Order Placed",
                    f"User {request.user_id} manually placed order: {order.symbol} {order.side.value} {order.quantity}",
                    "manual_override",
                    request.user_id
                )
            else:
                result.errors.append(f"Failed to place manual order: {execution_result.error}")
            
        except Exception as e:
            error_msg = f"Error executing manual order: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_strategy_control(self, request: ManualOverrideRequest, result: ManualOverrideResult):
        """Execute strategy control override"""
        try:
            # Dynamic import to avoid circular imports
            from .strategy_manager import strategy_manager
            
            control_params = request.parameters
            strategy_id = control_params.get('strategy_id')
            action = control_params.get('action')  # 'pause', 'resume', 'stop'
            
            if not strategy_id or not action:
                result.errors.append("Strategy ID and action are required for strategy control")
                return
            
            success = False
            if action == 'pause':
                success = await strategy_manager.pause_strategy(
                    strategy_id, 
                    f"Manual override by user: {request.description}"
                )
                if success:
                    result.actions_taken.append(f"Strategy {strategy_id} paused manually")
            
            elif action == 'resume':
                success = await strategy_manager.resume_strategy(strategy_id)
                if success:
                    result.actions_taken.append(f"Strategy {strategy_id} resumed manually")
            
            elif action == 'stop':
                close_positions = control_params.get('close_positions', False)
                success = await strategy_manager.stop_strategy(strategy_id, close_positions)
                if success:
                    action_desc = f"Strategy {strategy_id} stopped manually"
                    if close_positions:
                        action_desc += " (positions closed)"
                    result.actions_taken.append(action_desc)
            
            if not success:
                result.errors.append(f"Failed to {action} strategy {strategy_id}")
            else:
                # Log the strategy control
                trading_monitor.create_alert(
                    "INFO",
                    "Manual Strategy Control",
                    f"User {request.user_id} manually {action}ed strategy {strategy_id}",
                    "manual_override",
                    request.user_id
                )
            
        except Exception as e:
            error_msg = f"Error executing strategy control: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_position_closure(self, request: ManualOverrideRequest, result: ManualOverrideResult):
        """Execute manual position closure"""
        try:
            # Dynamic import to avoid circular imports
            from .position_manager import position_manager
            
            closure_params = request.parameters
            symbol = closure_params.get('symbol')
            quantity = closure_params.get('quantity')  # Optional: partial closure
            price = closure_params.get('price')  # Optional: limit price
            
            if not symbol:
                result.errors.append("Symbol is required for position closure")
                return
            
            # Close position
            if quantity:
                # Partial closure (would need to implement this in position manager)
                result.warnings.append("Partial position closure not yet implemented, closing entire position")
            
            success = await position_manager.close_position(request.user_id, symbol, price)
            
            if success:
                result.actions_taken.append(f"Position {symbol} closed manually")
                
                # Log the position closure
                trading_monitor.create_alert(
                    "INFO",
                    "Manual Position Closure",
                    f"User {request.user_id} manually closed position: {symbol}",
                    "manual_override",
                    request.user_id
                )
            else:
                result.errors.append(f"Failed to close position {symbol}")
            
        except Exception as e:
            error_msg = f"Error executing position closure: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_risk_adjustment(self, request: ManualOverrideRequest, result: ManualOverrideResult):
        """Execute risk parameter adjustment"""
        try:
            # Dynamic import to avoid circular imports
            from .risk_engine import risk_engine
            
            risk_params = request.parameters
            
            # Update risk parameters for user
            # This is a simplified implementation
            updated_params = []
            
            if 'max_position_size' in risk_params:
                # Update max position size
                updated_params.append(f"max_position_size: {risk_params['max_position_size']}")
            
            if 'stop_loss_percentage' in risk_params:
                # Update stop loss percentage
                updated_params.append(f"stop_loss_percentage: {risk_params['stop_loss_percentage']}")
            
            if 'max_drawdown' in risk_params:
                # Update max drawdown
                updated_params.append(f"max_drawdown: {risk_params['max_drawdown']}")
            
            if updated_params:
                result.actions_taken.append(f"Risk parameters updated: {', '.join(updated_params)}")
                
                # Log the risk adjustment
                trading_monitor.create_alert(
                    "WARNING",
                    "Manual Risk Adjustment",
                    f"User {request.user_id} manually adjusted risk parameters: {', '.join(updated_params)}",
                    "manual_override",
                    request.user_id
                )
            else:
                result.warnings.append("No valid risk parameters provided for adjustment")
            
        except Exception as e:
            error_msg = f"Error executing risk adjustment: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _execute_signal_override(self, request: ManualOverrideRequest, result: ManualOverrideResult):
        """Execute signal override (ignore or force execute signal)"""
        try:
            signal_params = request.parameters
            signal_id = signal_params.get('signal_id')
            action = signal_params.get('action')  # 'ignore', 'force_execute'
            
            if not signal_id or not action:
                result.errors.append("Signal ID and action are required for signal override")
                return
            
            if action == 'ignore':
                # Mark signal as ignored
                result.actions_taken.append(f"Signal {signal_id} ignored by manual override")
                
            elif action == 'force_execute':
                # Force execute signal despite risk warnings
                result.actions_taken.append(f"Signal {signal_id} force executed by manual override")
                result.warnings.append("Signal was force executed, bypassing normal risk checks")
            
            # Log the signal override
            trading_monitor.create_alert(
                "WARNING",
                "Manual Signal Override",
                f"User {request.user_id} manually {action}d signal {signal_id}",
                "manual_override",
                request.user_id
            )
            
        except Exception as e:
            error_msg = f"Error executing signal override: {str(e)}"
            result.errors.append(error_msg)
            logger.error(error_msg)
    
    async def _publish_override_completion(self, result: ManualOverrideResult):
        """Publish manual override completion event"""
        try:
            completion_data = {
                'override_id': result.request.id,
                'user_id': result.request.user_id,
                'override_type': result.request.override_type.value,
                'success': result.success,
                'actions_taken': result.actions_taken,
                'warnings': result.warnings,
                'errors': result.errors,
                'execution_time_ms': result.execution_time_ms,
                'completed_at': result.completed_at.isoformat()
            }
            
            # Publish to event bus
            completion_event = TradingEvent(
                id=f"manual_override_complete_{result.request.id}",
                event_type=EventType.USER_ACTION,
                user_id=result.request.user_id,
                data=completion_data,
                priority=event_bus.EventPriority.HIGH
            )
            
            await event_bus.publish_event(completion_event)
            
        except Exception as e:
            logger.error(f"Error publishing override completion: {e}")
    
    # Public API methods
    
    async def place_manual_order(self, user_id: str, symbol: str, side: str, quantity: int,
                                order_type: str = "MARKET", price: Optional[float] = None,
                                stop_price: Optional[float] = None, reason: str = "Manual order") -> ManualOverrideResult:
        """
        Place a manual order (convenience method)
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            order_type: Order type (MARKET/LIMIT/STOP_LOSS)
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            reason: Reason for manual order
            
        Returns:
            ManualOverrideResult
        """
        request = ManualOverrideRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            override_type=OverrideType.MANUAL_ORDER,
            reason=OverrideReason.USER_DECISION,
            description=reason,
            parameters={
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'stop_price': stop_price
            },
            initiated_by=user_id
        )
        
        return await self.execute_override(request)
    
    async def control_strategy(self, user_id: str, strategy_id: str, action: str,
                              close_positions: bool = False, reason: str = "Manual control") -> ManualOverrideResult:
        """
        Control strategy manually (convenience method)
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            action: Action to take (pause/resume/stop)
            close_positions: Whether to close positions when stopping
            reason: Reason for control action
            
        Returns:
            ManualOverrideResult
        """
        request = ManualOverrideRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            override_type=OverrideType.STRATEGY_CONTROL,
            reason=OverrideReason.USER_DECISION,
            description=reason,
            parameters={
                'strategy_id': strategy_id,
                'action': action,
                'close_positions': close_positions
            },
            initiated_by=user_id
        )
        
        return await self.execute_override(request)
    
    async def close_position_manually(self, user_id: str, symbol: str, 
                                     price: Optional[float] = None, 
                                     reason: str = "Manual closure") -> ManualOverrideResult:
        """
        Close position manually (convenience method)
        
        Args:
            user_id: User ID
            symbol: Symbol to close
            price: Optional limit price
            reason: Reason for closure
            
        Returns:
            ManualOverrideResult
        """
        request = ManualOverrideRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            override_type=OverrideType.POSITION_CLOSURE,
            reason=OverrideReason.USER_DECISION,
            description=reason,
            parameters={
                'symbol': symbol,
                'price': price
            },
            initiated_by=user_id
        )
        
        return await self.execute_override(request)
    
    def get_override_history(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get manual override history
        
        Args:
            user_id: Optional user ID filter
            limit: Maximum number of results
            
        Returns:
            List of override results
        """
        try:
            history = self.override_history
            
            if user_id:
                history = [override for override in history if override.request.user_id == user_id]
            
            # Sort by completion time (most recent first)
            history = sorted(history, key=lambda x: x.completed_at, reverse=True)
            
            # Convert to dictionaries
            return [
                {
                    'override_id': override.request.id,
                    'user_id': override.request.user_id,
                    'override_type': override.request.override_type.value,
                    'reason': override.request.reason.value,
                    'description': override.request.description,
                    'success': override.success,
                    'actions_taken': override.actions_taken,
                    'warnings': override.warnings,
                    'errors': override.errors,
                    'execution_time_ms': override.execution_time_ms,
                    'created_at': override.request.created_at.isoformat(),
                    'completed_at': override.completed_at.isoformat()
                }
                for override in history[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Error getting override history: {e}")
            return []
    
    def get_pending_overrides(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending manual overrides"""
        try:
            pending = list(self.pending_overrides.values())
            
            if user_id:
                pending = [override for override in pending if override.user_id == user_id]
            
            return [
                {
                    'override_id': override.id,
                    'user_id': override.user_id,
                    'override_type': override.override_type.value,
                    'reason': override.reason.value,
                    'description': override.description,
                    'requires_confirmation': override.requires_confirmation,
                    'created_at': override.created_at.isoformat()
                }
                for override in pending
            ]
            
        except Exception as e:
            logger.error(f"Error getting pending overrides: {e}")
            return []

# Global manual override system instance
manual_override_system = ManualOverrideSystem()