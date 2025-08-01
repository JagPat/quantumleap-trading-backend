"""
Trading Schema Optimizer for Railway Deployment

Optimized database schema design specifically for high-frequency trading operations
with Railway PostgreSQL and SQLite support.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class TableSchema:
    """Optimized table schema definition"""
    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    partitioning: Optional[Dict[str, Any]] = None
    optimization_notes: List[str] = None

class TradingSchemaOptimizer:
    """Optimized schema manager for trading operations"""
    
    def __init__(self, database_manager=None):
        self.database_manager = database_manager
        self.is_postgresql = self._detect_postgresql()
        
        # Trading-specific schema definitions
        self.trading_schemas = self._initialize_trading_schemas()
        
        logger.info("📊 Trading schema optimizer initialized for Railway")
    
    def _detect_postgresql(self) -> bool:
        """Detect database type"""
        if self.database_manager:
            return getattr(self.database_manager, 'is_postgresql', False)
        
        database_url = os.getenv('DATABASE_URL', '')
        return database_url.startswith(('postgresql://', 'postgres://'))
    
    def _initialize_trading_schemas(self) -> Dict[str, TableSchema]:
        """Initialize optimized trading table schemas"""
        schemas = {}
        
        # Optimized trades table
        schemas['trades'] = TableSchema(
            table_name='trades',
            columns=[
                {'name': 'id', 'type': 'BIGSERIAL' if self.is_postgresql else 'INTEGER', 
                 'constraints': ['PRIMARY KEY'], 'comment': 'Unique trade identifier'},
                {'name': 'user_id', 'type': 'VARCHAR(50)', 'constraints': ['NOT NULL'], 
                 'comment': 'User identifier'},
                {'name': 'symbol', 'type': 'VARCHAR(20)', 'constraints': ['NOT NULL'], 
                 'comment': 'Trading symbol'},
                {'name': 'side', 'type': 'VARCHAR(4)', 'constraints': ['NOT NULL'], 
                 'comment': 'BUY or SELL'},
                {'name': 'quantity', 'type': 'DECIMAL(18,8)', 'constraints': ['NOT NULL'], 
                 'comment': 'Trade quantity'},
                {'name': 'price', 'type': 'DECIMAL(18,8)', 'constraints': ['NOT NULL'], 
                 'comment': 'Trade price'},
                {'name': 'executed_at', 'type': 'TIMESTAMP', 
                 'constraints': ['NOT NULL', 'DEFAULT CURRENT_TIMESTAMP'], 
                 'comment': 'Execution timestamp'},
                {'name': 'strategy_id', 'type': 'VARCHAR(50)', 'constraints': [], 
                 'comment': 'Strategy identifier'},
                {'name': 'order_id', 'type': 'VARCHAR(50)', 'constraints': [], 
                 'comment': 'Original order ID'},
                {'name': 'commission', 'type': 'DECIMAL(10,4)', 'constraints': ['DEFAULT 0'], 
                 'comment': 'Trade commission'},
                {'name': 'status', 'type': 'VARCHAR(20)', 'constraints': ['DEFAULT \'EXECUTED\''], 
                 'comment': 'Trade status'},
                {'name': 'metadata', 'type': 'JSONB' if self.is_postgresql else 'TEXT', 
                 'constraints': [], 'comment': 'Additional trade metadata'}
            ],
            indexes=[
                {'name': 'idx_trades_user_symbol_time', 'columns': ['user_id', 'symbol', 'executed_at'], 
                 'type': 'btree', 'comment': 'Primary query pattern'},
                {'name': 'idx_trades_symbol_time', 'columns': ['symbol', 'executed_at'], 
                 'type': 'btree', 'comment': 'Symbol-based queries'},
                {'name': 'idx_trades_strategy', 'columns': ['strategy_id'], 
                 'type': 'btree', 'comment': 'Strategy performance analysis'},
                {'name': 'idx_trades_order', 'columns': ['order_id'], 
                 'type': 'btree', 'comment': 'Order tracking'}
            ],
            constraints=[
                {'type': 'CHECK', 'definition': 'side IN (\'BUY\', \'SELL\')', 
                 'comment': 'Valid trade sides'},
                {'type': 'CHECK', 'definition': 'quantity > 0', 
                 'comment': 'Positive quantity'},
                {'type': 'CHECK', 'definition': 'price > 0', 
                 'comment': 'Positive price'}
            ],
            optimization_notes=[
                'Partitioned by executed_at for time-series queries',
                'JSONB metadata for flexible data storage (PostgreSQL)',
                'Optimized for high-frequency inserts and time-range queries'
            ]
        )
        
        # Optimized portfolio table
        schemas['portfolio'] = TableSchema(
            table_name='portfolio',
            columns=[
                {'name': 'id', 'type': 'BIGSERIAL' if self.is_postgresql else 'INTEGER', 
                 'constraints': ['PRIMARY KEY']},
                {'name': 'user_id', 'type': 'VARCHAR(50)', 'constraints': ['NOT NULL']},
                {'name': 'symbol', 'type': 'VARCHAR(20)', 'constraints': ['NOT NULL']},
                {'name': 'quantity', 'type': 'DECIMAL(18,8)', 'constraints': ['NOT NULL', 'DEFAULT 0']},
                {'name': 'average_cost', 'type': 'DECIMAL(18,8)', 'constraints': ['NOT NULL', 'DEFAULT 0']},
                {'name': 'market_value', 'type': 'DECIMAL(18,2)', 'constraints': ['DEFAULT 0']},
                {'name': 'unrealized_pnl', 'type': 'DECIMAL(18,2)', 'constraints': ['DEFAULT 0']},
                {'name': 'realized_pnl', 'type': 'DECIMAL(18,2)', 'constraints': ['DEFAULT 0']},
                {'name': 'last_updated', 'type': 'TIMESTAMP', 
                 'constraints': ['NOT NULL', 'DEFAULT CURRENT_TIMESTAMP']},
                {'name': 'created_at', 'type': 'TIMESTAMP', 
                 'constraints': ['NOT NULL', 'DEFAULT CURRENT_TIMESTAMP']}
            ],
            indexes=[
                {'name': 'idx_portfolio_user_symbol', 'columns': ['user_id', 'symbol'], 
                 'type': 'unique', 'comment': 'Unique user-symbol combination'},
                {'name': 'idx_portfolio_user_updated', 'columns': ['user_id', 'last_updated'], 
                 'type': 'btree', 'comment': 'User portfolio queries'},
                {'name': 'idx_portfolio_symbol', 'columns': ['symbol'], 
                 'type': 'btree', 'comment': 'Symbol-based aggregations'}
            ],
            constraints=[
                {'type': 'UNIQUE', 'definition': '(user_id, symbol)', 
                 'comment': 'One position per user per symbol'}
            ],
            optimization_notes=[
                'Unique constraint prevents duplicate positions',
                'Denormalized PnL calculations for performance',
                'Optimized for real-time portfolio updates'
            ]
        )
        
        # Optimized orders table
        schemas['orders'] = TableSchema(
            table_name='orders',
            columns=[
                {'name': 'id', 'type': 'VARCHAR(50)', 'constraints': ['PRIMARY KEY']},
                {'name': 'user_id', 'type': 'VARCHAR(50)', 'constraints': ['NOT NULL']},
                {'name': 'symbol', 'type': 'VARCHAR(20)', 'constraints': ['NOT NULL']},
                {'name': 'side', 'type': 'VARCHAR(4)', 'constraints': ['NOT NULL']},
                {'name': 'order_type', 'type': 'VARCHAR(20)', 'constraints': ['NOT NULL']},
                {'name': 'quantity', 'type': 'DECIMAL(18,8)', 'constraints': ['NOT NULL']},
                {'name': 'price', 'type': 'DECIMAL(18,8)', 'constraints': []},
                {'name': 'stop_price', 'type': 'DECIMAL(18,8)', 'constraints': []},
                {'name': 'filled_quantity', 'type': 'DECIMAL(18,8)', 'constraints': ['DEFAULT 0']},
                {'name': 'average_fill_price', 'type': 'DECIMAL(18,8)', 'constraints': ['DEFAULT 0']},
                {'name': 'status', 'type': 'VARCHAR(20)', 'constraints': ['NOT NULL', 'DEFAULT \'PENDING\'']},
                {'name': 'strategy_id', 'type': 'VARCHAR(50)', 'constraints': []},
                {'name': 'created_at', 'type': 'TIMESTAMP', 
                 'constraints': ['NOT NULL', 'DEFAULT CURRENT_TIMESTAMP']},
                {'name': 'updated_at', 'type': 'TIMESTAMP', 
                 'constraints': ['NOT NULL', 'DEFAULT CURRENT_TIMESTAMP']},
                {'name': 'expires_at', 'type': 'TIMESTAMP', 'constraints': []},
                {'name': 'broker_order_id', 'type': 'VARCHAR(100)', 'constraints': []},
                {'name': 'error_message', 'type': 'TEXT', 'constraints': []}
            ],
            indexes=[
                {'name': 'idx_orders_user_status_time', 'columns': ['user_id', 'status', 'created_at'], 
                 'type': 'btree', 'comment': 'User order queries'},
                {'name': 'idx_orders_symbol_status', 'columns': ['symbol', 'status'], 
                 'type': 'btree', 'comment': 'Symbol order tracking'},
                {'name': 'idx_orders_strategy', 'columns': ['strategy_id'], 
                 'type': 'btree', 'comment': 'Strategy order tracking'},
                {'name': 'idx_orders_broker_id', 'columns': ['broker_order_id'], 
                 'type': 'btree', 'comment': 'Broker integration'},
                {'name': 'idx_orders_expires', 'columns': ['expires_at'], 
                 'type': 'btree', 'comment': 'Order expiration processing'}
            ],
            constraints=[
                {'type': 'CHECK', 'definition': 'side IN (\'BUY\', \'SELL\')', 
                 'comment': 'Valid order sides'},
                {'type': 'CHECK', 'definition': 'quantity > 0', 
                 'comment': 'Positive quantity'},
                {'type': 'CHECK', 'definition': 'filled_quantity >= 0', 
                 'comment': 'Non-negative filled quantity'},
                {'type': 'CHECK', 'definition': 'filled_quantity <= quantity', 
                 'comment': 'Filled cannot exceed total'}
            ],
            optimization_notes=[
                'String ID for broker compatibility',
                'Comprehensive order lifecycle tracking',
                'Optimized for order management queries'
            ]
        )
        
        return schemas