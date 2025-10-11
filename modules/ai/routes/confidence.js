/**
 * Confidence Management Routes
 * Manual review interface for AI confidence adjustments
 */

const express = require('express');
const router = express.Router();
const { getConfidenceManager } = require('../services/confidenceManager');

/**
 * GET /api/v2/ai/confidence/pending-reviews
 * Get decisions flagged for manual confidence review
 */
router.get('/pending-reviews', async (req, res) => {
  try {
    const { limit = 20 } = req.query;

    const confidenceManager = getConfidenceManager();
    const pendingReviews = await confidenceManager.getPendingReviews(parseInt(limit));

    res.json({
      success: true,
      reviews: pendingReviews,
      count: pendingReviews.length
    });

  } catch (error) {
    console.error('[ConfidenceRoutes] Error fetching pending reviews:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch pending reviews'
    });
  }
});

/**
 * POST /api/v2/ai/confidence/:decisionId/approve-adjustment
 * Approve an auto-suggested confidence adjustment
 */
router.post('/:decisionId/approve-adjustment', async (req, res) => {
  try {
    const { decisionId } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { proposedConfidence, reason } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!proposedConfidence) {
      return res.status(400).json({
        success: false,
        message: 'Proposed confidence value is required'
      });
    }

    const confidenceManager = getConfidenceManager();
    
    await confidenceManager.applyConfidenceAdjustment(
      parseInt(decisionId),
      parseFloat(proposedConfidence),
      reason || 'Manual review approved',
      userId
    );

    res.json({
      success: true,
      message: 'Confidence adjustment approved',
      decisionId: parseInt(decisionId),
      newConfidence: parseFloat(proposedConfidence)
    });

  } catch (error) {
    console.error('[ConfidenceRoutes] Error approving adjustment:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to approve adjustment'
    });
  }
});

/**
 * POST /api/v2/ai/confidence/:decisionId/manual-adjust
 * Manually adjust confidence score
 */
router.post('/:decisionId/manual-adjust', async (req, res) => {
  try {
    const { decisionId } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { newConfidence, reason } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!newConfidence || newConfidence < 0 || newConfidence > 1) {
      return res.status(400).json({
        success: false,
        message: 'Valid confidence value (0-1) is required'
      });
    }

    if (!reason) {
      return res.status(400).json({
        success: false,
        message: 'Reason for adjustment is required'
      });
    }

    const confidenceManager = getConfidenceManager();
    
    await confidenceManager.applyConfidenceAdjustment(
      parseInt(decisionId),
      parseFloat(newConfidence),
      `Manual adjustment: ${reason}`,
      userId
    );

    res.json({
      success: true,
      message: 'Confidence manually adjusted',
      decisionId: parseInt(decisionId),
      newConfidence: parseFloat(newConfidence)
    });

  } catch (error) {
    console.error('[ConfidenceRoutes] Error manual adjustment:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to adjust confidence'
    });
  }
});

/**
 * GET /api/v2/ai/confidence/:decisionId/history
 * Get confidence adjustment history for a decision
 */
router.get('/:decisionId/history', async (req, res) => {
  try {
    const { decisionId } = req.params;

    const confidenceManager = getConfidenceManager();
    const history = await confidenceManager.getConfidenceHistory(parseInt(decisionId));

    res.json({
      success: true,
      decisionId: parseInt(decisionId),
      history,
      count: history.length
    });

  } catch (error) {
    console.error('[ConfidenceRoutes] Error fetching history:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch confidence history'
    });
  }
});

module.exports = router;

