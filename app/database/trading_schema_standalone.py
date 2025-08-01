#!/usr/bin/env python3
"""
Standalone Trading Schema for Railway Deployment
Optimized database schema that doesn't depend on Settings or other complex imports
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TableType(Enum):
    """Database table types"""
    TRADES = "trades"
    PORTFOLIO = "portfolio"
    ORDERS = "orders"
    STRATEGIES = "strategies"
    MARKET_DATA = "market_data"
    USERS = "users"
    AUDIT_LOG = "audit_log"

@dataclass
class StandaloneSchemaConfig:
    """Standalone database schema configuration"""
    database_path: str
    enable_foreign_keys: bool = True
    enable_wal_mode: bool = True
    enable_synchronous: bool = True
    cache_size: int = -64000  # 64MB cache
    temp_store: str = "memory"

class StandaloneTradingSchema:
    """Standalone trading schema manager without external dependencies"""
    
    def __init__(self, config: Optional[StandaloneSchemaConfig] = None):
        self.config = config or StandaloneSchemaConfig(
            database_path=os.getenv("DATABASE_PATH", "trading_standalone.db")
        )
        self.connection = None
        self._schema_version = "1.0.0"
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimized settings"""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.config.database_path,
                check_same_thread=False
            )
            self._configure_connection()
        return self.connection
    
    def _configure_connection(self):
        """Configure connection with optimal settings"""
        conn = self.connection
        cursor = conn.cursor()
        
        # Enable foreign keys
        if self.config.enable_foreign_keys:
            cursor.execute("PRAGMA foreign_keys = ON")
        
        # Enable WAL mode for better concurrency
        if self.config.enable_wal_mode:
            cursor.execute("PRAGMA journal_mode = WAL")
        
        # Configure synchronous mode
        if self.config.enable_synchronous:
            cursor.execute("PRAGMA synchronous = NORMAL")
        
        # Set cache size
        cursor.execute(f"PRAGMA cache_size = {self.config.cache_size}")
        
        # Set temp store to memory
        cursor.execute(f"PRAGMA temp_store = {self.config.temp_store}")
        
        # Enable query planner optimization
        cursor.execute("PRAGMA optimize")
        
        conn.commit()
        logger.info("✅ Database connection configured with optimal settings")
    
    def create_optimized_schema(self) -> bool:
        """Create optimized database schema for trading operations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create schema version table
            self._create_schema_version_table(cursor)
            
            # Create core trading tables
            self._create_users_table(cursor)
            self._create_portfolio_table(cursor)
            self._create_orders_table(cursor)
            self._create_trades_table(cursor)
            self._create_strategies_table(cursor)
            self._create_market_data_table(cursor)
            self._create_audit_log_table(cursor)
            
            # Create optimized indexes
            self._create_optimized_indexes(cursor)
            
            # Create views for common queries
            self._create_optimized_views(cursor)
            
            # Create triggers for data integrity
            self._create_data_integrity_triggers(cursor)
            
            conn.commit()
            logger.info("✅ Optimized trading schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create optimized schema: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def _create_schema_version_table(self, cursor: sqlite3.Cursor):
        """Create schema version tracking table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY,
                version TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        
        # Insert current version
        cursor.execute("""
            INSERT OR REPLACE INTO schema_version (id, version, description)
            VALUES (1, ?, 'Standalone optimized trading schema')
        """, (self._schema_version,))
    
    def _create_users_table(self, cursor: sqlite3.Cursor):
        """Create optimized users table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                risk_profile TEXT DEFAULT 'moderate',
                max_position_size DECIMAL(15,2) DEFAULT 100000.00,
                max_daily_loss DECIMAL(15,2) DEFAULT 5000.00,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive')),
                CHECK (max_position_size > 0),
                CHECK (max_daily_loss > 0)
            )
        """)
    
    def _create_portfolio_table(self, cursor: sqlite3.Cursor):
        """Create optimized portfolio table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity DECIMAL(15,4) NOT NULL DEFAULT 0,
                average_price DECIMAL(15,4) NOT NULL DEFAULT 0,
                current_price DECIMAL(15,4) DEFAULT 0,
                market_value DECIMAL(15,2) GENERATED ALWAYS AS (quantity * current_price) STORED,
                unrealized_pnl DECIMAL(15,2) GENERATED ALWAYS AS ((current_price - average_price) * quantity) STORED,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign key constraints
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Unique constraint for user-symbol combination
                UNIQUE(user_id, symbol),
                
                -- Check constraints
                CHECK (quantity >= 0),
                CHECK (average_price >= 0),
                CHECK (current_price >= 0)
            )
        """)
    
    def _create_orders_table(self, cursor: sqlite3.Cursor):
        """Create optimized orders table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity DECIMAL(15,4) NOT NULL,
                price DECIMAL(15,4),
                stop_price DECIMAL(15,4),
                filled_quantity DECIMAL(15,4) DEFAULT 0,
                remaining_quantity DECIMAL(15,4) GENERATED ALWAYS AS (quantity - filled_quantity) STORED,
                average_fill_price DECIMAL(15,4) DEFAULT 0,
                status TEXT DEFAULT 'pending',
                strategy_id TEXT,
                time_in_force TEXT DEFAULT 'DAY',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filled_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                
                -- Foreign key constraints
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Check constraints
                CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
                CHECK (side IN ('buy', 'sell')),
                CHECK (quantity > 0),
                CHECK (filled_quantity >= 0),
                CHECK (filled_quantity <= quantity),
                CHECK (status IN ('pending', 'partial', 'filled', 'cancelled', 'rejected')),
                CHECK (time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK'))
            )
        """)
    
    def _create_trades_table(self, cursor: sqlite3.Cursor):
        """Create optimized trades table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity DECIMAL(15,4) NOT NULL,
                price DECIMAL(15,4) NOT NULL,
                value DECIMAL(15,2) GENERATED ALWAYS AS (quantity * price) STORED,
                commission DECIMAL(15,4) DEFAULT 0,
                net_value DECIMAL(15,2) GENERATED ALWAYS AS (value - commission) STORED,
                strategy_id TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settlement_date DATE,
                
                -- Foreign key constraints
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Check constraints
                CHECK (side IN ('buy', 'sell')),
                CHECK (quantity > 0),
                CHECK (price > 0),
                CHECK (commission >= 0)
            )
        """)
    
    def _create_strategies_table(self, cursor: sqlite3.Cursor):
        """Create optimized strategies table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                status TEXT DEFAULT 'inactive',
                parameters TEXT, -- JSON string
                symbols TEXT, -- JSON array of symbols
                max_position_size DECIMAL(15,2) DEFAULT 50000.00,
                max_daily_loss DECIMAL(15,2) DEFAULT 2000.00,
                total_pnl DECIMAL(15,2) DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                win_rate DECIMAL(5,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed TIMESTAMP,
                
                -- Foreign key constraints
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Check constraints
                CHECK (strategy_type IN ('momentum', 'mean_reversion', 'pairs_trading', 'arbitrage')),
                CHECK (status IN ('active', 'inactive', 'paused', 'stopped')),
                CHECK (max_position_size > 0),
                CHECK (max_daily_loss > 0),
                CHECK (win_rate >= 0 AND win_rate <= 100)
            )
        """)
    
    def _create_market_data_table(self, cursor: sqlite3.Cursor):
        """Create optimized market data table"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open_price DECIMAL(15,4),
                high_price DECIMAL(15,4),
                low_price DECIMAL(15,4),
                close_price DECIMAL(15,4) NOT NULL,
                volume INTEGER DEFAULT 0,
                vwap DECIMAL(15,4),
                data_source TEXT DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Unique constraint for symbol-timestamp combination
                UNIQUE(symbol, timestamp),
                
                -- Check constraints
                CHECK (open_price > 0 OR open_price IS NULL),
                CHECK (high_price > 0 OR high_price IS NULL),
                CHECK (low_price > 0 OR low_price IS NULL),
                CHECK (close_price > 0),
                CHECK (volume >= 0)
            )
        """)
    
    def _create_audit_log_table(self, cursor: sqlite3.Cursor):
        """Create audit log table for compliance"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT,
                old_values TEXT, -- JSON string
                new_values TEXT, -- JSON string
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                
                -- Check constraints
                CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
            )
        """)
    
    def _create_optimized_indexes(self, cursor: sqlite3.Cursor):
        """Create optimized indexes for trading operations"""
        
        # Portfolio indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_symbol ON portfolio(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_symbol ON portfolio(user_id, symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_last_updated ON portfolio(last_updated)")
        
        # Orders indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_strategy_id ON orders(strategy_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)")
        
        # Trades indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_order_id ON trades(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_executed_at ON trades(executed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_user_symbol_date ON trades(user_id, symbol, executed_at)")
        
        # Strategies indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_type ON strategies(strategy_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_last_executed ON strategies(last_executed)")
        
        # Market data indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)")
        
        # Audit log indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action)")
        
        logger.info("✅ Optimized indexes created")
    
    def _create_optimized_views(self, cursor: sqlite3.Cursor):
        """Create views for common trading queries"""
        
        # Portfolio summary view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS portfolio_summary AS
            SELECT 
                user_id,
                COUNT(*) as total_positions,
                SUM(market_value) as total_market_value,
                SUM(unrealized_pnl) as total_unrealized_pnl,
                AVG(CASE WHEN unrealized_pnl > 0 THEN 1.0 ELSE 0.0 END) * 100 as win_rate
            FROM portfolio 
            WHERE quantity > 0
            GROUP BY user_id
        """)
        
        # Daily trading summary view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS daily_trading_summary AS
            SELECT 
                user_id,
                symbol,
                DATE(executed_at) as trade_date,
                COUNT(*) as trades_count,
                SUM(CASE WHEN side = 'buy' THEN quantity ELSE 0 END) as total_bought,
                SUM(CASE WHEN side = 'sell' THEN quantity ELSE 0 END) as total_sold,
                SUM(CASE WHEN side = 'buy' THEN -net_value ELSE net_value END) as net_pnl
            FROM trades
            GROUP BY user_id, symbol, DATE(executed_at)
        """)
        
        # Active orders view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_orders AS
            SELECT 
                order_id,
                user_id,
                symbol,
                order_type,
                side,
                quantity,
                price,
                filled_quantity,
                remaining_quantity,
                status,
                created_at
            FROM orders
            WHERE status IN ('pending', 'partial')
            ORDER BY created_at DESC
        """)
        
        logger.info("✅ Optimized views created")
    
    def _create_data_integrity_triggers(self, cursor: sqlite3.Cursor):
        """Create triggers for data integrity and audit logging"""
        
        # Update timestamps trigger
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_portfolio_timestamp
            BEFORE UPDATE ON portfolio
            FOR EACH ROW
            BEGIN
                UPDATE portfolio SET last_updated = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_orders_timestamp
            BEFORE UPDATE ON orders
            FOR EACH ROW
            BEGIN
                UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_strategies_timestamp
            BEFORE UPDATE ON strategies
            FOR EACH ROW
            BEGIN
                UPDATE strategies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)
        
        logger.info("✅ Data integrity triggers created")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get comprehensive schema information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get index information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Get view information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            views = [row[0] for row in cursor.fetchall()]
            
            # Get trigger information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name")
            triggers = [row[0] for row in cursor.fetchall()]
            
            # Get schema version
            try:
                cursor.execute("SELECT version FROM schema_version WHERE id = 1")
                result = cursor.fetchone()
                version = result[0] if result else "unknown"
            except:
                version = "unknown"
            
            return {
                "schema_version": version,
                "tables": tables,
                "indexes": indexes,
                "views": views,
                "triggers": triggers,
                "total_objects": len(tables) + len(indexes) + len(views) + len(triggers),
                "database_path": self.config.database_path,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get schema info: {e}")
            return {"error": str(e)}
    
    def validate_schema(self) -> Dict[str, Any]:
        """Validate schema integrity and constraints"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            validation_results = {
                "valid": True,
                "checks": [],
                "errors": [],
                "warnings": []
            }
            
            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            if fk_violations:
                validation_results["valid"] = False
                validation_results["errors"].append(f"Foreign key violations: {len(fk_violations)}")
            else:
                validation_results["checks"].append("Foreign key constraints: OK")
            
            # Check table integrity
            for table in ["users", "portfolio", "orders", "trades", "strategies"]:
                try:
                    cursor.execute(f"PRAGMA integrity_check({table})")
                    result = cursor.fetchone()[0]
                    if result != "ok":
                        validation_results["valid"] = False
                        validation_results["errors"].append(f"Table {table} integrity: {result}")
                    else:
                        validation_results["checks"].append(f"Table {table} integrity: OK")
                except:
                    validation_results["warnings"].append(f"Could not check {table} integrity")
            
            # Check index usage
            cursor.execute("PRAGMA optimize")
            validation_results["checks"].append("Index optimization: Completed")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

# Global instance for easy access
standalone_trading_schema = None

def get_standalone_trading_schema(config: Optional[StandaloneSchemaConfig] = None) -> StandaloneTradingSchema:
    """Get or create standalone trading schema instance"""
    global standalone_trading_schema
    if standalone_trading_schema is None:
        standalone_trading_schema = StandaloneTradingSchema(config)
    return standalone_trading_schema

def initialize_standalone_trading_schema(database_path: Optional[str] = None) -> bool:
    """Initialize standalone trading schema"""
    try:
        config = StandaloneSchemaConfig(
            database_path=database_path or os.getenv("DATABASE_PATH", "trading_standalone.db")
        )
        
        schema_manager = get_standalone_trading_schema(config)
        success = schema_manager.create_optimized_schema()
        
        if success:
            logger.info("✅ Standalone trading schema initialized successfully")
            
            # Validate schema
            validation = schema_manager.validate_schema()
            if validation["valid"]:
                logger.info("✅ Schema validation passed")
            else:
                logger.warning(f"⚠️ Schema validation issues: {validation['errors']}")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize standalone trading schema: {e}")
        return False