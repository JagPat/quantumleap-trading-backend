/**
 * Portfolio Module
 * V2 endpoints for portfolio management with AI integration
 */

const express = require('express');
const capitalRoutes = require('./routes/capital');
const holdingsRoutes = require('./routes/holdings');

module.exports = {
  name: 'portfolio',
  version: '2.0.0',
  description: 'Portfolio management V2 with capital tracking and AI integration',
  dependencies: ['database', 'logger'],
  provides: ['portfolio-capital', 'portfolio-holdings'],

  /**
   * Initialize the Portfolio V2 module
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('[PortfolioModule] Setting up V2 portfolio routes');

      // Create router
      const router = express.Router();
      
      // Mount routes
      router.use('/', capitalRoutes);
      router.use('/', holdingsRoutes);

      // Register at V2 endpoint
      app.use('/api/v2/portfolio', router);

      this.logger.info('[PortfolioModule] V2 routes registered:');
      this.logger.info('  - GET  /api/v2/portfolio/capital');
      this.logger.info('  - GET  /api/v2/portfolio/capital/history');
      this.logger.info('  - POST /api/v2/portfolio/capital/refresh');
      this.logger.info('  - GET  /api/v2/portfolio/holdings-with-actions');
      this.logger.info('  - GET  /api/v2/portfolio/holdings/:symbol/recommendation');

      return true;
    } catch (error) {
      console.error('[PortfolioModule] Initialization error:', error);
      throw error;
    }
  }
};

