const { getAIAgentRouter } = require('./aiAgentRouter');
const { getPortfolioActionEngine } = require('./portfolioActionEngine');
const { ResearchIngestionService } = require('./researchIngestionService');
const { MarketRegimeAnalyzer } = require('./marketRegimeAnalyzer');
const db = require('../../../core/database/connection');

/**
 * AI Chat Service
 * Handles conversational AI for portfolio, strategy, and market queries
 * Provides context-aware responses with attribution
 */
class AIChatService {
  constructor() {
    this.aiRouter = null;
    this.portfolioEngine = null;
    this.researchService = null;
    this.regimeAnalyzer = null;
  }

  /**
   * Initialize service dependencies
   */
  async initialize() {
    try {
      this.aiRouter = getAIAgentRouter();
      this.portfolioEngine = getPortfolioActionEngine();
      this.researchService = new ResearchIngestionService();
      this.regimeAnalyzer = new MarketRegimeAnalyzer();
      
      console.log('[AIChatService] Initialized successfully');
    } catch (error) {
      console.error('[AIChatService] Initialization error:', error);
      throw error;
    }
  }

  /**
   * Process chat message with context
   * @param {Object} params - Chat parameters
   * @returns {Object} AI response with attribution
   */
  async processMessage(params) {
    const {
      userId,
      message,
      context = {},
      history = []
    } = params;

    try {
      // Gather context data based on page/context
      const contextData = await this.gatherContextData(userId, context);

      // Build enhanced prompt with context
      const enhancedPrompt = await this.buildPrompt(message, context, contextData, history);

      // Get AI response
      const aiResponse = await this.aiRouter.chat(enhancedPrompt, {
        userId,
        temperature: 0.7,
        maxTokens: 500
      });

      // Generate smart suggestions
      const suggestions = this.generateSuggestions(context, contextData);

      // Build attribution
      const attribution = this.buildAttribution(contextData);

      return {
        success: true,
        response: aiResponse,
        suggestions,
        attribution
      };
    } catch (error) {
      console.error('[AIChatService] Error processing message:', error);
      return {
        success: false,
        error: error.message,
        response: this.getFallbackResponse(message, context)
      };
    }
  }

  /**
   * Gather relevant context data
   * @param {number} userId - User ID
   * @param {Object} context - Page context
   * @returns {Object} Context data
   */
  async gatherContextData(userId, context) {
    const data = {
      page: context.page || 'unknown'
    };

    try {
      // Get market regime
      try {
        const regime = await this.regimeAnalyzer.detectCurrentRegime();
        data.marketRegime = regime;
      } catch (err) {
        console.warn('[AIChatService] Market regime unavailable:', err.message);
      }

      // Get portfolio data if relevant
      if (context.page === 'portfolio' || context.holdingSymbol) {
        try {
          const portfolioQuery = `
            SELECT * FROM holdings 
            WHERE user_id = $1 
            ORDER BY current_value DESC 
            LIMIT 10
          `;
          const result = await db.query(portfolioQuery, [userId]);
          data.holdings = result.rows;

          // Get portfolio summary
          if (result.rows.length > 0) {
            const totalValue = result.rows.reduce((sum, h) => sum + parseFloat(h.current_value || 0), 0);
            const totalPnL = result.rows.reduce((sum, h) => sum + parseFloat(h.pnl || 0), 0);
            
            data.portfolioSummary = {
              totalValue,
              totalPnL,
              totalPnLPercent: totalValue > 0 ? (totalPnL / (totalValue - totalPnL)) * 100 : 0,
              holdingsCount: result.rows.length
            };
          }
        } catch (err) {
          console.warn('[AIChatService] Portfolio data unavailable:', err.message);
        }
      }

      // Get specific holding data
      if (context.holdingSymbol) {
        try {
          const holdingQuery = `
            SELECT * FROM holdings 
            WHERE user_id = $1 AND symbol = $2
          `;
          const result = await db.query(holdingQuery, [userId, context.holdingSymbol]);
          
          if (result.rows.length > 0) {
            data.specificHolding = result.rows[0];
            
            // Get research for this symbol
            try {
              const research = await this.researchService.getLatestResearch(context.holdingSymbol);
              data.holdingResearch = research;
            } catch (err) {
              console.warn('[AIChatService] Research unavailable for', context.holdingSymbol);
            }
          }
        } catch (err) {
          console.warn('[AIChatService] Holding data unavailable:', err.message);
        }
      }

      // Get strategy data if relevant
      if (context.strategyId) {
        try {
          const strategyQuery = `
            SELECT * FROM strategy_automations 
            WHERE id = $1 AND user_id = $2
          `;
          const result = await db.query(strategyQuery, [context.strategyId, userId]);
          
          if (result.rows.length > 0) {
            data.strategy = result.rows[0];
          }
        } catch (err) {
          console.warn('[AIChatService] Strategy data unavailable:', err.message);
        }
      }

      // Get execution data if relevant
      if (context.executionId) {
        try {
          const executionQuery = `
            SELECT * FROM strategy_executions 
            WHERE id = $1
          `;
          const result = await db.query(executionQuery, [context.executionId]);
          
          if (result.rows.length > 0) {
            data.execution = result.rows[0];
          }
        } catch (err) {
          console.warn('[AIChatService] Execution data unavailable:', err.message);
        }
      }

      return data;
    } catch (error) {
      console.error('[AIChatService] Error gathering context:', error);
      return data;
    }
  }

  /**
   * Build enhanced prompt with context
   * @param {string} message - User message
   * @param {Object} context - Page context
   * @param {Object} contextData - Gathered data
   * @param {Array} history - Message history
   * @returns {string} Enhanced prompt
   */
  async buildPrompt(message, context, contextData, history) {
    let prompt = `You are an AI trading assistant for QuantumLeap platform. You help users understand their portfolio, strategies, and market conditions.

Current Context:
- Page: ${contextData.page}`;

    // Add market regime
    if (contextData.marketRegime) {
      prompt += `
- Market Regime: ${contextData.marketRegime.regime} (${Math.round(contextData.marketRegime.confidence * 100)}% confidence)
- Market Strategy: ${contextData.marketRegime.recommendedStrategy}`;
    }

    // Add portfolio context
    if (contextData.portfolioSummary) {
      prompt += `
- Portfolio Value: ₹${contextData.portfolioSummary.totalValue.toLocaleString()}
- Portfolio P&L: ₹${contextData.portfolioSummary.totalPnL.toLocaleString()} (${contextData.portfolioSummary.totalPnLPercent.toFixed(2)}%)
- Holdings Count: ${contextData.portfolioSummary.holdingsCount}`;
    }

    // Add specific holding context
    if (contextData.specificHolding) {
      const holding = contextData.specificHolding;
      prompt += `
- Stock: ${holding.symbol}
- Quantity: ${holding.quantity} shares
- Current Value: ₹${holding.current_value}
- P&L: ₹${holding.pnl} (${holding.pnl_percent}%)`;

      if (contextData.holdingResearch) {
        prompt += `
- Recent News: ${contextData.holdingResearch.newsCount || 0} articles
- Sentiment: ${contextData.holdingResearch.sentiment || 'neutral'}`;
      }
    }

    // Add strategy context
    if (contextData.strategy) {
      prompt += `
- Strategy: ${contextData.strategy.name}
- Target: ${contextData.strategy.profit_target_percent}% in ${contextData.strategy.timeframe_days} days
- Confidence: ${Math.round(contextData.strategy.ai_confidence_score * 100)}%`;
    }

    // Add conversation history (last 3 messages)
    if (history.length > 0) {
      prompt += `\n\nRecent Conversation:`;
      history.slice(-3).forEach(msg => {
        prompt += `\n${msg.role === 'user' ? 'User' : 'AI'}: ${msg.content}`;
      });
    }

    // Add user question
    prompt += `\n\nUser Question: ${message}

Please provide a helpful, concise response (2-3 sentences). Be specific and actionable. Use the context provided above.

Response:`;

    return prompt;
  }

  /**
   * Generate smart suggestions based on context
   * @param {Object} context - Page context
   * @param {Object} contextData - Gathered data
   * @returns {Array} Suggestion strings
   */
  generateSuggestions(context, contextData) {
    const suggestions = [];

    if (context.page === 'portfolio') {
      suggestions.push('What are my best performing stocks?');
      suggestions.push('Should I rebalance my portfolio?');
      
      if (contextData.portfolioSummary) {
        if (contextData.portfolioSummary.totalPnL > 0) {
          suggestions.push('Should I book profits?');
        } else {
          suggestions.push('How can I improve my portfolio?');
        }
      }
    }

    if (context.holdingSymbol) {
      suggestions.push(`What's the outlook for ${context.holdingSymbol}?`);
      suggestions.push(`Should I buy more ${context.holdingSymbol}?`);
    }

    if (context.page === 'strategy') {
      suggestions.push('How does this strategy compare to others?');
      suggestions.push('What are the risks?');
    }

    if (contextData.marketRegime) {
      suggestions.push(`What should I do in ${contextData.marketRegime.regime} market?`);
    }

    return suggestions.slice(0, 3); // Return max 3 suggestions
  }

  /**
   * Build attribution object
   * @param {Object} contextData - Gathered data
   * @returns {Object} Attribution
   */
  buildAttribution(contextData) {
    const attribution = {};

    if (contextData.holdings) {
      attribution.portfolio = 'Live portfolio data';
    }

    if (contextData.marketRegime) {
      attribution.marketRegime = 'AI-detected market regime';
    }

    if (contextData.holdingResearch) {
      attribution.research = 'Latest news and sentiment data';
    }

    if (contextData.strategy) {
      attribution.strategy = 'Active strategy data';
    }

    return attribution;
  }

  /**
   * Get fallback response when AI fails
   * @param {string} message - User message
   * @param {Object} context - Context
   * @returns {string} Fallback response
   */
  getFallbackResponse(message, context) {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('portfolio') || lowerMessage.includes('holdings')) {
      return "I can help you analyze your portfolio. Please ensure you're connected to your broker to see your latest holdings.";
    }

    if (lowerMessage.includes('strategy') || lowerMessage.includes('trade')) {
      return "I can explain strategies and trading decisions. Would you like to know about a specific strategy?";
    }

    if (lowerMessage.includes('market') || lowerMessage.includes('stock')) {
      return "I analyze market conditions and stock performance. Which stock or sector would you like to know about?";
    }

    return "I'm your AI trading assistant. I can help with portfolio analysis, strategy explanations, and market insights. What would you like to know?";
  }
}

// Singleton instance
let chatServiceInstance = null;

/**
 * Get AI Chat Service instance
 * @returns {AIChatService}
 */
function getAIChatService() {
  if (!chatServiceInstance) {
    chatServiceInstance = new AIChatService();
  }
  return chatServiceInstance;
}

module.exports = {
  AIChatService,
  getAIChatService
};

