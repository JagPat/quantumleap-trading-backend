"""
Optimized Order Database Adapter
Replaces the existing order_db with optimized database operations
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Import optimized database integration
from ..database.trading_engine_integration import trading_db_integration

# Import trading models
from .models import (
    Order, Position, Execution, StrategyDeployment, TradingSignal,
    OrderStatus, PositionStatus, OrderType, OrderSide
)

logger = logging.getLogger(__name__)

class OptimizedOrderDatabase:
    """
    Optimized database adapter for trading engine operations
    """
    
    def __init__(self):
        self.integration = trading_db_integration
        self._initialized = False
        
        logger.info("OptimizedOrderDatabase initialized")
    
    async def initialize(self):
        """Initialize the optimized database system"""
        if not self._initialized:
            await self.integration.initialize()
            self._initialized = True
            logger.info("OptimizedOrderDatabase system initialized")
    
    async def ensure_initialized(self):
        """Ensure the database system is initialized"""
        if not self._initialized:
            await self.initialize()
    
    # Order Operations
    
    async def create_order(self, order: Order) -> bool:
        """
        Create a new order with optimized database operations
        
        Args:
            order: Order object to create
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.create_order_optimized(order)
    
    async def update_order(self, order: Order) -> bool:
        """
        Update an existing order with optimized database operations
        
        Args:
            order: Order object to update
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.update_order_optimized(order)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID with optimized database operations
        
        Args:
            order_id: Order ID to retrieve
            
        Returns:
            Order object or None if not found
        """
        await self.ensure_initialized()
        return await self.integration.get_order_optimized(order_id)
    
    async def get_orders_by_user(self, user_id: str, status: Optional[OrderStatus] = None,
                               limit: int = 100) -> List[Order]:
        """
        Get orders for a user with optimized database operations
        
        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum number of orders
            
        Returns:
            List of Order objects
        """
        await self.ensure_initialized()
        return await self.integration.get_user_orders_optimized(user_id, status, limit)
    
    async def get_active_orders(self, user_id: Optional[str] = None) -> List[Order]:
        """
        Get active orders with optimized database operations
        
        Args:
            user_id: Optional user filter
            
        Returns:
            List of active Order objects
        """
        await self.ensure_initialized()
        
        active_statuses = [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
        
        if user_id:
            # Get active orders for specific user
            all_orders = []
            for status in active_statuses:
                orders = await self.integration.get_user_orders_optimized(user_id, status, 1000)
                all_orders.extend(orders)
            return all_orders
        else:
            # Get all active orders (this would need a different query in production)
            # For now, we'll return empty list as this requires a more complex query
            logger.warning("Getting all active orders without user filter not implemented")
            return []
    
    async def get_orders_by_symbol(self, symbol: str, user_id: Optional[str] = None,
                                 limit: int = 100) -> List[Order]:
        """
        Get orders by symbol with optimized database operations
        
        Args:
            symbol: Trading symbol
            user_id: Optional user filter
            limit: Maximum number of orders
            
        Returns:
            List of Order objects
        """
        await self.ensure_initialized()
        
        try:
            # Build optimized query for symbol-based lookup
            if user_id:
                query = """
                SELECT * FROM orders 
                WHERE symbol = ? AND user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """
                params = (symbol, user_id, limit)
            else:
                query = """
                SELECT * FROM orders 
                WHERE symbol = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """
                params = (symbol, limit)
            
            # Use the integration's database manager directly for custom queries
            results = await self.integration.db_manager.fetch_all(query, params)
            
            orders = [Order.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(orders)} orders for symbol {symbol}")
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get orders for symbol {symbol}: {e}")
            return []
    
    # Position Operations
    
    async def create_position(self, position: Position) -> bool:
        """
        Create a new position with optimized database operations
        
        Args:
            position: Position object to create
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.create_position_optimized(position)
    
    async def update_position(self, position: Position) -> bool:
        """
        Update an existing position with optimized database operations
        
        Args:
            position: Position object to update
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.update_position_optimized(position)
    
    async def get_position(self, user_id: str, symbol: str, 
                         strategy_id: Optional[str] = None) -> Optional[Position]:
        """
        Get position by user and symbol with optimized database operations
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            strategy_id: Optional strategy ID
            
        Returns:
            Position object or None if not found
        """
        await self.ensure_initialized()
        
        try:
            # Build query based on parameters
            if strategy_id:
                query = """
                SELECT * FROM positions 
                WHERE user_id = ? AND symbol = ? AND strategy_id = ? AND status = 'OPEN'
                """
                params = (user_id, symbol, strategy_id)
            else:
                query = """
                SELECT * FROM positions 
                WHERE user_id = ? AND symbol = ? AND status = 'OPEN'
                """
                params = (user_id, symbol)
            
            result = await self.integration.db_manager.fetch_one(query, params)
            
            if result:
                return Position.from_dict(dict(result))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get position for {user_id}/{symbol}: {e}")
            return None
    
    async def get_positions_by_user(self, user_id: str, 
                                  include_closed: bool = False) -> List[Position]:
        """
        Get positions for a user with optimized database operations
        
        Args:
            user_id: User ID
            include_closed: Whether to include closed positions
            
        Returns:
            List of Position objects
        """
        await self.ensure_initialized()
        return await self.integration.get_user_positions_optimized(user_id, include_closed)
    
    # Execution Operations
    
    async def record_execution(self, execution: Execution) -> bool:
        """
        Record a trade execution with optimized database operations
        
        Args:
            execution: Execution object to record
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.record_execution_optimized(execution)
    
    async def get_executions_by_order(self, order_id: str) -> List[Execution]:
        """
        Get executions for an order with optimized database operations
        
        Args:
            order_id: Order ID
            
        Returns:
            List of Execution objects
        """
        await self.ensure_initialized()
        
        try:
            query = """
            SELECT * FROM executions 
            WHERE order_id = ? 
            ORDER BY executed_at ASC
            """
            
            results = await self.integration.db_manager.fetch_all(query, (order_id,))
            
            executions = [Execution.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(executions)} executions for order {order_id}")
            return executions
            
        except Exception as e:
            logger.error(f"Failed to get executions for order {order_id}: {e}")
            return []
    
    async def get_executions_by_user(self, user_id: str, limit: int = 100) -> List[Execution]:
        """
        Get executions for a user with optimized database operations
        
        Args:
            user_id: User ID
            limit: Maximum number of executions
            
        Returns:
            List of Execution objects
        """
        await self.ensure_initialized()
        
        try:
            query = """
            SELECT * FROM executions 
            WHERE user_id = ? 
            ORDER BY executed_at DESC 
            LIMIT ?
            """
            
            results = await self.integration.db_manager.fetch_all(query, (user_id, limit))
            
            executions = [Execution.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(executions)} executions for user {user_id}")
            return executions
            
        except Exception as e:
            logger.error(f"Failed to get executions for user {user_id}: {e}")
            return []
    
    # Strategy Operations
    
    async def create_strategy_deployment(self, deployment: StrategyDeployment) -> bool:
        """
        Create a strategy deployment with optimized database operations
        
        Args:
            deployment: StrategyDeployment object to create
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        
        try:
            async with self.integration.optimized_transaction() as transaction_id:
                query = """
                INSERT INTO strategy_deployments (
                    id, user_id, strategy_id, status, configuration,
                    risk_parameters, performance_metrics, deployed_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                result = await self.integration.db_manager.execute_query(
                    query,
                    (
                        deployment.id, deployment.user_id, deployment.strategy_id,
                        deployment.status.value, str(deployment.configuration),
                        str(deployment.risk_parameters), str(deployment.performance_metrics),
                        deployment.deployed_at.isoformat(), deployment.updated_at.isoformat()
                    ),
                    transaction_id=transaction_id
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create strategy deployment {deployment.id}: {e}")
            return False
    
    async def update_strategy_deployment(self, deployment: StrategyDeployment) -> bool:
        """
        Update a strategy deployment with optimized database operations
        
        Args:
            deployment: StrategyDeployment object to update
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        
        try:
            async with self.integration.optimized_transaction() as transaction_id:
                query = """
                UPDATE strategy_deployments SET 
                    status = ?, configuration = ?, risk_parameters = ?,
                    performance_metrics = ?, updated_at = ?, paused_at = ?,
                    stopped_at = ?, error_message = ?
                WHERE id = ?
                """
                
                result = await self.integration.db_manager.execute_query(
                    query,
                    (
                        deployment.status.value, str(deployment.configuration),
                        str(deployment.risk_parameters), str(deployment.performance_metrics),
                        deployment.updated_at.isoformat(),
                        deployment.paused_at.isoformat() if deployment.paused_at else None,
                        deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                        deployment.error_message, deployment.id
                    ),
                    transaction_id=transaction_id
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update strategy deployment {deployment.id}: {e}")
            return False
    
    # Signal Operations
    
    async def create_trading_signal(self, signal: TradingSignal) -> bool:
        """
        Create a trading signal with optimized database operations
        
        Args:
            signal: TradingSignal object to create
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        
        try:
            async with self.integration.optimized_transaction() as transaction_id:
                query = """
                INSERT INTO trading_signals (
                    id, user_id, symbol, signal_type, confidence_score, reasoning,
                    target_price, stop_loss, take_profit, position_size, strategy_id,
                    provider_used, is_active, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                result = await self.integration.db_manager.execute_query(
                    query,
                    (
                        signal.id, signal.user_id, signal.symbol, signal.signal_type,
                        signal.confidence_score, signal.reasoning, signal.target_price,
                        signal.stop_loss, signal.take_profit, signal.position_size,
                        signal.strategy_id, signal.provider_used, signal.is_active,
                        signal.expires_at.isoformat() if signal.expires_at else None,
                        signal.created_at.isoformat()
                    ),
                    transaction_id=transaction_id
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create trading signal {signal.id}: {e}")
            return False
    
    async def get_active_signals(self, user_id: str) -> List[TradingSignal]:
        """
        Get active trading signals for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of active TradingSignal objects
        """
        await self.ensure_initialized()
        
        try:
            query = """
            SELECT * FROM trading_signals 
            WHERE user_id = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            """
            
            results = await self.integration.db_manager.fetch_all(
                query, (user_id, datetime.now().isoformat())
            )
            
            signals = [TradingSignal.from_dict(dict(row)) for row in results]
            
            logger.debug(f"Retrieved {len(signals)} active signals for user {user_id}")
            return signals
            
        except Exception as e:
            logger.error(f"Failed to get active signals for user {user_id}: {e}")
            return []
    
    # Performance and Analytics
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics from the optimized database
        
        Returns:
            Dictionary with performance metrics
        """
        await self.ensure_initialized()
        return await self.integration.get_performance_dashboard_data()
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old data using optimized operations
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        await self.ensure_initialized()
        await self.integration.cleanup_old_data(days_to_keep)
    
    async def create_backup(self, backup_name: Optional[str] = None) -> bool:
        """
        Create a performance-optimized backup
        
        Args:
            backup_name: Optional backup name
            
        Returns:
            True if successful, False otherwise
        """
        await self.ensure_initialized()
        return await self.integration.create_performance_backup(backup_name)
    
    # Health and Monitoring
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get database health status
        
        Returns:
            Dictionary with health information
        """
        await self.ensure_initialized()
        
        try:
            # Get basic health metrics
            health_data = await self.integration.db_monitor.get_health_status()
            
            # Add connection status
            health_data['connection_status'] = 'connected' if self.integration.db_manager else 'disconnected'
            health_data['initialized'] = self._initialized
            
            return health_data
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def shutdown(self):
        """Shutdown the optimized database system"""
        if self._initialized:
            await self.integration.shutdown()
            self._initialized = False
            logger.info("OptimizedOrderDatabase shutdown completed")

# Global optimized database instance
optimized_order_db = OptimizedOrderDatabase()