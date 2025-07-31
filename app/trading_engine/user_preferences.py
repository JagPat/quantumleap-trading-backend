"""
User Preferences System
Manages user preferences for trading strategies, notifications, and risk parameters
"""
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

from .models import RiskParameters
from .event_bus import event_bus, EventType, TradingEvent, EventHandler
from .monitoring import trading_monitor, time_async_operation

logger = logging.getLogger(__name__)

class PreferenceCategory(str, Enum):
    """Categories of user preferences"""
    TRADING = "TRADING"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    NOTIFICATIONS = "NOTIFICATIONS"
    STRATEGY = "STRATEGY"
    MARKET_DATA = "MARKET_DATA"
    PERFORMANCE = "PERFORMANCE"

class NotificationChannel(str, Enum):
    """Notification channels"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class NotificationPreference:
    """Notification preference configuration"""
    event_type: str
    channels: List[NotificationChannel]
    priority: NotificationPriority
    enabled: bool = True
    throttle_minutes: int = 0  # Minimum minutes between notifications
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'channels': [c.value for c in self.channels],
            'priority': self.priority.value,
            'enabled': self.enabled,
            'throttle_minutes': self.throttle_minutes,
            'conditions': self.conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationPreference':
        return cls(
            event_type=data['event_type'],
            channels=[NotificationChannel(c) for c in data['channels']],
            priority=NotificationPriority(data['priority']),
            enabled=data.get('enabled', True),
            throttle_minutes=data.get('throttle_minutes', 0),
            conditions=data.get('conditions', {})
        )

@dataclass
class TradingPreferences:
    """Trading-specific preferences"""
    auto_execute_signals: bool = True
    min_confidence_threshold: float = 0.7
    max_daily_trades: int = 50
    max_concurrent_positions: int = 10
    preferred_order_type: str = "MARKET"
    enable_after_hours_trading: bool = False
    enable_pre_market_trading: bool = False
    default_position_size_percent: float = 2.0
    enable_partial_fills: bool = True
    order_timeout_minutes: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingPreferences':
        return cls(**data)

@dataclass
class StrategyPreferences:
    """Strategy-specific preferences"""
    auto_deploy_optimized_strategies: bool = False
    enable_strategy_suggestions: bool = True
    max_strategies_per_user: int = 5
    strategy_performance_review_days: int = 30
    auto_pause_underperforming: bool = True
    underperformance_threshold: float = -0.05  # -5%
    enable_strategy_diversification: bool = True
    max_sector_concentration: float = 0.3  # 30%
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyPreferences':
        return cls(**data)

@dataclass
class MarketDataPreferences:
    """Market data preferences"""
    enable_real_time_data: bool = True
    data_refresh_interval_seconds: int = 1
    enable_extended_hours_data: bool = False
    preferred_data_sources: List[str] = field(default_factory=lambda: ["primary"])
    enable_level2_data: bool = False
    enable_options_data: bool = False
    enable_futures_data: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketDataPreferences':
        return cls(**data)

@dataclass
class PerformancePreferences:
    """Performance tracking preferences"""
    enable_real_time_pnl: bool = True
    pnl_update_interval_seconds: int = 5
    enable_performance_alerts: bool = True
    daily_pnl_alert_threshold: float = 0.05  # 5%
    enable_drawdown_alerts: bool = True
    max_drawdown_alert_threshold: float = 0.1  # 10%
    enable_benchmark_comparison: bool = True
    benchmark_symbol: str = "NIFTY50"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformancePreferences':
        return cls(**data)

@dataclass
class UserPreferences:
    """Complete user preferences"""
    user_id: str
    trading: TradingPreferences = field(default_factory=TradingPreferences)
    risk_management: RiskParameters = field(default_factory=RiskParameters)
    notifications: List[NotificationPreference] = field(default_factory=list)
    strategy: StrategyPreferences = field(default_factory=StrategyPreferences)
    market_data: MarketDataPreferences = field(default_factory=MarketDataPreferences)
    performance: PerformancePreferences = field(default_factory=PerformancePreferences)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'trading': self.trading.to_dict(),
            'risk_management': asdict(self.risk_management),
            'notifications': [n.to_dict() for n in self.notifications],
            'strategy': self.strategy.to_dict(),
            'market_data': self.market_data.to_dict(),
            'performance': self.performance.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        return cls(
            user_id=data['user_id'],
            trading=TradingPreferences.from_dict(data.get('trading', {})),
            risk_management=RiskParameters(**data.get('risk_management', {})),
            notifications=[NotificationPreference.from_dict(n) for n in data.get('notifications', [])],
            strategy=StrategyPreferences.from_dict(data.get('strategy', {})),
            market_data=MarketDataPreferences.from_dict(data.get('market_data', {})),
            performance=PerformancePreferences.from_dict(data.get('performance', {})),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )

class UserPreferencesManager:
    """
    Manages user preferences and their dynamic application to trading systems
    """
    
    def __init__(self):
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.preference_cache: Dict[str, Dict[str, Any]] = {}
        self.notification_throttle: Dict[str, datetime] = {}
        
        # Default notification preferences
        self.default_notifications = self._create_default_notifications()
        
        # Register event handlers
        self._register_event_handlers()
        
        logger.info("UserPreferencesManager initialized")
    
    def _create_default_notifications(self) -> List[NotificationPreference]:
        """Create default notification preferences"""
        return [
            NotificationPreference(
                event_type="ORDER_FILLED",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
                priority=NotificationPriority.MEDIUM,
                throttle_minutes=0
            ),
            NotificationPreference(
                event_type="ORDER_REJECTED",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.EMAIL],
                priority=NotificationPriority.HIGH,
                throttle_minutes=0
            ),
            NotificationPreference(
                event_type="STRATEGY_PAUSED",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.EMAIL],
                priority=NotificationPriority.HIGH,
                throttle_minutes=5
            ),
            NotificationPreference(
                event_type="EMERGENCY_STOP",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.EMAIL, NotificationChannel.SMS],
                priority=NotificationPriority.CRITICAL,
                throttle_minutes=0
            ),
            NotificationPreference(
                event_type="RISK_VIOLATION",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.EMAIL],
                priority=NotificationPriority.HIGH,
                throttle_minutes=10
            ),
            NotificationPreference(
                event_type="PERFORMANCE_ALERT",
                channels=[NotificationChannel.IN_APP, NotificationChannel.PUSH],
                priority=NotificationPriority.MEDIUM,
                throttle_minutes=30
            )
        ]
    
    def _register_event_handlers(self):
        """Register event handlers for preference updates"""
        class PreferenceUpdateHandler(EventHandler):
            def __init__(self, preferences_manager):
                super().__init__("preference_update_handler", [EventType.USER_ACTION])
                self.preferences_manager = preferences_manager
            
            async def handle_event(self, event: TradingEvent) -> bool:
                try:
                    if event.data.get('action_type') == 'preference_update':
                        await self.preferences_manager._handle_preference_update_event(event)
                    return True
                except Exception as e:
                    logger.error(f"Error handling preference update event: {e}")
                    return False
        
        # Register the handler
        handler = PreferenceUpdateHandler(self)
        event_bus.register_handler(handler)
    
    async def _handle_preference_update_event(self, event: TradingEvent):
        """Handle preference update event from event bus"""
        try:
            data = event.data
            user_id = event.user_id
            category = data.get('category')
            updates = data.get('updates', {})
            
            await self.update_preferences(user_id, category, updates)
            
        except Exception as e:
            logger.error(f"Error handling preference update event: {e}")
    
    @time_async_operation("get_user_preferences")
    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """
        Get user preferences, creating defaults if not exists
        
        Args:
            user_id: User ID
            
        Returns:
            UserPreferences object
        """
        try:
            if user_id not in self.user_preferences:
                # Create default preferences
                preferences = UserPreferences(
                    user_id=user_id,
                    notifications=self.default_notifications.copy()
                )
                self.user_preferences[user_id] = preferences
                
                # Cache preferences
                self.preference_cache[user_id] = preferences.to_dict()
                
                logger.info(f"Created default preferences for user {user_id}")
            
            return self.user_preferences[user_id]
            
        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            # Return default preferences on error
            return UserPreferences(user_id=user_id, notifications=self.default_notifications.copy())
    
    @time_async_operation("update_preferences")
    async def update_preferences(self, user_id: str, category: str, updates: Dict[str, Any]) -> bool:
        """
        Update user preferences dynamically
        
        Args:
            user_id: User ID
            category: Preference category to update
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            old_preferences = preferences.to_dict()
            
            # Apply updates based on category
            if category == PreferenceCategory.TRADING.value:
                for key, value in updates.items():
                    if hasattr(preferences.trading, key):
                        setattr(preferences.trading, key, value)
            
            elif category == PreferenceCategory.RISK_MANAGEMENT.value:
                for key, value in updates.items():
                    if hasattr(preferences.risk_management, key):
                        setattr(preferences.risk_management, key, value)
            
            elif category == PreferenceCategory.NOTIFICATIONS.value:
                await self._update_notification_preferences(preferences, updates)
            
            elif category == PreferenceCategory.STRATEGY.value:
                for key, value in updates.items():
                    if hasattr(preferences.strategy, key):
                        setattr(preferences.strategy, key, value)
            
            elif category == PreferenceCategory.MARKET_DATA.value:
                for key, value in updates.items():
                    if hasattr(preferences.market_data, key):
                        setattr(preferences.market_data, key, value)
            
            elif category == PreferenceCategory.PERFORMANCE.value:
                for key, value in updates.items():
                    if hasattr(preferences.performance, key):
                        setattr(preferences.performance, key, value)
            
            # Update timestamp
            preferences.updated_at = datetime.now()
            
            # Update cache
            self.preference_cache[user_id] = preferences.to_dict()
            
            # Apply changes to live systems
            await self._apply_preference_changes(user_id, category, old_preferences, preferences.to_dict())
            
            # Publish preference update event
            await self._publish_preference_update(user_id, category, updates)
            
            trading_monitor.increment_counter("preference_updates")
            logger.info(f"Updated {category} preferences for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}")
            return False
    
    async def _update_notification_preferences(self, preferences: UserPreferences, updates: Dict[str, Any]):
        """Update notification preferences"""
        try:
            if 'add' in updates:
                # Add new notification preference
                new_pref_data = updates['add']
                new_pref = NotificationPreference.from_dict(new_pref_data)
                preferences.notifications.append(new_pref)
            
            if 'update' in updates:
                # Update existing notification preference
                event_type = updates['update']['event_type']
                update_data = updates['update']['data']
                
                for pref in preferences.notifications:
                    if pref.event_type == event_type:
                        for key, value in update_data.items():
                            if hasattr(pref, key):
                                if key == 'channels':
                                    pref.channels = [NotificationChannel(c) for c in value]
                                elif key == 'priority':
                                    pref.priority = NotificationPriority(value)
                                else:
                                    setattr(pref, key, value)
                        break
            
            if 'remove' in updates:
                # Remove notification preference
                event_type = updates['remove']
                preferences.notifications = [
                    pref for pref in preferences.notifications 
                    if pref.event_type != event_type
                ]
            
        except Exception as e:
            logger.error(f"Error updating notification preferences: {e}")
    
    async def _apply_preference_changes(self, user_id: str, category: str, 
                                      old_prefs: Dict[str, Any], new_prefs: Dict[str, Any]):
        """Apply preference changes to live trading systems"""
        try:
            if category == PreferenceCategory.RISK_MANAGEMENT.value:
                await self._apply_risk_preference_changes(user_id, old_prefs, new_prefs)
            
            elif category == PreferenceCategory.TRADING.value:
                await self._apply_trading_preference_changes(user_id, old_prefs, new_prefs)
            
            elif category == PreferenceCategory.STRATEGY.value:
                await self._apply_strategy_preference_changes(user_id, old_prefs, new_prefs)
            
            elif category == PreferenceCategory.MARKET_DATA.value:
                await self._apply_market_data_preference_changes(user_id, old_prefs, new_prefs)
            
        except Exception as e:
            logger.error(f"Error applying preference changes: {e}")
    
    async def _apply_risk_preference_changes(self, user_id: str, old_prefs: Dict[str, Any], new_prefs: Dict[str, Any]):
        """Apply risk management preference changes"""
        try:
            # Dynamic import to avoid circular imports
            from .risk_engine import risk_engine
            
            old_risk = old_prefs.get('risk_management', {})
            new_risk = new_prefs.get('risk_management', {})
            
            # Update risk engine with new parameters
            risk_params = RiskParameters(**new_risk)
            risk_engine.update_user_risk_params(user_id, risk_params)
            
            # Check if any critical risk parameters changed
            critical_changes = []
            if old_risk.get('max_position_size_percent') != new_risk.get('max_position_size_percent'):
                critical_changes.append('max_position_size_percent')
            
            if old_risk.get('max_drawdown_percent') != new_risk.get('max_drawdown_percent'):
                critical_changes.append('max_drawdown_percent')
            
            if critical_changes:
                # Create alert for critical risk parameter changes
                trading_monitor.create_alert(
                    "WARNING",
                    "Critical Risk Parameters Changed",
                    f"User {user_id} changed critical risk parameters: {', '.join(critical_changes)}",
                    "user_preferences",
                    user_id
                )
            
        except Exception as e:
            logger.error(f"Error applying risk preference changes: {e}")
    
    async def _apply_trading_preference_changes(self, user_id: str, old_prefs: Dict[str, Any], new_prefs: Dict[str, Any]):
        """Apply trading preference changes"""
        try:
            old_trading = old_prefs.get('trading', {})
            new_trading = new_prefs.get('trading', {})
            
            # Check if auto-execution was disabled
            if (old_trading.get('auto_execute_signals', True) and 
                not new_trading.get('auto_execute_signals', True)):
                
                # Pause all active strategies if auto-execution is disabled
                from .strategy_manager import strategy_manager
                user_strategies = await strategy_manager.get_user_strategies(user_id)
                
                for strategy in user_strategies:
                    if strategy['status'] == 'ACTIVE':
                        await strategy_manager.pause_strategy(
                            strategy['strategy_id'],
                            "Auto-execution disabled by user preference"
                        )
            
            # Check if confidence threshold changed significantly
            old_threshold = old_trading.get('min_confidence_threshold', 0.7)
            new_threshold = new_trading.get('min_confidence_threshold', 0.7)
            
            if abs(old_threshold - new_threshold) > 0.1:  # 10% change
                trading_monitor.create_alert(
                    "INFO",
                    "Confidence Threshold Changed",
                    f"User {user_id} changed confidence threshold from {old_threshold} to {new_threshold}",
                    "user_preferences",
                    user_id
                )
            
        except Exception as e:
            logger.error(f"Error applying trading preference changes: {e}")
    
    async def _apply_strategy_preference_changes(self, user_id: str, old_prefs: Dict[str, Any], new_prefs: Dict[str, Any]):
        """Apply strategy preference changes"""
        try:
            old_strategy = old_prefs.get('strategy', {})
            new_strategy = new_prefs.get('strategy', {})
            
            # Check if auto-pause underperforming strategies setting changed
            old_auto_pause = old_strategy.get('auto_pause_underperforming', True)
            new_auto_pause = new_strategy.get('auto_pause_underperforming', True)
            
            if old_auto_pause != new_auto_pause:
                action = "enabled" if new_auto_pause else "disabled"
                trading_monitor.create_alert(
                    "INFO",
                    "Auto-Pause Setting Changed",
                    f"User {user_id} {action} auto-pause for underperforming strategies",
                    "user_preferences",
                    user_id
                )
            
        except Exception as e:
            logger.error(f"Error applying strategy preference changes: {e}")
    
    async def _apply_market_data_preference_changes(self, user_id: str, old_prefs: Dict[str, Any], new_prefs: Dict[str, Any]):
        """Apply market data preference changes"""
        try:
            old_market_data = old_prefs.get('market_data', {})
            new_market_data = new_prefs.get('market_data', {})
            
            # Check if real-time data setting changed
            old_real_time = old_market_data.get('enable_real_time_data', True)
            new_real_time = new_market_data.get('enable_real_time_data', True)
            
            if old_real_time != new_real_time:
                # Update market data subscriptions
                from .market_data_manager import market_data_manager
                
                if new_real_time:
                    # Enable real-time data for user
                    await market_data_manager.enable_user_real_time_data(user_id)
                else:
                    # Disable real-time data for user
                    await market_data_manager.disable_user_real_time_data(user_id)
            
        except Exception as e:
            logger.error(f"Error applying market data preference changes: {e}")
    
    async def _publish_preference_update(self, user_id: str, category: str, updates: Dict[str, Any]):
        """Publish preference update event"""
        try:
            update_event = TradingEvent(
                id=f"preference_update_{user_id}_{category}_{datetime.now().timestamp()}",
                event_type=EventType.USER_ACTION,
                user_id=user_id,
                data={
                    'action_type': 'preference_updated',
                    'category': category,
                    'updates': updates,
                    'updated_at': datetime.now().isoformat()
                },
                priority=event_bus.EventPriority.NORMAL
            )
            
            await event_bus.publish_event(update_event)
            
        except Exception as e:
            logger.error(f"Error publishing preference update: {e}")
    
    async def should_send_notification(self, user_id: str, event_type: str, 
                                     event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if notification should be sent based on user preferences
        
        Args:
            user_id: User ID
            event_type: Type of event
            event_data: Event data for condition checking
            
        Returns:
            Dictionary with notification decision and details
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            
            # Find notification preference for this event type
            notification_pref = None
            for pref in preferences.notifications:
                if pref.event_type == event_type:
                    notification_pref = pref
                    break
            
            if not notification_pref or not notification_pref.enabled:
                return {
                    'should_send': False,
                    'reason': 'Notification disabled for this event type'
                }
            
            # Check throttling
            throttle_key = f"{user_id}_{event_type}"
            if notification_pref.throttle_minutes > 0:
                last_sent = self.notification_throttle.get(throttle_key)
                if last_sent:
                    time_since_last = datetime.now() - last_sent
                    if time_since_last.total_seconds() < (notification_pref.throttle_minutes * 60):
                        return {
                            'should_send': False,
                            'reason': f'Throttled for {notification_pref.throttle_minutes} minutes'
                        }
            
            # Check conditions
            if notification_pref.conditions:
                if not self._check_notification_conditions(notification_pref.conditions, event_data):
                    return {
                        'should_send': False,
                        'reason': 'Notification conditions not met'
                    }
            
            # Update throttle timestamp
            self.notification_throttle[throttle_key] = datetime.now()
            
            return {
                'should_send': True,
                'channels': notification_pref.channels,
                'priority': notification_pref.priority,
                'preference': notification_pref.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error checking notification preference: {e}")
            return {
                'should_send': False,
                'reason': f'Error checking preferences: {str(e)}'
            }
    
    def _check_notification_conditions(self, conditions: Dict[str, Any], event_data: Dict[str, Any]) -> bool:
        """Check if notification conditions are met"""
        try:
            for condition_key, condition_value in conditions.items():
                if condition_key not in event_data:
                    return False
                
                event_value = event_data[condition_key]
                
                # Handle different condition types
                if isinstance(condition_value, dict):
                    # Range or comparison conditions
                    if 'min' in condition_value and event_value < condition_value['min']:
                        return False
                    if 'max' in condition_value and event_value > condition_value['max']:
                        return False
                    if 'equals' in condition_value and event_value != condition_value['equals']:
                        return False
                else:
                    # Direct value comparison
                    if event_value != condition_value:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification conditions: {e}")
            return False
    
    # Public API methods
    
    async def get_trading_preferences(self, user_id: str) -> TradingPreferences:
        """Get trading preferences for a user"""
        preferences = await self.get_user_preferences(user_id)
        return preferences.trading
    
    async def get_risk_preferences(self, user_id: str) -> RiskParameters:
        """Get risk management preferences for a user"""
        preferences = await self.get_user_preferences(user_id)
        return preferences.risk_management
    
    async def get_notification_preferences(self, user_id: str) -> List[NotificationPreference]:
        """Get notification preferences for a user"""
        preferences = await self.get_user_preferences(user_id)
        return preferences.notifications
    
    async def update_trading_preferences(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update trading preferences"""
        return await self.update_preferences(user_id, PreferenceCategory.TRADING.value, updates)
    
    async def update_risk_preferences(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update risk management preferences"""
        return await self.update_preferences(user_id, PreferenceCategory.RISK_MANAGEMENT.value, updates)
    
    async def update_notification_preferences(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update notification preferences"""
        return await self.update_preferences(user_id, PreferenceCategory.NOTIFICATIONS.value, updates)
    
    def get_preference_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user preferences"""
        try:
            if user_id not in self.user_preferences:
                return {'error': 'User preferences not found'}
            
            preferences = self.user_preferences[user_id]
            
            return {
                'user_id': user_id,
                'trading': {
                    'auto_execute_signals': preferences.trading.auto_execute_signals,
                    'min_confidence_threshold': preferences.trading.min_confidence_threshold,
                    'max_daily_trades': preferences.trading.max_daily_trades,
                    'preferred_order_type': preferences.trading.preferred_order_type
                },
                'risk_management': {
                    'max_position_size_percent': preferences.risk_management.max_position_size_percent,
                    'max_drawdown_percent': preferences.risk_management.max_drawdown_percent,
                    'stop_loss_percent': preferences.risk_management.stop_loss_percent
                },
                'notifications': {
                    'total_preferences': len(preferences.notifications),
                    'enabled_preferences': len([p for p in preferences.notifications if p.enabled])
                },
                'last_updated': preferences.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting preference summary: {e}")
            return {'error': str(e)}

# Global user preferences manager instance
user_preferences_manager = UserPreferencesManager()