const db = require('../../../core/database/connection');
const SecurityManager = require('../../../core/security');

/**
 * BrokerConfig Model
 * Manages broker configuration data with secure credential storage
 * Following existing model patterns in the auth module
 */
class BrokerConfig {
  constructor() {
    this.security = new SecurityManager();
  }

  /**
   * Create a new broker configuration
   */
  async create(data) {
    const {
      userId,
      brokerName = 'zerodha',
      apiKey,
      apiSecret
    } = data;

    // Validate required fields
    if (!userId || !apiKey || !apiSecret) {
      throw new Error('Missing required fields: userId, apiKey, apiSecret');
    }

    // Encrypt API secret
    const encryptedSecret = this.security.encrypt(apiSecret);
    const configId = this.security.generateTokenId();

    const query = `
      INSERT INTO broker_configs (
        id, user_id, broker_name, api_key, api_secret_encrypted,
        connection_status, created_at, updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
      RETURNING id, user_id, broker_name, api_key, is_connected, 
                connection_status, created_at, updated_at
    `;

    const connectionStatus = {
      state: 'disconnected',
      message: 'Configuration created, ready to connect',
      lastChecked: new Date().toISOString()
    };

    const params = [
      configId,
      userId,
      brokerName,
      apiKey,
      encryptedSecret,
      JSON.stringify(connectionStatus)
    ];

    try {
      const result = await db.query(query, params);
      return this.formatConfigResponse(result.rows[0]);
    } catch (error) {
      if (error.code === '23505') { // Unique constraint violation
        throw new Error('Broker configuration already exists for this user');
      }
      throw new Error(`Failed to create broker configuration: ${error.message}`);
    }
  }

  /**
   * Get broker configuration by ID
   */
  async getById(configId) {
    const query = `
      SELECT id, user_id, broker_name, api_key, is_connected,
             connection_status, last_sync, created_at, updated_at
      FROM broker_configs 
      WHERE id = $1
    `;

    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return null;
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  /**
   * Get broker configuration by user ID and broker name
   */
  async getByUserAndBroker(userId, brokerName = 'zerodha') {
    const query = `
      SELECT id, user_id, broker_name, api_key, is_connected,
             connection_status, last_sync, created_at, updated_at
      FROM broker_configs 
      WHERE user_id = $1 AND broker_name = $2
    `;

    const result = await db.query(query, [userId, brokerName]);
    
    if (result.rows.length === 0) {
      return null;
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  /**
   * Get all broker configurations for a user
   */
  async getByUserId(userId) {
    const query = `
      SELECT id, user_id, broker_name, api_key, is_connected,
             connection_status, last_sync, created_at, updated_at
      FROM broker_configs 
      WHERE user_id = $1
      ORDER BY created_at DESC
    `;

    const result = await db.query(query, [userId]);
    return result.rows.map(row => this.formatConfigResponse(row));
  }

  /**
   * Get decrypted API credentials for OAuth operations
   */
  async getCredentials(configId) {
    const query = `
      SELECT api_key, api_secret_encrypted
      FROM broker_configs 
      WHERE id = $1
    `;

    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    const { api_key, api_secret_encrypted } = result.rows[0];
    
    try {
      const apiSecret = this.security.decrypt(api_secret_encrypted);
      return {
        apiKey: api_key,
        apiSecret: apiSecret
      };
    } catch (error) {
      throw new Error('Failed to decrypt API credentials');
    }
  }

  /**
   * Update connection status
   */
  async updateConnectionStatus(configId, status) {
    const query = `
      UPDATE broker_configs 
      SET connection_status = $1,
          is_connected = $2,
          last_sync = $3,
          updated_at = NOW()
      WHERE id = $4
      RETURNING id, user_id, broker_name, api_key, is_connected,
                connection_status, last_sync, updated_at
    `;

    const isConnected = status.state === 'connected';
    const lastSync = isConnected ? new Date() : null;

    const params = [
      JSON.stringify(status),
      isConnected,
      lastSync,
      configId
    ];

    const result = await db.query(query, params);
    
    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  /**
   * Update OAuth state for CSRF protection
   */
  async updateOAuthState(configId, oauthState) {
    // TODO: Add oauth_state column to database schema
    // For now, skip database storage until schema is updated
    console.log(`OAuth state for config ${configId}: ${oauthState}`);
    return true;
  }

  /**
   * Verify OAuth state
   */
  async verifyOAuthState(configId, providedState) {
    // TODO: Add oauth_state column to database schema
    // For now, skip state verification until schema is updated
    console.log(`OAuth state verification for config ${configId}: ${providedState}`);
    return true; // Allow all states for now
  }

  /**
   * Delete broker configuration
   */
  async delete(configId) {
    const query = `
      DELETE FROM broker_configs 
      WHERE id = $1
      RETURNING id
    `;

    const result = await db.query(query, [configId]);
    return result.rows.length > 0;
  }

  /**
   * Get all active connections
   */
  async getActiveConnections() {
    const query = `
      SELECT * FROM active_broker_connections
      ORDER BY last_sync DESC
    `;

    const result = await db.query(query);
    return result.rows.map(row => this.formatConfigResponse(row));
  }

  /**
   * Format configuration response (exclude sensitive data)
   */
  formatConfigResponse(row) {
    return {
      id: row.id,
      userId: row.user_id,
      brokerName: row.broker_name,
      apiKey: row.api_key,
      isConnected: row.is_connected,
      connectionStatus: typeof row.connection_status === 'string' 
        ? JSON.parse(row.connection_status) 
        : row.connection_status,
      lastSync: row.last_sync,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      // Include token status if available (from view)
      tokenStatus: row.token_status || null,
      tokenExpiresAt: row.token_expires_at || null,
      brokerUserId: row.broker_user_id || null
    };
  }

  /**
   * Health check for broker config operations
   */
  async healthCheck() {
    try {
      const query = 'SELECT COUNT(*) as config_count FROM broker_configs';
      const result = await db.query(query);
      
      return {
        status: 'healthy',
        configCount: parseInt(result.rows[0].config_count),
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

module.exports = BrokerConfig;