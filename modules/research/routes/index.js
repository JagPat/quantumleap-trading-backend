/**
 * Research Routes
 * V2 API endpoints for research data and summaries
 */

const express = require('express');
const router = express.Router();
const { getResearchAggregator } = require('../services/researchAggregator');

/**
 * GET /api/v2/research/:symbol
 * Get comprehensive research for a symbol
 */
router.get('/:symbol', async (req, res) => {
  try {
    const { symbol } = req.params;
    const days = parseInt(req.query.days) || 7;

    console.log('[ResearchRoutes] Fetching comprehensive research for', symbol);

    const researchAggregator = getResearchAggregator();
    const research = await researchAggregator.getComprehensiveResearch(symbol, days);

    return res.status(200).json({
      success: true,
      data: research,
    });

  } catch (error) {
    console.error('[ResearchRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch research data',
    });
  }
});

/**
 * GET /api/v2/research/:symbol/summary
 * Get LLM-generated summary only (faster)
 */
router.get('/:symbol/summary', async (req, res) => {
  try {
    const { symbol } = req.params;

    console.log('[ResearchRoutes] Fetching summary for', symbol);

    const researchAggregator = getResearchAggregator();
    const summary = await researchAggregator.getSummaryOnly(symbol);

    return res.status(200).json({
      success: true,
      data: summary,
    });

  } catch (error) {
    console.error('[ResearchRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch research summary',
    });
  }
});

/**
 * POST /api/v2/research/clear-cache
 * Clear expired research cache
 */
router.post('/clear-cache', async (req, res) => {
  try {
    const researchAggregator = getResearchAggregator();
    await researchAggregator.clearExpiredCache();

    return res.status(200).json({
      success: true,
      message: 'Cache cleared successfully',
    });

  } catch (error) {
    console.error('[ResearchRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to clear cache',
    });
  }
});

module.exports = router;

