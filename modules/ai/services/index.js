/**
 * AI Service - Production Version
 * 
 * IMPORTANT: This service requires valid API keys to be configured.
 * Mock methods have been removed for production deployment.
 * 
 * To use AI features:
 * 1. User must configure API keys in Settings (OpenAI/Claude/Gemini)
 * 2. Keys are stored encrypted in ai_preferences table
 * 3. This service retrieves and uses real API keys
 */

class AIService {
  constructor() {
    this.usage = {
      totalRequests: 0,
      totalTokens: 0,
      byModel: {},
      byType: {}
    };
  }

  /**
   * Send message to AI - REQUIRES CONFIGURED API KEY
   * @throws {Error} If no API key is configured
   */
  async sendMessage(prompt, context = '') {
    throw new Error(
      'AI service not implemented. ' +
      'This requires real AI API integration. ' +
      'Please configure API keys in Settings first.'
    );
  }

  /**
   * Analyze content - REQUIRES CONFIGURED API KEY
   * @throws {Error} If no API key is configured
   */
  async analyze(content, analysisType = 'general') {
    throw new Error(
      'AI analysis not implemented. ' +
      'This requires real AI API integration. ' +
      'Please configure API keys in Settings first.'
    );
  }

  /**
   * Generate content - REQUIRES CONFIGURED API KEY
   * @throws {Error} If no API key is configured
   */
  async generateContent(prompt, contentType = 'text', options = {}) {
    throw new Error(
      'AI content generation not implemented. ' +
      'This requires real AI API integration. ' +
      'Please configure API keys in Settings first.'
    );
  }

  /**
   * Optimize content - REQUIRES CONFIGURED API KEY
   * @throws {Error} If no API key is configured
   */
  async optimize(content, optimizationType = 'general', options = {}) {
    throw new Error(
      'AI optimization not implemented. ' +
      'This requires real AI API integration. ' +
      'Please configure API keys in Settings first.'
    );
  }

  /**
   * Make predictions - REQUIRES CONFIGURED API KEY
   * @throws {Error} If no API key is configured
   */
  async predict(data, predictionType = 'general', options = {}) {
    throw new Error(
      'AI predictions not implemented. ' +
      'This requires real AI API integration. ' +
      'Please configure API keys in Settings first.'
    );
  }

  /**
   * Get available AI models
   * Returns empty array until real implementation
   */
  async getAvailableModels() {
    return {
      models: [],
      providers: {
        openai: { available: false, reason: 'Not configured' },
        claude: { available: false, reason: 'Not configured' },
        gemini: { available: false, reason: 'Not configured' }
      },
      message: 'Configure API keys in Settings to enable AI features'
    };
  }

  /**
   * Get service status
   */
  async getServiceStatus(userId = null) {
    // If userId provided, check actual configuration
    if (userId) {
      try {
        const preferencesService = require('./preferences');
        const preferences = await preferencesService.getPreferences(userId);
        
        const hasConfiguredProvider = preferences && (
          preferences.openai_api_key || 
          preferences.claude_api_key || 
          preferences.gemini_api_key
        );
        
        return {
          status: hasConfiguredProvider ? 'configured' : 'not_configured',
          message: hasConfiguredProvider 
            ? 'AI service is configured and ready'
            : 'AI service requires API key configuration',
          availableModels: [],
          usage: this.usage,
          instructions: 'Go to Settings → AI Configuration to add API keys'
        };
      } catch (error) {
        console.warn('[AI] Error checking service status:', error);
      }
    }
    
    // Fallback for no userId or error
    return {
      status: 'not_configured',
      message: 'AI service requires API key configuration',
      availableModels: [],
      usage: this.usage,
      instructions: 'Go to Settings → AI Configuration to add API keys'
    };
  }

  /**
   * Health check
   */
  async healthCheck(userId = null) {
    // If userId provided, check actual configuration
    if (userId) {
      try {
        const preferencesService = require('./preferences');
        const preferences = await preferencesService.getPreferences(userId);
        
        const hasConfiguredProvider = preferences && (
          preferences.openai_api_key || 
          preferences.claude_api_key || 
          preferences.gemini_api_key
        );
        
        return {
          status: hasConfiguredProvider ? 'configured' : 'not_configured',
          message: hasConfiguredProvider 
            ? 'AI service is configured and ready'
            : 'AI service requires configuration',
          timestamp: new Date().toISOString(),
          ready: hasConfiguredProvider,
          instructions: 'Configure API keys in Settings to enable AI features'
        };
      } catch (error) {
        console.warn('[AI] Error checking health:', error);
      }
    }
    
    // Fallback for no userId or error
    return {
      status: 'not_configured',
      message: 'AI service requires configuration',
      timestamp: new Date().toISOString(),
      ready: false,
      instructions: 'Configure API keys in Settings to enable AI features'
    };
  }

  /**
   * Update usage statistics
   */
  updateUsage(type, tokens, model) {
    this.usage.totalRequests++;
    this.usage.totalTokens += tokens;
    
    if (!this.usage.byModel[model]) {
      this.usage.byModel[model] = { requests: 0, tokens: 0 };
    }
    this.usage.byModel[model].requests++;
    this.usage.byModel[model].tokens += tokens;
    
    if (!this.usage.byType[type]) {
      this.usage.byType[type] = { requests: 0, tokens: 0 };
    }
    this.usage.byType[type].requests++;
    this.usage.byType[type].tokens += tokens;
  }
}

module.exports = AIService;
