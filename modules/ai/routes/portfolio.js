/**
 * AI Portfolio Routes
 * Endpoints for portfolio analysis and action suggestions
 */

const express = require('express');
const router = express.Router();
const getPortfolioActionEngine = require('../services/portfolioActionEngine');
const getAIAgentRouter = require('../services/aiAgentRouter');

/**
 * POST /api/modules/ai/portfolio/analyze-actions
 * Analyze portfolio and suggest actions (accumulate/dilute/exit/rebalance)
 */
router.post('/analyze-actions', async (req, res) => {
  try {
    const { portfolio_data, goal } = req.body;
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!portfolio_data) {
      return res.status(400).json({
        success: false,
        message: 'Portfolio data required'
      });
    }

    console.log(`[AI/Portfolio] Analyzing portfolio actions for user: ${userId}`);

    const portfolioEngine = getPortfolioActionEngine();
    const result = await portfolioEngine.analyzeAndSuggestActions(portfolio_data, goal);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Portfolio] Error analyzing actions:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to analyze portfolio actions'
    });
  }
});

/**
 * POST /api/modules/ai/portfolio/rebalance-plan
 * Generate complete rebalance plan
 */
router.post('/rebalance-plan', async (req, res) => {
  try {
    const { portfolio_data, goal } = req.body;
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Portfolio] Generating rebalance plan for user: ${userId}`);

    const portfolioEngine = getPortfolioActionEngine();
    const result = await portfolioEngine.generateRebalancePlan(portfolio_data, goal, userId);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Portfolio] Error generating rebalance plan:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to generate rebalance plan'
    });
  }
});

/**
 * GET /api/modules/ai/portfolio/optimization-score
 * Calculate portfolio optimization score (0-100)
 */
router.get('/optimization-score', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    
    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    // Fetch current portfolio
    const portfolioData = req.body.portfolio_data || req.query.portfolio_data;
    
    if (!portfolioData) {
      return res.status(400).json({
        success: false,
        message: 'Portfolio data required'
      });
    }

    console.log(`[AI/Portfolio] Calculating optimization score for user: ${userId}`);

    const portfolioEngine = getPortfolioActionEngine();
    const result = await portfolioEngine.calculateOptimizationScore(portfolioData);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Portfolio] Error calculating optimization score:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to calculate optimization score'
    });
  }
});

module.exports = router;

