-- @name: Add User Preferences
-- @description: Add user preferences and settings columns to users table
-- @type: table_modification
-- @author: Database Migration System
-- @dependencies: ["001_create_users_table"]
-- @reversible: true
-- @backup_required: true

-- UP
ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en';
ALTER TABLE users ADD COLUMN currency TEXT DEFAULT 'USD';
ALTER TABLE users ADD COLUMN notification_preferences TEXT DEFAULT '{}';
ALTER TABLE users ADD COLUMN trading_preferences TEXT DEFAULT '{}';
ALTER TABLE users ADD COLUMN risk_tolerance TEXT DEFAULT 'moderate';
ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0;

CREATE INDEX idx_users_timezone ON users(timezone);
CREATE INDEX idx_users_currency ON users(currency);
CREATE INDEX idx_users_risk_tolerance ON users(risk_tolerance);
CREATE INDEX idx_users_last_login ON users(last_login_at);

-- DOWN
DROP INDEX IF EXISTS idx_users_last_login;
DROP INDEX IF EXISTS idx_users_risk_tolerance;
DROP INDEX IF EXISTS idx_users_currency;
DROP INDEX IF EXISTS idx_users_timezone;

-- Note: SQLite doesn't support DROP COLUMN, so we would need to recreate the table
-- For this example, we'll leave the columns (they can be ignored)
-- In a real scenario, you might recreate the table without these columns