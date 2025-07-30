"""
Order Executor
Core component responsible for executing trading orders based on AI signals
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .models import Order, OrderType, OrderSide, OrderStatus, TradingSignal, Execution
# Note: order_service import removed to avoid circular import
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation, log_order_placement
# from app.broker.kite_service import kite_service  # Commented out for now
from app.database.service import get_user_credentials

logger = logging.getLogger(__name__)

class OrderExecutionResult:
    """Result of order execution attempt"""
    
    def __init__(self, success: bool, order: Optional[Order] = None, 
                 error: Optional[str] = None, broker_order_id: Optional[str] = None):
        self.success = success
        self.order = order
        self.error = error
        self.broker_order_id = broker_order_id
        self.timestamp = datetime.now()

class OrderExecutor:
    """
    Core order execution engine that processes AI signals and places orders
    """
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.order_timeout = 300  # 5 minutes
        
        # Register event handlers
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """Register event handlers for order processing"""
        from .event_bus import EventHandler
        
        class SignalHandler(EventHandler):
            def __init__(self, executor):
                super().__init__("signal_handler", [EventType.SIGNAL_GENERATED])
                self.executor = executor
            
            async def handle_event(self, event):
                try:
                    signal_data = event.data
                    await self.executor.process_signal_event(event.user_id, signal_data)
                    return True
                except Exception as e:
                    logger.error(f"Error handling signal event: {e}")
                    return False
        
        # Register the signal handler
        signal_handler = SignalHandler(self)
        event_bus.register_handler(signal_handler)
    
    @time_async_operation("process_signal")
    async def process_signal(self, signal: TradingSignal) -> OrderExecutionResult:
        """
        Process a trading signal and create an order
        
        Args:
            signal: TradingSignal object containing trade information
            
        Returns:
            OrderExecutionResult with execution details
        """
        try:
            logger.info(f"Processing signal {signal.id} for {signal.symbol}")
            
            # Validate signal
            if not self._validate_signal(signal):
                return OrderExecutionResult(
                    success=False,
                    error="Signal validation failed"
                )
            
            # Check if signal has expired
            if signal.is_expired():
                logger.warning(f"Signal {signal.id} has expired")
                return OrderExecutionResult(
                    success=False,
                    error="Signal has expired"
                )
            
            # Convert signal to order
            order = await self._signal_to_order(signal)
            if not order:
                return OrderExecutionResult(
                    success=False,
                    error="Failed to convert signal to order"
                )
            
            # Validate order before execution
            validation_result = await self._validate_order(order)
            if not validation_result["valid"]:
                return OrderExecutionResult(
                    success=False,
                    error=f"Order validation failed: {validation_result['error']}"
                )
            
            # Create order in database
            if not order_service.create_order(order):
                return OrderExecutionResult(
                    success=False,
                    error="Failed to create order in database"
                )
            
            # Publish order created event
            await publish_order_event(
                order.user_id,
                EventType.ORDER_CREATED,
                order.to_dict()
            )
            
            # Execute the order
            execution_result = await self._execute_order(order)
            
            # Update order status based on execution result
            if execution_result.success:
                order.status = OrderStatus.SUBMITTED
                order.broker_order_id = execution_result.broker_order_id
                order.submitted_at = datetime.now()
                
                # Publish order submitted event
                await publish_order_event(
                    order.user_id,
                    EventType.ORDER_SUBMITTED,
                    order.to_dict()
                )
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = execution_result.error
                
                # Publish order rejected event
                await publish_order_event(
                    order.user_id,
                    EventType.ORDER_REJECTED,
                    order.to_dict()
                )
            
            # Update order in database
            order_service.update_order(order)
            
            # Log order placement
            log_order_placement(
                order.user_id,
                order.id,
                order.symbol,
                order.order_type.value
            )
            
            return OrderExecutionResult(
                success=execution_result.success,
                order=order,
                error=execution_result.error,
                broker_order_id=execution_result.broker_order_id
            )
            
        except Exception as e:
            logger.error(f"Error processing signal {signal.id}: {e}")
            trading_monitor.create_alert(
                "ERROR",
                "Signal Processing Failed",
                f"Failed to process signal {signal.id}: {str(e)}",
                "order_executor",
                signal.user_id
            )
            return OrderExecutionResult(
                success=False,
                error=f"Signal processing error: {str(e)}"
            )
    
    async def process_signal_event(self, user_id: str, signal_data: Dict[str, Any]):
        """Process signal from event bus"""
        try:
            signal = TradingSignal.from_dict(signal_data)
            result = await self.process_signal(signal)
            
            if not result.success:
                logger.warning(f"Failed to process signal event: {result.error}")
                
        except Exception as e:
            logger.error(f"Error processing signal event: {e}")
    
    @time_async_operation("place_order")
    async def place_order(self, order: Order) -> OrderExecutionResult:
        """
        Place an order directly (not from signal)
        
        Args:
            order: Order object to place
            
        Returns:
            OrderExecutionResult with execution details
        """
        try:
            logger.info(f"Placing order {order.id} for {order.symbol}")
            
            # Validate order
            validation_result = await self._validate_order(order)
            if not validation_result["valid"]:
                return OrderExecutionResult(
                    success=False,
                    error=f"Order validation failed: {validation_result['error']}"
                )
            
            # Create order in database
            if not order_service.create_order(order):
                return OrderExecutionResult(
                    success=False,
                    error="Failed to create order in database"
                )
            
            # Execute the order
            execution_result = await self._execute_order(order)
            
            # Update order status
            if execution_result.success:
                order.status = OrderStatus.SUBMITTED
                order.broker_order_id = execution_result.broker_order_id
                order.submitted_at = datetime.now()
            else:
                order.status = OrderStatus.REJECTED
                order.error_message = execution_result.error
            
            # Update order in database
            order_service.update_order(order)
            
            return OrderExecutionResult(
                success=execution_result.success,
                order=order,
                error=execution_result.error,
                broker_order_id=execution_result.broker_order_id
            )
            
        except Exception as e:
            logger.error(f"Error placing order {order.id}: {e}")
            return OrderExecutionResult(
                success=False,
                error=f"Order placement error: {str(e)}"
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an active order
        
        Args:
            order_id: ID of the order to cancel
            
        Returns:
            True if cancellation was successful
        """
        try:
            order = order_service.get_order(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found for cancellation")
                return False
            
            if not order.is_active():
                logger.warning(f"Order {order_id} is not active, cannot cancel")
                return False
            
            # Cancel with broker if it was submitted
            if order.broker_order_id and order.status == OrderStatus.SUBMITTED:
                broker_success = await self._cancel_broker_order(order)
                if not broker_success:
                    logger.warning(f"Failed to cancel order {order_id} with broker")
            
            # Update order status
            success = order_service.cancel_order(order_id, "User cancelled")
            
            if success:
                # Publish order cancelled event
                await publish_order_event(
                    order.user_id,
                    EventType.ORDER_CANCELLED,
                    order.to_dict()
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderExecutionResult:
        """
        Modify an existing order
        
        Args:
            order_id: ID of the order to modify
            modifications: Dictionary of fields to modify
            
        Returns:
            OrderExecutionResult with modification details
        """
        try:
            order = order_service.get_order(order_id)
            if not order:
                return OrderExecutionResult(
                    success=False,
                    error="Order not found"
                )
            
            if not order.is_active():
                return OrderExecutionResult(
                    success=False,
                    error="Order is not active, cannot modify"
                )
            
            # Apply modifications
            if "quantity" in modifications:
                order.quantity = modifications["quantity"]
            if "price" in modifications:
                order.price = modifications["price"]
            if "stop_price" in modifications:
                order.stop_price = modifications["stop_price"]
            
            # Validate modified order
            validation_result = await self._validate_order(order)
            if not validation_result["valid"]:
                return OrderExecutionResult(
                    success=False,
                    error=f"Modified order validation failed: {validation_result['error']}"
                )
            
            # If order was submitted to broker, modify it there too
            if order.broker_order_id and order.status == OrderStatus.SUBMITTED:
                broker_success = await self._modify_broker_order(order, modifications)
                if not broker_success:
                    return OrderExecutionResult(
                        success=False,
                        error="Failed to modify order with broker"
                    )
            
            # Update order in database
            order.updated_at = datetime.now()
            success = order_service.update_order(order)
            
            return OrderExecutionResult(
                success=success,
                order=order,
                error=None if success else "Failed to update order in database"
            )
            
        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            return OrderExecutionResult(
                success=False,
                error=f"Order modification error: {str(e)}"
            )
    
    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of an order
        
        Args:
            order_id: ID of the order
            
        Returns:
            Dictionary with order status information
        """
        try:
            order = order_service.get_order(order_id)
            if not order:
                return None
            
            # Get executions for the order
            executions = order_service.get_order_executions(order_id)
            
            return {
                "order": order.to_dict(),
                "executions": [exec.to_dict() for exec in executions],
                "is_active": order.is_active(),
                "remaining_quantity": order.remaining_quantity()
            }
            
        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            return None
    
    def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate trading signal"""
        try:
            # Check required fields
            if not signal.user_id or not signal.symbol or not signal.signal_type:
                return False
            
            # Check confidence score
            if signal.confidence_score < 0 or signal.confidence_score > 1:
                return False
            
            # Check signal type
            if signal.signal_type not in ["BUY", "SELL", "HOLD"]:
                return False
            
            # Skip HOLD signals
            if signal.signal_type == "HOLD":
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False
    
    async def _signal_to_order(self, signal: TradingSignal) -> Optional[Order]:
        """Convert trading signal to order"""
        try:
            # Determine order side
            side = OrderSide.BUY if signal.signal_type == "BUY" else OrderSide.SELL
            
            # Calculate quantity based on position size
            # This is a simplified calculation - in production would consider portfolio value
            quantity = max(1, int(signal.position_size * 100))  # Simplified quantity calculation
            
            # Determine order type and price
            order_type = OrderType.MARKET  # Default to market orders for now
            price = signal.target_price if signal.target_price else None
            
            # Create order
            order = Order(
                user_id=signal.user_id,
                symbol=signal.symbol,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=price,
                stop_price=signal.stop_loss,
                strategy_id=signal.strategy_id,
                signal_id=signal.id,
                status=OrderStatus.PENDING
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error converting signal to order: {e}")
            return None
    
    async def _validate_order(self, order: Order) -> Dict[str, Any]:
        """Validate order before execution"""
        try:
            # Basic validation
            if not order.user_id or not order.symbol or order.quantity <= 0:
                return {"valid": False, "error": "Invalid order parameters"}
            
            # Check if user has valid credentials
            credentials = get_user_credentials(order.user_id)
            if not credentials:
                return {"valid": False, "error": "User credentials not found"}
            
            # Validate order type and price
            if order.order_type == OrderType.LIMIT and not order.price:
                return {"valid": False, "error": "Limit order requires price"}
            
            if order.order_type == OrderType.STOP_LOSS and not order.stop_price:
                return {"valid": False, "error": "Stop loss order requires stop price"}
            
            # Additional validations can be added here (risk checks, etc.)
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}
    
    async def _execute_order(self, order: Order) -> OrderExecutionResult:
        """Execute order with broker"""
        try:
            # Get user credentials
            credentials = get_user_credentials(order.user_id)
            if not credentials:
                return OrderExecutionResult(
                    success=False,
                    error="User credentials not found"
                )
            
            # Create Kite client
            kite = kite_service.create_kite_client(
                credentials['api_key'],
                credentials['access_token'],
                credentials.get('api_secret', '')
            )
            
            # Prepare order parameters for Kite
            kite_params = {
                "exchange": "NSE",  # Default to NSE
                "tradingsymbol": order.symbol,
                "transaction_type": "BUY" if order.side == OrderSide.BUY else "SELL",
                "quantity": order.quantity,
                "product": "MIS",  # Intraday for now
                "order_type": self._get_kite_order_type(order.order_type),
                "validity": "DAY"
            }
            
            # Add price for limit orders
            if order.order_type == OrderType.LIMIT and order.price:
                kite_params["price"] = order.price
            
            # Add trigger price for stop orders
            if order.order_type == OrderType.STOP_LOSS and order.stop_price:
                kite_params["trigger_price"] = order.stop_price
            
            # Place order with Kite
            try:
                broker_response = kite.place_order(**kite_params)
                broker_order_id = broker_response.get("order_id")
                
                if broker_order_id:
                    logger.info(f"Order {order.id} placed with broker, ID: {broker_order_id}")
                    return OrderExecutionResult(
                        success=True,
                        broker_order_id=broker_order_id
                    )
                else:
                    return OrderExecutionResult(
                        success=False,
                        error="No order ID returned from broker"
                    )
                    
            except Exception as broker_error:
                logger.error(f"Broker error placing order {order.id}: {broker_error}")
                return OrderExecutionResult(
                    success=False,
                    error=f"Broker error: {str(broker_error)}"
                )
            
        except Exception as e:
            logger.error(f"Error executing order {order.id}: {e}")
            return OrderExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}"
            )
    
    async def _cancel_broker_order(self, order: Order) -> bool:
        """Cancel order with broker"""
        try:
            credentials = get_user_credentials(order.user_id)
            if not credentials:
                return False
            
            kite = kite_service.create_kite_client(
                credentials['api_key'],
                credentials['access_token'],
                credentials.get('api_secret', '')
            )
            
            # Cancel order with Kite
            kite.cancel_order(
                variety="regular",
                order_id=order.broker_order_id
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling broker order {order.broker_order_id}: {e}")
            return False
    
    async def _modify_broker_order(self, order: Order, modifications: Dict[str, Any]) -> bool:
        """Modify order with broker"""
        try:
            credentials = get_user_credentials(order.user_id)
            if not credentials:
                return False
            
            kite = kite_service.create_kite_client(
                credentials['api_key'],
                credentials['access_token'],
                credentials.get('api_secret', '')
            )
            
            # Prepare modification parameters
            modify_params = {
                "variety": "regular",
                "order_id": order.broker_order_id
            }
            
            if "quantity" in modifications:
                modify_params["quantity"] = modifications["quantity"]
            if "price" in modifications:
                modify_params["price"] = modifications["price"]
            if "trigger_price" in modifications:
                modify_params["trigger_price"] = modifications["trigger_price"]
            
            # Modify order with Kite
            kite.modify_order(**modify_params)
            
            return True
            
        except Exception as e:
            logger.error(f"Error modifying broker order {order.broker_order_id}: {e}")
            return False
    
    def _get_kite_order_type(self, order_type: OrderType) -> str:
        """Convert internal order type to Kite order type"""
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP_LOSS: "SL",
            OrderType.STOP_LIMIT: "SL-M"
        }
        return mapping.get(order_type, "MARKET")

# Global executor instance
order_executor = OrderExecutor()
