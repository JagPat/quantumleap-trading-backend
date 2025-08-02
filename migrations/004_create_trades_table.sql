-- @name: Create Trades Table
-- @description: Create trades table to track executed trades
-- @type: table_creation
-- @author: Database Migration System
-- @dependencies: ["001_create_users_table", "003_create_orders_table"]
-- @reversible: true
-- @backup_required: true

-- UP
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE NOT NULL,
    order_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0.00,
    fees DECIMAL(10,2) DEFAULT 0.00,
    net_amount DECIMAL(15,2) NOT NULL,
    execution_venue TEXT,
    trade_date DATE NOT NULL,
    settlement_date DATE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (side IN ('buy', 'sell')),
    CHECK (quantity > 0),
    CHECK (price > 0),
    CHECK (value > 0),
    CHECK (commission >= 0),
    CHECK (fees >= 0),
    CHECK (ABS(value - (quantity * price)) < 0.01),
    CHECK (trade_date <= settlement_date OR settlement_date IS NULL)
);

CREATE INDEX idx_trades_trade_id ON trades(trade_id);
CREATE INDEX idx_trades_order_id ON trades(order_id);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_trade_date ON trades(trade_date);
CREATE INDEX idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX idx_trades_user_date ON trades(user_id, trade_date);

-- DOWN
DROP INDEX IF EXISTS idx_trades_user_date;
DROP INDEX IF EXISTS idx_trades_user_symbol;
DROP INDEX IF EXISTS idx_trades_trade_date;
DROP INDEX IF EXISTS idx_trades_timestamp;
DROP INDEX IF EXISTS idx_trades_symbol;
DROP INDEX IF EXISTS idx_trades_user_id;
DROP INDEX IF EXISTS idx_trades_order_id;
DROP INDEX IF EXISTS idx_trades_trade_id;
DROP TABLE IF EXISTS trades;