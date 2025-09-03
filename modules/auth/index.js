const express = require('express');
const AuthService = require('./services/authService');
const RateLimiter = require('./services/rateLimiter');
const authRoutes = require('./routes');
const User = require('./models/user');
const Otp = require('./models/otp');

module.exports = {
  name: 'auth',
  version: '2.0.0',
  description: 'OTP-based authentication and user management',
  
  async initialize(container) {
    try {
      // Check required environment variables
      const requiredEnvVars = [
        'OAUTH_ENCRYPTION_KEY',
        'JWT_SECRET', 
        'AUTH_OTP_PEPPER'
      ];
      
      const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
      
      if (missingVars.length > 0) {
        console.error('❌ Auth module missing required environment variables:', missingVars);
        console.error('📋 Please set these environment variables in Railway:');
        missingVars.forEach(varName => {
          console.error(`   - ${varName}`);
        });
        console.error('📖 See railway-env-setup.md for configuration details');
        throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
      }
      
      // Register models
      container.register('User', User);
      container.register('Otp', Otp);
      
      // Register OAuth models
      const BrokerConfig = require('./models/brokerConfig');
      const OAuthToken = require('./models/oauthToken');
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
    try {
      console.log('🔍 Auth getRoutes() called - START');
      console.log('🔍 authRoutes import type:', typeof authRoutes);
      console.log('🔍 authRoutes defined:', !!authRoutes);
      
      // Test if authRoutes can be called
      if (typeof authRoutes === 'function') {
        console.log('🔍 authRoutes is a function (Express router)');
        console.log('🔍 authRoutes.stack exists:', !!authRoutes.stack);
        console.log('🔍 authRoutes.stack length:', authRoutes.stack ? authRoutes.stack.length : 'N/A');
        
        if (authRoutes.stack) {
          console.log('🔍 Auth Router Stack Debug:');
          authRoutes.stack.forEach((layer, index) => {
            if (layer.route) {
              const methods = Object.keys(layer.route.methods);
              console.log(`  ${index}: ${methods.join(',').toUpperCase()} ${layer.route.path}`);
            } else if (layer.regexp) {
              console.log(`  ${index}: MIDDLEWARE ${layer.regexp}`);
            }
          });
        }
        
        console.log('🔍 Returning authRoutes');
        return authRoutes;
      } else {
        console.error('❌ authRoutes is not a function:', typeof authRoutes);
        return null;
      }
    } catch (error) {
      console.error('❌ Error in auth getRoutes():', error);
      console.error('❌ Error stack:', error.stack);
      return null;
    }
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
