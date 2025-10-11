/**
 * Rotational Trading Routes
 * V2 API endpoints for rotational trading management
 */

const express = require('express');
const router = express.Router();
const { getRotationalEngine } = require('../services/rotationalEngine');
const db = require('../../../core/database/connection');

/**
 * GET /api/v2/trading/rotation-opportunities
 * Get rotation opportunities for user's portfolio
 */
router.get('/rotation-opportunities', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    console.log('[RotationRoutes] Analyzing rotation opportunities for user:', userId);

    // Get live holdings from database (populated by Kite API sync)
    const holdingsResult = await db.query(
      `SELECT * FROM holdings 
       WHERE user_id = $1 AND config_id = $2 
       ORDER BY last_updated DESC`,
      [userId, configId]
    );

    if (holdingsResult.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No portfolio holdings found. Please sync your portfolio from broker.',
        hint: 'Connect your broker and refresh portfolio data'
      });
    }

    // Transform holdings to expected format
    const holdings = holdingsResult.rows.map(h => ({
      symbol: h.symbol || h.tradingsymbol,
      tradingsymbol: h.tradingsymbol,
      quantity: h.quantity || h.shares,
      average_price: h.average_price || h.averagePrice,
      last_price: h.last_price || h.ltp || h.current_price,
      current_value: h.current_value,
      pnl: h.pnl,
      pnl_percent: h.pnl_percent,
    }));

    // Analyze rotation opportunities
    const rotationalEngine = getRotationalEngine();
    const opportunities = await rotationalEngine.analyzeRotationOpportunities(holdings);

    return res.status(200).json({
      success: true,
      data: {
        opportunities,
        count: opportunities.length,
        summary: {
          high_priority: opportunities.filter(o => o.priority === 'HIGH').length,
          medium_priority: opportunities.filter(o => o.priority === 'MEDIUM').length,
          low_priority: opportunities.filter(o => o.priority === 'LOW').length,
        },
      },
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to analyze rotation opportunities',
    });
  }
});

/**
 * POST /api/v2/trading/enable-rotation
 * Enable/disable rotation for a specific holding
 */
router.post('/enable-rotation', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const { symbol, enable } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    if (!symbol) {
      return res.status(400).json({
        success: false,
        error: 'Symbol is required',
      });
    }

    console.log('[RotationRoutes] Toggling rotation for', symbol, ':', enable);

    const rotationalEngine = getRotationalEngine();
    const result = await rotationalEngine.toggleRotation(userId, symbol, enable);

    return res.status(200).json({
      success: true,
      data: result,
      message: `Rotation ${enable ? 'enabled' : 'disabled'} for ${symbol}`,
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to toggle rotation',
    });
  }
});

/**
 * POST /api/v2/trading/execute-rotation
 * Execute a rotation cycle for a holding
 */
router.post('/execute-rotation', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const rotation = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    if (!rotation.symbol || !rotation.sell_at || !rotation.rebuy_at) {
      return res.status(400).json({
        success: false,
        error: 'Missing required rotation parameters',
      });
    }

    console.log('[RotationRoutes] Executing rotation for', rotation.symbol);

    const rotationalEngine = getRotationalEngine();
    const result = await rotationalEngine.executeRotation(userId, configId, rotation);

    return res.status(200).json({
      success: true,
      data: result,
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to execute rotation',
    });
  }
});

/**
 * GET /api/v2/trading/active-rotations
 * Get active rotation cycles
 */
router.get('/active-rotations', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    if (!userId) {
      return res.status(401).json({
        success: false,
        error: 'User authentication required',
      });
    }

    const rotationalEngine = getRotationalEngine();
    const activeRotations = await rotationalEngine.getActiveRotations(userId, configId);

    return res.status(200).json({
      success: true,
      data: {
        rotations: activeRotations,
        count: activeRotations.length,
      },
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch active rotations',
    });
  }
});

/**
 * GET /api/v2/trading/rotation-history
 * Get rotation history
 */
router.get('/rotation-history', async (req, res) => {
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

    const rotationalEngine = getRotationalEngine();
    const history = await rotationalEngine.getRotationHistory(userId, configId, days);

    return res.status(200).json({
      success: true,
      data: {
        history,
        count: history.length,
        days,
      },
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to fetch rotation history',
    });
  }
});

/**
 * PUT /api/v2/trading/rotation/:cycleId/status
 * Update rotation cycle status
 */
router.put('/rotation/:cycleId/status', async (req, res) => {
  try {
    const { cycleId } = req.params;
    const { status, pnl } = req.body;

    if (!['SOLD', 'REBOUGHT', 'CANCELLED'].includes(status)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid status. Must be SOLD, REBOUGHT, or CANCELLED',
      });
    }

    const rotationalEngine = getRotationalEngine();
    const result = await rotationalEngine.updateRotationStatus(cycleId, status, { pnl });

    return res.status(200).json({
      success: true,
      data: result,
      message: `Rotation cycle updated to ${status}`,
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to update rotation status',
    });
  }
});

/**
 * DELETE /api/v2/trading/rotation/:cycleId
 * Cancel a rotation cycle
 */
router.delete('/rotation/:cycleId', async (req, res) => {
  try {
    const { cycleId } = req.params;
    const { reason } = req.body;

    const rotationalEngine = getRotationalEngine();
    const result = await rotationalEngine.cancelRotation(cycleId, reason || 'User cancelled');

    return res.status(200).json({
      success: true,
      data: result,
    });

  } catch (error) {
    console.error('[RotationRoutes] Error:', error);
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to cancel rotation',
    });
  }
});

module.exports = router;

