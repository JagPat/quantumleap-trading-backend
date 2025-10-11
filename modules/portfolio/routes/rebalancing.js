const express = require('express');
const router = express.Router();
const { getRebalancingService } = require('../services/rebalancingService');

/**
 * Portfolio Rebalancing Routes
 * Handles portfolio rebalancing analysis, execution, and history
 */

/**
 * POST /api/v2/portfolio/rebalancing/analyze
 * Analyze portfolio for rebalancing opportunities
 * 
 * Body:
 * {
 *   holdings: Array<{
 *     symbol: string,
 *     quantity: number,
 *     currentValue: number,
 *     targetWeight: number,
 *     avgPrice: number,
 *     purchaseDate: string
 *   }>
 * }
 */
router.post('/analyze', async (req, res) => {
  try {
    const { holdings } = req.body;
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    if (!holdings || !Array.isArray(holdings) || holdings.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Holdings array is required'
      });
    }

    console.log('[RebalancingRoutes] Analyzing portfolio:', {
      userId,
      holdingsCount: holdings.length
    });

    const rebalancingService = getRebalancingService();
    const analysis = await rebalancingService.analyzePortfolio(userId, holdings);

    return res.status(200).json({
      success: true,
      data: {
        analysis: {
          needsRebalancing: analysis.needsRebalancing,
          maxDrift: analysis.maxDrift,
          totalValue: analysis.totalValue,
          allocation: analysis.allocation
        },
        proposedTrades: analysis.proposedTrades,
        taxImpact: analysis.taxImpact
      }
    });
  } catch (error) {
    console.error('[RebalancingRoutes] Analysis error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to analyze portfolio',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * POST /api/v2/portfolio/rebalancing/execute
 * Execute rebalancing trades
 * 
 * Body:
 * {
 *   trades: Array<{
 *     symbol: string,
 *     action: 'BUY' | 'SELL',
 *     quantity: number,
 *     price: number,
 *     estimatedValue: number
 *   }>,
 *   taxOptimization: boolean
 * }
 */
router.post('/execute', async (req, res) => {
  try {
    const { trades, taxOptimization = true } = req.body;
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];

    if (!userId || !configId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication and broker config required'
      });
    }

    if (!trades || !Array.isArray(trades) || trades.length === 0) {
      return res.status(400).json({
        success: false,
        error: 'Trades array is required'
      });
    }

    console.log('[RebalancingRoutes] Executing rebalancing:', {
      userId,
      configId,
      tradesCount: trades.length,
      taxOptimization
    });

    const rebalancingService = getRebalancingService();
    const result = await rebalancingService.executeRebalancing(
      userId,
      configId,
      trades
    );

    return res.status(200).json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('[RebalancingRoutes] Execution error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to execute rebalancing',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * GET /api/v2/portfolio/rebalancing/history
 * Get rebalancing history
 */
router.get('/history', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const limit = parseInt(req.query.limit) || 10;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    const rebalancingService = getRebalancingService();
    const history = await rebalancingService.getHistory(userId, limit);

    return res.status(200).json({
      success: true,
      data: {
        history
      }
    });
  } catch (error) {
    console.error('[RebalancingRoutes] Get history error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to fetch rebalancing history',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * GET /api/v2/portfolio/rebalancing/settings
 * Get user's rebalancing settings
 */
router.get('/settings', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    const rebalancingService = getRebalancingService();
    const settings = await rebalancingService.getSettings(userId);

    return res.status(200).json({
      success: true,
      data: {
        settings
      }
    });
  } catch (error) {
    console.error('[RebalancingRoutes] Get settings error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to fetch settings',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * PUT /api/v2/portfolio/rebalancing/settings
 * Update user's rebalancing settings
 * 
 * Body:
 * {
 *   rebalancingEnabled: boolean,
 *   driftThreshold: number,
 *   taxOptimization: boolean,
 *   autoRebalanceFrequency: 'daily' | 'weekly' | 'monthly' | 'quarterly'
 * }
 */
router.put('/settings', async (req, res) => {
  try {
    const settings = req.body;
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required'
      });
    }

    const rebalancingService = getRebalancingService();
    await rebalancingService.updateSettings(userId, settings);

    return res.status(200).json({
      success: true,
      message: 'Rebalancing settings updated successfully'
    });
  } catch (error) {
    console.error('[RebalancingRoutes] Update settings error:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to update settings',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

module.exports = router;

