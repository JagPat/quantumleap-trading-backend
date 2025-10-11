/**
 * AI Agent Router
 * Intelligent routing layer for multi-agent AI system
 * Routes requests to specialized engines based on task type
 */

const StrategyEngine = require('./strategyEngine');
const GoalSuggestionEngine = require('./goalSuggestionEngine');
const ExecutionEngine = require('./executionEngine');
const AIPreferencesService = require('./preferences');

class AIAgentRouter {
  constructor() {
    this.strategyEngine = new StrategyEngine();
    this.goalEngine = new GoalSuggestionEngine();
    this.executionEngine = require('./executionEngine'); // Singleton
    this.preferencesService = new AIPreferencesService();
    this.portfolioEngine = null; // Will be set when PortfolioActionEngine is created
    
    // Task type to engine mapping
    this.engineMapping = {
      'strategy': 'strategyEngine',
      'goals': 'goalEngine',
      'portfolio_action': 'portfolioEngine',
      'execution': 'executionEngine',
      'portfolio_analysis': 'portfolioEngine',
      'rebalance': 'portfolioEngine'
    };
    
    console.log('[AIAgentRouter] Initialized with multi-agent routing');
  }

  /**
   * Set portfolio engine when it's available
   */
  setPortfolioEngine(engine) {
    this.portfolioEngine = engine;
    console.log('[AIAgentRouter] Portfolio engine registered');
  }

  /**
   * Route request to appropriate AI agent/engine
   * @param {string} taskType - Type of task (strategy|goals|portfolio_action|execution)
   * @param {Object} request - Request payload
   * @param {string} userId - User ID
   * @param {string} configId - Broker config ID
   * @returns {Object} Response from the appropriate engine
   */
  async route(taskType, request, userId, configId = null) {
    try {
      console.log(`[AIAgentRouter] Routing ${taskType} request for user ${userId}`);
      
      // Get user preferences to determine provider selection
      const preferences = await this.preferencesService.getPreferences(userId);
      
      // Select appropriate provider based on task type and user preferences
      const provider = this.selectProvider(taskType, preferences);
      
      // Get the engine for this task type
      const engineName = this.engineMapping[taskType];
      if (!engineName) {
        throw new Error(`Unknown task type: ${taskType}`);
      }
      
      const engine = this[engineName];
      if (!engine) {
        throw new Error(`Engine not available for task type: ${taskType}`);
      }
      
      // Route to appropriate engine based on task type
      let result;
      
      switch(taskType) {
        case 'strategy':
          result = await this.strategyEngine.generateGoalBasedStrategy(
            request,
            preferences,
            request.portfolioContext || null
          );
          break;
          
        case 'goals':
          result = await this.goalEngine.suggestGoals(
            userId,
            configId,
            request.portfolioData || {}
          );
          break;
          
        case 'portfolio_action':
        case 'portfolio_analysis':
        case 'rebalance':
          if (!this.portfolioEngine) {
            throw new Error('Portfolio engine not yet implemented');
          }
          result = await this.portfolioEngine.analyzeAndSuggestActions(
            request.portfolioData,
            request.goal || null
          );
          break;
          
        case 'execution':
          result = await this.executionEngine.executeStrategy(
            request.strategyId,
            request.mode || 'paper'
          );
          break;
          
        default:
          throw new Error(`Unhandled task type: ${taskType}`);
      }
      
      console.log(`[AIAgentRouter] ${taskType} request completed successfully`);
      
      return {
        success: true,
        taskType,
        engine: engineName,
        provider: provider,
        result,
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      console.error(`[AIAgentRouter] Error routing ${taskType}:`, error);
      throw error;
    }
  }

  /**
   * Select AI provider based on task type and user preferences
   * @param {string} taskType - Type of task
   * @param {Object} preferences - User AI preferences
   * @returns {string} Provider name (openai|claude|mistral)
   */
  selectProvider(taskType, preferences) {
    if (!preferences) {
      return 'openai'; // Default fallback
    }
    
    // Map task type to preference field
    const providerMapping = {
      'strategy': preferences.strategy_provider || preferences.preferred_ai_provider,
      'goals': preferences.goal_provider || preferences.preferred_ai_provider,
      'portfolio_action': preferences.portfolio_provider || preferences.preferred_ai_provider,
      'portfolio_analysis': preferences.portfolio_provider || preferences.preferred_ai_provider,
      'rebalance': preferences.portfolio_provider || preferences.preferred_ai_provider,
      'execution': preferences.preferred_ai_provider
    };
    
    const selectedProvider = providerMapping[taskType] || preferences.preferred_ai_provider || 'openai';
    
    // Verify the provider has API key configured
    const hasKey = this.hasProviderKey(selectedProvider, preferences);
    
    if (!hasKey) {
      console.warn(`[AIAgentRouter] ${selectedProvider} not configured, falling back`);
      return this.findAvailableProvider(preferences);
    }
    
    console.log(`[AIAgentRouter] Selected ${selectedProvider} for ${taskType}`);
    return selectedProvider;
  }

  /**
   * Check if provider has API key configured
   */
  hasProviderKey(provider, preferences) {
    const keyMapping = {
      'openai': preferences.openai_api_key,
      'claude': preferences.claude_api_key,
      'mistral': preferences.mistral_api_key
    };
    return !!keyMapping[provider];
  }

  /**
   * Find first available provider with configured API key
   */
  findAvailableProvider(preferences) {
    if (preferences.openai_api_key) return 'openai';
    if (preferences.claude_api_key) return 'claude';
    if (preferences.mistral_api_key) return 'mistral';
    
    throw new Error('No AI provider configured. Please add API keys in Settings.');
  }

  /**
   * Get routing statistics
   */
  getStats() {
    return {
      availableEngines: Object.keys(this.engineMapping),
      engineStatus: {
        strategy: !!this.strategyEngine,
        goals: !!this.goalEngine,
        execution: !!this.executionEngine,
        portfolio: !!this.portfolioEngine
      }
    };
  }
}

// Export singleton instance
let instance = null;

const getAIAgentRouter = () => {
  if (!instance) {
    instance = new AIAgentRouter();
  }
  return instance;
};

module.exports = getAIAgentRouter;

