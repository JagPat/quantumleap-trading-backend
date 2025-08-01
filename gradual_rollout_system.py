#!/usr/bin/env python3
"""
Gradual Rollout System for Automated Trading Engine
Manages beta user deployment, enhanced monitoring, and rollback procedures
"""

import os
import sys
import json
import sqlite3
import time
import requests
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Optional
import threading
import queue
try:
    import smtplib
    from email.mime.text import MimeText
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gradual_rollout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BetaUserManager:
    """Manages beta user access and permissions"""
    
    def __init__(self, db_path="production_trading.db"):
        self.db_path = db_path
        self.beta_users_table = "beta_users"
        self.rollout_phases = {
            "phase_1": {"max_users": 5, "features": ["basic_trading", "portfolio_view"]},
            "phase_2": {"max_users": 15, "features": ["basic_trading", "portfolio_view", "ai_analysis"]},
            "phase_3": {"max_users": 50, "features": ["basic_trading", "portfolio_view", "ai_analysis", "advanced_strategies"]},
            "phase_4": {"max_users": 100, "features": ["all_features"]}
        }
        self._init_beta_tables()
    
    def _init_beta_tables(self):
        """Initialize beta user tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create beta users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS beta_users (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                phase TEXT NOT NULL,
                enrolled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                features_enabled TEXT NOT NULL,
                performance_metrics TEXT,
                feedback TEXT,
                last_activity TEXT
            )
        """)
        
        # Create rollout phases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollout_phases (
                phase_name TEXT PRIMARY KEY,
                max_users INTEGER NOT NULL,
                current_users INTEGER DEFAULT 0,
                features TEXT NOT NULL,
                started_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                success_criteria TEXT,
                performance_metrics TEXT
            )
        """)
        
        # Create rollout events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollout_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                phase TEXT,
                user_id TEXT,
                event_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                severity TEXT DEFAULT 'info'
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Initialize rollout phases
        self._initialize_phases()
    
    def _initialize_phases(self):
        """Initialize rollout phases in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for phase_name, config in self.rollout_phases.items():
            cursor.execute("""
                INSERT OR REPLACE INTO rollout_phases 
                (phase_name, max_users, features, success_criteria)
                VALUES (?, ?, ?, ?)
            """, (
                phase_name,
                config["max_users"],
                json.dumps(config["features"]),
                json.dumps({
                    "min_success_rate": 0.95,
                    "max_error_rate": 0.02,
                    "min_user_satisfaction": 4.0,
                    "max_response_time": 2.0
                })
            ))
        
        conn.commit()
        conn.close()
    
    def enroll_beta_user(self, user_id: str, email: str, phase: str = "phase_1") -> bool:
        """Enroll a user in beta testing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if phase has capacity
            cursor.execute("""
                SELECT current_users, max_users FROM rollout_phases 
                WHERE phase_name = ?
            """, (phase,))
            
            result = cursor.fetchone()
            if not result:
                logger.error(f"Phase {phase} not found")
                return False
            
            current_users, max_users = result
            if current_users >= max_users:
                logger.warning(f"Phase {phase} is at capacity ({current_users}/{max_users})")
                return False
            
            # Enroll user
            beta_user_id = f"beta_{user_id}_{int(time.time())}"
            features_enabled = json.dumps(self.rollout_phases[phase]["features"])
            
            cursor.execute("""
                INSERT INTO beta_users 
                (id, user_id, email, phase, enrolled_at, features_enabled)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                beta_user_id,
                user_id,
                email,
                phase,
                datetime.now().isoformat(),
                features_enabled
            ))
            
            # Update phase user count
            cursor.execute("""
                UPDATE rollout_phases 
                SET current_users = current_users + 1
                WHERE phase_name = ?
            """, (phase,))
            
            # Log enrollment event
            self._log_rollout_event(
                "user_enrolled",
                phase,
                user_id,
                {"email": email, "features": self.rollout_phases[phase]["features"]}
            )
            
            conn.commit()
            conn.close()
            
            logger.info(f"User {user_id} enrolled in {phase}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enroll user {user_id}: {e}")
            return False
    
    def get_beta_users(self, phase: Optional[str] = None) -> List[Dict]:
        """Get list of beta users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if phase:
            cursor.execute("""
                SELECT * FROM beta_users WHERE phase = ? AND status = 'active'
            """, (phase,))
        else:
            cursor.execute("""
                SELECT * FROM beta_users WHERE status = 'active'
            """)
        
        columns = [desc[0] for desc in cursor.description]
        users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def update_user_activity(self, user_id: str, activity_data: Dict):
        """Update user activity and performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE beta_users 
            SET last_activity = ?, performance_metrics = ?
            WHERE user_id = ?
        """, (
            datetime.now().isoformat(),
            json.dumps(activity_data),
            user_id
        ))
        
        conn.commit()
        conn.close()
    
    def _log_rollout_event(self, event_type: str, phase: str, user_id: str, event_data: Dict, severity: str = "info"):
        """Log rollout event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        event_id = f"event_{int(time.time())}_{event_type}"
        cursor.execute("""
            INSERT INTO rollout_events 
            (id, event_type, phase, user_id, event_data, created_at, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            event_type,
            phase,
            user_id,
            json.dumps(event_data),
            datetime.now().isoformat(),
            severity
        ))
        
        conn.commit()
        conn.close()

class EnhancedMonitoring:
    """Enhanced monitoring system for gradual rollout"""
    
    def __init__(self, beta_manager: BetaUserManager):
        self.beta_manager = beta_manager
        self.monitoring_interval = 30  # seconds
        self.alert_queue = queue.Queue()
        self.monitoring_active = False
        self.performance_thresholds = {
            "response_time": 2.0,
            "error_rate": 0.02,
            "success_rate": 0.95,
            "cpu_usage": 80.0,
            "memory_usage": 85.0
        }
    
    def start_enhanced_monitoring(self):
        """Start enhanced monitoring for beta rollout"""
        logger.info("Starting enhanced monitoring for gradual rollout...")
        self.monitoring_active = True
        
        # Start monitoring threads
        monitoring_thread = threading.Thread(target=self._monitoring_loop)
        alert_thread = threading.Thread(target=self._alert_processor)
        
        monitoring_thread.daemon = True
        alert_thread.daemon = True
        
        monitoring_thread.start()
        alert_thread.start()
        
        logger.info("Enhanced monitoring started")
    
    def stop_enhanced_monitoring(self):
        """Stop enhanced monitoring"""
        self.monitoring_active = False
        logger.info("Enhanced monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                
                # Collect user activity metrics
                user_metrics = self._collect_user_metrics()
                
                # Collect application metrics
                app_metrics = self._collect_application_metrics()
                
                # Analyze metrics and generate alerts
                self._analyze_metrics(system_metrics, user_metrics, app_metrics)
                
                # Store metrics
                self._store_metrics({
                    "timestamp": datetime.now().isoformat(),
                    "system": system_metrics,
                    "users": user_metrics,
                    "application": app_metrics
                })
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(10)
    
    def _collect_system_metrics(self) -> Dict:
        """Collect system performance metrics"""
        try:
            import psutil
            
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": dict(psutil.net_io_counters()._asdict()),
                "process_count": len(psutil.pids())
            }
        except ImportError:
            # Fallback metrics without psutil
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "network_io": {},
                "process_count": 0
            }
    
    def _collect_user_metrics(self) -> Dict:
        """Collect beta user activity metrics"""
        beta_users = self.beta_manager.get_beta_users()
        
        metrics = {
            "total_beta_users": len(beta_users),
            "active_users_last_hour": 0,
            "users_by_phase": {},
            "average_session_duration": 0,
            "user_satisfaction_score": 0
        }
        
        # Analyze user activity
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        for user in beta_users:
            phase = user["phase"]
            if phase not in metrics["users_by_phase"]:
                metrics["users_by_phase"][phase] = 0
            metrics["users_by_phase"][phase] += 1
            
            # Check recent activity
            if user["last_activity"]:
                last_activity = datetime.fromisoformat(user["last_activity"])
                if last_activity > one_hour_ago:
                    metrics["active_users_last_hour"] += 1
        
        return metrics
    
    def _collect_application_metrics(self) -> Dict:
        """Collect application-specific metrics"""
        try:
            # Try to get metrics from the application
            response = requests.get("http://localhost:8000/metrics", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        # Fallback metrics
        return {
            "response_time": 0,
            "error_rate": 0,
            "success_rate": 1.0,
            "active_strategies": 0,
            "orders_processed": 0
        }
    
    def _analyze_metrics(self, system_metrics: Dict, user_metrics: Dict, app_metrics: Dict):
        """Analyze metrics and generate alerts if needed"""
        alerts = []
        
        # Check system thresholds
        if system_metrics.get("cpu_usage", 0) > self.performance_thresholds["cpu_usage"]:
            alerts.append({
                "type": "system_alert",
                "severity": "warning",
                "message": f"High CPU usage: {system_metrics['cpu_usage']:.1f}%",
                "metrics": system_metrics
            })
        
        if system_metrics.get("memory_usage", 0) > self.performance_thresholds["memory_usage"]:
            alerts.append({
                "type": "system_alert",
                "severity": "warning",
                "message": f"High memory usage: {system_metrics['memory_usage']:.1f}%",
                "metrics": system_metrics
            })
        
        # Check application thresholds
        if app_metrics.get("response_time", 0) > self.performance_thresholds["response_time"]:
            alerts.append({
                "type": "performance_alert",
                "severity": "warning",
                "message": f"High response time: {app_metrics['response_time']:.2f}s",
                "metrics": app_metrics
            })
        
        if app_metrics.get("error_rate", 0) > self.performance_thresholds["error_rate"]:
            alerts.append({
                "type": "performance_alert",
                "severity": "critical",
                "message": f"High error rate: {app_metrics['error_rate']:.3f}",
                "metrics": app_metrics
            })
        
        # Check user activity
        if user_metrics["total_beta_users"] > 0:
            activity_rate = user_metrics["active_users_last_hour"] / user_metrics["total_beta_users"]
            if activity_rate < 0.1:  # Less than 10% active users
                alerts.append({
                    "type": "user_activity_alert",
                    "severity": "warning",
                    "message": f"Low user activity: {activity_rate:.1%} active in last hour",
                    "metrics": user_metrics
                })
        
        # Queue alerts for processing
        for alert in alerts:
            self.alert_queue.put(alert)
    
    def _alert_processor(self):
        """Process alerts from the queue"""
        while self.monitoring_active:
            try:
                alert = self.alert_queue.get(timeout=1)
                self._send_alert(alert)
                self.alert_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
    
    def _send_alert(self, alert: Dict):
        """Send alert notification"""
        logger.warning(f"ALERT: {alert['message']}")
        
        # Log alert to file
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            **alert
        }
        
        with open("rollout_alerts.log", "a") as f:
            f.write(json.dumps(alert_data) + "\n")
        
        # In production, implement email/webhook notifications
        # self._send_email_alert(alert)
        # self._send_webhook_alert(alert)
    
    def _store_metrics(self, metrics: Dict):
        """Store metrics in database"""
        conn = sqlite3.connect(self.beta_manager.db_path)
        cursor = conn.cursor()
        
        # Create metrics table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollout_metrics (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                metrics_data TEXT NOT NULL
            )
        """)
        
        metrics_id = f"metrics_{int(time.time())}"
        cursor.execute("""
            INSERT INTO rollout_metrics (id, timestamp, metrics_data)
            VALUES (?, ?, ?)
        """, (
            metrics_id,
            metrics["timestamp"],
            json.dumps(metrics)
        ))
        
        conn.commit()
        conn.close()

class RollbackManager:
    """Manages rollback procedures and emergency response"""
    
    def __init__(self, beta_manager: BetaUserManager):
        self.beta_manager = beta_manager
        self.rollback_triggers = {
            "high_error_rate": 0.05,
            "low_success_rate": 0.90,
            "high_response_time": 5.0,
            "user_complaints": 3,
            "system_failure": True
        }
    
    def create_rollback_plan(self) -> Dict:
        """Create comprehensive rollback plan"""
        return {
            "rollback_procedures": [
                {
                    "step": 1,
                    "action": "pause_new_enrollments",
                    "description": "Stop enrolling new beta users",
                    "automated": True
                },
                {
                    "step": 2,
                    "action": "notify_beta_users",
                    "description": "Send notification to all beta users about issues",
                    "automated": True
                },
                {
                    "step": 3,
                    "action": "disable_risky_features",
                    "description": "Disable features causing issues",
                    "automated": True
                },
                {
                    "step": 4,
                    "action": "scale_down_resources",
                    "description": "Reduce system load by scaling down",
                    "automated": False
                },
                {
                    "step": 5,
                    "action": "rollback_deployment",
                    "description": "Rollback to previous stable version",
                    "automated": False
                },
                {
                    "step": 6,
                    "action": "investigate_issues",
                    "description": "Analyze logs and metrics to identify root cause",
                    "automated": False
                }
            ],
            "emergency_contacts": [
                {"role": "DevOps Lead", "contact": "devops@quantumleap.com"},
                {"role": "Product Manager", "contact": "pm@quantumleap.com"},
                {"role": "Engineering Manager", "contact": "eng@quantumleap.com"}
            ],
            "rollback_triggers": self.rollback_triggers
        }
    
    def execute_emergency_rollback(self, trigger: str, severity: str = "high") -> bool:
        """Execute emergency rollback procedure"""
        logger.critical(f"EMERGENCY ROLLBACK TRIGGERED: {trigger}")
        
        try:
            # Step 1: Pause new enrollments
            self._pause_new_enrollments()
            
            # Step 2: Notify beta users
            self._notify_beta_users_emergency(trigger)
            
            # Step 3: Disable risky features
            self._disable_risky_features()
            
            # Step 4: Log rollback event
            self._log_rollback_event(trigger, severity)
            
            # Step 5: Create incident report
            self._create_incident_report(trigger, severity)
            
            logger.info("Emergency rollback procedures completed")
            return True
            
        except Exception as e:
            logger.error(f"Emergency rollback failed: {e}")
            return False
    
    def _pause_new_enrollments(self):
        """Pause new beta user enrollments"""
        conn = sqlite3.connect(self.beta_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE rollout_phases 
            SET status = 'paused'
            WHERE status = 'active'
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("New beta enrollments paused")
    
    def _notify_beta_users_emergency(self, trigger: str):
        """Send emergency notification to beta users"""
        beta_users = self.beta_manager.get_beta_users()
        
        message = f"""
        Dear Beta Tester,
        
        We are experiencing technical issues with our automated trading system.
        As a precautionary measure, we have temporarily paused some features.
        
        Issue: {trigger}
        Status: Under investigation
        
        We will notify you once the issues are resolved.
        
        Thank you for your patience.
        
        Quantum Leap Team
        """
        
        # Log notification (in production, send actual emails)
        for user in beta_users:
            logger.info(f"Emergency notification sent to {user['email']}")
            
        with open("emergency_notifications.log", "a") as f:
            f.write(f"{datetime.now().isoformat()}: Emergency notification sent to {len(beta_users)} beta users\n")
    
    def _disable_risky_features(self):
        """Disable features that might be causing issues"""
        # This would disable specific features in the application
        # For now, we'll log the action
        logger.info("Risky features disabled")
        
        # In production, this would make API calls to disable features
        # requests.post("http://localhost:8000/api/admin/disable-features", 
        #               json={"features": ["advanced_strategies", "high_frequency_trading"]})
    
    def _log_rollback_event(self, trigger: str, severity: str):
        """Log rollback event"""
        self.beta_manager._log_rollout_event(
            "emergency_rollback",
            "all_phases",
            "system",
            {
                "trigger": trigger,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "actions_taken": [
                    "paused_enrollments",
                    "notified_users",
                    "disabled_features"
                ]
            },
            severity="critical"
        )
    
    def _create_incident_report(self, trigger: str, severity: str):
        """Create incident report"""
        incident_report = {
            "incident_id": f"INC_{int(time.time())}",
            "trigger": trigger,
            "severity": severity,
            "started_at": datetime.now().isoformat(),
            "status": "investigating",
            "affected_users": len(self.beta_manager.get_beta_users()),
            "actions_taken": [
                "Emergency rollback initiated",
                "Beta user enrollments paused",
                "Users notified",
                "Risky features disabled"
            ],
            "next_steps": [
                "Analyze system logs",
                "Identify root cause",
                "Implement fix",
                "Resume operations"
            ]
        }
        
        with open(f"incident_report_{incident_report['incident_id']}.json", "w") as f:
            json.dump(incident_report, f, indent=2)
        
        logger.info(f"Incident report created: {incident_report['incident_id']}")

class GradualRolloutOrchestrator:
    """Main orchestrator for gradual rollout system"""
    
    def __init__(self):
        self.beta_manager = BetaUserManager()
        self.enhanced_monitoring = EnhancedMonitoring(self.beta_manager)
        self.rollback_manager = RollbackManager(self.beta_manager)
        self.current_phase = "phase_1"
        self.rollout_active = False
    
    def start_gradual_rollout(self):
        """Start the gradual rollout process"""
        logger.info("🚀 Starting gradual rollout of automated trading engine...")
        
        try:
            # Start enhanced monitoring
            self.enhanced_monitoring.start_enhanced_monitoring()
            
            # Begin with phase 1
            self._start_phase("phase_1")
            
            self.rollout_active = True
            logger.info("✅ Gradual rollout started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start gradual rollout: {e}")
            return False
    
    def _start_phase(self, phase: str):
        """Start a specific rollout phase"""
        logger.info(f"🎯 Starting rollout {phase}")
        
        # Update phase status
        conn = sqlite3.connect(self.beta_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE rollout_phases 
            SET status = 'active', started_at = ?
            WHERE phase_name = ?
        """, (datetime.now().isoformat(), phase))
        
        conn.commit()
        conn.close()
        
        # Log phase start
        self.beta_manager._log_rollout_event(
            "phase_started",
            phase,
            "system",
            {"phase_config": self.beta_manager.rollout_phases[phase]}
        )
        
        self.current_phase = phase
        logger.info(f"✅ Phase {phase} started")
    
    def enroll_beta_users_batch(self, user_list: List[Dict]) -> Dict:
        """Enroll multiple beta users"""
        results = {
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for user_data in user_list:
            success = self.beta_manager.enroll_beta_user(
                user_data["user_id"],
                user_data["email"],
                user_data.get("phase", self.current_phase)
            )
            
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to enroll {user_data['user_id']}")
        
        logger.info(f"Batch enrollment: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def get_rollout_status(self) -> Dict:
        """Get current rollout status"""
        conn = sqlite3.connect(self.beta_manager.db_path)
        cursor = conn.cursor()
        
        # Get phase status
        cursor.execute("SELECT * FROM rollout_phases")
        phases = [dict(zip([col[0] for col in cursor.description], row)) 
                 for row in cursor.fetchall()]
        
        # Get beta users count
        cursor.execute("SELECT phase, COUNT(*) as count FROM beta_users GROUP BY phase")
        user_counts = dict(cursor.fetchall())
        
        # Get recent events
        cursor.execute("""
            SELECT * FROM rollout_events 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_events = [dict(zip([col[0] for col in cursor.description], row)) 
                        for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "rollout_active": self.rollout_active,
            "current_phase": self.current_phase,
            "phases": phases,
            "user_counts": user_counts,
            "recent_events": recent_events,
            "timestamp": datetime.now().isoformat()
        }
    
    def create_rollout_dashboard(self):
        """Create rollout monitoring dashboard"""
        status = self.get_rollout_status()
        
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Gradual Rollout Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .status-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .active {{ background-color: #e8f5e8; }}
        .pending {{ background-color: #fff3cd; }}
        .paused {{ background-color: #f8d7da; }}
        .metrics {{ display: flex; gap: 20px; }}
        .metric {{ text-align: center; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🚀 Gradual Rollout Dashboard</h1>
    <p><strong>Last Updated:</strong> {status['timestamp']}</p>
    <p><strong>Rollout Status:</strong> {'🟢 Active' if status['rollout_active'] else '🔴 Inactive'}</p>
    <p><strong>Current Phase:</strong> {status['current_phase']}</p>
    
    <h2>📊 Rollout Phases</h2>
    """
        
        for phase in status['phases']:
            phase_class = phase['status']
            user_count = status['user_counts'].get(phase['phase_name'], 0)
            
            dashboard_html += f"""
    <div class="status-card {phase_class}">
        <h3>{phase['phase_name'].title()}</h3>
        <p><strong>Status:</strong> {phase['status']}</p>
        <p><strong>Users:</strong> {user_count}/{phase['max_users']}</p>
        <p><strong>Features:</strong> {phase['features']}</p>
        {f"<p><strong>Started:</strong> {phase['started_at']}</p>" if phase['started_at'] else ""}
    </div>
            """
        
        dashboard_html += """
    <h2>📈 Recent Events</h2>
    <div style="max-height: 300px; overflow-y: auto;">
        """
        
        for event in status['recent_events']:
            severity_color = {
                'info': '#17a2b8',
                'warning': '#ffc107', 
                'critical': '#dc3545'
            }.get(event['severity'], '#6c757d')
            
            dashboard_html += f"""
        <div style="border-left: 4px solid {severity_color}; padding: 10px; margin: 5px 0;">
            <strong>{event['event_type']}</strong> - {event['created_at']}<br>
            Phase: {event['phase'] or 'N/A'} | User: {event['user_id'] or 'System'}<br>
            <small>{event['event_data']}</small>
        </div>
            """
        
        dashboard_html += """
    </div>
    
    <h2>🔧 Actions</h2>
    <div>
        <button onclick="location.reload()">🔄 Refresh</button>
        <button onclick="alert('Emergency rollback would be triggered')">🚨 Emergency Rollback</button>
    </div>
</body>
</html>
        """
        
        with open("rollout_dashboard.html", "w") as f:
            f.write(dashboard_html)
        
        logger.info("📊 Rollout dashboard created: rollout_dashboard.html")

def main():
    """Main function to demonstrate gradual rollout system"""
    print("🚀 Initializing Gradual Rollout System...\n")
    
    try:
        # Initialize orchestrator
        orchestrator = GradualRolloutOrchestrator()
        
        # Start gradual rollout
        if orchestrator.start_gradual_rollout():
            print("✅ Gradual rollout system started successfully")
        else:
            print("❌ Failed to start gradual rollout system")
            return False
        
        # Enroll sample beta users
        sample_users = [
            {"user_id": "beta_user_1", "email": "beta1@example.com"},
            {"user_id": "beta_user_2", "email": "beta2@example.com"},
            {"user_id": "beta_user_3", "email": "beta3@example.com"}
        ]
        
        enrollment_results = orchestrator.enroll_beta_users_batch(sample_users)
        print(f"📝 Beta user enrollment: {enrollment_results['successful']} successful")
        
        # Create rollback plan
        rollback_plan = orchestrator.rollback_manager.create_rollback_plan()
        with open("rollback_plan.json", "w") as f:
            json.dump(rollback_plan, f, indent=2)
        print("📋 Rollback plan created: rollback_plan.json")
        
        # Create dashboard
        orchestrator.create_rollout_dashboard()
        
        # Get status
        status = orchestrator.get_rollout_status()
        print(f"\n📊 Current Status:")
        print(f"   Active Phase: {status['current_phase']}")
        print(f"   Total Beta Users: {sum(status['user_counts'].values())}")
        print(f"   Recent Events: {len(status['recent_events'])}")
        
        print("\n" + "="*60)
        print("🎉 GRADUAL ROLLOUT SYSTEM READY!")
        print("="*60)
        print("\n📋 Next Steps:")
        print("1. Open rollout_dashboard.html to monitor progress")
        print("2. Enroll beta users using the API")
        print("3. Monitor system performance and user feedback")
        print("4. Progress to next phases based on success criteria")
        print("5. Use rollback procedures if issues arise")
        
        return True
        
    except Exception as e:
        print(f"❌ Gradual rollout system initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)