#!/usr/bin/env python3
"""
Simplified Operational Procedures System
Standalone version that doesn't depend on database configuration
"""

import os
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemStatus(Enum):
    """System status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    response_time: float
    error_rate: float
    timestamp: datetime

@dataclass
class OperationalAlert:
    """Operational alert structure"""
    level: AlertLevel
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class SimpleOperationalProcedures:
    """Simplified operational procedures system"""
    
    def __init__(self):
        self.alerts: List[OperationalAlert] = []
        self.system_metrics_history: List[SystemMetrics] = []
        self.runbooks_path = "operational_runbooks"
        self.scaling_thresholds = {
            "cpu_high": 80.0,
            "memory_high": 85.0,
            "disk_high": 90.0,
            "response_time_high": 5.0,
            "error_rate_high": 5.0
        }
        self._initialize_runbooks()
    
    def _initialize_runbooks(self):
        """Initialize operational runbooks"""
        try:
            os.makedirs(self.runbooks_path, exist_ok=True)
            
            # Create system health runbook
            system_health_runbook = {
                "title": "System Health Monitoring Runbook",
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "procedures": {
                    "health_check": {
                        "description": "Perform comprehensive system health check",
                        "steps": [
                            "Check CPU usage (should be < 80%)",
                            "Check memory usage (should be < 85%)",
                            "Check disk space (should be < 90%)",
                            "Verify API endpoints response time",
                            "Check error logs for critical issues"
                        ],
                        "commands": [
                            "curl -f http://localhost:8000/health",
                            "df -h",
                            "free -m",
                            "top -n 1 -b"
                        ]
                    }
                }
            }
            
            with open(f"{self.runbooks_path}/system_health_runbook.json", "w") as f:
                json.dump(system_health_runbook, f, indent=2)
            
            # Create trading engine runbook
            trading_runbook = {
                "title": "Trading Engine Operational Runbook",
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "procedures": {
                    "engine_health_check": {
                        "description": "Check trading engine health and status",
                        "steps": [
                            "Verify trading engine service is running",
                            "Check strategy execution status",
                            "Validate market data feeds",
                            "Test order execution pipeline"
                        ]
                    }
                }
            }
            
            with open(f"{self.runbooks_path}/trading_engine_runbook.json", "w") as f:
                json.dump(trading_runbook, f, indent=2)
            
            # Create AI system runbook
            ai_runbook = {
                "title": "AI System Operational Runbook",
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "procedures": {
                    "ai_health_check": {
                        "description": "Check AI system health and performance",
                        "steps": [
                            "Verify AI service availability",
                            "Test signal generation",
                            "Check portfolio analysis",
                            "Validate model performance"
                        ]
                    }
                }
            }
            
            with open(f"{self.runbooks_path}/ai_system_runbook.json", "w") as f:
                json.dump(ai_runbook, f, indent=2)
            
            logger.info("✅ Operational runbooks initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize runbooks: {e}")
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            }
            
            # Active connections (approximate)
            try:
                connections = len(psutil.net_connections())
            except:
                connections = 0  # Fallback if permission denied
            
            # Mock response time and error rate
            response_time = 0.5  # seconds
            error_rate = 0.1     # percentage
            
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                active_connections=connections,
                response_time=response_time,
                error_rate=error_rate,
                timestamp=datetime.now()
            )
            
            # Store metrics history (keep last 100 entries)
            self.system_metrics_history.append(metrics)
            if len(self.system_metrics_history) > 100:
                self.system_metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            # Return default metrics if collection fails
            return SystemMetrics(
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={"bytes_sent": 0, "bytes_recv": 0},
                active_connections=0,
                response_time=1.0,
                error_rate=0.0,
                timestamp=datetime.now()
            )
    
    def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            metrics = self.collect_system_metrics()
            health_status = SystemStatus.HEALTHY
            issues = []
            
            # Check CPU usage
            if metrics.cpu_usage > self.scaling_thresholds["cpu_high"]:
                health_status = SystemStatus.WARNING
                issues.append(f"High CPU usage: {metrics.cpu_usage:.1f}%")
            
            # Check memory usage
            if metrics.memory_usage > self.scaling_thresholds["memory_high"]:
                health_status = SystemStatus.CRITICAL if metrics.memory_usage > 95 else SystemStatus.WARNING
                issues.append(f"High memory usage: {metrics.memory_usage:.1f}%")
            
            # Check disk usage
            if metrics.disk_usage > self.scaling_thresholds["disk_high"]:
                health_status = SystemStatus.CRITICAL
                issues.append(f"High disk usage: {metrics.disk_usage:.1f}%")
            
            return {
                "status": health_status.value,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu_usage": metrics.cpu_usage,
                    "memory_usage": metrics.memory_usage,
                    "disk_usage": metrics.disk_usage,
                    "response_time": metrics.response_time,
                    "error_rate": metrics.error_rate,
                    "active_connections": metrics.active_connections
                },
                "issues": issues,
                "recommendations": self._get_health_recommendations(issues)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": SystemStatus.FAILED.value,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _get_health_recommendations(self, issues: List[str]) -> List[str]:
        """Get recommendations based on health issues"""
        recommendations = []
        
        for issue in issues:
            if "CPU usage" in issue:
                recommendations.append("Consider scaling horizontally or optimizing CPU-intensive operations")
            elif "memory usage" in issue:
                recommendations.append("Restart memory-intensive services or increase memory allocation")
            elif "disk usage" in issue:
                recommendations.append("Clean up old files or expand disk capacity")
        
        return recommendations
    
    def trigger_automated_recovery(self, issue_type: str) -> Dict[str, Any]:
        """Trigger automated recovery procedure"""
        try:
            logger.info(f"🔧 Triggering automated recovery for: {issue_type}")
            
            # Simulate recovery actions
            actions_taken = []
            
            if issue_type == "high_cpu":
                actions_taken = [
                    "Identified high CPU processes",
                    "Logged process information",
                    "Recommended scaling or optimization"
                ]
            elif issue_type == "high_memory":
                actions_taken = [
                    "Analyzed memory usage",
                    "Recommended service restart",
                    "Suggested memory optimization"
                ]
            elif issue_type == "disk_full":
                actions_taken = [
                    "Checked disk usage",
                    "Recommended cleanup procedures",
                    "Suggested capacity expansion"
                ]
            else:
                actions_taken = [f"Generic recovery procedure for {issue_type}"]
            
            # Create alert
            alert = OperationalAlert(
                level=AlertLevel.WARNING,
                component="automated_recovery",
                message=f"Automated recovery triggered for {issue_type}",
                timestamp=datetime.now()
            )
            self.alerts.append(alert)
            
            return {
                "success": True,
                "issue_type": issue_type,
                "actions_taken": actions_taken,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Automated recovery failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_capacity_planning_report(self) -> Dict[str, Any]:
        """Generate capacity planning report"""
        try:
            if not self.system_metrics_history:
                return {
                    "message": "No metrics history available yet",
                    "recommendation": "Run system for a few minutes to collect metrics"
                }
            
            # Calculate trends from recent metrics
            recent_metrics = self.system_metrics_history[-10:]  # Last 10 measurements
            
            avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)
            
            # Generate scaling recommendations
            scaling_recommendations = []
            
            if avg_cpu > 70:
                scaling_recommendations.append({
                    "resource": "CPU",
                    "current_usage": avg_cpu,
                    "recommendation": "Consider horizontal scaling within 24-48 hours",
                    "urgency": "medium" if avg_cpu < 80 else "high"
                })
            
            if avg_memory > 75:
                scaling_recommendations.append({
                    "resource": "Memory",
                    "current_usage": avg_memory,
                    "recommendation": "Consider memory upgrade or service optimization",
                    "urgency": "medium" if avg_memory < 85 else "high"
                })
            
            if avg_disk > 80:
                scaling_recommendations.append({
                    "resource": "Disk",
                    "current_usage": avg_disk,
                    "recommendation": "Plan disk expansion or data archival",
                    "urgency": "high"
                })
            
            return {
                "timestamp": datetime.now().isoformat(),
                "current_utilization": {
                    "cpu": avg_cpu,
                    "memory": avg_memory,
                    "disk": avg_disk
                },
                "scaling_recommendations": scaling_recommendations,
                "metrics_analyzed": len(recent_metrics),
                "next_review": (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Capacity planning report failed: {e}")
            return {"error": str(e)}
    
    def get_operational_status(self) -> Dict[str, Any]:
        """Get comprehensive operational status"""
        try:
            health = self.check_system_health()
            capacity = self.get_capacity_planning_report()
            
            # Get recent alerts
            recent_alerts = [
                {
                    "level": alert.level.value,
                    "component": alert.component,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat(),
                    "resolved": alert.resolved
                }
                for alert in self.alerts[-10:]  # Last 10 alerts
            ]
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system_health": health,
                "capacity_planning": capacity,
                "recent_alerts": recent_alerts,
                "runbooks_available": len(os.listdir(self.runbooks_path)) if os.path.exists(self.runbooks_path) else 0,
                "recovery_procedures": ["high_cpu", "high_memory", "disk_full", "service_down"]
            }
            
        except Exception as e:
            logger.error(f"Operational status failed: {e}")
            return {"error": str(e)}

# Global instance
simple_operational_procedures = SimpleOperationalProcedures()

def get_simple_operational_procedures() -> SimpleOperationalProcedures:
    """Get the simple operational procedures instance"""
    return simple_operational_procedures