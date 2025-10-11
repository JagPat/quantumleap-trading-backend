/**
 * AI Auto-Trading Consent Routes
 * Manages user consent for automated trading
 */

const express = require('express');
const router = express.Router();
const getTradingModeManager = require('../services/tradingModeManager');

/**
 * POST /api/modules/ai/consent/auto-trading
 * Grant auto-trading consent
 */
router.post('/auto-trading', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { disclaimers_accepted, ip_address } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!disclaimers_accepted || !Array.isArray(disclaimers_accepted) || disclaimers_accepted.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'You must accept all disclaimers before enabling auto-trading'
      });
    }

    console.log(`[AI/Consent] Recording auto-trading consent for user: ${userId}`);

    const tradingModeManager = getTradingModeManager();
    const result = await tradingModeManager.grantAutoTradingConsent(userId, {
      ip: ip_address || req.ip || req.connection.remoteAddress,
      disclaimers: disclaimers_accepted
    });

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Consent] Error granting consent:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to record auto-trading consent'
    });
  }
});

/**
 * DELETE /api/modules/ai/consent/auto-trading
 * Revoke auto-trading consent
 */
router.delete('/auto-trading', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    console.log(`[AI/Consent] Revoking auto-trading consent for user: ${userId}`);

    const tradingModeManager = getTradingModeManager();
    const result = await tradingModeManager.revokeAutoTradingConsent(userId);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Consent] Error revoking consent:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to revoke auto-trading consent'
    });
  }
});

/**
 * GET /api/modules/ai/consent/status
 * Check auto-trading consent status
 */
router.get('/status', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    const tradingModeManager = getTradingModeManager();
    const hasConsent = await tradingModeManager.hasAutoTradingConsent(userId);
    const status = await tradingModeManager.getStatus(userId);

    res.json({
      success: true,
      data: {
        hasConsent,
        ...status
      }
    });

  } catch (error) {
    console.error('[AI/Consent] Error checking consent status:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to check consent status'
    });
  }
});

/**
 * PUT /api/modules/ai/consent/trading-mode
 * Set trading mode (manual | auto)
 */
router.put('/trading-mode', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { mode } = req.body;

    if (!userId) {
      return res.status(401).json({
        success: false,
        message: 'User authentication required'
      });
    }

    if (!mode || !['manual', 'auto'].includes(mode)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid mode. Must be "manual" or "auto"'
      });
    }

    console.log(`[AI/Consent] Setting trading mode to ${mode} for user: ${userId}`);

    const tradingModeManager = getTradingModeManager();
    const result = await tradingModeManager.setMode(userId, mode);

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('[AI/Consent] Error setting trading mode:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to set trading mode'
    });
  }
});

module.exports = router;

