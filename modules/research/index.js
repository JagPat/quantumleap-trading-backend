/**
 * Research Module
 * V2 endpoints for research aggregation and analysis
 */

const express = require('express');
const researchRoutes = require('./routes');

class ResearchModule {
  constructor() {
    this.router = express.Router();
    this.setupRoutes();
  }

  setupRoutes() {
    console.log('[ResearchModule] Setting up V2 research routes');

    // Mount routes
    this.router.use('/', researchRoutes);

    console.log('[ResearchModule] V2 routes registered:');
    console.log('  - GET  /api/v2/research/:symbol');
    console.log('  - GET  /api/v2/research/:symbol/summary');
    console.log('  - POST /api/v2/research/clear-cache');
  }

  getRouter() {
    return this.router;
  }
}

// Singleton instance
let researchModuleInstance = null;

function getResearchModule() {
  if (!researchModuleInstance) {
    researchModuleInstance = new ResearchModule();
  }
  return researchModuleInstance;
}

module.exports = {
  ResearchModule,
  getResearchModule,
};

