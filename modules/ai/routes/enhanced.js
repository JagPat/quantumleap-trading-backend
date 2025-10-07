/**
 * Enhanced AI Routes - Phase 2.3
 * 
 * Advanced AI trading features:
 * - Enhanced strategy generation
 * - Broker-independent signals
 * - Portfolio optimization
 * - Risk profiling & automated suggestions
 */

const express = require('express');
const StrategyEngine = require('../services/strategyEngine');
const preferencesService = require('../services/preferences');

const router = express.Router();
const strategyEngine = new StrategyEngine();

/**
 * POST /api/ai/strategy/advanced
 * Generate advanced multi-component trading strategy
 */
router.post('/strategy/advanced', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const {
      goals,
      risk_tolerance,
      market_conditions,
      portfolio_context,
      broker_type = 'zerodha'
    } = req.body;

    console.log('[AI][Advanced Strategy] POST request from user:', userId);

    if (!userId) {
      return res.status(400).json({
        success: false,
        status: 'error',
        message: 'user_id is required in headers (X-User-ID)',
        endpoint: 'strategy/advanced'
      });
    }

    const result = await strategyEngine.generateAdvancedStrategy({
      goals,
      riskTolerance: risk_tolerance,
      marketConditions: market_conditions,
      portfolioContext: portfolio_context,
      brokerType: broker_type
    }, userId);

    res.status(200).json({
      success: true,
      status: 'success',
      data: result.strategy,
      endpoint: 'strategy/advanced',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[AI][Advanced Strategy] Error:', error);
    
    if (error.message.includes('API key not configured')) {
      return res.status(400).json({
        success: false,
        status: 'not_configured',
        message: 'OpenAI API key not configured. Please add it in AI Settings.',
        endpoint: 'strategy/advanced',
        instructions: 'Go to Settings → AI Configuration to add your OpenAI API key'
      });
    }

    res.status(500).json({
      success: false,
      status: 'error',
      message: 'Failed to generate advanced strategy',
      error: error.message,
      endpoint: 'strategy/advanced'
    });
  }
});

/**
 * POST /api/ai/signals/universal
 * Generate broker-independent trading signals
 */
router.post('/signals/universal', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const {
      symbols = [],
      timeframe = '1h',
      market_data = {},
      risk_level = 'moderate'
    } = req.body;

    console.log('[AI][Universal Signals] POST request from user:', userId);

    if (!userId) {
      return res.status(400).json({
        success: false,
        status: 'error',
        message: 'user_id is required in headers (X-User-ID)',
        endpoint: 'signals/universal'
      });
    }

    if (!symbols || symbols.length === 0) {
      return res.status(400).json({
        success: false,
        status: 'error',
        message: 'symbols array is required',
        endpoint: 'signals/universal'
      });
    }

    const result = await strategyEngine.generateUniversalSignals({
      symbols,
      timeframe,
      marketData: market_data,
      riskLevel: risk_level
    }, userId);

    res.status(200).json({
      success: true,
      status: 'success',
      data: result.signals,
      endpoint: 'signals/universal',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[AI][Universal Signals] Error:', error);
    
    if (error.message.includes('API key not configured')) {
      return res.status(400).json({
        success: false,
        status: 'not_configured',
        message: 'OpenAI API key not configured. Please add it in AI Settings.',
        endpoint: 'signals/universal',
        instructions: 'Go to Settings → AI Configuration to add your OpenAI API key'
      });
    }

    res.status(500).json({
      success: false,
      status: 'error',
      message: 'Failed to generate universal signals',
      error: error.message,
      endpoint: 'signals/universal'
    });
  }
});

/**
 * POST /api/ai/portfolio/optimize
 * Generate portfolio optimization recommendations
 */
router.post('/portfolio/optimize', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const {
      current_holdings = [],
      target_allocation = {},
      risk_tolerance = 'moderate',
      investment_horizon = 'medium_term',
      constraints = {}
    } = req.body;

    console.log('[AI][Portfolio Optimization] POST request from user:', userId);

    if (!userId) {
      return res.status(400).json({
        success: false,
        status: 'error',
        message: 'user_id is required in headers (X-User-ID)',
        endpoint: 'portfolio/optimize'
      });
    }

    const result = await strategyEngine.optimizePortfolio({
      currentHoldings: current_holdings,
      targetAllocation: target_allocation,
      riskTolerance: risk_tolerance,
      investmentHorizon: investment_horizon,
      constraints: constraints
    }, userId);

    res.status(200).json({
      success: true,
      status: 'success',
      data: result.optimization,
      endpoint: 'portfolio/optimize',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[AI][Portfolio Optimization] Error:', error);
    
    if (error.message.includes('API key not configured')) {
      return res.status(400).json({
        success: false,
        status: 'not_configured',
        message: 'OpenAI API key not configured. Please add it in AI Settings.',
        endpoint: 'portfolio/optimize',
        instructions: 'Go to Settings → AI Configuration to add your OpenAI API key'
      });
    }

    res.status(500).json({
      success: false,
      status: 'error',
      message: 'Failed to optimize portfolio',
      error: error.message,
      endpoint: 'portfolio/optimize'
    });
  }
});

/**
 * POST /api/ai/risk/profile
 * Generate risk profiling and automated suggestions
 */
router.post('/risk/profile', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const {
      trading_history = [],
      current_positions = [],
      risk_tolerance = 'moderate',
      portfolio_value = 0,
      investment_goals = {}
    } = req.body;

    console.log('[AI][Risk Profile] POST request from user:', userId);

    if (!userId) {
      return res.status(400).json({
        success: false,
        status: 'error',
        message: 'user_id is required in headers (X-User-ID)',
        endpoint: 'risk/profile'
      });
    }

    const result = await strategyEngine.generateRiskProfile({
      tradingHistory: trading_history,
      currentPositions: current_positions,
      riskTolerance: risk_tolerance,
      portfolioValue: portfolio_value,
      investmentGoals: investment_goals
    }, userId);

    res.status(200).json({
      success: true,
      status: 'success',
      data: result.riskProfile,
      endpoint: 'risk/profile',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('[AI][Risk Profile] Error:', error);
    
    if (error.message.includes('API key not configured')) {
      return res.status(400).json({
        success: false,
        status: 'not_configured',
        message: 'OpenAI API key not configured. Please add it in AI Settings.',
        endpoint: 'risk/profile',
        instructions: 'Go to Settings → AI Configuration to add your OpenAI API key'
      });
    }

    res.status(500).json({
      success: false,
      status: 'error',
      message: 'Failed to generate risk profile',
      error: error.message,
      endpoint: 'risk/profile'
    });
  }
});

/**
 * GET /api/ai/features/status
 * Get status of all Phase 2.3 AI features
 */
router.get('/features/status', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];

    console.log('[AI][Features Status] GET request from user:', userId);

    let featuresStatus = {
      advanced_strategy: { available: true, description: 'Multi-component strategy generation' },
      universal_signals: { available: true, description: 'Broker-independent trading signals' },
      portfolio_optimization: { available: true, description: 'AI-powered portfolio optimization' },
      risk_profiling: { available: true, description: 'Risk analysis and automated suggestions' }
    };

    if (userId) {
      const preferences = await preferencesService.getPreferences(userId);
      const hasApiKey = preferences && (preferences.openai_api_key || preferences.claude_api_key || preferences.gemini_api_key);
      
      if (hasApiKey) {
        featuresStatus = Object.keys(featuresStatus).reduce((acc, key) => {
          acc[key] = { ...featuresStatus[key], configured: true, ready: true };
          return acc;
        }, {});
      } else {
        featuresStatus = Object.keys(featuresStatus).reduce((acc, key) => {
          acc[key] = { ...featuresStatus[key], configured: false, ready: false, message: 'API key required' };
          return acc;
        }, {});
      }
    }

    res.status(200).json({
      success: true,
      status: 'success',
      data: {
        features: featuresStatus,
        version: '2.3',
        phase: 'Advanced AI Trading Features',
        timestamp: new Date().toISOString()
      },
      endpoint: 'features/status'
    });

  } catch (error) {
    console.error('[AI][Features Status] Error:', error);
    res.status(500).json({
      success: false,
      status: 'error',
      message: 'Failed to get features status',
      error: error.message,
      endpoint: 'features/status'
    });
  }
});

module.exports = router;
