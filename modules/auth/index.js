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
      // Register models
      container.register('User', User);
      container.register('Otp', Otp);
      
      // Register rate limiter
      const rateLimiter = new RateLimiter();
      container.register('rateLimiter', rateLimiter);
      
      // Register auth service
      const authService = new AuthService(container);
      container.register('authService', authService);
      
      // Get logger from container
      this.logger = container.get('logger');
      
      this.logger.info('AuthService initialized');
      
      // Setup event listeners
      this.setupEventListeners(container);
      
      this.logger.info('Auth module initialized successfully');
      this.logger.info('Auth routes registered at /api/modules/auth');
      
      return {
        status: 'initialized',
        routes: 'registered',
        services: ['authService', 'rateLimiter'],
        models: ['User', 'Otp']
      };
      
    } catch (error) {
      this.logger = container.get('logger');
      this.logger.error('Failed to initialize auth module:', error);
      throw error;
    }
  },
  
  setupEventListeners(container) {
    const eventBus = container.get('eventBusRouter');
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
    // Debug: Log the router stack to verify routes are registered
    const routes = authRoutes;
    if (routes && routes.stack) {
      console.log('🔍 Auth Router Stack Debug:');
      routes.stack.forEach((layer, index) => {
        if (layer.route) {
          const methods = Object.keys(layer.route.methods);
          console.log(`  ${index}: ${methods.join(',').toUpperCase()} ${layer.route.path}`);
        }
      });
    }
    return routes;
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
