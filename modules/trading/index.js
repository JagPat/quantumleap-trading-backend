/**
 * Trading Module
 * V2 endpoints for trading operations including rotational trading
 */

const express = require('express');
const rotationRoutes = require('./routes/rotation');

class TradingModule {
  constructor() {
    this.router = express.Router();
    this.setupRoutes();
  }

  setupRoutes() {
    console.log('[TradingModule] Setting up V2 trading routes');

    // Mount routes
    this.router.use('/', rotationRoutes);

    console.log('[TradingModule] V2 routes registered:');
    console.log('  - GET    /api/v2/trading/rotation-opportunities');
    console.log('  - POST   /api/v2/trading/enable-rotation');
    console.log('  - POST   /api/v2/trading/execute-rotation');
    console.log('  - GET    /api/v2/trading/active-rotations');
    console.log('  - GET    /api/v2/trading/rotation-history');
    console.log('  - PUT    /api/v2/trading/rotation/:cycleId/status');
    console.log('  - DELETE /api/v2/trading/rotation/:cycleId');
  }

  getRouter() {
    return this.router;
  }
}

// Singleton instance
let tradingModuleInstance = null;

function getTradingModule() {
  if (!tradingModuleInstance) {
    tradingModuleInstance = new TradingModule();
  }
  return tradingModuleInstance;
}

module.exports = {
  TradingModule,
  getTradingModule,
};

