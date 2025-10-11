-- Migration 012: Add Rebalancing Tables
-- Creates tables for portfolio rebalancing functionality

-- Rebalancing events table
CREATE TABLE IF NOT EXISTS rebalancing_events (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  config_id INTEGER,
  trades_count INTEGER NOT NULL DEFAULT 0,
  total_value DECIMAL(15, 2),
  max_drift DECIMAL(5, 2),
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Rebalancing trades table
CREATE TABLE IF NOT EXISTS rebalancing_trades (
  id SERIAL PRIMARY KEY,
  rebalancing_id INTEGER NOT NULL,
  symbol VARCHAR(50) NOT NULL,
  action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
  quantity INTEGER NOT NULL,
  price DECIMAL(15, 2),
  estimated_value DECIMAL(15, 2),
  actual_value DECIMAL(15, 2),
  status VARCHAR(20) DEFAULT 'pending',
  executed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (rebalancing_id) REFERENCES rebalancing_events(id) ON DELETE CASCADE
);

-- User preferences table (if not exists)
CREATE TABLE IF NOT EXISTS user_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE,
  rebalancing_enabled BOOLEAN DEFAULT false,
  drift_threshold DECIMAL(5, 2) DEFAULT 10.0,
  tax_optimization_enabled BOOLEAN DEFAULT true,
  auto_rebalance_frequency VARCHAR(20) DEFAULT 'monthly',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_rebalancing_events_user_id ON rebalancing_events(user_id);
CREATE INDEX IF NOT EXISTS idx_rebalancing_events_created_at ON rebalancing_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rebalancing_trades_rebalancing_id ON rebalancing_trades(rebalancing_id);
CREATE INDEX IF NOT EXISTS idx_rebalancing_trades_symbol ON rebalancing_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);

-- Add comments
COMMENT ON TABLE rebalancing_events IS 'Portfolio rebalancing events and execution history';
COMMENT ON TABLE rebalancing_trades IS 'Individual trades executed during rebalancing';
COMMENT ON TABLE user_preferences IS 'User preferences for rebalancing and other features';
COMMENT ON COLUMN rebalancing_events.max_drift IS 'Maximum portfolio drift percentage that triggered rebalancing';
COMMENT ON COLUMN user_preferences.drift_threshold IS 'Drift percentage threshold to trigger rebalancing alert';

