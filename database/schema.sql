-- QuantumLeap Trading Platform Database Schema
-- PostgreSQL Database Schema for Production Use

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table for authentication and user management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Broker configurations for OAuth integrations
CREATE TABLE broker_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL, -- Allow string user IDs for OAuth-only users
    broker_name VARCHAR(50) NOT NULL, -- 'zerodha', 'upstox', etc.
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    is_connected BOOLEAN DEFAULT false,
    connection_status JSONB DEFAULT '{"state": "disconnected", "message": "Not connected", "lastChecked": null}',
    oauth_state VARCHAR(64), -- For CSRF protection during OAuth flow
    broker_user_id VARCHAR(100), -- Broker's internal user ID
    broker_user_name VARCHAR(100),
    broker_user_type VARCHAR(50),
    last_sync_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, broker_name)
);

-- OAuth tokens storage with encryption
CREATE TABLE oauth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_id UUID NOT NULL REFERENCES broker_configs(id) ON DELETE CASCADE,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_type VARCHAR(20) DEFAULT 'Bearer',
    expires_at TIMESTAMP NOT NULL,
    scope TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(config_id)
);

-- OAuth audit log for security tracking
CREATE TABLE oauth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_id UUID REFERENCES broker_configs(id) ON DELETE SET NULL,
    user_id VARCHAR(255), -- Allow string user IDs for OAuth-only users
    action VARCHAR(50) NOT NULL, -- 'setup', 'callback', 'refresh', 'revoke', 'error'
    status VARCHAR(20) NOT NULL, -- 'success', 'failure', 'pending'
    ip_address INET,
    user_agent TEXT,
    request_data JSONB,
    response_data JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolios for trading management
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_config_id UUID REFERENCES broker_configs(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    total_value DECIMAL(15,2) DEFAULT 0,
    invested_amount DECIMAL(15,2) DEFAULT 0,
    current_value DECIMAL(15,2) DEFAULT 0,
    day_change DECIMAL(15,2) DEFAULT 0,
    day_change_percent DECIMAL(5,2) DEFAULT 0,
    total_return DECIMAL(15,2) DEFAULT 0,
    total_return_percent DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Holdings within portfolios
CREATE TABLE holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL, -- 'NSE', 'BSE', etc.
    instrument_type VARCHAR(20) DEFAULT 'EQ', -- 'EQ', 'FUT', 'OPT', etc.
    quantity INTEGER NOT NULL DEFAULT 0,
    average_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    invested_amount DECIMAL(15,2) NOT NULL,
    current_value DECIMAL(15,2),
    day_change DECIMAL(15,2) DEFAULT 0,
    day_change_percent DECIMAL(5,2) DEFAULT 0,
    total_return DECIMAL(15,2) DEFAULT 0,
    total_return_percent DECIMAL(5,2) DEFAULT 0,
    last_price_update TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, symbol, exchange)
);

-- Trading orders and execution history
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    broker_config_id UUID REFERENCES broker_configs(id) ON DELETE SET NULL,
    order_id VARCHAR(100), -- Broker's order ID
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    instrument_type VARCHAR(20) DEFAULT 'EQ',
    transaction_type VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    order_type VARCHAR(20) NOT NULL, -- 'MARKET', 'LIMIT', 'SL', 'SL-M'
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    trigger_price DECIMAL(10,2),
    executed_quantity INTEGER DEFAULT 0,
    executed_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED'
    status_message TEXT,
    order_timestamp TIMESTAMP,
    execution_timestamp TIMESTAMP,
    brokerage DECIMAL(10,2) DEFAULT 0,
    taxes DECIMAL(10,2) DEFAULT 0,
    total_charges DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market data cache for performance
CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    last_price DECIMAL(10,2),
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2),
    volume BIGINT,
    change_amount DECIMAL(10,2),
    change_percent DECIMAL(5,2),
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, exchange)
);

-- User sessions for authentication
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration and settings
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance optimization
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);

CREATE INDEX idx_broker_configs_user_id ON broker_configs(user_id);
CREATE INDEX idx_broker_configs_broker_name ON broker_configs(broker_name);
CREATE INDEX idx_broker_configs_connected ON broker_configs(is_connected);

CREATE INDEX idx_oauth_tokens_config_id ON oauth_tokens(config_id);
CREATE INDEX idx_oauth_tokens_expires_at ON oauth_tokens(expires_at);

CREATE INDEX idx_oauth_audit_user_id ON oauth_audit_log(user_id);
CREATE INDEX idx_oauth_audit_action ON oauth_audit_log(action);
CREATE INDEX idx_oauth_audit_created_at ON oauth_audit_log(created_at);

CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);
CREATE INDEX idx_portfolios_active ON portfolios(is_active);

CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);
CREATE INDEX idx_holdings_symbol ON holdings(symbol);

CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_portfolio_id ON trades(portfolio_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created_at ON trades(created_at);

CREATE INDEX idx_market_data_symbol_exchange ON market_data(symbol, exchange);
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_broker_configs_updated_at BEFORE UPDATE ON broker_configs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_holdings_updated_at BEFORE UPDATE ON holdings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_sessions_updated_at BEFORE UPDATE ON user_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
('app_version', '"2.0.0"', 'Application version'),
('maintenance_mode', 'false', 'Maintenance mode flag'),
('max_portfolios_per_user', '10', 'Maximum portfolios per user'),
('supported_brokers', '["zerodha", "upstox", "angel"]', 'List of supported brokers'),
('market_data_refresh_interval', '30', 'Market data refresh interval in seconds'),
('oauth_token_refresh_threshold', '3600', 'OAuth token refresh threshold in seconds')
ON CONFLICT (key) DO NOTHING;