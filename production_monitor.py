#!/usr/bin/env python3
"""
Production Database Monitoring Script
"""
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMonitor:
    def __init__(self):
        self.db_path = "production_trading_optimized.db"
        self.metrics_history = []
        
    def collect_metrics(self):
        """Collect performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM positions WHERE status = 'OPEN'")
            open_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM executions WHERE executed_at > datetime('now', '-1 hour')")
            recent_executions = cursor.fetchone()[0]
            
            # Calculate recent activity
            cursor.execute("SELECT COUNT(*) FROM orders WHERE created_at > datetime('now', '-1 hour')")
            recent_orders = cursor.fetchone()[0]
            
            conn.close()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "database_size_mb": round(db_size_mb, 2),
                "total_orders": order_count,
                "open_positions": open_positions,
                "recent_executions_1h": recent_executions,
                "recent_orders_1h": recent_orders,
                "orders_per_minute": round(recent_orders / 60, 2),
                "executions_per_minute": round(recent_executions / 60, 2)
            }
            
            self.metrics_history.append(metrics)
            
            # Keep only last 24 hours of metrics
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.metrics_history = [
                m for m in self.metrics_history 
                if datetime.fromisoformat(m["timestamp"]) > cutoff_time
            ]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return None
    
    def check_alerts(self, metrics):
        """Check for alert conditions"""
        alerts = []
        
        if metrics["database_size_mb"] > 1000:
            alerts.append(f"Large database size: {metrics['database_size_mb']:.1f}MB")
        
        if metrics["orders_per_minute"] > 100:
            alerts.append(f"High order rate: {metrics['orders_per_minute']:.1f}/min")
        
        if len(alerts) > 0:
            logger.warning(f"Alerts: {', '.join(alerts)}")
        
        return alerts
    
    def generate_report(self):
        """Generate monitoring report"""
        if not self.metrics_history:
            return "No metrics available"
        
        latest = self.metrics_history[-1]
        
        report = f"""
DATABASE MONITORING REPORT
========================
Timestamp: {latest['timestamp']}
Database Size: {latest['database_size_mb']:.1f}MB
Total Orders: {latest['total_orders']:,}
Open Positions: {latest['open_positions']:,}
Recent Activity (1 hour):
  - Orders: {latest['recent_orders_1h']:,}
  - Executions: {latest['recent_executions_1h']:,}
Activity Rates:
  - Orders/minute: {latest['orders_per_minute']:.1f}
  - Executions/minute: {latest['executions_per_minute']:.1f}
"""
        return report
    
    def run_monitoring(self):
        """Run continuous monitoring"""
        logger.info("Starting database monitoring...")
        
        while True:
            try:
                metrics = self.collect_metrics()
                if metrics:
                    alerts = self.check_alerts(metrics)
                    
                    # Log summary every 10 minutes
                    if datetime.now().minute % 10 == 0:
                        logger.info(f"DB: {metrics['database_size_mb']:.1f}MB, "
                                  f"Orders: {metrics['orders_per_minute']:.1f}/min, "
                                  f"Executions: {metrics['executions_per_minute']:.1f}/min")
                
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = DatabaseMonitor()
    
    print("📊 Database Monitoring Started")
    print("Press Ctrl+C to stop")
    
    try:
        monitor.run_monitoring()
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")
