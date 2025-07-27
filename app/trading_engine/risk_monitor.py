"""
Real-time Risk Monitoring System
Continuously monitors portfolio risk and executes automatic risk controls
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from .models import Order, OrderSide, OrderStatus, Position
from .risk_engine import risk_engine, PortfolioRisk
from .position_manager import position_manager
from .order_service import order_service
from .order_db import order_db
from .event_bus import event_bus, EventType, publish_order_event
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

@dataclass
class RiskAlert:
    """Risk alert information"""
    id: str
    user_id: str
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    current_value: float
    threshold_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    actions_taken: List[str] = None

@dataclass
class StopLossOrder:
    """Stop loss order configuration"""
    user_id: str
    symbol: str
    trigger_price: float
    order_type: str  # MARKET, LIMIT
    limit_price: Optional[float] = None
    quantity: int = 0  # 0 means close entire position

class RiskMonitor:
    """
    Real-time risk monitoring and automatic risk control system
    """
    
    def __init__(self):
        self.active_alerts = {}  # user_id -> List[RiskAlert]
        self.stop_loss_orders = {}  # user_id -> Dict[symbol, StopLossOrder]
        self.emergency_stops = set()  # Set of user_ids with emergency stops active
        self.monitoring_active = True
        
        # Risk monitoring thresholds
        self.risk_thresholds = {
            'portfolio_risk_score': {'medium': 0.6, 'high': 0.8, 'critical': 0.9},
            'drawdown_percent': {'medium': 10.0, 'high': 15.0, 'critical': 20.0},
            'exposure_percent': {'medium': 70.0, 'high': 85.0, 'critical': 95.0},
            'sector_concentration': {'medium': 25.0, 'high': 35.0, 'critical': 45.0},
            'position_concentration': {'medium': 8.0, 'high': 12.0, 'critical': 15.0}
        }
        
        # Start monitoring tasks
        self._monitoring_task = None
        self._start_monitoring()
        
        logger.info("RiskMonitor initialized and monitoring started")
    
    def _start_monitoring(self):
        """Start background monitoring tasks"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
                # Get all users with active positions
                active_users = await self._get_active_users()
                
                for user_id in active_users:
                    if user_id not in self.emergency_stops:
                        await self._monitor_user_risk(user_id)
                
                # Clean up resolved alerts
                await self._cleanup_resolved_alerts()
                
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _get_active_users(self) -> Set[str]:
        """Get list of users with active positions or orders"""
        try:
            active_users = set()
            
            # Get users with active orders
            active_orders = order_db.get_active_orders()
            for order in active_orders:
                active_users.add(order.user_id)
            
            # Get users with open positions (simplified - would be more efficient in production)
            # For now, we'll monitor a fixed set of test users
            active_users.update(['test_user_1', 'test_user_2'])
            
            return active_users
            
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return set()
    
    @time_async_operation("monitor_user_risk")
    async def _monitor_user_risk(self, user_id: str):
        """Monitor risk for a specific user"""
        try:
            # Calculate current portfolio risk
            portfolio_risk = await risk_engine.calculate_portfolio_risk(user_id)
            
            # Check for risk threshold breaches
            await self._check_risk_thresholds(user_id, portfolio_risk)
            
            # Check stop loss triggers
            await self._check_stop_loss_triggers(user_id)
            
            # Check for emergency stop conditions
            await self._check_emergency_stop_conditions(user_id, portfolio_risk)
            
            trading_monitor.increment_counter("risk_monitoring_checks")
            
        except Exception as e:
            logger.error(f"Error monitoring risk for user {user_id}: {e}")
            trading_monitor.increment_counter("risk_monitoring_errors")
    
    async def _check_risk_thresholds(self, user_id: str, portfolio_risk: PortfolioRisk):
        """Check if any risk thresholds are breached"""
        try:
            current_alerts = self.active_alerts.get(user_id, [])
            new_alerts = []
            
            # Check portfolio risk score
            risk_score = portfolio_risk.risk_score
            severity = self._get_severity_level('portfolio_risk_score', risk_score)
            if severity:
                alert = await self._create_risk_alert(
                    user_id, 'portfolio_risk_score', severity,
                    f"Portfolio risk score is {risk_score:.3f}",
                    risk_score, self.risk_thresholds['portfolio_risk_score'][severity]
                )
                new_alerts.append(alert)
            
            # Check drawdown
            drawdown = portfolio_risk.current_drawdown
            severity = self._get_severity_level('drawdown_percent', drawdown)
            if severity:
                alert = await self._create_risk_alert(
                    user_id, 'drawdown_percent', severity,
                    f"Portfolio drawdown is {drawdown:.1f}%",
                    drawdown, self.risk_thresholds['drawdown_percent'][severity]
                )
                new_alerts.append(alert)
            
            # Check exposure
            exposure = portfolio_risk.exposure_percentage
            severity = self._get_severity_level('exposure_percent', exposure)
            if severity:
                alert = await self._create_risk_alert(
                    user_id, 'exposure_percent', severity,
                    f"Portfolio exposure is {exposure:.1f}%",
                    exposure, self.risk_thresholds['exposure_percent'][severity]
                )
                new_alerts.append(alert)
            
            # Check sector concentration
            if portfolio_risk.sector_exposures:
                max_sector_exposure = max(portfolio_risk.sector_exposures.values())
                severity = self._get_severity_level('sector_concentration', max_sector_exposure)
                if severity:
                    max_sector = max(portfolio_risk.sector_exposures.items(), key=lambda x: x[1])
                    alert = await self._create_risk_alert(
                        user_id, 'sector_concentration', severity,
                        f"High sector concentration in {max_sector[0]}: {max_sector_exposure:.1f}%",
                        max_sector_exposure, self.risk_thresholds['sector_concentration'][severity]
                    )
                    new_alerts.append(alert)
            
            # Check position concentration
            if portfolio_risk.position_concentrations:
                max_position_concentration = max(portfolio_risk.position_concentrations.values())
                severity = self._get_severity_level('position_concentration', max_position_concentration)
                if severity:
                    max_position = max(portfolio_risk.position_concentrations.items(), key=lambda x: x[1])
                    alert = await self._create_risk_alert(
                        user_id, 'position_concentration', severity,
                        f"High position concentration in {max_position[0]}: {max_position_concentration:.1f}%",
                        max_position_concentration, self.risk_thresholds['position_concentration'][severity]
                    )
                    new_alerts.append(alert)
            
            # Update active alerts
            if new_alerts:
                self.active_alerts[user_id] = current_alerts + new_alerts
                
                # Publish risk alerts
                for alert in new_alerts:
                    await publish_order_event(user_id, EventType.RISK_ALERT, {
                        'alert': {
                            'id': alert.id,
                            'type': alert.alert_type,
                            'severity': alert.severity,
                            'message': alert.message,
                            'current_value': alert.current_value,
                            'threshold_value': alert.threshold_value,
                            'triggered_at': alert.triggered_at.isoformat()
                        }
                    })
                
                logger.warning(f"Generated {len(new_alerts)} risk alerts for user {user_id}")
                trading_monitor.increment_counter("risk_alerts_generated", len(new_alerts))
            
        except Exception as e:
            logger.error(f"Error checking risk thresholds for user {user_id}: {e}")
    
    def _get_severity_level(self, metric_type: str, value: float) -> Optional[str]:
        """Determine severity level for a metric value"""
        thresholds = self.risk_thresholds.get(metric_type, {})
        
        if value >= thresholds.get('critical', float('inf')):
            return 'critical'
        elif value >= thresholds.get('high', float('inf')):
            return 'high'
        elif value >= thresholds.get('medium', float('inf')):
            return 'medium'
        
        return None
    
    async def _create_risk_alert(self, user_id: str, alert_type: str, severity: str,
                               message: str, current_value: float, threshold_value: float) -> RiskAlert:
        """Create a new risk alert"""
        alert_id = f"{user_id}_{alert_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        alert = RiskAlert(
            id=alert_id,
            user_id=user_id,
            alert_type=alert_type,
            severity=severity.upper(),
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            triggered_at=datetime.now(),
            actions_taken=[]
        )
        
        return alert
    
    async def _check_stop_loss_triggers(self, user_id: str):
        """Check if any stop loss orders should be triggered"""
        try:
            if user_id not in self.stop_loss_orders:
                return
            
            positions = await position_manager.get_user_positions(user_id)
            
            for position in positions:
                symbol = position['symbol']
                if symbol in self.stop_loss_orders[user_id]:
                    stop_loss = self.stop_loss_orders[user_id][symbol]
                    current_price = position.get('current_price', position['average_price'])
                    
                    # Check if stop loss should trigger
                    should_trigger = False
                    if position['quantity'] > 0:  # Long position
                        should_trigger = current_price <= stop_loss.trigger_price
                    else:  # Short position
                        should_trigger = current_price >= stop_loss.trigger_price
                    
                    if should_trigger:
                        await self._execute_stop_loss(user_id, symbol, stop_loss, current_price)
            
        except Exception as e:
            logger.error(f"Error checking stop loss triggers for user {user_id}: {e}")
    
    async def _execute_stop_loss(self, user_id: str, symbol: str, stop_loss: StopLossOrder, current_price: float):
        """Execute a stop loss order"""
        try:
            logger.warning(f"Executing stop loss for {user_id}/{symbol} at price {current_price}")
            
            # Get current position
            position = await position_manager.get_position(user_id, symbol)
            if not position or position.is_closed:
                logger.warning(f"No open position found for stop loss execution: {user_id}/{symbol}")
                return
            
            # Determine order details
            if position.quantity > 0:
                side = OrderSide.SELL
                quantity = abs(stop_loss.quantity) if stop_loss.quantity > 0 else abs(position.quantity)
            else:
                side = OrderSide.BUY
                quantity = abs(stop_loss.quantity) if stop_loss.quantity > 0 else abs(position.quantity)
            
            # Create stop loss order
            from .models import Order, OrderType
            import uuid
            
            order = Order(
                id=str(uuid.uuid4()),
                user_id=user_id,
                symbol=symbol,
                order_type=OrderType.MARKET if stop_loss.order_type == 'MARKET' else OrderType.LIMIT,
                side=side,
                quantity=quantity,
                price=stop_loss.limit_price if stop_loss.order_type == 'LIMIT' else None,
                metadata={
                    'stop_loss_execution': True,
                    'trigger_price': stop_loss.trigger_price,
                    'original_position_quantity': position.quantity
                }
            )
            
            # Execute the order
            result = await order_service.create_order_from_signal(
                # Create a dummy signal for stop loss execution
                # In production, this would be handled differently
                type('TradingSignal', (), {
                    'id': f"stop_loss_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'user_id': user_id,
                    'symbol': symbol,
                    'signal_type': 'SELL' if side == OrderSide.SELL else 'BUY',
                    'confidence_score': 1.0,
                    'processed': False,
                    'is_expired': lambda: False
                })()
            )
            
            if result.success:
                # Remove the stop loss order
                del self.stop_loss_orders[user_id][symbol]
                
                # Create alert
                alert = await self._create_risk_alert(
                    user_id, 'stop_loss_executed', 'high',
                    f"Stop loss executed for {symbol} at {current_price}",
                    current_price, stop_loss.trigger_price
                )
                
                if user_id not in self.active_alerts:
                    self.active_alerts[user_id] = []
                self.active_alerts[user_id].append(alert)
                
                # Publish event
                await publish_order_event(user_id, EventType.STOP_LOSS_EXECUTED, {
                    'symbol': symbol,
                    'trigger_price': stop_loss.trigger_price,
                    'execution_price': current_price,
                    'quantity': quantity,
                    'order_id': order.id
                })
                
                trading_monitor.increment_counter("stop_losses_executed")
                logger.info(f"Stop loss executed successfully for {user_id}/{symbol}")
            else:
                logger.error(f"Failed to execute stop loss for {user_id}/{symbol}: {result.error_message}")
                trading_monitor.increment_counter("stop_loss_execution_failures")
            
        except Exception as e:
            logger.error(f"Error executing stop loss for {user_id}/{symbol}: {e}")
            trading_monitor.increment_counter("stop_loss_execution_errors")
    
    async def _check_emergency_stop_conditions(self, user_id: str, portfolio_risk: PortfolioRisk):
        """Check if emergency stop should be triggered"""
        try:
            if user_id in self.emergency_stops:
                return  # Already in emergency stop
            
            # Emergency stop conditions
            emergency_conditions = []
            
            if portfolio_risk.risk_score >= 0.95:
                emergency_conditions.append(f"Critical risk score: {portfolio_risk.risk_score:.3f}")
            
            if portfolio_risk.current_drawdown >= 25.0:
                emergency_conditions.append(f"Excessive drawdown: {portfolio_risk.current_drawdown:.1f}%")
            
            if portfolio_risk.exposure_percentage >= 98.0:
                emergency_conditions.append(f"Excessive exposure: {portfolio_risk.exposure_percentage:.1f}%")
            
            if emergency_conditions:
                await self._trigger_emergency_stop(user_id, emergency_conditions)
            
        except Exception as e:
            logger.error(f"Error checking emergency stop conditions for user {user_id}: {e}")
    
    async def _trigger_emergency_stop(self, user_id: str, conditions: List[str]):
        """Trigger emergency stop for a user"""
        try:
            logger.critical(f"EMERGENCY STOP triggered for user {user_id}: {conditions}")
            
            # Add to emergency stops
            self.emergency_stops.add(user_id)
            
            # Cancel all active orders
            active_orders = order_db.get_active_orders(user_id)
            cancelled_orders = []
            
            for order in active_orders:
                success = await order_service.cancel_order(order.id, user_id)
                if success:
                    cancelled_orders.append(order.id)
            
            # Create critical alert
            alert = await self._create_risk_alert(
                user_id, 'emergency_stop', 'critical',
                f"Emergency stop triggered: {'; '.join(conditions)}",
                1.0, 0.95
            )
            alert.actions_taken = [
                f"Cancelled {len(cancelled_orders)} active orders",
                "All new orders blocked until manual review"
            ]
            
            if user_id not in self.active_alerts:
                self.active_alerts[user_id] = []
            self.active_alerts[user_id].append(alert)
            
            # Publish emergency stop event
            await publish_order_event(user_id, EventType.EMERGENCY_STOP, {
                'conditions': conditions,
                'cancelled_orders': cancelled_orders,
                'timestamp': datetime.now().isoformat()
            })
            
            trading_monitor.increment_counter("emergency_stops_triggered")
            logger.critical(f"Emergency stop executed for user {user_id}: cancelled {len(cancelled_orders)} orders")
            
        except Exception as e:
            logger.error(f"Error triggering emergency stop for user {user_id}: {e}")
    
    async def _cleanup_resolved_alerts(self):
        """Clean up old resolved alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)  # Keep alerts for 24 hours
            
            for user_id in list(self.active_alerts.keys()):
                alerts = self.active_alerts[user_id]
                active_alerts = [
                    alert for alert in alerts
                    if alert.resolved_at is None or alert.resolved_at > cutoff_time
                ]
                
                if len(active_alerts) != len(alerts):
                    self.active_alerts[user_id] = active_alerts
                    logger.debug(f"Cleaned up {len(alerts) - len(active_alerts)} old alerts for user {user_id}")
                
                if not active_alerts:
                    del self.active_alerts[user_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up resolved alerts: {e}")
    
    # Public API methods
    
    async def add_stop_loss(self, user_id: str, symbol: str, trigger_price: float,
                          order_type: str = 'MARKET', limit_price: Optional[float] = None,
                          quantity: int = 0) -> bool:
        """Add a stop loss order for monitoring"""
        try:
            stop_loss = StopLossOrder(
                user_id=user_id,
                symbol=symbol,
                trigger_price=trigger_price,
                order_type=order_type,
                limit_price=limit_price,
                quantity=quantity
            )
            
            if user_id not in self.stop_loss_orders:
                self.stop_loss_orders[user_id] = {}
            
            self.stop_loss_orders[user_id][symbol] = stop_loss
            
            logger.info(f"Added stop loss for {user_id}/{symbol} at {trigger_price}")
            trading_monitor.increment_counter("stop_losses_added")
            return True
            
        except Exception as e:
            logger.error(f"Error adding stop loss for {user_id}/{symbol}: {e}")
            return False
    
    async def remove_stop_loss(self, user_id: str, symbol: str) -> bool:
        """Remove a stop loss order"""
        try:
            if user_id in self.stop_loss_orders and symbol in self.stop_loss_orders[user_id]:
                del self.stop_loss_orders[user_id][symbol]
                logger.info(f"Removed stop loss for {user_id}/{symbol}")
                trading_monitor.increment_counter("stop_losses_removed")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing stop loss for {user_id}/{symbol}: {e}")
            return False
    
    async def get_user_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active alerts for a user"""
        try:
            alerts = self.active_alerts.get(user_id, [])
            return [
                {
                    'id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'message': alert.message,
                    'current_value': alert.current_value,
                    'threshold_value': alert.threshold_value,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'actions_taken': alert.actions_taken or []
                }
                for alert in alerts
            ]
            
        except Exception as e:
            logger.error(f"Error getting alerts for user {user_id}: {e}")
            return []
    
    async def resolve_alert(self, user_id: str, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        try:
            if user_id in self.active_alerts:
                for alert in self.active_alerts[user_id]:
                    if alert.id == alert_id:
                        alert.resolved_at = datetime.now()
                        logger.info(f"Resolved alert {alert_id} for user {user_id}")
                        return True
            return False
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id} for user {user_id}: {e}")
            return False
    
    async def clear_emergency_stop(self, user_id: str) -> bool:
        """Clear emergency stop for a user (manual intervention required)"""
        try:
            if user_id in self.emergency_stops:
                self.emergency_stops.remove(user_id)
                
                # Resolve emergency stop alert
                if user_id in self.active_alerts:
                    for alert in self.active_alerts[user_id]:
                        if alert.alert_type == 'emergency_stop' and alert.resolved_at is None:
                            alert.resolved_at = datetime.now()
                            alert.actions_taken.append("Emergency stop cleared by manual intervention")
                
                logger.info(f"Emergency stop cleared for user {user_id}")
                trading_monitor.increment_counter("emergency_stops_cleared")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error clearing emergency stop for user {user_id}: {e}")
            return False
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        try:
            return {
                'monitoring_active': self.monitoring_active,
                'active_alerts_count': sum(len(alerts) for alerts in self.active_alerts.values()),
                'users_with_alerts': len(self.active_alerts),
                'stop_loss_orders_count': sum(len(orders) for orders in self.stop_loss_orders.values()),
                'users_with_stop_losses': len(self.stop_loss_orders),
                'emergency_stops_active': len(self.emergency_stops),
                'risk_thresholds': self.risk_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}")
            return {}
    
    def stop(self):
        """Stop risk monitoring"""
        self.monitoring_active = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
        logger.info("RiskMonitor stopped")
    
    def start(self):
        """Start risk monitoring"""
        self.monitoring_active = True
        self._start_monitoring()
        logger.info("RiskMonitor started")

# Global risk monitor instance
risk_monitor = RiskMonitor()