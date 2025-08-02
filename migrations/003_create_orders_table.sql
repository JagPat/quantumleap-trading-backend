-- @name: Create Orders Table
-- @description: Create orders table to track trading orders
-- @type: table_creation
-- @author: Database Migration System
-- @dependencies: ["001_create_users_table"]
-- @reversible: true
-- @backup_required: true

-- UP
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    filled_quantity INTEGER DEFAULT 0,
    remaining_quantity INTEGER DEFAULT 0,
    price DECIMAL(10,2),
    stop_price DECIMAL(10,2),
    limit_price DECIMAL(10,2),
    status TEXT DEFAULT 'pending',
    time_in_force TEXT DEFAULT 'DAY',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (side IN ('buy', 'sell')),
    CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    CHECK (quantity > 0),
    CHECK (filled_quantity >= 0),
    CHECK (filled_quantity <= quantity),
    CHECK (remaining_quantity >= 0),
    CHECK (remaining_quantity = quantity - filled_quantity),
    CHECK (price > 0 OR order_type = 'market'),
    CHECK (status IN ('pending', 'partial', 'filled', 'cancelled', 'rejected')),
    CHECK (time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK'))
);

CREATE INDEX idx_orders_order_id ON orders(order_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- DOWN
DROP INDEX IF EXISTS idx_orders_user_status;
DROP INDEX IF EXISTS idx_orders_created_at;
DROP INDEX IF EXISTS idx_orders_status;
DROP INDEX IF EXISTS idx_orders_symbol;
DROP INDEX IF EXISTS idx_orders_user_id;
DROP INDEX IF EXISTS idx_orders_order_id;
DROP TABLE IF EXISTS orders;