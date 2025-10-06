const express = require('express');
const AuthService = require('./services/authService');
const RateLimiter = require('./services/rateLimiter');
// Remove top-level import to prevent loading issues
const User = require('./models/user');
const Otp = require('./models/otp');

module.exports = {
  name: 'auth',
  version: '2.0.0',
  description: 'OTP-based authentication and user management',
  _getRoutesCalled: false,
  
  async initialize(container) {
    try {
      // Check required environment variables (but don't fail initialization)
      const requiredEnvVars = [
        'OAUTH_ENCRYPTION_KEY',
        'JWT_SECRET', 
        'AUTH_OTP_PEPPER'
      ];
      
      const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
      
      if (missingVars.length > 0) {
        console.warn('⚠️ Auth module missing some environment variables:', missingVars);
        console.warn('📋 Some features may not work without these variables:');
        missingVars.forEach(varName => {
          console.warn(`   - ${varName}`);
        });
        console.warn('📖 See railway-env-setup.md for configuration details');
        // Don't throw error - continue with limited functionality
      } else {
        console.log('✅ All required environment variables are present');
      }
      
      // Register models
      container.register('User', User);
      container.register('Otp', Otp);
      
      // Register OAuth models
      const BrokerConfig = require('../models/brokerConfig');
      const OAuthToken = require('../../database/models/OAuthToken');
      container.register('BrokerConfig', BrokerConfig);
      container.register('OAuthToken', OAuthToken);
      
      // Register rate limiter
      const rateLimiter = new RateLimiter();
      container.register('rateLimiter', rateLimiter);
      
      // Register auth service
      const authService = new AuthService(container);
      container.register('authService', authService);
      
      // Register OAuth services
      const BrokerService = require('./services/brokerService');
      const TokenManager = require('./services/tokenManager');
      const KiteClient = require('./services/kiteClient');
      
      const brokerService = new BrokerService();
      const tokenManager = new TokenManager();
      const kiteClient = new KiteClient();
      
      container.register('brokerService', brokerService);
      container.register('tokenManager', tokenManager);
      container.register('kiteClient', kiteClient);
      
      // Get logger from container
      this.logger = container.get('logger');
      
      // Initialize OAuth database schema
      try {
        const { initialize: initOAuth } = require('../../core/database/initOAuth');
        await initOAuth();
        this.logger.info('OAuth database schema initialized');
      } catch (error) {
        this.logger.warn('OAuth database initialization failed (continuing):', error.message);
      }
      
      // Initialize AI Preferences database schema
      try {
        const { initAIPreferences } = require('../../core/database/initAIPreferences');
        await initAIPreferences();
        this.logger.info('AI Preferences database schema initialized');
      } catch (error) {
        this.logger.warn('AI Preferences database initialization failed (continuing):', error.message);
      }
      
      this.logger.info('AuthService initialized');
      this.logger.info('OAuth services initialized');
      
      // Setup event listeners
      this.setupEventListeners(container);
      
      this.logger.info('Auth module initialized successfully');
      this.logger.info('Auth routes registered at /api/modules/auth');
      this.logger.info('OAuth routes registered at /api/modules/auth/broker');
      
      return {
        status: 'initialized',
        routes: 'registered',
        services: ['authService', 'rateLimiter', 'brokerService', 'tokenManager', 'kiteClient'],
        models: ['User', 'Otp', 'BrokerConfig', 'OAuthToken']
      };
      
    } catch (error) {
      this.logger = container.get('logger');
      this.logger.error('Failed to initialize auth module:', error);
      throw error;
    }
  },
  
  setupEventListeners(container) {
    const eventBus = container.get('eventBus');
    const authService = container.get('authService');
    
    // Listen for auth events and re-emit them to the central event bus
    eventBus.on('auth:otp:requested', (data) => {
      this.logger.info('OTP requested event received', data);
    });
    
    eventBus.on('auth:otp:verified', (data) => {
      this.logger.info('OTP verified event received', data);
    });
    
    eventBus.on('auth:user:invited', (data) => {
      this.logger.info('User invited event received', data);
    });
    
    eventBus.on('auth:user:activated', (data) => {
      this.logger.info('User activated event received', data);
    });
    
    eventBus.on('auth:login', (data) => {
      this.logger.info('User login event received', data);
    });
  },
  
  getRoutes() {
    console.log('🔍 Auth getRoutes() called at', new Date().toISOString());
    
    const express = require('express');
    const router = express.Router();
    
    console.log('🔍 Creating router...');
    
    // Test route with detailed logging
    router.get('/test', (req, res) => {
      console.log('🔍 /test route hit!');
      res.json({
        success: true,
        message: 'Auth routes working!',
        timestamp: new Date().toISOString(),
        path: req.path,
        method: req.method
      });
    });
    
    // Debug route to check module status
    router.get('/debug', (req, res) => {
      res.json({
        success: true,
        data: {
          name: this.name,
          version: this.version,
          status: 'initialized',
          description: this.description,
          registeredAt: new Date().toISOString(),
          methods: {
            hasHealth: typeof this.getHealthCheck === 'function',
            hasInitialize: typeof this.initialize === 'function',
            hasStart: typeof this.start === 'function',
            hasStop: typeof this.stop === 'function'
          },
          dependencies: [],
          provides: [],
          services: {},
          routes: 'registered'
        },
        moduleName: this.name,
        timestamp: new Date().toISOString()
      });
    });
    
    // Mount OAuth routes at /broker (Production version with database)
    try {
      const oauthRoutes = require('./routes/oauth');
      router.use('/broker', oauthRoutes);
      console.log('✅ OAuth routes (Production) mounted at /broker');
    } catch (error) {
      console.error('❌ Failed to load OAuth routes:', error);
      // Add fallback route to show the error
      router.get('/broker/error', (req, res) => {
        res.status(500).json({
          success: false,
          error: 'OAuth routes failed to load',
          message: error.message,
          timestamp: new Date().toISOString()
        });
      });
    }
    
    // Add a catch-all route to see what's happening
    router.use('*', (req, res, next) => {
      console.log('🔍 Auth catch-all route hit:', req.method, req.path);
      next();
    });
    
    console.log('🔍 Router created with stack length:', router.stack ? router.stack.length : 'undefined');
    console.log('🔍 Router type:', typeof router);
    console.log('🔍 Router constructor:', router.constructor.name);
    
    return router;
  },
  
  getHealthCheck() {
    return async (container) => {
      try {
        const authService = container.get('authService');
        return await authService.healthCheck();
      } catch (error) {
        return {
          status: 'unhealthy',
          error: error.message
        };
      }
    };
  }
};
