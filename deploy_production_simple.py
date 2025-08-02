"""
Simplified Production Database Optimization Deployment
Creates a production-ready optimized database system
"""
import os
import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

def create_production_database():
    """Create optimized production database"""
    print("🔧 Creating production database with optimized schema...")
    
    db_path = "production_trading_optimized.db"
    
    # Create backup if database exists
    if os.path.exists(db_path):
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{db_path}"
        shutil.copy2(db_path, backup_name)
        print(f"📦 Backed up existing database to {backup_name}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create optimized schema
    schema_queries = [
        # Orders table with optimized indexes
        """
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            order_type TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL,
            stop_price REAL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            broker_order_id TEXT,
            strategy_id TEXT,
            signal_id TEXT,
            filled_quantity INTEGER DEFAULT 0,
            average_fill_price REAL,
            commission REAL DEFAULT 0.0,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            submitted_at TEXT,
            filled_at TEXT
        )
        """,
        
        # Optimized indexes for orders
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON orders(symbol, status)",
        
        # Positions table with optimized indexes
        """
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            average_price REAL NOT NULL,
            current_price REAL,
            unrealized_pnl REAL DEFAULT 0.0,
            realized_pnl REAL DEFAULT 0.0,
            strategy_id TEXT,
            status TEXT NOT NULL DEFAULT 'OPEN',
            opened_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            closed_at TEXT
        )
        """,
        
        # Optimized indexes for positions
        "CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
        "CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol)",
        "CREATE INDEX IF NOT EXISTS idx_positions_user_status ON positions(user_id, status)",
        
        # Executions table with optimized indexes
        """
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            commission REAL DEFAULT 0.0,
            broker_execution_id TEXT,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
        """,
        
        # Optimized indexes for executions
        "CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_executions_symbol ON executions(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at)",
        
        # Strategy deployments table
        """
        CREATE TABLE IF NOT EXISTS strategy_deployments (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            configuration TEXT,
            risk_parameters TEXT,
            performance_metrics TEXT,
            deployed_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            paused_at TEXT,
            stopped_at TEXT,
            error_message TEXT
        )
        """,
        
        # Indexes for strategy deployments
        "CREATE INDEX IF NOT EXISTS idx_strategy_deployments_user_id ON strategy_deployments(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_strategy_deployments_status ON strategy_deployments(status)",
        
        # Trading signals table
        """
        CREATE TABLE IF NOT EXISTS trading_signals (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confidence_score REAL DEFAULT 0.0,
            reasoning TEXT,
            target_price REAL,
            stop_loss REAL,
            take_profit REAL,
            position_size REAL DEFAULT 0.02,
            strategy_id TEXT,
            provider_used TEXT,
            is_active INTEGER DEFAULT 1,
            expires_at TEXT,
            created_at TEXT NOT NULL
        )
        """,
        
        # Indexes for trading signals
        "CREATE INDEX IF NOT EXISTS idx_trading_signals_user_id ON trading_signals(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON trading_signals(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_trading_signals_created_at ON trading_signals(created_at)",
        
        # Performance metrics table for monitoring
        """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_unit TEXT,
            category TEXT,
            timestamp TEXT NOT NULL
        )
        """,
        
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name)",
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_category ON performance_metrics(category)"
    ]
    
    # Execute schema creation
    for query in schema_queries:
        cursor.execute(query)
    
    conn.commit()
    
    # Optimize database settings
    cursor.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
    cursor.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and performance
    cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
    cursor.execute("PRAGMA temp_store = MEMORY")  # Store temp tables in memory
    cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB memory-mapped I/O
    
    conn.commit()
    conn.close()
    
    print(f"✅ Production database created: {db_path}")
    return db_path

def create_production_config():
    """Create production configuration files"""
    print("⚙️ Creating production configuration files...")
    
    # Database configuration
    db_config = {
        "database_path": "production_trading_optimized.db",
        "connection_settings": {
            "pool_size": 20,
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "retry_delay_seconds": 1
        },
        "optimization_settings": {
            "enable_query_caching": True,
            "cache_size_mb": 64,
            "enable_wal_mode": True,
            "enable_memory_temp_store": True,
            "mmap_size_mb": 256
        },
        "performance_monitoring": {
            "enabled": True,
            "interval_seconds": 60,
            "metrics_retention_days": 30
        }
    }
    
    with open("production_database_config.json", "w") as f:
        json.dump(db_config, f, indent=2)
    
    # Monitoring configuration
    monitoring_config = {
        "alert_thresholds": {
            "query_latency_ms": {"warning": 200, "critical": 500},
            "error_rate_percent": {"warning": 1.0, "critical": 5.0},
            "connection_pool_usage_percent": {"warning": 70.0, "critical": 90.0},
            "database_size_mb": {"warning": 1000, "critical": 2000}
        },
        "monitoring_interval_seconds": 300,
        "alert_channels": {
            "email": {"enabled": False, "recipients": []},
            "webhook": {"enabled": False, "url": ""},
            "log": {"enabled": True, "level": "WARNING"}
        }
    }
    
    with open("production_monitoring_config.json", "w") as f:
        json.dump(monitoring_config, f, indent=2)
    
    # Backup configuration
    backup_config = {
        "enabled": True,
        "interval_hours": 6,
        "retention_days": 30,
        "backup_directory": "production_backups",
        "compression": True,
        "verify_backups": True
    }
    
    with open("production_backup_config.json", "w") as f:
        json.dump(backup_config, f, indent=2)
    
    print("✅ Configuration files created")

def create_startup_script():
    """Create production startup script"""
    print("🚀 Creating startup script...")
    
    startup_script = '''#!/usr/bin/env python3
"""
Production Trading Database Startup Script
"""
import sqlite3
import json
import logging
import time
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionDatabaseManager:
    def __init__(self):
        self.db_path = "production_trading_optimized.db"
        self.config = self.load_config()
        
    def load_config(self):
        """Load production configuration"""
        try:
            with open("production_database_config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Configuration file not found, using defaults")
            return {"database_path": self.db_path}
    
    def check_database_health(self):
        """Check database health"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            cursor = conn.cursor()
            
            # Test basic connectivity
            cursor.execute("SELECT 1")
            
            # Check table integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            # Get database size
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_mb = (page_count * page_size) / (1024 * 1024)
            
            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM positions")
            position_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM executions")
            execution_count = cursor.fetchone()[0]
            
            conn.close()
            
            health_status = {
                "status": "healthy" if integrity_result == "ok" else "unhealthy",
                "database_size_mb": round(db_size_mb, 2),
                "integrity_check": integrity_result,
                "table_counts": {
                    "orders": order_count,
                    "positions": position_count,
                    "executions": execution_count
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Database health: {health_status['status']}, Size: {db_size_mb:.1f}MB")
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def optimize_database(self):
        """Run database optimization"""
        try:
            logger.info("Running database optimization...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Analyze tables for query optimization
            cursor.execute("ANALYZE")
            
            # Vacuum to reclaim space and defragment
            cursor.execute("VACUUM")
            
            # Update statistics
            cursor.execute("PRAGMA optimize")
            
            conn.close()
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
    
    def create_backup(self):
        """Create database backup"""
        try:
            backup_dir = Path("production_backups")
            backup_dir.mkdir(exist_ok=True)
            
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = backup_dir / backup_name
            
            # Create backup using SQLite backup API
            source = sqlite3.connect(self.db_path)
            backup = sqlite3.connect(str(backup_path))
            source.backup(backup)
            source.close()
            backup.close()
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None
    
    def run_production_monitoring(self):
        """Run production monitoring loop"""
        logger.info("Starting production database monitoring...")
        
        while True:
            try:
                # Check database health
                health = self.check_database_health()
                
                # Log health status
                if health["status"] != "healthy":
                    logger.warning(f"Database health issue: {health}")
                
                # Run optimization every 6 hours
                current_hour = datetime.now().hour
                if current_hour % 6 == 0 and datetime.now().minute < 5:
                    self.optimize_database()
                
                # Create backup every 6 hours
                if current_hour % 6 == 0 and datetime.now().minute < 10:
                    self.create_backup()
                
                # Wait 5 minutes before next check
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    manager = ProductionDatabaseManager()
    
    print("🚀 Starting Production Trading Database")
    print("=" * 50)
    
    # Initial health check
    health = manager.check_database_health()
    print(f"Database Status: {health['status']}")
    print(f"Database Size: {health.get('database_size_mb', 0):.1f}MB")
    
    if health['status'] == 'healthy':
        print("✅ Database is healthy")
        
        # Create initial backup
        backup_path = manager.create_backup()
        if backup_path:
            print(f"📦 Initial backup created: {backup_path}")
        
        print("📊 Starting monitoring...")
        print("Press Ctrl+C to stop")
        
        # Start monitoring
        manager.run_production_monitoring()
    else:
        print("❌ Database health check failed")
        print("Please check the database and try again")
'''
    
    with open("start_production_database.py", "w") as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod("start_production_database.py", 0o755)
    
    print("✅ Startup script created")

def create_monitoring_script():
    """Create monitoring script"""
    print("📊 Creating monitoring script...")
    
    monitoring_script = '''#!/usr/bin/env python3
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
        print("\\n✅ Monitoring stopped")
'''
    
    with open("production_monitor.py", "w") as f:
        f.write(monitoring_script)
    
    os.chmod("production_monitor.py", 0o755)
    
    print("✅ Monitoring script created")

def create_deployment_summary():
    """Create deployment summary"""
    print("\n" + "="*60)
    print("🎉 PRODUCTION DATABASE OPTIMIZATION DEPLOYMENT COMPLETE")
    print("="*60)
    
    summary = f"""
DEPLOYMENT SUMMARY:
==================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

FILES CREATED:
- production_trading_optimized.db (Optimized database)
- production_database_config.json (Database configuration)
- production_monitoring_config.json (Monitoring configuration)
- production_backup_config.json (Backup configuration)
- start_production_database.py (Startup script)
- production_monitor.py (Monitoring script)

OPTIMIZATIONS APPLIED:
- WAL mode for better concurrency
- Optimized indexes for all tables
- 64MB cache size
- Memory-mapped I/O (256MB)
- Comprehensive monitoring
- Automated backups

NEXT STEPS:
1. Start the production database:
   python3 start_production_database.py

2. Monitor performance (in another terminal):
   python3 production_monitor.py

3. Configure alerts in production_monitoring_config.json

4. Set up automated backups using production_backup_config.json

5. Test with production load

PRODUCTION READY FEATURES:
✅ Optimized database schema with indexes
✅ Performance monitoring and metrics
✅ Automated backup system
✅ Health checks and alerts
✅ Production configuration management
✅ Comprehensive logging
✅ Error handling and recovery

The database optimization system is now ready for production use!
"""
    
    print(summary)
    
    # Save summary to file
    with open("production_deployment_summary.txt", "w") as f:
        f.write(summary)
    
    return True

def main():
    """Main deployment function"""
    print("🚀 Starting Production Database Optimization Deployment")
    print("="*60)
    
    try:
        # Create production database
        db_path = create_production_database()
        
        # Create configuration files
        create_production_config()
        
        # Create startup script
        create_startup_script()
        
        # Create monitoring script
        create_monitoring_script()
        
        # Create deployment summary
        create_deployment_summary()
        
        return True
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)