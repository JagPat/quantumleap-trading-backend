"""
Operational Procedures System for Automated Trading Engine

This module provides operational runbooks, automated system recovery,
failover procedures, and capacity planning for the trading engine.
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import subprocess
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class SystemStatus(Enum):
    """System status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    database_connections: int
    queue_depth: int
    response_time_ms: float
    error_rate: float
    throughput_per_second: float

@dataclass
class OperationalAlert:
    """Operational alert structure"""
    id: str
    timestamp: datetime
    level: AlertLevel
    component: str
    message: str
    details: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class RecoveryAction:
    """Recovery action definition"""
    name: str
    description: str
    conditions: List[str]
    action_function: str
    timeout_seconds: int
    retry_count: int
    escalation_level: AlertLevel

class OperationalProcedures:
    """
    Operational procedures and system management
    """
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.active_alerts: List[OperationalAlert] = []
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.system_status = SystemStatus.HEALTHY
        self.monitoring_active = False
        self.recovery_in_progress = False
        
        # Initialize recovery actions
        self._initialize_recovery_actions()
        
        # Performance thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'response_time_warning': 1000.0,  # ms
            'response_time_critical': 5000.0,  # ms
            'error_rate_warning': 0.05,  # 5%
            'error_rate_critical': 0.10,  # 10%
            'queue_depth_warning': 1000,
            'queue_depth_critical': 5000
        }
    
    def _initialize_recovery_actions(self):
        """Initialize predefined recovery actions"""
        
        self.recovery_actions = {
            'restart_service': RecoveryAction(
                name="Restart Trading Service",
                description="Restart the main trading engine service",
                conditions=["high_error_rate", "service_unresponsive"],
                action_function="restart_trading_service",
                timeout_seconds=60,
                retry_count=3,
                escalation_level=AlertLevel.CRITICAL
            ),
            
            'clear_queue': RecoveryAction(
                name="Clear Processing Queue",
                description="Clear backed up processing queues",
                conditions=["high_queue_depth", "queue_stalled"],
                action_function="clear_processing_queue",
                timeout_seconds=30,
                retry_count=2,
                escalation_level=AlertLevel.WARNING
            ),
            
            'scale_resources': RecoveryAction(
                name="Scale System Resources",
                description="Increase system resources allocation",
                conditions=["high_cpu_usage", "high_memory_usage"],
                action_function="scale_system_resources",
                timeout_seconds=120,
                retry_count=1,
                escalation_level=AlertLevel.WARNING
            ),
            
            'emergency_stop': RecoveryAction(
                name="Emergency System Stop",
                description="Stop all trading activities immediately",
                conditions=["system_failure", "data_corruption"],
                action_function="emergency_stop_all",
                timeout_seconds=10,
                retry_count=1,
                escalation_level=AlertLevel.EMERGENCY
            ),
            
            'database_recovery': RecoveryAction(
                name="Database Recovery",
                description="Recover database connections and integrity",
                conditions=["database_connection_failure", "database_corruption"],
                action_function="recover_database",
                timeout_seconds=180,
                retry_count=2,
                escalation_level=AlertLevel.CRITICAL
            )
        }
    
    async def start_monitoring(self):
        """Start continuous system monitoring"""
        self.monitoring_active = True
        logger.info("Starting operational monitoring")
        
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = await self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only last 24 hours of metrics
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
                # Analyze metrics and trigger alerts
                await self._analyze_metrics(metrics)
                
                # Check for recovery conditions
                await self._check_recovery_conditions()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Connection counts
            connections = len(psutil.net_connections())
            
            # Database connections (mock - would integrate with actual DB)
            db_connections = await self._get_database_connections()
            
            # Queue depth (mock - would integrate with actual queue system)
            queue_depth = await self._get_queue_depth()
            
            # Response time (mock - would measure actual API response times)
            response_time = await self._measure_response_time()
            
            # Error rate (mock - would calculate from actual error logs)
            error_rate = await self._calculate_error_rate()
            
            # Throughput (mock - would measure actual transaction throughput)
            throughput = await self._measure_throughput()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_io=network_io,
                active_connections=connections,
                database_connections=db_connections,
                queue_depth=queue_depth,
                response_time_ms=response_time,
                error_rate=error_rate,
                throughput_per_second=throughput
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                active_connections=0,
                database_connections=0,
                queue_depth=0,
                response_time_ms=0.0,
                error_rate=0.0,
                throughput_per_second=0.0
            )
    
    async def _get_database_connections(self) -> int:
        """Get current database connection count"""
        # Mock implementation - would integrate with actual database
        return 10
    
    async def _get_queue_depth(self) -> int:
        """Get current processing queue depth"""
        # Mock implementation - would integrate with actual queue system
        return 50
    
    async def _measure_response_time(self) -> float:
        """Measure average API response time"""
        # Mock implementation - would measure actual API response times
        return 150.0
    
    async def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        # Mock implementation - would calculate from actual error logs
        return 0.02  # 2% error rate
    
    async def _measure_throughput(self) -> float:
        """Measure current transaction throughput"""
        # Mock implementation - would measure actual throughput
        return 25.5  # transactions per second
    
    async def _analyze_metrics(self, metrics: SystemMetrics):
        """Analyze metrics and generate alerts"""
        alerts = []
        
        # CPU usage alerts
        if metrics.cpu_usage > self.thresholds['cpu_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "system",
                f"Critical CPU usage: {metrics.cpu_usage:.1f}%",
                {"cpu_usage": metrics.cpu_usage, "threshold": self.thresholds['cpu_critical']}
            ))
        elif metrics.cpu_usage > self.thresholds['cpu_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"High CPU usage: {metrics.cpu_usage:.1f}%",
                {"cpu_usage": metrics.cpu_usage, "threshold": self.thresholds['cpu_warning']}
            ))
        
        # Memory usage alerts
        if metrics.memory_usage > self.thresholds['memory_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "system",
                f"Critical memory usage: {metrics.memory_usage:.1f}%",
                {"memory_usage": metrics.memory_usage, "threshold": self.thresholds['memory_critical']}
            ))
        elif metrics.memory_usage > self.thresholds['memory_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "system",
                f"High memory usage: {metrics.memory_usage:.1f}%",
                {"memory_usage": metrics.memory_usage, "threshold": self.thresholds['memory_warning']}
            ))
        
        # Disk usage alerts
        if metrics.disk_usage > self.thresholds['disk_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "storage",
                f"Critical disk usage: {metrics.disk_usage:.1f}%",
                {"disk_usage": metrics.disk_usage, "threshold": self.thresholds['disk_critical']}
            ))
        elif metrics.disk_usage > self.thresholds['disk_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "storage",
                f"High disk usage: {metrics.disk_usage:.1f}%",
                {"disk_usage": metrics.disk_usage, "threshold": self.thresholds['disk_warning']}
            ))
        
        # Response time alerts
        if metrics.response_time_ms > self.thresholds['response_time_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "performance",
                f"Critical response time: {metrics.response_time_ms:.1f}ms",
                {"response_time": metrics.response_time_ms, "threshold": self.thresholds['response_time_critical']}
            ))
        elif metrics.response_time_ms > self.thresholds['response_time_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "performance",
                f"High response time: {metrics.response_time_ms:.1f}ms",
                {"response_time": metrics.response_time_ms, "threshold": self.thresholds['response_time_warning']}
            ))
        
        # Error rate alerts
        if metrics.error_rate > self.thresholds['error_rate_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "errors",
                f"Critical error rate: {metrics.error_rate:.2%}",
                {"error_rate": metrics.error_rate, "threshold": self.thresholds['error_rate_critical']}
            ))
        elif metrics.error_rate > self.thresholds['error_rate_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "errors",
                f"High error rate: {metrics.error_rate:.2%}",
                {"error_rate": metrics.error_rate, "threshold": self.thresholds['error_rate_warning']}
            ))
        
        # Queue depth alerts
        if metrics.queue_depth > self.thresholds['queue_depth_critical']:
            alerts.append(self._create_alert(
                AlertLevel.CRITICAL,
                "queue",
                f"Critical queue depth: {metrics.queue_depth}",
                {"queue_depth": metrics.queue_depth, "threshold": self.thresholds['queue_depth_critical']}
            ))
        elif metrics.queue_depth > self.thresholds['queue_depth_warning']:
            alerts.append(self._create_alert(
                AlertLevel.WARNING,
                "queue",
                f"High queue depth: {metrics.queue_depth}",
                {"queue_depth": metrics.queue_depth, "threshold": self.thresholds['queue_depth_warning']}
            ))
        
        # Add new alerts
        for alert in alerts:
            await self._add_alert(alert)
        
        # Update system status
        await self._update_system_status(metrics, alerts)
    
    def _create_alert(self, level: AlertLevel, component: str, message: str, details: Dict[str, Any]) -> OperationalAlert:
        """Create a new operational alert"""
        return OperationalAlert(
            id=f"{component}_{int(time.time())}_{level.value}",
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            details=details
        )
    
    async def _add_alert(self, alert: OperationalAlert):
        """Add a new alert and handle notifications"""
        # Check if similar alert already exists
        existing = [a for a in self.active_alerts 
                   if a.component == alert.component and a.level == alert.level and not a.resolved]
        
        if not existing:
            self.active_alerts.append(alert)
            logger.warning(f"New {alert.level.value} alert: {alert.message}")
            
            # Send notifications based on alert level
            await self._send_alert_notification(alert)
    
    async def _send_alert_notification(self, alert: OperationalAlert):
        """Send alert notifications"""
        try:
            # Mock notification system - would integrate with actual notification service
            notification_data = {
                'alert_id': alert.id,
                'level': alert.level.value,
                'component': alert.component,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'details': alert.details
            }
            
            logger.info(f"Sending {alert.level.value} notification: {alert.message}")
            
            # Different notification channels based on severity
            if alert.level == AlertLevel.EMERGENCY:
                # Send to all channels immediately
                await self._send_emergency_notification(notification_data)
            elif alert.level == AlertLevel.CRITICAL:
                # Send to critical channels
                await self._send_critical_notification(notification_data)
            elif alert.level == AlertLevel.WARNING:
                # Send to standard channels
                await self._send_warning_notification(notification_data)
            else:
                # Log only for info alerts
                logger.info(f"Info alert: {alert.message}")
                
        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")
    
    async def _send_emergency_notification(self, data: Dict[str, Any]):
        """Send emergency notifications to all channels"""
        # Mock implementation - would integrate with actual notification services
        logger.critical(f"EMERGENCY ALERT: {data['message']}")
    
    async def _send_critical_notification(self, data: Dict[str, Any]):
        """Send critical notifications"""
        # Mock implementation - would integrate with actual notification services
        logger.error(f"CRITICAL ALERT: {data['message']}")
    
    async def _send_warning_notification(self, data: Dict[str, Any]):
        """Send warning notifications"""
        # Mock implementation - would integrate with actual notification services
        logger.warning(f"WARNING ALERT: {data['message']}")
    
    async def _update_system_status(self, metrics: SystemMetrics, alerts: List[OperationalAlert]):
        """Update overall system status"""
        # Determine status based on active alerts
        critical_alerts = [a for a in self.active_alerts if a.level == AlertLevel.CRITICAL and not a.resolved]
        emergency_alerts = [a for a in self.active_alerts if a.level == AlertLevel.EMERGENCY and not a.resolved]
        warning_alerts = [a for a in self.active_alerts if a.level == AlertLevel.WARNING and not a.resolved]
        
        if emergency_alerts or self.recovery_in_progress:
            new_status = SystemStatus.FAILED if emergency_alerts else SystemStatus.RECOVERING
        elif critical_alerts:
            new_status = SystemStatus.CRITICAL
        elif warning_alerts:
            new_status = SystemStatus.WARNING
        else:
            new_status = SystemStatus.HEALTHY
        
        if new_status != self.system_status:
            logger.info(f"System status changed from {self.system_status.value} to {new_status.value}")
            self.system_status = new_status
    
    async def _check_recovery_conditions(self):
        """Check if any recovery actions should be triggered"""
        if self.recovery_in_progress:
            return
        
        # Check each recovery action's conditions
        for action_name, action in self.recovery_actions.items():
            if await self._should_trigger_recovery(action):
                await self._execute_recovery_action(action)
    
    async def _should_trigger_recovery(self, action: RecoveryAction) -> bool:
        """Check if recovery action conditions are met"""
        # Mock condition checking - would implement actual condition logic
        recent_metrics = self.metrics_history[-5:] if len(self.metrics_history) >= 5 else self.metrics_history
        
        if not recent_metrics:
            return False
        
        # Check conditions based on recent metrics
        for condition in action.conditions:
            if condition == "high_error_rate":
                if any(m.error_rate > self.thresholds['error_rate_critical'] for m in recent_metrics):
                    return True
            elif condition == "high_cpu_usage":
                if any(m.cpu_usage > self.thresholds['cpu_critical'] for m in recent_metrics):
                    return True
            elif condition == "high_memory_usage":
                if any(m.memory_usage > self.thresholds['memory_critical'] for m in recent_metrics):
                    return True
            elif condition == "high_queue_depth":
                if any(m.queue_depth > self.thresholds['queue_depth_critical'] for m in recent_metrics):
                    return True
            elif condition == "service_unresponsive":
                if any(m.response_time_ms > self.thresholds['response_time_critical'] for m in recent_metrics):
                    return True
        
        return False
    
    async def _execute_recovery_action(self, action: RecoveryAction):
        """Execute a recovery action"""
        self.recovery_in_progress = True
        logger.warning(f"Executing recovery action: {action.name}")
        
        try:
            # Get the recovery function
            recovery_function = getattr(self, action.action_function, None)
            if not recovery_function:
                logger.error(f"Recovery function {action.action_function} not found")
                return
            
            # Execute with timeout and retries
            for attempt in range(action.retry_count):
                try:
                    await asyncio.wait_for(
                        recovery_function(),
                        timeout=action.timeout_seconds
                    )
                    logger.info(f"Recovery action {action.name} completed successfully")
                    break
                except asyncio.TimeoutError:
                    logger.warning(f"Recovery action {action.name} timed out (attempt {attempt + 1})")
                except Exception as e:
                    logger.error(f"Recovery action {action.name} failed (attempt {attempt + 1}): {e}")
                
                if attempt < action.retry_count - 1:
                    await asyncio.sleep(10)  # Wait before retry
            else:
                # All attempts failed
                logger.error(f"Recovery action {action.name} failed after {action.retry_count} attempts")
                await self._escalate_recovery_failure(action)
        
        finally:
            self.recovery_in_progress = False
    
    async def _escalate_recovery_failure(self, action: RecoveryAction):
        """Escalate when recovery action fails"""
        escalation_alert = self._create_alert(
            action.escalation_level,
            "recovery",
            f"Recovery action failed: {action.name}",
            {"action": action.name, "description": action.description}
        )
        await self._add_alert(escalation_alert)
    
    # Recovery action implementations
    async def restart_trading_service(self):
        """Restart the trading service"""
        logger.info("Restarting trading service...")
        # Mock implementation - would restart actual service
        await asyncio.sleep(5)  # Simulate restart time
        logger.info("Trading service restarted")
    
    async def clear_processing_queue(self):
        """Clear backed up processing queues"""
        logger.info("Clearing processing queues...")
        # Mock implementation - would clear actual queues
        await asyncio.sleep(2)
        logger.info("Processing queues cleared")
    
    async def scale_system_resources(self):
        """Scale system resources"""
        logger.info("Scaling system resources...")
        # Mock implementation - would scale actual resources
        await asyncio.sleep(10)
        logger.info("System resources scaled")
    
    async def emergency_stop_all(self):
        """Emergency stop all trading activities"""
        logger.critical("EMERGENCY STOP: Stopping all trading activities")
        # Mock implementation - would stop actual trading
        await asyncio.sleep(1)
        logger.critical("All trading activities stopped")
    
    async def recover_database(self):
        """Recover database connections and integrity"""
        logger.info("Recovering database connections...")
        # Mock implementation - would recover actual database
        await asyncio.sleep(15)
        logger.info("Database connections recovered")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        recent_metrics = self.metrics_history[-1] if self.metrics_history else None
        active_alerts = [a for a in self.active_alerts if not a.resolved]
        
        return {
            'status': self.system_status.value,
            'timestamp': datetime.now().isoformat(),
            'monitoring_active': self.monitoring_active,
            'recovery_in_progress': self.recovery_in_progress,
            'active_alerts_count': len(active_alerts),
            'critical_alerts_count': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
            'recent_metrics': asdict(recent_metrics) if recent_metrics else None,
            'uptime_hours': self._calculate_uptime(),
            'total_alerts_today': len([a for a in self.active_alerts 
                                     if a.timestamp.date() == datetime.now().date()])
        }
    
    def _calculate_uptime(self) -> float:
        """Calculate system uptime in hours"""
        # Mock implementation - would calculate actual uptime
        return 24.5
    
    def get_operational_runbook(self) -> Dict[str, Any]:
        """Get operational runbook and procedures"""
        return {
            'system_overview': {
                'description': 'Automated Trading Engine Operational Procedures',
                'version': '1.0.0',
                'last_updated': datetime.now().isoformat()
            },
            'monitoring_procedures': {
                'health_checks': [
                    'System resource utilization (CPU, Memory, Disk)',
                    'Database connectivity and performance',
                    'API response times and error rates',
                    'Queue depths and processing rates',
                    'Network connectivity and throughput'
                ],
                'alert_thresholds': self.thresholds,
                'monitoring_frequency': '30 seconds'
            },
            'recovery_procedures': {
                action_name: {
                    'name': action.name,
                    'description': action.description,
                    'conditions': action.conditions,
                    'timeout_seconds': action.timeout_seconds,
                    'retry_count': action.retry_count,
                    'escalation_level': action.escalation_level.value
                }
                for action_name, action in self.recovery_actions.items()
            },
            'escalation_procedures': {
                'warning': 'Log alert and monitor for escalation',
                'critical': 'Immediate notification to operations team',
                'emergency': 'Immediate notification to all stakeholders and emergency response'
            },
            'capacity_planning': {
                'cpu_scaling_threshold': 70,
                'memory_scaling_threshold': 80,
                'disk_cleanup_threshold': 85,
                'connection_pool_scaling': 'Auto-scale based on demand',
                'database_scaling': 'Monitor connection count and query performance'
            },
            'troubleshooting_guides': {
                'high_cpu_usage': [
                    'Check for runaway processes',
                    'Review recent deployments',
                    'Scale resources if needed',
                    'Restart services if necessary'
                ],
                'high_memory_usage': [
                    'Check for memory leaks',
                    'Review application logs',
                    'Restart affected services',
                    'Scale memory allocation'
                ],
                'database_issues': [
                    'Check database connectivity',
                    'Review slow query logs',
                    'Check connection pool status',
                    'Restart database connections'
                ],
                'api_performance_issues': [
                    'Check API response times',
                    'Review error logs',
                    'Check external service dependencies',
                    'Scale API instances if needed'
                ]
            }
        }
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        logger.info("Operational monitoring stopped")

# Global instance
operational_procedures = OperationalProcedures()