const express = require('express');
const router = express.Router();
const StrategyGoalsService = require('../services/strategyGoals');
const StrategyEngine = require('../services/strategyEngine');
const AIPreferencesService = require('../services/preferences');
const PerformanceTracker = require('../services/performanceTracker');
const GoalSuggestionEngine = require('../services/goalSuggestionEngine');
const resolveUserIdentifier = require('../../auth/services/resolveUserIdentifier');

const strategyGoalsService = new StrategyGoalsService();
const strategyEngine = new StrategyEngine();
const preferencesService = new AIPreferencesService();
const performanceTracker = new PerformanceTracker();
const goalSuggestionEngine = new GoalSuggestionEngine();

/**
 * POST /api/ai/goals/suggest
 * Get AI-suggested trading goals based on portfolio and history
 */
router.post('/goals/suggest', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;
    const { portfolio_data } = req.body;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    if (!portfolio_data) {
      return res.status(400).json({
        status: 'error',
        message: 'portfolio_data is required in request body'
      });
    }

    console.log('[AutomationRoutes] Generating goal suggestions for user:', userId);

    const result = await goalSuggestionEngine.suggestGoals(userId, configId, portfolio_data);

    // Return response in expected format
    res.json({
      status: 'success',
      message: 'Goal suggestions generated successfully',
      data: {
        suggestions: result.suggestions,
        portfolio_analysis: result.portfolio_analysis,
        based_on: result.based_on
      }
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error generating goal suggestions:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Failed to generate goal suggestions'
    });
  }
});

/**
 * POST /api/ai/strategy-automation
 * Create a new strategy automation from user goals
 */
router.post('/strategy-automation', async (req, res) => {
  try {
    const { profitTarget, timeframe, maxLoss, riskTolerance, symbols, name } = req.body;
    
    // Extract user identifiers from headers or session
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const configId = req.headers['x-config-id'] || req.session?.config_id;

    // ✅ ENHANCED LOGGING: Log full request context
    console.log('[AutomationRoutes] ========== STRATEGY AUTOMATION REQUEST ==========');
    console.log('[AutomationRoutes] Request payload:', {
      profitTarget,
      timeframe,
      maxLoss,
      riskTolerance,
      symbols,
      name,
      userId: userId || 'MISSING',
      configId: configId || 'MISSING'
    });

    if (!userId) {
      console.warn('[AutomationRoutes] ❌ Request rejected: No user authentication');
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] ✅ User authenticated, proceeding with automation creation');

    // Store the goals
    const goalsResult = await strategyGoalsService.storeGoals(userId, configId, {
      profitTarget,
      timeframe,
      maxLoss,
      riskTolerance,
      symbols,
      name
    });

    if (!goalsResult.success) {
      return res.status(400).json({
        status: 'error',
        message: 'Failed to store goals',
        errors: goalsResult.errors
      });
    }

    const automation = goalsResult.automation;

    // Get AI preferences to determine which provider to use
    const prefsResult = await preferencesService.getPreferences(userId, configId);
    const preferences = prefsResult.preferences || {};

    // Generate AI strategy based on goals
    console.log('[AutomationRoutes] Calling strategyEngine.generateGoalBasedStrategy...');
    console.log('[AutomationRoutes] Goal parameters:', {
      profitTarget: automation.profitTargetPercent,
      timeframe: automation.timeframeDays,
      maxLoss: automation.maxLossPercent,
      riskTolerance: automation.riskTolerance,
      symbols: automation.symbols,
      symbolsType: typeof automation.symbols,
      symbolsIsArray: Array.isArray(automation.symbols)
    });
    
    try {
      const strategyResult = await strategyEngine.generateGoalBasedStrategy(
        {
          profitTarget: automation.profitTargetPercent,
          timeframe: automation.timeframeDays,
          maxLoss: automation.maxLossPercent,
          riskTolerance: automation.riskTolerance,
          symbols: automation.symbols
        },
        prefsResult.preferences || {},
        null // portfolioContext - can be added later
      );

      console.log('[AutomationRoutes] ✅ Strategy generation completed:', {
        success: strategyResult.success,
        hasStrategy: !!strategyResult.strategy,
        confidence: strategyResult.confidence,
        selectedStocksCount: strategyResult.selectedStocks?.length || 0,
        stockSelectionMode: strategyResult.stockSelectionMode
      });

      // Attach strategy to automation
      if (strategyResult.success && strategyResult.strategy) {
        await strategyGoalsService.updateWithStrategy(
          automation.id,
          strategyResult.strategy,
          strategyResult.confidence || 0.75
        );

        console.log('[AutomationRoutes] ✅ Strategy automation created successfully (ID: ' + automation.id + ')');
        
        return res.status(201).json({
          status: 'success',
          message: 'Strategy automation created successfully',
          data: {
            automation: {
              ...automation,
              strategyRules: strategyResult.strategy,
              aiConfidenceScore: strategyResult.confidence || 0.75,
              selectedStocks: strategyResult.selectedStocks,
              stockSelectionMode: strategyResult.stockSelectionMode
            },
            requiresApproval: true
          }
        });
      }
    } catch (aiError) {
      console.error('[AutomationRoutes] ❌ AI strategy generation failed');
      console.error('[AutomationRoutes] Error name:', aiError.name);
      console.error('[AutomationRoutes] Error message:', aiError.message);
      console.error('[AutomationRoutes] Error stack:', aiError.stack);
      console.error('[AutomationRoutes] Error context:', {
        userId,
        configId,
        automationId: automation?.id,
        symbols: automation?.symbols
      });
      
      // Still return the automation, but without strategy rules
      return res.status(201).json({
        status: 'partial_success',
        message: 'Goals saved, but AI strategy generation failed. Please try again.',
        data: {
          automation,
          error: aiError.message,
          errorDetails: {
            name: aiError.name,
            fallbackUsed: 'Phase 7 services may be unavailable'
          }
        }
      });
    }

    // Fallback if no strategy generated
    return res.status(201).json({
      status: 'success',
      message: 'Goals saved successfully',
      data: {
        automation
      }
    });

  } catch (error) {
    console.error('[AutomationRoutes] ========== FATAL ERROR IN STRATEGY AUTOMATION ==========');
    console.error('[AutomationRoutes] Error name:', error.name);
    console.error('[AutomationRoutes] Error message:', error.message);
    console.error('[AutomationRoutes] Error stack:', error.stack);
    console.error('[AutomationRoutes] Request body:', req.body);
    console.error('[AutomationRoutes] User context:', {
      userId: req.headers['x-user-id'],
      configId: req.headers['x-config-id']
    });
    console.error('[AutomationRoutes] ========================================================');
    
    res.status(500).json({
      status: 'error',
      message: error.message || 'Failed to create strategy automation',
      errorType: error.name,
      details: process.env.NODE_ENV === 'development' ? {
        stack: error.stack,
        fullError: error.toString()
      } : undefined
    });
  }
});

/**
 * GET /api/ai/strategy-automation
 * Get all strategy automations for the authenticated user
 */
router.get('/strategy-automation', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const status = req.query.status;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    const result = await strategyGoalsService.getUserAutomations(userId, status);

    res.json({
      status: 'success',
      data: {
        automations: result.automations,
        count: result.automations.length
      }
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error fetching automations:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Failed to fetch automations'
    });
  }
});

/**
 * GET /api/ai/strategy-automation/:id
 * Get a specific strategy automation by ID
 */
router.get('/strategy-automation/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    const result = await strategyGoalsService.getAutomation(id, userId);

    res.json({
      status: 'success',
      data: result.automation
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error fetching automation:', error);
    const statusCode = error.message.includes('not found') ? 404 : 500;
    res.status(statusCode).json({
      status: 'error',
      message: error.message || 'Failed to fetch automation'
    });
  }
});

/**
 * POST /api/ai/strategy-automation/:id/approve
 * Approve a strategy automation (with optional parameter adjustments)
 */
router.post('/strategy-automation/:id/approve', async (req, res) => {
  try {
    const { id } = req.params;
    const { adjustments } = req.body;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Approving automation:', {
      automationId: id,
      userId,
      hasAdjustments: !!adjustments
    });

    const result = await strategyGoalsService.approveAutomation(id, userId, adjustments);

    res.json({
      status: 'success',
      message: 'Strategy approved successfully',
      data: result.automation
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error approving automation:', error);
    const statusCode = error.message.includes('not found') ? 404 : 500;
    res.status(statusCode).json({
      status: 'error',
      message: error.message || 'Failed to approve automation'
    });
  }
});

/**
 * POST /api/ai/strategy-automation/:id/reject
 * Reject a strategy automation
 */
router.post('/strategy-automation/:id/reject', async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Rejecting automation:', {
      automationId: id,
      userId,
      reason
    });

    const result = await strategyGoalsService.rejectAutomation(id, userId, reason);

    res.json({
      status: 'success',
      message: 'Strategy rejected',
      data: result.automation
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error rejecting automation:', error);
    const statusCode = error.message.includes('not found') ? 404 : 500;
    res.status(statusCode).json({
      status: 'error',
      message: error.message || 'Failed to reject automation'
    });
  }
});

/**
 * GET /api/ai/strategy-automation/:id/performance
 * Get performance metrics for a specific automation
 */
router.get('/strategy-automation/:id/performance', async (req, res) => {
  try {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Fetching performance for automation:', {
      automationId: id,
      userId
    });

    const result = await performanceTracker.getPerformanceSummary(id);

    // Verify user owns this automation
    if (result.automation.userId !== userId) {
      return res.status(403).json({
        status: 'error',
        message: 'Unauthorized access to this automation'
      });
    }

    res.json({
      status: 'success',
      data: result
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error fetching performance:', error);
    const statusCode = error.message.includes('not found') ? 404 : 500;
    res.status(statusCode).json({
      status: 'error',
      message: error.message || 'Failed to fetch performance data'
    });
  }
});

/**
 * GET /api/ai/strategy-automation/:id/export
 * Export performance data as CSV
 */
router.get('/strategy-automation/:id/export', async (req, res) => {
  try {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;
    const format = req.query.format || 'csv';

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Exporting performance:', {
      automationId: id,
      userId,
      format
    });

    // Verify user owns this automation
    const automation = await strategyGoalsService.getAutomation(id, userId);
    if (!automation.success) {
      return res.status(404).json({
        status: 'error',
        message: 'Automation not found'
      });
    }

    const report = await performanceTracker.generatePerformanceReport(id, format);

    if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="${report.filename}"`);
      res.send(report.data);
    } else {
      res.json({
        status: 'success',
        data: report
      });
    }

  } catch (error) {
    console.error('[AutomationRoutes] Error exporting performance:', error);
    const statusCode = error.message.includes('not found') ? 404 : 500;
    res.status(statusCode).json({
      status: 'error',
      message: error.message || 'Failed to export performance data'
    });
  }
});

/**
 * POST /api/ai/strategy-automation/:id/activate
 * Activate an approved automation
 */
router.post('/strategy-automation/:id/activate', async (req, res) => {
  try {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Activating automation:', {
      automationId: id,
      userId
    });

    // Get execution engine and activate
    const getExecutionEngine = require('../services/executionEngine');
    const executionEngine = getExecutionEngine();
    
    const automation = await executionEngine.activateAutomation(id);

    res.json({
      status: 'success',
      message: 'Automation activated successfully',
      data: automation
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error activating automation:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Failed to activate automation'
    });
  }
});

/**
 * POST /api/ai/strategy-automation/:id/pause
 * Pause an active automation
 */
router.post('/strategy-automation/:id/pause', async (req, res) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;
    const userId = req.headers['x-user-id'] || req.session?.user_id;

    if (!userId) {
      return res.status(401).json({
        status: 'error',
        message: 'User authentication required'
      });
    }

    console.log('[AutomationRoutes] Pausing automation:', {
      automationId: id,
      userId,
      reason
    });

    // Get execution engine and pause
    const getExecutionEngine = require('../services/executionEngine');
    const executionEngine = getExecutionEngine();
    
    await executionEngine.pauseAutomation(id, reason || 'User requested pause');

    res.json({
      status: 'success',
      message: 'Automation paused successfully'
    });

  } catch (error) {
    console.error('[AutomationRoutes] Error pausing automation:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Failed to pause automation'
    });
  }
});

module.exports = router;

