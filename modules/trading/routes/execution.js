/**
 * Trade Execution Routes
 * V2 API endpoints for trade validation and execution
 */

const express = require('express');
const router = express.Router();
const { getTradeExecutor } = require('../services/tradeExecutor');

/**
 * POST /api/v2/trading/validate-trade
 * Validate trade before execution
 */
router.post('/validate-trade', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const tradeDetails = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const tradeExecutor = getTradeExecutor();
    const validation = await tradeExecutor.validateTrade(userId, configId, tradeDetails);

    return res.status(200).json({
      success: true,
      data: validation,
    });

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to validate trade',
    });
  }
});

/**
 * POST /api/v2/trading/prepare-trade
 * Prepare trade for execution (create pending trade)
 */
router.post('/prepare-trade', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const tradeDetails = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const tradeExecutor = getTradeExecutor();
    const result = await tradeExecutor.prepareTrade(userId, configId, tradeDetails);

    return res.status(result.success ? 200 : 400).json(result);

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to prepare trade',
    });
  }
});

/**
 * POST /api/v2/trading/execute-trade/:tradeId
 * Execute a prepared trade
 */
router.post('/execute-trade/:tradeId', async (req, res) => {
  try {
    const { tradeId } = req.params;
    const brokerClient = req.brokerClient; // From middleware

    const tradeExecutor = getTradeExecutor();
    const result = await tradeExecutor.executeTrade(tradeId, brokerClient);

    return res.status(result.success ? 200 : 400).json(result);

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to execute trade',
    });
  }
});

/**
 * GET /api/v2/trading/pending-trades
 * Get pending trades for user
 */
router.get('/pending-trades', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const tradeExecutor = getTradeExecutor();
    const trades = await tradeExecutor.getPendingTrades(userId, configId);

    return res.status(200).json({
      success: true,
      data: {
        trades,
        count: trades.length,
      },
    });

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch pending trades',
    });
  }
});

/**
 * DELETE /api/v2/trading/cancel-trade/:tradeId
 * Cancel a pending trade
 */
router.delete('/cancel-trade/:tradeId', async (req, res) => {
  try {
    const { tradeId } = req.params;
    const { reason } = req.body;

    const tradeExecutor = getTradeExecutor();
    const result = await tradeExecutor.cancelTrade(tradeId, reason || 'User cancelled');

    return res.status(200).json(result);

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to cancel trade',
    });
  }
});

/**
 * GET /api/v2/trading/trade-history
 * Get trade execution history
 */
router.get('/trade-history', async (req, res) => {
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

    const tradeExecutor = getTradeExecutor();
    const history = await tradeExecutor.getTradeHistory(userId, configId, days);

    return res.status(200).json({
      success: true,
      data: {
        history,
        count: history.length,
        days,
      },
    });

  } catch (error) {
    console.error('[ExecutionRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch trade history',
    });
  }
});

module.exports = router;

