const analyticsRoutes = require('./routes');
const analyticsService = require('./services');

module.exports = {
  name: 'analytics',
  version: '1.0.0',
  description: 'Analytics and reporting module with performance metrics and insights',
  dependencies: ['database', 'eventBus', 'logger'],
  provides: ['data-analytics', 'performance-metrics', 'user-behavior', 'custom-reports'],
  
  routes: analyticsRoutes,
  service: analyticsService,

  /**
   * Initialize the Analytics module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing Analytics module...');
      
      // Register routes
      if (this.routes) {
        app.use('/api/modules/analytics', this.routes);
        this.logger.info('Analytics module routes registered at /api/modules/analytics');
      }
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('Analytics module initialized successfully');
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  },

  /**
   * Get module health status
   * @returns {Object} Health information
   */
  async health() {
    try {
      const health = await this.service.healthCheck();
      return {
        status: 'healthy',
        module: this.name,
        version: this.version,
        timestamp: new Date().toISOString(),
        ...health
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        module: this.name,
        version: this.version,
        timestamp: new Date().toISOString(),
        error: error.message
      };
    }
  },

  /**
   * Handle module errors
   * @param {Error} error - Error object
   */
  handleError(error) {
    this.status = 'error';
    this.error = error.message;
    if (this.logger) {
      this.logger.error(`Analytics module error: ${error.message}`, error);
    }
  },

  /**
   * Start the module
   */
  async start() {
    try {
      this.status = 'started';
      this.startedAt = new Date();
      if (this.logger) {
        this.logger.info('Analytics module started');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  },

  /**
   * Stop the module
   */
  async stop() {
    try {
      this.status = 'stopped';
      this.stoppedAt = new Date();
      if (this.logger) {
        this.logger.info('Analytics module stopped');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
};
