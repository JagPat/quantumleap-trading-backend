const express = require('express');
const Joi = require('joi');
const crypto = require('crypto');

const router = express.Router();

// In-memory storage for Phase-1 testing (no database)
const inMemoryStorage = {
  configs: new Map(),
  tokens: new Map(),
  states: new Map()
};

// Apply basic security headers
router.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

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
  config_id: Joi.string().required()
});

// Helper functions
const generateId = () => crypto.randomUUID();
const generateState = () => crypto.randomBytes(32).toString('hex');

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

    // Generate config ID and OAuth state
    const configId = generateId();
    const oauthState = generateState();

    // Store config in memory
    const config = {
      id: configId,
      userId: user_id,
      brokerName: 'zerodha',
      apiKey: api_key,
      apiSecret: api_secret, // In production, this would be encrypted
      isConnected: false,
      connectionStatus: {
        state: 'connecting',
        message: 'OAuth flow initiated',
        lastChecked: new Date().toISOString()
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    inMemoryStorage.configs.set(configId, config);
    inMemoryStorage.states.set(oauthState, { configId, userId: user_id, createdAt: Date.now() });

    // Generate OAuth URL
    const redirectUri = frontend_url ? 
      `${frontend_url}/broker-callback` : 
      `${process.env.ZERODHA_REDIRECT_URI || 'http://localhost:3000/broker-callback'}`;

    const encodedRedirect = encodeURIComponent(redirectUri);
    const oauthUrl = `https://kite.zerodha.com/connect/login?api_key=${api_key}&v=3&state=${oauthState}&redirect_uri=${encodedRedirect}&response_type=code`;

    console.log(`✅ OAuth setup successful for user ${user_id}, config ${configId}`);

    res.json({
      success: true,
      data: {
        oauth_url: oauthUrl,
        state: oauthState,
        config_id: configId,
        redirect_uri: redirectUri
      },
      message: 'OAuth flow initiated successfully'
    });

  } catch (error) {
    console.error('OAuth setup error:', error);
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

    // Verify OAuth state
    const stateData = inMemoryStorage.states.get(state);
    if (!stateData || stateData.configId !== config_id) {
      return res.status(400).json({
        success: false,
        error: 'Invalid OAuth state'
      });
    }

    // Get config
    const config = inMemoryStorage.configs.get(config_id);
    if (!config) {
      return res.status(404).json({
        success: false,
        error: 'Broker configuration not found'
      });
    }

    // For Phase-1 testing, simulate successful token exchange
    const mockTokens = {
      access_token: `mock_access_token_${Date.now()}`,
      refresh_token: `mock_refresh_token_${Date.now()}`,
      user_id: `mock_user_${config.userId}`,
      user_type: 'individual',
      user_shortname: 'Test User'
    };

    // Store tokens in memory
    inMemoryStorage.tokens.set(config_id, {
      ...mockTokens,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // 24 hours
      createdAt: new Date().toISOString()
    });

    // Update config status
    config.isConnected = true;
    config.connectionStatus = {
      state: 'connected',
      message: 'Successfully connected to Zerodha (Phase-1 Mock)',
      lastChecked: new Date().toISOString()
    };
    config.updatedAt = new Date().toISOString();

    // Clear OAuth state
    inMemoryStorage.states.delete(state);

    console.log(`✅ OAuth callback successful for config ${config_id}`);

    res.json({
      success: true,
      data: {
        user_id: mockTokens.user_id,
        user_type: mockTokens.user_type,
        user_shortname: mockTokens.user_shortname,
        broker_user_id: mockTokens.user_id
      },
      message: 'OAuth authentication completed successfully (Phase-1 Mock)'
    });

  } catch (error) {
    console.error('OAuth callback error:', error);
    res.status(500).json({
      success: false,
      error: 'OAuth authentication failed',
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
      config = inMemoryStorage.configs.get(config_id);
    } else {
      // Find config by user_id
      for (const [id, cfg] of inMemoryStorage.configs.entries()) {
        if (cfg.userId === user_id && cfg.brokerName === 'zerodha') {
          config = cfg;
          break;
        }
      }
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
    const tokens = inMemoryStorage.tokens.get(config.id);
    const tokenStatus = tokens ? {
      hasTokens: true,
      expiresAt: tokens.expiresAt,
      isExpired: new Date(tokens.expiresAt) < new Date()
    } : {
      hasTokens: false,
      isExpired: true
    };

    res.json({
      success: true,
      data: {
        configId: config.id,
        isConnected: config.isConnected,
        connectionStatus: config.connectionStatus,
        tokenStatus: tokenStatus,
        lastSync: config.updatedAt,
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
 * Disconnect broker
 * POST /broker/disconnect
 */
router.post('/disconnect', async (req, res) => {
  try {
    const { config_id } = req.body;

    if (!config_id) {
      return res.status(400).json({
        success: false,
        error: 'config_id is required'
      });
    }

    const config = inMemoryStorage.configs.get(config_id);
    if (!config) {
      return res.status(404).json({
        success: false,
        error: 'Broker configuration not found'
      });
    }

    // Remove tokens
    inMemoryStorage.tokens.delete(config_id);

    // Update config status
    config.isConnected = false;
    config.connectionStatus = {
      state: 'disconnected',
      message: 'Disconnected successfully',
      lastChecked: new Date().toISOString()
    };
    config.updatedAt = new Date().toISOString();

    console.log(`✅ Disconnected config ${config_id}`);

    res.json({
      success: true,
      message: 'Disconnected successfully'
    });

  } catch (error) {
    console.error('Disconnect error:', error);
    res.status(500).json({
      success: false,
      error: 'Disconnect failed',
      message: error.message
    });
  }
});

/**
 * Health check for OAuth endpoints
 * GET /broker/health
 */
router.get('/health', async (req, res) => {
  try {
    const stats = {
      totalConfigs: inMemoryStorage.configs.size,
      connectedConfigs: Array.from(inMemoryStorage.configs.values()).filter(c => c.isConnected).length,
      activeTokens: inMemoryStorage.tokens.size,
      pendingStates: inMemoryStorage.states.size
    };

    res.json({
      success: true,
      data: {
        status: 'healthy',
        module: 'brokerService',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        mode: 'phase-1-testing',
        storage: 'in-memory',
        stats,
        note: 'Phase-1 testing mode - using in-memory storage instead of database'
      },
      moduleName: 'brokerService',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'OAuth health check failed',
      timestamp: new Date().toISOString()
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

    const userConfigs = Array.from(inMemoryStorage.configs.values())
      .filter(config => config.userId === user_id);

    res.json({
      success: true,
      data: userConfigs,
      count: userConfigs.length
    });

  } catch (error) {
    console.error('Get configs error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to get broker configurations'
    });
  }
});

module.exports = router;
