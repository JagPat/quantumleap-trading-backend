const db = require('../../core/database/connection');
const crypto = require('crypto');

class BrokerConfig {
  constructor() {
    this.tableName = 'broker_configs';
  }

  // Encrypt sensitive data
  encrypt(text) {
    const algorithm = 'aes-256-gcm';
    const key = Buffer.from(process.env.OAUTH_ENCRYPTION_KEY || 'default-key-32-characters-long!!', 'utf8');
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher(algorithm, key);
    
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    const authTag = cipher.getAuthTag();
    
    return iv.toString('hex') + ':' + authTag.toString('hex') + ':' + encrypted;
  }

  // Decrypt sensitive data
  decrypt(encryptedText) {
    const algorithm = 'aes-256-gcm';
    const key = Buffer.from(process.env.OAUTH_ENCRYPTION_KEY || 'default-key-32-characters-long!!', 'utf8');
    const parts = encryptedText.split(':');
    const iv = Buffer.from(parts[0], 'hex');
    const authTag = Buffer.from(parts[1], 'hex');
    const encrypted = parts[2];
    
    const decipher = crypto.createDecipher(algorithm, key);
    decipher.setAuthTag(authTag);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  async create(data) {
    const {
      userId,
      brokerName,
      apiKey,
      apiSecret,
      brokerUserId = null,
      brokerUserName = null,
      brokerUserType = null
    } = data;

    const query = `
      INSERT INTO ${this.tableName} (
        user_id, broker_name, api_key_encrypted, api_secret_encrypted,
        broker_user_id, broker_user_name, broker_user_type
      ) VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING *
    `;

    const values = [
      userId,
      brokerName,
      this.encrypt(apiKey),
      this.encrypt(apiSecret),
      brokerUserId,
      brokerUserName,
      brokerUserType
    ];

    const result = await db.query(query, values);
    return this.formatConfig(result.rows[0]);
  }

  async findById(id) {
    const query = `SELECT * FROM ${this.tableName} WHERE id = $1`;
    const result = await db.query(query, [id]);
    
    if (result.rows.length === 0) {
      return null;
    }
    
    return this.formatConfig(result.rows[0]);
  }

  async findByUserAndBroker(userId, brokerName) {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE user_id = $1 AND broker_name = $2
    `;
    const result = await db.query(query, [userId, brokerName]);
    
    if (result.rows.length === 0) {
      return null;
    }
    
    return this.formatConfig(result.rows[0]);
  }

  async findByUser(userId) {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE user_id = $1 
      ORDER BY created_at DESC
    `;
    const result = await db.query(query, [userId]);
    return result.rows.map(row => this.formatConfig(row));
  }

  async updateConnectionStatus(id, status, brokerUserData = {}) {
    const {
      brokerUserId,
      brokerUserName,
      brokerUserType
    } = brokerUserData;

    const query = `
      UPDATE ${this.tableName} 
      SET 
        is_connected = $2,
        connection_status = $3,
        broker_user_id = COALESCE($4, broker_user_id),
        broker_user_name = COALESCE($5, broker_user_name),
        broker_user_type = COALESCE($6, broker_user_type),
        last_sync_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
      RETURNING *
    `;

    const values = [
      id,
      status.state === 'connected',
      JSON.stringify(status),
      brokerUserId,
      brokerUserName,
      brokerUserType
    ];

    const result = await db.query(query, values);
    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    return this.formatConfig(result.rows[0]);
  }

  async delete(id) {
    const query = `DELETE FROM ${this.tableName} WHERE id = $1 RETURNING *`;
    const result = await db.query(query, [id]);
    
    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }
    
    return this.formatConfig(result.rows[0]);
  }

  async getConnectedConfigs() {
    const query = `
      SELECT * FROM ${this.tableName} 
      WHERE is_connected = true 
      ORDER BY last_sync_at DESC
    `;
    const result = await db.query(query);
    return result.rows.map(row => this.formatConfig(row));
  }

  // Format config object and decrypt sensitive fields when needed
  formatConfig(row, includeSensitive = false) {
    if (!row) return null;

    const config = {
      id: row.id,
      userId: row.user_id,
      brokerName: row.broker_name,
      isConnected: row.is_connected,
      connectionStatus: row.connection_status,
      brokerUserId: row.broker_user_id,
      brokerUserName: row.broker_user_name,
      brokerUserType: row.broker_user_type,
      lastSyncAt: row.last_sync_at,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };

    // Only decrypt sensitive fields when explicitly requested
    if (includeSensitive) {
      try {
        config.apiKey = this.decrypt(row.api_key_encrypted);
        config.apiSecret = this.decrypt(row.api_secret_encrypted);
      } catch (error) {
        console.error('Failed to decrypt broker config:', error.message);
        config.apiKey = null;
        config.apiSecret = null;
      }
    }

    return config;
  }

  // Get decrypted credentials for OAuth operations
  async getCredentials(id) {
    const query = `
      SELECT api_key_encrypted, api_secret_encrypted 
      FROM ${this.tableName} 
      WHERE id = $1
    `;
    const result = await db.query(query, [id]);
    
    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    const row = result.rows[0];
    try {
      return {
        apiKey: this.decrypt(row.api_key_encrypted),
        apiSecret: this.decrypt(row.api_secret_encrypted)
      };
    } catch (error) {
      throw new Error('Failed to decrypt broker credentials');
    }
  }

  // Alias methods for OAuth route compatibility
  async getById(id) {
    return this.findById(id);
  }

  async getByUserAndBroker(userId, brokerName) {
    return this.findByUserAndBroker(userId, brokerName);
  }

  // OAuth state management methods
  async updateOAuthState(configId, oauthState) {
    const query = `
      UPDATE ${this.tableName} 
      SET oauth_state = $1, updated_at = CURRENT_TIMESTAMP
      WHERE id = $2
    `;
    await db.query(query, [oauthState, configId]);
  }

  async verifyOAuthState(configId, providedState) {
    const query = `
      SELECT oauth_state FROM ${this.tableName} WHERE id = $1
    `;
    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return false;
    }

    const storedState = result.rows[0].oauth_state;
    return storedState === providedState; // Simple comparison for now
  }
}

module.exports = new BrokerConfig();