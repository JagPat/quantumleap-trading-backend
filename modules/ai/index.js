const aiRoutes = require('./routes');
const aiService = require('./services');

module.exports = {
  name: 'ai',
  version: '1.0.0',
  description: 'AI-powered features module with chat, analysis, and content generation',
  dependencies: ['database', 'eventBus', 'logger'],
  provides: ['ai-chat', 'content-analysis', 'content-generation', 'ai-templates'],
  
  routes: aiRoutes,
  service: aiService,

  /**
   * Initialize the AI module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing AI module...');
      
      // Register routes
      if (this.routes) {
        app.use('/api/modules/ai', this.routes);
        this.logger.info('AI module routes registered at /api/modules/ai');
      }
      
      // Initialize execution engine for strategy automation
      const getExecutionEngine = require('./services/executionEngine');
      this.executionEngine = getExecutionEngine();
      this.logger.info('Strategy execution engine initialized');
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('AI module initialized successfully');
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
      this.logger.error(`AI module error: ${error.message}`, error);
    }
  },

  /**
   * Start the module
   */
  async start() {
    try {
      this.status = 'started';
      this.startedAt = new Date();
      
      // Start execution engine monitoring
      if (this.executionEngine) {
        await this.executionEngine.startMonitoring();
        if (this.logger) {
          this.logger.info('Strategy execution engine monitoring started');
        }
      }
      
      if (this.logger) {
        this.logger.info('AI module started');
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
      // Stop execution engine monitoring
      if (this.executionEngine) {
        this.executionEngine.stopMonitoring();
        if (this.logger) {
          this.logger.info('Strategy execution engine monitoring stopped');
        }
      }
      
      this.status = 'stopped';
      this.stoppedAt = new Date();
      if (this.logger) {
        this.logger.info('AI module stopped');
      }
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
};
