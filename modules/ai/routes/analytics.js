/**
 * AI Analytics Routes
 * Endpoints for tracking and retrieving AI usage metrics
 */

const express = require('express');
const router = express.Router();
const getAIAnalyticsService = require('../services/analyticsService');

/**
 * POST /api/modules/ai/analytics/track
 * Track an AI usage metric
 */
router.post('/track', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { metric, value, metadata } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!metric || !value) {
      return res.status(400).json({
        success: false,
        message: 'Metric type and value are required'
      });
    }

    const analyticsService = getAIAnalyticsService();
    
    // Route to appropriate tracking method
    switch(metric) {
      case 'stock_selection_mode':
        await analyticsService.trackStockSelectionMode(userId, value, metadata);
        break;
      case 'trading_mode':
        await analyticsService.trackTradingMode(userId, value);
        break;
      case 'portfolio_action':
        await analyticsService.trackPortfolioActionAcceptance(
          userId, 
          metadata?.actionType || 'unknown',
          value === 'accepted',
          metadata
        );
        break;
      case 'provider_usage':
        await analyticsService.trackProviderUsage(userId, value, metadata?.taskType || 'unknown', metadata);
        break;
      default:
        console.warn(`[AI/Analytics] Unknown metric type: ${metric}`);
    }

    res.json({
      success: true,
      message: 'Metric tracked successfully'
    });

  } catch (error) {
    console.error('[AI/Analytics] Error tracking metric:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to track metric'
    });
  }
});

/**
 * GET /api/modules/ai/analytics/stats
 * Get aggregated usage statistics
 */
router.get('/stats', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { dateRange } = req.query;

    const analyticsService = getAIAnalyticsService();
    const stats = await analyticsService.getUsageStats(userId, parseInt(dateRange) || 30);

    res.json({
      success: true,
      data: stats
    });

  } catch (error) {
    console.error('[AI/Analytics] Error getting stats:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to get usage stats'
    });
  }
});

/**
 * GET /api/modules/ai/analytics/dashboard
 * Get dashboard metrics summary
 */
router.get('/dashboard', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const analyticsService = getAIAnalyticsService();
    const metrics = await analyticsService.getDashboardMetrics(userId);

    res.json({
      success: true,
      data: metrics
    });

  } catch (error) {
    console.error('[AI/Analytics] Error getting dashboard metrics:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to get dashboard metrics'
    });
  }
});

module.exports = router;

