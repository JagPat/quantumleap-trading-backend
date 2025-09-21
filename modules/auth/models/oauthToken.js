const db = require('../../../core/database/connection');
const SecurityManager = require('../../../core/security');

/**
 * OAuthToken Model
 * Handles secure storage of broker access tokens and lifecycle metadata.
 */
class OAuthToken {
  constructor() {
    this.security = new SecurityManager();
    this.defaultSource = 'user_login';
  }

  /**
   * Persist a fresh access token for a broker configuration.
   * Removes any existing tokens tied to the same config and (optionally) user.
   */
  async store(data) {
    const {
      configId,
      accessToken,
      refreshToken,
      expiresIn,
      tokenType = 'Bearer',
      scope,
      userId = null,
      brokerUserId = null,
      source = this.defaultSource
    } = data;

    if (!configId || !accessToken || !expiresIn) {
      throw new Error('Missing required fields: configId, accessToken, expiresIn');
    }

    const encryptedAccessToken = this.security.encrypt(accessToken);
    const encryptedRefreshToken = refreshToken ? this.security.encrypt(refreshToken) : null;
    const expiresAt = this.security.calculateTokenExpiry(expiresIn);
    const tokenId = this.security.generateTokenId();

    // Enforce single active token per config and optional per user
    await this.deleteByConfigId(configId);
    if (userId) {
      await this.deleteByUserId(userId);
    }

    const query = `
      INSERT INTO oauth_tokens (
        id,
        config_id,
        access_token_encrypted,
        refresh_token_encrypted,
        token_type,
        expires_at,
        scope,
        user_id,
        broker_user_id,
        status,
        source,
        last_refreshed,
        needs_reauth,
        created_at,
        updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'connected', $10, NOW(), false, NOW(), NOW())
      RETURNING *
    `;

    const params = [
      tokenId,
      configId,
      encryptedAccessToken,
      encryptedRefreshToken,
      tokenType,
      expiresAt,
      scope ? JSON.stringify(scope) : null,
      userId,
      brokerUserId,
      source
    ];

    const result = await db.query(query, params);
    return this.formatTokenResponse(result.rows[0]);
  }

  async getByConfigId(configId) {
    const query = `
      SELECT *
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

  async getAccessToken(configId, { allowExpired = false } = {}) {
    const tokenData = await this.getByConfigId(configId);
    if (!tokenData) {
      throw new Error('No OAuth tokens found for configuration');
    }

    if (!allowExpired && this.security.hasTokenExpired(tokenData.expiresAt)) {
      throw new Error('Access token has expired');
    }

    return this.security.decrypt(tokenData.accessTokenEncrypted);
  }

  async getRefreshToken(configId) {
    const tokenData = await this.getByConfigId(configId);
    if (!tokenData || !tokenData.refreshTokenEncrypted) {
      throw new Error('No refresh token found for configuration');
    }

    return this.security.decrypt(tokenData.refreshTokenEncrypted);
  }

  async updateTokens(configId, newTokenData) {
    const {
      accessToken,
      refreshToken,
      expiresIn,
      tokenType = 'Bearer',
      source = 'auto_refresh'
    } = newTokenData;

    const encryptedAccessToken = this.security.encrypt(accessToken);
    const encryptedRefreshToken = refreshToken ? this.security.encrypt(refreshToken) : null;
    const expiresAt = this.security.calculateTokenExpiry(expiresIn);

    const query = `
      UPDATE oauth_tokens
      SET access_token_encrypted = $1,
          refresh_token_encrypted = COALESCE($2, refresh_token_encrypted),
          token_type = $3,
          expires_at = $4,
          source = $5,
          status = 'connected',
          needs_reauth = false,
          last_refreshed = NOW(),
          updated_at = NOW()
      WHERE config_id = $6
      RETURNING *
    `;

    const params = [
      encryptedAccessToken,
      encryptedRefreshToken,
      tokenType,
      expiresAt,
      source,
      configId
    ];

    const result = await db.query(query, params);
    if (result.rows.length === 0) {
      throw new Error('No tokens found to update for configuration');
    }

    return this.formatTokenResponse(result.rows[0]);
  }

  async isValidToken(configId, bufferMinutes = 15) {
    const token = await this.getByConfigId(configId);
    if (!token) {
      return false;
    }

    if (token.needsReauth) {
      return false;
    }

    if (this.security.hasTokenExpired(token.expiresAt)) {
      return false;
    }

    return !this.security.isWithinExpiryBuffer(token.expiresAt, bufferMinutes);
  }

  async getTokenStatus(configId, bufferMinutes = 15) {
    const query = `
      SELECT config_id, expires_at, status, needs_reauth, last_refreshed, source
      FROM oauth_tokens
      WHERE config_id = $1
    `;

    const result = await db.query(query, [configId]);
    if (result.rows.length === 0) {
      return { status: 'no_token', expiresAt: null, needsReauth: true };
    }

    const row = result.rows[0];
    const expiresAt = row.expires_at;

    if (row.needs_reauth) {
      return { status: 'needs_reauth', expiresAt, needsReauth: true };
    }

    if (this.security.hasTokenExpired(expiresAt)) {
      return { status: 'expired', expiresAt, needsReauth: true };
    }

    if (this.security.isWithinExpiryBuffer(expiresAt, bufferMinutes)) {
      return { status: 'expiring_soon', expiresAt, needsReauth: false };
    }

    return {
      status: row.status || 'valid',
      expiresAt,
      source: row.source,
      needsReauth: false,
      lastRefreshed: row.last_refreshed
    };
  }

  async updateStatus(configId, status, { needsReauth = null, source = null } = {}) {
    await db.query(`
      UPDATE oauth_tokens
      SET status = $2,
          needs_reauth = COALESCE($3, needs_reauth),
          source = COALESCE($4, source),
          updated_at = NOW()
      WHERE config_id = $1
    `, [configId, status, needsReauth, source]);
  }

  async markNeedsReauth(configId, reason = 'token_expired') {
    await db.query(`
      UPDATE oauth_tokens
      SET needs_reauth = true,
          status = 'needs_reauth',
          source = $2,
          updated_at = NOW()
      WHERE config_id = $1
    `, [configId, reason]);
  }

  async deleteByConfigId(configId) {
    const result = await db.query(
      'DELETE FROM oauth_tokens WHERE config_id = $1 RETURNING id',
      [configId]
    );
    return result.rows.length;
  }

  async deleteByUserId(userId) {
    if (!userId) return 0;
    const result = await db.query(
      'DELETE FROM oauth_tokens WHERE user_id = $1 RETURNING id',
      [userId]
    );
    return result.rows.length;
  }

  async deleteExpiredTokens() {
    const result = await db.query(
      'DELETE FROM oauth_tokens WHERE expires_at < NOW() RETURNING id'
    );
    return result.rows.length;
  }

  async getExpiringSoon(minutesAhead = 60) {
    const query = `
      SELECT ot.config_id, ot.expires_at, ot.needs_reauth, ot.status, ot.user_id,
             bc.user_id AS config_user_id, bc.broker_name
      FROM oauth_tokens ot
      JOIN broker_configs bc ON ot.config_id = bc.id
      WHERE ot.expires_at BETWEEN NOW() AND NOW() + INTERVAL '${minutesAhead} minutes'
      AND bc.is_connected = true
    `;

    const result = await db.query(query);
    return result.rows;
  }

  formatTokenResponse(row, includeEncrypted = false) {
    if (!row) return null;

    const response = {
      id: row.id,
      configId: row.config_id,
      tokenType: row.token_type,
      expiresAt: row.expires_at,
      scope: typeof row.scope === 'string' ? JSON.parse(row.scope) : row.scope,
      userId: row.user_id,
      brokerUserId: row.broker_user_id,
      status: row.status,
      source: row.source,
      needsReauth: row.needs_reauth,
      lastRefreshed: row.last_refreshed,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };

    if (includeEncrypted) {
      response.accessTokenEncrypted = row.access_token_encrypted;
      response.refreshTokenEncrypted = row.refresh_token_encrypted;
    }

    return response;
  }

  async healthCheck() {
    try {
      const results = await Promise.all([
        db.query('SELECT COUNT(*) as total_tokens FROM oauth_tokens'),
        db.query('SELECT COUNT(*) as expired_tokens FROM oauth_tokens WHERE expires_at < NOW()'),
        db.query("SELECT COUNT(*) as expiring_soon FROM oauth_tokens WHERE expires_at BETWEEN NOW() AND NOW() + INTERVAL '1 hour'")
      ]);

      return {
        status: 'healthy',
        totalTokens: parseInt(results[0].rows[0].total_tokens, 10),
        expiredTokens: parseInt(results[1].rows[0].expired_tokens, 10),
        expiringSoon: parseInt(results[2].rows[0].expiring_soon, 10),
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
