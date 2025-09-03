const express = require('express');
const Joi = require('joi');
const BrokerService = require('../services/brokerService');
const SecurityManager = require('../../../core/security');

const router = express.Router();

// Initialize services and security
const brokerService = new BrokerService();
const security = new SecurityManager();

// Validation schemas
const setupOAuthSchema = Joi.object({
  api_key: Joi.string().required().min(10).max(100),
  api_secret: Joi.string().required().min(10).max(100),
  user_id: Joi.string().required(),
  frontend_url: Joi.string().uri().optional()
});

const callbackSchema = Joi.object({
  request_token: Joi.string().required(),
  state: Joi.string().required(),
  config_id: Joi.string().uuid().required()
});

const refreshTokenSchema = Joi.object({
  config_id: Joi.string().uuid().required()
});

const disconnectSchema = Joi.object({
  config_id: Joi.string().uuid().required()
});

// Get client IP helper
const getClientIP = (req) => {
  return req.headers['x-forwarded-for'] || 
         req.headers['x-real-ip'] || 
         req.connection.remoteAddress || 
         req.socket.remoteAddress || 
         '127.0.0.1';
};

// Log OAuth operation for audit
const logOAuthOperation = async (configId, userId, action, status, details = null, req = null) => {
  try {
    const db = require('../../../core/database/connection');
    await db.query(`
      INSERT INTO oauth_audit_log (config_id, user_id, action, status, details, ip_address, user_agent)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
    `, [
      configId,
      userId,
      action,
      status,
      details ? JSON.stringify(details) : null,
      req ? getClientIP(req) : null,
      req ? req.get('User-Agent') : null
    ]);
  } catch (error) {
    console.error('Failed to log OAuth operation:', error);
  }
};

/**
 * Setup OAuth credentials and initiate OAuth flow
 * POST /broker/setup-oauth
 */
router.post('/setup-oauth', async (req, res) => {
  try {
    const { error, value } = setupOAuthSchema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request data',
        details: error.details[0].message
      });
    }

    const { api_key, api_secret, user_id, frontend_url } = value;

    // Check if config already exists
    let config = await brokerConfig.getByUserAndBroker(user_id, 'zerodha');
    
    if (config) {
      // Update existing config
      const credentials = await brokerConfig.getCredentials(config.id);
      if (credentials.apiKey !== api_key || credentials.apiSecret !== api_secret) {
        // Credentials changed, need to recreate config
        await brokerConfig.delete(config.id);
        config = await brokerConfig.create({
          userId: user_id,
          brokerName: 'zerodha',
          apiKey: api_key,
          apiSecret: api_secret
        });
      }
    } else {
      // Create new config
      config = await brokerConfig.create({
        userId: user_id,
        brokerName: 'zerodha',
        apiKey: api_key,
        apiSecret: api_secret
      });
    }

    // Generate OAuth state for CSRF protection
    const oauthState = security.generateOAuthState();
    await brokerConfig.updateOAuthState(config.id, oauthState);

    // Generate OAuth URL
    const redirectUri = frontend_url ? 
      `${frontend_url}/broker-callback` : 
      `${process.env.ZERODHA_REDIRECT_URI || 'http://localhost:3000/broker-callback'}`;

    const oauthUrl = `https://kite.zerodha.com/connect/login?api_key=${api_key}&v=3&state=${oauthState}`;

    // Update connection status
    await brokerConfig.updateConnectionStatus(config.id, {
      state: 'connecting',
      message: 'OAuth flow initiated',
      lastChecked: new Date().toISOString()
    });

    // Log operation
    await logOAuthOperation(config.id, user_id, 'oauth_initiated', 'success', {
      redirectUri,
      apiKey: api_key
    }, req);

    res.json({
      success: true,
      data: {
        oauth_url: oauthUrl,
        state: oauthState,
        config_id: config.id,
        redirect_uri: redirectUri
      },
      message: 'OAuth flow initiated successfully'
    });

  } catch (error) {
    console.error('OAuth setup error:', error);
    
    // Log error
    if (req.body.user_id) {
      await logOAuthOperation(null, req.body.user_id, 'oauth_initiated', 'failed', {
        error: error.message
      }, req);
    }

    res.status(500).json({
      success: false,
      error: 'Failed to setup OAuth',
      message: error.message
    });
  }
});

/**
 * Handle OAuth callback from Zerodha
 * POST /broker/callback
 */
router.post('/callback', async (req, res) => {
  try {
    const { error, value } = callbackSchema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: 'Invalid callback data',
        details: error.details[0].message
      });
    }

    const { request_token, state, config_id } = value;

    // Verify OAuth state to prevent CSRF
    const isValidState = await brokerConfig.verifyOAuthState(config_id, state);
    if (!isValidState) {
      await logOAuthOperation(config_id, null, 'oauth_callback', 'failed', {
        error: 'Invalid OAuth state'
      }, req);
      
      return res.status(400).json({
        success: false,
        error: 'Invalid OAuth state'
      });
    }

    // Get config and credentials
    const config = await brokerConfig.getById(config_id);
    if (!config) {
      return res.status(404).json({
        success: false,
        error: 'Broker configuration not found'
      });
    }

    const credentials = await brokerConfig.getCredentials(config_id);

    // Exchange request token for access token
    const KiteConnect = require('kiteconnect').KiteConnect;
    const kc = new KiteConnect({
      api_key: credentials.apiKey
    });

    const sessionData = await kc.generateSession(request_token, credentials.apiSecret);

    // Store tokens securely
    await oauthToken.store({
      configId: config_id,
      accessToken: sessionData.access_token,
      refreshToken: sessionData.refresh_token,
      expiresIn: 86400, // 24 hours for Zerodha
      tokenType: 'Bearer',
      userId: sessionData.user_id
    });

    // Update connection status
    await brokerConfig.updateConnectionStatus(config_id, {
      state: 'connected',
      message: 'Successfully connected to Zerodha',
      lastChecked: new Date().toISOString()
    });

    // Clear OAuth state
    await brokerConfig.updateOAuthState(config_id, null);

    // Log success
    await logOAuthOperation(config_id, config.userId, 'token_exchanged', 'success', {
      brokerUserId: sessionData.user_id,
      userType: sessionData.user_type
    }, req);

    res.json({
      success: true,
      data: {
        user_id: sessionData.user_id,
        user_type: sessionData.user_type,
        user_shortname: sessionData.user_shortname,
        broker_user_id: sessionData.user_id
      },
      message: 'OAuth authentication completed successfully'
    });

  } catch (error) {
    console.error('OAuth callback error:', error);

    // Update connection status to error
    if (req.body.config_id) {
      await brokerConfig.updateConnectionStatus(req.body.config_id, {
        state: 'error',
        message: `OAuth failed: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      await logOAuthOperation(req.body.config_id, null, 'token_exchanged', 'failed', {
        error: error.message
      }, req);
    }

    res.status(500).json({
      success: false,
      error: 'OAuth authentication failed',
      message: error.message
    });
  }
});

/**
 * Refresh OAuth tokens
 * POST /broker/refresh-token
 */
router.post('/refresh-token', async (req, res) => {
  try {
    const { error, value } = refreshTokenSchema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request data'
      });
    }

    const { config_id } = value;

    // Get config and tokens
    const config = await brokerConfig.getById(config_id);
    if (!config) {
      return res.status(404).json({
        success: false,
        error: 'Broker configuration not found'
      });
    }

    const credentials = await brokerConfig.getCredentials(config_id);
    const refreshToken = await oauthToken.getRefreshToken(config_id);

    // Refresh tokens using Kite Connect
    const KiteConnect = require('kiteconnect').KiteConnect;
    const kc = new KiteConnect({
      api_key: credentials.apiKey
    });

    const newTokenData = await kc.renewAccessToken(refreshToken, credentials.apiSecret);

    // Update stored tokens
    await oauthToken.updateTokens(config_id, {
      accessToken: newTokenData.access_token,
      refreshToken: newTokenData.refresh_token,
      expiresIn: 86400 // 24 hours
    });

    // Update connection status
    await brokerConfig.updateConnectionStatus(config_id, {
      state: 'connected',
      message: 'Tokens refreshed successfully',
      lastChecked: new Date().toISOString()
    });

    // Log operation
    await logOAuthOperation(config_id, config.userId, 'token_refreshed', 'success', null, req);

    res.json({
      success: true,
      message: 'Tokens refreshed successfully'
    });

  } catch (error) {
    console.error('Token refresh error:', error);

    // Update connection status to error
    if (req.body.config_id) {
      await brokerConfig.updateConnectionStatus(req.body.config_id, {
        state: 'error',
        message: `Token refresh failed: ${error.message}`,
        lastChecked: new Date().toISOString()
      });

      await logOAuthOperation(req.body.config_id, null, 'token_refreshed', 'failed', {
        error: error.message
      }, req);
    }

    res.status(500).json({
      success: false,
      error: 'Token refresh failed',
      message: error.message
    });
  }
});

/**
 * Disconnect broker and revoke tokens
 * POST /broker/disconnect
 */
router.post('/disconnect', async (req, res) => {
  try {
    const { error, value } = disconnectSchema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request data'
      });
    }

    const { config_id } = value;

    // Get config
    const config = await brokerConfig.getById(config_id);
    if (!config) {
      return res.status(404).json({
        success: false,
        error: 'Broker configuration not found'
      });
    }

    try {
      // Try to revoke tokens with Zerodha (if possible)
      const accessToken = await oauthToken.getAccessToken(config_id);
      const credentials = await brokerConfig.getCredentials(config_id);
      
      const KiteConnect = require('kiteconnect').KiteConnect;
      const kc = new KiteConnect({
        api_key: credentials.apiKey,
        access_token: accessToken
      });

      // Zerodha doesn't have explicit token revocation, but we can try to invalidate
      await kc.invalidateAccessToken();
    } catch (error) {
      // Continue even if revocation fails
      console.warn('Token revocation failed (continuing with local cleanup):', error.message);
    }

    // Delete stored tokens
    await oauthToken.deleteByConfigId(config_id);

    // Update connection status
    await brokerConfig.updateConnectionStatus(config_id, {
      state: 'disconnected',
      message: 'Disconnected successfully',
      lastChecked: new Date().toISOString()
    });

    // Log operation
    await logOAuthOperation(config_id, config.userId, 'disconnected', 'success', null, req);

    res.json({
      success: true,
      message: 'Disconnected successfully'
    });

  } catch (error) {
    console.error('Disconnect error:', error);

    // Log error
    if (req.body.config_id) {
      await logOAuthOperation(req.body.config_id, null, 'disconnected', 'failed', {
        error: error.message
      }, req);
    }

    res.status(500).json({
      success: false,
      error: 'Disconnect failed',
      message: error.message
    });
  }
});

/**
 * Get connection status
 * GET /broker/status
 */
router.get('/status', async (req, res) => {
  try {
    const { config_id, user_id } = req.query;

    if (!config_id && !user_id) {
      return res.status(400).json({
        success: false,
        error: 'Either config_id or user_id is required'
      });
    }

    let config;
    if (config_id) {
      config = await brokerConfig.getById(config_id);
    } else {
      config = await brokerConfig.getByUserAndBroker(user_id, 'zerodha');
    }

    if (!config) {
      return res.json({
        success: true,
        data: {
          isConnected: false,
          connectionStatus: {
            state: 'disconnected',
            message: 'No broker configuration found',
            lastChecked: new Date().toISOString()
          }
        }
      });
    }

    // Check token status
    const tokenStatus = await oauthToken.getTokenStatus(config.id);

    res.json({
      success: true,
      data: {
        configId: config.id,
        isConnected: config.isConnected,
        connectionStatus: config.connectionStatus,
        tokenStatus: tokenStatus,
        lastSync: config.lastSync,
        brokerName: config.brokerName
      }
    });

  } catch (error) {
    console.error('Status check error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to check status'
    });
  }
});

/**
 * Get broker configurations for user
 * GET /broker/configs
 */
router.get('/configs', async (req, res) => {
  try {
    const { user_id } = req.query;

    if (!user_id) {
      return res.status(400).json({
        success: false,
        error: 'user_id is required'
      });
    }

    const result = await brokerService.getAllConfigsByUser(user_id);

    res.json({
      success: true,
      data: result.configs,
      count: result.count
    });

  } catch (error) {
    console.error('Get configs error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get broker configurations'
    });
  }
});

/**
 * Create or update broker configuration
 * POST /broker/configs
 */
router.post('/configs', async (req, res) => {
  try {
    const { user_id, api_key, api_secret, broker_name } = req.body;

    if (!user_id || !api_key || !api_secret) {
      return res.status(400).json({
        success: false,
        error: 'user_id, api_key, and api_secret are required'
      });
    }

    const result = await brokerService.createOrUpdateConfig(user_id, {
      brokerName: broker_name || 'zerodha',
      apiKey: api_key,
      apiSecret: api_secret
    });

    res.json({
      success: true,
      data: result.config,
      message: result.message
    });

  } catch (error) {
    console.error('Create config error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Delete broker configuration
 * DELETE /broker/configs/:configId
 */
router.delete('/configs/:configId', async (req, res) => {
  try {
    const { configId } = req.params;
    const { user_id } = req.query;

    if (!user_id) {
      return res.status(400).json({
        success: false,
        error: 'user_id is required'
      });
    }

    const result = await brokerService.deleteConfig(configId, user_id);

    res.json({
      success: true,
      message: result.message
    });

  } catch (error) {
    console.error('Delete config error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Reconnect broker
 * POST /broker/reconnect
 */
router.post('/reconnect', async (req, res) => {
  try {
    const { config_id } = req.body;

    if (!config_id) {
      return res.status(400).json({
        success: false,
        error: 'config_id is required'
      });
    }

    const result = await brokerService.reconnectBroker(config_id);

    if (result.success) {
      res.json({
        success: true,
        message: result.message,
        connectionStatus: result.connectionStatus
      });
    } else {
      res.status(400).json({
        success: false,
        error: result.error,
        message: result.message
      });
    }

  } catch (error) {
    console.error('Reconnect error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Get active connections
 * GET /broker/active
 */
router.get('/active', async (req, res) => {
  try {
    const result = await brokerService.getActiveConnections();

    res.json({
      success: true,
      data: result.connections,
      count: result.count,
      timestamp: result.timestamp
    });

  } catch (error) {
    console.error('Get active connections error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get active connections'
    });
  }
});

/**
 * Get service statistics
 * GET /broker/stats
 */
router.get('/stats', async (req, res) => {
  try {
    const result = await brokerService.getServiceStats();

    res.json({
      success: true,
      data: result.stats,
      timestamp: result.timestamp
    });

  } catch (error) {
    console.error('Get stats error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get service statistics'
    });
  }
});

/**
 * Health check for OAuth endpoints
 * GET /broker/health
 */
router.get('/health', async (req, res) => {
  try {
    const health = await brokerService.healthCheck();

    res.json({
      success: true,
      data: health
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'OAuth health check failed',
      timestamp: new Date().toISOString()
    });
  }
});

module.exports = router;