const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

class DatabaseConnection {
  constructor() {
    this.pool = null;
    this.isConnected = false;
    this.connectionAttempts = 0;
    this.maxRetries = 5;
    this.retryDelay = 5000; // 5 seconds
  }

  async initialize() {
    try {
      console.log('🔧 Initializing database connection...');
      
      // Database configuration from environment variables
      const dbConfig = {
        connectionString: process.env.DATABASE_URL,
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
        max: 20, // Maximum number of clients in the pool
        idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
        connectionTimeoutMillis: 10000, // Return an error after 10 seconds if connection could not be established
        maxUses: 7500, // Close (and replace) a connection after it has been used 7500 times
      };

      if (!dbConfig.connectionString) {
        throw new Error('DATABASE_URL environment variable is not set');
      }

      this.pool = new Pool(dbConfig);

      // Test the connection
      const client = await this.pool.connect();
      await client.query('SELECT NOW()');
      client.release();

      this.isConnected = true;
      console.log('✅ Database connection established successfully');

      // Run migrations if needed
      await this.runMigrations();

      return true;
    } catch (error) {
      console.error('❌ Database connection failed:', error.message);
      this.isConnected = false;
      
      if (this.connectionAttempts < this.maxRetries) {
        this.connectionAttempts++;
        console.log(`🔄 Retrying database connection (${this.connectionAttempts}/${this.maxRetries}) in ${this.retryDelay/1000} seconds...`);
        setTimeout(() => {
          this.initialize();
        }, this.retryDelay);
      } else {
        console.error('💥 Maximum database connection retries exceeded');
        throw error;
      }
      return false;
    }
  }

  async runMigrations() {
    try {
      console.log('🔧 Checking database schema...');
      const schemaPath = path.join(__dirname, 'schema.sql');
      
      if (!fs.existsSync(schemaPath)) {
        console.log('⚠️ Schema file not found, skipping migrations');
        return;
      }

      // Check if tables exist
      const client = await this.pool.connect();
      try {
        const result = await client.query(`
          SELECT table_name 
          FROM information_schema.tables 
          WHERE table_schema = 'public' AND table_name = 'users'
        `);

        if (result.rows.length === 0) {
          console.log('🔧 Running database migrations...');
          const schema = fs.readFileSync(schemaPath, 'utf8');
          await client.query(schema);
          console.log('✅ Database schema created successfully');
        } else {
          console.log('✅ Database schema already exists');
        }
      } finally {
        client.release();
      }
    } catch (error) {
      console.error('❌ Migration failed:', error.message);
      throw error;
    }
  }

  async query(text, params) {
    if (!this.isConnected) {
      throw new Error('Database not connected');
    }

    try {
      const start = Date.now();
      const result = await this.pool.query(text, params);
      const duration = Date.now() - start;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('🔍 Query executed:', { text: text.substring(0, 100), duration, rows: result.rowCount });
      }
      
      return result;
    } catch (error) {
      console.error('❌ Database query error:', error.message);
      throw error;
    }
  }

  async getClient() {
    if (!this.isConnected) {
      throw new Error('Database not connected');
    }
    return await this.pool.connect();
  }

  async transaction(callback) {
    const client = await this.getClient();
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async healthCheck() {
    try {
      if (!this.isConnected) {
        return { status: 'disconnected', error: 'Database not connected' };
      }

      const result = await this.query('SELECT NOW() as current_time, version() as version');
      const stats = await this.getConnectionStats();

      return {
        status: 'connected',
        timestamp: result.rows[0].current_time,
        version: result.rows[0].version,
        stats
      };
    } catch (error) {
      return {
        status: 'error',
        error: error.message
      };
    }
  }

  async getConnectionStats() {
    try {
      return {
        totalConnections: this.pool.totalCount,
        idleConnections: this.pool.idleCount,
        waitingClients: this.pool.waitingCount
      };
    } catch (error) {
      return { error: error.message };
    }
  }

  async close() {
    if (this.pool) {
      console.log('🔧 Closing database connection...');
      await this.pool.end();
      this.isConnected = false;
      console.log('✅ Database connection closed');
    }
  }
}

// Export singleton instance
module.exports = new DatabaseConnection();