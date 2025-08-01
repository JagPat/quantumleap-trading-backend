#!/usr/bin/env python3
"""
Production Monitoring Script
Monitors system health and sends alerts
"""

import json
import time
import requests
import logging
import sqlite3
from datetime import datetime, timedelta
import psutil
import smtplib
from email.mime.text import MimeText

class ProductionMonitor:
    def __init__(self, config_path="monitoring/monitoring_config.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def check_system_health(self):
        """Check overall system health"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "components": {}
        }
        
        # Check database
        try:
            conn = sqlite3.connect("production_trading.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM orders")
            conn.close()
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"
        
        # Check API endpoints
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                health_status["components"]["api"] = "healthy"
            else:
                health_status["components"]["api"] = f"unhealthy: HTTP {response.status_code}"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["api"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"
        
        # Check system resources
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        
        health_status["metrics"] = {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage
        }
        
        # Check thresholds
        if cpu_usage > self.config["performance_metrics"]["cpu_usage"]["critical_threshold"]:
            health_status["status"] = "critical"
            self.send_alert(f"Critical CPU usage: {cpu_usage}%")
        elif memory_usage > self.config["performance_metrics"]["memory_usage"]["critical_threshold"]:
            health_status["status"] = "critical"
            self.send_alert(f"Critical memory usage: {memory_usage}%")
        
        return health_status
    
    def send_alert(self, message):
        """Send alert notification"""
        self.logger.warning(f"ALERT: {message}")
        
        # In production, implement actual email/webhook alerts
        # For now, just log the alert
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "severity": "critical"
        }
        
        with open("alerts.log", "a") as f:
            f.write(json.dumps(alert_data) + "\n")
    
    def run_monitoring_loop(self):
        """Run continuous monitoring"""
        self.logger.info("Starting production monitoring...")
        
        while True:
            try:
                health = self.check_system_health()
                
                # Log health status
                with open("health_status.log", "a") as f:
                    f.write(json.dumps(health) + "\n")
                
                if health["status"] != "healthy":
                    self.logger.warning(f"System status: {health['status']}")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(30)  # Shorter interval on error

if __name__ == "__main__":
    monitor = ProductionMonitor()
    monitor.run_monitoring_loop()
