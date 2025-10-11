/**
 * AI Learning Routes
 * Endpoints for accessing learning data, execution history, and performance insights
 */

const express = require('express');
const router = express.Router();
const { getStrategyExecutionTracker } = require('../services/strategyExecutionTracker');
const { getUserOverrideTracker } = require('../services/userOverrideTracker');
const { getConfidenceManager } = require('../services/confidenceManager');
const { getBenchmarkService } = require('../services/benchmarkService');
const { getStrategyVariantManager } = require('../services/strategyVariantManager');

/**
 * GET /api/v2/ai/learning/execution-history
 * Get strategy execution history for a user
 */
router.get('/execution-history', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { strategyId, limit = 50 } = req.query;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const executionTracker = getStrategyExecutionTracker();

    let history;
    if (strategyId) {
      history = await executionTracker.getExecutionHistory(parseInt(strategyId), parseInt(limit));
    } else {
      history = await executionTracker.getActiveExecutions(userId);
    }

    res.json({
      success: true,
      executions: history,
      count: history.length
    });

  } catch (error) {
    console.error('[LearningRoutes] Error fetching execution history:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch execution history'
    });
  }
});

/**
 * GET /api/v2/ai/learning/override-analysis
 * Analyze user override patterns and performance
 */
router.get('/override-analysis', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { days = 30 } = req.query;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const overrideTracker = getUserOverrideTracker();

    // Get pattern analysis
    const pattern = await overrideTracker.getUserOverridePattern(userId);
    
    // Get performance comparison
    const comparison = await overrideTracker.getOverridePerformanceComparison(
      userId, 
      parseInt(days)
    );

    // Get recent overrides
    const recent = await overrideTracker.getRecentOverrides(userId, 10);

    res.json({
      success: true,
      analysis: {
        pattern,
        comparison,
        recentOverrides: recent
      }
    });

  } catch (error) {
    console.error('[LearningRoutes] Error analyzing overrides:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to analyze overrides'
    });
  }
});

/**
 * GET /api/v2/ai/learning/confidence-evolution
 * Track AI confidence evolution over time
 */
router.get('/confidence-evolution', async (req, res) => {
  try {
    const { decisionId } = req.query;

    if (!decisionId) {
      return res.status(400).json({
        success: false,
        message: 'Decision ID is required'
      });
    }

    const confidenceManager = getConfidenceManager();
    const history = await confidenceManager.getConfidenceHistory(parseInt(decisionId));

    res.json({
      success: true,
      decisionId: parseInt(decisionId),
      history,
      count: history.length
    });

  } catch (error) {
    console.error('[LearningRoutes] Error fetching confidence evolution:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch confidence evolution'
    });
  }
});

/**
 * GET /api/v2/ai/learning/benchmark-comparison
 * Compare strategy performance to market benchmarks
 */
router.get('/benchmark-comparison', async (req, res) => {
  try {
    const { executionId, benchmark = 'NIFTY50' } = req.query;

    if (!executionId) {
      return res.status(400).json({
        success: false,
        message: 'Execution ID is required'
      });
    }

    const benchmarkService = getBenchmarkService();
    
    // Get comparison
    const comparison = await benchmarkService.compareStrategyToBenchmark(
      parseInt(executionId),
      benchmark
    );

    // Get alpha/beta
    const alphaBeta = await benchmarkService.getAlphaBeta(
      parseInt(executionId),
      benchmark
    );

    res.json({
      success: true,
      executionId: parseInt(executionId),
      benchmark,
      comparison,
      alphaBeta
    });

  } catch (error) {
    console.error('[LearningRoutes] Error comparing to benchmark:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to compare to benchmark'
    });
  }
});

/**
 * GET /api/v2/ai/learning/variant-performance
 * Get A/B test variant performance
 */
router.get('/variant-performance', async (req, res) => {
  try {
    const { testName } = req.query;

    if (!testName) {
      return res.status(400).json({
        success: false,
        message: 'Test name is required'
      });
    }

    const variantManager = getStrategyVariantManager();
    
    // Get active variants
    const variants = await variantManager.getActiveVariants(testName);
    
    if (variants.length === 0) {
      return res.json({
        success: true,
        testName,
        message: 'No active variants found'
      });
    }

    // Compare performance
    const variantIds = variants.map(v => v.id);
    const comparison = await variantManager.compareVariantPerformance(variantIds, 'pnl');

    res.json({
      success: true,
      testName,
      variants,
      comparison
    });

  } catch (error) {
    console.error('[LearningRoutes] Error fetching variant performance:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch variant performance'
    });
  }
});

/**
 * GET /api/v2/ai/learning/attribution/:executionId
 * Get decision attribution for a strategy execution
 */
router.get('/attribution/:executionId', async (req, res) => {
  try {
    const { executionId } = req.params;

    const executionTracker = getStrategyExecutionTracker();
    
    // Get execution details
    const history = await executionTracker.getExecutionHistory(null, 1);
    const execution = history.find(e => e.id === parseInt(executionId));

    if (!execution) {
      return res.status(404).json({
        success: false,
        message: 'Execution not found'
      });
    }

    // Get performance metrics
    const performance = execution.strategy_id 
      ? await executionTracker.getExecutionPerformance(execution.strategy_id)
      : null;

    res.json({
      success: true,
      execution,
      attribution: execution.attribution_metadata,
      performance
    });

  } catch (error) {
    console.error('[LearningRoutes] Error fetching attribution:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch attribution'
    });
  }
});

/**
 * GET /api/v2/ai/learning/summary
 * Get overall learning summary for a user
 */
router.get('/summary', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { days = 30 } = req.query;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const executionTracker = getStrategyExecutionTracker();
    const overrideTracker = getUserOverrideTracker();

    // Get execution summary
    const executions = await executionTracker.getActiveExecutions(userId);
    
    // Get override summary
    const overrideComparison = await overrideTracker.getOverridePerformanceComparison(
      userId,
      parseInt(days)
    );

    res.json({
      success: true,
      period: `Last ${days} days`,
      summary: {
        activeExecutions: executions.length,
        overrideMetrics: overrideComparison
      }
    });

  } catch (error) {
    console.error('[LearningRoutes] Error fetching summary:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch summary'
    });
  }
});

module.exports = router;

