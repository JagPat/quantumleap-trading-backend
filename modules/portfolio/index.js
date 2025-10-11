/**
 * Portfolio Module
 * V2 endpoints for portfolio management with AI integration
 */

const express = require('express');
const capitalRoutes = require('./routes/capital');
const holdingsRoutes = require('./routes/holdings');
const rebalancingRoutes = require('./routes/rebalancing');

module.exports = {
  name: 'portfolio',
  version: '2.0.0',
  description: 'Portfolio management V2 with capital tracking, rebalancing, and AI integration',
  dependencies: ['database', 'logger'],
  provides: ['portfolio-capital', 'portfolio-holdings', 'portfolio-rebalancing'],

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
      router.use('/rebalancing', rebalancingRoutes);

      // Register at V2 endpoint
      app.use('/api/v2/portfolio', router);

      this.logger.info('[PortfolioModule] V2 routes registered:');
      this.logger.info('  - GET  /api/v2/portfolio/capital');
      this.logger.info('  - GET  /api/v2/portfolio/capital/history');
      this.logger.info('  - POST /api/v2/portfolio/capital/refresh');
      this.logger.info('  - GET  /api/v2/portfolio/holdings-with-actions');
      this.logger.info('  - GET  /api/v2/portfolio/holdings/:symbol/recommendation');
      this.logger.info('  - POST /api/v2/portfolio/rebalancing/analyze');
      this.logger.info('  - POST /api/v2/portfolio/rebalancing/execute');
      this.logger.info('  - GET  /api/v2/portfolio/rebalancing/history');
      this.logger.info('  - GET  /api/v2/portfolio/rebalancing/settings');
      this.logger.info('  - PUT  /api/v2/portfolio/rebalancing/settings');

      return true;
    } catch (error) {
      console.error('[PortfolioModule] Initialization error:', error);
      throw error;
    }
  }
};

