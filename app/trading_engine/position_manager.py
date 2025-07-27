"""
Position Manager
Manages trading positions and portfolio state
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .models import Position, Execution, OrderSide
from .order_db import order_db
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

class PositionManager:
    """
    Manages trading positions and portfolio state
    """
    
    def __init__(self):
        self.position_cache = {}  # Cache for frequently accessed positions
        self.cache_ttl = 300  # 5 minutes cache TTL
        
        logger.info("PositionManager initialized")
    
    def _get_cache_key(self, user_id: str, symbol: str, strategy_id: Optional[str] = None) -> str:
        """Generate cache key for position"""
        return f"{user_id}:{symbol}:{strategy_id or 'default'}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        return (datetime.now() - cache_entry['timestamp']).total_seconds() < self.cache_ttl
    
    @time_async_operation("get_position")
    async def get_position(self, user_id: str, symbol: str, strategy_id: Optional[str] = None) -> Optional[Position]:
        """
        Get current position for user and symbol
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            strategy_id: Optional strategy ID
            
        Returns:
            Position object or None if no position exists
        """
        try:
            cache_key = self._get_cache_key(user_id, symbol, strategy_id)
            
            # Check cache first
            if cache_key in self.position_cache and self._is_cache_valid(self.position_cache[cache_key]):
                return self.position_cache[cache_key]['position']
            
            # Get from database
            position = order_db.get_position(user_id, symbol, strategy_id)
            
            # Update cache
            if position:
                self.position_cache[cache_key] = {
                    'position': position,
                    'timestamp': datetime.now()
                }
            
            return position
            
        except Exception as e:
            logger.error(f"Error getting position for {user_id}/{symbol}: {e}")
            return None
    
    @time_async_operation("update_position_from_execution")
    async def update_position_from_execution(self, execution: Execution) -> bool:
        """
        Update position based on execution
        
        Args:
            execution: Execution to process
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create position
            position = await self.get_position(execution.user_id, execution.symbol)
            
            if not position:
                # Create new position
                position = Position(
                    id=f"{execution.user_id}_{execution.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    user_id=execution.user_id,
                    symbol=execution.symbol,
                    quantity=0,
                    average_price=0.0
                )
            
            # Update position with execution
            if execution.side == OrderSide.BUY:
                position.add_to_position(execution.quantity, execution.price)
            else:
                position.add_to_position(-execution.quantity, execution.price)
            
            # Save to database
            if position.quantity == 0 and not position.is_closed:
                # Position closed
                position.close_position(execution.price)
            
            success = order_db.update_position(position)
            
            if success:
                # Update cache
                cache_key = self._get_cache_key(execution.user_id, execution.symbol)
                self.position_cache[cache_key] = {
                    'position': position,
                    'timestamp': datetime.now()
                }
                
                # Publish position update event
                await publish_order_event(execution.user_id, EventType.POSITION_UPDATED, {
                    'position': position.to_dict(),
                    'execution': execution.to_dict()
                })
                
                trading_monitor.increment_counter("positions_updated")
                logger.debug(f"Updated position for {execution.symbol}: {position.quantity} shares")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating position from execution {execution.id}: {e}")
            return False
    
    async def get_user_positions(self, user_id: str, include_closed: bool = False) -> List[Dict[str, Any]]:
        """
        Get all positions for a user
        
        Args:
            user_id: User ID
            include_closed: Whether to include closed positions
            
        Returns:
            List of position dictionaries
        """
        try:
            positions = order_db.get_positions_by_user(user_id, include_closed)
            
            # Convert to dictionaries and add calculated fields
            result = []
            for position in positions:
                pos_dict = position.to_dict()
                
                # Add calculated metrics
                pos_dict['market_value'] = position.market_value
                pos_dict['cost_basis'] = position.cost_basis
                pos_dict['unrealized_pnl_percent'] = (position.unrealized_pnl / position.cost_basis * 100) if position.cost_basis > 0 else 0
                pos_dict['is_profitable'] = position.unrealized_pnl > 0
                
                result.append(pos_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions for user {user_id}: {e}")
            return []
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get portfolio summary for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Portfolio summary dictionary
        """
        try:
            positions = await self.get_user_positions(user_id, include_closed=False)
            
            if not positions:
                return {
                    'total_positions': 0,
                    'total_market_value': 0.0,
                    'total_cost_basis': 0.0,
                    'total_unrealized_pnl': 0.0,
                    'total_realized_pnl': 0.0,
                    'portfolio_return_percent': 0.0,
                    'positions_by_symbol': {},
                    'sector_exposure': {},
                    'long_short_breakdown': {'long_value': 0.0, 'short_value': 0.0}
                }
            
            # Calculate totals
            total_market_value = sum(pos['market_value'] for pos in positions)
            total_cost_basis = sum(pos['cost_basis'] for pos in positions)
            total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
            total_realized_pnl = sum(pos['realized_pnl'] for pos in positions)
            
            # Calculate portfolio return
            portfolio_return_percent = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
            
            # Group by symbol
            positions_by_symbol = {}
            for pos in positions:
                symbol = pos['symbol']
                if symbol not in positions_by_symbol:
                    positions_by_symbol[symbol] = []
                positions_by_symbol[symbol].append(pos)
            
            # Calculate long/short breakdown
            long_value = sum(pos['market_value'] for pos in positions if pos['quantity'] > 0)
            short_value = sum(pos['market_value'] for pos in positions if pos['quantity'] < 0)
            
            return {
                'total_positions': len(positions),
                'total_market_value': total_market_value,
                'total_cost_basis': total_cost_basis,
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'portfolio_return_percent': portfolio_return_percent,
                'positions_by_symbol': positions_by_symbol,
                'long_short_breakdown': {
                    'long_value': long_value,
                    'short_value': short_value,
                    'net_exposure': long_value - short_value,
                    'gross_exposure': long_value + short_value
                },
                'top_positions': sorted(positions, key=lambda x: abs(x['market_value']), reverse=True)[:10],
                'profitable_positions': len([pos for pos in positions if pos['unrealized_pnl'] > 0]),
                'losing_positions': len([pos for pos in positions if pos['unrealized_pnl'] < 0])
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio summary for user {user_id}: {e}")
            return {}
    
    async def close_position(self, user_id: str, symbol: str, price: Optional[float] = None) -> bool:
        """
        Close a position at market price
        
        Args:
            user_id: User ID
            symbol: Symbol to close
            price: Optional close price (uses current market price if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            position = await self.get_position(user_id, symbol)
            if not position or position.is_closed:
                logger.warning(f"No open position found for {user_id}/{symbol}")
                return False
            
            # Use provided price or default to average price for simulation
            close_price = price or position.average_price
            
            # Close the position
            position.close_position(close_price)
            
            # Update in database
            success = order_db.update_position(position)
            
            if success:
                # Update cache
                cache_key = self._get_cache_key(user_id, symbol)
                self.position_cache[cache_key] = {
                    'position': position,
                    'timestamp': datetime.now()
                }
                
                # Publish position closed event
                await publish_order_event(user_id, EventType.POSITION_CLOSED, {
                    'position': position.to_dict(),
                    'close_price': close_price
                })
                
                trading_monitor.increment_counter("positions_closed")
                logger.info(f"Closed position for {symbol}: realized P&L = {position.realized_pnl}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error closing position for {user_id}/{symbol}: {e}")
            return False
    
    async def update_market_prices(self, price_updates: Dict[str, float]) -> int:
        """
        Update market prices for positions
        
        Args:
            price_updates: Dictionary of symbol -> price updates
            
        Returns:
            Number of positions updated
        """
        try:
            updated_count = 0
            
            # Get all open positions that need price updates
            for symbol, new_price in price_updates.items():
                # Find positions for this symbol in cache
                positions_to_update = []
                for cache_key, cache_entry in self.position_cache.items():
                    if cache_entry['position'].symbol == symbol and not cache_entry['position'].is_closed:
                        positions_to_update.append(cache_entry['position'])
                
                # Also get from database if not in cache
                # This is a simplified approach - in production, you'd want more efficient bulk updates
                
                for position in positions_to_update:
                    position.update_price(new_price)
                    if order_db.update_position(position):
                        updated_count += 1
                        
                        # Update cache
                        cache_key = self._get_cache_key(position.user_id, position.symbol)
                        self.position_cache[cache_key] = {
                            'position': position,
                            'timestamp': datetime.now()
                        }
            
            if updated_count > 0:
                trading_monitor.increment_counter("position_price_updates", updated_count)
                logger.debug(f"Updated prices for {updated_count} positions")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating market prices: {e}")
            return 0
    
    async def get_position_history(self, user_id: str, symbol: Optional[str] = None, 
                                 days: int = 30) -> List[Dict[str, Any]]:
        """
        Get position history for a user
        
        Args:
            user_id: User ID
            symbol: Optional symbol filter
            days: Number of days to look back
            
        Returns:
            List of historical positions
        """
        try:
            positions = order_db.get_positions_by_user(user_id, include_closed=True)
            
            # Filter by symbol if provided
            if symbol:
                positions = [pos for pos in positions if pos.symbol == symbol]
            
            # Filter by date
            cutoff_date = datetime.now() - timedelta(days=days)
            positions = [pos for pos in positions if pos.opened_at >= cutoff_date]
            
            # Convert to dictionaries with performance metrics
            result = []
            for position in positions:
                pos_dict = position.to_dict()
                
                # Add performance metrics
                if position.is_closed:
                    holding_period = (position.closed_at - position.opened_at).days
                    pos_dict['holding_period_days'] = holding_period
                    pos_dict['annualized_return'] = (position.realized_pnl / position.cost_basis * 365 / holding_period) if holding_period > 0 and position.cost_basis > 0 else 0
                else:
                    pos_dict['holding_period_days'] = (datetime.now() - position.opened_at).days
                    pos_dict['annualized_return'] = None
                
                pos_dict['total_return'] = position.realized_pnl + position.unrealized_pnl
                pos_dict['total_return_percent'] = (pos_dict['total_return'] / position.cost_basis * 100) if position.cost_basis > 0 else 0
                
                result.append(pos_dict)
            
            # Sort by opened date (most recent first)
            result.sort(key=lambda x: x['opened_at'], reverse=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting position history for user {user_id}: {e}")
            return []
    
    def clear_cache(self, user_id: Optional[str] = None, symbol: Optional[str] = None):
        """
        Clear position cache
        
        Args:
            user_id: Optional user filter
            symbol: Optional symbol filter
        """
        try:
            if user_id is None and symbol is None:
                # Clear all cache
                self.position_cache.clear()
                logger.debug("Cleared all position cache")
            else:
                # Clear specific entries
                keys_to_remove = []
                for cache_key in self.position_cache.keys():
                    parts = cache_key.split(':')
                    cache_user_id, cache_symbol = parts[0], parts[1]
                    
                    if (user_id is None or cache_user_id == user_id) and \
                       (symbol is None or cache_symbol == symbol):
                        keys_to_remove.append(cache_key)
                
                for key in keys_to_remove:
                    del self.position_cache[key]
                
                logger.debug(f"Cleared {len(keys_to_remove)} position cache entries")
                
        except Exception as e:
            logger.error(f"Error clearing position cache: {e}")

# Global position manager instance
position_manager = PositionManager()