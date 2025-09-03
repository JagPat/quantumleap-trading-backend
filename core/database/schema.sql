-- OAuth Broker Integration Database Schema
-- Following existing database patterns in the project

-- Broker configurations table
CREATE TABLE IF NOT EXISTS broker_configs (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  user_id VARCHAR(36) NOT NULL,
  broker_name VARCHAR(50) NOT NULL DEFAULT 'zerodha',
  api_key VARCHAR(255) NOT NULL,
  api_secret_encrypted TEXT NOT NULL,
  is_connected BOOLEAN DEFAULT FALSE,
  connection_status JSON DEFAULT '{"state": "disconnected", "message": "Not connected", "lastChecked": null}',
  oauth_state VARCHAR(64) NULL, -- For CSRF protection during OAuth flow
  last_sync TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- Indexes for performance
  INDEX idx_user_broker (user_id, broker_name),
  INDEX idx_connection_status (is_connected, broker_name),
  
  -- Constraints
  UNIQUE KEY unique_user_broker (user_id, broker_name),
  CONSTRAINT chk_broker_name CHECK (broker_name IN ('zerodha'))
);

-- OAuth tokens table
CREATE TABLE IF NOT EXISTS oauth_tokens (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  config_id VARCHAR(36) NOT NULL,
  access_token_encrypted TEXT NOT NULL,
  refresh_token_encrypted TEXT NULL,
  token_type VARCHAR(20) DEFAULT 'Bearer',
  expires_at TIMESTAMP NOT NULL,
  scope JSON NULL,
  user_id VARCHAR(255) NULL, -- Zerodha user ID from token response
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- Foreign key relationship
  FOREIGN KEY (config_id) REFERENCES broker_configs(id) ON DELETE CASCADE,
  
  -- Indexes
  INDEX idx_config_id (config_id),
  INDEX idx_expires_at (expires_at),
  INDEX idx_user_id (user_id)
);

-- OAuth sessions table (for tracking active OAuth flows)
CREATE TABLE IF NOT EXISTS oauth_sessions (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  config_id VARCHAR(36) NOT NULL,
  state VARCHAR(64) NOT NULL,
  request_token VARCHAR(255) NULL,
  status ENUM('pending', 'completed', 'failed', 'expired') DEFAULT 'pending',
  redirect_uri TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  -- Foreign key
  FOREIGN KEY (config_id) REFERENCES broker_configs(id) ON DELETE CASCADE,
  
  -- Indexes
  INDEX idx_state (state),
  INDEX idx_status_expires (status, expires_at),
  INDEX idx_config_id (config_id)
);

-- Add audit log table for OAuth operations
CREATE TABLE IF NOT EXISTS oauth_audit_log (
  id VARCHAR(36) PRIMARY KEY DEFAULT (UUID()),
  config_id VARCHAR(36) NULL,
  user_id VARCHAR(36) NOT NULL,
  action VARCHAR(50) NOT NULL, -- 'oauth_initiated', 'token_exchanged', 'token_refreshed', 'disconnected'
  status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'error'
  details JSON NULL,
  ip_address VARCHAR(45) NULL,
  user_agent TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  -- Foreign key (nullable for cases where config is deleted)
  FOREIGN KEY (config_id) REFERENCES broker_configs(id) ON DELETE SET NULL,
  
  -- Indexes
  INDEX idx_user_action (user_id, action),
  INDEX idx_created_at (created_at),
  INDEX idx_config_id (config_id)
);

-- Create views for easier querying
CREATE OR REPLACE VIEW active_broker_connections AS
SELECT 
  bc.id,
  bc.user_id,
  bc.broker_name,
  bc.api_key,
  bc.is_connected,
  bc.connection_status,
  bc.last_sync,
  ot.expires_at as token_expires_at,
  ot.user_id as broker_user_id,
  CASE 
    WHEN ot.expires_at IS NULL THEN 'no_token'
    WHEN ot.expires_at < NOW() THEN 'expired'
    WHEN ot.expires_at < DATE_ADD(NOW(), INTERVAL 1 HOUR) THEN 'expiring_soon'
    ELSE 'valid'
  END as token_status
FROM broker_configs bc
LEFT JOIN oauth_tokens ot ON bc.id = ot.config_id
WHERE bc.is_connected = TRUE;

-- Create view for OAuth session monitoring
CREATE OR REPLACE VIEW oauth_session_status AS
SELECT 
  os.id,
  os.config_id,
  os.state,
  os.status,
  os.expires_at,
  bc.user_id,
  bc.broker_name,
  CASE 
    WHEN os.expires_at < NOW() THEN 'expired'
    WHEN os.status = 'pending' AND os.expires_at > NOW() THEN 'active'
    ELSE os.status
  END as current_status
FROM oauth_sessions os
JOIN broker_configs bc ON os.config_id = bc.id;