const db = require('../../database/connection');
const fs = require('fs').promises;
const path = require('path');

/**
 * Initialize OAuth database schema
 * Creates tables and views for OAuth broker integration
 */
class OAuthDatabaseInitializer {
  constructor() {
    this.schemaPath = path.join(__dirname, '../../database/schema.sql');
    this.maxConnectionAttempts = 5;
    this.retryDelayMs = 2000;
  }

  async waitForConnection() {
    if (db.isConnected) {
      console.log('✅ OAuth initializer detected active database connection');
      return;
    }

    for (let attempt = 1; attempt <= this.maxConnectionAttempts; attempt++) {
      console.log(`🔄 [OAuthInit] Waiting for database connection (attempt ${attempt}/${this.maxConnectionAttempts})...`);
      try {
        await db.initialize();
      } catch (err) {
        console.warn(`⚠️ [OAuthInit] Database initialize attempt ${attempt} failed: ${err.message}`);
      }

      if (db.isConnected) {
        console.log('✅ [OAuthInit] Database connection established for OAuth schema initialization');
        return;
      }

      await new Promise(resolve => setTimeout(resolve, this.retryDelayMs));
    }

    throw new Error('Database not connected after retries');
  }

  async ensureCoreObjects() {
    const statements = [
      `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`,
      `CREATE TABLE IF NOT EXISTS oauth_sessions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        config_id UUID NOT NULL REFERENCES broker_configs(id) ON DELETE CASCADE,
        state VARCHAR(64) NOT NULL,
        request_token VARCHAR(255),
        status VARCHAR(20) DEFAULT 'pending',
        redirect_uri TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`,
      `CREATE OR REPLACE FUNCTION touch_oauth_sessions_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at := CURRENT_TIMESTAMP;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;`,
      `DROP TRIGGER IF EXISTS trg_oauth_sessions_updated_at ON oauth_sessions;`,
      `CREATE TRIGGER trg_oauth_sessions_updated_at
         BEFORE UPDATE ON oauth_sessions
         FOR EACH ROW EXECUTE FUNCTION touch_oauth_sessions_updated_at();`,
      `CREATE OR REPLACE VIEW active_broker_connections AS
        SELECT 
          bc.id,
          bc.user_id,
          bc.broker_name,
          bc.api_key,
          bc.is_connected,
          bc.connection_status,
          bc.last_sync,
          ot.expires_at AS token_expires_at,
          ot.broker_user_id,
          CASE
            WHEN ot.id IS NULL THEN 'no_token'
            WHEN ot.expires_at < NOW() THEN 'expired'
            WHEN ot.expires_at < NOW() + INTERVAL '1 hour' THEN 'expiring_soon'
            ELSE 'valid'
          END AS token_status
        FROM broker_configs bc
        LEFT JOIN oauth_tokens ot ON bc.id = ot.config_id
        WHERE bc.is_connected = TRUE;`,
      `CREATE OR REPLACE VIEW oauth_session_status AS
        SELECT
          os.id,
          os.config_id,
          os.state,
          os.status,
          os.expires_at,
          os.created_at,
          bc.user_id,
          bc.broker_name,
          CASE
            WHEN os.expires_at < NOW() THEN 'expired'
            WHEN os.status = 'pending' THEN 'active'
            ELSE os.status
          END AS current_status
        FROM oauth_sessions os
        JOIN broker_configs bc ON os.config_id = bc.id;`
    ];

    // Non-destructive schema fixes for production drift
    const safeAlterStatements = [
      // Postgres syntax: ALTER TABLE <name> ADD COLUMN IF NOT EXISTS ...
      // oauth_tokens expected columns
      `ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'connected'`,
      `ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS needs_reauth BOOLEAN DEFAULT false`,
      `ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS last_refreshed TIMESTAMP NULL`,
      `ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS source VARCHAR(64) NULL`,
      `ALTER TABLE oauth_tokens ADD COLUMN IF NOT EXISTS user_id UUID`,
      `CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_id ON oauth_tokens(user_id)`,
      `DO $$
      BEGIN
        ALTER TABLE oauth_tokens
        ADD CONSTRAINT oauth_tokens_user_id_fk
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
      EXCEPTION
        WHEN duplicate_object THEN NULL;
      END;
      $$`,
      // broker_configs expected columns
      `ALTER TABLE broker_configs ADD COLUMN IF NOT EXISTS needs_reauth BOOLEAN DEFAULT false`,
      `ALTER TABLE broker_configs ADD COLUMN IF NOT EXISTS session_status VARCHAR(32) DEFAULT 'disconnected'`,
      `ALTER TABLE broker_configs ADD COLUMN IF NOT EXISTS last_token_refresh TIMESTAMP NULL`,
      `ALTER TABLE broker_configs ADD COLUMN IF NOT EXISTS last_status_check TIMESTAMP NULL`
    ];

    for (const statement of statements) {
      try {
        await db.query(statement);
        console.log(`✅ [OAuthInit] Executed schema statement: ${statement.substring(0, 60)}...`);
      } catch (error) {
        console.error(`❌ [OAuthInit] Failed schema statement: ${statement.substring(0, 60)}...`, error.message);
        throw error;
      }
    }

    // Apply safe, idempotent ALTERs
    for (const statement of safeAlterStatements) {
      try {
        await db.query(statement);
        console.log(`✅ [OAuthInit] Applied safe alter: ${statement.substring(0, 60)}...`);
      } catch (error) {
        console.warn(`⚠️ [OAuthInit] Safe alter skipped: ${error.message}`);
      }
    }
  }

  /**
   * Initialize OAuth database schema
   */
  async initialize() {
    try {
      console.log('🔧 Initializing OAuth database schema...');
      await this.waitForConnection();
      
      // Attempt to run legacy schema file for backward compatibility
      try {
        const legacySchema = await fs.readFile(this.schemaPath, 'utf8');
        const statements = legacySchema
          .split(';')
          .map(stmt => stmt.trim())
          .filter(stmt => stmt.length > 0);

        for (const statement of statements) {
          try {
            await db.query(statement);
            console.log(`✅ [OAuthInit] Legacy schema statement executed: ${statement.substring(0, 50)}...`);
          } catch (legacyError) {
            if (legacyError.message && legacyError.message.includes('already exists')) {
              console.log(`ℹ️ [OAuthInit] Legacy schema already applied: ${statement.substring(0, 50)}...`);
            } else {
              console.warn(`⚠️ [OAuthInit] Skipping legacy statement due to error: ${legacyError.message}`);
            }
          }
        }
      } catch (fileError) {
        console.warn('⚠️ [OAuthInit] Legacy schema file not applied:', fileError.message);
      }

      await this.ensureCoreObjects();

      console.log('✅ OAuth database schema initialized successfully');
       
      // Verify tables were created
      await this.verifyTables();
      
      return true;
    } catch (error) {
      console.error('❌ Failed to initialize OAuth database schema:', error);
      throw error;
    }
  }

  /**
   * Verify that all required tables exist
   */
  async verifyTables() {
    const requiredTables = [
      'broker_configs',
      'oauth_tokens', 
      'oauth_sessions',
      'oauth_audit_log'
    ];

    const requiredViews = [
      'active_broker_connections',
      'oauth_session_status'
    ];

    console.log('🔍 Verifying OAuth database tables...');

    for (const table of requiredTables) {
      const result = await db.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_name = $1
        )
      `, [table]);

      if (!result.rows[0].exists) {
        throw new Error(`Required table '${table}' was not created`);
      }
      console.log(`✅ Table '${table}' exists`);
    }

    console.log('🔍 Verifying OAuth database views...');

    for (const view of requiredViews) {
      const result = await db.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.views 
          WHERE table_name = $1
        )
      `, [view]);

      if (!result.rows[0].exists) {
        throw new Error(`Required view '${view}' was not created`);
      }
      console.log(`✅ View '${view}' exists`);
    }

    console.log('✅ All OAuth database objects verified');
  }

  /**
   * Drop OAuth schema (for testing/cleanup)
   */
  async dropSchema() {
    try {
      console.log('🗑️ Dropping OAuth database schema...');
      
      const dropStatements = [
        'DROP VIEW IF EXISTS oauth_session_status',
        'DROP VIEW IF EXISTS active_broker_connections',
        'DROP TABLE IF EXISTS oauth_audit_log',
        'DROP TABLE IF EXISTS oauth_sessions',
        'DROP TABLE IF EXISTS oauth_tokens',
        'DROP TABLE IF EXISTS broker_configs'
      ];

      for (const statement of dropStatements) {
        await db.query(statement);
        console.log(`✅ ${statement}`);
      }

      console.log('✅ OAuth database schema dropped successfully');
      return true;
    } catch (error) {
      console.error('❌ Failed to drop OAuth database schema:', error);
      throw error;
    }
  }

  /**
   * Reset OAuth schema (drop and recreate)
   */
  async resetSchema() {
    await this.dropSchema();
    await this.initialize();
  }

  /**
   * Get schema status
   */
  async getStatus() {
    try {
      const tableQuery = `
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_name IN ('broker_configs', 'oauth_tokens', 'oauth_sessions', 'oauth_audit_log')
      `;

      const viewQuery = `
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_name IN ('active_broker_connections', 'oauth_session_status')
      `;

      const [tableResult, viewResult] = await Promise.all([
        db.query(tableQuery),
        db.query(viewQuery)
      ]);

      return {
        status: 'ready',
        tables: tableResult.rows.map(row => row.table_name),
        views: viewResult.rows.map(row => row.table_name),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

// Export both class and convenience functions
const initializer = new OAuthDatabaseInitializer();

module.exports = {
  OAuthDatabaseInitializer,
  initialize: () => initializer.initialize(),
  dropSchema: () => initializer.dropSchema(),
  resetSchema: () => initializer.resetSchema(),
  getStatus: () => initializer.getStatus(),
  verifyTables: () => initializer.verifyTables()
};
