const OAuthToken = require('../models/oauthToken');
const BrokerConfig = require('../models/brokerConfig');
const KiteClient = require('./kiteClient');
const SecurityManager = require('../../../core/security');

/**
 * Token Manager Service
 * Centralises lifecycle management of Zerodha OAuth tokens.
 */
class TokenManager {
  constructor() {
    this.oauthToken = new OAuthToken();
    this.brokerConfig = new BrokerConfig();
    this.kiteClient = new KiteClient();
    this.security = new SecurityManager();

    this.refreshThresholdMinutes = parseInt(
      process.env.BROKER_REFRESH_THRESHOLD_MINUTES || '15',
      10
    );
    this.maxRetries = 3;
    this.retryDelayMs = 1000;

    this.startTokenRefreshJob();
  }

  async storeTokens(configId, tokenData) {
    try {
      const storedToken = await this.oauthToken.store({
        ...tokenData,
        configId
      });

      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'connected',
        message: 'Broker session established',
        lastChecked: new Date().toISOString(),
        needsReauth: false,
        sessionStatus: 'connected'
      });

      await this.brokerConfig.updateSessionMetadata(configId, {
        needsReauth: false,
        lastTokenRefresh: new Date().toISOString(),
        sessionStatus: 'connected'
      });

      return {
        success: true,
        tokenId: storedToken.id,
        expiresAt: storedToken.expiresAt
      };
    } catch (error) {
      throw new Error(`Failed to store tokens: ${error.message}`);
    }
  }

  async getValidAccessToken(configId) {
    const status = await this.oauthToken.getTokenStatus(
      configId,
      this.refreshThresholdMinutes
    );

    if (status.status === 'no_token' || status.status === 'needs_reauth') {
      await this.handleNeedsReauth(configId, status.status);
      throw new Error('No valid access token available');
    }

    if (status.status === 'expired') {
      const refreshed = await this.refreshTokens(configId);
      if (!refreshed.success) {
        await this.handleNeedsReauth(configId, 'token_expired');
        throw new Error(refreshed.error || 'Token refresh failed');
      }
      return this.oauthToken.getAccessToken(configId);
    }

    if (status.status === 'expiring_soon') {
      const refreshed = await this.refreshTokens(configId);
      if (refreshed.success) {
        return this.oauthToken.getAccessToken(configId);
      }
      console.warn('[TokenManager] Refresh failed while token expiring soon, using current token');
    }

    return this.oauthToken.getAccessToken(configId);
  }

  async refreshTokens(configId, retryCount = 0) {
    try {
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        throw new Error('Broker configuration not found');
      }

      const credentials = await this.brokerConfig.getCredentials(configId);
      const refreshToken = await this.oauthToken.getRefreshToken(configId);

      const refreshResult = await this.kiteClient.refreshAccessToken(
        refreshToken,
        credentials.apiKey,
        credentials.apiSecret
      );

      if (!refreshResult.success || !refreshResult.accessToken) {
        throw new Error(refreshResult.message || 'Token refresh failed');
      }

      await this.oauthToken.updateTokens(configId, {
        accessToken: refreshResult.accessToken,
        refreshToken: refreshResult.refreshToken,
        expiresIn: refreshResult.expiresIn,
        source: 'auto_refresh'
      });

      await this.brokerConfig.updateSessionMetadata(configId, {
        lastTokenRefresh: new Date().toISOString(),
        needsReauth: false,
        sessionStatus: 'connected'
      });

      return {
        success: true,
        message: 'Tokens refreshed successfully'
      };
    } catch (error) {
      if (retryCount < this.maxRetries) {
        await new Promise(resolve => setTimeout(resolve, this.retryDelayMs * (retryCount + 1)));
        return this.refreshTokens(configId, retryCount + 1);
      }

      await this.handleNeedsReauth(configId, 'refresh_failed', error.message);

      return {
        success: false,
        error: error.message,
        message: 'Token refresh failed after retries'
      };
    }
  }

  async validateToken(configId) {
    const status = await this.oauthToken.getTokenStatus(
      configId,
      this.refreshThresholdMinutes
    );

    return {
      valid: status.status === 'valid',
      status: status.status,
      message: status.status === 'valid' ? 'Token valid' : 'Token requires attention'
    };
  }

  async getTokenExpiry(configId) {
    const status = await this.oauthToken.getTokenStatus(configId, this.refreshThresholdMinutes);
    return status.expiresAt || null;
  }

  async revokeTokens(configId, { userId = null, reason = 'manual_revoke' } = {}) {
    if (configId) {
      await this.oauthToken.deleteByConfigId(configId);
    }
    if (userId) {
      await this.oauthToken.deleteByUserId(userId);
    }

    if (configId) {
      await this.brokerConfig.updateSessionMetadata(configId, {
        sessionStatus: 'disconnected',
        needsReauth: true,
        lastTokenRefresh: null,
        lastStatusCheck: new Date().toISOString()
      });

      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'disconnected',
        message: 'Broker tokens revoked',
        lastChecked: new Date().toISOString(),
        needsReauth: true,
        sessionStatus: 'disconnected'
      });
    }

    return { success: true, reason };
  }

  async handleNeedsReauth(configId, reason = 'token_expired', errorMessage = '') {
    await this.oauthToken.markNeedsReauth(configId, reason);
    await this.brokerConfig.updateSessionMetadata(configId, {
      needsReauth: true,
      sessionStatus: 'needs_reauth',
      lastStatusCheck: new Date().toISOString()
    });

    await this.brokerConfig.updateConnectionStatus(configId, {
      state: 'error',
      message: errorMessage || 'Broker session requires reauthentication',
      lastChecked: new Date().toISOString(),
      needsReauth: true,
      sessionStatus: 'needs_reauth'
    });
  }

  startTokenRefreshJob() {
    if (this.refreshJobInterval) {
      clearInterval(this.refreshJobInterval);
    }

    const intervalMinutes = parseInt(process.env.BROKER_REFRESH_JOB_INTERVAL_MINUTES || '10', 10);
    const intervalMs = Math.max(1, intervalMinutes) * 60 * 1000;

    this.refreshJobInterval = setInterval(async () => {
      try {
        const expiringTokens = await this.oauthToken.getExpiringSoon(this.refreshThresholdMinutes);
        for (const token of expiringTokens) {
          await this.refreshTokens(token.config_id);
        }
      } catch (error) {
        console.error('[TokenManager] Background refresh job failed:', error.message);
      }
    }, intervalMs);

    this.refreshJobInterval.unref?.();
  }

  async healthCheck() {
    return this.oauthToken.healthCheck();
  }

  async flagReauthRequired(configId, reason = 'manual', message = '') {
    await this.handleNeedsReauth(configId, reason, message);
  }

  async getTokenStats() {
    return this.oauthToken.healthCheck();
  }
}

module.exports = TokenManager;
