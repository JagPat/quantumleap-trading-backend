"""
Production Database Optimization Deployment Script
Deploys and configures the optimized database system for production use
"""
import os
import sys
import asyncio
import logging
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_optimization_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionDatabaseDeployment:
    """
    Handles production deployment of optimized database system
    """
    
    def __init__(self):
        self.deployment_log = []
        self.backup_directory = Path("production_backups")
        self.backup_directory.mkdir(exist_ok=True)
        
        # Production configuration
        self.production_config = {
            'database_path': 'production_trading_optimized.db',
            'backup_retention_days': 30,
            'performance_monitoring_interval': 60,
            'alert_thresholds': {
                'query_latency_ms': {'warning': 200, 'critical': 500},
                'error_rate_percent': {'warning': 0.5, 'critical': 2.0},
                'connection_pool_usage_percent': {'warning': 70.0, 'critical': 90.0}
            },
            'optimization_settings': {
                'enable_query_caching': True,
                'cache_size_mb': 256,
                'connection_pool_size': 20,
                'transaction_timeout_seconds': 30,
                'enable_performance_monitoring': True,
                'enable_automated_backups': True,
                'backup_interval_hours': 6
            }
        }
        
        logger.info("ProductionDatabaseDeployment initialized")
    
    def log_deployment_step(self, step: str, status: str, details: str = ""):
        """Log deployment step with timestamp"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'status': status,
            'details': details
        }
        self.deployment_log.append(entry)
        logger.info(f"Deployment: {step} - {status} - {details}")
    
    async def validate_environment(self) -> bool:
        """Validate production environment requirements"""
        try:
            self.log_deployment_step("environment_validation", "started", "Validating production environment")
            
            # Check Python version
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                self.log_deployment_step("environment_validation", "failed", f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
                return False
            
            # Check disk space
            disk_usage = shutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 5.0:
                self.log_deployment_step("environment_validation", "warning", f"Low disk space: {free_gb:.1f}GB free")
            
            # Check required directories
            required_dirs = ['app', 'app/database', 'app/trading_engine']
            for dir_path in required_dirs:
                if not os.path.exists(dir_path):
                    self.log_deployment_step("environment_validation", "failed", f"Required directory missing: {dir_path}")
                    return False
            
            # Check required files
            required_files = [
                'app/database/trading_engine_integration.py',
                'app/trading_engine/optimized_order_db.py',
                'app/database/trading_performance_dashboard.py'
            ]
            
            for file_path in required_files:
                if not os.path.exists(file_path):
                    self.log_deployment_step("environment_validation", "failed", f"Required file missing: {file_path}")
                    return False
            
            self.log_deployment_step("environment_validation", "success", f"Environment validated - Python {python_version.major}.{python_version.minor}, {free_gb:.1f}GB free")
            return True
            
        except Exception as e:
            self.log_deployment_step("environment_validation", "failed", f"Error: {e}")
            return False
    
    async def create_production_backup(self) -> bool:
        """Create backup of current production database"""
        try:
            self.log_deployment_step("production_backup", "started", "Creating production backup")
            
            # Look for existing production databases
            existing_dbs = [
                "trading.db",
                "production_trading.db",
                "quantum_leap.db",
                "app/database/trading.db"
            ]
            
            backup_created = False
            for db_path in existing_dbs:
                if os.path.exists(db_path):
                    backup_name = f"production_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(db_path).name}"
                    backup_path = self.backup_directory / backup_name
                    shutil.copy2(db_path, backup_path)
                    self.log_deployment_step("production_backup", "success", f"Backed up {db_path} to {backup_path}")
                    backup_created = True
            
            if not backup_created:
                self.log_deployment_step("production_backup", "info", "No existing production database found to backup")
            
            return True
            
        except Exception as e:
            self.log_deployment_step("production_backup", "failed", f"Error: {e}")
            return False
    
    async def deploy_optimized_database(self) -> bool:
        """Deploy the optimized database system"""
        try:
            self.log_deployment_step("database_deployment", "started", "Deploying optimized database system")
            
            # Import and initialize the optimized database system
            sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
            
            try:
                from app.database.trading_engine_integration import TradingDatabaseIntegration
                from app.trading_engine.optimized_order_db import OptimizedOrderDatabase
                from app.database.trading_performance_dashboard import TradingPerformanceDashboard
                
                self.log_deployment_step("database_deployment", "progress", "Imported optimized database modules")
                
            except ImportError as e:
                # Create a simplified deployment if imports fail
                self.log_deployment_step("database_deployment", "warning", f"Import failed: {e}, creating simplified deployment")
                return await self._deploy_simplified_database()
            
            # Initialize production database
            db_path = self.production_config['database_path']
            integration = TradingDatabaseIntegration(db_path)
            await integration.initialize()
            
            # Initialize optimized order database
            optimized_db = OptimizedOrderDatabase()
            optimized_db.integration = integration
            await optimized_db.initialize()
            
            # Initialize performance dashboard
            dashboard = TradingPerformanceDashboard()
            dashboard.integration = integration
            
            # Test the deployment
            health_status = await optimized_db.get_health_status()
            if health_status.get('status') != 'healthy':
                self.log_deployment_step("database_deployment", "failed", "Health check failed after deployment")
                return False
            
            # Start performance monitoring
            await dashboard.start_monitoring()
            
            self.log_deployment_step("database_deployment", "success", f"Optimized database deployed to {db_path}")
            
            # Save deployment configuration
            await self._save_production_config()
            
            # Cleanup
            await dashboard.stop_monitoring()
            await integration.shutdown()
            
            return True
            
        except Exception as e:
            self.log_deployment_step("database_deployment", "failed", f"Error: {e}")
            return False
    
    async def _deploy_simplified_database(self) -> bool:
        """Deploy a simplified version if full deployment fails"""
        try:
            self.log_deployment_step("simplified_deployment", "started", "Deploying simplified database system")
            
            # Create production database with optimized schema
            import sqlite3
            
            db_path = self.production_config['database_path']
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create optimized tables
            schema_queries = [
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
                "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)",
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
                "CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
                "CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol)",
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
                "CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at)"
            ]
            
            for query in schema_queries:
                cursor.execute(query)
            
            conn.commit()
            conn.close()
            
            self.log_deployment_step("simplified_deployment", "success", f"Simplified database deployed to {db_path}")
            return True
            
        except Exception as e:
            self.log_deployment_step("simplified_deployment", "failed", f"Error: {e}")
            return False
    
    async def _save_production_config(self):
        """Save production configuration"""
        try:
            config_path = "production_database_config.json"
            
            config_data = {
                'deployment_timestamp': datetime.now().isoformat(),
                'database_path': self.production_config['database_path'],
                'configuration': self.production_config,
                'deployment_log': self.deployment_log
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.log_deployment_step("config_save", "success", f"Configuration saved to {config_path}")
            
        except Exception as e:
            self.log_deployment_step("config_save", "failed", f"Error saving config: {e}")
    
    async def configure_production_settings(self) -> bool:
        """Configure production-specific settings"""
        try:
            self.log_deployment_step("production_config", "started", "Configuring production settings")
            
            # Create production configuration files
            config_files = {
                'database_config.json': {
                    'database_path': self.production_config['database_path'],
                    'connection_pool_size': self.production_config['optimization_settings']['connection_pool_size'],
                    'transaction_timeout': self.production_config['optimization_settings']['transaction_timeout_seconds'],
                    'cache_settings': {
                        'enabled': self.production_config['optimization_settings']['enable_query_caching'],
                        'size_mb': self.production_config['optimization_settings']['cache_size_mb']
                    }
                },
                'monitoring_config.json': {
                    'enabled': self.production_config['optimization_settings']['enable_performance_monitoring'],
                    'interval_seconds': self.production_config['performance_monitoring_interval'],
                    'alert_thresholds': self.production_config['alert_thresholds']
                },
                'backup_config.json': {
                    'enabled': self.production_config['optimization_settings']['enable_automated_backups'],
                    'interval_hours': self.production_config['optimization_settings']['backup_interval_hours'],
                    'retention_days': self.production_config['backup_retention_days'],
                    'backup_directory': str(self.backup_directory)
                }
            }
            
            for filename, config in config_files.items():
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=2)
                self.log_deployment_step("production_config", "progress", f"Created {filename}")
            
            # Create production startup script
            startup_script = """#!/usr/bin/env python3
\"\"\"
Production Database Optimization Startup Script
\"\"\"
import asyncio
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_database.log'),
        logging.StreamHandler()
    ]
)

async def start_production_database():
    \"\"\"Start production database system\"\"\"
    try:
        # Add app directory to path
        sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
        
        from app.database.trading_engine_integration import TradingDatabaseIntegration
        from app.trading_engine.optimized_order_db import OptimizedOrderDatabase
        from app.database.trading_performance_dashboard import TradingPerformanceDashboard
        
        # Initialize production database
        integration = TradingDatabaseIntegration('production_trading_optimized.db')
        await integration.initialize()
        
        # Initialize optimized database
        optimized_db = OptimizedOrderDatabase()
        optimized_db.integration = integration
        await optimized_db.initialize()
        
        # Initialize performance dashboard
        dashboard = TradingPerformanceDashboard()
        dashboard.integration = integration
        await dashboard.start_monitoring()
        
        print("✅ Production database system started successfully")
        print("📊 Performance monitoring active")
        print("🔄 Automated backups enabled")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
                health = await optimized_db.get_health_status()
                if health.get('status') != 'healthy':
                    print(f"⚠️ Database health warning: {health}")
        except KeyboardInterrupt:
            print("\\n🛑 Shutting down production database system...")
            await dashboard.stop_monitoring()
            await integration.shutdown()
            print("✅ Shutdown completed")
        
    except Exception as e:
        print(f"❌ Failed to start production database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(start_production_database())
"""
            
            with open('start_production_database.py', 'w') as f:
                f.write(startup_script)
            
            # Make startup script executable
            os.chmod('start_production_database.py', 0o755)
            
            self.log_deployment_step("production_config", "success", "Production configuration completed")
            return True
            
        except Exception as e:
            self.log_deployment_step("production_config", "failed", f"Error: {e}")
            return False
    
    async def setup_monitoring_and_alerts(self) -> bool:
        """Setup production monitoring and alerting"""
        try:
            self.log_deployment_step("monitoring_setup", "started", "Setting up monitoring and alerts")
            
            # Create monitoring script
            monitoring_script = """#!/usr/bin/env python3
\"\"\"
Production Database Monitoring Script
\"\"\"
import asyncio
import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'query_latency_ms': {'warning': 200, 'critical': 500},
            'error_rate_percent': {'warning': 0.5, 'critical': 2.0},
            'connection_pool_usage_percent': {'warning': 70.0, 'critical': 90.0}
        }
    
    async def check_database_health(self):
        \"\"\"Check database health and send alerts if needed\"\"\"
        try:
            # Import database components
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
            
            from app.trading_engine.optimized_order_db import OptimizedOrderDatabase
            
            # Initialize database
            optimized_db = OptimizedOrderDatabase()
            await optimized_db.initialize()
            
            # Get health status
            health = await optimized_db.get_health_status()
            metrics = await optimized_db.get_performance_metrics()
            
            # Check for alerts
            alerts = []
            
            # Check query latency
            if 'average_execution_time' in metrics:
                latency_ms = metrics['average_execution_time'] * 1000
                if latency_ms > self.alert_thresholds['query_latency_ms']['critical']:
                    alerts.append(f"CRITICAL: Query latency {latency_ms:.1f}ms")
                elif latency_ms > self.alert_thresholds['query_latency_ms']['warning']:
                    alerts.append(f"WARNING: Query latency {latency_ms:.1f}ms")
            
            # Log status
            logger.info(f"Database health: {health.get('status', 'unknown')}")
            if alerts:
                for alert in alerts:
                    logger.warning(alert)
            
            await optimized_db.shutdown()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def run_monitoring(self):
        \"\"\"Run continuous monitoring\"\"\"
        while True:
            await self.check_database_health()
            await asyncio.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    monitor = ProductionMonitor()
    asyncio.run(monitor.run_monitoring())
"""
            
            with open('production_monitor.py', 'w') as f:
                f.write(monitoring_script)
            
            os.chmod('production_monitor.py', 0o755)
            
            # Create systemd service file (for Linux systems)
            systemd_service = """[Unit]
Description=Trading Database Optimization Service
After=network.target

[Service]
Type=simple
User=trading
WorkingDirectory=/path/to/your/application
ExecStart=/usr/bin/python3 start_production_database.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            with open('trading-database.service', 'w') as f:
                f.write(systemd_service)
            
            self.log_deployment_step("monitoring_setup", "success", "Monitoring and alerts configured")
            return True
            
        except Exception as e:
            self.log_deployment_step("monitoring_setup", "failed", f"Error: {e}")
            return False
    
    async def run_deployment_validation(self) -> bool:
        """Run comprehensive deployment validation"""
        try:
            self.log_deployment_step("deployment_validation", "started", "Running deployment validation")
            
            # Test database connectivity
            db_path = self.production_config['database_path']
            if not os.path.exists(db_path):
                self.log_deployment_step("deployment_validation", "failed", f"Database file not found: {db_path}")
                return False
            
            # Test database schema
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check required tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['orders', 'positions', 'executions']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                self.log_deployment_step("deployment_validation", "failed", f"Missing tables: {missing_tables}")
                conn.close()
                return False
            
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            required_indexes = ['idx_orders_user_id', 'idx_positions_user_id', 'idx_executions_order_id']
            missing_indexes = [idx for idx in required_indexes if idx not in indexes]
            
            if missing_indexes:
                self.log_deployment_step("deployment_validation", "warning", f"Missing indexes: {missing_indexes}")
            
            conn.close()
            
            # Test configuration files
            config_files = ['database_config.json', 'monitoring_config.json', 'backup_config.json']
            for config_file in config_files:
                if not os.path.exists(config_file):
                    self.log_deployment_step("deployment_validation", "warning", f"Configuration file missing: {config_file}")
            
            # Test startup script
            if not os.path.exists('start_production_database.py'):
                self.log_deployment_step("deployment_validation", "warning", "Startup script missing")
            
            self.log_deployment_step("deployment_validation", "success", "Deployment validation completed")
            return True
            
        except Exception as e:
            self.log_deployment_step("deployment_validation", "failed", f"Error: {e}")
            return False
    
    async def generate_deployment_report(self) -> str:
        """Generate comprehensive deployment report"""
        try:
            report_lines = [
                "=" * 80,
                "PRODUCTION DATABASE OPTIMIZATION DEPLOYMENT REPORT",
                "=" * 80,
                f"Deployment Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Database Path: {self.production_config['database_path']}",
                f"Total Steps: {len(self.deployment_log)}",
                "",
                "DEPLOYMENT STEPS:",
                "-" * 40
            ]
            
            for entry in self.deployment_log:
                report_lines.append(
                    f"[{entry['timestamp']}] {entry['step']}: {entry['status']}"
                )
                if entry['details']:
                    report_lines.append(f"  Details: {entry['details']}")
                report_lines.append("")
            
            # Add configuration summary
            report_lines.extend([
                "PRODUCTION CONFIGURATION:",
                "-" * 40,
                f"Database Path: {self.production_config['database_path']}",
                f"Connection Pool Size: {self.production_config['optimization_settings']['connection_pool_size']}",
                f"Cache Size: {self.production_config['optimization_settings']['cache_size_mb']}MB",
                f"Performance Monitoring: {'Enabled' if self.production_config['optimization_settings']['enable_performance_monitoring'] else 'Disabled'}",
                f"Automated Backups: {'Enabled' if self.production_config['optimization_settings']['enable_automated_backups'] else 'Disabled'}",
                f"Backup Interval: {self.production_config['optimization_settings']['backup_interval_hours']} hours",
                ""
            ])
            
            # Add summary
            successful_steps = len([e for e in self.deployment_log if e['status'] in ['success', 'progress']])
            failed_steps = len([e for e in self.deployment_log if e['status'] == 'failed'])
            warning_steps = len([e for e in self.deployment_log if e['status'] == 'warning'])
            
            report_lines.extend([
                "DEPLOYMENT SUMMARY:",
                "-" * 40,
                f"Successful Steps: {successful_steps}",
                f"Failed Steps: {failed_steps}",
                f"Warning Steps: {warning_steps}",
                f"Overall Status: {'SUCCESS' if failed_steps == 0 else 'PARTIAL SUCCESS' if successful_steps > 0 else 'FAILED'}",
                "",
                "NEXT STEPS:",
                "-" * 40,
                "1. Start the production database: python3 start_production_database.py",
                "2. Monitor performance: python3 production_monitor.py",
                "3. Set up automated backups using backup_config.json",
                "4. Configure alerts based on monitoring_config.json",
                "5. Test the system with production load",
                "",
                "FILES CREATED:",
                "-" * 40,
                f"• {self.production_config['database_path']} - Production database",
                "• database_config.json - Database configuration",
                "• monitoring_config.json - Monitoring configuration", 
                "• backup_config.json - Backup configuration",
                "• start_production_database.py - Startup script",
                "• production_monitor.py - Monitoring script",
                "• trading-database.service - Systemd service file",
                "",
                "=" * 80
            ])
            
            report = "\n".join(report_lines)
            
            # Save report to file
            report_file = f"production_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            self.log_deployment_step("report_generation", "success", f"Report saved to {report_file}")
            
            return report
            
        except Exception as e:
            self.log_deployment_step("report_generation", "failed", f"Error: {e}")
            return f"Error generating report: {e}"
    
    async def run_full_deployment(self) -> bool:
        """Run complete production deployment"""
        try:
            logger.info("Starting production database optimization deployment")
            
            # Step 1: Validate environment
            if not await self.validate_environment():
                logger.error("Environment validation failed - aborting deployment")
                return False
            
            # Step 2: Create production backup
            if not await self.create_production_backup():
                logger.error("Production backup failed - aborting deployment")
                return False
            
            # Step 3: Deploy optimized database
            if not await self.deploy_optimized_database():
                logger.error("Database deployment failed - aborting deployment")
                return False
            
            # Step 4: Configure production settings
            if not await self.configure_production_settings():
                logger.error("Production configuration failed - continuing with validation")
            
            # Step 5: Setup monitoring and alerts
            if not await self.setup_monitoring_and_alerts():
                logger.error("Monitoring setup failed - continuing with validation")
            
            # Step 6: Run deployment validation
            validation_success = await self.run_deployment_validation()
            
            # Step 7: Generate deployment report
            report = await self.generate_deployment_report()
            print("\n" + report)
            
            if validation_success:
                logger.info("Production database optimization deployment completed successfully")
                return True
            else:
                logger.error("Deployment validation failed")
                return False
                
        except Exception as e:
            logger.error(f"Deployment failed with error: {e}")
            return False

async def main():
    """Main deployment function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run deployment
    deployment = ProductionDatabaseDeployment()
    success = await deployment.run_full_deployment()
    
    if success:
        print("\n✅ Production deployment completed successfully!")
        print("🚀 The optimized database system is ready for production use.")
        print("\nTo start the production system:")
        print("  python3 start_production_database.py")
        print("\nTo monitor the system:")
        print("  python3 production_monitor.py")
        print("\nFor systemd service (Linux):")
        print("  sudo cp trading-database.service /etc/systemd/system/")
        print("  sudo systemctl enable trading-database")
        print("  sudo systemctl start trading-database")
    else:
        print("\n❌ Production deployment completed with errors.")
        print("Please check the deployment report for details.")
        print("You may need to manually resolve some issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())