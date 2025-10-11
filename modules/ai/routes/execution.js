/**
 * AI Execution Routes
 * Manages pending trades and trade execution for manual/auto modes
 */

const express = require('express');
const router = express.Router();
const db = require('../../../core/database/connection');
const getExecutionEngine = require('../services/executionEngine');
const getTradingModeManager = require('../services/tradingModeManager');
const { getUserOverrideTracker } = require('../services/userOverrideTracker');

/**
 * GET /api/modules/ai/execution/pending-trades
 * Get all pending trades awaiting user approval (manual mode)
 */
router.get('/pending-trades', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Execution] Fetching pending trades for user: ${userId}`);

    // Fetch trades with status = 'pending_approval'
    const result = await db.query(
      `SELECT 
        st.id,
        st.strategy_id,
        st.user_id,
        st.symbol,
        st.action,
        st.quantity,
        st.price,
        st.status,
        st.created_at,
        st.rationale,
        sa.name as strategy_name
       FROM strategy_trades st
       LEFT JOIN strategy_automations sa ON st.strategy_id = sa.id
       WHERE st.user_id = $1 
         AND st.status = 'pending_approval'
       ORDER BY st.created_at DESC`,
      [userId]
    );

    res.json({
      success: true,
      trades: result.rows,
      count: result.rows.length
    });

  } catch (error) {
    console.error('[AI/Execution] Error fetching pending trades:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch pending trades'
    });
  }
});

/**
 * POST /api/modules/ai/execution/pending-trades/:id/approve
 * Approve a pending trade for execution
 */
router.post('/pending-trades/:id/approve', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const tradeId = req.params.id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Execution] Approving trade ${tradeId} for user: ${userId}`);

    // Verify trade belongs to user
    const tradeCheck = await db.query(
      'SELECT id, user_id FROM strategy_trades WHERE id = $1',
      [tradeId]
    );

    if (tradeCheck.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Trade not found'
      });
    }

    if (tradeCheck.rows[0].user_id !== userId) {
      return res.status(403).json({
        success: false,
        message: 'Unauthorized to approve this trade'
      });
    }

    // Update trade status to approved
    await db.query(
      `UPDATE strategy_trades 
       SET status = 'approved',
           approved_at = NOW(),
           updated_at = NOW()
       WHERE id = $1`,
      [tradeId]
    );

    // Execute the trade
    const executionEngine = getExecutionEngine();
    try {
      await executionEngine.executeTradeById(tradeId);
    } catch (execError) {
      console.warn('[AI/Execution] Trade approved but execution failed:', execError);
      // Still return success for approval, but note execution issue
    }

    res.json({
      success: true,
      message: 'Trade approved and queued for execution'
    });

  } catch (error) {
    console.error('[AI/Execution] Error approving trade:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to approve trade'
    });
  }
});

/**
 * POST /api/modules/ai/execution/pending-trades/:id/reject
 * Reject a pending trade
 */
router.post('/pending-trades/:id/reject', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const tradeId = req.params.id;
    const { reason } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Execution] Rejecting trade ${tradeId} for user: ${userId}`);

    // Verify trade belongs to user and get AI recommendation
    const tradeCheck = await db.query(
      'SELECT id, user_id, symbol, quantity, price, rationale FROM strategy_trades WHERE id = $1',
      [tradeId]
    );

    if (tradeCheck.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Trade not found'
      });
    }

    if (tradeCheck.rows[0].user_id !== userId) {
      return res.status(403).json({
        success: false,
        message: 'Unauthorized to reject this trade'
      });
    }

    const trade = tradeCheck.rows[0];

    // Update trade status to rejected
    await db.query(
      `UPDATE strategy_trades 
       SET status = 'rejected',
           rejection_reason = $2,
           rejected_at = NOW(),
           updated_at = NOW()
       WHERE id = $1`,
      [tradeId, reason || 'User rejected']
    );

    // Track override in learning system
    try {
      const overrideTracker = getUserOverrideTracker();
      const { reasonCategory, reasonText } = req.body;
      
      await overrideTracker.recordOverride(userId, null, {
        executionId: null,
        overrideType: 'reject',
        aiRecommendation: {
          symbol: trade.symbol,
          quantity: trade.quantity,
          price: trade.price,
          rationale: trade.rationale
        },
        userAlternative: { action: 'rejected' },
        reasonCategory: reasonCategory || 'user_preference',
        reasonText: reasonText || reason || 'User rejected trade'
      });
    } catch (overrideError) {
      console.warn('[AI/Execution] Failed to track override:', overrideError.message);
      // Don't fail the rejection if override tracking fails
    }

    res.json({
      success: true,
      message: 'Trade rejected successfully'
    });

  } catch (error) {
    console.error('[AI/Execution] Error rejecting trade:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to reject trade'
    });
  }
});

/**
 * PUT /api/modules/ai/execution/pending-trades/:id/modify
 * Modify a pending trade (adjust quantity, price, etc.)
 */
router.put('/pending-trades/:id/modify', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const tradeId = req.params.id;
    const { quantity, price, stop_loss, take_profit } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Execution] Modifying trade ${tradeId} for user: ${userId}`);

    // Verify trade belongs to user
    const tradeCheck = await db.query(
      'SELECT id, user_id FROM strategy_trades WHERE id = $1',
      [tradeId]
    );

    if (tradeCheck.rows.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'Trade not found'
      });
    }

    if (tradeCheck.rows[0].user_id !== userId) {
      return res.status(403).json({
        success: false,
        message: 'Unauthorized to modify this trade'
      });
    }

    // Update trade with modifications
    const updates = [];
    const values = [];
    let paramIndex = 1;

    if (quantity !== undefined) {
      updates.push(`quantity = $${paramIndex++}`);
      values.push(quantity);
    }
    if (price !== undefined) {
      updates.push(`price = $${paramIndex++}`);
      values.push(price);
    }
    if (stop_loss !== undefined) {
      updates.push(`stop_loss = $${paramIndex++}`);
      values.push(stop_loss);
    }
    if (take_profit !== undefined) {
      updates.push(`take_profit = $${paramIndex++}`);
      values.push(take_profit);
    }

    if (updates.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'No modifications specified'
      });
    }

    updates.push(`updated_at = NOW()`);
    values.push(tradeId);

    await db.query(
      `UPDATE strategy_trades 
       SET ${updates.join(', ')}
       WHERE id = $${paramIndex}`,
      values
    );

    res.json({
      success: true,
      message: 'Trade modified successfully'
    });

  } catch (error) {
    console.error('[AI/Execution] Error modifying trade:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to modify trade'
    });
  }
});

module.exports = router;

