/**
 * AI Preferences Database Schema
 * Stores user AI API keys (encrypted) and preferences
 */

const { pool: db } = require('./pool');

const initAIPreferences = async () => {
  console.log('[AIPreferences] Initializing AI preferences schema...');

  const statements = [
    // Create ai_preferences table
    `CREATE TABLE IF NOT EXISTS ai_preferences (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id VARCHAR(255) NOT NULL,
      config_id UUID REFERENCES broker_configs(id) ON DELETE CASCADE,
      preferred_ai_provider VARCHAR(50) DEFAULT 'auto',
      openai_api_key_encrypted TEXT,
      claude_api_key_encrypted TEXT,
      gemini_api_key_encrypted TEXT,
      openai_key_preview VARCHAR(50),
      claude_key_preview VARCHAR(50),
      gemini_key_preview VARCHAR(50),
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW(),
      CONSTRAINT unique_user_ai_prefs UNIQUE(user_id)
    )`,

    // Create index for faster lookups
    `CREATE INDEX IF NOT EXISTS idx_ai_preferences_user_id ON ai_preferences(user_id)`,
    `CREATE INDEX IF NOT EXISTS idx_ai_preferences_config_id ON ai_preferences(config_id)`,

    // Create updated_at trigger
    `CREATE OR REPLACE FUNCTION update_ai_preferences_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql`,

    `DROP TRIGGER IF EXISTS trigger_ai_preferences_updated_at ON ai_preferences`,
    
    `CREATE TRIGGER trigger_ai_preferences_updated_at
    BEFORE UPDATE ON ai_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_preferences_updated_at()`
  ];

  try {
    for (const statement of statements) {
      await db.query(statement);
    }
    
    console.log('✅ [AIPreferences] Schema initialized successfully');
    
    // Verify table exists
    const verifyResult = await db.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name = 'ai_preferences'
    `);
    
    if (verifyResult.rows.length > 0) {
      console.log('✅ [AIPreferences] Table verified');
    } else {
      console.warn('⚠️ [AIPreferences] Table verification failed');
    }
    
    return true;
  } catch (error) {
    console.error('❌ [AIPreferences] Failed to initialize schema:', error);
    throw error;
  }
};

module.exports = { initAIPreferences };



