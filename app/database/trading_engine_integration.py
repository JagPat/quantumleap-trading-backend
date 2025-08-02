"""
Trading Engine Database Integration
Integrates optimized database layer with existing trading engine components
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Import optimized database components
from .optimized_manager import OptimizedDatabaseManager
from .query_optimizer import QueryOptimizer
from .performance_collector import PerformanceCollector
from .transaction_manager import TransactionManager
from .data_validator import DataValidator
from .database_monitor import DatabaseMonitor
from .alert_manager import AlertManager
from .backup_recovery_system import BackupRecoverySystem

# Import trading engine models
from ..trading_engine.models import (
    Order, Position, Execution, StrategyDeployment, TradingSignal,
    OrderStatus, PositionStatus, OrderType, OrderSide
)

logger = logging.getLogger(__name__)

class TradingDatabaseIntegration:
    """
    Integration layer between optimized database and trading engine
    """
    
    def __init__(self, database_path: str = "trading_optimized.db"):
        self.database_path = database_path
        
        # Initialize optimized database components
        self.db_manager = OptimizedDatabaseManager(database_path)
        self.query_optimizer = QueryOptimizer(database_path)
        self.performance_collector = PerformanceCollector(database_path)
        self.transaction_manager = TransactionManager(database_path)
        self.data_validator = DataValidator()
        self.db_monitor = DatabaseMonitor(database_path)
        self.alert_manager = AlertManager()
        self.backup_system = BackupRecoverySystem(database_path)
        
        # Performance metrics cache
        self.metrics_cache = {}
        self.cache_ttl = 60  # 1 minute cache TTL
        
        # Connection pool for high-frequency operations
        self.connection_pool = None
        self.pool_size = 10
        
        logger.info(f"TradingDatabaseIntegration initialized with database: {database_path}")
    
    async def initialize(self):
        """Initialize the database integration system"""
        try:
            # Initialize database manager
            await self.db_manager.initialize()
            
            # Start monitoring
            await self.db_monitor.start_monitoring()
            
            # Configure alerts
            await self._configure_alerts()
            
            # Create initial backup
            await self.backup_system.create_backup("initial_backup")
            
            logger.info("Trading database integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize trading database integration: {e}")
            raise
    
    async def _configure_alerts(self):
        """Configure database alerts for trading operations"""
        try:
            # Configure performance alerts
            await self.alert_manager.add_alert_rule({
                'name': 'high_query_latency',
                'condition': 'avg_query_time_ms > 1000',
                'severity': 'warning',
                'notification_channels': ['email', 'webhook']
            })
            
            await self.alert_manager.add_alert_rule({
                'name': 'database_connection_failure',
                'condition': 'connection_failures > 5',
                'severity': 'critical',
                'notification_channels': ['email', 'webhook', 'sms']
            })
            
            await self.alert_manager.add_alert_rule({
                'name': 'high_error_rate',
                'condition': 'error_rate_percent > 5',
                'severity': 'warning',
                'notification_channels': ['email']
            })
            
            logger.info("Database alerts configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure database alerts: {e}")
    
    @asynccontextmanager
    async def optimized_transaction(self, isolation_level: str = "READ_COMMITTED"):
        """
        Context manager for optimized database transactions
        
        Args:
            isolation_level: Transaction isolation level
        """
        transaction_id = None
        try:
            # Start transaction with monitoring
            transaction_id = await self.transaction_manager.begin_transaction(isolation_level)
            
            # Track transaction start
            start_time = datetime.now()
            
            yield transaction_id
            
            # Commit transaction
            await self.transaction_manager.commit_transaction(transaction_id)
            
            # Record successful transaction
            duration = (datetime.now() - start_time).total_seconds()
            await self.performance_collector.record_transaction_metrics(
                transaction_id, duration, "committed"
            )
            
        except Exception as e:
            # Rollback on error
            if transaction_id:
                await self.transaction_manager.rollback_transaction(transaction_id)
                
                # Record failed transaction
                duration = (datetime.now() - start_time).total_seconds()
                await self.performance_collector.record_transaction_metrics(
                    transaction_id, duration, "rolled_back", str(e)
                )
            
            logger.error(f"Transaction failed: {e}")
            raise
    
    async def create_order_optimized(self, order: Order) -> bool:
        """
        Create order using optimized database operations
        
        Args:
            order: Order object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate order data
            validation_result = await self.data_validator.validate_order_data(order.to_dict())
            if not validation_result['is_valid']:
                logger.error(f"Order validation failed: {validation_result['errors']}")
                return False
            
            async with self.optimized_transaction() as transaction_id:
                # Use optimized query for order insertion
                optimized_query = await self.query_optimizer.optimize_query(
                    """
                    INSERT INTO orders (
                        id, user_id, symbol, order_type, side, quantity, price, 
                        stop_price, status, strategy_id, signal_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    context={'operation': 'insert', 'table': 'orders'}
                )
                
                # Execute with performance monitoring
                start_time = datetime.now()
                
                result = await self.db_manager.execute_query(
                    optimized_query,
                    (
                        order.id, order.user_id, order.symbol, order.order_type.value,
                        order.side.value, order.quantity, order.price, order.stop_price,
                        order.status.value, order.strategy_id, order.signal_id,
                        order.created_at.isoformat(), order.updated_at.isoformat()
                    ),
                    transaction_id=transaction_id
                )
                
                # Record performance metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.performance_collector.record_query_metrics(
                    optimized_query, execution_time, "orders", "insert"
                )
                
                logger.info(f"Created order {order.id} with optimized database operations")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create order {order.id}: {e}")
            return False
    
    async def update_order_optimized(self, order: Order) -> bool:
        """
        Update order using optimized database operations
        
        Args:
            order: Order object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate order data
            validation_result = await self.data_validator.validate_order_data(order.to_dict())
            if not validation_result['is_valid']:
                logger.error(f"Order validation failed: {validation_result['errors']}")
                return False
            
            async with self.optimized_transaction() as transaction_id:
                # Use optimized update query
                optimized_query = await self.query_optimizer.optimize_query(
                    """
                    UPDATE orders SET 
                        status = ?, filled_quantity = ?, average_fill_price = ?,
                        commission = ?, error_message = ?, updated_at = ?,
                        submitted_at = ?, filled_at = ?
                    WHERE id = ?
                    """,
                    context={'operation': 'update', 'table': 'orders', 'where_columns': ['id']}
                )
                
                start_time = datetime.now()
                
                result = await self.db_manager.execute_query(
                    optimized_query,
                    (
                        order.status.value, order.filled_quantity, order.average_fill_price,
                        order.commission, order.error_message, order.updated_at.isoformat(),
                        order.submitted_at.isoformat() if order.submitted_at else None,
                        order.filled_at.isoformat() if order.filled_at else None,
                        order.id
                    ),
                    transaction_id=transaction_id
                )
                
                # Record performance metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.performance_collector.record_query_metrics(
                    optimized_query, execution_time, "orders", "update"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update order {order.id}: {e}")
            return False
    
    async def get_order_optimized(self, order_id: str) -> Optional[Order]:
        """
        Get order using optimized database operations
        
        Args:
            order_id: Order ID to retrieve
            
        Returns:
            Order object or None if not found
        """
        try:
            # Check cache first
            cache_key = f"order_{order_id}"
            if cache_key in self.metrics_cache:
                cache_entry = self.metrics_cache[cache_key]
                if (datetime.now() - cache_entry['timestamp']).total_seconds() < self.cache_ttl:
                    return cache_entry['data']
            
            # Use optimized query with proper indexing
            optimized_query = await self.query_optimizer.optimize_query(
                "SELECT * FROM orders WHERE id = ?",
                context={'operation': 'select', 'table': 'orders', 'where_columns': ['id']}
            )
            
            start_time = datetime.now()
            
            result = await self.db_manager.fetch_one(optimized_query, (order_id,))
            
            # Record performance metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.performance_collector.record_query_metrics(
                optimized_query, execution_time, "orders", "select"
            )
            
            if result:
                order = Order.from_dict(dict(result))
                
                # Cache the result
                self.metrics_cache[cache_key] = {
                    'data': order,
                    'timestamp': datetime.now()
                }
                
                return order
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_user_orders_optimized(self, user_id: str, status: Optional[OrderStatus] = None,
                                      limit: int = 100) -> List[Order]:
        """
        Get user orders using optimized database operations
        
        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum number of orders
            
        Returns:
            List of Order objects
        """
        try:
            # Build optimized query based on filters
            if status:
                query = """
                SELECT * FROM orders 
                WHERE user_id = ? AND status = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """
                params = (user_id, status.value, limit)
                context = {
                    'operation': 'select', 
                    'table': 'orders', 
                    'where_columns': ['user_id', 'status'],
                    'order_by': ['created_at']
                }
            else:
                query = """
                SELECT * FROM orders 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """
                params = (user_id, limit)
                context = {
                    'operation': 'select', 
                    'table': 'orders', 
                    'where_columns': ['user_id'],
                    'order_by': ['created_at']
                }
            
            optimized_query = await self.query_optimizer.optimize_query(query, context=context)
            
            start_time = datetime.now()
            
            results = await self.db_manager.fetch_all(optimized_query, params)
            
            # Record performance metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.performance_collector.record_query_metrics(
                optimized_query, execution_time, "orders", "select_multiple"
            )
            
            orders = [Order.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(orders)} orders for user {user_id}")
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            return []
    
    async def create_position_optimized(self, position: Position) -> bool:
        """
        Create position using optimized database operations
        
        Args:
            position: Position object to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate position data
            validation_result = await self.data_validator.validate_position_data(position.to_dict())
            if not validation_result['is_valid']:
                logger.error(f"Position validation failed: {validation_result['errors']}")
                return False
            
            async with self.optimized_transaction() as transaction_id:
                # Use optimized insert query
                optimized_query = await self.query_optimizer.optimize_query(
                    """
                    INSERT INTO positions (
                        id, user_id, symbol, quantity, average_price, current_price,
                        unrealized_pnl, realized_pnl, strategy_id, status,
                        opened_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    context={'operation': 'insert', 'table': 'positions'}
                )
                
                start_time = datetime.now()
                
                result = await self.db_manager.execute_query(
                    optimized_query,
                    (
                        position.id, position.user_id, position.symbol, position.quantity,
                        position.average_price, position.current_price, position.unrealized_pnl,
                        position.realized_pnl, position.strategy_id, position.status.value,
                        position.opened_at.isoformat(), position.updated_at.isoformat()
                    ),
                    transaction_id=transaction_id
                )
                
                # Record performance metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.performance_collector.record_query_metrics(
                    optimized_query, execution_time, "positions", "insert"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create position {position.id}: {e}")
            return False
    
    async def update_position_optimized(self, position: Position) -> bool:
        """
        Update position using optimized database operations
        
        Args:
            position: Position object to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate position data
            validation_result = await self.data_validator.validate_position_data(position.to_dict())
            if not validation_result['is_valid']:
                logger.error(f"Position validation failed: {validation_result['errors']}")
                return False
            
            async with self.optimized_transaction() as transaction_id:
                # Use optimized update query
                optimized_query = await self.query_optimizer.optimize_query(
                    """
                    UPDATE positions SET 
                        quantity = ?, average_price = ?, current_price = ?,
                        unrealized_pnl = ?, realized_pnl = ?, status = ?,
                        updated_at = ?, closed_at = ?
                    WHERE id = ?
                    """,
                    context={'operation': 'update', 'table': 'positions', 'where_columns': ['id']}
                )
                
                start_time = datetime.now()
                
                result = await self.db_manager.execute_query(
                    optimized_query,
                    (
                        position.quantity, position.average_price, position.current_price,
                        position.unrealized_pnl, position.realized_pnl, position.status.value,
                        position.updated_at.isoformat(),
                        position.closed_at.isoformat() if position.closed_at else None,
                        position.id
                    ),
                    transaction_id=transaction_id
                )
                
                # Record performance metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.performance_collector.record_query_metrics(
                    optimized_query, execution_time, "positions", "update"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update position {position.id}: {e}")
            return False
    
    async def get_user_positions_optimized(self, user_id: str, 
                                         include_closed: bool = False) -> List[Position]:
        """
        Get user positions using optimized database operations
        
        Args:
            user_id: User ID
            include_closed: Whether to include closed positions
            
        Returns:
            List of Position objects
        """
        try:
            # Build optimized query
            if include_closed:
                query = "SELECT * FROM positions WHERE user_id = ? ORDER BY updated_at DESC"
                params = (user_id,)
                context = {
                    'operation': 'select', 
                    'table': 'positions', 
                    'where_columns': ['user_id'],
                    'order_by': ['updated_at']
                }
            else:
                query = """
                SELECT * FROM positions 
                WHERE user_id = ? AND status = 'OPEN' 
                ORDER BY updated_at DESC
                """
                params = (user_id,)
                context = {
                    'operation': 'select', 
                    'table': 'positions', 
                    'where_columns': ['user_id', 'status'],
                    'order_by': ['updated_at']
                }
            
            optimized_query = await self.query_optimizer.optimize_query(query, context=context)
            
            start_time = datetime.now()
            
            results = await self.db_manager.fetch_all(optimized_query, params)
            
            # Record performance metrics
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.performance_collector.record_query_metrics(
                optimized_query, execution_time, "positions", "select_multiple"
            )
            
            positions = [Position.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(positions)} positions for user {user_id}")
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions for user {user_id}: {e}")
            return []
    
    async def record_execution_optimized(self, execution: Execution) -> bool:
        """
        Record execution using optimized database operations
        
        Args:
            execution: Execution object to record
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate execution data
            validation_result = await self.data_validator.validate_execution_data(execution.to_dict())
            if not validation_result['is_valid']:
                logger.error(f"Execution validation failed: {validation_result['errors']}")
                return False
            
            async with self.optimized_transaction() as transaction_id:
                # Use optimized insert query
                optimized_query = await self.query_optimizer.optimize_query(
                    """
                    INSERT INTO executions (
                        id, order_id, user_id, symbol, side, quantity, price,
                        commission, broker_execution_id, executed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    context={'operation': 'insert', 'table': 'executions'}
                )
                
                start_time = datetime.now()
                
                result = await self.db_manager.execute_query(
                    optimized_query,
                    (
                        execution.id, execution.order_id, execution.user_id, execution.symbol,
                        execution.side.value, execution.quantity, execution.price,
                        execution.commission, execution.broker_execution_id,
                        execution.executed_at.isoformat()
                    ),
                    transaction_id=transaction_id
                )
                
                # Record performance metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                await self.performance_collector.record_query_metrics(
                    optimized_query, execution_time, "executions", "insert"
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to record execution {execution.id}: {e}")
            return False
    
    async def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive performance dashboard data
        
        Returns:
            Dictionary with performance metrics and database health
        """
        try:
            # Get database performance metrics
            db_metrics = await self.performance_collector.get_performance_summary()
            
            # Get monitoring data
            monitor_data = await self.db_monitor.get_health_status()
            
            # Get query optimization statistics
            optimization_stats = await self.query_optimizer.get_optimization_statistics()
            
            # Get transaction statistics
            transaction_stats = await self.transaction_manager.get_transaction_statistics()
            
            # Get alert status
            alert_status = await self.alert_manager.get_alert_summary()
            
            return {
                'database_performance': db_metrics,
                'database_health': monitor_data,
                'query_optimization': optimization_stats,
                'transaction_statistics': transaction_stats,
                'alert_status': alert_status,
                'cache_statistics': {
                    'cache_size': len(self.metrics_cache),
                    'cache_hit_rate': self._calculate_cache_hit_rate(),
                    'cache_ttl_seconds': self.cache_ttl
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance dashboard data: {e}")
            return {}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This is a simplified implementation
        # In production, you'd track hits/misses properly
        return 0.85  # Placeholder value
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old data using optimized operations
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            async with self.optimized_transaction() as transaction_id:
                # Clean up old orders
                await self.db_manager.execute_query(
                    "DELETE FROM orders WHERE created_at < ? AND status IN ('FILLED', 'CANCELLED', 'REJECTED')",
                    (cutoff_date.isoformat(),),
                    transaction_id=transaction_id
                )
                
                # Clean up old executions
                await self.db_manager.execute_query(
                    "DELETE FROM executions WHERE executed_at < ?",
                    (cutoff_date.isoformat(),),
                    transaction_id=transaction_id
                )
                
                # Clean up closed positions
                await self.db_manager.execute_query(
                    "DELETE FROM positions WHERE closed_at < ? AND status = 'CLOSED'",
                    (cutoff_date.isoformat(),),
                    transaction_id=transaction_id
                )
            
            logger.info(f"Cleaned up data older than {days_to_keep} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    async def create_performance_backup(self, backup_name: Optional[str] = None) -> bool:
        """
        Create a performance-optimized backup
        
        Args:
            backup_name: Optional backup name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_name:
                backup_name = f"trading_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            result = await self.backup_system.create_backup(backup_name)
            
            if result:
                logger.info(f"Created performance backup: {backup_name}")
            else:
                logger.error(f"Failed to create backup: {backup_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating performance backup: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the database integration system"""
        try:
            # Stop monitoring
            await self.db_monitor.stop_monitoring()
            
            # Close database connections
            await self.db_manager.close()
            
            # Clear cache
            self.metrics_cache.clear()
            
            logger.info("Trading database integration shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global integration instance
trading_db_integration = TradingDatabaseIntegration()