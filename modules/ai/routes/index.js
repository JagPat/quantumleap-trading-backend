const express = require('express');
const aiService = require('../services');
const AIPreferencesService = require('../services/preferences');
const analysisRoutes = require('./analysis');

const router = express.Router();
const preferencesService = new AIPreferencesService();

// Mount analysis routes (portfolio analysis, trade analysis, strategy generation)
router.use('/', analysisRoutes);

// Health check
router.get('/health', async (req, res) => {
  try {
    console.log('[AI] Health check requested');
    
    // Return safe response - AI service is in "not configured" state
    // This is NOT an error - it's the expected state until users add API keys
    const health = {
      status: 'not_configured',
      message: 'AI service is ready but not yet configured. Add API keys in Settings to enable AI features.',
      module: 'ai',
      timestamp: new Date().toISOString(),
      ready: false,
      instructions: 'Go to Settings → AI Configuration to add OpenAI, Claude, or Gemini API keys'
    };
    
    res.status(200).json(health);
  } catch (error) {
    console.error('[AI] Health check error:', error);
    // Even on error, return 200 with safe response
    res.status(200).json({ 
      status: 'error',
      message: 'AI service health check encountered an error',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// AI Preferences Management
// GET /api/ai/preferences - Get user's AI API key preferences
router.get('/preferences', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    
    if (!userId) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'User ID required in X-User-ID header' 
      });
    }
    
    console.log('[AI][Preferences] GET request from user:', userId);
    
    // Get preferences from database
    const preferences = await preferencesService.getPreferences(userId);
    
    if (!preferences) {
      // No preferences exist yet - return defaults
      return res.json({
        status: 'no_key',
        preferences: {
          preferred_ai_provider: 'auto',
          has_openai_key: false,
          has_claude_key: false,
          has_gemini_key: false,
          openai_key_preview: '',
          claude_key_preview: '',
          gemini_key_preview: ''
        }
      });
    }
    
    res.json({
      status: 'success',
      preferences
    });
  } catch (error) {
    console.error('[AI][Preferences] Failed to get preferences:', error);
    res.status(500).json({ 
      status: 'error', 
      message: 'Failed to retrieve AI preferences' 
    });
  }
});

// POST /api/ai/validate-key - Validate an AI API key
router.post('/validate-key', async (req, res) => {
  try {
    const { provider, api_key } = req.body;
    
    if (!provider || !api_key) {
      return res.status(400).json({ 
        valid: false,
        message: 'Provider and API key are required' 
      });
    }
    
    console.log(`[AI][Validate] Validating ${provider} API key...`);
    
    // Validate the API key by making a test request
    const validation = await preferencesService.validateApiKey(provider, api_key);
    
    res.json({
      valid: validation.valid,
      provider: provider,
      message: validation.message || (validation.valid ? 'API key is valid' : 'API key is invalid')
    });
  } catch (error) {
    console.error('[AI][Validate] Validation error:', error);
    res.status(500).json({ 
      valid: false,
      message: error.message || 'Failed to validate API key' 
    });
  }
});

// POST /api/ai/preferences - Save user's AI API keys
router.post('/preferences', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    const { preferred_ai_provider, openai_api_key, claude_api_key, gemini_api_key } = req.body;
    
    if (!userId) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'User ID required in X-User-ID header' 
      });
    }
    
    console.log('[AI][Preferences] POST request from user:', userId);
    console.log('[AI][Preferences] Saving preferences:', {
      preferred_ai_provider,
      has_openai: !!openai_api_key,
      has_claude: !!claude_api_key,
      has_gemini: !!gemini_api_key
    });
    
    // Save preferences to database
    const result = await preferencesService.savePreferences(userId, configId, {
      preferred_ai_provider: preferred_ai_provider || 'auto',
      openai_api_key,
      claude_api_key,
      gemini_api_key
    });
    
    console.log('✅ [AI][Preferences] Saved successfully for user:', userId);
    
    res.json({
      status: 'success',
      preferences: result,
      message: 'AI preferences saved successfully'
    });
  } catch (error) {
    console.error('[AI][Preferences] Failed to save preferences:', error);
    res.status(500).json({ 
      status: 'error', 
      message: error.message || 'Failed to save AI preferences' 
    });
  }
});

// DELETE /api/ai/preferences - Delete user's AI preferences
router.delete('/preferences', async (req, res) => {
  try {
    const userId = req.headers['x-user-id'];
    
    if (!userId) {
      return res.status(400).json({ 
        status: 'error', 
        message: 'User ID required in X-User-ID header' 
      });
    }
    
    console.log('[AI][Preferences] DELETE request from user:', userId);
    
    await preferencesService.deletePreferences(userId);
    
    res.json({
      status: 'success',
      message: 'AI preferences deleted successfully'
    });
  } catch (error) {
    console.error('[AI][Preferences] Failed to delete preferences:', error);
    res.status(500).json({ 
      status: 'error', 
      message: 'Failed to delete AI preferences' 
    });
  }
});

// Chat functionality
router.post('/chat', async (req, res) => {
  try {
    const { prompt, context } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }
    
    // AI service not implemented yet
    res.status(501).json({ 
      error: 'AI chat not implemented',
      message: 'This feature requires real AI API integration. Please add API keys in Settings first.',
      instructions: 'Go to Settings → AI Configuration to add OpenAI, Claude, or Gemini API keys'
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to process chat message' });
  }
});

// Conversation management
router.post('/conversations', async (req, res) => {
  try {
    const { userId, title } = req.body;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    const conversation = await aiService.createConversation(userId, title);
    res.status(201).json(conversation);
  } catch (error) {
    res.status(400).json({ error: 'Failed to create conversation' });
  }
});

router.get('/conversations', async (req, res) => {
  try {
    const { userId, limit } = req.query;
    
    if (!userId) {
      return res.status(400).json({ error: 'User ID is required' });
    }
    
    const conversations = await aiService.getConversations(userId, { limit: parseInt(limit) });
    res.json(conversations);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch conversations' });
  }
});

router.get('/conversations/:id', async (req, res) => {
  try {
    const conversation = await aiService.getConversationById(req.params.id);
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    
    res.json(conversation);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch conversation' });
  }
});

router.post('/conversations/:id/messages', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const message = req.body;
    
    const newMessage = await aiService.addMessageToConversation(conversationId, message);
    
    if (!newMessage) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    
    res.status(201).json(newMessage);
  } catch (error) {
    res.status(400).json({ error: 'Failed to add message to conversation' });
  }
});

router.delete('/conversations/:id', async (req, res) => {
  try {
    const deleted = await aiService.deleteConversation(req.params.id);
    
    if (!deleted) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    
    res.json({ message: 'Conversation deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete conversation' });
  }
});

// Content analysis
router.post('/analyze', async (req, res) => {
  try {
    const { content, analysisType } = req.body;
    
    if (!content) {
      return res.status(400).json({ error: 'Content is required' });
    }
    
    const analysis = await aiService.analyzeContent(content, analysisType);
    res.json(analysis);
  } catch (error) {
    res.status(500).json({ error: 'Failed to analyze content' });
  }
});

// Template management
router.post('/templates', async (req, res) => {
  try {
    const template = await aiService.createTemplate(req.body);
    res.status(201).json(template);
  } catch (error) {
    res.status(400).json({ error: 'Failed to create template' });
  }
});

router.get('/templates', async (req, res) => {
  try {
    const templates = await aiService.getTemplates(req.query);
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch templates' });
  }
});

router.get('/templates/:id', async (req, res) => {
  try {
    const template = await aiService.getTemplateById(req.params.id);
    
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    
    res.json(template);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch template' });
  }
});

router.put('/templates/:id', async (req, res) => {
  try {
    const template = await aiService.updateTemplate(req.params.id, req.body);
    
    if (!template) {
      return res.status(404).json({ error: 'Template not found' });
    }
    
    res.json(template);
  } catch (error) {
    res.status(400).json({ error: 'Failed to update template' });
  }
});

router.delete('/templates/:id', async (req, res) => {
  try {
    const deleted = await aiService.deleteTemplate(req.params.id);
    
    if (!deleted) {
      return res.status(404).json({ error: 'Template not found' });
    }
    
    res.json({ message: 'Template deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete template' });
  }
});

// Content generation
router.post('/generate', async (req, res) => {
  try {
    const { prompt, contentType, options } = req.body;
    
    if (!prompt) {
      return res.status(400).json({ error: 'Prompt is required' });
    }
    
    const content = await aiService.generateContent(prompt, contentType, options);
    res.json(content);
  } catch (error) {
    res.status(500).json({ error: 'Failed to generate content' });
  }
});

// Content optimization
router.post('/optimize', async (req, res) => {
  try {
    const { content, optimizationType } = req.body;
    
    if (!content) {
      return res.status(400).json({ error: 'Content is required' });
    }
    
    const optimization = await aiService.optimizeContent(content, optimizationType);
    res.json(optimization);
  } catch (error) {
    res.status(500).json({ error: 'Failed to optimize content' });
  }
});

// Predictions
router.post('/predict', async (req, res) => {
  try {
    const { data, predictionType } = req.body;
    
    if (!data) {
      return res.status(400).json({ error: 'Data is required' });
    }
    
    const predictions = await aiService.getPredictions(data, predictionType);
    res.json(predictions);
  } catch (error) {
    res.status(500).json({ error: 'Failed to generate predictions' });
  }
});

// Usage analytics
router.get('/usage', async (req, res) => {
  try {
    const { timeRange } = req.query;
    const usage = await aiService.getUsageAnalytics(timeRange);
    res.json(usage);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch usage analytics' });
  }
});

// Available models
router.get('/models', async (req, res) => {
  try {
    console.log('[AI] Available models requested');
    
    // Return safe response - no models available until configured
    const models = {
      models: [],
      providers: {
        openai: { available: false, reason: 'Not configured - add API key in Settings' },
        claude: { available: false, reason: 'Not configured - add API key in Settings' },
        gemini: { available: false, reason: 'Not configured - add API key in Settings' }
      },
      message: 'Configure API keys in Settings to enable AI features',
      timestamp: new Date().toISOString()
    };
    
    res.status(200).json(models);
  } catch (error) {
    console.error('[AI] Models fetch error:', error);
    res.status(200).json({ 
      models: [],
      message: 'AI models not available. Configure API keys in Settings.',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Service status
router.get('/status', async (req, res) => {
  try {
    console.log('[AI] Status check requested');
    
    // Check if user has configured any AI providers
    const userId = req.headers['x-user-id'];
    const configId = req.headers['x-config-id'];
    
    let hasConfiguredProvider = false;
    let configuredProviders = [];
    
    if (userId) {
      try {
        const prefs = await preferencesService.getPreferences(userId);
        if (prefs) {
          if (prefs.has_openai_key) configuredProviders.push('openai');
          if (prefs.has_claude_key) configuredProviders.push('claude');
          if (prefs.has_gemini_key) configuredProviders.push('gemini');
          hasConfiguredProvider = configuredProviders.length > 0;
        }
      } catch (prefError) {
        console.warn('[AI] Could not fetch preferences:', prefError.message);
      }
    }
    
    // Return safe status response
    const status = {
      status: hasConfiguredProvider ? 'configured' : 'not_configured',
      message: hasConfiguredProvider 
        ? `AI service is configured with ${configuredProviders.length} provider(s)`
        : 'AI service not yet connected. Please add API keys in Settings.',
      availableModels: [],
      configuredProviders,
      usage: {
        totalRequests: 0,
        totalTokens: 0,
        byModel: {},
        byType: {}
      },
      timestamp: new Date().toISOString(),
      instructions: hasConfiguredProvider 
        ? 'AI features are ready to use'
        : 'Go to Settings → AI Configuration to add OpenAI, Claude, or Gemini API keys'
    };
    
    res.status(200).json(status);
  } catch (error) {
    console.error('[AI] Status check error:', error);
    // Even on error, return 200 with safe response
    res.status(200).json({ 
      status: 'not_configured',
      message: 'AI service requires configuration. Add API keys in Settings.',
      error: error.message,
      timestamp: new Date().toISOString(),
      instructions: 'Go to Settings → AI Configuration to enable AI features'
    });
  }
});

module.exports = router;
