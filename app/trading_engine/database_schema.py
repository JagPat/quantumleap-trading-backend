"""
Database schema extensions for Automatic Trading Engine
"""
import sqlite3
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

def create_trading_engine_tables():
    """Create database tables for the automatic trading engine"""
    
    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    
    try:
        # Create orders table for order management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_orders (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,  -- MARKET, LIMIT, STOP_LOSS, STOP_LIMIT
                side TEXT NOT NULL,        -- BUY, SELL
                quantity INTEGER NOT NULL,
                price REAL,
                stop_price REAL,
                status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, SUBMITTED, FILLED, CANCELLED, REJECTED
                broker_order_id TEXT,
                strategy_id TEXT,
                signal_id TEXT,
                filled_quantity INTEGER DEFAULT 0,
                average_fill_price REAL,
                commission REAL DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_at TIMESTAMP,
                filled_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (strategy_id) REFERENCES ai_strategies (id),
                FOREIGN KEY (signal_id) REFERENCES ai_trading_signals (id)
            )
        ''')
        
        # Create positions table for position tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_positions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                average_price REAL NOT NULL,
                current_price REAL,
                unrealized_pnl REAL DEFAULT 0,
                realized_pnl REAL DEFAULT 0,
                strategy_id TEXT,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (strategy_id) REFERENCES ai_strategies (id),
                UNIQUE(user_id, symbol, strategy_id)
            )
        ''')
        
        # Create executions table for trade execution tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_executions (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                commission REAL DEFAULT 0,
                broker_execution_id TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES trading_orders (id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create strategy deployments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_deployments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, PAUSED, STOPPED, ERROR
                configuration TEXT NOT NULL,  -- JSON configuration
                risk_parameters TEXT NOT NULL,  -- JSON risk parameters
                performance_metrics TEXT,  -- JSON performance data
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paused_at TIMESTAMP,
                stopped_at TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (strategy_id) REFERENCES ai_strategies (id)
            )
        ''')
        
        # Create events table for event tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- SIGNAL, ORDER, EXECUTION, RISK, SYSTEM
                event_data TEXT NOT NULL,  -- JSON event data
                related_id TEXT,  -- Related order/position/strategy ID
                severity TEXT DEFAULT 'INFO',  -- INFO, WARNING, ERROR, CRITICAL
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create risk violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS risk_violations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,  -- POSITION_LIMIT, EXPOSURE_LIMIT, DRAWDOWN, etc.
                severity TEXT NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
                description TEXT NOT NULL,
                violation_data TEXT,  -- JSON violation details
                action_taken TEXT,  -- Action taken to resolve
                resolved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create audit trail table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_audit_trail (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,  -- ORDER_PLACED, POSITION_OPENED, STRATEGY_DEPLOYED, etc.
                entity_type TEXT NOT NULL,  -- ORDER, POSITION, STRATEGY, SIGNAL
                entity_id TEXT NOT NULL,
                old_data TEXT,  -- JSON of previous state
                new_data TEXT,  -- JSON of new state
                decision_rationale TEXT,  -- AI decision reasoning
                metadata TEXT,  -- Additional context
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Create performance tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                deployment_id TEXT NOT NULL,
                date DATE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                daily_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                sharpe_ratio REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (strategy_id) REFERENCES ai_strategies (id),
                FOREIGN KEY (deployment_id) REFERENCES strategy_deployments (id),
                UNIQUE(deployment_id, date)
            )
        ''')
        
        # Create market data cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data_cache (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER,
                bid REAL,
                ask REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol)
            )
        ''')
        
        # Create system configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_system_config (
                id TEXT PRIMARY KEY,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_status ON trading_orders(user_id, status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON trading_orders(symbol, status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_user_symbol ON trading_positions(user_id, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_executions_order_id ON trading_executions(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_user_type ON trading_events(user_id, event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_processed ON trading_events(processed, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_action ON trading_audit_trail(user_id, action)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_performance_strategy_date ON strategy_performance(strategy_id, date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data_cache(symbol)')
        
        # Insert default system configuration
        default_configs = [
            ('max_concurrent_orders', '10', 'Maximum concurrent orders per user'),
            ('order_timeout_seconds', '300', 'Order timeout in seconds'),
            ('risk_check_enabled', 'true', 'Enable risk checking'),
            ('emergency_stop_enabled', 'true', 'Enable emergency stop functionality'),
            ('max_position_size_percent', '5', 'Maximum position size as percentage of portfolio'),
            ('max_portfolio_exposure_percent', '80', 'Maximum portfolio exposure percentage'),
            ('max_sector_exposure_percent', '30', 'Maximum sector exposure percentage'),
            ('default_stop_loss_percent', '5', 'Default stop loss percentage'),
            ('market_data_refresh_seconds', '1', 'Market data refresh interval in seconds')
        ]
        
        for config_key, config_value, description in default_configs:
            cursor.execute('''
                INSERT OR IGNORE INTO trading_system_config (id, config_key, config_value, description)
                VALUES (?, ?, ?, ?)
            ''', (f"config_{config_key}", config_key, config_value, description))
        
        conn.commit()
        logger.info("Successfully created all trading engine database tables")
        
    except Exception as e:
        logger.error(f"Error creating trading engine tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_trading_system_config(config_key: str) -> str:
    """Get system configuration value"""
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT config_value FROM trading_system_config WHERE config_key = ?', (config_key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting system config {config_key}: {e}")
        return None

def set_trading_system_config(config_key: str, config_value: str, description: str = None) -> bool:
    """Set system configuration value"""
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO trading_system_config (id, config_key, config_value, description, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (f"config_{config_key}", config_key, config_value, description))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting system config {config_key}: {e}")
        return False

def check_trading_engine_health() -> Dict[str, Any]:
    """Check trading engine database health"""
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Check if all required tables exist
        required_tables = [
            'trading_orders', 'trading_positions', 'trading_executions',
            'strategy_deployments', 'trading_events', 'risk_violations',
            'trading_audit_trail', 'strategy_performance', 'market_data_cache',
            'trading_system_config'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        # Get table counts
        table_counts = {}
        for table in required_tables:
            if table in existing_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "status": "healthy" if not missing_tables else "unhealthy",
            "required_tables": required_tables,
            "existing_tables": existing_tables,
            "missing_tables": missing_tables,
            "table_counts": table_counts
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }