const OAuthToken = require('../models/oauthToken');
const BrokerConfig = require('../models/brokerConfig');
const KiteClient = require('./kiteClient');
const SecurityManager = require('../../../core/security');

/**
 * Token Manager Service
 * Handles OAuth token lifecycle, automatic refresh, and validation
 * Following existing service patterns in the auth module
 */
class TokenManager {
  constructor() {
    this.oauthToken = new OAuthToken();
    this.brokerConfig = new BrokerConfig();
    this.kiteClient = new KiteClient();
    this.security = new SecurityManager();
    
    // Token refresh settings
    this.refreshThresholdMinutes = 60; // Refresh tokens 1 hour before expiry
    this.maxRetries = 3;
    this.retryDelayMs = 1000;
    
    // Start background token refresh job
    this.startTokenRefreshJob();
  }

  /**
   * Store OAuth tokens securely
   */
  async storeTokens(configId, tokenData) {
    try {
      const {
        accessToken,
        refreshToken,
        expiresIn,
        userId,
        tokenType = 'Bearer',
        scope
      } = tokenData;

      // Validate required fields
      if (!configId || !accessToken || !expiresIn) {
        throw new Error('Missing required token data: configId, accessToken, expiresIn');
      }

      // Store tokens using the model
      const storedToken = await this.oauthToken.store({
        configId,
        accessToken,
        refreshToken,
        expiresIn,
        tokenType,
        scope,
        userId
      });

      // Update broker config connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'connected',
        message: 'Tokens stored successfully',
        lastChecked: new Date().toISOString()
      });

      return {
        success: true,
        tokenId: storedToken.id,
        expiresAt: storedToken.expiresAt,
        message: 'Tokens stored successfully'
      };

    } catch (error) {
      throw new Error(`Failed to store tokens: ${error.message}`);
    }
  }

  /**
   * Get valid access token (with automatic refresh if needed)
   */
  async getValidAccessToken(configId) {
    try {
      // Check if token exists and is valid
      const isValid = await this.oauthToken.isValidToken(configId);
      
      if (isValid) {
        // Token is valid, return it
        return await this.oauthToken.getAccessToken(configId);
      }

      // Token is expired or doesn't exist, try to refresh
      const refreshResult = await this.refreshTokens(configId);
      
      if (refreshResult.success) {
        return await this.oauthToken.getAccessToken(configId);
      }

      throw new Error('No valid access token available and refresh failed');

    } catch (error) {
      // Update connection status to indicate token issues
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'error',
        message: `Token error: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      throw new Error(`Failed to get valid access token: ${error.message}`);
    }
  }

  /**
   * Refresh OAuth tokens
   */
  async refreshTokens(configId, retryCount = 0) {
    try {
      // Get broker config and credentials
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        throw new Error('Broker configuration not found');
      }

      const credentials = await this.brokerConfig.getCredentials(configId);
      
      // Get current refresh token
      const refreshToken = await this.oauthToken.getRefreshToken(configId);

      // Use Kite client to refresh tokens
      const refreshResult = await this.kiteClient.refreshAccessToken(
        refreshToken,
        credentials.apiKey,
        credentials.apiSecret
      );

      if (!refreshResult.success) {
        throw new Error('Token refresh failed');
      }

      // Update stored tokens
      await this.oauthToken.updateTokens(configId, {
        accessToken: refreshResult.accessToken,
        refreshToken: refreshResult.refreshToken,
        expiresIn: refreshResult.expiresIn
      });

      // Update connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'connected',
        message: 'Tokens refreshed successfully',
        lastChecked: new Date().toISOString()
      });

      return {
        success: true,
        message: 'Tokens refreshed successfully'
      };

    } catch (error) {
      console.error(`Token refresh failed for config ${configId}:`, error);

      // Retry logic
      if (retryCount < this.maxRetries) {
        console.log(`Retrying token refresh (${retryCount + 1}/${this.maxRetries})...`);
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, this.retryDelayMs * (retryCount + 1)));
        
        return this.refreshTokens(configId, retryCount + 1);
      }

      // All retries failed, update connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'error',
        message: `Token refresh failed: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      return {
        success: false,
        error: error.message,
        message: 'Token refresh failed after retries'
      };
    }
  }

  /**
   * Validate token and connection
   */
  async validateToken(configId) {
    try {
      // Get token status
      const tokenStatus = await this.oauthToken.getTokenStatus(configId);
      
      if (tokenStatus.status === 'no_token') {
        return {
          valid: false,
          status: 'no_token',
          message: 'No OAuth token found'
        };
      }

      if (tokenStatus.status === 'expired') {
        return {
          valid: false,
          status: 'expired',
          message: 'OAuth token has expired',
          expiresAt: tokenStatus.expiresAt
        };
      }

      // Token exists and is not expired, test connection
      try {
        const accessToken = await this.oauthToken.getAccessToken(configId);
        const credentials = await this.brokerConfig.getCredentials(configId);
        
        const connectionTest = await this.kiteClient.testConnection(accessToken, credentials.apiKey);
        
        if (connectionTest.success) {
          return {
            valid: true,
            status: tokenStatus.status,
            connected: true,
            userId: connectionTest.userId,
            expiresAt: tokenStatus.expiresAt,
            message: 'Token is valid and connection is active'
          };
        } else {
          return {
            valid: false,
            status: 'connection_failed',
            connected: false,
            error: connectionTest.error,
            message: 'Token exists but connection test failed'
          };
        }

      } catch (error) {
        return {
          valid: false,
          status: 'validation_error',
          error: error.message,
          message: 'Token validation failed'
        };
      }

    } catch (error) {
      throw new Error(`Token validation failed: ${error.message}`);
    }
  }

  /**
   * Revoke and cleanup tokens
   */
  async revokeTokens(configId) {
    try {
      // Get current tokens and credentials
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        throw new Error('Broker configuration not found');
      }

      try {
        // Try to invalidate token with Zerodha
        const accessToken = await this.oauthToken.getAccessToken(configId);
        const credentials = await this.brokerConfig.getCredentials(configId);
        
        await this.kiteClient.invalidateAccessToken(accessToken, credentials.apiKey);
      } catch (error) {
        // Continue with local cleanup even if remote revocation fails
        console.warn('Remote token revocation failed (continuing with local cleanup):', error.message);
      }

      // Delete local tokens
      const deletedCount = await this.oauthToken.deleteByConfigId(configId);

      // Update connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'disconnected',
        message: 'Tokens revoked successfully',
        lastChecked: new Date().toISOString()
      });

      return {
        success: true,
        deletedTokens: deletedCount,
        message: 'Tokens revoked and cleaned up successfully'
      };

    } catch (error) {
      throw new Error(`Token revocation failed: ${error.message}`);
    }
  }

  /**
   * Get token expiry information
   */
  async getTokenExpiry(configId) {
    try {
      const tokenStatus = await this.oauthToken.getTokenStatus(configId);
      
      if (tokenStatus.status === 'no_token') {
        return {
          hasToken: false,
          status: 'no_token'
        };
      }

      const expiresAt = new Date(tokenStatus.expiresAt);
      const now = new Date();
      const timeUntilExpiry = expiresAt - now;
      const hoursUntilExpiry = Math.floor(timeUntilExpiry / (1000 * 60 * 60));
      const minutesUntilExpiry = Math.floor((timeUntilExpiry % (1000 * 60 * 60)) / (1000 * 60));

      return {
        hasToken: true,
        status: tokenStatus.status,
        expiresAt: tokenStatus.expiresAt,
        timeUntilExpiry: timeUntilExpiry,
        hoursUntilExpiry: hoursUntilExpiry,
        minutesUntilExpiry: minutesUntilExpiry,
        needsRefresh: tokenStatus.status === 'expiring_soon'
      };

    } catch (error) {
      throw new Error(`Failed to get token expiry: ${error.message}`);
    }
  }

  /**
   * Background job to refresh expiring tokens
   */
  startTokenRefreshJob() {
    // Run every 30 minutes
    const intervalMs = 30 * 60 * 1000;
    
    setInterval(async () => {
      try {
        console.log('🔄 Running background token refresh job...');
        
        // Get tokens expiring soon
        const expiringSoon = await this.oauthToken.getExpiringSoon(this.refreshThresholdMinutes);
        
        if (expiringSoon.length === 0) {
          console.log('✅ No tokens need refreshing');
          return;
        }

        console.log(`🔄 Found ${expiringSoon.length} tokens that need refreshing`);

        // Refresh each token
        for (const tokenInfo of expiringSoon) {
          try {
            console.log(`🔄 Refreshing token for config ${tokenInfo.config_id}...`);
            
            const result = await this.refreshTokens(tokenInfo.config_id);
            
            if (result.success) {
              console.log(`✅ Successfully refreshed token for config ${tokenInfo.config_id}`);
            } else {
              console.error(`❌ Failed to refresh token for config ${tokenInfo.config_id}:`, result.error);
            }

          } catch (error) {
            console.error(`❌ Error refreshing token for config ${tokenInfo.config_id}:`, error);
          }
        }

        console.log('🔄 Background token refresh job completed');

      } catch (error) {
        console.error('❌ Background token refresh job failed:', error);
      }
    }, intervalMs);

    console.log(`🔄 Background token refresh job started (interval: ${intervalMs / 1000 / 60} minutes)`);
  }

  /**
   * Cleanup expired tokens
   */
  async cleanupExpiredTokens() {
    try {
      const deletedCount = await this.oauthToken.deleteExpiredTokens();
      
      console.log(`🧹 Cleaned up ${deletedCount} expired tokens`);
      
      return {
        success: true,
        deletedCount,
        message: `Cleaned up ${deletedCount} expired tokens`
      };

    } catch (error) {
      throw new Error(`Token cleanup failed: ${error.message}`);
    }
  }

  /**
   * Get token statistics
   */
  async getTokenStats() {
    try {
      const health = await this.oauthToken.healthCheck();
      
      return {
        success: true,
        stats: {
          totalTokens: health.totalTokens,
          expiredTokens: health.expiredTokens,
          expiringSoon: health.expiringSoon,
          healthyTokens: health.totalTokens - health.expiredTokens - health.expiringSoon
        },
        timestamp: health.timestamp
      };

    } catch (error) {
      throw new Error(`Failed to get token stats: ${error.message}`);
    }
  }

  /**
   * Health check for token manager
   */
  async healthCheck() {
    try {
      const tokenHealth = await this.oauthToken.healthCheck();
      const configHealth = await this.brokerConfig.healthCheck();
      const kiteHealth = await this.kiteClient.healthCheck();

      return {
        status: 'healthy',
        tokenManager: 'operational',
        components: {
          oauthTokens: tokenHealth,
          brokerConfigs: configHealth,
          kiteClient: kiteHealth
        },
        refreshJob: 'running',
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

module.exports = TokenManager;