/**
 * AI Provider Factory
 * Creates and manages AI provider instances (OpenAI, Claude, Mistral)
 */

const OpenAIProvider = require('./openai');

class ProviderFactory {
  constructor() {
    this.providers = new Map();
  }

  /**
   * Get or create AI provider instance
   * @param {string} providerName - Provider name (openai|claude|mistral)
   * @param {string} apiKey - API key for the provider
   * @param {Object} options - Provider options
   * @returns {Object} Provider instance
   */
  getProvider(providerName, apiKey, options = {}) {
    if (!apiKey) {
      throw new Error(`API key required for ${providerName}`);
    }

    // Create cache key
    const cacheKey = `${providerName}:${apiKey.substring(0, 10)}`;
    
    // Return cached instance if available
    if (this.providers.has(cacheKey)) {
      return this.providers.get(cacheKey);
    }

    // Create new provider instance
    let provider;
    
    switch(providerName.toLowerCase()) {
      case 'openai':
        provider = new OpenAIProvider(apiKey, options);
        break;
        
      case 'claude':
        // Claude provider will be implemented
        const ClaudeProvider = require('./claude');
        provider = new ClaudeProvider(apiKey, options);
        break;
        
      case 'mistral':
        // Mistral uses OpenAI-compatible API
        provider = new OpenAIProvider(apiKey, {
          ...options,
          baseURL: 'https://api.mistral.ai/v1',
          model: options.model || 'mistral-large-latest'
        });
        break;
        
      default:
        throw new Error(`Unsupported provider: ${providerName}`);
    }

    // Cache the provider
    this.providers.set(cacheKey, provider);
    
    console.log(`[ProviderFactory] Created ${providerName} provider instance`);
    return provider;
  }

  /**
   * Get provider for specific task based on preferences
   * @param {string} taskType - Task type
   * @param {Object} preferences - User AI preferences
   * @returns {Object} Provider instance
   */
  getProviderForTask(taskType, preferences) {
    const providerName = this.selectProviderForTask(taskType, preferences);
    const apiKey = this.getApiKey(providerName, preferences);
    
    if (!apiKey) {
      throw new Error(`No API key configured for ${providerName}`);
    }
    
    return this.getProvider(providerName, apiKey);
  }

  /**
   * Select provider based on task type and preferences
   */
  selectProviderForTask(taskType, preferences) {
    const mapping = {
      'strategy': preferences.strategy_provider,
      'goals': preferences.goal_provider,
      'portfolio': preferences.portfolio_provider,
      'default': preferences.preferred_ai_provider
    };
    
    return mapping[taskType] || mapping.default || 'openai';
  }

  /**
   * Get API key for provider
   */
  getApiKey(providerName, preferences) {
    const keyMapping = {
      'openai': preferences.openai_api_key,
      'claude': preferences.claude_api_key,
      'mistral': preferences.mistral_api_key
    };
    
    return keyMapping[providerName];
  }

  /**
   * Clear provider cache (for testing or key rotation)
   */
  clearCache() {
    this.providers.clear();
    console.log('[ProviderFactory] Provider cache cleared');
  }

  /**
   * Get available providers based on configured keys
   */
  getAvailableProviders(preferences) {
    const available = [];
    
    if (preferences.openai_api_key) available.push('openai');
    if (preferences.claude_api_key) available.push('claude');
    if (preferences.mistral_api_key) available.push('mistral');
    
    return available;
  }
}

// Export singleton instance
let instance = null;

const getProviderFactory = () => {
  if (!instance) {
    instance = new ProviderFactory();
  }
  return instance;
};

module.exports = getProviderFactory;

