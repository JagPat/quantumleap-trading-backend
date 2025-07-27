"""
Strategy Manager
Manages deployment, monitoring, and control of trading strategies
"""
import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from .models import StrategyStatus, RiskParameters
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation
from .risk_engine import risk_engine
from .position_manager import position_manager
from .order_service import order_service

logger = logging.getLogger(__name__)

class StrategyType(str, Enum):
    """Strategy types"""
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    ARBITRAGE = "ARBITRAGE"
    PAIRS_TRADING = "PAIRS_TRADING"
    MARKET_MAKING = "MARKET_MAKING"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    CUSTOM = "CUSTOM"

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    id: str
    name: str
    description: str
    strategy_type: StrategyType
    user_id: str
    symbols: List[str]
    parameters: Dict[str, Any]
    risk_parameters: RiskParameters
    max_positions: int = 10
    max_daily_trades: int = 50
    enabled_hours: Dict[str, Any] = None  # Trading hours configuration
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.enabled_hours is None:
            self.enabled_hours = {
                'start_time': '09:15',
                'end_time': '15:30',
                'timezone': 'Asia/Kolkata',
                'trading_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            }

@dataclass
class StrategyInstance:
    """Running strategy instance"""
    config: StrategyConfig
    status: StrategyStatus
    deployed_at: Optional[datetime] = None
    last_signal_at: Optional[datetime] = None
    total_signals: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    current_positions: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'total_return': 0.0
            }

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_id: str
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    avg_trade_duration: float
    best_trade: float
    worst_trade: float
    volatility: float
    calculated_at: datetime

class StrategyManager:
    """
    Manages trading strategy deployment, monitoring, and control
    """
    
    def __init__(self):
        self.deployed_strategies = {}  # strategy_id -> StrategyInstance
        self.strategy_configs = {}  # strategy_id -> StrategyConfig
        self.performance_cache = {}  # strategy_id -> StrategyPerformance
        self.monitoring_active = True
        
        # Performance thresholds for automatic actions
        self.performance_thresholds = {
            'min_win_rate': 0.4,  # 40% minimum win rate
            'max_drawdown': 0.15,  # 15% maximum drawdown
            'min_sharpe_ratio': 0.5,  # Minimum Sharpe ratio
            'max_consecutive_losses': 5,  # Max consecutive losing trades
            'error_threshold': 10  # Max errors before pausing
        }
        
        # Start monitoring task
        self._monitoring_task = None
        self._start_monitoring()
        
        logger.info("StrategyManager initialized")
    
    def _start_monitoring(self):
        """Start background monitoring task"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop for strategies"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(60)  # Monitor every minute
                
                for strategy_id, instance in self.deployed_strategies.items():
                    if instance.status == StrategyStatus.ACTIVE:
                        await self._monitor_strategy_performance(strategy_id)
                        await self._check_strategy_health(strategy_id)
                
            except Exception as e:
                logger.error(f"Error in strategy monitoring loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    @time_async_operation("deploy_strategy")
    async def deploy_strategy(self, config: StrategyConfig) -> Dict[str, Any]:
        """
        Deploy a trading strategy
        
        Args:
            config: Strategy configuration
            
        Returns:
            Deployment result
        """
        try:
            logger.info(f"Deploying strategy {config.id} for user {config.user_id}")
            
            # Validate strategy configuration
            validation_result = await self._validate_strategy_config(config)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Strategy validation failed',
                    'details': validation_result['errors']
                }
            
            # Check if strategy already exists
            if config.id in self.deployed_strategies:
                return {
                    'success': False,
                    'error': 'Strategy already deployed',
                    'strategy_id': config.id
                }
            
            # Create strategy instance
            instance = StrategyInstance(
                config=config,
                status=StrategyStatus.DEPLOYING,
                deployed_at=datetime.now()
            )
            
            # Store configuration and instance
            self.strategy_configs[config.id] = config
            self.deployed_strategies[config.id] = instance
            
            # Initialize strategy-specific components
            await self._initialize_strategy(config.id)
            
            # Set status to active
            instance.status = StrategyStatus.ACTIVE
            
            # Publish deployment event
            await publish_order_event(config.user_id, EventType.STRATEGY_DEPLOYED, {
                'strategy_id': config.id,
                'strategy_name': config.name,
                'strategy_type': config.strategy_type,
                'deployed_at': instance.deployed_at.isoformat()
            })
            
            trading_monitor.increment_counter("strategies_deployed")
            logger.info(f"Strategy {config.id} deployed successfully")
            
            return {
                'success': True,
                'strategy_id': config.id,
                'status': instance.status.value,
                'deployed_at': instance.deployed_at.isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error deploying strategy {config.id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("strategy_deployment_errors")
            
            # Clean up on error
            if config.id in self.deployed_strategies:
                del self.deployed_strategies[config.id]
            if config.id in self.strategy_configs:
                del self.strategy_configs[config.id]
            
            return {
                'success': False,
                'error': error_msg,
                'strategy_id': config.id
            }
    
    async def _validate_strategy_config(self, config: StrategyConfig) -> Dict[str, Any]:
        """Validate strategy configuration"""
        try:
            errors = []
            warnings = []
            
            # Basic validation
            if not config.name or len(config.name.strip()) == 0:
                errors.append("Strategy name is required")
            
            if not config.symbols or len(config.symbols) == 0:
                errors.append("At least one symbol is required")
            
            if config.max_positions <= 0:
                errors.append("Max positions must be positive")
            
            if config.max_daily_trades <= 0:
                errors.append("Max daily trades must be positive")
            
            # Validate symbols
            for symbol in config.symbols:
                if not isinstance(symbol, str) or len(symbol.strip()) == 0:
                    errors.append(f"Invalid symbol: {symbol}")
            
            # Validate risk parameters
            if config.risk_parameters.max_position_size_percent <= 0:
                errors.append("Max position size must be positive")
            
            if config.risk_parameters.max_position_size_percent > 20:
                warnings.append("Max position size exceeds 20% - high risk")
            
            # Validate strategy parameters
            if not config.parameters:
                warnings.append("No strategy parameters defined")
            
            # Check user permissions (simplified)
            # In production, this would check actual user permissions
            if not config.user_id:
                errors.append("User ID is required")
            
            # Validate trading hours
            if config.enabled_hours:
                try:
                    start_time = config.enabled_hours.get('start_time', '09:15')
                    end_time = config.enabled_hours.get('end_time', '15:30')
                    
                    # Basic time format validation
                    datetime.strptime(start_time, '%H:%M')
                    datetime.strptime(end_time, '%H:%M')
                    
                except ValueError:
                    errors.append("Invalid trading hours format")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating strategy config: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    async def _initialize_strategy(self, strategy_id: str):
        """Initialize strategy-specific components"""
        try:
            config = self.strategy_configs[strategy_id]
            
            # Initialize performance tracking
            self.performance_cache[strategy_id] = StrategyPerformance(
                strategy_id=strategy_id,
                period_start=datetime.now(),
                period_end=datetime.now(),
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                avg_trade_duration=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                volatility=0.0,
                calculated_at=datetime.now()
            )
            
            # Set up risk parameters for the user
            risk_engine.update_user_risk_params(config.user_id, config.risk_parameters)
            
            logger.debug(f"Strategy {strategy_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing strategy {strategy_id}: {e}")
            raise
    
    async def pause_strategy(self, strategy_id: str, reason: str = "Manual pause") -> bool:
        """
        Pause a running strategy
        
        Args:
            strategy_id: Strategy ID to pause
            reason: Reason for pausing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if strategy_id not in self.deployed_strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            instance = self.deployed_strategies[strategy_id]
            
            if instance.status != StrategyStatus.ACTIVE:
                logger.warning(f"Strategy {strategy_id} is not active (status: {instance.status})")
                return False
            
            # Update status
            instance.status = StrategyStatus.PAUSED
            
            # Cancel any pending orders for this strategy
            await self._cancel_strategy_orders(strategy_id)
            
            # Publish pause event
            await publish_order_event(instance.config.user_id, EventType.STRATEGY_PAUSED, {
                'strategy_id': strategy_id,
                'reason': reason,
                'paused_at': datetime.now().isoformat()
            })
            
            trading_monitor.increment_counter("strategies_paused")
            logger.info(f"Strategy {strategy_id} paused: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error pausing strategy {strategy_id}: {e}")
            return False
    
    async def resume_strategy(self, strategy_id: str) -> bool:
        """
        Resume a paused strategy
        
        Args:
            strategy_id: Strategy ID to resume
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if strategy_id not in self.deployed_strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            instance = self.deployed_strategies[strategy_id]
            
            if instance.status != StrategyStatus.PAUSED:
                logger.warning(f"Strategy {strategy_id} is not paused (status: {instance.status})")
                return False
            
            # Validate strategy can be resumed
            validation_result = await self._validate_strategy_resume(strategy_id)
            if not validation_result['can_resume']:
                logger.error(f"Cannot resume strategy {strategy_id}: {validation_result['reason']}")
                return False
            
            # Update status
            instance.status = StrategyStatus.ACTIVE
            
            # Publish resume event
            await publish_order_event(instance.config.user_id, EventType.STRATEGY_RESUMED, {
                'strategy_id': strategy_id,
                'resumed_at': datetime.now().isoformat()
            })
            
            trading_monitor.increment_counter("strategies_resumed")
            logger.info(f"Strategy {strategy_id} resumed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resuming strategy {strategy_id}: {e}")
            return False
    
    async def _validate_strategy_resume(self, strategy_id: str) -> Dict[str, Any]:
        """Validate if strategy can be resumed"""
        try:
            instance = self.deployed_strategies[strategy_id]
            
            # Check error count
            if instance.error_count >= self.performance_thresholds['error_threshold']:
                return {
                    'can_resume': False,
                    'reason': f"Too many errors ({instance.error_count})"
                }
            
            # Check performance metrics
            if strategy_id in self.performance_cache:
                perf = self.performance_cache[strategy_id]
                
                if perf.max_drawdown > self.performance_thresholds['max_drawdown']:
                    return {
                        'can_resume': False,
                        'reason': f"Excessive drawdown ({perf.max_drawdown*100:.1f}%)"
                    }
                
                if perf.total_trades > 10 and perf.win_rate < self.performance_thresholds['min_win_rate']:
                    return {
                        'can_resume': False,
                        'reason': f"Poor win rate ({perf.win_rate*100:.1f}%)"
                    }
            
            # Check trading hours
            if not self._is_trading_hours(instance.config):
                return {
                    'can_resume': False,
                    'reason': "Outside trading hours"
                }
            
            return {
                'can_resume': True,
                'reason': "Strategy can be resumed"
            }
            
        except Exception as e:
            logger.error(f"Error validating strategy resume: {e}")
            return {
                'can_resume': False,
                'reason': f"Validation error: {str(e)}"
            }
    
    async def stop_strategy(self, strategy_id: str, close_positions: bool = True) -> bool:
        """
        Stop a strategy and optionally close positions
        
        Args:
            strategy_id: Strategy ID to stop
            close_positions: Whether to close all positions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if strategy_id not in self.deployed_strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            instance = self.deployed_strategies[strategy_id]
            
            # Update status
            instance.status = StrategyStatus.STOPPED
            
            # Cancel pending orders
            await self._cancel_strategy_orders(strategy_id)
            
            # Close positions if requested
            if close_positions:
                await self._close_strategy_positions(strategy_id)
            
            # Publish stop event
            await publish_order_event(instance.config.user_id, EventType.STRATEGY_STOPPED, {
                'strategy_id': strategy_id,
                'close_positions': close_positions,
                'stopped_at': datetime.now().isoformat()
            })
            
            trading_monitor.increment_counter("strategies_stopped")
            logger.info(f"Strategy {strategy_id} stopped (close_positions: {close_positions})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_id}: {e}")
            return False
    
    async def _cancel_strategy_orders(self, strategy_id: str):
        """Cancel all pending orders for a strategy"""
        try:
            instance = self.deployed_strategies[strategy_id]
            
            # Get active orders for the user
            active_orders = await order_service.get_active_orders(instance.config.user_id)
            
            # Filter orders by strategy
            strategy_orders = [
                order for order in active_orders 
                if order.get('strategy_id') == strategy_id
            ]
            
            # Cancel each order
            cancelled_count = 0
            for order in strategy_orders:
                success = await order_service.cancel_order(order['id'], instance.config.user_id)
                if success:
                    cancelled_count += 1
            
            logger.info(f"Cancelled {cancelled_count} orders for strategy {strategy_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling orders for strategy {strategy_id}: {e}")
    
    async def _close_strategy_positions(self, strategy_id: str):
        """Close all positions for a strategy"""
        try:
            instance = self.deployed_strategies[strategy_id]
            
            # Get user positions
            positions = await position_manager.get_user_positions(instance.config.user_id)
            
            # Filter positions by strategy symbols
            strategy_positions = [
                pos for pos in positions 
                if pos['symbol'] in instance.config.symbols and not pos.get('is_closed', False)
            ]
            
            # Close each position
            closed_count = 0
            for position in strategy_positions:
                success = await position_manager.close_position(
                    instance.config.user_id, 
                    position['symbol']
                )
                if success:
                    closed_count += 1
            
            logger.info(f"Closed {closed_count} positions for strategy {strategy_id}")
            
        except Exception as e:
            logger.error(f"Error closing positions for strategy {strategy_id}: {e}")
    
    def _is_trading_hours(self, config: StrategyConfig) -> bool:
        """Check if current time is within trading hours"""
        try:
            now = datetime.now()
            
            # Check day of week
            current_day = now.strftime('%A')
            trading_days = config.enabled_hours.get('trading_days', [])
            
            if current_day not in trading_days:
                return False
            
            # Check time
            start_time_str = config.enabled_hours.get('start_time', '09:15')
            end_time_str = config.enabled_hours.get('end_time', '15:30')
            
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            current_time = now.time()
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            logger.error(f"Error checking trading hours: {e}")
            return True  # Default to allowing trading on error
    
    async def _monitor_strategy_performance(self, strategy_id: str):
        """Monitor strategy performance and take action if needed"""
        try:
            instance = self.deployed_strategies[strategy_id]
            
            # Update performance metrics
            await self._update_performance_metrics(strategy_id)
            
            # Check performance thresholds
            if strategy_id in self.performance_cache:
                perf = self.performance_cache[strategy_id]
                
                # Check drawdown
                if perf.max_drawdown > self.performance_thresholds['max_drawdown']:
                    await self.pause_strategy(
                        strategy_id, 
                        f"Excessive drawdown: {perf.max_drawdown*100:.1f}%"
                    )
                    return
                
                # Check win rate (only after sufficient trades)
                if (perf.total_trades >= 20 and 
                    perf.win_rate < self.performance_thresholds['min_win_rate']):
                    await self.pause_strategy(
                        strategy_id,
                        f"Poor win rate: {perf.win_rate*100:.1f}%"
                    )
                    return
            
        except Exception as e:
            logger.error(f"Error monitoring strategy performance {strategy_id}: {e}")
    
    async def _check_strategy_health(self, strategy_id: str):
        """Check strategy health and error conditions"""
        try:
            instance = self.deployed_strategies[strategy_id]
            
            # Check error threshold
            if instance.error_count >= self.performance_thresholds['error_threshold']:
                await self.pause_strategy(
                    strategy_id,
                    f"Too many errors: {instance.error_count}"
                )
                return
            
            # Check if strategy is responsive
            if instance.last_signal_at:
                time_since_signal = datetime.now() - instance.last_signal_at
                if time_since_signal > timedelta(hours=4):  # No signals for 4 hours
                    logger.warning(f"Strategy {strategy_id} has not generated signals for {time_since_signal}")
            
            # Check trading hours
            if not self._is_trading_hours(instance.config):
                if instance.status == StrategyStatus.ACTIVE:
                    await self.pause_strategy(strategy_id, "Outside trading hours")
            
        except Exception as e:
            logger.error(f"Error checking strategy health {strategy_id}: {e}")
    
    async def _update_performance_metrics(self, strategy_id: str):
        """Update performance metrics for a strategy"""
        try:
            # This is a simplified implementation
            # In production, this would calculate actual performance from trade history
            
            instance = self.deployed_strategies[strategy_id]
            
            if strategy_id not in self.performance_cache:
                return
            
            perf = self.performance_cache[strategy_id]
            
            # Update basic metrics (simplified)
            perf.total_trades = instance.successful_trades + instance.failed_trades
            perf.winning_trades = instance.successful_trades
            perf.losing_trades = instance.failed_trades
            perf.win_rate = (instance.successful_trades / perf.total_trades) if perf.total_trades > 0 else 0
            perf.total_pnl = instance.total_pnl
            perf.calculated_at = datetime.now()
            
            # Update instance performance metrics
            instance.performance_metrics.update({
                'win_rate': perf.win_rate,
                'total_return': perf.total_pnl,
                'total_trades': perf.total_trades
            })
            
        except Exception as e:
            logger.error(f"Error updating performance metrics for {strategy_id}: {e}")
    
    # Public API methods
    
    async def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a strategy"""
        try:
            if strategy_id not in self.deployed_strategies:
                return None
            
            instance = self.deployed_strategies[strategy_id]
            config = self.strategy_configs[strategy_id]
            
            return {
                'strategy_id': strategy_id,
                'name': config.name,
                'type': config.strategy_type,
                'status': instance.status.value,
                'deployed_at': instance.deployed_at.isoformat() if instance.deployed_at else None,
                'last_signal_at': instance.last_signal_at.isoformat() if instance.last_signal_at else None,
                'total_signals': instance.total_signals,
                'successful_trades': instance.successful_trades,
                'failed_trades': instance.failed_trades,
                'total_pnl': instance.total_pnl,
                'current_positions': instance.current_positions,
                'error_count': instance.error_count,
                'last_error': instance.last_error,
                'performance_metrics': instance.performance_metrics,
                'symbols': config.symbols,
                'max_positions': config.max_positions,
                'max_daily_trades': config.max_daily_trades
            }
            
        except Exception as e:
            logger.error(f"Error getting strategy status {strategy_id}: {e}")
            return None
    
    async def get_user_strategies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all strategies for a user"""
        try:
            user_strategies = []
            
            for strategy_id, instance in self.deployed_strategies.items():
                if instance.config.user_id == user_id:
                    status = await self.get_strategy_status(strategy_id)
                    if status:
                        user_strategies.append(status)
            
            return user_strategies
            
        except Exception as e:
            logger.error(f"Error getting strategies for user {user_id}: {e}")
            return []
    
    async def get_strategy_performance(self, strategy_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
        """Get detailed performance metrics for a strategy"""
        try:
            if strategy_id not in self.performance_cache:
                return None
            
            perf = self.performance_cache[strategy_id]
            
            return {
                'strategy_id': strategy_id,
                'period_days': days,
                'total_trades': perf.total_trades,
                'winning_trades': perf.winning_trades,
                'losing_trades': perf.losing_trades,
                'win_rate': perf.win_rate,
                'total_pnl': perf.total_pnl,
                'max_drawdown': perf.max_drawdown,
                'sharpe_ratio': perf.sharpe_ratio,
                'avg_trade_duration': perf.avg_trade_duration,
                'best_trade': perf.best_trade,
                'worst_trade': perf.worst_trade,
                'volatility': perf.volatility,
                'calculated_at': perf.calculated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting strategy performance {strategy_id}: {e}")
            return None
    
    async def update_strategy_config(self, strategy_id: str, updates: Dict[str, Any]) -> bool:
        """Update strategy configuration"""
        try:
            if strategy_id not in self.strategy_configs:
                logger.error(f"Strategy {strategy_id} not found")
                return False
            
            config = self.strategy_configs[strategy_id]
            instance = self.deployed_strategies[strategy_id]
            
            # Only allow updates for paused or stopped strategies
            if instance.status == StrategyStatus.ACTIVE:
                logger.error(f"Cannot update active strategy {strategy_id}")
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.now()
            
            # Re-validate configuration
            validation_result = await self._validate_strategy_config(config)
            if not validation_result['valid']:
                logger.error(f"Updated configuration invalid: {validation_result['errors']}")
                return False
            
            logger.info(f"Strategy {strategy_id} configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating strategy config {strategy_id}: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get strategy manager monitoring status"""
        try:
            active_strategies = len([s for s in self.deployed_strategies.values() if s.status == StrategyStatus.ACTIVE])
            paused_strategies = len([s for s in self.deployed_strategies.values() if s.status == StrategyStatus.PAUSED])
            stopped_strategies = len([s for s in self.deployed_strategies.values() if s.status == StrategyStatus.STOPPED])
            
            return {
                'monitoring_active': self.monitoring_active,
                'total_strategies': len(self.deployed_strategies),
                'active_strategies': active_strategies,
                'paused_strategies': paused_strategies,
                'stopped_strategies': stopped_strategies,
                'performance_thresholds': self.performance_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}")
            return {}
    
    def stop(self):
        """Stop strategy manager"""
        self.monitoring_active = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        logger.info("StrategyManager stopped")
    
    def start(self):
        """Start strategy manager"""
        self.monitoring_active = True
        self._start_monitoring()
        logger.info("StrategyManager started")

# Global strategy manager instance
strategy_manager = StrategyManager()