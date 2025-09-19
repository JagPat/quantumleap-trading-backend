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
  }

  /**
   * Initialize OAuth database schema
   */
  async initialize() {
    try {
      console.log('🔧 Initializing OAuth database schema...');
      
      // Read schema file
      const schemaSQL = await fs.readFile(this.schemaPath, 'utf8');
      
      // Split into individual statements
      const statements = schemaSQL
        .split(';')
        .map(stmt => stmt.trim())
        .filter(stmt => stmt.length > 0);

      // Execute each statement
      for (const statement of statements) {
        try {
          await db.query(statement);
          console.log(`✅ Executed: ${statement.substring(0, 50)}...`);
        } catch (error) {
          // Log but don't fail on "already exists" errors
          if (error.message.includes('already exists')) {
            console.log(`ℹ️ Skipped (exists): ${statement.substring(0, 50)}...`);
          } else {
            console.error(`❌ Failed: ${statement.substring(0, 50)}...`);
            throw error;
          }
        }
      }

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