const systemRoutes = require('./routes');
const systemService = require('./services');

module.exports = {
  name: 'system',
  version: '1.0.0',
  description: 'System monitoring and management module',
  dependencies: ['database', 'eventBus', 'logger'],
  provides: ['system-monitoring', 'performance-metrics', 'module-management'],
  
  routes: systemRoutes,

  /**
   * Get routes for dynamic mounting
   * Required by module loader for route registration
   * @returns {Router} Express router
   */
  getRoutes() {
    return systemRoutes;
  },
  service: systemService,

  /**
   * Initialize the System module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing System module...');
      
      // Register routes
      if (this.routes) {
        app.use('/api/modules/system', this.routes);
        this.logger.info('System module routes registered at /api/modules/system');
      }
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('System module initialized successfully');
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
      this.logger.error(`System module error: ${error.message}`, error);
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
        this.logger.info('System module started');
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
        this.logger.info('System module stopped');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
};
