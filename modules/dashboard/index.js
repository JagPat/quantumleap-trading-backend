const dashboardRoutes = require('./routes');
const dashboardService = require('./services');

module.exports = {
  name: 'dashboard',
  version: '1.0.0',
  description: 'Dashboard analytics and overview module',
  dependencies: ['database', 'eventBus', 'logger'],
  provides: ['dashboard-analytics', 'performance-metrics', 'user-insights'],
  
  routes: dashboardRoutes,

  /**
   * Get routes for dynamic mounting
   * Required by module loader for route registration
   * @returns {Router} Express router
   */
  getRoutes() {
    return dashboardRoutes;
  },
  service: dashboardService,

  /**
   * Initialize the Dashboard module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing Dashboard module...');
      
      // Register routes
      if (this.routes) {
        app.use('/api/modules/dashboard', this.routes);
        this.logger.info('Dashboard module routes registered at /api/modules/dashboard');
      }
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('Dashboard module initialized successfully');
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
      this.logger.error(`Dashboard module error: ${error.message}`, error);
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
        this.logger.info('Dashboard module started');
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
        this.logger.info('Dashboard module stopped');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
};
