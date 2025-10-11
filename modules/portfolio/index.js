/**
 * Portfolio Module
 * V2 endpoints for portfolio management with AI integration
 */

const express = require('express');
const capitalRoutes = require('./routes/capital');
const holdingsRoutes = require('./routes/holdings');

class PortfolioModule {
  constructor() {
    this.router = express.Router();
    this.setupRoutes();
  }

  setupRoutes() {
    console.log('[PortfolioModule] Setting up V2 portfolio routes');

    // Mount routes
    this.router.use('/', capitalRoutes);
    this.router.use('/', holdingsRoutes);

    console.log('[PortfolioModule] V2 routes registered:');
    console.log('  - GET  /api/v2/portfolio/capital');
    console.log('  - GET  /api/v2/portfolio/capital/history');
    console.log('  - POST /api/v2/portfolio/capital/refresh');
    console.log('  - GET  /api/v2/portfolio/holdings-with-actions');
    console.log('  - GET  /api/v2/portfolio/holdings/:symbol/recommendation');
  }

  getRouter() {
    return this.router;
  }
}

// Singleton instance
let portfolioModuleInstance = null;

function getPortfolioModule() {
  if (!portfolioModuleInstance) {
    portfolioModuleInstance = new PortfolioModule();
  }
  return portfolioModuleInstance;
}

module.exports = {
  PortfolioModule,
  getPortfolioModule,
};

