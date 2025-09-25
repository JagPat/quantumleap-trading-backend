const db = require('../../../core/database/connection');
const SecurityManager = require('../../../core/security');

/**
 * BrokerConfig Model
 * Handles persistence of broker configuration/connection metadata.
 */
class BrokerConfig {
  constructor() {
    this.security = new SecurityManager();
  }

  async create(data) {
    const {
      userId,
      brokerName = 'zerodha',
      apiKey,
      apiSecret
    } = data;

    if (!userId || !apiKey || !apiSecret) {
      throw new Error('Missing required fields: userId, apiKey, apiSecret');
    }

    const encryptedSecret = this.security.encrypt(apiSecret);
    const configId = this.security.generateTokenId();

    const connectionStatus = {
      state: 'disconnected',
      message: 'Configuration created, awaiting authentication',
      lastChecked: new Date().toISOString()
    };

    const query = `
      INSERT INTO broker_configs (
        id,
        user_id,
        broker_name,
        api_key,
        api_secret_encrypted,
        connection_status,
        session_status,
        needs_reauth,
        created_at,
        updated_at
      ) VALUES ($1, $2, $3, $4, $5, $6, 'disconnected', false, NOW(), NOW())
      RETURNING *
    `;

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
      if (error.code === '23505') {
        throw new Error('Broker configuration already exists for this user');
      }
      throw new Error(`Failed to create broker configuration: ${error.message}`);
    }
  }

  async getById(configId) {
    const result = await db.query(`
      SELECT *
      FROM broker_configs
      WHERE id = $1
    `, [configId]);

    if (result.rows.length === 0) {
      return null;
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  async getByUserAndBroker(userId, brokerName = 'zerodha') {
    const result = await db.query(`
      SELECT *
      FROM broker_configs
      WHERE user_id = $1 AND broker_name = $2
    `, [userId, brokerName]);

    if (result.rows.length === 0) {
      return null;
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  async getByUserId(userId) {
    const result = await db.query(`
      SELECT *
      FROM broker_configs
      WHERE user_id = $1
      ORDER BY created_at DESC
    `, [userId]);

    return result.rows.map(row => this.formatConfigResponse(row));
  }

  async getCredentials(configId) {
    const result = await db.query(`
      SELECT api_key, api_secret_encrypted
      FROM broker_configs
      WHERE id = $1
    `, [configId]);

    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    const { api_key, api_secret_encrypted } = result.rows[0];
    return {
      apiKey: api_key,
      apiSecret: this.security.decrypt(api_secret_encrypted)
    };
  }

  async updateConnectionStatus(configId, status) {
    const connectionStatus = {
      ...status,
      lastChecked: status.lastChecked || new Date().toISOString()
    };

    const isConnected = status.state === 'connected';

    const result = await db.query(`
      UPDATE broker_configs
      SET connection_status = $1,
          is_connected = $2,
          last_sync = $3,
          session_status = COALESCE($4, session_status),
          needs_reauth = COALESCE($5, needs_reauth),
          last_status_check = NOW(),
          updated_at = NOW()
      WHERE id = $6
      RETURNING *
    `, [
      JSON.stringify(connectionStatus),
      isConnected,
      isConnected ? new Date() : null,
      status.sessionStatus || (isConnected ? 'connected' : status.state || 'error'),
      status.needsReauth ?? false,
      configId
    ]);

    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  async updateSessionMetadata(configId, { sessionStatus, needsReauth, lastTokenRefresh, lastStatusCheck }) {
    const result = await db.query(`
      UPDATE broker_configs
      SET session_status = COALESCE($2, session_status),
          needs_reauth = COALESCE($3, needs_reauth),
          last_token_refresh = COALESCE($4, last_token_refresh),
          last_status_check = COALESCE($5, last_status_check),
          updated_at = NOW()
      WHERE id = $1
      RETURNING *
    `, [
      configId,
      sessionStatus,
      needsReauth,
      lastTokenRefresh ? new Date(lastTokenRefresh) : null,
      lastStatusCheck ? new Date(lastStatusCheck) : null
    ]);

    if (result.rows.length === 0) {
      throw new Error('Broker configuration not found');
    }

    return this.formatConfigResponse(result.rows[0]);
  }

  async updateOAuthState(configId, oauthState) {
    console.debug('[BrokerConfig] updateOAuthState', { configId, oauthState });
    try {
      // Best-effort persist in oauth_sessions for state verification
      if (configId && oauthState) {
        const expiresAt = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes
        await db.query(
          `INSERT INTO oauth_sessions (config_id, state, status, redirect_uri, expires_at)
           VALUES ($1, $2, 'pending', '', $3)`,
          [configId, oauthState, expiresAt]
        ).catch(() => {});
      }
      await db.query('UPDATE broker_configs SET updated_at = NOW() WHERE id = $1', [configId]);
      return true;
    } catch (err) {
      console.warn('[BrokerConfig] updateOAuthState failed:', err.message);
      return false;
    }
  }

  async verifyOAuthState(configId, providedState) {
    console.debug('[BrokerConfig] verifyOAuthState', { configId, providedState });
    try {
      if (!configId || !providedState) return false;
      const result = await db.query(
        `SELECT 1 FROM oauth_sessions WHERE config_id = $1 AND state = $2 AND expires_at > NOW() LIMIT 1`,
        [configId, providedState]
      );
      return result.rows.length > 0;
    } catch (err) {
      console.warn('[BrokerConfig] verifyOAuthState failed:', err.message);
      return false;
    }
  }

  async delete(configId) {
    await db.query('DELETE FROM broker_configs WHERE id = $1', [configId]);
  }

  async getActiveConnections() {
    const result = await db.query(`
      SELECT *
      FROM broker_configs
      WHERE is_connected = true AND (needs_reauth IS NULL OR needs_reauth = false)
    `);
    return result.rows.map(row => this.formatConfigResponse(row));
  }

  async healthCheck() {
    const [total, connected, needsReauth] = await Promise.all([
      db.query('SELECT COUNT(*)::int AS count FROM broker_configs'),
      db.query('SELECT COUNT(*)::int AS count FROM broker_configs WHERE is_connected = true'),
      db.query('SELECT COUNT(*)::int AS count FROM broker_configs WHERE needs_reauth = true')
    ]);

    return {
      configCount: total.rows[0].count,
      connectedCount: connected.rows[0].count,
      needsReauthCount: needsReauth.rows[0].count,
      timestamp: new Date().toISOString()
    };
  }

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
      sessionStatus: row.session_status,
      needsReauth: row.needs_reauth,
      lastSync: row.last_sync,
      lastTokenRefresh: row.last_token_refresh,
      lastStatusCheck: row.last_status_check,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
}

module.exports = BrokerConfig;
