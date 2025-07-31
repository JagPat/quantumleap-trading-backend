"""
Performance Tracker
Real-time strategy performance tracking and analysis system
"""
import asyncio
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
from .models import Position, Order, Execution, StrategyStatus
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation
from .order_db import order_db

logger = logging.getLogger(__name__)

class PerformanceAlert(str, Enum):
    """Performance alert types"""
    DEGRADATION = "DEGRADATION"
    DRAWDOWN_EXCEEDED = "DRAWDOWN_EXCEEDED"
    WIN_RATE_LOW = "WIN_RATE_LOW"
    VOLATILITY_HIGH = "VOLATILITY_HIGH"
    SHARPE_RATIO_LOW = "SHARPE_RATIO_LOW"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    BENCHMARK_UNDERPERFORMANCE = "BENCHMARK_UNDERPERFORMANCE"

@dataclass
class TradeMetrics:
    """Individual trade performance metrics"""
    trade_id: str
    strategy_id: str
    user_id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    pnl: float
    pnl_percent: float
    holding_period_hours: float
    commission: float
    is_winner: bool
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trade_id": self.trade_id,
            "strategy_id": self.strategy_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "holding_period_hours": self.holding_period_hours,
            "commission": self.commission,
            "is_winner": self.is_winner,
            "max_favorable_excursion": self.max_favorable_excursion,
            "max_adverse_excursion": self.max_adverse_excursion
        }

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a strategy"""
    strategy_id: str
    user_id: str
    period_start: datetime
    period_end: datetime
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0  # Gross profit / Gross loss
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    current_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Time-based metrics
    avg_holding_period_hours: float = 0.0
    max_holding_period_hours: float = 0.0
    min_holding_period_hours: float = 0.0
    
    # Streak metrics
    current_win_streak: int = 0
    current_loss_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    # Best/worst trades
    best_trade: float = 0.0
    worst_trade: float = 0.0
    best_trade_percent: float = 0.0
    worst_trade_percent: float = 0.0
    
    # Execution metrics
    avg_slippage: float = 0.0
    total_commission: float = 0.0
    
    # Comparison metrics
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None
    
    # Backtesting comparison
    backtest_win_rate: Optional[float] = None
    backtest_sharpe: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    live_vs_backtest_deviation: Optional[float] = None
    
    # Update timestamp
    calculated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "strategy_id": self.strategy_id,
            "user_id": self.user_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_pnl": self.total_pnl,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "net_profit": self.net_profit,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": self.max_drawdown_percent,
            "current_drawdown": self.current_drawdown,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "avg_holding_period_hours": self.avg_holding_period_hours,
            "max_holding_period_hours": self.max_holding_period_hours,
            "min_holding_period_hours": self.min_holding_period_hours,
            "current_win_streak": self.current_win_streak,
            "current_loss_streak": self.current_loss_streak,
            "max_win_streak": self.max_win_streak,
            "max_loss_streak": self.max_loss_streak,
            "best_trade": self.best_trade,
            "worst_trade": self.worst_trade,
            "best_trade_percent": self.best_trade_percent,
            "worst_trade_percent": self.worst_trade_percent,
            "avg_slippage": self.avg_slippage,
            "total_commission": self.total_commission,
            "benchmark_return": self.benchmark_return,
            "alpha": self.alpha,
            "beta": self.beta,
            "information_ratio": self.information_ratio,
            "backtest_win_rate": self.backtest_win_rate,
            "backtest_sharpe": self.backtest_sharpe,
            "backtest_max_drawdown": self.backtest_max_drawdown,
            "live_vs_backtest_deviation": self.live_vs_backtest_deviation,
            "calculated_at": self.calculated_at.isoformat()
        }

@dataclass
class PerformanceAlert:
    """Performance alert data"""
    alert_id: str
    strategy_id: str
    user_id: str
    alert_type: PerformanceAlert
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    current_value: float
    threshold_value: float
    triggered_at: datetime
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "strategy_id": self.strategy_id,
            "user_id": self.user_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "triggered_at": self.triggered_at.isoformat(),
            "acknowledged": self.acknowledged
        }

class PerformanceTracker:
    """
    Real-time strategy performance tracking and analysis system
    """
    
    def __init__(self):
        self.performance_cache = {}  # strategy_id -> PerformanceMetrics
        self.trade_history = {}  # strategy_id -> List[TradeMetrics]
        self.active_alerts = {}  # strategy_id -> List[PerformanceAlert]
        self.benchmark_data = {}  # symbol -> price history for benchmark comparison
        self.backtest_data = {}  # strategy_id -> backtest results
        
        # Performance thresholds for alerts
        self.alert_thresholds = {
            'max_drawdown_percent': 15.0,  # 15% max drawdown
            'min_win_rate': 40.0,  # 40% minimum win rate
            'min_sharpe_ratio': 0.5,  # Minimum Sharpe ratio
            'max_consecutive_losses': 5,  # Max consecutive losses
            'max_volatility': 30.0,  # 30% max volatility
            'min_profit_factor': 1.2,  # Minimum profit factor
            'backtest_deviation_threshold': 20.0  # 20% deviation from backtest
        }
        
        # Start background monitoring
        self.monitoring_active = True
        self._monitoring_task = None
        self._start_monitoring()
        
        logger.info("PerformanceTracker initialized")
    
    def _start_monitoring(self):
        """Start background monitoring task"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(300)  # Monitor every 5 minutes
                
                for strategy_id in list(self.performance_cache.keys()):
                    await self._update_real_time_metrics(strategy_id)
                    await self._check_performance_alerts(strategy_id)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(600)  # Wait longer on error
    
    @time_async_operation("calculate_strategy_performance")
    async def calculate_strategy_performance(self, strategy_id: str, user_id: str, 
                                           period_days: int = 30) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics for a strategy
        
        Args:
            strategy_id: Strategy ID
            user_id: User ID
            period_days: Period to analyze (days)
            
        Returns:
            PerformanceMetrics object
        """
        try:
            period_start = datetime.now() - timedelta(days=period_days)
            period_end = datetime.now()
            
            # Get trade history for the period
            trades = await self._get_strategy_trades(strategy_id, user_id, period_start, period_end)
            
            if not trades:
                return PerformanceMetrics(
                    strategy_id=strategy_id,
                    user_id=user_id,
                    period_start=period_start,
                    period_end=period_end
                )
            
            # Calculate basic trade statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.is_winner])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate P&L metrics
            total_pnl = sum(t.pnl for t in trades)
            gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
            net_profit = total_pnl
            
            avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0
            avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
            
            # Calculate risk metrics
            returns = [t.pnl_percent for t in trades]
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            
            # Calculate drawdown
            cumulative_returns = []
            running_total = 0
            for trade in trades:
                running_total += trade.pnl_percent
                cumulative_returns.append(running_total)
            
            max_drawdown, max_drawdown_percent = self._calculate_drawdown(cumulative_returns)
            current_drawdown = self._calculate_current_drawdown(cumulative_returns)
            
            # Calculate Sharpe ratio (assuming risk-free rate of 2%)
            risk_free_rate = 2.0
            excess_returns = [r - (risk_free_rate / 365) for r in returns]
            sharpe_ratio = (statistics.mean(excess_returns) / statistics.stdev(excess_returns)) if len(excess_returns) > 1 and statistics.stdev(excess_returns) > 0 else 0
            
            # Calculate Sortino ratio (downside deviation)
            downside_returns = [r for r in excess_returns if r < 0]
            downside_deviation = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 0
            sortino_ratio = (statistics.mean(excess_returns) / downside_deviation) if downside_deviation > 0 else 0
            
            # Calculate Calmar ratio
            calmar_ratio = (statistics.mean(returns) * 365 / max_drawdown_percent) if max_drawdown_percent > 0 else 0
            
            # Calculate time-based metrics
            holding_periods = [t.holding_period_hours for t in trades if t.exit_time]
            avg_holding_period = statistics.mean(holding_periods) if holding_periods else 0
            max_holding_period = max(holding_periods) if holding_periods else 0
            min_holding_period = min(holding_periods) if holding_periods else 0
            
            # Calculate streak metrics
            win_streaks, loss_streaks = self._calculate_streaks(trades)
            current_win_streak, current_loss_streak = self._calculate_current_streaks(trades)
            
            # Best/worst trades
            best_trade = max(t.pnl for t in trades) if trades else 0
            worst_trade = min(t.pnl for t in trades) if trades else 0
            best_trade_percent = max(t.pnl_percent for t in trades) if trades else 0
            worst_trade_percent = min(t.pnl_percent for t in trades) if trades else 0
            
            # Execution metrics
            avg_slippage = statistics.mean([abs(t.max_adverse_excursion) for t in trades]) if trades else 0
            total_commission = sum(t.commission for t in trades)
            
            # Create performance metrics object
            metrics = PerformanceMetrics(
                strategy_id=strategy_id,
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                gross_profit=gross_profit,
                gross_loss=gross_loss,
                net_profit=net_profit,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                max_drawdown_percent=max_drawdown_percent,
                current_drawdown=current_drawdown,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                avg_holding_period_hours=avg_holding_period,
                max_holding_period_hours=max_holding_period,
                min_holding_period_hours=min_holding_period,
                current_win_streak=current_win_streak,
                current_loss_streak=current_loss_streak,
                max_win_streak=max(win_streaks) if win_streaks else 0,
                max_loss_streak=max(loss_streaks) if loss_streaks else 0,
                best_trade=best_trade,
                worst_trade=worst_trade,
                best_trade_percent=best_trade_percent,
                worst_trade_percent=worst_trade_percent,
                avg_slippage=avg_slippage,
                total_commission=total_commission
            )
            
            # Add benchmark comparison if available
            await self._add_benchmark_comparison(metrics, trades)
            
            # Add backtesting comparison if available
            await self._add_backtest_comparison(metrics)
            
            # Cache the metrics
            self.performance_cache[strategy_id] = metrics
            
            # Store trade history
            self.trade_history[strategy_id] = trades
            
            trading_monitor.increment_counter("performance_calculations")
            logger.debug(f"Calculated performance for strategy {strategy_id}: {total_trades} trades, {win_rate:.1f}% win rate")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating strategy performance {strategy_id}: {e}")
            return PerformanceMetrics(
                strategy_id=strategy_id,
                user_id=user_id,
                period_start=datetime.now() - timedelta(days=period_days),
                period_end=datetime.now()
            )
    
    async def _get_strategy_trades(self, strategy_id: str, user_id: str, 
                                 start_date: datetime, end_date: datetime) -> List[TradeMetrics]:
        """Get trade history for a strategy"""
        try:
            # Get orders and executions from database
            orders = order_db.get_orders_by_strategy(strategy_id, user_id, start_date, end_date)
            
            # Group orders into trades (entry and exit pairs)
            trades = []
            open_positions = {}  # symbol -> entry order
            
            for order in sorted(orders, key=lambda x: x.created_at):
                if not order.is_filled():
                    continue
                
                symbol = order.symbol
                
                if symbol not in open_positions:
                    # This is an entry order
                    if order.side.value in ['BUY', 'SELL']:
                        open_positions[symbol] = order
                else:
                    # This is an exit order
                    entry_order = open_positions[symbol]
                    
                    # Calculate trade metrics
                    entry_time = entry_order.filled_at or entry_order.created_at
                    exit_time = order.filled_at or order.created_at
                    
                    holding_period = (exit_time - entry_time).total_seconds() / 3600  # hours
                    
                    # Calculate P&L
                    if entry_order.side.value == 'BUY':
                        pnl = (order.average_fill_price - entry_order.average_fill_price) * entry_order.filled_quantity
                    else:
                        pnl = (entry_order.average_fill_price - order.average_fill_price) * entry_order.filled_quantity
                    
                    pnl_percent = (pnl / (entry_order.average_fill_price * entry_order.filled_quantity)) * 100
                    
                    trade = TradeMetrics(
                        trade_id=f"{entry_order.id}_{order.id}",
                        strategy_id=strategy_id,
                        user_id=user_id,
                        symbol=symbol,
                        entry_time=entry_time,
                        exit_time=exit_time,
                        entry_price=entry_order.average_fill_price,
                        exit_price=order.average_fill_price,
                        quantity=entry_order.filled_quantity,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        holding_period_hours=holding_period,
                        commission=entry_order.commission + order.commission,
                        is_winner=pnl > 0
                    )
                    
                    trades.append(trade)
                    del open_positions[symbol]
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting strategy trades: {e}")
            return []
    
    def _calculate_drawdown(self, cumulative_returns: List[float]) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if not cumulative_returns:
            return 0.0, 0.0
        
        peak = cumulative_returns[0]
        max_drawdown = 0.0
        
        for value in cumulative_returns:
            if value > peak:
                peak = value
            
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        max_drawdown_percent = (max_drawdown / peak * 100) if peak > 0 else 0
        return max_drawdown, max_drawdown_percent
    
    def _calculate_current_drawdown(self, cumulative_returns: List[float]) -> float:
        """Calculate current drawdown from peak"""
        if not cumulative_returns:
            return 0.0
        
        peak = max(cumulative_returns)
        current = cumulative_returns[-1]
        
        return peak - current
    
    def _calculate_streaks(self, trades: List[TradeMetrics]) -> Tuple[List[int], List[int]]:
        """Calculate win and loss streaks"""
        if not trades:
            return [], []
        
        win_streaks = []
        loss_streaks = []
        current_win_streak = 0
        current_loss_streak = 0
        
        for trade in trades:
            if trade.is_winner:
                if current_loss_streak > 0:
                    loss_streaks.append(current_loss_streak)
                    current_loss_streak = 0
                current_win_streak += 1
            else:
                if current_win_streak > 0:
                    win_streaks.append(current_win_streak)
                    current_win_streak = 0
                current_loss_streak += 1
        
        # Add final streak
        if current_win_streak > 0:
            win_streaks.append(current_win_streak)
        if current_loss_streak > 0:
            loss_streaks.append(current_loss_streak)
        
        return win_streaks, loss_streaks
    
    def _calculate_current_streaks(self, trades: List[TradeMetrics]) -> Tuple[int, int]:
        """Calculate current win/loss streaks"""
        if not trades:
            return 0, 0
        
        current_win_streak = 0
        current_loss_streak = 0
        
        # Count from the end
        for trade in reversed(trades):
            if trade.is_winner:
                if current_loss_streak > 0:
                    break
                current_win_streak += 1
            else:
                if current_win_streak > 0:
                    break
                current_loss_streak += 1
        
        return current_win_streak, current_loss_streak
    
    async def _add_benchmark_comparison(self, metrics: PerformanceMetrics, trades: List[TradeMetrics]):
        """Add benchmark comparison metrics"""
        try:
            # This is a simplified implementation
            # In production, you would fetch actual benchmark data (e.g., S&P 500, NIFTY 50)
            
            # For now, assume a benchmark return of 8% annually
            benchmark_annual_return = 8.0
            period_days = (metrics.period_end - metrics.period_start).days
            benchmark_return = benchmark_annual_return * (period_days / 365)
            
            metrics.benchmark_return = benchmark_return
            
            # Calculate alpha (excess return over benchmark)
            strategy_return = sum(t.pnl_percent for t in trades)
            metrics.alpha = strategy_return - benchmark_return
            
            # Simplified beta calculation (would need market data for accurate calculation)
            metrics.beta = 1.0  # Assume market beta for now
            
            # Information ratio (alpha / tracking error)
            # Simplified calculation
            tracking_error = abs(strategy_return - benchmark_return)
            metrics.information_ratio = metrics.alpha / tracking_error if tracking_error > 0 else 0
            
        except Exception as e:
            logger.error(f"Error adding benchmark comparison: {e}")
    
    async def _add_backtest_comparison(self, metrics: PerformanceMetrics):
        """Add backtesting comparison metrics"""
        try:
            strategy_id = metrics.strategy_id
            
            if strategy_id in self.backtest_data:
                backtest = self.backtest_data[strategy_id]
                
                metrics.backtest_win_rate = backtest.get('win_rate')
                metrics.backtest_sharpe = backtest.get('sharpe_ratio')
                metrics.backtest_max_drawdown = backtest.get('max_drawdown')
                
                # Calculate deviation from backtest
                if metrics.backtest_win_rate:
                    win_rate_deviation = abs(metrics.win_rate - metrics.backtest_win_rate)
                    sharpe_deviation = abs(metrics.sharpe_ratio - (metrics.backtest_sharpe or 0))
                    drawdown_deviation = abs(metrics.max_drawdown_percent - (metrics.backtest_max_drawdown or 0))
                    
                    # Average deviation
                    metrics.live_vs_backtest_deviation = (win_rate_deviation + sharpe_deviation + drawdown_deviation) / 3
            
        except Exception as e:
            logger.error(f"Error adding backtest comparison: {e}")
    
    async def _update_real_time_metrics(self, strategy_id: str):
        """Update real-time performance metrics"""
        try:
            if strategy_id not in self.performance_cache:
                return
            
            metrics = self.performance_cache[strategy_id]
            
            # Recalculate metrics with latest data
            updated_metrics = await self.calculate_strategy_performance(
                strategy_id, 
                metrics.user_id, 
                period_days=30
            )
            
            # Check for significant changes
            if self._has_significant_change(metrics, updated_metrics):
                await self._publish_performance_update(updated_metrics)
            
        except Exception as e:
            logger.error(f"Error updating real-time metrics for {strategy_id}: {e}")
    
    def _has_significant_change(self, old_metrics: PerformanceMetrics, 
                               new_metrics: PerformanceMetrics) -> bool:
        """Check if there's a significant change in performance"""
        try:
            # Define thresholds for significant changes
            thresholds = {
                'win_rate': 5.0,  # 5% change in win rate
                'sharpe_ratio': 0.2,  # 0.2 change in Sharpe ratio
                'max_drawdown_percent': 2.0,  # 2% change in max drawdown
                'total_pnl': 1000.0  # ₹1000 change in P&L
            }
            
            changes = {
                'win_rate': abs(new_metrics.win_rate - old_metrics.win_rate),
                'sharpe_ratio': abs(new_metrics.sharpe_ratio - old_metrics.sharpe_ratio),
                'max_drawdown_percent': abs(new_metrics.max_drawdown_percent - old_metrics.max_drawdown_percent),
                'total_pnl': abs(new_metrics.total_pnl - old_metrics.total_pnl)
            }
            
            for metric, change in changes.items():
                if change >= thresholds[metric]:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking significant change: {e}")
            return False
    
    async def _publish_performance_update(self, metrics: PerformanceMetrics):
        """Publish performance update event"""
        try:
            await publish_order_event(metrics.user_id, EventType.PERFORMANCE_UPDATED, {
                'strategy_id': metrics.strategy_id,
                'metrics': metrics.to_dict(),
                'updated_at': datetime.now().isoformat()
            })
            
            trading_monitor.increment_counter("performance_updates_published")
            
        except Exception as e:
            logger.error(f"Error publishing performance update: {e}")
    
    async def _check_performance_alerts(self, strategy_id: str):
        """Check for performance alerts"""
        try:
            if strategy_id not in self.performance_cache:
                return
            
            metrics = self.performance_cache[strategy_id]
            alerts = []
            
            # Check drawdown alert
            if metrics.max_drawdown_percent > self.alert_thresholds['max_drawdown_percent']:
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.DRAWDOWN_EXCEEDED,
                    "CRITICAL",
                    f"Maximum drawdown exceeded: {metrics.max_drawdown_percent:.1f}%",
                    metrics.max_drawdown_percent,
                    self.alert_thresholds['max_drawdown_percent']
                ))
            
            # Check win rate alert
            if metrics.total_trades >= 10 and metrics.win_rate < self.alert_thresholds['min_win_rate']:
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.WIN_RATE_LOW,
                    "HIGH",
                    f"Win rate below threshold: {metrics.win_rate:.1f}%",
                    metrics.win_rate,
                    self.alert_thresholds['min_win_rate']
                ))
            
            # Check Sharpe ratio alert
            if metrics.sharpe_ratio < self.alert_thresholds['min_sharpe_ratio']:
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.SHARPE_RATIO_LOW,
                    "MEDIUM",
                    f"Sharpe ratio below threshold: {metrics.sharpe_ratio:.2f}",
                    metrics.sharpe_ratio,
                    self.alert_thresholds['min_sharpe_ratio']
                ))
            
            # Check consecutive losses
            if metrics.current_loss_streak >= self.alert_thresholds['max_consecutive_losses']:
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.CONSECUTIVE_LOSSES,
                    "HIGH",
                    f"Consecutive losses: {metrics.current_loss_streak}",
                    metrics.current_loss_streak,
                    self.alert_thresholds['max_consecutive_losses']
                ))
            
            # Check volatility alert
            if metrics.volatility > self.alert_thresholds['max_volatility']:
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.VOLATILITY_HIGH,
                    "MEDIUM",
                    f"High volatility detected: {metrics.volatility:.1f}%",
                    metrics.volatility,
                    self.alert_thresholds['max_volatility']
                ))
            
            # Check backtest deviation
            if (metrics.live_vs_backtest_deviation and 
                metrics.live_vs_backtest_deviation > self.alert_thresholds['backtest_deviation_threshold']):
                alerts.append(self._create_alert(
                    strategy_id, metrics.user_id,
                    PerformanceAlert.BENCHMARK_UNDERPERFORMANCE,
                    "HIGH",
                    f"Performance deviates from backtest: {metrics.live_vs_backtest_deviation:.1f}%",
                    metrics.live_vs_backtest_deviation,
                    self.alert_thresholds['backtest_deviation_threshold']
                ))
            
            # Store and publish alerts
            if alerts:
                if strategy_id not in self.active_alerts:
                    self.active_alerts[strategy_id] = []
                
                for alert in alerts:
                    # Check if alert already exists
                    existing_alert = next(
                        (a for a in self.active_alerts[strategy_id] 
                         if a.alert_type == alert.alert_type and not a.acknowledged),
                        None
                    )
                    
                    if not existing_alert:
                        self.active_alerts[strategy_id].append(alert)
                        await self._publish_performance_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking performance alerts for {strategy_id}: {e}")
    
    def _create_alert(self, strategy_id: str, user_id: str, alert_type: PerformanceAlert,
                     severity: str, message: str, current_value: float, 
                     threshold_value: float) -> PerformanceAlert:
        """Create a performance alert"""
        return PerformanceAlert(
            alert_id=f"{strategy_id}_{alert_type.value}_{int(datetime.now().timestamp())}",
            strategy_id=strategy_id,
            user_id=user_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            triggered_at=datetime.now()
        )
    
    async def _publish_performance_alert(self, alert: PerformanceAlert):
        """Publish performance alert"""
        try:
            await publish_order_event(alert.user_id, EventType.PERFORMANCE_ALERT, {
                'alert': alert.to_dict()
            })
            
            trading_monitor.increment_counter("performance_alerts_triggered")
            logger.warning(f"Performance alert triggered: {alert.message}")
            
        except Exception as e:
            logger.error(f"Error publishing performance alert: {e}")
    
    # Public API methods
    
    async def get_strategy_performance(self, strategy_id: str, user_id: str, 
                                     period_days: int = 30) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a strategy"""
        try:
            metrics = await self.calculate_strategy_performance(strategy_id, user_id, period_days)
            return metrics.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting strategy performance: {e}")
            return None
    
    async def compare_with_backtest(self, strategy_id: str, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare live performance with backtest results"""
        try:
            # Store backtest data
            self.backtest_data[strategy_id] = backtest_results
            
            if strategy_id not in self.performance_cache:
                return {'error': 'No live performance data available'}
            
            live_metrics = self.performance_cache[strategy_id]
            
            comparison = {
                'strategy_id': strategy_id,
                'comparison_date': datetime.now().isoformat(),
                'metrics_comparison': {
                    'win_rate': {
                        'live': live_metrics.win_rate,
                        'backtest': backtest_results.get('win_rate', 0),
                        'difference': live_metrics.win_rate - backtest_results.get('win_rate', 0)
                    },
                    'sharpe_ratio': {
                        'live': live_metrics.sharpe_ratio,
                        'backtest': backtest_results.get('sharpe_ratio', 0),
                        'difference': live_metrics.sharpe_ratio - backtest_results.get('sharpe_ratio', 0)
                    },
                    'max_drawdown': {
                        'live': live_metrics.max_drawdown_percent,
                        'backtest': backtest_results.get('max_drawdown', 0),
                        'difference': live_metrics.max_drawdown_percent - backtest_results.get('max_drawdown', 0)
                    },
                    'profit_factor': {
                        'live': live_metrics.profit_factor,
                        'backtest': backtest_results.get('profit_factor', 0),
                        'difference': live_metrics.profit_factor - backtest_results.get('profit_factor', 0)
                    }
                },
                'overall_deviation': live_metrics.live_vs_backtest_deviation,
                'performance_status': self._get_performance_status(live_metrics, backtest_results)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing with backtest: {e}")
            return {'error': str(e)}
    
    def _get_performance_status(self, live_metrics: PerformanceMetrics, 
                               backtest_results: Dict[str, Any]) -> str:
        """Get overall performance status compared to backtest"""
        try:
            if not live_metrics.live_vs_backtest_deviation:
                return "INSUFFICIENT_DATA"
            
            if live_metrics.live_vs_backtest_deviation < 10:
                return "PERFORMING_AS_EXPECTED"
            elif live_metrics.live_vs_backtest_deviation < 20:
                return "MINOR_DEVIATION"
            elif live_metrics.live_vs_backtest_deviation < 30:
                return "SIGNIFICANT_DEVIATION"
            else:
                return "MAJOR_DEVIATION"
                
        except Exception as e:
            logger.error(f"Error getting performance status: {e}")
            return "ERROR"
    
    async def get_performance_alerts(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get active performance alerts for a strategy"""
        try:
            if strategy_id not in self.active_alerts:
                return []
            
            return [alert.to_dict() for alert in self.active_alerts[strategy_id] if not alert.acknowledged]
            
        except Exception as e:
            logger.error(f"Error getting performance alerts: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a performance alert"""
        try:
            for strategy_alerts in self.active_alerts.values():
                for alert in strategy_alerts:
                    if alert.alert_id == alert_id:
                        alert.acknowledged = True
                        logger.info(f"Alert acknowledged: {alert_id}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()

# Global performance tracker instance
performance_tracker = PerformanceTracker()