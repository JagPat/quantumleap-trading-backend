const contactRoutes = require('./routes');
const contactService = require('./services');

module.exports = {
  name: 'contacts',
  version: '1.0.0',
  description: 'Contact management module with groups, tags, and import/export',
  dependencies: ['database', 'eventBus', 'logger'],
  provides: ['contact-management', 'contact-groups', 'contact-tags', 'contact-import-export'],
  
  routes: contactRoutes,
  service: contactService,

  /**
   * Initialize the Contacts module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing Contacts module...');
      
      // Register routes
      if (this.routes) {
        app.use('/api/modules/contacts', this.routes);
        this.logger.info('Contacts module routes registered at /api/modules/contacts');
      }
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('Contacts module initialized successfully');
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
      this.logger.error(`Contacts module error: ${error.message}`, error);
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
        this.logger.info('Contacts module started');
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
        this.logger.info('Contacts module stopped');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
};
