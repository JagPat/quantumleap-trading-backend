const { Pool } = require('pg');

class DatabaseConnection {
  constructor() {
    this.pool = null;
    this.isConnected = false;
  }

  async initialize() {
    try {
      // Database configuration from environment variables
      const config = {
        connectionString: process.env.DATABASE_URL,
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
        max: 20, // Maximum number of clients in the pool
        idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
        connectionTimeoutMillis: 2000, // Return an error after 2 seconds if connection could not be established
      };

      // If no DATABASE_URL, try individual components
      if (!config.connectionString) {
        config.host = process.env.DB_HOST || 'localhost';
        config.port = process.env.DB_PORT || 5432;
        config.database = process.env.DB_NAME || 'quantumleap';
        config.user = process.env.DB_USER || 'postgres';
        config.password = process.env.DB_PASSWORD || '';
        delete config.connectionString;
      }

      this.pool = new Pool(config);

      // Test the connection
      const client = await this.pool.connect();
      await client.query('SELECT NOW()');
      client.release();

      this.isConnected = true;
      console.log('✅ Database connection established successfully');
      
      return true;
    } catch (error) {
      console.error('❌ Database connection failed:', error.message);
      this.isConnected = false;
      throw error;
    }
  }

  async query(text, params) {
    if (!this.isConnected || !this.pool) {
      throw new Error('Database not connected');
    }

    try {
      const start = Date.now();
      const result = await this.pool.query(text, params);
      const duration = Date.now() - start;
      
      if (process.env.NODE_ENV === 'development') {
        console.log('🔍 Database query executed:', { text, duration, rows: result.rowCount });
      }
      
      return result;
    } catch (error) {
      console.error('❌ Database query error:', error);
      throw error;
    }
  }

  async getClient() {
    if (!this.isConnected || !this.pool) {
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

  async close() {
    if (this.pool) {
      await this.pool.end();
      this.isConnected = false;
      console.log('✅ Database connection closed');
    }
  }

  getStatus() {
    return {
      connected: this.isConnected,
      totalCount: this.pool?.totalCount || 0,
      idleCount: this.pool?.idleCount || 0,
      waitingCount: this.pool?.waitingCount || 0
    };
  }
}

// Export singleton instance
const db = new DatabaseConnection();
module.exports = db;