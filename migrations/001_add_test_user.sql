-- Migration: Add Test User for Authentication Testing
-- This migration creates a test user that can be used for backend API testing

-- Create test user in main users table
INSERT OR IGNORE INTO users (user_id, api_key, api_secret, user_name, email, created_at, updated_at)
VALUES (
  'test-user-001',
  'test_api_key_001',
  'test_api_secret_001', 
  'Test User',
  'test@quantumleap.com',
  datetime('now'),
  datetime('now')
);

-- Create auth_users table if it doesn't exist
CREATE TABLE IF NOT EXISTS auth_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    user_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add authentication record for test user
-- Password hash is SHA256 of 'test123'
INSERT OR IGNORE INTO auth_users (email, password_hash, user_id, is_active)
VALUES (
  'test@quantumleap.com',
  '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
  'test-user-001',
  1
);

-- Verify the user was created
SELECT 'Test user created:' as message, email, user_id, is_active 
FROM auth_users 
WHERE email = 'test@quantumleap.com';