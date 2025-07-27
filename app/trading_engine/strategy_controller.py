"""
Strategy Controller
Advanced strategy control and monitoring operations
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .strategy_manager import strategy_manager, StrategyStatus
from .models import TradingSignal, SignalType
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation
from .order_service import order_service
from .position_manager import position_manager

logger = logging.getLogger(__name__)

@dataclass
class StrategyControlAction:
    """Strategy control action record"""
    action_id: str
    strategy_id: str
    action_type: str  # PAUSE, RESUME, STOP, MODIFY, EMERGENCY_STOP
    reason: str
    triggered_by: str  # USER, SYSTEM, PERFORMANCE, RISK
    executed_at: datetime
    success: bool
    details: Dict[str, Any]

@dataclass
class PerformanceAlert:
    """Performance-based alert"""
    alert_id: str
    strategy_id: str
    alert_type: str
    severity: str
    message: str
    metric_value: float
    threshold_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

class StrategyController:
    """
    Advanced strategy control and monitoring system
    """
    
    def __init__(self):
        self.control_actions = {}  # strategy_id -> List[StrategyControlAction]
        self.performance_alerts = {}  # strategy_id -> List[PerformanceAlert]
        self.auto_control_enabled = True
        
        # Performance monitoring thresholds
        self.alert_thresholds = {
            'win_rate_warning': 0.45,
            'win_rate_critical': 0.35,
            'drawdown_warning': 0.10,
            'drawdown_critical': 0.15,
            'pnl_decline_warning': 0.05,
            'pnl_decline_critical': 0.10,
            'error_rate_warning': 0.05,
            'error_rate_critical': 0.10
        }
        
        # Auto-control rules
        self.auto_control_rules = {
            'pause_on_critical_drawdown': True,
            'pause_on_critical_win_rate': True,
            'pause_on_excessive_errors': True,
            'stop_on_emergency_conditions': True,
            'auto_resume_after_pause': False  # Require manual intervention
        }
        
        logger.info("StrategyController initialized")
    
    @time_async_operation("execute_control_action")
    async def execute_control_action(self, strategy_id: str, action_type: str, 
                                   reason: str, triggered_by: str = "USER",
                                   parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a strategy control action
        
        Args:
            strategy_id: Strategy ID
            action_type: Type of action (PAUSE, RESUME, STOP, etc.)
            reason: Reason for the action
            triggered_by: Who/what triggered the action
            parameters: Additional parameters for the action
            
        Returns:
            Action result
        """
        try:
            logger.info(f"Executing {action_type} action on strategy {strategy_id}: {reason}")
            
            action_id = f"{strategy_id}_{action_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Execute the action
            success = False
            details = {}
            
            if action_type == "PAUSE":
                success = await strategy_manager.pause_strategy(strategy_id, reason)
                details = {'paused_at': datetime.now().isoformat()}
                
            elif action_type == "RESUME":
                success = await strategy_manager.resume_strategy(strategy_id)
                details = {'resumed_at': datetime.now().isoformat()}
                
            elif action_type == "STOP":
                close_positions = parameters.get('close_positions', True) if parameters else True
                success = await strategy_manager.stop_strategy(strategy_id, close_positions)
                details = {
                    'stopped_at': datetime.now().isoformat(),
                    'close_positions': close_positions
                }
                
            elif action_type == "EMERGENCY_STOP":
                success = await self._execute_emergency_stop(strategy_id, reason)
                details = {'emergency_stop_at': datetime.now().isoformat()}
                
            elif action_type == "MODIFY":
                if parameters:
                    success = await strategy_manager.update_strategy_config(strategy_id, parameters)
                    details = {'modifications': parameters}
                else:
                    success = False
                    details = {'error': 'No parameters provided for modification'}
                    
            else:
                success = False
                details = {'error': f'Unknown action type: {action_type}'}
            
            # Record the action
            action = StrategyControlAction(
                action_id=action_id,
                strategy_id=strategy_id,
                action_type=action_type,
                reason=reason,
                triggered_by=triggered_by,
                executed_at=datetime.now(),
                success=success,
                details=details
            )
            
            if strategy_id not in self.control_actions:
                self.control_actions[strategy_id] = []
            self.control_actions[strategy_id].append(action)
            
            # Publish control action event
            strategy_status = await strategy_manager.get_strategy_status(strategy_id)
            if strategy_status:
                await publish_order_event(strategy_status['user_id'], EventType.STRATEGY_CONTROL_ACTION, {
                    'action_id': action_id,
                    'strategy_id': strategy_id,
                    'action_type': action_type,
                    'reason': reason,
                    'triggered_by': triggered_by,
                    'success': success,
                    'executed_at': action.executed_at.isoformat()
                })
            
            # Update monitoring counters
            if success:
                trading_monitor.increment_counter(f"strategy_actions_{action_type.lower()}_success")
            else:
                trading_monitor.increment_counter(f"strategy_actions_{action_type.lower()}_failed")
            
            logger.info(f"Control action {action_type} on strategy {strategy_id}: {'SUCCESS' if success else 'FAILED'}")
            
            return {
                'success': success,
                'action_id': action_id,
                'strategy_id': strategy_id,
                'action_type': action_type,
                'executed_at': action.executed_at.isoformat(),
                'details': details
            }
            
        except Exception as e:
            error_msg = f"Error executing control action {action_type} on strategy {strategy_id}: {str(e)}"
            logger.error(error_msg)
            trading_monitor.increment_counter("strategy_control_errors")
            
            return {
                'success': False,
                'error': error_msg,
                'strategy_id': strategy_id,
                'action_type': action_type
            }
    
    async def _execute_emergency_stop(self, strategy_id: str, reason: str) -> bool:
        """Execute emergency stop procedure"""
        try:
            logger.critical(f"EMERGENCY STOP for strategy {strategy_id}: {reason}")
            
            # Stop the strategy immediately
            stop_success = await strategy_manager.stop_strategy(strategy_id, close_positions=True)
            
            if stop_success:
                # Cancel all pending orders
                strategy_status = await strategy_manager.get_strategy_status(strategy_id)
                if strategy_status:
                    active_orders = await order_service.get_active_orders(strategy_status.get('user_id'))
                    strategy_orders = [o for o in active_orders if o.get('strategy_id') == strategy_id]
                    
                    for order in strategy_orders:
                        await order_service.cancel_order(order['id'], strategy_status['user_id'])
                
                trading_monitor.increment_counter("emergency_stops_executed")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing emergency stop for strategy {strategy_id}: {e}")
            return False
    
    @time_async_operation("check_performance_alerts")
    async def check_performance_alerts(self, strategy_id: str) -> List[PerformanceAlert]:
        """
        Check for performance-based alerts
        
        Args:
            strategy_id: Strategy ID to check
            
        Returns:
            List of new alerts
        """
        try:
            new_alerts = []
            
            # Get strategy performance
            performance = await strategy_manager.get_strategy_performance(strategy_id)
            if not performance:
                return new_alerts
            
            strategy_status = await strategy_manager.get_strategy_status(strategy_id)
            if not strategy_status:
                return new_alerts
            
            # Check win rate alerts
            if performance['total_trades'] >= 10:  # Only check after sufficient trades
                win_rate = performance['win_rate']
                
                if win_rate <= self.alert_thresholds['win_rate_critical']:
                    alert = await self._create_performance_alert(
                        strategy_id, 'WIN_RATE', 'CRITICAL',
                        f"Critical win rate: {win_rate*100:.1f}%",
                        win_rate, self.alert_thresholds['win_rate_critical']
                    )
                    new_alerts.append(alert)
                    
                    # Auto-pause if enabled
                    if self.auto_control_rules['pause_on_critical_win_rate']:
                        await self.execute_control_action(
                            strategy_id, 'PAUSE',
                            f"Auto-pause: Critical win rate {win_rate*100:.1f}%",
                            'SYSTEM'
                        )
                        
                elif win_rate <= self.alert_thresholds['win_rate_warning']:
                    alert = await self._create_performance_alert(
                        strategy_id, 'WIN_RATE', 'WARNING',
                        f"Low win rate: {win_rate*100:.1f}%",
                        win_rate, self.alert_thresholds['win_rate_warning']
                    )
                    new_alerts.append(alert)
            
            # Check drawdown alerts
            max_drawdown = performance['max_drawdown']
            
            if max_drawdown >= self.alert_thresholds['drawdown_critical']:
                alert = await self._create_performance_alert(
                    strategy_id, 'DRAWDOWN', 'CRITICAL',
                    f"Critical drawdown: {max_drawdown*100:.1f}%",
                    max_drawdown, self.alert_thresholds['drawdown_critical']
                )
                new_alerts.append(alert)
                
                # Auto-pause if enabled
                if self.auto_control_rules['pause_on_critical_drawdown']:
                    await self.execute_control_action(
                        strategy_id, 'PAUSE',
                        f"Auto-pause: Critical drawdown {max_drawdown*100:.1f}%",
                        'SYSTEM'
                    )
                    
            elif max_drawdown >= self.alert_thresholds['drawdown_warning']:
                alert = await self._create_performance_alert(
                    strategy_id, 'DRAWDOWN', 'WARNING',
                    f"High drawdown: {max_drawdown*100:.1f}%",
                    max_drawdown, self.alert_thresholds['drawdown_warning']
                )
                new_alerts.append(alert)
            
            # Check error rate alerts
            total_signals = strategy_status['total_signals']
            error_count = strategy_status['error_count']
            
            if total_signals > 0:
                error_rate = error_count / total_signals
                
                if error_rate >= self.alert_thresholds['error_rate_critical']:
                    alert = await self._create_performance_alert(
                        strategy_id, 'ERROR_RATE', 'CRITICAL',
                        f"Critical error rate: {error_rate*100:.1f}%",
                        error_rate, self.alert_thresholds['error_rate_critical']
                    )
                    new_alerts.append(alert)
                    
                    # Auto-pause if enabled
                    if self.auto_control_rules['pause_on_excessive_errors']:
                        await self.execute_control_action(
                            strategy_id, 'PAUSE',
                            f"Auto-pause: Critical error rate {error_rate*100:.1f}%",
                            'SYSTEM'
                        )
                        
                elif error_rate >= self.alert_thresholds['error_rate_warning']:
                    alert = await self._create_performance_alert(
                        strategy_id, 'ERROR_RATE', 'WARNING',
                        f"High error rate: {error_rate*100:.1f}%",
                        error_rate, self.alert_thresholds['error_rate_warning']
                    )
                    new_alerts.append(alert)
            
            # Store new alerts
            if new_alerts:
                if strategy_id not in self.performance_alerts:
                    self.performance_alerts[strategy_id] = []
                self.performance_alerts[strategy_id].extend(new_alerts)
                
                # Publish alerts
                for alert in new_alerts:
                    await publish_order_event(strategy_status.get('user_id'), EventType.PERFORMANCE_ALERT, {
                        'alert_id': alert.alert_id,
                        'strategy_id': strategy_id,
                        'alert_type': alert.alert_type,
                        'severity': alert.severity,
                        'message': alert.message,
                        'metric_value': alert.metric_value,
                        'threshold_value': alert.threshold_value,
                        'triggered_at': alert.triggered_at.isoformat()
                    })
                
                trading_monitor.increment_counter("performance_alerts_generated", len(new_alerts))
                logger.warning(f"Generated {len(new_alerts)} performance alerts for strategy {strategy_id}")
            
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error checking performance alerts for strategy {strategy_id}: {e}")
            return []
    
    async def _create_performance_alert(self, strategy_id: str, alert_type: str, severity: str,
                                      message: str, metric_value: float, 
                                      threshold_value: float) -> PerformanceAlert:
        """Create a performance alert"""
        alert_id = f"{strategy_id}_{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return PerformanceAlert(
            alert_id=alert_id,
            strategy_id=strategy_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metric_value=metric_value,
            threshold_value=threshold_value,
            triggered_at=datetime.now()
        )
    
    async def batch_control_action(self, strategy_ids: List[str], action_type: str,
                                 reason: str, triggered_by: str = "USER") -> Dict[str, Any]:
        """
        Execute control action on multiple strategies
        
        Args:
            strategy_ids: List of strategy IDs
            action_type: Action to execute
            reason: Reason for the action
            triggered_by: Who triggered the action
            
        Returns:
            Batch operation result
        """
        try:
            logger.info(f"Executing batch {action_type} on {len(strategy_ids)} strategies")
            
            results = []
            successful = 0
            failed = 0
            
            # Execute action on each strategy
            for strategy_id in strategy_ids:
                result = await self.execute_control_action(
                    strategy_id, action_type, reason, triggered_by
                )
                results.append(result)
                
                if result['success']:
                    successful += 1
                else:
                    failed += 1
            
            batch_result = {
                'success': failed == 0,
                'total_strategies': len(strategy_ids),
                'successful': successful,
                'failed': failed,
                'action_type': action_type,
                'executed_at': datetime.now().isoformat(),
                'results': results
            }
            
            trading_monitor.increment_counter(f"batch_strategy_actions_{action_type.lower()}")
            logger.info(f"Batch {action_type} completed: {successful} successful, {failed} failed")
            
            return batch_result
            
        except Exception as e:
            error_msg = f"Error executing batch control action {action_type}: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'action_type': action_type
            }
    
    async def get_strategy_control_history(self, strategy_id: str, 
                                         limit: int = 50) -> List[Dict[str, Any]]:
        """Get control action history for a strategy"""
        try:
            if strategy_id not in self.control_actions:
                return []
            
            actions = self.control_actions[strategy_id]
            
            # Sort by execution time (most recent first)
            sorted_actions = sorted(actions, key=lambda x: x.executed_at, reverse=True)
            
            # Limit results
            limited_actions = sorted_actions[:limit]
            
            return [
                {
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'reason': action.reason,
                    'triggered_by': action.triggered_by,
                    'executed_at': action.executed_at.isoformat(),
                    'success': action.success,
                    'details': action.details
                }
                for action in limited_actions
            ]
            
        except Exception as e:
            logger.error(f"Error getting control history for strategy {strategy_id}: {e}")
            return []
    
    async def get_performance_alerts(self, strategy_id: str, 
                                   include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Get performance alerts for a strategy"""
        try:
            if strategy_id not in self.performance_alerts:
                return []
            
            alerts = self.performance_alerts[strategy_id]
            
            # Filter resolved alerts if requested
            if not include_resolved:
                alerts = [alert for alert in alerts if alert.resolved_at is None]
            
            return [
                {
                    'alert_id': alert.alert_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'message': alert.message,
                    'metric_value': alert.metric_value,
                    'threshold_value': alert.threshold_value,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                }
                for alert in alerts
            ]
            
        except Exception as e:
            logger.error(f"Error getting performance alerts for strategy {strategy_id}: {e}")
            return []
    
    async def resolve_performance_alert(self, strategy_id: str, alert_id: str) -> bool:
        """Mark a performance alert as resolved"""
        try:
            if strategy_id not in self.performance_alerts:
                return False
            
            for alert in self.performance_alerts[strategy_id]:
                if alert.alert_id == alert_id:
                    alert.resolved_at = datetime.now()
                    logger.info(f"Resolved performance alert {alert_id} for strategy {strategy_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id} for strategy {strategy_id}: {e}")
            return False
    
    def update_control_rules(self, rules: Dict[str, Any]) -> bool:
        """Update auto-control rules"""
        try:
            for key, value in rules.items():
                if key in self.auto_control_rules:
                    self.auto_control_rules[key] = value
            
            logger.info(f"Updated auto-control rules: {rules}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating control rules: {e}")
            return False
    
    def update_alert_thresholds(self, thresholds: Dict[str, float]) -> bool:
        """Update performance alert thresholds"""
        try:
            for key, value in thresholds.items():
                if key in self.alert_thresholds:
                    self.alert_thresholds[key] = value
            
            logger.info(f"Updated alert thresholds: {thresholds}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {e}")
            return False
    
    def get_controller_status(self) -> Dict[str, Any]:
        """Get strategy controller status"""
        try:
            total_actions = sum(len(actions) for actions in self.control_actions.values())
            total_alerts = sum(len(alerts) for alerts in self.performance_alerts.values())
            active_alerts = sum(
                len([a for a in alerts if a.resolved_at is None])
                for alerts in self.performance_alerts.values()
            )
            
            return {
                'auto_control_enabled': self.auto_control_enabled,
                'total_control_actions': total_actions,
                'strategies_with_actions': len(self.control_actions),
                'total_performance_alerts': total_alerts,
                'active_performance_alerts': active_alerts,
                'strategies_with_alerts': len(self.performance_alerts),
                'alert_thresholds': self.alert_thresholds,
                'auto_control_rules': self.auto_control_rules
            }
            
        except Exception as e:
            logger.error(f"Error getting controller status: {e}")
            return {}

# Global strategy controller instance
strategy_controller = StrategyController()