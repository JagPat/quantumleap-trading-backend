/**
 * Trading Module
 * V2 endpoints for trading operations including rotational trading
 */

const express = require('express');
const rotationRoutes = require('./routes/rotation');
const executionRoutes = require('./routes/execution');

module.exports = {
  name: 'trading',
  version: '2.0.0',
  description: 'Trading operations V2 with rotational trading and execution',
  dependencies: ['database', 'logger'],
  provides: ['trading-rotation', 'trade-execution'],

  /**
   * Initialize the Trading V2 module
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('[TradingModule] Setting up V2 trading routes');

      // Create router
      const router = express.Router();
      
      // Mount routes
      router.use('/', rotationRoutes);
      router.use('/', executionRoutes);

      // Register at V2 endpoint
      app.use('/api/v2/trading', router);

      this.logger.info('[TradingModule] V2 routes registered:');
      this.logger.info('  - GET    /api/v2/trading/rotation-opportunities');
      this.logger.info('  - POST   /api/v2/trading/enable-rotation');
      this.logger.info('  - POST   /api/v2/trading/execute-rotation');
      this.logger.info('  - GET    /api/v2/trading/active-rotations');
      this.logger.info('  - GET    /api/v2/trading/rotation-history');
      this.logger.info('  - PUT    /api/v2/trading/rotation/:cycleId/status');
      this.logger.info('  - DELETE /api/v2/trading/rotation/:cycleId');
      this.logger.info('  - POST   /api/v2/trading/validate-trade');
      this.logger.info('  - POST   /api/v2/trading/prepare-trade');
      this.logger.info('  - POST   /api/v2/trading/execute-trade/:tradeId');
      this.logger.info('  - GET    /api/v2/trading/pending-trades');
      this.logger.info('  - DELETE /api/v2/trading/cancel-trade/:tradeId');
      this.logger.info('  - GET    /api/v2/trading/trade-history');

      return true;
    } catch (error) {
      console.error('[TradingModule] Initialization error:', error);
      throw error;
    }
  }
};

