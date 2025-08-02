-- @name: Create Users Table
-- @description: Create the main users table with authentication and profile information
-- @type: table_creation
-- @author: Database Migration System
-- @dependencies: []
-- @reversible: true
-- @backup_required: true

-- UP
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    balance DECIMAL(15,2) DEFAULT 0.00,
    initial_balance DECIMAL(15,2) DEFAULT 0.00,
    credit_limit DECIMAL(15,2) DEFAULT 0.00,
    max_position_size DECIMAL(15,2) DEFAULT 10000.00,
    max_daily_loss DECIMAL(15,2) DEFAULT 1000.00,
    is_active BOOLEAN DEFAULT 1,
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (balance >= (credit_limit * -1)),
    CHECK (max_position_size > 0),
    CHECK (max_daily_loss > 0),
    CHECK (email LIKE '%@%.%')
);

CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- DOWN
DROP INDEX IF EXISTS idx_users_created_at;
DROP INDEX IF EXISTS idx_users_is_active;
DROP INDEX IF EXISTS idx_users_email;
DROP INDEX IF EXISTS idx_users_user_id;
DROP TABLE IF EXISTS users;