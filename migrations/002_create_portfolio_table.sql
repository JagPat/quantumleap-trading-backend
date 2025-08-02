-- @name: Create Portfolio Table
-- @description: Create portfolio table to track user holdings
-- @type: table_creation
-- @author: Database Migration System
-- @dependencies: ["001_create_users_table"]
-- @reversible: true
-- @backup_required: true

-- UP
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity INTEGER DEFAULT 0,
    average_price DECIMAL(10,2) DEFAULT 0.00,
    current_price DECIMAL(10,2) DEFAULT 0.00,
    market_value DECIMAL(15,2) DEFAULT 0.00,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0.00,
    realized_pnl DECIMAL(15,2) DEFAULT 0.00,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, symbol),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (quantity >= 0),
    CHECK (average_price >= 0),
    CHECK (current_price >= 0)
);

CREATE INDEX idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX idx_portfolio_symbol ON portfolio(symbol);
CREATE INDEX idx_portfolio_user_symbol ON portfolio(user_id, symbol);
CREATE INDEX idx_portfolio_last_updated ON portfolio(last_updated);

-- DOWN
DROP INDEX IF EXISTS idx_portfolio_last_updated;
DROP INDEX IF EXISTS idx_portfolio_user_symbol;
DROP INDEX IF EXISTS idx_portfolio_symbol;
DROP INDEX IF EXISTS idx_portfolio_user_id;
DROP TABLE IF EXISTS portfolio;