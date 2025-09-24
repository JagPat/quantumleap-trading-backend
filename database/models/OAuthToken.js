const db = require('../../core/database/connection');
const SecurityManager = require('../../core/security');

class OAuthToken {
  constructor() {
    this.tableName = 'oauth_tokens';
    this.security = new SecurityManager();
  }

  async create(data) {
    const {
      configId,
      accessToken,
      refreshToken,
      tokenType = 'Bearer',
      expiresIn,
      scope = null
    } = data;

    // Calculate expiration time
    const expiresAt = new Date(Date.now() + (expiresIn * 1000));

    const query = `
      INSERT INTO ${this.tableName} (
        config_id, access_token_encrypted, refresh_token_encrypted,
        token_type, expires_at, scope
      ) VALUES ($1, $2, $3, $4, $5, $6)
      ON CONFLICT (config_id) 
      DO UPDATE SET
        access_token_encrypted = EXCLUDED.access_token_encrypted,
        refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
        token_type = EXCLUDED.token_type,
        expires_at = EXCLUDED.expires_at,
        scope = EXCLUDED.scope,
        updated_at = CURRENT_TIMESTAMP
      RETURNING *
    `;

    const values = [
      configId,
      this.security.encrypt(accessToken),
      refreshToken ? this.security.encrypt(refreshToken) : null,
      tokenType,
      expiresAt,
      scope
    ];

    const result = await db.query(query, values);
    return this.formatToken(result.rows[0]);
  }

  async findByConfigId(configId) {
    const query = `SELECT * FROM ${this.tableName} WHERE config_id = $1`;
    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return null;
    }
    
    return this.formatToken(result.rows[0]);
  }

  async getDecryptedTokens(configId) {
    const query = `
      SELECT access_token_encrypted, refresh_token_encrypted, expires_at, token_type
      FROM ${this.tableName} 
      WHERE config_id = $1
    `;
    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    try {
      return {
        accessToken: this.security.decrypt(row.access_token_encrypted),
        refreshToken: row.refresh_token_encrypted ? this.security.decrypt(row.refresh_token_encrypted) : null,
        expiresAt: row.expires_at,
        tokenType: row.token_type,
        isExpired: new Date(row.expires_at) < new Date()
      };
    } catch (error) {
      throw new Error('Failed to decrypt OAuth tokens');
    }
  }

  async updateTokens(configId, data) {
    const {
      accessToken,
      refreshToken,
      expiresIn
    } = data;

    const expiresAt = new Date(Date.now() + (expiresIn * 1000));

    const query = `
      UPDATE ${this.tableName} 
      SET 
        access_token_encrypted = $2,
        refresh_token_encrypted = COALESCE($3, refresh_token_encrypted),
        expires_at = $4,
        updated_at = CURRENT_TIMESTAMP
      WHERE config_id = $1
      RETURNING *
    `;

    const values = [
      configId,
      this.security.encrypt(accessToken),
      refreshToken ? this.security.encrypt(refreshToken) : null,
      expiresAt
    ];

    const result = await db.query(query, values);
    if (result.rows.length === 0) {
      throw new Error('OAuth tokens not found');
    }

    return this.formatToken(result.rows[0]);
  }

  async deleteByConfigId(configId) {
    const query = `DELETE FROM ${this.tableName} WHERE config_id = $1 RETURNING *`;
    const result = await db.query(query, [configId]);
    return result.rows.length > 0;
  }

  async getExpiringTokens(thresholdMinutes = 60) {
    const threshold = new Date(Date.now() + (thresholdMinutes * 60 * 1000));
    
    const query = `
      SELECT ot.*, bc.user_id, bc.broker_name
      FROM ${this.tableName} ot
      JOIN broker_configs bc ON ot.config_id = bc.id
      WHERE ot.expires_at <= $1 AND bc.is_connected = true
      ORDER BY ot.expires_at ASC
    `;
    const result = await db.query(query, [threshold]);
    
    return result.rows.map(row => ({
      ...this.formatToken(row),
      userId: row.user_id,
      brokerName: row.broker_name
    }));
  }

  async cleanupExpiredTokens() {
    const query = `
      DELETE FROM ${this.tableName} 
      WHERE expires_at < NOW() - INTERVAL '7 days'
      RETURNING count(*)
    `;
    const result = await db.query(query);
    return result.rowCount;
  }

  // Format token object (without decrypting)
  formatToken(row) {
    if (!row) return null;

    return {
      id: row.id,
      configId: row.config_id,
      tokenType: row.token_type,
      expiresAt: row.expires_at,
      scope: row.scope,
      isExpired: new Date(row.expires_at) < new Date(),
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }

  // Alias methods for OAuth route compatibility
  async store(data) {
    return this.create(data);
  }

  async getRefreshToken(configId) {
    const tokens = await this.getDecryptedTokens(configId);
    return tokens ? tokens.refreshToken : null;
  }

  async getAccessToken(configId) {
    const tokens = await this.getDecryptedTokens(configId);
    return tokens ? tokens.accessToken : null;
  }

  async getTokenStatus(configId) {
    const token = await this.findByConfigId(configId);
    if (!token) {
      return {
        status: 'no_token',
        isExpired: true,
        expiresAt: null
      };
    }

    const isExpired = new Date(token.expiresAt) < new Date();
    const expiresIn = Math.max(0, new Date(token.expiresAt).getTime() - Date.now());
    const expiringThreshold = 60 * 60 * 1000; // 1 hour

    let status = 'valid';
    if (isExpired) {
      status = 'expired';
    } else if (expiresIn < expiringThreshold) {
      status = 'expiring_soon';
    }

    return {
      status,
      isExpired,
      expiresAt: token.expiresAt,
      expiresIn: Math.floor(expiresIn / 1000) // in seconds
    };
  }
}

module.exports = new OAuthToken();
