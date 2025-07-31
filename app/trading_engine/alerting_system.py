"""
Trading Engine Alerting and Notification System
Provides multi-channel alerts with intelligent prioritization and throttling
"""
import asyncio
import json
import smtplib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import sqlite3
import threading
from collections import defaultdict, deque
import time
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class AlertChannel(Enum):
    """Available alert channels"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WEBHOOK = "WEBHOOK"
    IN_APP = "IN_APP"

class AlertCategory(Enum):
    """Alert categories"""
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    STRATEGY_PERFORMANCE = "STRATEGY_PERFORMANCE"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    MARKET_CONDITIONS = "MARKET_CONDITIONS"
    USER_ACTIONS = "USER_ACTIONS"

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    category: AlertCategory
    severity: AlertSeverity
    condition: str  # JSON string describing the condition
    channels: List[AlertChannel]
    enabled: bool = True
    throttle_minutes: int = 5
    max_alerts_per_hour: int = 10
    user_id: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    user_id: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    data: Dict[str, Any]
    channels: List[AlertChannel]
    created_at: datetime
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'user_id': self.user_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'channels': [c.value for c in self.channels],
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class AlertThrottler:
    """Manages alert throttling and rate limiting"""
    
    def __init__(self):
        self.alert_counts = defaultdict(lambda: defaultdict(int))  # rule_id -> hour -> count
        self.last_sent = {}  # rule_id -> timestamp
        self.lock = threading.Lock()
    
    def should_send_alert(self, rule: AlertRule) -> bool:
        """Check if alert should be sent based on throttling rules"""
        with self.lock:
            now = datetime.now()
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            
            # Check throttle time
            if rule.rule_id in self.last_sent:
                time_since_last = now - self.last_sent[rule.rule_id]
                if time_since_last.total_seconds() < rule.throttle_minutes * 60:
                    return False
            
            # Check hourly limit
            current_count = self.alert_counts[rule.rule_id][current_hour]
            if current_count >= rule.max_alerts_per_hour:
                return False
            
            # Update counters
            self.alert_counts[rule.rule_id][current_hour] += 1
            self.last_sent[rule.rule_id] = now
            
            # Clean old entries
            self._cleanup_old_entries()
            
            return True
    
    def _cleanup_old_entries(self):
        """Clean up old throttling entries"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for rule_id in list(self.alert_counts.keys()):
            for hour in list(self.alert_counts[rule_id].keys()):
                if hour < cutoff_time:
                    del self.alert_counts[rule_id][hour]
            
            if not self.alert_counts[rule_id]:
                del self.alert_counts[rule_id]

class AlertConditionEvaluator:
    """Evaluates alert conditions against data"""
    
    def __init__(self):
        self.operators = {
            'gt': lambda x, y: x > y,
            'gte': lambda x, y: x >= y,
            'lt': lambda x, y: x < y,
            'lte': lambda x, y: x <= y,
            'eq': lambda x, y: x == y,
            'ne': lambda x, y: x != y,
            'in': lambda x, y: x in y,
            'not_in': lambda x, y: x not in y,
            'contains': lambda x, y: y in x,
            'starts_with': lambda x, y: str(x).startswith(str(y)),
            'ends_with': lambda x, y: str(x).endswith(str(y))
        }
    
    def evaluate(self, condition: str, data: Dict[str, Any]) -> bool:
        """Evaluate condition against data"""
        try:
            condition_obj = json.loads(condition)
            return self._evaluate_condition(condition_obj, data)
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _evaluate_condition(self, condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Recursively evaluate condition"""
        if 'and' in condition:
            return all(self._evaluate_condition(c, data) for c in condition['and'])
        
        if 'or' in condition:
            return any(self._evaluate_condition(c, data) for c in condition['or'])
        
        if 'not' in condition:
            return not self._evaluate_condition(condition['not'], data)
        
        # Simple condition
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not all([field, operator]):
            return False
        
        data_value = self._get_nested_value(data, field)
        if data_value is None:
            return False
        
        op_func = self.operators.get(operator)
        if not op_func:
            return False
        
        return op_func(data_value, value)
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """Get nested value from data using dot notation"""
        keys = field.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value

class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send_alert(self, alert: Alert, recipient: str) -> bool:
        """Send alert via email"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = recipient
            msg['Subject'] = f"[{alert.severity.value}] {alert.title}"
            
            # Create HTML body
            html_body = self._create_html_body(alert)
            msg.attach(MimeText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_html_body(self, alert: Alert) -> str:
        """Create HTML email body"""
        severity_colors = {
            AlertSeverity.CRITICAL: '#dc3545',
            AlertSeverity.HIGH: '#fd7e14',
            AlertSeverity.MEDIUM: '#ffc107',
            AlertSeverity.LOW: '#28a745',
            AlertSeverity.INFO: '#17a2b8'
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        
        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">{alert.title}</h2>
                    <p style="margin: 5px 0 0 0;">Severity: {alert.severity.value}</p>
                </div>
                <div style="background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px;">
                    <p><strong>Category:</strong> {alert.category.value}</p>
                    <p><strong>Time:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Message:</strong></p>
                    <div style="background-color: white; padding: 15px; border-radius: 3px; border-left: 4px solid {color};">
                        {alert.message}
                    </div>
                    {self._format_alert_data(alert.data)}
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_alert_data(self, data: Dict[str, Any]) -> str:
        """Format alert data for email"""
        if not data:
            return ""
        
        html = "<p><strong>Additional Data:</strong></p><ul>"
        for key, value in data.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        return html

class SMSNotifier:
    """SMS notification handler (mock implementation)"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    async def send_alert(self, alert: Alert, phone_number: str) -> bool:
        """Send alert via SMS"""
        try:
            # Mock SMS implementation
            message = f"[{alert.severity.value}] {alert.title}: {alert.message}"
            
            # In real implementation, integrate with SMS provider (Twilio, AWS SNS, etc.)
            logger.info(f"SMS alert sent to {phone_number}: {message[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
            return False

class PushNotifier:
    """Push notification handler (mock implementation)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def send_alert(self, alert: Alert, device_token: str) -> bool:
        """Send push notification"""
        try:
            # Mock push notification implementation
            payload = {
                'title': alert.title,
                'body': alert.message,
                'data': alert.data
            }
            
            # In real implementation, integrate with push service (FCM, APNS, etc.)
            logger.info(f"Push notification sent to device: {payload}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

class WebhookNotifier:
    """Webhook notification handler"""
    
    def __init__(self):
        self.session = None
    
    async def send_alert(self, alert: Alert, webhook_url: str) -> bool:
        """Send alert via webhook"""
        try:
            import aiohttp
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = alert.to_dict()
            
            async with self.session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Webhook alert sent to {webhook_url}")
                    return True
                else:
                    logger.error(f"Webhook failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False

class AlertingSystem:
    """Main alerting and notification system"""
    
    def __init__(self, db_path: str = "trading_alerts.db"):
        self.db_path = db_path
        self.rules: Dict[str, AlertRule] = {}
        self.throttler = AlertThrottler()
        self.condition_evaluator = AlertConditionEvaluator()
        self.alert_queue = asyncio.Queue()
        self.processing_task = None
        self.user_preferences = defaultdict(dict)
        
        # Initialize notifiers (with mock configurations)
        self.notifiers = {
            AlertChannel.EMAIL: EmailNotifier(
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                username="alerts@quantumleap.com",
                password="app_password"
            ),
            AlertChannel.SMS: SMSNotifier(
                api_key="mock_api_key",
                api_secret="mock_api_secret"
            ),
            AlertChannel.PUSH: PushNotifier(api_key="mock_push_key"),
            AlertChannel.WEBHOOK: WebhookNotifier()
        }
        
        self._init_database()
        self._load_rules()
        self._start_processing()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    channels TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    throttle_minutes INTEGER DEFAULT 5,
                    max_alerts_per_hour INTEGER DEFAULT 10,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT NOT NULL,
                    channels TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules (rule_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    address TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    PRIMARY KEY (user_id, channel)
                )
            """)
    
    def _load_rules(self):
        """Load alert rules from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM alert_rules WHERE enabled = 1")
            for row in cursor.fetchall():
                rule = AlertRule(
                    rule_id=row[0],
                    name=row[1],
                    category=AlertCategory(row[2]),
                    severity=AlertSeverity(row[3]),
                    condition=row[4],
                    channels=[AlertChannel(c) for c in json.loads(row[5])],
                    enabled=bool(row[6]),
                    throttle_minutes=row[7],
                    max_alerts_per_hour=row[8],
                    user_id=row[9],
                    created_at=datetime.fromisoformat(row[10])
                )
                self.rules[rule.rule_id] = rule
    
    def _start_processing(self):
        """Start alert processing task"""
        if not self.processing_task:
            self.processing_task = asyncio.create_task(self._process_alerts())
    
    async def _process_alerts(self):
        """Process alerts from queue"""
        while True:
            try:
                alert = await self.alert_queue.get()
                await self._send_alert(alert)
                self.alert_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
    
    def add_rule(self, rule: AlertRule) -> bool:
        """Add new alert rule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO alert_rules 
                    (rule_id, name, category, severity, condition, channels, enabled, 
                     throttle_minutes, max_alerts_per_hour, user_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id, rule.name, rule.category.value, rule.severity.value,
                    rule.condition, json.dumps([c.value for c in rule.channels]),
                    rule.enabled, rule.throttle_minutes, rule.max_alerts_per_hour,
                    rule.user_id, rule.created_at.isoformat()
                ))
            
            self.rules[rule.rule_id] = rule
            logger.info(f"Added alert rule: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add alert rule: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove alert rule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,))
            
            if rule_id in self.rules:
                del self.rules[rule_id]
            
            logger.info(f"Removed alert rule: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove alert rule: {e}")
            return False
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, str]) -> bool:
        """Update user notification preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clear existing preferences
                conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
                
                # Add new preferences
                for channel, address in preferences.items():
                    if channel in [c.value for c in AlertChannel]:
                        conn.execute("""
                            INSERT INTO user_preferences (user_id, channel, address, enabled)
                            VALUES (?, ?, ?, 1)
                        """, (user_id, channel, address))
            
            self.user_preferences[user_id] = preferences
            logger.info(f"Updated preferences for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return False
    
    async def trigger_alert(self, rule_id: str, data: Dict[str, Any], 
                          title: str = None, message: str = None) -> bool:
        """Trigger alert evaluation and sending"""
        try:
            if rule_id not in self.rules:
                logger.warning(f"Alert rule not found: {rule_id}")
                return False
            
            rule = self.rules[rule_id]
            
            # Check if rule is enabled
            if not rule.enabled:
                return False
            
            # Evaluate condition
            if not self.condition_evaluator.evaluate(rule.condition, data):
                return False
            
            # Check throttling
            if not self.throttler.should_send_alert(rule):
                logger.info(f"Alert throttled: {rule_id}")
                return False
            
            # Create alert
            alert_id = self._generate_alert_id(rule_id, data)
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule_id,
                user_id=rule.user_id or "system",
                category=rule.category,
                severity=rule.severity,
                title=title or f"{rule.category.value} Alert",
                message=message or f"Alert triggered for rule: {rule.name}",
                data=data,
                channels=rule.channels,
                created_at=datetime.now()
            )
            
            # Save alert to database
            self._save_alert(alert)
            
            # Queue for processing
            await self.alert_queue.put(alert)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
            return False
    
    def _generate_alert_id(self, rule_id: str, data: Dict[str, Any]) -> str:
        """Generate unique alert ID"""
        content = f"{rule_id}_{datetime.now().isoformat()}_{json.dumps(data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _save_alert(self, alert: Alert):
        """Save alert to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts 
                (alert_id, rule_id, user_id, category, severity, title, message, 
                 data, channels, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id, alert.rule_id, alert.user_id,
                alert.category.value, alert.severity.value,
                alert.title, alert.message, json.dumps(alert.data),
                json.dumps([c.value for c in alert.channels]),
                alert.created_at.isoformat()
            ))
    
    async def _send_alert(self, alert: Alert):
        """Send alert through configured channels"""
        user_prefs = self.user_preferences.get(alert.user_id, {})
        
        for channel in alert.channels:
            try:
                notifier = self.notifiers.get(channel)
                if not notifier:
                    continue
                
                # Get user's address for this channel
                address = user_prefs.get(channel.value)
                if not address:
                    continue
                
                # Send notification
                success = await notifier.send_alert(alert, address)
                
                if success:
                    logger.info(f"Alert sent via {channel.value}: {alert.alert_id}")
                else:
                    logger.error(f"Failed to send alert via {channel.value}: {alert.alert_id}")
                    
            except Exception as e:
                logger.error(f"Error sending alert via {channel.value}: {e}")
        
        # Update sent timestamp
        self._update_alert_sent(alert.alert_id)
    
    def _update_alert_sent(self, alert_id: str):
        """Update alert sent timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE alerts SET sent_at = ? WHERE alert_id = ?
            """, (datetime.now().isoformat(), alert_id))
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts SET acknowledged_at = ? WHERE alert_id = ?
                """, (datetime.now().isoformat(), alert_id))
            
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts SET resolved_at = ? WHERE alert_id = ?
                """, (datetime.now().isoformat(), alert_id))
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def get_alerts(self, user_id: str = None, category: AlertCategory = None,
                   severity: AlertSeverity = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get alerts with optional filtering"""
        try:
            query = "SELECT * FROM alerts WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if category:
                query += " AND category = ?"
                params.append(category.value)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity.value)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                alerts = []
                
                for row in cursor.fetchall():
                    alert_data = {
                        'alert_id': row[0],
                        'rule_id': row[1],
                        'user_id': row[2],
                        'category': row[3],
                        'severity': row[4],
                        'title': row[5],
                        'message': row[6],
                        'data': json.loads(row[7]),
                        'channels': json.loads(row[8]),
                        'created_at': row[9],
                        'sent_at': row[10],
                        'acknowledged_at': row[11],
                        'resolved_at': row[12]
                    }
                    alerts.append(alert_data)
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def get_alert_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                base_query = "SELECT COUNT(*) FROM alerts"
                params = []
                
                if user_id:
                    base_query += " WHERE user_id = ?"
                    params.append(user_id)
                
                # Total alerts
                cursor = conn.execute(base_query, params)
                total_alerts = cursor.fetchone()[0]
                
                # Alerts by severity
                severity_query = base_query.replace("COUNT(*)", "severity, COUNT(*)")
                if user_id:
                    severity_query += " GROUP BY severity"
                else:
                    severity_query += " WHERE 1=1 GROUP BY severity"
                
                cursor = conn.execute(severity_query, params)
                severity_counts = dict(cursor.fetchall())
                
                # Recent alerts (last 24 hours)
                recent_query = base_query + (" AND" if user_id else " WHERE") + " created_at > ?"
                recent_params = params + [datetime.now() - timedelta(hours=24)]
                cursor = conn.execute(recent_query, recent_params)
                recent_alerts = cursor.fetchone()[0]
                
                return {
                    'total_alerts': total_alerts,
                    'severity_breakdown': severity_counts,
                    'recent_alerts_24h': recent_alerts,
                    'active_rules': len([r for r in self.rules.values() if r.enabled])
                }
                
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {}
    
    async def shutdown(self):
        """Shutdown alerting system"""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Close webhook session
        if hasattr(self.notifiers[AlertChannel.WEBHOOK], 'session') and \
           self.notifiers[AlertChannel.WEBHOOK].session:
            await self.notifiers[AlertChannel.WEBHOOK].session.close()

# Global alerting system instance
alerting_system = AlertingSystem()

# Convenience functions for common alert types
async def send_risk_alert(user_id: str, risk_type: str, current_value: float, 
                         threshold: float, additional_data: Dict[str, Any] = None):
    """Send risk management alert"""
    data = {
        'risk_type': risk_type,
        'current_value': current_value,
        'threshold': threshold,
        'timestamp': datetime.now().isoformat()
    }
    if additional_data:
        data.update(additional_data)
    
    await alerting_system.trigger_alert(
        rule_id=f"risk_{risk_type}",
        data=data,
        title=f"Risk Alert: {risk_type}",
        message=f"Risk threshold exceeded: {current_value} > {threshold}"
    )

async def send_order_alert(user_id: str, order_id: str, status: str, 
                          additional_data: Dict[str, Any] = None):
    """Send order execution alert"""
    data = {
        'order_id': order_id,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    if additional_data:
        data.update(additional_data)
    
    await alerting_system.trigger_alert(
        rule_id=f"order_{status.lower()}",
        data=data,
        title=f"Order {status}",
        message=f"Order {order_id} status: {status}"
    )

async def send_strategy_alert(user_id: str, strategy_id: str, event_type: str,
                             additional_data: Dict[str, Any] = None):
    """Send strategy performance alert"""
    data = {
        'strategy_id': strategy_id,
        'event_type': event_type,
        'timestamp': datetime.now().isoformat()
    }
    if additional_data:
        data.update(additional_data)
    
    await alerting_system.trigger_alert(
        rule_id=f"strategy_{event_type.lower()}",
        data=data,
        title=f"Strategy Alert: {event_type}",
        message=f"Strategy {strategy_id}: {event_type}"
    )

async def send_system_alert(severity: AlertSeverity, component: str, message: str,
                           additional_data: Dict[str, Any] = None):
    """Send system health alert"""
    data = {
        'component': component,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    if additional_data:
        data.update(additional_data)
    
    await alerting_system.trigger_alert(
        rule_id=f"system_{component.lower()}",
        data=data,
        title=f"System Alert: {component}",
        message=message
    )