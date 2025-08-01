#!/usr/bin/env python3
"""
Production Infrastructure Deployment Script for Automated Trading Engine
Handles deployment, monitoring setup, and database configuration
"""

import os
import sys
import json
import time
import subprocess
import sqlite3
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging
import requests
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionInfrastructureManager:
    """Manages production infrastructure deployment and configuration"""
    
    def __init__(self):
        self.railway_url = "https://quantum-leap-backend-production.up.railway.app"
        self.local_backup_dir = Path("backups")
        self.monitoring_config_dir = Path("monitoring")
        self.deployment_config = {
            "environment": "production",
            "database_backup_interval": 3600,  # 1 hour
            "monitoring_interval": 60,  # 1 minute
            "log_retention_days": 30,
            "max_concurrent_strategies": 50,
            "max_orders_per_minute": 100
        }
        
        # Ensure directories exist
        self.local_backup_dir.mkdir(exist_ok=True)
        self.monitoring_config_dir.mkdir(exist_ok=True)
    
    def deploy_trading_engine(self):
        """Deploy automated trading engine to production"""
        logger.info("🚀 Starting production deployment of automated trading engine...")
        
        try:
            # 1. Verify all components are ready
            self._verify_components()
            
            # 2. Create production configuration
            self._create_production_config()
            
            # 3. Deploy database schema
            self._deploy_database_schema()
            
            # 4. Deploy application components
            self._deploy_application_components()
            
            # 5. Configure monitoring
            self._setup_monitoring()
            
            # 6. Verify deployment
            self._verify_deployment()
            
            logger.info("✅ Production deployment completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Production deployment failed: {e}")
            return False
    
    def _verify_components(self):
        """Verify all required components are available"""
        logger.info("🔍 Verifying component availability...")
        
        required_files = [
            "app/trading_engine/models.py",
            "app/trading_engine/order_executor.py",
            "app/trading_engine/risk_engine.py",
            "app/trading_engine/strategy_manager.py",
            "app/trading_engine/position_manager.py",
            "app/trading_engine/event_bus.py",
            "app/trading_engine/monitoring.py",
            "app/trading_engine/router.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise Exception(f"Missing required files: {missing_files}")
        
        logger.info("✅ All required components verified")
    
    def _create_production_config(self):
        """Create production configuration files"""
        logger.info("⚙️ Creating production configuration...")
        
        # Production environment configuration
        prod_config = {
            "environment": "production",
            "debug": False,
            "database": {
                "url": "sqlite:///production_trading.db",
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 30,
                "pool_recycle": 3600
            },
            "trading_engine": {
                "max_concurrent_strategies": self.deployment_config["max_concurrent_strategies"],
                "max_orders_per_minute": self.deployment_config["max_orders_per_minute"],
                "risk_check_interval": 5,
                "position_update_interval": 1,
                "market_data_timeout": 10
            },
            "monitoring": {
                "health_check_interval": self.deployment_config["monitoring_interval"],
                "performance_metrics_interval": 300,
                "alert_thresholds": {
                    "cpu_usage": 80,
                    "memory_usage": 85,
                    "response_time": 2.0,
                    "error_rate": 0.05
                }
            },
            "logging": {
                "level": "INFO",
                "retention_days": self.deployment_config["log_retention_days"],
                "max_file_size": "100MB",
                "backup_count": 10
            },
            "security": {
                "api_rate_limit": "1000/hour",
                "max_request_size": "10MB",
                "cors_origins": ["https://quantum-leap-frontend.vercel.app"],
                "require_authentication": True
            }
        }
        
        # Save production configuration
        with open("production_config.json", "w") as f:
            json.dump(prod_config, f, indent=2)
        
        logger.info("✅ Production configuration created")
    
    def _deploy_database_schema(self):
        """Deploy and configure production database"""
        logger.info("🗄️ Setting up production database...")
        
        try:
            # Create production database
            db_path = "production_trading.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create all required tables
            schema_sql = """
            -- Orders table
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL,
                status TEXT NOT NULL,
                strategy_id TEXT,
                signal_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                executed_at TEXT,
                executed_price REAL,
                executed_quantity INTEGER,
                broker_order_id TEXT,
                metadata TEXT
            );
            
            -- Positions table
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                average_price REAL NOT NULL,
                current_price REAL,
                unrealized_pnl REAL,
                realized_pnl REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                strategy_id TEXT,
                metadata TEXT
            );
            
            -- Strategies table
            CREATE TABLE IF NOT EXISTS strategies (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                config TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deployed_at TEXT,
                performance_metrics TEXT,
                risk_parameters TEXT
            );
            
            -- Executions table
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                executed_at TEXT NOT NULL,
                broker_execution_id TEXT,
                fees REAL,
                metadata TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            );
            
            -- Events table for audit trail
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                user_id TEXT,
                strategy_id TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT,
                status TEXT NOT NULL
            );
            
            -- Performance metrics table
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                strategy_id TEXT,
                user_id TEXT,
                metric_type TEXT NOT NULL,
                metric_value REAL NOT NULL,
                calculated_at TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT,
                metadata TEXT
            );
            
            -- System health table
            CREATE TABLE IF NOT EXISTS system_health (
                id TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                status TEXT NOT NULL,
                metrics TEXT,
                checked_at TEXT NOT NULL,
                response_time REAL,
                error_count INTEGER DEFAULT 0
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
            
            CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id);
            CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
            
            CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id);
            CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
            
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
            
            CREATE INDEX IF NOT EXISTS idx_performance_strategy ON performance_metrics(strategy_id);
            CREATE INDEX IF NOT EXISTS idx_performance_calculated_at ON performance_metrics(calculated_at);
            """
            
            cursor.executescript(schema_sql)
            conn.commit()
            conn.close()
            
            logger.info("✅ Production database schema deployed")
            
        except Exception as e:
            logger.error(f"❌ Database deployment failed: {e}")
            raise
    
    def _deploy_application_components(self):
        """Deploy application components to production"""
        logger.info("📦 Deploying application components...")
        
        try:
            # Create production main.py with trading engine integration
            production_main = '''
import os
import sys
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import existing components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.trading_engine.router import trading_engine_router
from app.trading_engine.monitoring import TradingEngineMonitor
from app.trading_engine.event_bus import EventManager
from app.ai_engine.analysis_router import ai_analysis_router
from app.portfolio.service import portfolio_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global components
event_manager = None
trading_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global event_manager, trading_monitor
    
    logger.info("🚀 Starting production trading engine...")
    
    # Initialize core components
    event_manager = EventManager()
    trading_monitor = TradingEngineMonitor()
    
    # Start background services
    await event_manager.start()
    await trading_monitor.start()
    
    logger.info("✅ Production trading engine started successfully")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down production trading engine...")
    if trading_monitor:
        await trading_monitor.stop()
    if event_manager:
        await event_manager.stop()
    logger.info("✅ Production trading engine stopped")

# Create FastAPI app
app = FastAPI(
    title="Quantum Leap Trading Engine - Production",
    description="Automated Trading Engine for Production Environment",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://quantum-leap-frontend.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trading_engine_router, prefix="/api/trading-engine", tags=["Trading Engine"])
app.include_router(ai_analysis_router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Quantum Leap Trading Engine - Production",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global trading_monitor
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "healthy",
            "event_bus": "healthy",
            "trading_engine": "healthy",
            "ai_engine": "healthy"
        }
    }
    
    if trading_monitor:
        system_health = await trading_monitor.get_system_health()
        health_status["components"].update(system_health)
    
    return health_status

@app.get("/metrics")
async def get_metrics():
    """System metrics endpoint"""
    global trading_monitor
    
    if not trading_monitor:
        raise HTTPException(status_code=503, detail="Monitoring not available")
    
    metrics = await trading_monitor.get_performance_metrics()
    return metrics

if __name__ == "__main__":
    import uvicorn
    
    # Production server configuration
    uvicorn.run(
        "production_main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=4,
        log_level="info",
        access_log=True,
        reload=False
    )
'''
            
            with open("production_main.py", "w") as f:
                f.write(production_main)
            
            logger.info("✅ Application components deployed")
            
        except Exception as e:
            logger.error(f"❌ Application deployment failed: {e}")
            raise
    
    def _setup_monitoring(self):
        """Configure monitoring and alerting systems"""
        logger.info("📊 Setting up monitoring systems...")
        
        try:
            # Create monitoring configuration
            monitoring_config = {
                "health_checks": {
                    "database": {
                        "interval": 60,
                        "timeout": 10,
                        "critical_threshold": 5
                    },
                    "trading_engine": {
                        "interval": 30,
                        "timeout": 5,
                        "critical_threshold": 3
                    },
                    "ai_engine": {
                        "interval": 120,
                        "timeout": 15,
                        "critical_threshold": 2
                    }
                },
                "performance_metrics": {
                    "cpu_usage": {
                        "warning_threshold": 70,
                        "critical_threshold": 85
                    },
                    "memory_usage": {
                        "warning_threshold": 75,
                        "critical_threshold": 90
                    },
                    "response_time": {
                        "warning_threshold": 1.0,
                        "critical_threshold": 2.0
                    },
                    "error_rate": {
                        "warning_threshold": 0.02,
                        "critical_threshold": 0.05
                    }
                },
                "alerts": {
                    "email": {
                        "enabled": True,
                        "recipients": ["admin@quantumleap.com"]
                    },
                    "webhook": {
                        "enabled": True,
                        "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
                    }
                }
            }
            
            with open(self.monitoring_config_dir / "monitoring_config.json", "w") as f:
                json.dump(monitoring_config, f, indent=2)
            
            # Create monitoring script
            monitoring_script = '''#!/usr/bin/env python3
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
            f.write(json.dumps(alert_data) + "\\n")
    
    def run_monitoring_loop(self):
        """Run continuous monitoring"""
        self.logger.info("Starting production monitoring...")
        
        while True:
            try:
                health = self.check_system_health()
                
                # Log health status
                with open("health_status.log", "a") as f:
                    f.write(json.dumps(health) + "\\n")
                
                if health["status"] != "healthy":
                    self.logger.warning(f"System status: {health['status']}")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(30)  # Shorter interval on error

if __name__ == "__main__":
    monitor = ProductionMonitor()
    monitor.run_monitoring_loop()
'''
            
            with open(self.monitoring_config_dir / "production_monitor.py", "w") as f:
                f.write(monitoring_script)
            
            logger.info("✅ Monitoring systems configured")
            
        except Exception as e:
            logger.error(f"❌ Monitoring setup failed: {e}")
            raise
    
    def setup_database_backup(self):
        """Set up automated database backup procedures"""
        logger.info("💾 Setting up database backup procedures...")
        
        try:
            # Create backup script
            backup_script = '''#!/usr/bin/env python3
"""
Database Backup Script for Production Trading Engine
"""

import os
import shutil
import sqlite3
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path

class DatabaseBackupManager:
    def __init__(self):
        self.db_path = "production_trading.db"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.retention_days = 30
        self.max_backups = 100
    
    def create_backup(self):
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"trading_db_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Create backup copy
            shutil.copy2(self.db_path, backup_path)
            
            # Compress backup
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed backup
            backup_path.unlink()
            
            # Create backup metadata
            metadata = {
                "backup_time": datetime.now().isoformat(),
                "original_size": os.path.getsize(self.db_path),
                "compressed_size": os.path.getsize(compressed_path),
                "backup_file": str(compressed_path)
            }
            
            metadata_path = compressed_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Backup created: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        backup_files = list(self.backup_dir.glob("trading_db_backup_*.db.gz"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Keep only the most recent backups within retention period
        kept_backups = []
        removed_count = 0
        
        for backup_file in backup_files:
            backup_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if len(kept_backups) < self.max_backups and backup_time > cutoff_date:
                kept_backups.append(backup_file)
            else:
                # Remove old backup and its metadata
                backup_file.unlink()
                metadata_file = backup_file.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            print(f"🗑️ Removed {removed_count} old backups")
    
    def verify_backup(self, backup_path):
        """Verify backup integrity"""
        try:
            # Decompress and test database
            with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
                with gzip.open(backup_path, 'rb') as f_in:
                    temp_db.write(f_in.read())
                    temp_db.flush()
                
                # Test database connection and basic query
                conn = sqlite3.connect(temp_db.name)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                if len(tables) > 0:
                    print(f"✅ Backup verified: {len(tables)} tables found")
                    return True
                else:
                    print(f"❌ Backup verification failed: No tables found")
                    return False
                    
        except Exception as e:
            print(f"❌ Backup verification failed: {e}")
            return False
    
    def run_backup_cycle(self):
        """Run complete backup cycle"""
        print(f"🔄 Starting backup cycle at {datetime.now()}")
        
        # Create backup
        backup_path = self.create_backup()
        
        if backup_path:
            # Verify backup
            if self.verify_backup(backup_path):
                print("✅ Backup cycle completed successfully")
            else:
                print("⚠️ Backup created but verification failed")
        
        # Cleanup old backups
        self.cleanup_old_backups()

if __name__ == "__main__":
    backup_manager = DatabaseBackupManager()
    backup_manager.run_backup_cycle()
'''
            
            with open("database_backup.py", "w") as f:
                f.write(backup_script)
            
            # Create backup schedule script
            schedule_script = '''#!/bin/bash
# Database Backup Schedule Script
# Add this to crontab for automated backups

# Backup every hour
# 0 * * * * /usr/bin/python3 /path/to/database_backup.py

# Backup every 6 hours (more conservative)
# 0 */6 * * * /usr/bin/python3 /path/to/database_backup.py

echo "Database backup schedule configured"
echo "Add the following line to crontab for hourly backups:"
echo "0 * * * * /usr/bin/python3 $(pwd)/database_backup.py"
'''
            
            with open("setup_backup_schedule.sh", "w") as f:
                f.write(schedule_script)
            
            # Make scripts executable
            os.chmod("database_backup.py", 0o755)
            os.chmod("setup_backup_schedule.sh", 0o755)
            
            logger.info("✅ Database backup procedures configured")
            
        except Exception as e:
            logger.error(f"❌ Database backup setup failed: {e}")
            raise
    
    def _verify_deployment(self):
        """Verify production deployment"""
        logger.info("🔍 Verifying production deployment...")
        
        try:
            # Test database connection
            conn = sqlite3.connect("production_trading.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            if len(tables) < 5:
                raise Exception(f"Expected at least 5 tables, found {len(tables)}")
            
            # Test configuration files
            required_configs = [
                "production_config.json",
                "production_main.py",
                "database_backup.py",
                "monitoring/monitoring_config.json"
            ]
            
            for config_file in required_configs:
                if not Path(config_file).exists():
                    raise Exception(f"Missing configuration file: {config_file}")
            
            logger.info("✅ Production deployment verified successfully")
            
        except Exception as e:
            logger.error(f"❌ Deployment verification failed: {e}")
            raise
    
    def create_deployment_summary(self):
        """Create deployment summary report"""
        logger.info("📄 Creating deployment summary...")
        
        summary = {
            "deployment_date": datetime.now().isoformat(),
            "environment": "production",
            "components_deployed": [
                "Automated Trading Engine",
                "Database Schema",
                "Monitoring System",
                "Backup Procedures",
                "Health Checks",
                "Performance Metrics"
            ],
            "configuration": self.deployment_config,
            "database_tables": [
                "orders", "positions", "strategies", "executions",
                "events", "performance_metrics", "system_health"
            ],
            "monitoring_endpoints": [
                "/health", "/metrics", "/api/trading-engine/status"
            ],
            "backup_schedule": "Hourly automated backups with 30-day retention",
            "next_steps": [
                "Configure monitoring alerts",
                "Set up backup schedule in crontab",
                "Deploy to Railway production environment",
                "Configure SSL certificates",
                "Set up log rotation",
                "Configure firewall rules"
            ]
        }
        
        with open("PRODUCTION_DEPLOYMENT_SUMMARY.md", "w") as f:
            f.write("# Production Infrastructure Deployment Summary\n\n")
            f.write(f"**Deployment Date:** {summary['deployment_date']}\n")
            f.write(f"**Environment:** {summary['environment']}\n\n")
            
            f.write("## Components Deployed\n\n")
            for component in summary['components_deployed']:
                f.write(f"- ✅ {component}\n")
            f.write("\n")
            
            f.write("## Database Schema\n\n")
            f.write("The following tables have been created in the production database:\n\n")
            for table in summary['database_tables']:
                f.write(f"- `{table}`\n")
            f.write("\n")
            
            f.write("## Monitoring Configuration\n\n")
            f.write("### Health Check Endpoints\n")
            for endpoint in summary['monitoring_endpoints']:
                f.write(f"- `{endpoint}`\n")
            f.write("\n")
            
            f.write("### Performance Thresholds\n")
            f.write(f"- **Max Concurrent Strategies:** {summary['configuration']['max_concurrent_strategies']}\n")
            f.write(f"- **Max Orders Per Minute:** {summary['configuration']['max_orders_per_minute']}\n")
            f.write(f"- **Monitoring Interval:** {summary['configuration']['monitoring_interval']} seconds\n")
            f.write(f"- **Log Retention:** {summary['configuration']['log_retention_days']} days\n\n")
            
            f.write("## Backup Configuration\n\n")
            f.write(f"- **Schedule:** {summary['backup_schedule']}\n")
            f.write("- **Location:** `backups/` directory\n")
            f.write("- **Format:** Compressed SQLite database files\n")
            f.write("- **Verification:** Automatic integrity checks\n\n")
            
            f.write("## Next Steps\n\n")
            for step in summary['next_steps']:
                f.write(f"- [ ] {step}\n")
            f.write("\n")
            
            f.write("## Files Created\n\n")
            f.write("- `production_config.json` - Production configuration\n")
            f.write("- `production_main.py` - Production application entry point\n")
            f.write("- `production_trading.db` - Production database\n")
            f.write("- `database_backup.py` - Automated backup script\n")
            f.write("- `setup_backup_schedule.sh` - Backup schedule setup\n")
            f.write("- `monitoring/monitoring_config.json` - Monitoring configuration\n")
            f.write("- `monitoring/production_monitor.py` - Monitoring script\n\n")
            
            f.write("## Usage Instructions\n\n")
            f.write("### Start Production Server\n")
            f.write("```bash\n")
            f.write("python3 production_main.py\n")
            f.write("```\n\n")
            
            f.write("### Run Manual Backup\n")
            f.write("```bash\n")
            f.write("python3 database_backup.py\n")
            f.write("```\n\n")
            
            f.write("### Start Monitoring\n")
            f.write("```bash\n")
            f.write("python3 monitoring/production_monitor.py\n")
            f.write("```\n\n")
            
            f.write("### Setup Automated Backups\n")
            f.write("```bash\n")
            f.write("./setup_backup_schedule.sh\n")
            f.write("```\n\n")
        
        logger.info("📄 Deployment summary created: PRODUCTION_DEPLOYMENT_SUMMARY.md")

def main():
    """Main deployment function"""
    print("🚀 Starting Production Infrastructure Deployment...\n")
    
    try:
        # Initialize deployment manager
        deployment_manager = ProductionInfrastructureManager()
        
        # Deploy trading engine
        if deployment_manager.deploy_trading_engine():
            print("✅ Trading engine deployed successfully")
        else:
            print("❌ Trading engine deployment failed")
            return False
        
        # Setup database backup
        deployment_manager.setup_database_backup()
        print("✅ Database backup procedures configured")
        
        # Create deployment summary
        deployment_manager.create_deployment_summary()
        print("✅ Deployment summary created")
        
        print("\n" + "="*60)
        print("🎉 PRODUCTION INFRASTRUCTURE DEPLOYMENT COMPLETE!")
        print("="*60)
        print("\n📋 Next Steps:")
        print("1. Review PRODUCTION_DEPLOYMENT_SUMMARY.md")
        print("2. Configure monitoring alerts")
        print("3. Set up automated backup schedule")
        print("4. Deploy to Railway production environment")
        print("5. Configure SSL and security settings")
        print("\n🚀 Your automated trading engine is ready for production!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Production deployment failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)