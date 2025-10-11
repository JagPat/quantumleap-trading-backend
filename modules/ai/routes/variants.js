/**
 * Strategy Variant Management Routes
 * A/B testing and strategy evolution endpoints
 */

const express = require('express');
const router = express.Router();
const { getStrategyVariantManager } = require('../services/strategyVariantManager');

/**
 * POST /api/v2/ai/variants/create
 * Create a new strategy variant for A/B testing
 */
router.post('/create', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { baseStrategyId, variantName, variantConfig, testGroup } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!baseStrategyId || !variantName || !variantConfig || !testGroup) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: baseStrategyId, variantName, variantConfig, testGroup'
      });
    }

    const variantManager = getStrategyVariantManager();
    
    const variantId = await variantManager.createVariant(baseStrategyId, {
      variantName,
      config: variantConfig,
      testGroup
    });

    res.json({
      success: true,
      message: 'Strategy variant created',
      variantId,
      testGroup
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error creating variant:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to create variant'
    });
  }
});

/**
 * GET /api/v2/ai/variants/:testName/performance
 * Compare performance of all variants in a test
 */
router.get('/:testName/performance', async (req, res) => {
  try {
    const { testName } = req.params;
    const { metricType = 'pnl' } = req.query;

    const variantManager = getStrategyVariantManager();
    
    // Get active variants
    const variants = await variantManager.getActiveVariants(testName);

    if (variants.length === 0) {
      return res.json({
        success: true,
        testName,
        message: 'No active variants found for this test'
      });
    }

    // Compare performance
    const variantIds = variants.map(v => v.id);
    const comparison = await variantManager.compareVariantPerformance(variantIds, metricType);

    res.json({
      success: true,
      testName,
      comparison
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error comparing performance:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to compare variant performance'
    });
  }
});

/**
 * POST /api/v2/ai/variants/:testName/conclude
 * Conclude A/B test and promote winning variant
 */
router.post('/:testName/conclude', async (req, res) => {
  try {
    const { testName } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const variantManager = getStrategyVariantManager();
    
    const result = await variantManager.promoteWinningVariant(testName);

    if (result.error) {
      return res.status(400).json({
        success: false,
        message: result.error
      });
    }

    res.json({
      success: true,
      message: 'Test concluded and winner promoted',
      result
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error concluding test:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to conclude test'
    });
  }
});

/**
 * GET /api/v2/ai/variants/:testName/active
 * Get all active variants for a test
 */
router.get('/:testName/active', async (req, res) => {
  try {
    const { testName } = req.params;

    const variantManager = getStrategyVariantManager();
    const variants = await variantManager.getActiveVariants(testName);

    res.json({
      success: true,
      testName,
      variants,
      count: variants.length
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error fetching active variants:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch active variants'
    });
  }
});

/**
 * POST /api/v2/ai/variants/:variantId/archive
 * Archive an underperforming variant
 */
router.post('/:variantId/archive', async (req, res) => {
  try {
    const { variantId } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const variantManager = getStrategyVariantManager();
    await variantManager.archiveUnderperformingVariant(parseInt(variantId));

    res.json({
      success: true,
      message: 'Variant archived',
      variantId: parseInt(variantId)
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error archiving variant:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to archive variant'
    });
  }
});

/**
 * GET /api/v2/ai/variants/assignment/:testName
 * Get user's assigned variant for a test
 */
router.get('/assignment/:testName', async (req, res) => {
  try {
    const { testName } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const variantManager = getStrategyVariantManager();
    const assignment = await variantManager.assignUserToTestGroup(userId, testName);

    res.json({
      success: true,
      assignment
    });

  } catch (error) {
    console.error('[VariantsRoutes] Error getting assignment:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to get test assignment'
    });
  }
});

module.exports = router;

