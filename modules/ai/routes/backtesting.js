const express = require('express');
const router = express.Router();
const { getBacktestingService } = require('../services/backtestingService');

/**
 * POST /api/v2/ai/backtesting/run
 * Run backtest for a strategy
 */
router.post('/run', async (req, res) => {
  try {
    const { strategyId, timeframe = '1Y', days = 365 } = req.body;
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    if (!strategyId) {
      return res.status(400).json({
        success: false,
        error: 'Strategy ID is required'
      });
    }

    const backtestingService = getBacktestingService();
    const result = await backtestingService.runBacktest(strategyId, timeframe, days);

    return res.status(200).json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('[BacktestingRoutes] Run error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to run backtest',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * POST /api/v2/ai/backtesting/compare
 * Compare multiple strategies
 */
router.post('/compare', async (req, res) => {
  try {
    const { strategyIds, timeframe = '1Y' } = req.body;
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    if (!strategyIds || !Array.isArray(strategyIds)) {
      return res.status(400).json({
        success: false,
        error: 'Strategy IDs array is required'
      });
    }

    const backtestingService = getBacktestingService();
    const comparisons = await backtestingService.compareStrategies(strategyIds, timeframe);

    return res.status(200).json({
      success: true,
      data: { comparisons }
    });
  } catch (error) {
    console.error('[BacktestingRoutes] Compare error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to compare strategies',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;

