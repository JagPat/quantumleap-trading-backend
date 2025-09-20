const BrokerConfig = require('../models/brokerConfig');
const OAuthToken = require('../models/oauthToken');
const TokenManager = require('./tokenManager');
const KiteClient = require('./kiteClient');
const SecurityManager = require('../../../core/security');

/**
 * Broker Service
 * Manages broker configurations, connection status, and real-time updates
 * Following existing service patterns in the auth module
 */
class BrokerService {
  constructor() {
    this.brokerConfig = new BrokerConfig();
    this.oauthToken = new OAuthToken();
    this.tokenManager = new TokenManager();
    this.kiteClient = new KiteClient();
    this.security = new SecurityManager();
    
    // Connection monitoring settings
    this.monitoringInterval = 5 * 60 * 1000; // 5 minutes
    this.connectionTimeout = 10000; // 10 seconds
    
    // Start connection monitoring
    this.startConnectionMonitoring();
  }

  /**
   * Create or update broker configuration
   */
  async createOrUpdateConfig(userId, configData) {
    try {
      const {
        brokerName = 'zerodha',
        apiKey,
        apiSecret
      } = configData;

      // Validate credentials format
      const validation = this.kiteClient.validateCredentials(apiKey, apiSecret);
      if (!validation.valid) {
        throw new Error(validation.error);
      }

      // Check if config already exists
      let config = await this.brokerConfig.getByUserAndBroker(userId, brokerName);
      
      if (config) {
        // Check if credentials changed
        const existingCredentials = await this.brokerConfig.getCredentials(config.id);
        
        if (existingCredentials.apiKey !== apiKey || existingCredentials.apiSecret !== apiSecret) {
          // Credentials changed, revoke existing tokens and update config
          await this.tokenManager.revokeTokens(config.id);
          
          // Delete and recreate config with new credentials
          await this.brokerConfig.delete(config.id);
          config = await this.brokerConfig.create({
            userId,
            brokerName,
            apiKey,
            apiSecret
          });
        }
      } else {
        // Create new config
        config = await this.brokerConfig.create({
          userId,
          brokerName,
          apiKey,
          apiSecret
        });
      }

      return {
        success: true,
        config: config,
        message: config ? 'Broker configuration updated' : 'Broker configuration created'
      };

    } catch (error) {
      throw new Error(`Failed to create/update broker configuration: ${error.message}`);
    }
  }

  /**
   * Generate broker session using request token
   */
  async generateBrokerSession({ requestToken, apiKey, apiSecret, userId, originalUserId = null, configId = null }) {
    if (!requestToken || !apiKey || !apiSecret) {
      throw new Error('Request token, API key, and API secret are required');
    }

    let targetConfig = null;

    if (configId) {
      targetConfig = await this.brokerConfig.getById(configId);
      if (!targetConfig) {
        throw new Error('Broker configuration not found');
      }

      await this.createOrUpdateConfig(targetConfig.userId, {
        brokerName: targetConfig.brokerName || 'zerodha',
        apiKey,
        apiSecret
      });

      targetConfig = await this.brokerConfig.getById(configId);
    } else {
      if (!userId) {
        throw new Error('User identifier is required to create broker configuration');
      }

      const upsertResult = await this.createOrUpdateConfig(userId, {
        brokerName: 'zerodha',
        apiKey,
        apiSecret
      });

      targetConfig = upsertResult.config || await this.brokerConfig.getByUserAndBroker(userId, 'zerodha');
    }

    if (!targetConfig) {
      throw new Error('Failed to prepare broker configuration');
    }

    const sessionResponse = await this.kiteClient.generateSession(requestToken, apiKey, apiSecret);

    if (!sessionResponse.success) {
      throw new Error(sessionResponse.message || 'Failed to generate broker session');
    }

    await this.tokenManager.storeTokens(targetConfig.id, {
      accessToken: sessionResponse.accessToken,
      refreshToken: sessionResponse.refreshToken,
      expiresIn: sessionResponse.expiresIn,
      userId: sessionResponse.userId
    });

    await this.brokerConfig.updateConnectionStatus(targetConfig.id, {
      state: 'connected',
      message: 'Broker session established',
      lastChecked: new Date().toISOString()
    });

    const userData = {
      user_id: sessionResponse.userId,
      user_type: sessionResponse.userType,
      user_shortname: sessionResponse.userShortname,
      avatar_url: sessionResponse.avatarUrl,
      broker: sessionResponse.broker,
      exchanges: sessionResponse.exchanges,
      products: sessionResponse.products,
      order_types: sessionResponse.orderTypes
    };

    return {
      status: 'success',
      config_id: targetConfig.id,
      user_id: targetConfig.userId,
      original_user_id: originalUserId,
      access_token: sessionResponse.accessToken,
      refresh_token: sessionResponse.refreshToken,
      user_data: userData
    };
  }

  /**
   * Update access token provided by automation (e.g., Selenium + TOTP jobs)
   */
  async updateAccessTokenFromAutomation({ normalizedUserId = null, originalUserId = null, accessToken, expiresIn = null, expiresAt = null, source = 'automation' }) {
    if (!accessToken) {
      throw new Error('Access token is required');
    }

    const candidateUserIds = [normalizedUserId, originalUserId].filter(Boolean);
    if (candidateUserIds.length === 0) {
      throw new Error('User identifier is required');
    }

    let config = null;
    for (const candidate of candidateUserIds) {
      config = await this.brokerConfig.getByUserAndBroker(candidate, 'zerodha');
      if (config) {
        break;
      }
    }

    if (!config) {
      throw new Error('Broker configuration not found for provided user');
    }

    let computedExpiresIn = Number(expiresIn);

    if ((!computedExpiresIn || !Number.isFinite(computedExpiresIn) || computedExpiresIn <= 0) && expiresAt) {
      const expiryDate = new Date(expiresAt);
      if (!Number.isNaN(expiryDate.getTime())) {
        computedExpiresIn = Math.floor((expiryDate.getTime() - Date.now()) / 1000);
      }
    }

    if (!computedExpiresIn || !Number.isFinite(computedExpiresIn) || computedExpiresIn <= 0) {
      computedExpiresIn = 24 * 60 * 60; // default to 24 hours
    }

    // Ensure we always have at least 15 minutes to account for buffer subtraction
    computedExpiresIn = Math.max(computedExpiresIn, 900);

    await this.tokenManager.storeTokens(config.id, {
      accessToken,
      refreshToken: null,
      expiresIn: computedExpiresIn,
      userId: config.userId,
      scope: { source: source || 'automation' }
    });

    const expiresAt = new Date(Date.now() + computedExpiresIn * 1000);
    console.info('[Auth][Broker] Access token updated', {
      configId: config.id,
      userId: config.userId,
      source: source || 'automation',
      expiresAt: expiresAt.toISOString(),
      expiresIn: computedExpiresIn
    });

    await this.brokerConfig.updateConnectionStatus(config.id, {
      state: 'connected',
      message: `Access token updated via ${source || 'automation'}`,
      lastChecked: new Date().toISOString()
    });

    return {
      config_id: config.id,
      user_id: config.userId,
      expires_in: computedExpiresIn,
      expires_at: expiresAt.toISOString()
    };
  }

  /**
   * Retrieve token metadata for administrative inspection
   */
  async getTokenMetadata({ normalizedUserId = null, originalUserId = null, configId = null }) {
    let config = null;

    if (configId) {
      config = await this.brokerConfig.getById(configId);
    }

    if (!config) {
      const candidateIds = [normalizedUserId, originalUserId].filter(Boolean);
      for (const candidate of candidateIds) {
        config = await this.brokerConfig.getByUserAndBroker(candidate, 'zerodha');
        if (config) {
          break;
        }
      }
    }

    if (!config) {
      throw new Error('Broker configuration not found for supplied identifiers');
    }

    const tokenRecord = await this.oauthToken.getByConfigId(config.id);
    const tokenStatus = await this.oauthToken.getTokenStatus(config.id);

    return {
      config_id: config.id,
      user_id: config.userId,
      token_present: !!tokenRecord,
      expires_at: tokenRecord?.expiresAt || null,
      updated_at: tokenRecord?.updatedAt || null,
      source: tokenRecord?.scope?.source || null,
      status: tokenStatus?.status || 'unknown'
    };
  }

  /**
   * Get broker configuration by user ID
   */
  async getConfigByUser(userId, brokerName = 'zerodha') {
    try {
      const config = await this.brokerConfig.getByUserAndBroker(userId, brokerName);
      
      if (!config) {
        return {
          success: true,
          config: null,
          message: 'No broker configuration found'
        };
      }

      // Get token status
      const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
      
      // Get connection validation
      const connectionStatus = await this.validateConnection(config.id);

      return {
        success: true,
        config: {
          ...config,
          tokenStatus,
          connectionValidation: connectionStatus
        }
      };

    } catch (error) {
      throw new Error(`Failed to get broker configuration: ${error.message}`);
    }
  }

  /**
   * Get all configurations for a user
   */
  async getAllConfigsByUser(userId) {
    try {
      const configs = await this.brokerConfig.getByUserId(userId);
      
      // Enhance each config with token and connection status
      const enhancedConfigs = await Promise.all(
        configs.map(async (config) => {
          try {
            const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
            const connectionStatus = await this.validateConnection(config.id);
            
            return {
              ...config,
              tokenStatus,
              connectionValidation: connectionStatus
            };
          } catch (error) {
            return {
              ...config,
              tokenStatus: { status: 'error', error: error.message },
              connectionValidation: { valid: false, error: error.message }
            };
          }
        })
      );

      return {
        success: true,
        configs: enhancedConfigs,
        count: enhancedConfigs.length
      };

    } catch (error) {
      throw new Error(`Failed to get broker configurations: ${error.message}`);
    }
  }

  /**
   * Validate broker connection
   */
  async validateConnection(configId) {
    try {
      // Check if we have valid tokens
      const tokenValidation = await this.tokenManager.validateToken(configId);
      
      if (!tokenValidation.valid) {
        return {
          valid: false,
          status: tokenValidation.status,
          message: tokenValidation.message,
          canReconnect: tokenValidation.status === 'expired' || tokenValidation.status === 'expiring_soon'
        };
      }

      // Test actual API connection
      const accessToken = await this.tokenManager.getValidAccessToken(configId);
      const credentials = await this.brokerConfig.getCredentials(configId);
      
      const connectionTest = await this.kiteClient.testConnection(accessToken, credentials.apiKey);
      
      if (connectionTest.success) {
        // Update connection status
        await this.brokerConfig.updateConnectionStatus(configId, {
          state: 'connected',
          message: 'Connection validated successfully',
          lastChecked: new Date().toISOString()
        });

        return {
          valid: true,
          status: 'connected',
          userId: connectionTest.userId,
          message: 'Connection is active and healthy',
          lastChecked: new Date().toISOString()
        };
      } else {
        // Update connection status
        await this.brokerConfig.updateConnectionStatus(configId, {
          state: 'error',
          message: `Connection test failed: ${connectionTest.error}`,
          lastChecked: new Date().toISOString()
        });

        return {
          valid: false,
          status: 'connection_failed',
          error: connectionTest.error,
          message: 'Connection test failed',
          canReconnect: true
        };
      }

    } catch (error) {
      // Update connection status
      await this.brokerConfig.updateConnectionStatus(configId, {
        state: 'error',
        message: `Validation error: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      return {
        valid: false,
        status: 'validation_error',
        error: error.message,
        message: 'Connection validation failed',
        canReconnect: true
      };
    }
  }

  /**
   * Reconnect broker (refresh tokens and validate)
   */
  async reconnectBroker(configId) {
    try {
      // Try to refresh tokens
      const refreshResult = await this.tokenManager.refreshTokens(configId);
      
      if (!refreshResult.success) {
        return {
          success: false,
          error: refreshResult.error,
          message: 'Token refresh failed - manual re-authentication required'
        };
      }

      // Validate the new connection
      const connectionStatus = await this.validateConnection(configId);
      
      if (connectionStatus.valid) {
        return {
          success: true,
          message: 'Broker reconnected successfully',
          connectionStatus
        };
      } else {
        return {
          success: false,
          error: connectionStatus.error,
          message: 'Reconnection failed - manual re-authentication may be required'
        };
      }

    } catch (error) {
      throw new Error(`Reconnection failed: ${error.message}`);
    }
  }

  /**
   * Disconnect broker
   */
  async disconnectBroker(configId) {
    try {
      const result = await this.tokenManager.revokeTokens(configId);
      
      return {
        success: true,
        message: 'Broker disconnected successfully',
        deletedTokens: result.deletedTokens
      };

    } catch (error) {
      throw new Error(`Disconnect failed: ${error.message}`);
    }
  }

  /**
   * Delete broker configuration
   */
  async deleteConfig(configId, userId) {
    try {
      // Verify ownership
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        throw new Error('Broker configuration not found');
      }

      if (config.userId !== userId) {
        throw new Error('Unauthorized: Configuration belongs to different user');
      }

      // Disconnect first (this will revoke tokens)
      await this.disconnectBroker(configId);

      // Delete configuration
      const deleted = await this.brokerConfig.delete(configId);
      
      if (!deleted) {
        throw new Error('Failed to delete broker configuration');
      }

      return {
        success: true,
        message: 'Broker configuration deleted successfully'
      };

    } catch (error) {
      throw new Error(`Failed to delete configuration: ${error.message}`);
    }
  }

  /**
   * Get real-time connection status
   */
  async getConnectionStatus(configId) {
    try {
      const config = await this.brokerConfig.getById(configId);
      if (!config) {
        return {
          success: false,
          error: 'Configuration not found'
        };
      }

      const tokenStatus = await this.oauthToken.getTokenStatus(config.id);
      const tokenExpiry = await this.tokenManager.getTokenExpiry(config.id);

      return {
        success: true,
        status: {
          configId: config.id,
          isConnected: config.isConnected,
          connectionStatus: config.connectionStatus,
          tokenStatus: tokenStatus,
          tokenExpiry: tokenExpiry,
          lastSync: config.lastSync,
          brokerName: config.brokerName
        }
      };

    } catch (error) {
      throw new Error(`Failed to get connection status: ${error.message}`);
    }
  }

  /**
   * Get active connections overview
   */
  async getActiveConnections() {
    try {
      const activeConnections = await this.brokerConfig.getActiveConnections();
      
      return {
        success: true,
        connections: activeConnections,
        count: activeConnections.length,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      throw new Error(`Failed to get active connections: ${error.message}`);
    }
  }

  /**
   * Background connection monitoring
   */
  startConnectionMonitoring() {
    setInterval(async () => {
      try {
        console.log('🔍 Running connection health check...');
        
        const activeConnections = await this.brokerConfig.getActiveConnections();
        
        if (activeConnections.length === 0) {
          console.log('✅ No active connections to monitor');
          return;
        }

        console.log(`🔍 Monitoring ${activeConnections.length} active connections`);

        for (const connection of activeConnections) {
          try {
            const validation = await this.validateConnection(connection.id);
            
            if (validation.valid) {
              console.log(`✅ Connection ${connection.id} is healthy`);
            } else {
              console.warn(`⚠️ Connection ${connection.id} has issues: ${validation.message}`);
              
              // Try to reconnect if possible
              if (validation.canReconnect) {
                console.log(`🔄 Attempting to reconnect ${connection.id}...`);
                const reconnectResult = await this.reconnectBroker(connection.id);
                
                if (reconnectResult.success) {
                  console.log(`✅ Successfully reconnected ${connection.id}`);
                } else {
                  console.error(`❌ Failed to reconnect ${connection.id}: ${reconnectResult.error}`);
                }
              }
            }

          } catch (error) {
            console.error(`❌ Error monitoring connection ${connection.id}:`, error);
          }
        }

        console.log('🔍 Connection health check completed');

      } catch (error) {
        console.error('❌ Connection monitoring job failed:', error);
      }
    }, this.monitoringInterval);

    console.log(`🔍 Connection monitoring started (interval: ${this.monitoringInterval / 1000 / 60} minutes)`);
  }

  /**
   * Get broker service statistics
   */
  async getServiceStats() {
    try {
      const configHealth = await this.brokerConfig.healthCheck();
      const tokenStats = await this.tokenManager.getTokenStats();
      const activeConnections = await this.getActiveConnections();

      return {
        success: true,
        stats: {
          totalConfigs: configHealth.configCount,
          activeConnections: activeConnections.count,
          tokenStats: tokenStats.stats,
          healthStatus: 'operational'
        },
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      throw new Error(`Failed to get service stats: ${error.message}`);
    }
  }

  /**
   * Health check for broker service
   */
  async healthCheck() {
    try {
      const configHealth = await this.brokerConfig.healthCheck();
      const tokenHealth = await this.tokenManager.healthCheck();
      const kiteHealth = await this.kiteClient.healthCheck();

      return {
        status: 'healthy',
        brokerService: 'operational',
        components: {
          brokerConfigs: configHealth,
          tokenManager: tokenHealth,
          kiteClient: kiteHealth
        },
        monitoring: 'active',
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

module.exports = BrokerService;
