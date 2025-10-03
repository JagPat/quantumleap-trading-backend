const express = require('express');
const Joi = require('joi');
const crypto = require('crypto');
const { v4: uuidv4, v5: uuidv5, validate: uuidValidate } = require('uuid');

const USER_ID_NAMESPACE = process.env.BROKER_USER_NAMESPACE || 'e7c9b9f4-7a07-49f2-9b75-95f47b8f9b35';

const normalizeUserIdentifier = (incoming) => {
  if (!incoming) {
    return null;
  }

  if (uuidValidate(incoming)) {
    return incoming;
  }

  try {
    return uuidv5(String(incoming), USER_ID_NAMESPACE);
  } catch (error) {
    console.warn('⚠️ Unable to normalize user identifier, falling back to raw value:', error);
    return incoming;
  }
};

const router = express.Router();

const parseBoolean = (value, defaultValue = false) => {
  if (value === undefined || value === null) return defaultValue;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true' || value === '1';
  }
  return defaultValue;
};

const mapBrokerErrorStatus = (error) => {
  if (!error || !error.code) {
    return 500;
  }

  switch (error.code) {
    case 'TOKEN_EXPIRED':
    case 'TOKEN_INVALID':
    case 'TOKEN_ERROR':
      return 401;
    case 'BROKER_UNAUTHORIZED':
      return 403;
    case 'RATE_LIMIT':
      return 429;
    case 'BROKER_ERROR':
      return 502;
    default:
      return 500;
  }
};

const respondWithBrokerError = (res, error) => {
  const status = mapBrokerErrorStatus(error);
  return res.status(status).json({
    success: false,
    error: error.message,
    code: error.code || 'BROKER_ERROR',
    needs_reauth: Boolean(error.needs_reauth || status === 401 || status === 403),
    details: error.details || null,
    timestamp: new Date().toISOString()
  });
};

// Security middleware (temporarily disabled for deployment)
// TODO: Re-enable after middleware files are deployed
// const { createOAuthRateLimiter, createTokenRefreshLimiter } = require('../../../middleware/rateLimiter');
// const csrfProtection = require('../../../middleware/csrfProtection');
// const secureLogger = require('../../../middleware/secureLogger');
// const { securityHeaders, validateInput, requestSizeLimit } = require('../../../middleware/securityHeaders');

// Apply basic security headers
router.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

// Lazy initialization functions to avoid loading issues
const getBrokerService = () => {
  const BrokerService = require('../services/brokerService');
  return new BrokerService();
};

const getSecurity = () => {
  const SecurityManager = require('../../../core/security');
  return new SecurityManager();
};

const getBrokerConfig = () => {
  // Auth model exports a class; instantiate per use
  const BrokerConfig = require('../models/brokerConfig');
  return new BrokerConfig();
};

const getOAuthToken = () => {
  // Auth model exports a class; instantiate per use
  const OAuthToken = require('../models/oauthToken');
  return new OAuthToken();
};

// Optional admin key to protect admin endpoints (set ADMIN_CRON_KEY in env)
const ADMIN_CRON_KEY = process.env.ADMIN_CRON_KEY || null;
const verifyAdminKey = (req, res, next) => {
  if (!ADMIN_CRON_KEY) return next(); // if not set, allow (development)
  const provided = req.get('X-Admin-Key') || req.query.admin_key;
  if (provided && provided === ADMIN_CRON_KEY) return next();
  return res.status(403).json({ success: false, error: 'Forbidden' });
};

// Validation schemas
const setupOAuthSchema = Joi.object({
  api_key: Joi.string().required().min(10).max(100),
  api_secret: Joi.string().required().min(10).max(100),
  user_id: Joi.string().allow('', null).optional(),
  frontend_url: Joi.string().uri().optional()
});

const callbackSchema = Joi.object({
  request_token: Joi.string().required(),
  state: Joi.string().required(),
  config_id: Joi.string().uuid().required()
});

const generateSessionSchema = Joi.object({
  request_token: Joi.string().required().min(8),
  api_key: Joi.string().required().min(6),
  api_secret: Joi.string().required().min(6),
  user_id: Joi.string().allow('', null).optional(),
  config_id: Joi.string().uuid().optional()
});

const refreshTokenSchema = Joi.object({
  config_id: Joi.string().uuid().required()
});

const disconnectSchema = Joi.object({
  config_id: Joi.string().uuid().required()
});

const tokenUpdateSchema = Joi.object({
  user_id: Joi.string().required(),
  access_token: Joi.string().required(),
  expires_in: Joi.number().integer().positive().optional(),
  expires_at: Joi.alternatives().try(Joi.date().iso(), Joi.string()).optional(),
  source: Joi.string().max(120).optional()
});

const tokenMetadataQuerySchema = Joi.object({
  user_id: Joi.string().optional(),
  config_id: Joi.string().uuid().optional()
}).or('user_id', 'config_id');

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

    let { api_key, api_secret, user_id, frontend_url } = value;

    const originalUserId = user_id;
    let normalizedUserId = normalizeUserIdentifier(user_id) || uuidv4();

    console.log('[OAuth] Normalized user identifier', { originalUserId, normalizedUserId });

    // Initialize services
    const brokerConfig = getBrokerConfig();
    const security = getSecurity();

    // Ensure user exists in users table (create if not exists)
    try {
      const db = require('../../../core/database/connection');
      if (uuidValidate(normalizedUserId)) {
        await db.query(`
          INSERT INTO users (id, email, created_at, updated_at) 
          VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
          ON CONFLICT (id) DO NOTHING
        `, [normalizedUserId, `temp_${normalizedUserId}@example.com`]);
      } else {
        console.warn('⚠️ Skipping users table upsert for non-UUID user_id:', normalizedUserId);
      }
    } catch (userError) {
      console.error('Failed to create/verify user:', userError);
      // Continue anyway - user might already exist
    }

    // Check if config already exists
    let config = await brokerConfig.getByUserAndBroker(normalizedUserId, 'zerodha');
    
    if (config) {
      let credentials = null;
      try {
        credentials = await brokerConfig.getCredentials(config.id);
      } catch (decryptError) {
        console.warn('[OAuth] Failed to decrypt existing broker credentials, recreating config', {
          configId: config.id,
          userId: normalizedUserId,
          error: decryptError.message
        });

        await brokerConfig.delete(config.id);
        config = null;
      }

      if (config && credentials) {
        if (credentials.apiKey !== api_key || credentials.apiSecret !== api_secret) {
          // Credentials changed, need to recreate config
          await brokerConfig.delete(config.id);
          config = null;
        }
      }
    }

    if (!config) {
      // Create new config
      config = await brokerConfig.create({
        userId: normalizedUserId,
        brokerName: 'zerodha',
        apiKey: api_key,
        apiSecret: api_secret
      });
    }

    // Generate OAuth state for CSRF protection
    const oauthState = security.generateOAuthState();
    await brokerConfig.updateOAuthState(config.id, oauthState);

    // Store pending OAuth session in database
    const db = require('../../../core/database/connection');
    const redirectUri = frontend_url ? 
      `${frontend_url}/broker-callback` : 
      `${process.env.FRONTEND_URL || 'http://localhost:3000'}/broker-callback`;
    
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes
    await db.query(
      `INSERT INTO oauth_sessions (config_id, state, status, redirect_uri, expires_at)
       VALUES ($1, $2, 'pending', $3, $4)
       ON CONFLICT DO NOTHING`,
      [config.id, oauthState, redirectUri, expiresAt]
    );

    // Zerodha Kite Connect uses the redirect URL configured in the developer console.
    // Do not pass redirect_uri/response_type in the login URL; keep to official format.
    const oauthUrl = `https://kite.zerodha.com/connect/login?api_key=${api_key}&v=3&state=${oauthState}`;

    // Update connection status
    await brokerConfig.updateConnectionStatus(config.id, {
      state: 'connecting',
      message: 'OAuth flow initiated',
      lastChecked: new Date().toISOString()
    });

    // Log operation
    const auditUserId = uuidValidate(normalizedUserId) ? normalizedUserId : null;

    await logOAuthOperation(config.id, auditUserId, 'oauth_initiated', 'success', {
      redirectUri,
      apiKey: api_key
    }, req);

    res.json({
      success: true,
      config_id: config.id,
      user_id: normalizedUserId,
      data: {
        oauth_url: oauthUrl,
        state: oauthState,
        config_id: config.id,
        redirect_uri: redirectUri,
        user_id: normalizedUserId,
        original_user_id: originalUserId || null
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

    // Initialize services
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();

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
        config_id,
        user_id: sessionData.user_id,
        broker_user_id: sessionData.user_id,
        user_type: sessionData.user_type,
        user_shortname: sessionData.user_shortname
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
 * Exchange request token for access token (direct session generation)
 * POST /broker/generate-session
 */
router.post('/generate-session', async (req, res) => {
  try {
    const { error, value } = generateSessionSchema.validate(req.body);
    if (error) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request data',
        details: error.details[0].message
      });
    }

    const { request_token, api_key, api_secret, user_id, config_id } = value;

    const normalizedUserId = user_id ? (normalizeUserIdentifier(user_id) || uuidv4()) : (config_id ? null : uuidv4());

    const brokerService = getBrokerService();

    const sessionResult = await brokerService.generateBrokerSession({
      requestToken: request_token,
      apiKey: api_key,
      apiSecret: api_secret,
      userId: normalizedUserId,
      originalUserId: user_id || null,
      configId: config_id || null
    });

    res.json({
      success: true,
      data: sessionResult
    });
  } catch (error) {
    console.error('Generate session error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate broker session',
      message: error.message
    });
  }
});

/**
 * OAuth callback handler (GET version for standard OAuth flow)
 * GET /broker/callback
 */
router.get('/callback', async (req, res) => {
  try {
    console.log('OAuth GET callback received:', req.query);

    const { request_token, action, type, status, state } = req.query;

    // Basic validation
    if (!request_token) {
      return res.status(400).json({
        success: false,
        error: 'Missing request_token parameter'
      });
    }

    if (status !== 'success') {
      return res.status(400).json({
        success: false,
        error: 'OAuth authentication was not successful',
        details: { status, action, type }
      });
    }

    // Zerodha does NOT return state parameter in callback
    // We need to find the most recent pending oauth_session and use request_token to identify it
    const db = require('../../../core/database/connection');
    
    let configId = null;
    
    if (state) {
      // If state is provided (shouldn't happen with Zerodha but check anyway)
      const stateLookup = await db.query(
        `SELECT config_id FROM oauth_sessions WHERE state = $1 AND expires_at > NOW() ORDER BY created_at DESC LIMIT 1`,
        [state]
      );
      if (stateLookup.rows.length > 0) {
        configId = stateLookup.rows[0].config_id;
      }
    }
    
    if (!configId) {
      // Find the most recent pending session (within last 10 minutes)
      const recentSession = await db.query(
        `SELECT config_id FROM oauth_sessions 
         WHERE status = 'pending' AND expires_at > NOW() 
         ORDER BY created_at DESC LIMIT 1`
      );
      
      if (recentSession.rows.length === 0) {
        console.warn('[OAuth] No pending session found for callback');
        const rawFrontendUrl = process.env.FRONTEND_URL || 'https://quantum-leap-frontend-production.up.railway.app';
        const frontendUrl = rawFrontendUrl.trim().replace(/\s+/g, '');
        const redirectUrl = `${frontendUrl}/broker-callback?status=error&error=${encodeURIComponent('No pending OAuth session found. Please try again.')}`;
        return res.redirect(redirectUrl);
      }
      
      configId = recentSession.rows[0].config_id;
    }

    // At this point we have a valid configId
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();

    const config = await brokerConfig.getById(configId);
    if (!config) {
      const rawFrontendUrl = process.env.FRONTEND_URL || 'https://quantum-leap-frontend-production.up.railway.app';
      const frontendUrl = rawFrontendUrl.trim().replace(/\s+/g, '');
      const redirectUrl = `${frontendUrl}/broker-callback?status=error&error=${encodeURIComponent('Configuration not found')}`;
      return res.redirect(redirectUrl);
    }

    try {
      const credentials = await brokerConfig.getCredentials(configId);
      const KiteConnect = require('kiteconnect').KiteConnect;
      const kc = new KiteConnect({ api_key: credentials.apiKey });

      const sessionData = await kc.generateSession(request_token, credentials.apiSecret);
      
      // Log the complete Zerodha session data for debugging
      console.log('🔍 [OAuth] Complete Zerodha session data:', JSON.stringify(sessionData, null, 2));
      
      console.log('📊 [OAuth] Zerodha session data fields:', {
        user_id: sessionData.user_id,
        user_type: sessionData.user_type,
        email: sessionData.email,
        user_name: sessionData.user_name,
        user_shortname: sessionData.user_shortname,
        broker: sessionData.broker,
        has_user_id: !!sessionData.user_id
      });
      
      // According to Zerodha Kite Connect API documentation:
      // The token exchange only returns access_token, not user details
      // We need to make a separate API call to /user/profile to get user_id
      
      let brokerUserId = 'unknown';
      
      try {
        // Fetch user profile from Zerodha API to get user_id
        console.log('🔍 [OAuth] Fetching user profile from Zerodha API...');
        const profileResponse = await fetch('https://api.kite.trade/user/profile', {
          method: 'GET',
          headers: {
            'Authorization': `token ${sessionData.access_token}`,
            'X-Kite-Version': '3'
          }
        });
        
        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          console.log('🔍 [OAuth] Zerodha profile response:', JSON.stringify(profileData, null, 2));
          
          // Extract user_id from profile response
          // Zerodha returns: { data: { user_id: "ABC123", user_name: "John Doe", email: "..." } }
          // We need the user_id (client code), NOT user_name (full name)
          if (profileData.data?.user_id) {
            brokerUserId = profileData.data.user_id;
            console.log('✅ [OAuth] Got user_id from profile API:', brokerUserId);
          } else {
            console.warn('⚠️ [OAuth] user_id not found in profile response, using email as fallback');
            brokerUserId = profileData.data?.email || sessionData.user_name || 'unknown';
          }
        } else {
          console.warn('⚠️ [OAuth] Failed to fetch user profile:', profileResponse.status, profileResponse.statusText);
          // Fallback: try to extract from session data
          // sessionData from generateSession() might have user_id directly
          brokerUserId = sessionData.user_id || sessionData.email || 'unknown';
        }
      } catch (error) {
        console.error('❌ [OAuth] Error fetching user profile:', error.message);
        // Fallback to session data if available
        brokerUserId = sessionData.user_id || sessionData.email || 'unknown';
      }
      
      console.log('🔑 [OAuth] Final broker user_id:', brokerUserId);

      // Store tokens securely
      await oauthToken.store({
        configId: configId,
        accessToken: sessionData.access_token,
        refreshToken: sessionData.refresh_token,
        expiresIn: 86400,
        tokenType: 'Bearer',
        userId: brokerUserId
      });
      
      // Update broker_configs with user_id (skip for now - column type issue)
      // TODO: Fix broker_configs.user_id column type (currently UUID, should be VARCHAR)
      // await db.query(
      //   `UPDATE broker_configs SET user_id = $1, updated_at = NOW() WHERE id = $2`,
      //   [brokerUserId, configId]
      // ).catch(err => console.error('Failed to update broker_configs user_id:', err));

      // Update connection status
      await brokerConfig.updateConnectionStatus(configId, {
        state: 'connected',
        message: 'Successfully connected to Zerodha',
        lastChecked: new Date().toISOString()
      });

      // Mark oauth session completed (update any matching session for this config)
      await db.query(
        `UPDATE oauth_sessions SET request_token = $1, status = 'completed', updated_at = NOW() 
         WHERE config_id = $2 AND status = 'pending'`,
        [request_token, configId]
      ).catch(() => {});

      // Log success
      await logOAuthOperation(configId, config.userId, 'token_exchanged', 'success', {
        brokerUserId: brokerUserId,
        userType: sessionData.user_type
      }, req);

      // Clean and validate frontend URL
      const rawFrontendUrl = process.env.FRONTEND_URL || 'https://quantum-leap-frontend-production.up.railway.app';
      const frontendUrl = rawFrontendUrl.trim().replace(/\s+/g, '');
      const redirectUrl = `${frontendUrl}/broker-callback?status=success&config_id=${encodeURIComponent(configId)}&user_id=${encodeURIComponent(brokerUserId)}`;
      
      console.log('🔄 Redirecting to frontend:', redirectUrl);
      console.log('🔑 Redirect includes user_id:', brokerUserId);
      return res.redirect(redirectUrl);
    } catch (exchangeError) {
      console.error('OAuth GET callback exchange error:', exchangeError);
      await db.query(
        `UPDATE oauth_sessions SET status = 'failed', updated_at = NOW() WHERE config_id = $1 AND status = 'pending'`,
        [configId]
      ).catch(() => {});
      await logOAuthOperation(configId, config.userId, 'token_exchanged', 'failed', {
        error: exchangeError.message
      }, req).catch(() => {});

      const rawFrontendUrl = process.env.FRONTEND_URL || 'https://quantum-leap-frontend-production.up.railway.app';
      const frontendUrl = rawFrontendUrl.trim().replace(/\s+/g, '');
      const redirectUrl = `${frontendUrl}/broker-callback?status=error&error=${encodeURIComponent(exchangeError.message)}`;
      return res.redirect(redirectUrl);
    }

  } catch (error) {
    console.error('OAuth GET callback error:', error);
    
    // Redirect to frontend with error
    const rawFrontendUrl = process.env.FRONTEND_URL || 'https://quantum-leap-frontend-production.up.railway.app';
    const frontendUrl = rawFrontendUrl.trim().replace(/\s+/g, '');
    const redirectUrl = `${frontendUrl}/broker-callback?status=error&error=${encodeURIComponent(error.message)}`;
    
    res.redirect(redirectUrl);
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

    // Initialize services
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();

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

    // Initialize services
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();

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
  // Check both query parameters and headers for config_id and user_id
  const config_id = req.query.config_id || req.headers['x-config-id'];
  const user_id = req.query.user_id || req.headers['x-user-id'];
  const requestTimestamp = new Date().toISOString();
  console.info('[Auth][Broker] %s GET /broker/status %o', requestTimestamp, {
    configId: config_id || null,
    userId: user_id || null,
    fromQuery: !!req.query.config_id,
    fromHeaders: !!req.headers['x-config-id']
  });

  try {
    if (!config_id && !user_id) {
      return res.status(400).json({ success: false, error: 'Either config_id or user_id is required' });
    }

    const brokerService = getBrokerService();
    let configId = config_id || null;

    // Validate UUID format if config_id is provided
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (configId && !uuidRegex.test(configId)) {
      console.warn('[Auth][Broker] Invalid UUID format for config_id:', configId);
      return res.status(400).json({ 
        success: false, 
        error: 'Invalid config_id format (must be valid UUID)' 
      });
    }

    if (!configId) {
      const normalizedLookupId = normalizeUserIdentifier(user_id);
      const brokerConfig = getBrokerConfig();
      const cfg = await brokerConfig.getByUserAndBroker(normalizedLookupId, 'zerodha');
      if (!cfg) {
        return res.json({
          success: true,
          data: {
            isConnected: false,
            needsReauth: true,
            needs_reauth: true,
            connectionStatus: {
              state: 'disconnected',
              message: 'No broker configuration found',
              lastChecked: new Date().toISOString()
            }
          }
        });
      }
      configId = cfg.id;
    }

    // Delegate to service for consistent status evaluation
    const connection = await brokerService.getConnectionStatus(configId);
    if (!connection?.success) {
      // Fallback shape if service returns plain status object
      return res.json({ success: true, data: connection?.status || connection });
    }
    return res.json({ success: true, data: connection.status });
  } catch (error) {
    console.error('Status check error:', error);
    return res.status(500).json({ success: false, error: 'Failed to check status' });
  }
});

/**
 * Get broker session details
 * GET /broker/session
 */
router.get('/session', async (req, res) => {
  const { config_id, user_id } = req.query;
  const requestTimestamp = new Date().toISOString();
  console.info('[Auth][Broker] %s GET /broker/session %o', requestTimestamp, {
    configId: config_id || null,
    userId: user_id || null
  });

  if (!config_id && !user_id) {
    return res.status(400).json({
      status: 'error',
      message: 'Either config_id or user_id is required'
    });
  }

  try {
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();
    const security = getSecurity();

    let config = null;
    if (config_id) {
      config = await brokerConfig.getById(config_id);
    } else {
      const normalizedId = normalizeUserIdentifier(user_id);
      config = await brokerConfig.getByUserAndBroker(normalizedId, 'zerodha');
    }

    if (!config) {
      return res.json({
        status: 'not_found',
        message: 'Broker session not found for the provided identifier',
        data: null
      });
    }

    const tokenStatus = await oauthToken.getTokenStatus(config.id);
    const tokenRecord = await oauthToken.getByConfigId(config.id);

    let accessToken = null;
    let refreshToken = null;
    let brokerUserId = null;
    let tokenExpiresAt = null;

    if (tokenRecord) {
      brokerUserId = tokenRecord.userId || null;
      tokenExpiresAt = tokenRecord.expiresAt || null;

      try {
        if (tokenRecord.accessTokenEncrypted) {
          accessToken = security.decrypt(tokenRecord.accessTokenEncrypted);
        }
        if (tokenRecord.refreshTokenEncrypted) {
          refreshToken = security.decrypt(tokenRecord.refreshTokenEncrypted);
        }
      } catch (tokenError) {
        console.error('[Auth][Broker] Failed to decrypt tokens for config %s: %s', config.id, tokenError.message);
      }
    }

    console.info('[Auth][Broker] Session handler decrypts stored tokens', {
      configId: config.id,
      userId: brokerUserId,
      hasTokenRecord: !!tokenRecord,
      hasAccessToken: !!accessToken,
      hasRefreshToken: !!refreshToken
    });

    return res.json({
      status: 'success',
      data: {
        id: config.id,
        broker_name: config.brokerName,
        api_key: config.apiKey,
        is_connected: config.isConnected,
        connection_status: config.connectionStatus,
        last_sync: config.lastSync,
        updated_at: config.updatedAt,
        user_id: config.userId,
        user_data: brokerUserId ? { user_id: brokerUserId } : null,
        access_token: accessToken,
        refresh_token: refreshToken,
        token_expires_at: tokenExpiresAt,
        token_status: tokenStatus
      },
      meta: {
        requested_at: requestTimestamp
      }
    });
  } catch (error) {
    console.error('[Auth][Broker] Session lookup failed:', error);
    return res.status(500).json({
      status: 'error',
      message: 'Failed to retrieve broker session',
      error: error.message
    });
  }
});

/**
 * Persist broker session metadata from frontend
 * POST /broker/session/create
 */
router.post('/session/create', async (req, res) => {
  const requestTimestamp = new Date().toISOString();
  const { broker_name = 'zerodha', user_data = null } = req.body || {};
  const clientUserId = user_data?.user_id || null;

  console.info('[Auth][Broker] %s POST /broker/session/create %o', requestTimestamp, {
    brokerName: broker_name,
    userId: clientUserId
  });

  if (!clientUserId) {
    return res.status(400).json({
      status: 'error',
      message: 'user_data.user_id is required to persist session metadata'
    });
  }

  try {
    const brokerConfig = getBrokerConfig();
    const normalizedId = normalizeUserIdentifier(clientUserId);

    const config = await brokerConfig.getByUserAndBroker(normalizedId, broker_name);

    if (!config) {
      return res.status(404).json({
        status: 'not_found',
        message: 'Broker configuration not found for the provided user_id',
        data: null
      });
    }

    const statusPayload = {
      state: 'connected',
      message: 'Session confirmed by frontend client',
      lastChecked: requestTimestamp
    };

    await brokerConfig.updateConnectionStatus(config.id, statusPayload);

    return res.json({
      status: 'success',
      message: 'Broker session metadata recorded',
      data: {
        config_id: config.id,
        broker_name,
        user_id: normalizedId,
        connection_status: statusPayload
      },
      meta: {
        recorded_at: requestTimestamp
      }
    });
  } catch (error) {
    console.error('[Auth][Broker] Failed to record session metadata:', error);
    return res.status(500).json({
      status: 'error',
      message: 'Failed to persist broker session metadata',
      error: error.message
    });
  }
});

/**
 * Update broker access token from automated jobs
 * POST /broker/token/update
 */
router.post('/token/update', async (req, res) => {
  const { error, value } = tokenUpdateSchema.validate(req.body || {});
  if (error) {
    return res.status(400).json({
      success: false,
      error: 'Invalid token update payload',
      details: error.details?.[0]?.message
    });
  }

  const { user_id, access_token, expires_in, expires_at, source } = value;
  const normalizedUserId = normalizeUserIdentifier(user_id);
  const brokerService = getBrokerService();

  try {
    const result = await brokerService.updateAccessTokenFromAutomation({
      normalizedUserId,
      originalUserId: user_id,
      accessToken: access_token,
      expiresIn: expires_in,
      expiresAt: expires_at,
      source: source || 'automation'
    });

    return res.json({
      success: true,
      message: 'Access token updated successfully',
      data: result
    });
  } catch (err) {
    console.error('[Auth][Broker] Token update failed:', err);
    return res.status(500).json({
      success: false,
      error: 'Failed to persist access token',
      message: err.message
    });
  }
});

/**
 * Inspect broker token expiry/metadata (admin use)
 * GET /broker/token/expiry
 */
router.get('/token/expiry', async (req, res) => {
  const { error, value } = tokenMetadataQuerySchema.validate(req.query || {});
  if (error) {
    return res.status(400).json({
      success: false,
      error: 'Invalid query parameters',
      details: error.details?.[0]?.message
    });
  }

  const { user_id: userId, config_id: configId } = value;
  const brokerService = getBrokerService();

  try {
    const result = await brokerService.getTokenMetadata({
      normalizedUserId: userId ? normalizeUserIdentifier(userId) : null,
      originalUserId: userId,
      configId
    });

    return res.json({
      success: true,
      data: result
    });
  } catch (err) {
    console.error('[Auth][Broker] Token metadata lookup failed:', err);
    return res.status(404).json({
      success: false,
      error: err.message || 'Token metadata not found'
    });
  }
});

/**
 * Fetch live holdings from Zerodha via backend
 */
router.get('/holdings', async (req, res) => {
  const { user_id: userId, config_id: configId, bypass_cache: bypassCache } = req.query;
  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerService = getBrokerService();
    const data = await brokerService.getHoldingsData({
      normalizedUserId: userId ? normalizeUserIdentifier(userId) : null,
      originalUserId: userId,
      configId,
      bypassCache: parseBoolean(bypassCache)
    });
    return res.json({ success: true, data });
  } catch (error) {
    console.error('[Broker][DataFetch] Holdings fetch failed:', { message: error.message, code: error.code });
    return respondWithBrokerError(res, error);
  }
});

router.get('/positions', async (req, res) => {
  const { user_id: userId, config_id: configId, bypass_cache: bypassCache } = req.query;
  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerService = getBrokerService();
    const data = await brokerService.getPositionsData({
      normalizedUserId: userId ? normalizeUserIdentifier(userId) : null,
      originalUserId: userId,
      configId,
      bypassCache: parseBoolean(bypassCache)
    });
    return res.json({ success: true, data });
  } catch (error) {
    console.error('[Broker][DataFetch] Positions fetch failed:', { message: error.message, code: error.code });
    return respondWithBrokerError(res, error);
  }
});

router.get('/orders', async (req, res) => {
  const { user_id: userId, config_id: configId, bypass_cache: bypassCache } = req.query;
  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerService = getBrokerService();
    const data = await brokerService.getOrdersData({
      normalizedUserId: userId ? normalizeUserIdentifier(userId) : null,
      originalUserId: userId,
      configId,
      bypassCache: parseBoolean(bypassCache)
    });
    return res.json({ success: true, data });
  } catch (error) {
    console.error('[Broker][DataFetch] Orders fetch failed:', { message: error.message, code: error.code });
    return respondWithBrokerError(res, error);
  }
});

/**
 * Get broker user profile
 * GET /broker/profile
 * Optional POST alias for compatibility
 */
const handleGetProfile = async (req, res, userIdParam, configIdParam) => {
  const { user_id: qUserId, config_id: qConfigId } = req.query || {};
  const userId = userIdParam || qUserId;
  const configId = configIdParam || qConfigId;

  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerConfig = getBrokerConfig();
    const TokenManager = require('../services/tokenManager');
    const KiteClient = require('../services/kiteClient');

    let config = null;
    if (configId) {
      config = await brokerConfig.getById(configId);
    } else {
      const normalizedId = normalizeUserIdentifier(userId);
      config = await brokerConfig.getByUserAndBroker(normalizedId, 'zerodha');
    }

    if (!config) {
      return res.status(404).json({ success: false, error: 'Broker configuration not found' });
    }

    const tokenManager = new TokenManager();
    let accessToken;
    try {
      accessToken = await tokenManager.getValidAccessToken(config.id);
    } catch (tokenError) {
      const err = new Error('Unable to retrieve valid access token');
      err.code = 'TOKEN_ERROR';
      err.needs_reauth = true;
      return respondWithBrokerError(res, err);
    }

    const credentials = await brokerConfig.getCredentials(config.id);
    const kiteClient = new KiteClient();
    const result = await kiteClient.getUserProfile(accessToken, credentials.apiKey);

    return res.json({ success: true, data: { profile: result.profile } });
  } catch (error) {
    console.error('[Broker][Profile] Fetch failed:', error);
    return respondWithBrokerError(res, error);
  }
};

router.get('/profile', async (req, res) => {
  return handleGetProfile(req, res);
});

router.post('/profile', async (req, res) => {
  const { user_id, config_id } = req.body || {};
  return handleGetProfile(req, res, user_id, config_id);
});

/**
 * Get broker margins
 * GET /broker/margins
 * Optional POST alias for compatibility
 */
const handleGetMargins = async (req, res, userIdParam, configIdParam) => {
  const { user_id: qUserId, config_id: qConfigId } = req.query || {};
  const userId = userIdParam || qUserId;
  const configId = configIdParam || qConfigId;

  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerConfig = getBrokerConfig();
    const TokenManager = require('../services/tokenManager');
    const KiteClient = require('../services/kiteClient');

    let config = null;
    if (configId) {
      config = await brokerConfig.getById(configId);
    } else {
      const normalizedId = normalizeUserIdentifier(userId);
      config = await brokerConfig.getByUserAndBroker(normalizedId, 'zerodha');
    }

    if (!config) {
      return res.status(404).json({ success: false, error: 'Broker configuration not found' });
    }

    const tokenManager = new TokenManager();
    let accessToken;
    try {
      accessToken = await tokenManager.getValidAccessToken(config.id);
    } catch (tokenError) {
      const err = new Error('Unable to retrieve valid access token');
      err.code = 'TOKEN_ERROR';
      err.needs_reauth = true;
      return respondWithBrokerError(res, err);
    }

    const credentials = await brokerConfig.getCredentials(config.id);
    const kiteClient = new KiteClient();
    const result = await kiteClient.getMargins(accessToken, credentials.apiKey);

    return res.json({ success: true, data: { margins: result.margins } });
  } catch (error) {
    console.error('[Broker][Margins] Fetch failed:', error);
    return respondWithBrokerError(res, error);
  }
};

router.get('/margins', async (req, res) => {
  return handleGetMargins(req, res);
});

router.post('/margins', async (req, res) => {
  const { user_id, config_id } = req.body || {};
  return handleGetMargins(req, res, user_id, config_id);
});

/**
 * Admin: Refresh tokens for all active connections
 * POST /broker/admin/refresh-all
 * Header: X-Admin-Key: <ADMIN_CRON_KEY>
 */
router.post('/admin/refresh-all', verifyAdminKey, async (req, res) => {
  try {
    const brokerService = getBrokerService();
    const tokenManager = new (require('../services/tokenManager'))();
    const active = await brokerService.getActiveConnections();
    const results = [];
    for (const conn of active.connections || []) {
      try {
        const r = await tokenManager.refreshTokens(conn.id);
        results.push({ configId: conn.id, success: r.success, message: r.message || null, error: r.error || null });
      } catch (e) {
        results.push({ configId: conn.id, success: false, error: e.message });
      }
    }
    return res.json({ success: true, count: results.length, results, timestamp: new Date().toISOString() });
  } catch (error) {
    console.error('[Admin][RefreshAll] Error:', error);
    return res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * Admin: Inspect session-state for a user/config
 * GET /broker/admin/session-state?user_id=...&config_id=...
 * Header: X-Admin-Key: <ADMIN_CRON_KEY>
 */
router.get('/admin/session-state', verifyAdminKey, async (req, res) => {
  try {
    const { user_id: userId, config_id: configId } = req.query || {};
    const brokerConfig = getBrokerConfig();
    const oauthToken = getOAuthToken();

    let config = null;
    if (configId) {
      config = await brokerConfig.getById(configId);
    } else if (userId) {
      const normalized = normalizeUserIdentifier(userId);
      config = await brokerConfig.getByUserAndBroker(normalized, 'zerodha');
    }

    if (!config) {
      return res.json({ success: true, data: { hasConfig: false } });
    }

    const tokenStatus = await oauthToken.getTokenStatus(config.id);
    const tokenRecord = await oauthToken.getByConfigId(config.id);
    return res.json({
      success: true,
      data: {
        hasConfig: true,
        configId: config.id,
        needsReauth: config.needsReauth,
        sessionStatus: config.sessionStatus,
        tokenStatus,
        hasTokenRecord: !!tokenRecord,
        tokenExpiresAt: tokenRecord?.expiresAt || null,
        hasRefreshToken: Boolean(tokenRecord?.refreshTokenEncrypted)
      }
    });
  } catch (error) {
    console.error('[Admin][SessionState] Error:', error);
    return res.status(500).json({ success: false, error: error.message });
  }
});

router.get('/portfolio', async (req, res) => {
  const { user_id: userId, config_id: configId, bypass_cache: bypassCache } = req.query;
  if (!userId && !configId) {
    return res.status(400).json({ success: false, error: 'user_id or config_id is required' });
  }

  try {
    const brokerService = getBrokerService();
    const data = await brokerService.getPortfolioSnapshot({
      normalizedUserId: userId ? normalizeUserIdentifier(userId) : null,
      originalUserId: userId,
      configId,
      bypassCache: parseBoolean(bypassCache)
    });
    return res.json({ success: true, data });
  } catch (error) {
    console.error('[Broker][DataFetch] Portfolio snapshot failed:', { message: error.message, code: error.code });
    return respondWithBrokerError(res, error);
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

    // Initialize services
    const brokerService = getBrokerService();

    const normalizedLookupId = normalizeUserIdentifier(user_id);

    const result = await brokerService.getAllConfigsByUser(normalizedLookupId);

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

    // Initialize services
    const brokerService = getBrokerService();

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

    // Initialize services
    const brokerService = getBrokerService();

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

    // Initialize services
    const brokerService = getBrokerService();

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
    // Initialize services
    const brokerService = getBrokerService();

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
    // Initialize services
    const brokerService = getBrokerService();

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
    // Initialize services
    const brokerService = getBrokerService();

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
