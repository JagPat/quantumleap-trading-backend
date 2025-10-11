/**
 * Holdings Routes
 * V2 API endpoints for holdings with AI recommendations
 */

const express = require('express');
const router = express.Router();
const { getPortfolioReviewEngine } = require('../../ai/services/portfolioReviewEngine');
const { query } = require('../../../core/database');

/**
 * GET /api/v2/portfolio/holdings-with-actions
 * Get holdings with AI recommendations
 */
router.get('/holdings-with-actions', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    console.log('[HoldingsRoutes] Fetching holdings with actions for user:', userId);

    // Get portfolio data
    const portfolioResult = await query(
      `SELECT data FROM portfolio_snapshots 
       WHERE user_id = $1 AND config_id = $2 
       ORDER BY created_at DESC LIMIT 1`,
      [userId, configId]
    );

    if (portfolioResult.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No portfolio data found',
      });
    }

    const portfolioData = portfolioResult.rows[0].data;

    // Get AI recommendations
    const reviewEngine = getPortfolioReviewEngine();
    const holdingsWithActions = await reviewEngine.reviewPortfolio(portfolioData);

    return res.status(200).json({
      success: true,
      data: {
        holdings: holdingsWithActions,
        actions: holdingsWithActions
          .filter(h => h.ai_recommendation?.type !== 'HOLD')
          .map(h => ({
            symbol: h.symbol || h.tradingsymbol,
            ...h.ai_recommendation,
          })),
        summary: {
          total_holdings: holdingsWithActions.length,
          actions_count: holdingsWithActions.filter(h => h.ai_recommendation?.type !== 'HOLD').length,
          health_score: reviewEngine.calculateHealthScore(
            portfolioData,
            holdingsWithActions.map(h => h.ai_recommendation)
          ),
        },
      },
    });

  } catch (error) {
    console.error('[HoldingsRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch holdings with actions',
    });
  }
});

/**
 * GET /api/v2/portfolio/holdings/:symbol/recommendation
 * Get AI recommendation for a specific holding
 */
router.get('/holdings/:symbol/recommendation', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const symbol = req.params.symbol;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    console.log('[HoldingsRoutes] Getting recommendation for symbol:', symbol);

    // Get portfolio data
    const portfolioResult = await query(
      `SELECT data FROM portfolio_snapshots 
       WHERE user_id = $1 AND config_id = $2 
       ORDER BY created_at DESC LIMIT 1`,
      [userId, configId]
    );

    if (portfolioResult.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No portfolio data found',
      });
    }

    const portfolioData = portfolioResult.rows[0].data;

    // Find holding
    const holding = portfolioData.holdings?.find(h => 
      (h.symbol || h.tradingsymbol) === symbol
    );

    if (!holding) {
      return res.status(404).json({
        success: false,
        error: `Holding ${symbol} not found`,
      });
    }

    // Get recommendation
    const reviewEngine = getPortfolioReviewEngine();
    const recommendation = await reviewEngine.getHoldingRecommendation(holding, portfolioData);

    return res.status(200).json({
      success: true,
      data: {
        symbol,
        holding,
        recommendation,
      },
    });

  } catch (error) {
    console.error('[HoldingsRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to get holding recommendation',
    });
  }
});

module.exports = router;

