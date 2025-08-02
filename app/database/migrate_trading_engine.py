"""
Trading Engine Migration Script
Migrates existing trading engine to use optimized database layer
"""
import os
import sys
import logging
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.database.trading_engine_integration import trading_db_integration
from app.trading_engine.optimized_order_db import optimized_order_db

logger = logging.getLogger(__name__)

class TradingEngineMigration:
    """
    Handles migration of trading engine to optimized database
    """
    
    def __init__(self):
        self.migration_log = []
        self.backup_directory = Path("migration_backups")
        self.backup_directory.mkdir(exist_ok=True)
        
        logger.info("TradingEngineMigration initialized")
    
    def log_migration_step(self, step: str, status: str, details: str = ""):
        """Log migration step with timestamp"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'status': status,
            'details': details
        }
        self.migration_log.append(entry)
        logger.info(f"Migration: {step} - {status} - {details}")
    
    async def create_migration_backup(self) -> bool:
        """Create backup before migration"""
        try:
            self.log_migration_step("backup_creation", "started", "Creating pre-migration backup")
            
            # Create backup of existing database if it exists
            existing_db_paths = [
                "trading.db",
                "app/database/trading.db",
                "trading_engine.db"
            ]
            
            backup_created = False
            for db_path in existing_db_paths:
                if os.path.exists(db_path):
                    backup_name = f"pre_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    backup_path = self.backup_directory / backup_name
                    shutil.copy2(db_path, backup_path)
                    self.log_migration_step("backup_creation", "success", f"Backed up {db_path} to {backup_path}")
                    backup_created = True
            
            if not backup_created:
                self.log_migration_step("backup_creation", "skipped", "No existing database found to backup")
            
            return True
            
        except Exception as e:
            self.log_migration_step("backup_creation", "failed", f"Error: {e}")
            return False
    
    async def initialize_optimized_database(self) -> bool:
        """Initialize the optimized database system"""
        try:
            self.log_migration_step("database_initialization", "started", "Initializing optimized database")
            
            # Initialize the trading database integration
            await trading_db_integration.initialize()
            
            # Initialize the optimized order database
            await optimized_order_db.initialize()
            
            self.log_migration_step("database_initialization", "success", "Optimized database initialized")
            return True
            
        except Exception as e:
            self.log_migration_step("database_initialization", "failed", f"Error: {e}")
            return False
    
    async def create_optimized_schema(self) -> bool:
        """Create optimized database schema"""
        try:
            self.log_migration_step("schema_creation", "started", "Creating optimized database schema")
            
            # Create tables with optimized schema
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
                """
                CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)
                """,
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
                """
                CREATE INDEX IF NOT EXISTS idx_positions_user_id ON positions(user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON positions(user_id, symbol)
                """,
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
                """
                CREATE INDEX IF NOT EXISTS idx_executions_order_id ON executions(order_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_executions_user_id ON executions(user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at)
                """,
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
                """
                CREATE INDEX IF NOT EXISTS idx_strategy_deployments_user_id ON strategy_deployments(user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_strategy_deployments_status ON strategy_deployments(status)
                """,
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
                """
                CREATE INDEX IF NOT EXISTS idx_trading_signals_user_id ON trading_signals(user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON trading_signals(is_active)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_trading_signals_created_at ON trading_signals(created_at)
                """
            ]
            
            # Execute schema creation queries
            for query in schema_queries:
                await trading_db_integration.db_manager.execute_query(query)
            
            self.log_migration_step("schema_creation", "success", f"Created {len(schema_queries)} schema objects")
            return True
            
        except Exception as e:
            self.log_migration_step("schema_creation", "failed", f"Error: {e}")
            return False
    
    async def migrate_existing_data(self) -> bool:
        """Migrate existing data to optimized database"""
        try:
            self.log_migration_step("data_migration", "started", "Migrating existing data")
            
            # Check for existing data sources
            existing_data_found = False
            
            # Look for existing database files
            existing_db_paths = [
                "trading.db",
                "app/database/trading.db",
                "trading_engine.db"
            ]
            
            for db_path in existing_db_paths:
                if os.path.exists(db_path):
                    existing_data_found = True
                    await self._migrate_from_database(db_path)
            
            if not existing_data_found:
                self.log_migration_step("data_migration", "skipped", "No existing data found to migrate")
            else:
                self.log_migration_step("data_migration", "success", "Data migration completed")
            
            return True
            
        except Exception as e:
            self.log_migration_step("data_migration", "failed", f"Error: {e}")
            return False
    
    async def _migrate_from_database(self, source_db_path: str):
        """Migrate data from existing database"""
        try:
            import sqlite3
            
            # Connect to source database
            source_conn = sqlite3.connect(source_db_path)
            source_conn.row_factory = sqlite3.Row
            source_cursor = source_conn.cursor()
            
            # Get table names
            source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in source_cursor.fetchall()]
            
            migrated_records = 0
            
            for table in tables:
                if table in ['orders', 'positions', 'executions', 'strategy_deployments', 'trading_signals']:
                    # Get all records from source table
                    source_cursor.execute(f"SELECT * FROM {table}")
                    records = source_cursor.fetchall()
                    
                    if records:
                        # Prepare insert query for target database
                        columns = [description[0] for description in source_cursor.description]
                        placeholders = ', '.join(['?' for _ in columns])
                        insert_query = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                        
                        # Insert records into optimized database
                        for record in records:
                            await trading_db_integration.db_manager.execute_query(
                                insert_query, tuple(record)
                            )
                            migrated_records += 1
                        
                        self.log_migration_step("data_migration", "progress", 
                                              f"Migrated {len(records)} records from {table}")
            
            source_conn.close()
            self.log_migration_step("data_migration", "success", 
                                  f"Migrated {migrated_records} total records from {source_db_path}")
            
        except Exception as e:
            self.log_migration_step("data_migration", "error", f"Error migrating from {source_db_path}: {e}")
    
    async def update_trading_engine_components(self) -> bool:
        """Update trading engine components to use optimized database"""
        try:
            self.log_migration_step("component_update", "started", "Updating trading engine components")
            
            # Create updated import statements for trading engine files
            updates = [
                {
                    'file': 'app/trading_engine/position_manager.py',
                    'old_import': 'from .order_db import order_db',
                    'new_import': 'from .optimized_order_db import optimized_order_db as order_db'
                },
                {
                    'file': 'app/trading_engine/order_service.py',
                    'old_import': 'from .order_db import order_db',
                    'new_import': 'from .optimized_order_db import optimized_order_db as order_db'
                },
                {
                    'file': 'app/trading_engine/order_executor.py',
                    'old_import': 'from .order_db import order_db',
                    'new_import': 'from .optimized_order_db import optimized_order_db as order_db'
                }
            ]
            
            updated_files = 0
            for update in updates:
                if os.path.exists(update['file']):
                    try:
                        # Read file content
                        with open(update['file'], 'r') as f:
                            content = f.read()
                        
                        # Replace import statement
                        if update['old_import'] in content:
                            content = content.replace(update['old_import'], update['new_import'])
                            
                            # Write updated content
                            with open(update['file'], 'w') as f:
                                f.write(content)
                            
                            updated_files += 1
                            self.log_migration_step("component_update", "progress", 
                                                  f"Updated imports in {update['file']}")
                    
                    except Exception as e:
                        self.log_migration_step("component_update", "warning", 
                                              f"Could not update {update['file']}: {e}")
            
            self.log_migration_step("component_update", "success", f"Updated {updated_files} component files")
            return True
            
        except Exception as e:
            self.log_migration_step("component_update", "failed", f"Error: {e}")
            return False
    
    async def verify_migration(self) -> bool:
        """Verify migration was successful"""
        try:
            self.log_migration_step("verification", "started", "Verifying migration")
            
            # Test database connectivity
            health_status = await optimized_order_db.get_health_status()
            if health_status.get('status') != 'healthy':
                self.log_migration_step("verification", "failed", "Database health check failed")
                return False
            
            # Test basic operations
            from app.trading_engine.models import Order, OrderType, OrderSide
            
            # Create test order
            test_order = Order(
                id="test_migration_order",
                user_id="test_user",
                symbol="TEST",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                quantity=100
            )
            
            # Test create operation
            create_success = await optimized_order_db.create_order(test_order)
            if not create_success:
                self.log_migration_step("verification", "failed", "Test order creation failed")
                return False
            
            # Test read operation
            retrieved_order = await optimized_order_db.get_order(test_order.id)
            if not retrieved_order:
                self.log_migration_step("verification", "failed", "Test order retrieval failed")
                return False
            
            # Clean up test data
            await trading_db_integration.db_manager.execute_query(
                "DELETE FROM orders WHERE id = ?", (test_order.id,)
            )
            
            # Get performance metrics
            metrics = await optimized_order_db.get_performance_metrics()
            if not metrics:
                self.log_migration_step("verification", "warning", "Performance metrics not available")
            
            self.log_migration_step("verification", "success", "Migration verification completed")
            return True
            
        except Exception as e:
            self.log_migration_step("verification", "failed", f"Error: {e}")
            return False
    
    async def generate_migration_report(self) -> str:
        """Generate migration report"""
        try:
            report_lines = [
                "=" * 80,
                "TRADING ENGINE DATABASE MIGRATION REPORT",
                "=" * 80,
                f"Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Steps: {len(self.migration_log)}",
                "",
                "MIGRATION STEPS:",
                "-" * 40
            ]
            
            for entry in self.migration_log:
                report_lines.append(
                    f"[{entry['timestamp']}] {entry['step']}: {entry['status']}"
                )
                if entry['details']:
                    report_lines.append(f"  Details: {entry['details']}")
                report_lines.append("")
            
            # Add summary
            successful_steps = len([e for e in self.migration_log if e['status'] in ['success', 'progress']])
            failed_steps = len([e for e in self.migration_log if e['status'] == 'failed'])
            
            report_lines.extend([
                "MIGRATION SUMMARY:",
                "-" * 40,
                f"Successful Steps: {successful_steps}",
                f"Failed Steps: {failed_steps}",
                f"Overall Status: {'SUCCESS' if failed_steps == 0 else 'PARTIAL SUCCESS' if successful_steps > 0 else 'FAILED'}",
                "",
                "=" * 80
            ])
            
            report = "\n".join(report_lines)
            
            # Save report to file
            report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            self.log_migration_step("report_generation", "success", f"Report saved to {report_file}")
            
            return report
            
        except Exception as e:
            self.log_migration_step("report_generation", "failed", f"Error: {e}")
            return f"Error generating report: {e}"
    
    async def run_full_migration(self) -> bool:
        """Run complete migration process"""
        try:
            logger.info("Starting trading engine database migration")
            
            # Step 1: Create backup
            if not await self.create_migration_backup():
                logger.error("Migration backup failed - aborting")
                return False
            
            # Step 2: Initialize optimized database
            if not await self.initialize_optimized_database():
                logger.error("Database initialization failed - aborting")
                return False
            
            # Step 3: Create optimized schema
            if not await self.create_optimized_schema():
                logger.error("Schema creation failed - aborting")
                return False
            
            # Step 4: Migrate existing data
            if not await self.migrate_existing_data():
                logger.error("Data migration failed - continuing with verification")
            
            # Step 5: Update trading engine components
            if not await self.update_trading_engine_components():
                logger.error("Component update failed - continuing with verification")
            
            # Step 6: Verify migration
            verification_success = await self.verify_migration()
            
            # Step 7: Generate report
            report = await self.generate_migration_report()
            print("\n" + report)
            
            if verification_success:
                logger.info("Trading engine database migration completed successfully")
                return True
            else:
                logger.error("Migration verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            return False

async def main():
    """Main migration function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    migration = TradingEngineMigration()
    success = await migration.run_full_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The trading engine is now using the optimized database layer.")
        print("Please restart your application to use the new database system.")
    else:
        print("\n❌ Migration completed with errors.")
        print("Please check the migration report for details.")
        print("You may need to manually resolve some issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())