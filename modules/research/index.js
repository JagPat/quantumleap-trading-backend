/**
 * Research Module
 * V2 endpoints for research aggregation and analysis
 */

const express = require('express');
const researchRoutes = require('./routes');

module.exports = {
  name: 'research',
  version: '2.0.0',
  description: 'Research aggregation V2 with AI-driven insights',
  dependencies: ['database', 'logger'],
  provides: ['research-aggregation', 'research-cache'],

  /**
   * Initialize the Research V2 module
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('[ResearchModule] Setting up V2 research routes');

      // Create router
      const router = express.Router();
      
      // Mount routes
      router.use('/', researchRoutes);

      // Register at V2 endpoint
      app.use('/api/v2/research', router);

      this.logger.info('[ResearchModule] V2 routes registered:');
      this.logger.info('  - GET  /api/v2/research/:symbol');
      this.logger.info('  - GET  /api/v2/research/:symbol/summary');
      this.logger.info('  - POST /api/v2/research/clear-cache');

      return true;
    } catch (error) {
      console.error('[ResearchModule] Initialization error:', error);
      throw error;
    }
  }
};

