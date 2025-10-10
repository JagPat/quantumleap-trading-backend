-- Strategy Automation Tables Migration
-- Adds tables for goal-based strategy automation, order execution tracking, and performance monitoring

-- Strategy automation goals and configurations
CREATE TABLE IF NOT EXISTS strategy_automations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    config_id UUID REFERENCES broker_configs(id) ON DELETE SET NULL,
    strategy_id UUID, -- links to AI-generated strategy if applicable
    name VARCHAR(100) NOT NULL,
    profit_target_percent DECIMAL(5,2) NOT NULL,
    timeframe_days INTEGER NOT NULL,
    max_loss_percent DECIMAL(5,2) NOT NULL,
    risk_tolerance VARCHAR(20) DEFAULT 'moderate', -- 'low', 'moderate', 'high'
    symbols JSONB DEFAULT '[]', -- target symbols array
    strategy_rules JSONB, -- AI-generated entry/exit rules
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'active', 'paused', 'completed', 'rejected'
    trading_mode VARCHAR(10) DEFAULT 'paper', -- 'paper', 'live'
    is_active BOOLEAN DEFAULT false,
    ai_confidence_score DECIMAL(3,2), -- AI confidence in strategy (0.0-1.0)
    approved_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order execution log (paper + live trades)
CREATE TABLE IF NOT EXISTS automated_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    automation_id UUID NOT NULL REFERENCES strategy_automations(id) ON DELETE CASCADE,
    order_id VARCHAR(100), -- broker order ID (null for paper trades)
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'NSE',
    transaction_type VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    order_type VARCHAR(20) NOT NULL, -- 'MARKET', 'LIMIT', 'SL', 'SL-M'
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    trigger_price DECIMAL(10,2),
    executed_quantity INTEGER DEFAULT 0,
    executed_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'OPEN', 'COMPLETE', 'CANCELLED', 'REJECTED'
    is_paper_trade BOOLEAN DEFAULT true,
    trigger_reason TEXT, -- why this order was placed
    pnl DECIMAL(15,2), -- realized P&L for this order
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance tracking (daily snapshots)
CREATE TABLE IF NOT EXISTS automation_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    automation_id UUID NOT NULL REFERENCES strategy_automations(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_pnl DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    trades_count INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    max_drawdown DECIMAL(5,2) DEFAULT 0,
    goal_progress_percent DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(automation_id, date)
);

-- Add trading mode preferences to broker_configs if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='broker_configs' AND column_name='trading_mode') THEN
        ALTER TABLE broker_configs ADD COLUMN trading_mode VARCHAR(10) DEFAULT 'paper';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='broker_configs' AND column_name='max_daily_loss') THEN
        ALTER TABLE broker_configs ADD COLUMN max_daily_loss DECIMAL(10,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='broker_configs' AND column_name='max_trades_per_day') THEN
        ALTER TABLE broker_configs ADD COLUMN max_trades_per_day INTEGER DEFAULT 10;
    END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_strategy_automations_user_id ON strategy_automations(user_id);
CREATE INDEX IF NOT EXISTS idx_strategy_automations_status ON strategy_automations(status);
CREATE INDEX IF NOT EXISTS idx_strategy_automations_is_active ON strategy_automations(is_active);
CREATE INDEX IF NOT EXISTS idx_automated_orders_automation_id ON automated_orders(automation_id);
CREATE INDEX IF NOT EXISTS idx_automated_orders_symbol ON automated_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_automated_orders_status ON automated_orders(status);
CREATE INDEX IF NOT EXISTS idx_automation_performance_automation_id ON automation_performance(automation_id);
CREATE INDEX IF NOT EXISTS idx_automation_performance_date ON automation_performance(date);

-- Add updated_at trigger for strategy_automations
CREATE OR REPLACE FUNCTION update_strategy_automation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_strategy_automation_updated_at ON strategy_automations;
CREATE TRIGGER trigger_update_strategy_automation_updated_at
    BEFORE UPDATE ON strategy_automations
    FOR EACH ROW
    EXECUTE FUNCTION update_strategy_automation_updated_at();

-- Add updated_at trigger for automated_orders
DROP TRIGGER IF EXISTS trigger_update_automated_order_updated_at ON automated_orders;
CREATE TRIGGER trigger_update_automated_order_updated_at
    BEFORE UPDATE ON automated_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_strategy_automation_updated_at();

