const db = require('../../../core/database/connection');
const SecurityManager = require('../../../core/security');

/**
 * OAuthToken Model
 * Manages OAuth token storage with encryption and lifecycle management
 * Following existing model patterns in the auth module
 */
class OAuthToken {
  constructor() {
    this.security = new SecurityManager();
  }

  /**
   * Store OAuth tokens securely
   */
  async store(data) {
    const {
      configId,
      accessToken,
      refreshToken,
      expiresIn,
      tokenType = 'Bearer',
      scope,
      userId // Zerodha user ID from token response
    } = data;

    // Validate required fields
    if (!configId || !accessToken || !expiresIn) {
      throw new Error('Missing required fields: configId, accessToken, expiresIn');
    }

    // Encrypt tokens
    const encryptedAccessToken = this.security.encrypt(accessToken);
    const encryptedRefreshToken = refreshToken ? this.security.encrypt(refreshToken) : null;
    
    // Calculate expiry time with buffer
    const expiresAt = this.security.calculateTokenExpiry(expiresIn);
    const tokenId = this.security.generateTokenId();

    // First, delete any existing tokens for this config
    await this.deleteByConfigId(configId);

    const query = `
      INSERT INTO oauth_tokens (
        id, config_id, access_token_encrypted, refresh_token_encrypted,
        token_type, expires_at, scope, user_id, created_at, updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
      RETURNING id, config_id, token_type, expires_at, scope, user_id, created_at
    `;

    const params = [
      tokenId,
      configId,
      encryptedAccessToken,
      encryptedRefreshToken,
      tokenType,
      expiresAt,
      scope ? JSON.stringify(scope) : null,
      userId
    ];

    try {
      const result = await db.query(query, params);
      return this.formatTokenResponse(result.rows[0]);
    } catch (error) {
      throw new Error(`Failed to store OAuth tokens: ${error.message}`);
    }
  }

  /**
   * Get OAuth tokens by config ID
   */
  async getByConfigId(configId) {
    const query = `
      SELECT id, config_id, access_token_encrypted, refresh_token_encrypted,
             token_type, expires_at, scope, user_id, created_at, updated_at
      FROM oauth_tokens 
      WHERE config_id = $1
      ORDER BY created_at DESC
      LIMIT 1
    `;

    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return null;
    }

    return this.formatTokenResponse(result.rows[0], true);
  }

  /**
   * Get decrypted access token for API calls
   */
  async getAccessToken(configId) {
    const tokenData = await this.getByConfigId(configId);
    
    if (!tokenData) {
      throw new Error('No OAuth tokens found for configuration');
    }

    if (this.security.isTokenExpired(tokenData.expiresAt)) {
      throw new Error('Access token has expired');
    }

    try {
      return this.security.decrypt(tokenData.accessTokenEncrypted);
    } catch (error) {
      throw new Error('Failed to decrypt access token');
    }
  }

  /**
   * Get decrypted refresh token for token refresh
   */
  async getRefreshToken(configId) {
    const tokenData = await this.getByConfigId(configId);
    
    if (!tokenData || !tokenData.refreshTokenEncrypted) {
      throw new Error('No refresh token found for configuration');
    }

    try {
      return this.security.decrypt(tokenData.refreshTokenEncrypted);
    } catch (error) {
      throw new Error('Failed to decrypt refresh token');
    }
  }

  /**
   * Update tokens (for refresh operations)
   */
  async updateTokens(configId, newTokenData) {
    const {
      accessToken,
      refreshToken,
      expiresIn,
      tokenType = 'Bearer'
    } = newTokenData;

    // Encrypt new tokens
    const encryptedAccessToken = this.security.encrypt(accessToken);
    const encryptedRefreshToken = refreshToken ? this.security.encrypt(refreshToken) : null;
    
    // Calculate new expiry
    const expiresAt = this.security.calculateTokenExpiry(expiresIn);

    const query = `
      UPDATE oauth_tokens 
      SET access_token_encrypted = $1,
          refresh_token_encrypted = $2,
          token_type = $3,
          expires_at = $4,
          updated_at = NOW()
      WHERE config_id = $5
      RETURNING id, config_id, token_type, expires_at, scope, user_id, updated_at
    `;

    const params = [
      encryptedAccessToken,
      encryptedRefreshToken,
      tokenType,
      expiresAt,
      configId
    ];

    const result = await db.query(query, params);
    
    if (result.rows.length === 0) {
      throw new Error('No tokens found to update for configuration');
    }

    return this.formatTokenResponse(result.rows[0]);
  }

  /**
   * Check if token exists and is valid
   */
  async isValidToken(configId) {
    const query = `
      SELECT expires_at
      FROM oauth_tokens 
      WHERE config_id = $1
    `;

    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return false;
    }

    const expiresAt = result.rows[0].expires_at;
    return !this.security.isTokenExpired(expiresAt);
  }

  /**
   * Get token expiry status
   */
  async getTokenStatus(configId) {
    const query = `
      SELECT expires_at, created_at
      FROM oauth_tokens 
      WHERE config_id = $1
    `;

    const result = await db.query(query, [configId]);
    
    if (result.rows.length === 0) {
      return { status: 'no_token', expiresAt: null };
    }

    const expiresAt = result.rows[0].expires_at;
    const now = new Date();
    const expiry = new Date(expiresAt);
    const oneHour = 60 * 60 * 1000; // 1 hour in milliseconds

    if (now >= expiry) {
      return { status: 'expired', expiresAt };
    } else if ((expiry - now) < oneHour) {
      return { status: 'expiring_soon', expiresAt };
    } else {
      return { status: 'valid', expiresAt };
    }
  }

  /**
   * Delete tokens by config ID
   */
  async deleteByConfigId(configId) {
    const query = `
      DELETE FROM oauth_tokens 
      WHERE config_id = $1
      RETURNING id
    `;

    const result = await db.query(query, [configId]);
    return result.rows.length;
  }

  /**
   * Delete expired tokens (cleanup job)
   */
  async deleteExpiredTokens() {
    const query = `
      DELETE FROM oauth_tokens 
      WHERE expires_at < NOW()
      RETURNING id
    `;

    const result = await db.query(query);
    return result.rows.length;
  }

  /**
   * Get all tokens expiring soon (for proactive refresh)
   */
  async getExpiringSoon(minutesAhead = 60) {
    const query = `
      SELECT ot.config_id, ot.expires_at, bc.user_id, bc.broker_name
      FROM oauth_tokens ot
      JOIN broker_configs bc ON ot.config_id = bc.id
      WHERE ot.expires_at BETWEEN NOW() AND NOW() + INTERVAL '${minutesAhead} minutes'
      AND bc.is_connected = true
    `;

    const result = await db.query(query);
    return result.rows;
  }

  /**
   * Format token response (exclude encrypted data in basic format)
   */
  formatTokenResponse(row, includeEncrypted = false) {
    const response = {
      id: row.id,
      configId: row.config_id,
      tokenType: row.token_type,
      expiresAt: row.expires_at,
      scope: typeof row.scope === 'string' ? JSON.parse(row.scope) : row.scope,
      userId: row.user_id,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };

    if (includeEncrypted) {
      response.accessTokenEncrypted = row.access_token_encrypted;
      response.refreshTokenEncrypted = row.refresh_token_encrypted;
    }

    return response;
  }

  /**
   * Health check for token operations
   */
  async healthCheck() {
    try {
      const queries = [
        'SELECT COUNT(*) as total_tokens FROM oauth_tokens',
        'SELECT COUNT(*) as expired_tokens FROM oauth_tokens WHERE expires_at < NOW()',
        'SELECT COUNT(*) as expiring_soon FROM oauth_tokens WHERE expires_at BETWEEN NOW() AND NOW() + INTERVAL \'1 hour\''
      ];

      const results = await Promise.all(
        queries.map(query => db.query(query))
      );

      return {
        status: 'healthy',
        totalTokens: parseInt(results[0].rows[0].total_tokens),
        expiredTokens: parseInt(results[1].rows[0].expired_tokens),
        expiringSoon: parseInt(results[2].rows[0].expiring_soon),
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

module.exports = OAuthToken;