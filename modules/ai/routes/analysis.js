/**
 * AI Analysis Routes
 * Endpoints for portfolio analysis, trade analysis, and strategy generation
 */

const express = require('express');
const router = express.Router();
const OpenAIProvider = require('../services/providers/openai');
const preferencesService = require('../services/preferences');

/**
 * POST /api/ai/analyze-portfolio
 * Analyze portfolio and provide insights
 */
router.post('/analyze-portfolio', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const { portfolio_data } = req.body;

    console.log('[AI Analysis] Portfolio analysis request:', { 
      userId, 
      configId, 
      hasPortfolioData: !!portfolio_data 
    });

    // Validate inputs
    if (!userId) {
      return res.status(400).json({ 
        success: false, 
        error: 'user_id is required in headers (X-User-ID)' 
      });
    }

    if (!portfolio_data) {
      return res.status(400).json({ 
        success: false, 
        error: 'portfolio_data is required in request body' 
      });
    }

    // Get user's AI preferences
    const preferences = await preferencesService.getPreferences(userId);
    
    if (!preferences) {
      return res.status(400).json({
        success: false,
        error: 'No AI provider configured. Please add an API key in AI Settings.',
        code: 'NO_AI_PROVIDER'
      });
    }

    // Determine which provider to use
    let apiKey = null;
    let provider = preferences.preferred_ai_provider || 'auto';
    
    if (provider === 'auto') {
      // Auto-select based on availability: OpenAI > Claude > Gemini
      if (preferences.openai_api_key) {
        apiKey = preferences.openai_api_key;
        provider = 'openai';
      } else if (preferences.claude_api_key) {
        apiKey = preferences.claude_api_key;
        provider = 'claude';
      } else if (preferences.gemini_api_key) {
        apiKey = preferences.gemini_api_key;
        provider = 'gemini';
      } else {
        return res.status(400).json({
          success: false,
          error: 'No API keys configured. Please add at least one API key in AI Settings.',
          code: 'NO_API_KEYS'
        });
      }
    } else {
      // Use specific provider
      apiKey = preferences[`${provider}_api_key`];
      if (!apiKey) {
        return res.status(400).json({
          success: false,
          error: `${provider} API key not configured. Please add it in AI Settings or use auto mode.`,
          code: 'PROVIDER_NOT_CONFIGURED'
        });
      }
    }

    console.log(`[AI Analysis] Using provider: ${provider}`);

    // Currently only OpenAI is implemented
    if (provider !== 'openai') {
      return res.status(501).json({
        success: false,
        error: `${provider} provider is not yet implemented. Please use OpenAI or set to auto.`,
        code: 'PROVIDER_NOT_IMPLEMENTED'
      });
    }

    // Perform analysis
    const aiProvider = new OpenAIProvider(apiKey);
    const analysis = await aiProvider.analyzePortfolio(portfolio_data);

    console.log('[AI Analysis] Analysis complete:', { 
      provider, 
      hasInsights: analysis.insights?.length > 0 
    });

    // Return analysis
    res.json({
      success: true,
      data: {
        ...analysis,
        user_id: userId,
        analyzed_at: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[AI Analysis] Portfolio analysis error:', error);
    
    // Handle specific error types
    if (error.message?.includes('API key')) {
      return res.status(401).json({
        success: false,
        error: 'Invalid or expired API key. Please check your AI settings.',
        code: 'INVALID_API_KEY',
        details: error.message
      });
    }

    if (error.message?.includes('quota') || error.message?.includes('rate limit')) {
      return res.status(429).json({
        success: false,
        error: 'API rate limit exceeded. Please try again later.',
        code: 'RATE_LIMIT_EXCEEDED',
        details: error.message
      });
    }

    res.status(500).json({
      success: false,
      error: 'Failed to analyze portfolio. Please try again.',
      code: 'ANALYSIS_FAILED',
      details: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
});

/**
 * POST /api/ai/analyze-trade
 * Analyze a specific trade opportunity
 */
router.post('/analyze-trade', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { trade_data, portfolio_context } = req.body;

    if (!userId) {
      return res.status(400).json({ 
        success: false, 
        error: 'user_id is required in headers' 
      });
    }

    if (!trade_data) {
      return res.status(400).json({ 
        success: false, 
        error: 'trade_data is required' 
      });
    }

    // Get user's AI preferences and provider
    const preferences = await preferencesService.getPreferences(userId);
    if (!preferences || !preferences.openai_api_key) {
      return res.status(400).json({
        success: false,
        error: 'OpenAI API key not configured',
        code: 'NO_API_KEY'
      });
    }

    const aiProvider = new OpenAIProvider(preferences.openai_api_key);
    const analysis = await aiProvider.analyzeTrade(trade_data, portfolio_context);

    res.json({
      success: true,
      data: analysis
    });

  } catch (error) {
    console.error('[AI Analysis] Trade analysis error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to analyze trade',
      details: error.message
    });
  }
});

/**
 * POST /api/ai/generate-strategy
 * Generate a trading strategy based on goals and risk tolerance
 */
router.post('/generate-strategy', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const { goals, risk_tolerance, market_conditions } = req.body;

    if (!userId) {
      return res.status(400).json({ 
        success: false, 
        error: 'user_id is required in headers' 
      });
    }

    if (!goals || !risk_tolerance) {
      return res.status(400).json({ 
        success: false, 
        error: 'goals and risk_tolerance are required' 
      });
    }

    // Get user's AI preferences
    const preferences = await preferencesService.getPreferences(userId);
    if (!preferences || !preferences.openai_api_key) {
      return res.status(400).json({
        success: false,
        error: 'OpenAI API key not configured',
        code: 'NO_API_KEY'
      });
    }

    const aiProvider = new OpenAIProvider(preferences.openai_api_key);
    const strategy = await aiProvider.generateStrategy(goals, risk_tolerance, market_conditions);

    res.json({
      success: true,
      data: strategy
    });

  } catch (error) {
    console.error('[AI Analysis] Strategy generation error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to generate strategy',
      details: error.message
    });
  }
});

/**
 * POST /api/ai/chat
 * Chat with AI assistant (implemented in main routes/index.js)
 * This is a placeholder - actual implementation should go in the main AI routes
 */
router.post('/chat', async (req, res) => {
  res.status(501).json({
    success: false,
    error: 'Chat endpoint not implemented in analysis routes. Use main /api/ai/chat endpoint.'
  });
});

module.exports = router;


