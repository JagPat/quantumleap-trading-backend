/**
 * Portfolio Action Engine
 * Analyzes portfolio and suggests actions: ACCUMULATE, DILUTE, EXIT, REBALANCE
 * Goal-centric portfolio optimization
 */

const getProviderFactory = require('./providers/providerFactory');
const getMarketUniverse = require('./marketUniverse');
const AIPreferencesService = require('./preferences');

class PortfolioActionEngine {
  constructor() {
    this.providerFactory = getProviderFactory();
    this.marketUniverse = getMarketUniverse();
    this.preferencesService = new AIPreferencesService();
    
    // Thresholds for action suggestions
    this.thresholds = {
      overweight: 0.25,      // 25% - suggest dilution
      underweight: 0.05,     // 5% - suggest accumulation
      concentrationRisk: 0.30, // 30% - suggest rebalance
      minAllocation: 0.02    // 2% - minimum meaningful position
    };
  }

  /**
   * Analyze portfolio and suggest actions to achieve goal
   * ENHANCED with research data + market regime context
   * @param {Object} portfolioData - Current portfolio
   * @param {Object} goal - User's trading goal (optional)
   * @param {string} userId - User ID for attribution tracking
   * @returns {Object} Suggested actions with reasoning
   */
  async analyzeAndSuggestActions(portfolioData, goal = null, userId = null) {
    try {
      console.log('[PortfolioActionEngine] Analyzing portfolio for action suggestions (research-enhanced)');
      
      // ✅ NEW: Initialize research and regime services
      const ResearchIngestionService = require('./researchIngestionService');
      const MarketRegimeAnalyzer = require('./marketRegimeAnalyzer');
      const FeedbackIntegrationService = require('./feedbackIntegrationService');
      const DecisionAttributionTracker = require('./decisionAttributionTracker');
      
      const researchService = new ResearchIngestionService();
      const regimeAnalyzer = new MarketRegimeAnalyzer();
      const feedbackService = new FeedbackIntegrationService();
      const attributionTracker = new DecisionAttributionTracker();
      
      // Calculate current portfolio weights
      const currentWeights = this.analyzeWeights(portfolioData);
      
      // ✅ NEW: Fetch market regime
      const currentRegime = await regimeAnalyzer.getActiveRegime();
      console.log(`[PortfolioActionEngine] Current market regime: ${currentRegime.regime}`);
      
      // ✅ NEW: Fetch research data for all holdings
      const holdings = currentWeights.holdings || [];
      const holdingsResearch = [];
      
      for (const holding of holdings) {
        try {
          const research = await researchService.getRelevantResearch(holding.symbol, 7);
          holdingsResearch.push({
            symbol: holding.symbol,
            currentWeight: holding.weight,
            research
          });
        } catch (error) {
          console.warn(`[PortfolioActionEngine] Could not fetch research for ${holding.symbol}`);
        }
      }
      
      // ✅ NEW: Get historical learnings
      const learnings = await feedbackService.getContextualLearnings(null, 'portfolio_action');
      
      // Calculate ideal allocation based on goal
      const idealAllocation = await this.calculateIdealAllocation(
        portfolioData,
        goal,
        currentWeights
      );
      
      // ✅ ENHANCED: Generate research-aware actions
      const actions = await this.generateResearchAwareActions(
        currentWeights,
        idealAllocation,
        portfolioData,
        holdingsResearch,
        currentRegime,
        goal
      );
      
      // Calculate risk impact of suggested actions
      const riskImpact = this.calculateRiskImpact(currentWeights, idealAllocation);
      
      // ✅ NEW: Store decision with attribution if userId provided
      if (userId && actions.length > 0) {
        await attributionTracker.recordPortfolioAction(
          userId,
          actions,
          currentRegime,
          holdingsResearch
        );
      }
      
      return {
        success: true,
        actions,
        currentWeights,
        idealWeights: idealAllocation.weights,
        riskImpact,
        summary: this.generateSummary(actions),
        regime: currentRegime, // ✅ NEW
        researchUsed: holdingsResearch.length, // ✅ NEW
        learningsApplied: learnings.length, // ✅ NEW
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      console.error('[PortfolioActionEngine] Error analyzing portfolio:', error);
      throw error;
    }
  }

  /**
   * Calculate current portfolio weights
   */
  analyzeWeights(portfolioData) {
    const holdings = portfolioData.holdings || [];
    const totalValue = portfolioData.summary?.total_value || 
                      portfolioData.summary?.totalValue || 
                      holdings.reduce((sum, h) => sum + (h.current_value || h.currentValue || 0), 0);
    
    if (totalValue === 0) {
      return { totalValue: 0, weights: {}, holdings: [] };
    }

    const weights = {};
    const holdingsWithWeights = [];

    for (const holding of holdings) {
      const symbol = holding.symbol || holding.tradingsymbol;
      const value = holding.current_value || holding.currentValue || 0;
      const weight = value / totalValue;
      
      weights[symbol] = weight;
      holdingsWithWeights.push({
        symbol,
        value,
        weight,
        quantity: holding.quantity || 0,
        avgPrice: holding.average_price || holding.avgPrice || 0,
        pnl: holding.pnl || 0,
        pnlPercent: ((holding.pnl || 0) / (holding.average_price || 1)) * 100
      });
    }

    // Calculate concentration metrics
    const maxWeight = Math.max(...Object.values(weights), 0);
    const top3Weight = holdingsWithWeights
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 3)
      .reduce((sum, h) => sum + h.weight, 0);

    return {
      totalValue,
      weights,
      holdings: holdingsWithWeights,
      concentrationMetrics: {
        maxSingleHolding: maxWeight,
        top3Concentration: top3Weight,
        numberOfHoldings: holdings.length,
        avgWeight: holdings.length > 0 ? 1 / holdings.length : 0
      }
    };
  }

  /**
   * Calculate ideal allocation based on goal
   */
  async calculateIdealAllocation(portfolioData, goal, currentWeights) {
    if (!goal) {
      // If no goal provided, suggest balanced diversification
      return this.suggestBalancedAllocation(currentWeights);
    }

    const riskTolerance = goal.riskTolerance || goal.risk_tolerance || 'moderate';
    const profitTarget = goal.profitTarget || goal.profit_target || 10;
    
    // Risk-based allocation profiles
    const allocationProfiles = {
      conservative: { maxSinglePosition: 0.15, minHoldings: 10, sectorMax: 0.25 },
      moderate: { maxSinglePosition: 0.20, minHoldings: 7, sectorMax: 0.35 },
      aggressive: { maxSinglePosition: 0.30, minHoldings: 5, sectorMax: 0.50 }
    };
    
    const profile = allocationProfiles[riskTolerance] || allocationProfiles.moderate;
    
    // Calculate ideal weights for current holdings
    const holdings = currentWeights.holdings || [];
    const idealWeights = {};
    
    // Simple equal-weight with risk constraints
    const targetWeight = Math.min(1 / Math.max(holdings.length, profile.minHoldings), profile.maxSinglePosition);
    
    for (const holding of holdings) {
      idealWeights[holding.symbol] = targetWeight;
    }

    return {
      weights: idealWeights,
      profile,
      riskTolerance,
      recommendedHoldings: profile.minHoldings
    };
  }

  /**
   * Suggest balanced allocation when no goal specified
   */
  suggestBalancedAllocation(currentWeights) {
    const holdings = currentWeights.holdings || [];
    const idealWeights = {};
    
    // Equal weight allocation
    const equalWeight = holdings.length > 0 ? 1 / holdings.length : 0;
    
    for (const holding of holdings) {
      idealWeights[holding.symbol] = equalWeight;
    }

    return {
      weights: idealWeights,
      profile: { maxSinglePosition: 0.20, minHoldings: 7, sectorMax: 0.35 },
      riskTolerance: 'moderate',
      recommendedHoldings: Math.max(holdings.length, 7)
    };
  }

  /**
   * Generate action suggestions based on weight comparison
   */
  generateActions(currentWeights, idealAllocation, portfolioData) {
    const actions = [];
    const currentHoldings = currentWeights.holdings || [];
    const idealWeights = idealAllocation.weights || {};

    // Check for overweight positions (DILUTE)
    for (const holding of currentHoldings) {
      const currentWeight = holding.weight;
      const idealWeight = idealWeights[holding.symbol] || 0;
      const delta = currentWeight - idealWeight;

      if (delta > this.thresholds.overweight) {
        actions.push({
          type: 'DILUTE',
          symbol: holding.symbol,
          currentWeight: (currentWeight * 100).toFixed(2) + '%',
          idealWeight: (idealWeight * 100).toFixed(2) + '%',
          delta: (delta * 100).toFixed(2) + '%',
          reason: `Overexposed by ${(delta * 100).toFixed(1)}% - Reduce position to manage concentration risk`,
          priority: delta > 0.35 ? 'HIGH' : 'MEDIUM',
          suggestedAction: `Sell ${((delta * currentWeights.totalValue) / holding.avgPrice).toFixed(0)} shares`,
          expectedValue: (delta * currentWeights.totalValue).toFixed(2)
        });
      }
      
      // Check for underweight positions (ACCUMULATE)
      if (delta < -this.thresholds.underweight && idealWeight > this.thresholds.minAllocation) {
        actions.push({
          type: 'ACCUMULATE',
          symbol: holding.symbol,
          currentWeight: (currentWeight * 100).toFixed(2) + '%',
          idealWeight: (idealWeight * 100).toFixed(2) + '%',
          delta: (Math.abs(delta) * 100).toFixed(2) + '%',
          reason: `Underweight by ${(Math.abs(delta) * 100).toFixed(1)}% - Increase position to match ideal allocation`,
          priority: Math.abs(delta) > 0.10 ? 'MEDIUM' : 'LOW',
          suggestedAction: `Buy ${((Math.abs(delta) * currentWeights.totalValue) / holding.avgPrice).toFixed(0)} shares`,
          expectedValue: (Math.abs(delta) * currentWeights.totalValue).toFixed(2)
        });
      }
    }

    // Check for concentration risk (REBALANCE)
    if (currentWeights.concentrationMetrics.maxSingleHolding > this.thresholds.concentrationRisk) {
      actions.push({
        type: 'REBALANCE',
        symbol: null,
        reason: `Concentration risk detected: Single position at ${(currentWeights.concentrationMetrics.maxSingleHolding * 100).toFixed(1)}%`,
        priority: 'HIGH',
        suggestedAction: 'Rebalance entire portfolio to reduce concentration',
        details: {
          currentMaxWeight: (currentWeights.concentrationMetrics.maxSingleHolding * 100).toFixed(2) + '%',
          recommendedMaxWeight: (this.thresholds.concentrationRisk * 100).toFixed(2) + '%',
          top3Concentration: (currentWeights.concentrationMetrics.top3Concentration * 100).toFixed(2) + '%'
        }
      });
    }

    // Check for positions that should be exited (very small or loss-making)
    for (const holding of currentHoldings) {
      const isVerySmall = holding.weight < this.thresholds.minAllocation;
      const isSignificantLoss = holding.pnlPercent < -20; // -20% loss threshold
      
      if (isVerySmall || isSignificantLoss) {
        actions.push({
          type: 'EXIT',
          symbol: holding.symbol,
          currentWeight: (holding.weight * 100).toFixed(2) + '%',
          reason: isVerySmall 
            ? `Position too small (${(holding.weight * 100).toFixed(2)}%) - Not meaningful for portfolio`
            : `Significant loss of ${holding.pnlPercent.toFixed(1)}% - Consider cutting losses`,
          priority: isSignificantLoss ? 'HIGH' : 'LOW',
          suggestedAction: `Sell all ${holding.quantity} shares`,
          expectedValue: holding.value.toFixed(2),
          currentPnL: holding.pnl.toFixed(2)
        });
      }
    }

    // Sort actions by priority
    const priorityOrder = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2 };
    actions.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

    return actions;
  }

  /**
   * Generate research-aware action suggestions
   * ENHANCED version that considers news, sentiment, fundamentals, and regime
   */
  async generateResearchAwareActions(currentWeights, idealAllocation, portfolioData, holdingsResearch, regime, goal) {
    const actions = [];
    const currentHoldings = currentWeights.holdings || [];
    const idealWeights = idealAllocation.weights || {};

    // Analyze each holding with research context
    for (const holding of currentHoldings) {
      const currentWeight = holding.weight;
      const idealWeight = idealWeights[holding.symbol] || 0;
      const delta = currentWeight - idealWeight;
      
      // Find research for this holding
      const holdingResearch = holdingsResearch.find(h => h.symbol === holding.symbol);
      const research = holdingResearch?.research || {};
      
      // Analyze research signals
      const signals = this.analyzeResearchSignals(research, regime);
      
      // DILUTE: Overweight OR negative signals
      if (delta > this.thresholds.overweight || (signals.overall === 'negative' && currentWeight > 0.05)) {
        let reason = '';
        let priority = 'MEDIUM';
        
        if (delta > this.thresholds.overweight) {
          reason = `Overexposed by ${(delta * 100).toFixed(1)}% - `;
          priority = delta > 0.35 ? 'HIGH' : 'MEDIUM';
        }
        
        // Add research-based reasoning
        if (signals.overall === 'negative') {
          const negativeFactors = [];
          if (signals.news === 'negative') negativeFactors.push('negative news');
          if (signals.sentiment === 'bearish') negativeFactors.push(`bearish sentiment (${(research.sentiment?.score * 100).toFixed(0)}%)`);
          if (signals.fundamentals === 'deteriorating') negativeFactors.push('deteriorating fundamentals');
          
          reason += negativeFactors.length > 0 
            ? `Research signals: ${negativeFactors.join(', ')}`
            : 'Reduce position to manage risk';
            
          priority = 'HIGH'; // Negative signals = high priority
        } else {
          reason += 'Reduce position to manage concentration risk';
        }
        
        actions.push({
          type: 'DILUTE',
          symbol: holding.symbol,
          currentWeight: (currentWeight * 100).toFixed(2) + '%',
          idealWeight: (idealWeight * 100).toFixed(2) + '%',
          delta: (Math.abs(delta) * 100).toFixed(2) + '%',
          reason,
          priority,
          researchSignals: signals, // ✅ NEW
          data_sources: this.getDataSourcesUsed(signals), // ✅ NEW
          suggestedAction: `Sell ${((Math.abs(delta) * currentWeights.totalValue) / holding.avgPrice).toFixed(0)} shares`,
          expectedValue: (Math.abs(delta) * currentWeights.totalValue).toFixed(2)
        });
        continue;
      }
      
      // ACCUMULATE: Underweight OR positive signals
      if ((delta < -this.thresholds.underweight && idealWeight > this.thresholds.minAllocation) || 
          (signals.overall === 'positive' && currentWeight < 0.15)) {
        let reason = '';
        let priority = 'LOW';
        
        if (delta < -this.thresholds.underweight) {
          reason = `Underweight by ${(Math.abs(delta) * 100).toFixed(1)}% - `;
          priority = Math.abs(delta) > 0.10 ? 'MEDIUM' : 'LOW';
        }
        
        // Add research-based reasoning
        if (signals.overall === 'positive') {
          const positiveFactors = [];
          if (signals.news === 'positive') positiveFactors.push('positive news momentum');
          if (signals.sentiment === 'bullish') positiveFactors.push(`bullish sentiment (${(research.sentiment?.score * 100).toFixed(0)}%)`);
          if (signals.fundamentals === 'improving') positiveFactors.push('improving fundamentals');
          
          reason += positiveFactors.length > 0
            ? `Research signals: ${positiveFactors.join(', ')}`
            : 'Increase position for growth potential';
            
          priority = regime.regime === 'BULL' ? 'MEDIUM' : 'LOW'; // Higher priority in bull market
        } else {
          reason += 'Increase position to match ideal allocation';
        }
        
        actions.push({
          type: 'ACCUMULATE',
          symbol: holding.symbol,
          currentWeight: (currentWeight * 100).toFixed(2) + '%',
          idealWeight: (idealWeight * 100).toFixed(2) + '%',
          delta: (Math.abs(delta) * 100).toFixed(2) + '%',
          reason,
          priority,
          researchSignals: signals, // ✅ NEW
          data_sources: this.getDataSourcesUsed(signals), // ✅ NEW
          suggestedAction: `Buy ${((Math.abs(delta) * currentWeights.totalValue) / holding.avgPrice).toFixed(0)} shares`,
          expectedValue: (Math.abs(delta) * currentWeights.totalValue).toFixed(2)
        });
        continue;
      }
      
      // EXIT: Small position with losses OR strongly negative signals
      const isVerySmall = currentWeight < this.thresholds.minAllocation;
      const isSignificantLoss = holding.pnlPercent < -15;
      
      if ((isVerySmall && holding.pnlPercent < -5) || isSignificantLoss || 
          (signals.overall === 'very_negative' && holding.pnlPercent < 0)) {
        let reason = '';
        
        if (signals.overall === 'very_negative') {
          reason = `Strong negative signals across multiple data sources - `;
        }
        
        reason += isVerySmall 
          ? `Position too small (${(currentWeight * 100).toFixed(2)}%) and unprofitable`
          : `Significant loss of ${holding.pnlPercent.toFixed(1)}%`;
        
        // Add regime context
        if (regime.regime === 'BEAR') {
          reason += ' - BEAR market suggests defensive positioning';
        }
        
        actions.push({
          type: 'EXIT',
          symbol: holding.symbol,
          currentWeight: (currentWeight * 100).toFixed(2) + '%',
          reason,
          priority: signals.overall === 'very_negative' ? 'HIGH' : (isSignificantLoss ? 'HIGH' : 'LOW'),
          researchSignals: signals, // ✅ NEW
          data_sources: this.getDataSourcesUsed(signals), // ✅ NEW
          suggestedAction: `Sell all ${holding.quantity} shares`,
          expectedValue: holding.value.toFixed(2),
          currentPnL: holding.pnl.toFixed(2)
        });
      }
    }

    // Sort actions by priority
    const priorityOrder = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2 };
    actions.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

    return actions;
  }

  /**
   * Analyze research signals for a holding
   */
  analyzeResearchSignals(research, regime) {
    const signals = {
      news: 'neutral',
      sentiment: 'neutral',
      fundamentals: 'stable',
      overall: 'neutral'
    };
    
    let positiveCount = 0;
    let negativeCount = 0;
    
    // Analyze news
    if (research.news && research.news.length > 0) {
      const recentNews = research.news.slice(0, 3);
      const positiveNews = recentNews.filter(n => n.sentiment === 'positive').length;
      const negativeNews = recentNews.filter(n => n.sentiment === 'negative').length;
      
      if (positiveNews > negativeNews) {
        signals.news = 'positive';
        positiveCount++;
      } else if (negativeNews > positiveNews) {
        signals.news = 'negative';
        negativeCount++;
      }
    }
    
    // Analyze sentiment
    if (research.sentiment) {
      const score = research.sentiment.score || 0.5;
      if (score > 0.65) {
        signals.sentiment = 'bullish';
        positiveCount++;
      } else if (score < 0.35) {
        signals.sentiment = 'bearish';
        negativeCount++;
      }
    }
    
    // Analyze fundamentals
    if (research.fundamentals) {
      const trend = research.fundamentals.trend;
      if (trend === 'improving') {
        signals.fundamentals = 'improving';
        positiveCount++;
      } else if (trend === 'deteriorating') {
        signals.fundamentals = 'deteriorating';
        negativeCount++;
      }
    }
    
    // Determine overall signal
    if (positiveCount >= 2) {
      signals.overall = 'positive';
    } else if (negativeCount >= 2) {
      signals.overall = 'negative';
    } else if (negativeCount === 3) {
      signals.overall = 'very_negative';
    }
    
    // Regime adjustment
    if (regime && regime.regime === 'BEAR' && signals.overall === 'neutral') {
      signals.overall = 'negative'; // More conservative in bear market
    }
    
    return signals;
  }

  /**
   * Get list of data sources used in signal analysis
   */
  getDataSourcesUsed(signals) {
    const sources = [];
    if (signals.news !== 'neutral') sources.push('news');
    if (signals.sentiment !== 'neutral') sources.push('sentiment');
    if (signals.fundamentals !== 'stable') sources.push('fundamentals');
    return sources;
  }

  /**
   * Calculate risk impact of suggested actions
   */
  calculateRiskImpact(currentWeights, idealAllocation) {
    const current = currentWeights.concentrationMetrics;
    const ideal = {
      maxSingleHolding: Math.max(...Object.values(idealAllocation.weights || {}), 0),
      avgWeight: Object.keys(idealAllocation.weights || {}).length > 0 
        ? 1 / Object.keys(idealAllocation.weights).length 
        : 0
    };

    return {
      concentrationChange: ((ideal.maxSingleHolding - current.maxSingleHolding) * 100).toFixed(2) + '%',
      diversificationImprovement: current.maxSingleHolding > ideal.maxSingleHolding ? 'Improved' : 'Maintained',
      riskReduction: current.maxSingleHolding > ideal.maxSingleHolding 
        ? ((current.maxSingleHolding - ideal.maxSingleHolding) * 100).toFixed(1) + '% risk reduction'
        : 'No change',
      recommendedAction: current.maxSingleHolding > this.thresholds.concentrationRisk 
        ? 'REBALANCE RECOMMENDED'
        : 'PORTFOLIO BALANCED'
    };
  }

  /**
   * Generate summary of actions
   */
  generateSummary(actions) {
    const summary = {
      totalActions: actions.length,
      byType: {
        ACCUMULATE: actions.filter(a => a.type === 'ACCUMULATE').length,
        DILUTE: actions.filter(a => a.type === 'DILUTE').length,
        EXIT: actions.filter(a => a.type === 'EXIT').length,
        REBALANCE: actions.filter(a => a.type === 'REBALANCE').length
      },
      byPriority: {
        HIGH: actions.filter(a => a.priority === 'HIGH').length,
        MEDIUM: actions.filter(a => a.priority === 'MEDIUM').length,
        LOW: actions.filter(a => a.priority === 'LOW').length
      },
      message: actions.length > 0 
        ? `${actions.length} portfolio action(s) recommended`
        : 'Portfolio is well-balanced, no actions needed'
    };

    return summary;
  }

  /**
   * Generate complete rebalance plan
   */
  async generateRebalancePlan(portfolioData, goal, userId) {
    try {
      const currentWeights = this.analyzeWeights(portfolioData);
      const idealAllocation = await this.calculateIdealAllocation(portfolioData, goal, currentWeights);
      
      const rebalancePlan = [];
      
      for (const holding of currentWeights.holdings) {
        const symbol = holding.symbol;
        const currentWeight = holding.weight;
        const idealWeight = idealAllocation.weights[symbol] || 0;
        const delta = idealWeight - currentWeight;
        
        if (Math.abs(delta) > 0.02) { // 2% threshold for rebalancing
          const action = delta > 0 ? 'BUY' : 'SELL';
          const shares = Math.abs((delta * currentWeights.totalValue) / holding.avgPrice);
          
          rebalancePlan.push({
            symbol,
            action,
            shares: Math.round(shares),
            currentWeight: (currentWeight * 100).toFixed(2) + '%',
            targetWeight: (idealWeight * 100).toFixed(2) + '%',
            deltaWeight: (delta * 100).toFixed(2) + '%',
            estimatedValue: (Math.abs(delta) * currentWeights.totalValue).toFixed(2),
            reason: action === 'BUY' ? 'Increase exposure' : 'Reduce exposure'
          });
        }
      }

      return {
        success: true,
        plan: rebalancePlan,
        totalTrades: rebalancePlan.length,
        estimatedCost: this.estimateTradingCost(rebalancePlan),
        expectedRiskReduction: this.calculateRiskImpact(currentWeights, idealAllocation)
      };
      
    } catch (error) {
      console.error('[PortfolioActionEngine] Error generating rebalance plan:', error);
      throw error;
    }
  }

  /**
   * Estimate trading cost for rebalance plan
   */
  estimateTradingCost(rebalancePlan) {
    const brokerage = 0.0003; // 0.03% per trade
    const totalValue = rebalancePlan.reduce((sum, trade) => sum + parseFloat(trade.estimatedValue), 0);
    const estimatedBrokerage = totalValue * brokerage * 2; // Buy + Sell
    
    return {
      brokerage: estimatedBrokerage.toFixed(2),
      totalTrades: rebalancePlan.length,
      totalValue: totalValue.toFixed(2)
    };
  }

  /**
   * Calculate portfolio optimization score
   * @param {Object} portfolioData - Current portfolio
   * @returns {Object} Optimization score (0-100)
   */
  async calculateOptimizationScore(portfolioData) {
    const weights = this.analyzeWeights(portfolioData);
    
    let score = 100;
    const penalties = [];

    // Penalty for concentration risk
    if (weights.concentrationMetrics.maxSingleHolding > this.thresholds.concentrationRisk) {
      const penalty = (weights.concentrationMetrics.maxSingleHolding - this.thresholds.concentrationRisk) * 100;
      score -= penalty;
      penalties.push({
        type: 'concentration',
        penalty: penalty.toFixed(1),
        reason: 'High concentration in single holding'
      });
    }

    // Penalty for insufficient diversification
    if (weights.concentrationMetrics.numberOfHoldings < 5) {
      const penalty = (5 - weights.concentrationMetrics.numberOfHoldings) * 5;
      score -= penalty;
      penalties.push({
        type: 'diversification',
        penalty: penalty.toFixed(1),
        reason: 'Insufficient number of holdings'
      });
    }

    // Penalty for very small positions
    const smallPositions = weights.holdings.filter(h => h.weight < this.thresholds.minAllocation);
    if (smallPositions.length > 0) {
      const penalty = smallPositions.length * 3;
      score -= penalty;
      penalties.push({
        type: 'small_positions',
        penalty: penalty.toFixed(1),
        reason: `${smallPositions.length} positions too small to be meaningful`
      });
    }

    score = Math.max(0, Math.min(100, score));

    return {
      score: score.toFixed(1),
      grade: score >= 80 ? 'A' : score >= 60 ? 'B' : score >= 40 ? 'C' : 'D',
      penalties,
      recommendation: score < 70 ? 'Portfolio optimization recommended' : 'Portfolio well-balanced'
    };
  }
}

// Export singleton instance
let instance = null;

const getPortfolioActionEngine = () => {
  if (!instance) {
    instance = new PortfolioActionEngine();
  }
  return instance;
};

module.exports = getPortfolioActionEngine;

