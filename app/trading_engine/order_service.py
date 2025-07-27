"""
Order Service
High-level service for managing trading orders and coordinating with execution engine
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from .models import Order, OrderStatus, OrderResult, TradingSignal, OrderType
from .order_executor import order_executor
from .order_db import order_db
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

class OrderService:
    """
    High-level service for order management and coordination
    """
    
    def __init__(self):
        self.retry_attempts = {}  # Track retry attempts per order
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds
        self.retry_backoff_multiplier = 2.0  # Exponential backoff
        
        # Start background retry processor
        self._retry_task = None
        self._start_retry_processor()
        
        logger.info("OrderService initialized with retry processor")
    
    def _start_retry_processor(self):
        """Start background task for processing order retries"""
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._process_retries())
    
    async def _process_retries(self):
        """Background task to process order retries with exponential backoff"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Get failed orders that need retry
                failed_orders = order_db.get_active_orders()
                failed_orders = [o for o in failed_orders if o.status == OrderStatus.ERROR]
                
                for order in failed_orders:
                    if order.id not in self.retry_attempts:
                        self.retry_attempts[order.id] = {
                            'count': 0,
                            'last_attempt': None,
                            'next_attempt': datetime.now()
                        }
                    
                    retry_info = self.retry_attempts[order.id]
                    
                    # Check if it's time for next retry
                    if (retry_info['count'] < self.max_retries and 
                        datetime.now() >= retry_info['next_attempt']):
                        
                        await self._retry_order(order)
                
            except Exception as e:
                logger.error(f"Error in retry processor: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _retry_order(self, order: Order):
        """
        Retry a failed order with exponential backoff
        
        Args:
            order: Order to retry
        """
        try:
            retry_info = self.retry_attempts[order.id]
            retry_info['count'] += 1
            retry_info['last_attempt'] = datetime.now()
            
            logger.info(f"Retrying order {order.id} (attempt {retry_info['count']}/{self.max_retries})")
            
            # Reset order status for retry
            order.update_status(OrderStatus.PENDING)
            order.error_message = None
            order_db.update_order(order)
            
            # Attempt to place order again
            execution_result = await order_executor.place_order(order)
            
            if execution_result.success:
                # Success - remove from retry tracking
                del self.retry_attempts[order.id]
                trading_monitor.increment_counter("order_retries_success")
                logger.info(f"Order {order.id} retry successful")
            else:
                # Failed - schedule next retry with exponential backoff
                delay = self.retry_delay * (self.retry_backoff_multiplier ** (retry_info['count'] - 1))
                retry_info['next_attempt'] = datetime.now() + timedelta(seconds=delay)
                
                if retry_info['count'] >= self.max_retries:
                    # Max retries reached - mark as permanently failed
                    order.update_status(OrderStatus.REJECTED, f"Max retries ({self.max_retries}) exceeded")
                    order_db.update_order(order)
                    del self.retry_attempts[order.id]
                    
                    # Publish permanent failure event
                    await publish_order_event(order.user_id, EventType.ORDER_REJECTED, {
                        'order': order.to_dict(),
                        'error': 'Max retries exceeded',
                        'retry_count': retry_info['count']
                    })
                    
                    trading_monitor.increment_counter("order_retries_exhausted")
                    logger.error(f"Order {order.id} permanently failed after {retry_info['count']} retries")
                else:
                    trading_monitor.increment_counter("order_retries_failed")
                    logger.warning(f"Order {order.id} retry {retry_info['count']} failed, next attempt in {delay}s")
                
        except Exception as e:
            logger.error(f"Error retrying order {order.id}: {e}")
    
    @time_async_operation("create_order_from_signal")
    async def create_order_from_signal(self, signal: TradingSignal) -> OrderResult:
        """
        Create and execute order from trading signal
        
        Args:
            signal: TradingSignal to process
            
        Returns:
            OrderResult with execution details
        """
        try:
            logger.info(f"Creating order from signal {signal.id}")
            
            # Use order executor to process signal
            result = await order_executor.process_signal(signal)
            
            if result.success:
                trading_monitor.increment_counter("orders_created_success")
                logger.info(f"Successfully created order from signal {signal.id}")
            else:
                trading_monitor.increment_counter("orders_created_failed")
                logger.error(f"Failed to create order from signal {signal.id}: {result.error_message}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error creating order from signal {signal.id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("order_creation_errors")
            return OrderResult(success=False, error_message=error_msg, error_code="SERVICE_ERROR")
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order details by ID with real-time status updates
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details or None if not found
        """
        try:
            order_status = await order_executor.get_order_status(order_id)
            
            if order_status:
                # Add retry information if available
                if order_id in self.retry_attempts:
                    order_status['retry_info'] = self.retry_attempts[order_id].copy()
                    # Convert datetime to string for JSON serialization
                    if order_status['retry_info']['last_attempt']:
                        order_status['retry_info']['last_attempt'] = order_status['retry_info']['last_attempt'].isoformat()
                    if order_status['retry_info']['next_attempt']:
                        order_status['retry_info']['next_attempt'] = order_status['retry_info']['next_attempt'].isoformat()
            
            return order_status
            
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
    
    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        """
        Cancel an order with proper authorization and cleanup
        
        Args:
            order_id: Order ID to cancel
            user_id: User ID for authorization
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify order belongs to user
            order = order_db.get_order(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            if order.user_id != user_id:
                logger.error(f"User {user_id} not authorized to cancel order {order_id}")
                return False
            
            # Remove from retry tracking if present
            if order_id in self.retry_attempts:
                del self.retry_attempts[order_id]
                logger.debug(f"Removed order {order_id} from retry tracking")
            
            result = await order_executor.cancel_order(order_id)
            
            if result:
                trading_monitor.increment_counter("orders_cancelled_success")
                logger.info(f"Successfully cancelled order {order_id}")
            else:
                trading_monitor.increment_counter("orders_cancelled_failed")
                logger.error(f"Failed to cancel order {order_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            trading_monitor.increment_counter("order_cancellation_errors")
            return False
    
    async def modify_order(self, order_id: str, user_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify an existing order with validation
        
        Args:
            order_id: Order ID to modify
            user_id: User ID for authorization
            modifications: Dictionary of fields to modify
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify order belongs to user
            order = order_db.get_order(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            if order.user_id != user_id:
                logger.error(f"User {user_id} not authorized to modify order {order_id}")
                return False
            
            # Validate modifications
            valid_fields = ['price', 'quantity', 'stop_price']
            invalid_fields = [field for field in modifications.keys() if field not in valid_fields]
            if invalid_fields:
                logger.error(f"Invalid modification fields: {invalid_fields}")
                return False
            
            # Validate values
            if 'quantity' in modifications and modifications['quantity'] <= 0:
                logger.error("Order quantity must be positive")
                return False
            
            if 'price' in modifications and modifications['price'] <= 0:
                logger.error("Order price must be positive")
                return False
            
            if 'stop_price' in modifications and modifications['stop_price'] <= 0:
                logger.error("Stop price must be positive")
                return False
            
            result = await order_executor.modify_order(order_id, modifications)
            
            if result:
                # Publish order modified event
                await publish_order_event(user_id, EventType.ORDER_UPDATED, {
                    'order_id': order_id,
                    'modifications': modifications
                })
                
                trading_monitor.increment_counter("orders_modified_success")
                logger.info(f"Successfully modified order {order_id}")
            else:
                trading_monitor.increment_counter("orders_modified_failed")
                logger.error(f"Failed to modify order {order_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            trading_monitor.increment_counter("order_modification_errors")
            return False
    
    async def get_user_orders(self, user_id: str, status: Optional[OrderStatus] = None,
                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get orders for a user with enhanced details
        
        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum number of orders
            
        Returns:
            List of order details with retry information
        """
        try:
            orders = await order_executor.get_user_orders(user_id, status, limit)
            
            # Add retry information to orders
            for order in orders:
                order_id = order['id']
                if order_id in self.retry_attempts:
                    retry_info = self.retry_attempts[order_id].copy()
                    # Convert datetime to string for JSON serialization
                    if retry_info['last_attempt']:
                        retry_info['last_attempt'] = retry_info['last_attempt'].isoformat()
                    if retry_info['next_attempt']:
                        retry_info['next_attempt'] = retry_info['next_attempt'].isoformat()
                    order['retry_info'] = retry_info
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []
    
    async def get_active_orders(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active orders with real-time status tracking
        
        Args:
            user_id: Optional user filter
            
        Returns:
            List of active orders with enhanced status information
        """
        try:
            orders = await order_executor.get_active_orders(user_id)
            
            # Add retry information and enhanced status
            for order in orders:
                order_id = order['id']
                if order_id in self.retry_attempts:
                    retry_info = self.retry_attempts[order_id].copy()
                    # Convert datetime to string
                    if retry_info['last_attempt']:
                        retry_info['last_attempt'] = retry_info['last_attempt'].isoformat()
                    if retry_info['next_attempt']:
                        retry_info['next_attempt'] = retry_info['next_attempt'].isoformat()
                    order['retry_info'] = retry_info
                    
                    # Add time until next retry
                    if retry_info['next_attempt']:
                        next_attempt = datetime.fromisoformat(retry_info['next_attempt'])
                        time_to_retry = (next_attempt - datetime.now()).total_seconds()
                        order['time_to_retry_seconds'] = max(0, time_to_retry)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting active orders: {e}")
            return []
    
    async def get_order_history(self, user_id: str, symbol: Optional[str] = None,
                              days: int = 30) -> List[Dict[str, Any]]:
        """
        Get order history with performance metrics
        
        Args:
            user_id: User ID
            symbol: Optional symbol filter
            days: Number of days to look back
            
        Returns:
            List of historical orders with performance data
        """
        try:
            orders = await order_executor.get_order_history(user_id, symbol, days)
            
            # Add performance metrics
            for order in orders:
                if order['status'] == OrderStatus.FILLED.value:
                    # Calculate order performance metrics
                    fill_time = None
                    if order['filled_at'] and order['submitted_at']:
                        submitted = datetime.fromisoformat(order['submitted_at'])
                        filled = datetime.fromisoformat(order['filled_at'])
                        fill_time = (filled - submitted).total_seconds()
                    
                    order['performance_metrics'] = {
                        'fill_time_seconds': fill_time,
                        'fill_percentage': order.get('filled_quantity', 0) / order.get('quantity', 1),
                        'average_fill_price': order.get('average_fill_price'),
                        'total_commission': order.get('commission', 0)
                    }
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting order history for user {user_id}: {e}")
            return []
    
    async def get_execution_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get execution history with enhanced details
        
        Args:
            user_id: User ID
            limit: Maximum number of executions
            
        Returns:
            List of executions with performance metrics
        """
        try:
            executions = await order_executor.get_execution_history(user_id, limit)
            
            # Add performance metrics to executions
            for execution in executions:
                execution['performance_metrics'] = {
                    'total_value': execution['quantity'] * execution['price'],
                    'net_value': (execution['quantity'] * execution['price']) - execution.get('commission', 0),
                    'commission_rate': execution.get('commission', 0) / (execution['quantity'] * execution['price']) if execution['quantity'] * execution['price'] > 0 else 0
                }
            
            return executions
            
        except Exception as e:
            logger.error(f"Error getting execution history for user {user_id}: {e}")
            return []
    
    async def get_trading_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive trading statistics
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Enhanced trading statistics with retry metrics
        """
        try:
            base_stats = await order_executor.get_statistics(user_id, days)
            
            # Add retry statistics
            user_retry_stats = {
                'active_retries': len([r for r in self.retry_attempts.values() if r['count'] > 0]),
                'total_retry_attempts': sum(r['count'] for r in self.retry_attempts.values()),
                'orders_in_retry': len(self.retry_attempts)
            }
            
            # Add order success rates
            orders = await self.get_user_orders(user_id, limit=1000)
            recent_orders = [
                o for o in orders 
                if datetime.fromisoformat(o['created_at']) >= datetime.now() - timedelta(days=days)
            ]
            
            if recent_orders:
                success_rate = len([o for o in recent_orders if o['status'] in [OrderStatus.FILLED.value, OrderStatus.PARTIALLY_FILLED.value]]) / len(recent_orders)
                cancellation_rate = len([o for o in recent_orders if o['status'] == OrderStatus.CANCELLED.value]) / len(recent_orders)
                rejection_rate = len([o for o in recent_orders if o['status'] in [OrderStatus.REJECTED.value, OrderStatus.ERROR.value]]) / len(recent_orders)
            else:
                success_rate = cancellation_rate = rejection_rate = 0.0
            
            base_stats['retry_statistics'] = user_retry_stats
            base_stats['success_rates'] = {
                'order_success_rate': success_rate,
                'order_cancellation_rate': cancellation_rate,
                'order_rejection_rate': rejection_rate
            }
            
            return base_stats
            
        except Exception as e:
            logger.error(f"Error getting statistics for user {user_id}: {e}")
            return {}
    
    async def get_retry_status(self) -> Dict[str, Any]:
        """
        Get current retry processor status
        
        Returns:
            Dictionary with retry processor information
        """
        try:
            return {
                'retry_processor_active': self._retry_task and not self._retry_task.done(),
                'orders_in_retry': len(self.retry_attempts),
                'retry_attempts_by_order': {
                    order_id: {
                        'count': info['count'],
                        'last_attempt': info['last_attempt'].isoformat() if info['last_attempt'] else None,
                        'next_attempt': info['next_attempt'].isoformat() if info['next_attempt'] else None
                    }
                    for order_id, info in self.retry_attempts.items()
                },
                'max_retries': self.max_retries,
                'retry_delay': self.retry_delay,
                'backoff_multiplier': self.retry_backoff_multiplier
            }
            
        except Exception as e:
            logger.error(f"Error getting retry status: {e}")
            return {}
    
    def stop(self):
        """Stop the order service and retry processor"""
        if self._retry_task and not self._retry_task.done():
            self._retry_task.cancel()
        logger.info("OrderService stopped")
    
    def start(self):
        """Start the order service and retry processor"""
        self._start_retry_processor()
        logger.info("OrderService started")

# Global order service instance
order_service = OrderService()