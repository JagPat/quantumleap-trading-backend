#!/usr/bin/env python3
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
