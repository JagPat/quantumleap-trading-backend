/**
 * Portfolio Review Engine
 * Generates AI recommendations for each holding in the portfolio
 * Enhances existing PortfolioActionEngine with per-holding analysis
 */

const { getAIAgentRouter } = require('./aiAgentRouter');
const { getPortfolioActionEngine } = require('./portfolioActionEngine');

class PortfolioReviewEngine {
  constructor() {
    this.aiRouter = null;
    this.portfolioEngine = null;
  }

  /**
   * Initialize services (lazy loading)
   */
  async initialize() {
    if (!this.aiRouter) {
      this.aiRouter = getAIAgentRouter();
    }
    if (!this.portfolioEngine) {
      this.portfolioEngine = getPortfolioActionEngine();
    }
  }

  /**
   * Generate AI recommendations for all holdings
   * @param {object} portfolioData - Portfolio data with holdings
   * @param {object} goal - Optional goal context
   * @returns {Promise<Array>} Array of holding recommendations
   */
  async reviewPortfolio(portfolioData, goal = null) {
    try {
      await this.initialize();

      console.log('[PortfolioReviewEngine] Reviewing portfolio with', portfolioData.holdings?.length, 'holdings');

      if (!portfolioData || !portfolioData.holdings || portfolioData.holdings.length === 0) {
        return [];
      }

      // Get portfolio-level actions from existing engine
      const portfolioActions = await this.portfolioEngine.analyzeAndSuggestActions(
        portfolioData,
        goal
      );

      // Map actions to holdings
      const holdingsWithActions = [];

      for (const holding of portfolioData.holdings) {
        const symbol = holding.symbol || holding.tradingsymbol;
        
        // Find matching action
        const matchingAction = portfolioActions.actions?.find(
          action => action.symbol === symbol || action.tradingsymbol === symbol
        );

        if (matchingAction) {
          // Add action to holding
          holdingsWithActions.push({
            ...holding,
            ai_recommendation: {
              type: matchingAction.type,
              priority: matchingAction.priority,
              reason: matchingAction.reason,
              reasoning: matchingAction.reasoning,
              currentWeight: matchingAction.currentWeight,
              idealWeight: matchingAction.idealWeight,
              delta: matchingAction.delta,
              suggestedAction: matchingAction.suggestedAction,
              research_signals: matchingAction.research_signals,
              data_sources: matchingAction.data_sources,
              confidence: matchingAction.confidence,
            },
          });
        } else {
          // No specific action - mark as HOLD
          holdingsWithActions.push({
            ...holding,
            ai_recommendation: {
              type: 'HOLD',
              priority: 'LOW',
              reason: 'Position is well-balanced',
              reasoning: 'Current allocation is appropriate for your portfolio',
              confidence: 0.7,
            },
          });
        }
      }

      return holdingsWithActions;

    } catch (error) {
      console.error('[PortfolioReviewEngine] Error reviewing portfolio:', error);
      throw error;
    }
  }

  /**
   * Get recommendation for a single holding
   * @param {object} holding - Holding data
   * @param {object} portfolioData - Full portfolio context
   * @returns {Promise<object>} Recommendation
   */
  async getHoldingRecommendation(holding, portfolioData) {
    try {
      await this.initialize();

      const symbol = holding.symbol || holding.tradingsymbol;
      console.log('[PortfolioReviewEngine] Getting recommendation for', symbol);

      // Review entire portfolio to get context
      const holdingsWithActions = await this.reviewPortfolio(portfolioData);

      // Find this holding
      const holdingWithAction = holdingsWithActions.find(h => 
        (h.symbol || h.tradingsymbol) === symbol
      );

      if (holdingWithAction) {
        return holdingWithAction.ai_recommendation;
      }

      // Default HOLD
      return {
        type: 'HOLD',
        priority: 'LOW',
        reason: 'No specific recommendation available',
        confidence: 0.5,
      };

    } catch (error) {
      console.error('[PortfolioReviewEngine] Error getting holding recommendation:', error);
      throw error;
    }
  }

  /**
   * Calculate portfolio health score
   * @param {object} portfolioData - Portfolio data
   * @param {Array} actions - AI actions
   * @returns {number} Health score (0-100)
   */
  calculateHealthScore(portfolioData, actions) {
    try {
      if (!actions || actions.length === 0) {
        return 100; // Perfect health if no actions needed
      }

      // Deduct points based on priority
      let score = 100;
      
      actions.forEach(action => {
        if (action.priority === 'HIGH') {
          score -= 15;
        } else if (action.priority === 'MEDIUM') {
          score -= 5;
        } else if (action.priority === 'LOW') {
          score -= 2;
        }
      });

      // Minimum score is 50
      return Math.max(score, 50);

    } catch (error) {
      console.error('[PortfolioReviewEngine] Error calculating health score:', error);
      return 75; // Default moderate score
    }
  }
}

// Singleton instance
let portfolioReviewEngineInstance = null;

function getPortfolioReviewEngine() {
  if (!portfolioReviewEngineInstance) {
    portfolioReviewEngineInstance = new PortfolioReviewEngine();
  }
  return portfolioReviewEngineInstance;
}

module.exports = {
  PortfolioReviewEngine,
  getPortfolioReviewEngine,
};

