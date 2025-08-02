#!/usr/bin/env python3
"""
Database Alert Manager
Configurable alerting system with multiple notification channels and escalation
"""
import os
import sqlite3
import threading
import time
import logging
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import queue

# Email imports (optional, for email notifications)
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    """Notification channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"
    LOG = "log"
    CONSOLE = "console"

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    metric_type: str
    condition: str  # "greater_than", "less_than", "equals", "not_equals"
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 15
    max_alerts_per_hour: int = 10
    notification_channels: List[NotificationChannel] = None
    escalation_rules: List[str] = None
    
    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = [NotificationChannel.LOG]
        if self.escalation_rules is None:
            self.escalation_rules = []

@dataclass
class Alert:
    """Individual alert instance"""
    alert_id: str
    rule_id: str
    metric_type: str
    metric_value: float
    threshold: float
    severity: AlertSeverity
    status: AlertStatus
    message: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    escalation_level: int = 0
    notification_count: int = 0
    last_notification: Optional[datetime] = None

@dataclass
class NotificationConfig:
    """Notification channel configuration"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}

@dataclass
class EscalationRule:
    """Alert escalation rule"""
    rule_id: str
    name: str
    trigger_after_minutes: int
    target_severity: AlertSeverity
    notification_channels: List[NotificationChannel]
    enabled: bool = True

class AlertManager:
    """Database alert management system"""
    
    def __init__(self, database_path: str = None):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_alerts.db")
        
        # Alert management
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.escalation_rules: Dict[str, EscalationRule] = {}
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Threading
        self.alert_lock = threading.RLock()
        self.processing_thread = None
        self.is_processing = False
        
        # Alert suppression and grouping
        self.suppressed_rules: Set[str] = set()
        self.alert_groups: Dict[str, List[str]] = {}
        self.notification_queue = queue.Queue()
        
        # Rate limiting
        self.alert_counts: Dict[str, List[datetime]] = {}
        self.notification_counts: Dict[str, List[datetime]] = {}
        
        # Initialize database and default configurations
        self._initialize_alert_db()
        self._setup_default_configurations()
        self._load_existing_rules()
    
    def _initialize_alert_db(self):
        """Initialize alert database tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create alert rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_rules (
                        rule_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        metric_type TEXT NOT NULL,
                        condition TEXT NOT NULL,
                        threshold REAL NOT NULL,
                        severity TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        cooldown_minutes INTEGER DEFAULT 15,
                        max_alerts_per_hour INTEGER DEFAULT 10,
                        notification_channels TEXT,
                        escalation_rules TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        alert_id TEXT PRIMARY KEY,
                        rule_id TEXT NOT NULL,
                        metric_type TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        threshold REAL NOT NULL,
                        severity TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        acknowledged_at TEXT,
                        resolved_at TEXT,
                        acknowledged_by TEXT,
                        resolved_by TEXT,
                        escalation_level INTEGER DEFAULT 0,
                        notification_count INTEGER DEFAULT 0,
                        last_notification TEXT,
                        FOREIGN KEY (rule_id) REFERENCES alert_rules(rule_id)
                    )
                """)
                
                # Create escalation rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS escalation_rules (
                        rule_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        trigger_after_minutes INTEGER NOT NULL,
                        target_severity TEXT NOT NULL,
                        notification_channels TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Create notification configs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS notification_configs (
                        channel TEXT PRIMARY KEY,
                        enabled BOOLEAN DEFAULT TRUE,
                        config TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Create alert history table for analytics
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS alert_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        performed_by TEXT,
                        timestamp TEXT NOT NULL,
                        details TEXT
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_rule_id ON alerts(rule_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history(alert_id)")
                
                conn.commit()
                logger.info("✅ Alert database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize alert database: {e}")
            raise
    
    def _setup_default_configurations(self):
        """Setup default notification configurations"""
        # Default email configuration
        self.notification_configs[NotificationChannel.EMAIL] = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=False,  # Disabled by default, requires configuration
            config={
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": []
            }
        )
        
        # Default webhook configuration
        self.notification_configs[NotificationChannel.WEBHOOK] = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=False,
            config={
                "url": "",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "timeout": 30
            }
        )
        
        # Default Slack configuration
        self.notification_configs[NotificationChannel.SLACK] = NotificationConfig(
            channel=NotificationChannel.SLACK,
            enabled=False,
            config={
                "webhook_url": "",
                "channel": "#alerts",
                "username": "Database Monitor"
            }
        )
        
        # Log and console are always enabled
        self.notification_configs[NotificationChannel.LOG] = NotificationConfig(
            channel=NotificationChannel.LOG,
            enabled=True,
            config={}
        )
        
        self.notification_configs[NotificationChannel.CONSOLE] = NotificationConfig(
            channel=NotificationChannel.CONSOLE,
            enabled=True,
            config={}
        )
    
    def _load_existing_rules(self):
        """Load existing alert rules from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Load alert rules
                cursor.execute("SELECT * FROM alert_rules")
                for row in cursor.fetchall():
                    rule = AlertRule(
                        rule_id=row[0],
                        name=row[1],
                        description=row[2],
                        metric_type=row[3],
                        condition=row[4],
                        threshold=row[5],
                        severity=AlertSeverity(row[6]),
                        enabled=bool(row[7]),
                        cooldown_minutes=row[8],
                        max_alerts_per_hour=row[9],
                        notification_channels=[NotificationChannel(ch) for ch in json.loads(row[10] or "[]")],
                        escalation_rules=json.loads(row[11] or "[]")
                    )
                    self.alert_rules[rule.rule_id] = rule
                
                # Load escalation rules
                cursor.execute("SELECT * FROM escalation_rules")
                for row in cursor.fetchall():
                    escalation_rule = EscalationRule(
                        rule_id=row[0],
                        name=row[1],
                        trigger_after_minutes=row[2],
                        target_severity=AlertSeverity(row[3]),
                        notification_channels=[NotificationChannel(ch) for ch in json.loads(row[4])],
                        enabled=bool(row[5])
                    )
                    self.escalation_rules[escalation_rule.rule_id] = escalation_rule
                
                # Load active alerts
                cursor.execute("SELECT * FROM alerts WHERE status IN ('active', 'acknowledged')")
                for row in cursor.fetchall():
                    alert = Alert(
                        alert_id=row[0],
                        rule_id=row[1],
                        metric_type=row[2],
                        metric_value=row[3],
                        threshold=row[4],
                        severity=AlertSeverity(row[5]),
                        status=AlertStatus(row[6]),
                        message=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        acknowledged_at=datetime.fromisoformat(row[9]) if row[9] else None,
                        resolved_at=datetime.fromisoformat(row[10]) if row[10] else None,
                        acknowledged_by=row[11],
                        resolved_by=row[12],
                        escalation_level=row[13],
                        notification_count=row[14],
                        last_notification=datetime.fromisoformat(row[15]) if row[15] else None
                    )
                    self.active_alerts[alert.alert_id] = alert
                
                logger.info(f"✅ Loaded {len(self.alert_rules)} alert rules, {len(self.escalation_rules)} escalation rules, {len(self.active_alerts)} active alerts")
                
        except Exception as e:
            logger.error(f"Failed to load existing rules: {e}")
    
    def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule"""
        try:
            with self.alert_lock:
                if rule.rule_id in self.alert_rules:
                    raise ValueError(f"Alert rule {rule.rule_id} already exists")
                
                # Store in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO alert_rules 
                        (rule_id, name, description, metric_type, condition, threshold, 
                         severity, enabled, cooldown_minutes, max_alerts_per_hour, 
                         notification_channels, escalation_rules, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rule.rule_id,
                        rule.name,
                        rule.description,
                        rule.metric_type,
                        rule.condition,
                        rule.threshold,
                        rule.severity.value,
                        rule.enabled,
                        rule.cooldown_minutes,
                        rule.max_alerts_per_hour,
                        json.dumps([ch.value for ch in rule.notification_channels]),
                        json.dumps(rule.escalation_rules),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                
                # Store in memory
                self.alert_rules[rule.rule_id] = rule
                
                logger.info(f"✅ Created alert rule: {rule.rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create alert rule: {e}")
            return False
    
    def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing alert rule"""
        try:
            with self.alert_lock:
                if rule_id not in self.alert_rules:
                    raise ValueError(f"Alert rule {rule_id} not found")
                
                rule = self.alert_rules[rule_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                
                # Update in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE alert_rules SET 
                        name=?, description=?, metric_type=?, condition=?, threshold=?, 
                        severity=?, enabled=?, cooldown_minutes=?, max_alerts_per_hour=?, 
                        notification_channels=?, escalation_rules=?, updated_at=?
                        WHERE rule_id=?
                    """, (
                        rule.name,
                        rule.description,
                        rule.metric_type,
                        rule.condition,
                        rule.threshold,
                        rule.severity.value,
                        rule.enabled,
                        rule.cooldown_minutes,
                        rule.max_alerts_per_hour,
                        json.dumps([ch.value for ch in rule.notification_channels]),
                        json.dumps(rule.escalation_rules),
                        datetime.now().isoformat(),
                        rule_id
                    ))
                    conn.commit()
                
                logger.info(f"✅ Updated alert rule: {rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update alert rule: {e}")
            return False
    
    def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule"""
        try:
            with self.alert_lock:
                if rule_id not in self.alert_rules:
                    raise ValueError(f"Alert rule {rule_id} not found")
                
                # Delete from database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM alert_rules WHERE rule_id=?", (rule_id,))
                    conn.commit()
                
                # Remove from memory
                del self.alert_rules[rule_id]
                
                logger.info(f"✅ Deleted alert rule: {rule_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete alert rule: {e}")
            return False
    
    def evaluate_metrics(self, metrics: Dict[str, Any]):
        """Evaluate metrics against alert rules"""
        try:
            current_time = datetime.now()
            
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check if metric exists
                if rule.metric_type not in metrics:
                    continue
                
                metric_value = metrics[rule.metric_type]
                
                # Evaluate condition
                triggered = self._evaluate_condition(
                    metric_value, rule.condition, rule.threshold
                )
                
                if triggered:
                    # Check rate limiting
                    if self._is_rate_limited(rule_id, current_time):
                        continue
                    
                    # Check cooldown
                    if self._is_in_cooldown(rule_id, current_time):
                        continue
                    
                    # Create alert
                    alert = self._create_alert(rule, metric_value, current_time)
                    if alert:
                        self._process_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to evaluate metrics: {e}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition"""
        if condition == "greater_than":
            return value > threshold
        elif condition == "less_than":
            return value < threshold
        elif condition == "equals":
            return abs(value - threshold) < 0.001  # Float comparison
        elif condition == "not_equals":
            return abs(value - threshold) >= 0.001
        elif condition == "greater_equal":
            return value >= threshold
        elif condition == "less_equal":
            return value <= threshold
        else:
            logger.error(f"Unknown condition: {condition}")
            return False
    
    def _is_rate_limited(self, rule_id: str, current_time: datetime) -> bool:
        """Check if rule is rate limited"""
        rule = self.alert_rules[rule_id]
        
        # Clean old entries
        if rule_id not in self.alert_counts:
            self.alert_counts[rule_id] = []
        
        cutoff_time = current_time - timedelta(hours=1)
        self.alert_counts[rule_id] = [
            t for t in self.alert_counts[rule_id] if t > cutoff_time
        ]
        
        # Check limit
        return len(self.alert_counts[rule_id]) >= rule.max_alerts_per_hour
    
    def _is_in_cooldown(self, rule_id: str, current_time: datetime) -> bool:
        """Check if rule is in cooldown period"""
        rule = self.alert_rules[rule_id]
        
        # Find most recent alert for this rule
        recent_alerts = [
            alert for alert in self.active_alerts.values()
            if alert.rule_id == rule_id
        ]
        
        if not recent_alerts:
            return False
        
        most_recent = max(recent_alerts, key=lambda a: a.created_at)
        cooldown_end = most_recent.created_at + timedelta(minutes=rule.cooldown_minutes)
        
        return current_time < cooldown_end
    
    def _create_alert(self, rule: AlertRule, metric_value: float, current_time: datetime) -> Optional[Alert]:
        """Create a new alert"""
        try:
            # Generate alert ID
            alert_id = self._generate_alert_id(rule.rule_id, metric_value, current_time)
            
            # Check if similar alert already exists
            if alert_id in self.active_alerts:
                return None
            
            # Create alert message
            message = self._generate_alert_message(rule, metric_value)
            
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                metric_type=rule.metric_type,
                metric_value=metric_value,
                threshold=rule.threshold,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                message=message,
                created_at=current_time
            )
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None
    
    def _generate_alert_id(self, rule_id: str, metric_value: float, timestamp: datetime) -> str:
        """Generate unique alert ID"""
        content = f"{rule_id}_{metric_value}_{timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_alert_message(self, rule: AlertRule, metric_value: float) -> str:
        """Generate alert message"""
        return (f"{rule.severity.value.upper()}: {rule.name} - "
                f"{rule.metric_type} is {metric_value} (threshold: {rule.threshold}). "
                f"{rule.description}")
    
    def _process_alert(self, alert: Alert):
        """Process a new alert"""
        try:
            with self.alert_lock:
                # Store alert
                self.active_alerts[alert.alert_id] = alert
                self._store_alert(alert)
                
                # Record in rate limiting
                rule_id = alert.rule_id
                if rule_id not in self.alert_counts:
                    self.alert_counts[rule_id] = []
                self.alert_counts[rule_id].append(alert.created_at)
                
                # Queue notifications
                self._queue_notifications(alert)
                
                # Log alert history
                self._log_alert_action(alert.alert_id, "created", None, "Alert created")
                
                logger.info(f"🚨 Alert created: {alert.alert_id} - {alert.message}")
                
        except Exception as e:
            logger.error(f"Failed to process alert: {e}")
    
    def _store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alerts 
                    (alert_id, rule_id, metric_type, metric_value, threshold, severity, 
                     status, message, created_at, escalation_level, notification_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.rule_id,
                    alert.metric_type,
                    alert.metric_value,
                    alert.threshold,
                    alert.severity.value,
                    alert.status.value,
                    alert.message,
                    alert.created_at.isoformat(),
                    alert.escalation_level,
                    alert.notification_count
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    def _queue_notifications(self, alert: Alert):
        """Queue notifications for alert"""
        rule = self.alert_rules[alert.rule_id]
        
        for channel in rule.notification_channels:
            if channel in self.notification_configs and self.notification_configs[channel].enabled:
                self.notification_queue.put((alert, channel))
    
    def _log_alert_action(self, alert_id: str, action: str, performed_by: Optional[str], details: str):
        """Log alert action to history"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO alert_history (alert_id, action, performed_by, timestamp, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (alert_id, action, performed_by, datetime.now().isoformat(), details))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log alert action: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            with self.alert_lock:
                if alert_id not in self.active_alerts:
                    raise ValueError(f"Alert {alert_id} not found")
                
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                
                # Update in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE alerts SET status=?, acknowledged_at=?, acknowledged_by=?
                        WHERE alert_id=?
                    """, (
                        alert.status.value,
                        alert.acknowledged_at.isoformat(),
                        alert.acknowledged_by,
                        alert_id
                    ))
                    conn.commit()
                
                # Log action
                self._log_alert_action(alert_id, "acknowledged", acknowledged_by, "Alert acknowledged")
                
                logger.info(f"✅ Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        try:
            with self.alert_lock:
                if alert_id not in self.active_alerts:
                    raise ValueError(f"Alert {alert_id} not found")
                
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                alert.resolved_by = resolved_by
                
                # Update in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE alerts SET status=?, resolved_at=?, resolved_by=?
                        WHERE alert_id=?
                    """, (
                        alert.status.value,
                        alert.resolved_at.isoformat(),
                        alert.resolved_by,
                        alert_id
                    ))
                    conn.commit()
                
                # Remove from active alerts
                del self.active_alerts[alert_id]
                
                # Log action
                self._log_alert_action(alert_id, "resolved", resolved_by, "Alert resolved")
                
                logger.info(f"✅ Alert resolved: {alert_id} by {resolved_by}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def start_notification_processing(self):
        """Start notification processing thread"""
        try:
            if self.is_processing:
                logger.warning("Notification processing is already running")
                return
            
            self.is_processing = True
            self.processing_thread = threading.Thread(
                target=self._notification_processing_loop,
                daemon=True,
                name="AlertNotificationProcessor"
            )
            self.processing_thread.start()
            
            logger.info("✅ Alert notification processing started")
            
        except Exception as e:
            logger.error(f"Failed to start notification processing: {e}")
            self.is_processing = False
    
    def stop_notification_processing(self):
        """Stop notification processing"""
        try:
            if not self.is_processing:
                logger.warning("Notification processing is not running")
                return
            
            self.is_processing = False
            
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=10)
            
            logger.info("✅ Alert notification processing stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop notification processing: {e}")
    
    def _notification_processing_loop(self):
        """Process notification queue"""
        while self.is_processing:
            try:
                # Get notification from queue (with timeout)
                try:
                    alert, channel = self.notification_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Send notification
                success = self._send_notification(alert, channel)
                
                if success:
                    # Update notification count
                    alert.notification_count += 1
                    alert.last_notification = datetime.now()
                    
                    # Update in database
                    with sqlite3.connect(self.database_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE alerts SET notification_count=?, last_notification=?
                            WHERE alert_id=?
                        """, (
                            alert.notification_count,
                            alert.last_notification.isoformat(),
                            alert.alert_id
                        ))
                        conn.commit()
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in notification processing loop: {e}")
                time.sleep(1)
    
    def _send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send notification through specified channel"""
        try:
            config = self.notification_configs.get(channel)
            if not config or not config.enabled:
                return False
            
            if channel == NotificationChannel.LOG:
                return self._send_log_notification(alert)
            elif channel == NotificationChannel.CONSOLE:
                return self._send_console_notification(alert)
            elif channel == NotificationChannel.EMAIL:
                return self._send_email_notification(alert, config)
            elif channel == NotificationChannel.WEBHOOK:
                return self._send_webhook_notification(alert, config)
            elif channel == NotificationChannel.SLACK:
                return self._send_slack_notification(alert, config)
            else:
                logger.error(f"Unsupported notification channel: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification via {channel}: {e}")
            return False
    
    def _send_log_notification(self, alert: Alert) -> bool:
        """Send log notification"""
        logger.warning(f"ALERT: {alert.message}")
        return True
    
    def _send_console_notification(self, alert: Alert) -> bool:
        """Send console notification"""
        print(f"🚨 ALERT: {alert.message}")
        return True
    
    def _send_email_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send email notification"""
        try:
            if not EMAIL_AVAILABLE:
                logger.error("Email functionality not available (missing dependencies)")
                return False
            
            email_config = config.config
            
            if not all(key in email_config for key in ['smtp_server', 'username', 'password', 'from_email', 'to_emails']):
                logger.error("Incomplete email configuration")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"Database Alert: {alert.severity.value.upper()}"
            
            body = f"""
            Alert Details:
            - Alert ID: {alert.alert_id}
            - Severity: {alert.severity.value.upper()}
            - Metric: {alert.metric_type}
            - Value: {alert.metric_value}
            - Threshold: {alert.threshold}
            - Message: {alert.message}
            - Created: {alert.created_at}
            
            Please investigate and take appropriate action.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(email_config['smtp_server'], email_config.get('smtp_port', 587))
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email notification sent for alert: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_webhook_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send webhook notification"""
        try:
            webhook_config = config.config
            
            if 'url' not in webhook_config:
                logger.error("Webhook URL not configured")
                return False
            
            payload = {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "severity": alert.severity.value,
                "metric_type": alert.metric_type,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "status": alert.status.value
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config.get('headers', {}),
                timeout=webhook_config.get('timeout', 30)
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Webhook notification sent for alert: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    def _send_slack_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send Slack notification"""
        try:
            slack_config = config.config
            
            if 'webhook_url' not in slack_config:
                logger.error("Slack webhook URL not configured")
                return False
            
            # Create Slack message
            color = {
                AlertSeverity.INFO: "good",
                AlertSeverity.WARNING: "warning", 
                AlertSeverity.CRITICAL: "danger",
                AlertSeverity.EMERGENCY: "danger"
            }.get(alert.severity, "warning")
            
            payload = {
                "channel": slack_config.get('channel', '#alerts'),
                "username": slack_config.get('username', 'Database Monitor'),
                "attachments": [{
                    "color": color,
                    "title": f"Database Alert: {alert.severity.value.upper()}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Metric", "value": alert.metric_type, "short": True},
                        {"title": "Value", "value": str(alert.metric_value), "short": True},
                        {"title": "Threshold", "value": str(alert.threshold), "short": True},
                        {"title": "Alert ID", "value": alert.alert_id, "short": True}
                    ],
                    "timestamp": int(alert.created_at.timestamp())
                }]
            }
            
            response = requests.post(
                slack_config['webhook_url'],
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            
            logger.info(f"✅ Slack notification sent for alert: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def configure_notification_channel(self, channel: NotificationChannel, config: Dict[str, Any]) -> bool:
        """Configure notification channel"""
        try:
            if channel not in self.notification_configs:
                self.notification_configs[channel] = NotificationConfig(channel=channel)
            
            self.notification_configs[channel].config.update(config)
            self.notification_configs[channel].enabled = True
            
            # Store in database
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO notification_configs (channel, enabled, config, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    channel.value,
                    True,
                    json.dumps(self.notification_configs[channel].config),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            logger.info(f"✅ Configured notification channel: {channel.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure notification channel: {e}")
            return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts"""
        with self.alert_lock:
            alerts = list(self.active_alerts.values())
            
            if severity:
                alerts = [alert for alert in alerts if alert.severity == severity]
            
            return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Total alerts
                cursor.execute("SELECT COUNT(*) FROM alerts WHERE created_at > ?", (cutoff_time.isoformat(),))
                total_alerts = cursor.fetchone()[0]
                
                # Alerts by severity
                cursor.execute("""
                    SELECT severity, COUNT(*) FROM alerts 
                    WHERE created_at > ? GROUP BY severity
                """, (cutoff_time.isoformat(),))
                alerts_by_severity = dict(cursor.fetchall())
                
                # Alerts by status
                cursor.execute("""
                    SELECT status, COUNT(*) FROM alerts 
                    WHERE created_at > ? GROUP BY status
                """, (cutoff_time.isoformat(),))
                alerts_by_status = dict(cursor.fetchall())
                
                # Top alert rules
                cursor.execute("""
                    SELECT rule_id, COUNT(*) as count FROM alerts 
                    WHERE created_at > ? GROUP BY rule_id ORDER BY count DESC LIMIT 5
                """, (cutoff_time.isoformat(),))
                top_rules = cursor.fetchall()
                
                return {
                    "total_alerts": total_alerts,
                    "active_alerts": len(self.active_alerts),
                    "alerts_by_severity": alerts_by_severity,
                    "alerts_by_status": alerts_by_status,
                    "top_alert_rules": [{"rule_id": rule[0], "count": rule[1]} for rule in top_rules],
                    "time_period_hours": hours
                }
                
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {}
    
    def cleanup_old_alerts(self, days: int = 30):
        """Clean up old resolved alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Delete old resolved alerts
                cursor.execute("""
                    DELETE FROM alerts 
                    WHERE status = 'resolved' AND resolved_at < ?
                """, (cutoff_time.isoformat(),))
                alerts_deleted = cursor.rowcount
                
                # Delete old alert history
                cursor.execute("""
                    DELETE FROM alert_history 
                    WHERE timestamp < ?
                """, (cutoff_time.isoformat(),))
                history_deleted = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"✅ Cleaned up old alerts: {alerts_deleted} alerts, {history_deleted} history entries")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop_notification_processing()
        except:
            pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize alert manager
    alert_manager = AlertManager()
    
    # Create a test alert rule
    rule = AlertRule(
        rule_id="test_response_time",
        name="High Response Time",
        description="Database response time is too high",
        metric_type="response_time",
        condition="greater_than",
        threshold=100.0,
        severity=AlertSeverity.WARNING,
        notification_channels=[NotificationChannel.LOG, NotificationChannel.CONSOLE]
    )
    
    alert_manager.create_alert_rule(rule)
    
    # Start notification processing
    alert_manager.start_notification_processing()
    
    try:
        # Test with metrics that should trigger alert
        test_metrics = {
            "response_time": 150.0,  # Above threshold
            "connection_count": 5,
            "error_rate": 2.0
        }
        
        alert_manager.evaluate_metrics(test_metrics)
        
        # Wait for processing
        time.sleep(2)
        
        # Check active alerts
        active_alerts = alert_manager.get_active_alerts()
        print(f"Active alerts: {len(active_alerts)}")
        
        if active_alerts:
            alert = active_alerts[0]
            print(f"Alert: {alert.message}")
            
            # Acknowledge alert
            alert_manager.acknowledge_alert(alert.alert_id, "test_user")
            
            # Resolve alert
            alert_manager.resolve_alert(alert.alert_id, "test_user")
        
        # Get statistics
        stats = alert_manager.get_alert_statistics()
        print(f"Alert statistics: {stats}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping alert manager...")
    finally:
        alert_manager.stop_notification_processing()
        print("✅ Alert manager stopped")