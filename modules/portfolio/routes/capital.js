/**
 * Capital Routes
 * V2 API endpoints for capital and liquidity data
 */

const express = require('express');
const router = express.Router();
const { getCapitalService } = require('../services/capitalService');

/**
 * GET /api/v2/portfolio/capital
 * Get capital breakdown for user
 */
router.get('/capital', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    console.log('[CapitalRoutes] Fetching capital for user:', userId);

    const capitalService = getCapitalService();
    
    // Get broker client if available (optional)
    let brokerClient = null;
    if (req.brokerClient) {
      brokerClient = req.brokerClient;
    }

    const capitalData = await capitalService.getCapitalBreakdown(
      userId,
      configId,
      brokerClient
    );

    return res.status(200).json({
      success: true,
      data: capitalData,
    });

  } catch (error) {
    console.error('[CapitalRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch capital data',
    });
  }
});

/**
 * GET /api/v2/portfolio/capital/history
 * Get historical capital snapshots
 */
router.get('/capital/history', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const days = parseInt(req.query.days) || 30;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const capitalService = getCapitalService();
    const history = await capitalService.getCapitalHistory(userId, configId, days);

    return res.status(200).json({
      success: true,
      data: {
        history,
        count: history.length,
        days,
      },
    });

  } catch (error) {
    console.error('[CapitalRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch capital history',
    });
  }
});

/**
 * POST /api/v2/portfolio/capital/refresh
 * Force refresh capital data (clear cache)
 */
router.post('/capital/refresh', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const capitalService = getCapitalService();
    
    // Clear cache
    capitalService.clearCache(userId, configId);

    // Get fresh data
    const capitalData = await capitalService.getCapitalBreakdown(
      userId,
      configId,
      req.brokerClient
    );

    return res.status(200).json({
      success: true,
      data: capitalData,
      message: 'Capital data refreshed',
    });

  } catch (error) {
    console.error('[CapitalRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to refresh capital data',
    });
  }
});

module.exports = router;

