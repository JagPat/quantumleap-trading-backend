const express = require('express');
const aiService = require('../services');
const AIPreferencesService = require('../services/preferences');

const router = express.Router();
const preferencesService = new AIPreferencesService();

// Health check
router.get('/health', async (req, res) => {
  try {
    const health = await aiService.healthCheck();
    res.json(health);
  } catch (error) {
    res.status(500).json({ error: 'AI service health check failed' });
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
    
    const response = await aiService.sendMessage(prompt, context);
    res.json(response);
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
    const models = await aiService.getAvailableModels();
    res.json(models);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch available models' });
  }
});

// Service status
router.get('/status', async (req, res) => {
  try {
    const status = await aiService.getServiceStatus();
    res.json(status);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch service status' });
  }
});

module.exports = router;
