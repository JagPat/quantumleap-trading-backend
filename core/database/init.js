const db = require('./connection');
const migrations = require('./migrations');

class DatabaseInitializer {
  async initialize() {
    try {
      console.log('🔄 Initializing database...');

      // Step 1: Connect to database
      await db.initialize();

      // Step 2: Run migrations
      await migrations.runMigrations();

      // Step 3: Verify database health
      await this.verifyDatabaseHealth();

      console.log('✅ Database initialization completed successfully');
      return true;

    } catch (error) {
      console.error('❌ Database initialization failed:', error);
      
      // If database connection fails, continue without database for development
      if (process.env.NODE_ENV === 'development') {
        console.warn('⚠️ Continuing without database in development mode');
        return false;
      }
      
      throw error;
    }
  }

  async verifyDatabaseHealth() {
    try {
      // Test basic operations
      const result = await db.query('SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = $1', ['public']);
      const tableCount = parseInt(result.rows[0].table_count);
      
      console.log(`📊 Database health check: ${tableCount} tables found`);
      
      // Verify critical tables exist
      const criticalTables = ['users', 'broker_configs', 'oauth_tokens'];
      for (const table of criticalTables) {
        const tableExists = await db.query(
          'SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = $1 AND table_name = $2)',
          ['public', table]
        );
        
        if (!tableExists.rows[0].exists) {
          throw new Error(`Critical table '${table}' not found`);
        }
      }
      
      console.log('✅ All critical tables verified');
      return true;
      
    } catch (error) {
      console.error('❌ Database health check failed:', error);
      throw error;
    }
  }

  async getStatus() {
    try {
      const dbStatus = db.getStatus();
      
      if (!dbStatus.connected) {
        return {
          status: 'disconnected',
          error: 'Database not connected'
        };
      }

      // Get table counts
      const tablesResult = await db.query(`
        SELECT 
          schemaname,
          tablename,
          n_tup_ins as inserts,
          n_tup_upd as updates,
          n_tup_del as deletes
        FROM pg_stat_user_tables 
        ORDER BY schemaname, tablename
      `);

      // Get database size
      const sizeResult = await db.query(`
        SELECT pg_size_pretty(pg_database_size(current_database())) as size
      `);

      return {
        status: 'connected',
        connection: dbStatus,
        tables: tablesResult.rows,
        size: sizeResult.rows[0]?.size || 'unknown',
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

  async cleanup() {
    try {
      await db.close();
      console.log('✅ Database cleanup completed');
    } catch (error) {
      console.error('❌ Database cleanup failed:', error);
    }
  }
}

module.exports = new DatabaseInitializer();