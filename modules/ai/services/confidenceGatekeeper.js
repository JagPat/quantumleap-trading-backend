/**
 * Confidence Gatekeeper
 * Prevents low-confidence decisions from auto-executing
 * Safety layer for automated trading
 */

const TradeOutcomeTracker = require('./tradeOutcomeTracker');
const DecisionAttributionTracker = require('./decisionAttributionTracker');
const FeedbackIntegrationService = require('./feedbackIntegrationService');

class ConfidenceGatekeeper {
  constructor() {
    this.outcomeTracker = new TradeOutcomeTracker();
    this.attributionTracker = new DecisionAttributionTracker();
    this.feedbackService = new FeedbackIntegrationService();
    
    // Default thresholds
    this.defaultThresholds = {
      minConfidence: 0.7,
      minDataSourceAgreement: 0.6,
      minRecentWinRate: 0.5,
      maxVolatilityVIX: 25
    };
  }

  /**
   * Determine if a decision should require manual approval
   * @param {Object} decision - AI decision with confidence and data sources
   * @param {string} userId - User ID
   * @returns {Object} { approved: boolean, reason: string, requiresApproval: boolean }
   */
  async shouldRequireManualApproval(decision, userId) {
    console.log(`[ConfidenceGatekeeper] Evaluating decision for user ${userId}`);
    
    try {
      const checks = [];
      
      // Check 1: LLM Confidence
      const confidenceCheck = this.checkLLMConfidence(decision);
      checks.push(confidenceCheck);
      
      if (!confidenceCheck.passed) {
        return {
          approved: false,
          requiresApproval: true,
          reason: confidenceCheck.reason,
          check: 'llm_confidence'
        };
      }
      
      // Check 2: Data Source Agreement
      const agreementCheck = this.checkDataSourceAgreement(decision);
      checks.push(agreementCheck);
      
      if (!agreementCheck.passed) {
        return {
          approved: false,
          requiresApproval: true,
          reason: agreementCheck.reason,
          check: 'data_source_agreement'
        };
      }
      
      // Check 3: Recent Performance in Current Regime
      const performanceCheck = await this.checkRecentPerformance(decision, userId);
      checks.push(performanceCheck);
      
      if (!performanceCheck.passed) {
        return {
          approved: false,
          requiresApproval: true,
          reason: performanceCheck.reason,
          check: 'recent_performance'
        };
      }
      
      // Check 4: Market Volatility
      const volatilityCheck = await this.checkMarketVolatility(decision);
      checks.push(volatilityCheck);
      
      if (!volatilityCheck.passed) {
        return {
          approved: false,
          requiresApproval: true,
          reason: volatilityCheck.reason,
          check: 'market_volatility'
        };
      }
      
      // Check 5: User's Historical Success Rate
      const userPerformanceCheck = await this.checkUserPerformance(userId);
      checks.push(userPerformanceCheck);
      
      if (!userPerformanceCheck.passed) {
        return {
          approved: false,
          requiresApproval: true,
          reason: userPerformanceCheck.reason,
          check: 'user_performance'
        };
      }
      
      // All checks passed - safe for auto-execution
      console.log(`[ConfidenceGatekeeper] ✅ All ${checks.length} safety checks passed`);
      
      return {
        approved: true,
        requiresApproval: false,
        reason: 'All safety checks passed',
        checks: checks.map(c => ({ name: c.name, passed: c.passed }))
      };
      
    } catch (error) {
      console.error('[ConfidenceGatekeeper] Error in approval check:', error.message);
      
      // Fail-safe: require manual approval if error
      return {
        approved: false,
        requiresApproval: true,
        reason: 'Safety check error - manual approval required',
        check: 'system_error'
      };
    }
  }

  /**
   * Check LLM confidence level
   */
  checkLLMConfidence(decision) {
    const confidence = decision.confidence || decision.regime_confidence || 0.5;
    const threshold = this.defaultThresholds.minConfidence;
    
    return {
      name: 'llm_confidence',
      passed: confidence >= threshold,
      reason: confidence < threshold 
        ? `Low AI confidence (${(confidence * 100).toFixed(0)}% < ${(threshold * 100).toFixed(0)}%). Manual review recommended.`
        : `High AI confidence (${(confidence * 100).toFixed(0)}%)`,
      confidence,
      threshold
    };
  }

  /**
   * Check data source agreement
   */
  checkDataSourceAgreement(decision) {
    const dataSources = decision.decision_data?.selectedStocks || [];
    
    if (dataSources.length === 0) {
      return { name: 'data_source_agreement', passed: true, reason: 'No multi-source data available' };
    }
    
    // Calculate agreement: how many stocks have multiple supporting data sources?
    const stocksWithMultipleSources = dataSources.filter(stock => {
      const sources = stock.data_sources || [];
      return sources.length >= 2; // At least 2 sources agree
    });
    
    const agreementRate = stocksWithMultipleSources.length / dataSources.length;
    const threshold = this.defaultThresholds.minDataSourceAgreement;
    
    return {
      name: 'data_source_agreement',
      passed: agreementRate >= threshold,
      reason: agreementRate < threshold
        ? `Conflicting signals: only ${(agreementRate * 100).toFixed(0)}% of stocks have corroborating data sources`
        : `Strong data agreement (${(agreementRate * 100).toFixed(0)}% stocks have multiple sources)`,
      agreementRate,
      threshold
    };
  }

  /**
   * Check recent performance in current market regime
   */
  async checkRecentPerformance(decision, userId) {
    try {
      const regime = decision.market_regime || 'UNKNOWN';
      
      // Get recent performance for this user in this regime
      const performance = await this.outcomeTracker.getUserPerformanceSummary(userId, 30);
      
      if (!performance || performance.totalTrades < 5) {
        // Not enough historical data - pass check but with lower confidence
        return {
          name: 'recent_performance',
          passed: true,
          reason: 'Insufficient historical data (manual approval recommended)',
          warning: true
        };
      }
      
      const winRate = performance.winRate || 0;
      const threshold = this.defaultThresholds.minRecentWinRate;
      
      return {
        name: 'recent_performance',
        passed: winRate >= threshold,
        reason: winRate < threshold
          ? `Recent win rate is low (${(winRate * 100).toFixed(0)}% < ${(threshold * 100).toFixed(0)}%). Performance below par.`
          : `Strong recent performance (${(winRate * 100).toFixed(0)}% win rate)`,
        winRate,
        threshold,
        totalTrades: performance.totalTrades
      };
      
    } catch (error) {
      console.error('[ConfidenceGatekeeper] Error checking performance:', error.message);
      return {
        name: 'recent_performance',
        passed: false,
        reason: 'Unable to verify recent performance - manual approval required'
      };
    }
  }

  /**
   * Check market volatility (high VIX = require approval)
   */
  async checkMarketVolatility(decision) {
    try {
      // In production, fetch real VIX data
      // For now, use regime indicators
      const regime = decision.market_regime;
      
      if (regime === 'VOLATILE') {
        return {
          name: 'market_volatility',
          passed: false,
          reason: 'High market volatility detected (VOLATILE regime). Manual approval recommended.',
          regime
        };
      }
      
      return {
        name: 'market_volatility',
        passed: true,
        reason: `Market volatility acceptable (${regime} regime)`,
        regime
      };
      
    } catch (error) {
      console.error('[ConfidenceGatekeeper] Error checking volatility:', error.message);
      return {
        name: 'market_volatility',
        passed: true,
        reason: 'Volatility check unavailable - proceeding with caution'
      };
    }
  }

  /**
   * Check user's overall performance history
   */
  async checkUserPerformance(userId) {
    try {
      const performance = await this.outcomeTracker.getUserPerformanceSummary(userId, 90); // 90 days
      
      if (!performance || performance.totalTrades < 10) {
        return {
          name: 'user_performance',
          passed: true,
          reason: 'New user - allow trading to build history',
          warning: true
        };
      }
      
      // Check if user is consistently losing
      const avgReturn = performance.avgPnLPercent || 0;
      const winRate = performance.winRate || 0;
      
      if (avgReturn < -5 || winRate < 0.3) {
        return {
          name: 'user_performance',
          passed: false,
          reason: `Poor overall performance (${(winRate * 100).toFixed(0)}% win rate, ${avgReturn.toFixed(2)}% avg return). Suggesting caution.`,
          winRate,
          avgReturn
        };
      }
      
      return {
        name: 'user_performance',
        passed: true,
        reason: `Acceptable user performance (${(winRate * 100).toFixed(0)}% win rate)`,
        winRate,
        avgReturn
      };
      
    } catch (error) {
      console.error('[ConfidenceGatekeeper] Error checking user performance:', error.message);
      return {
        name: 'user_performance',
        passed: true,
        reason: 'User performance check unavailable'
      };
    }
  }

  /**
   * Get recommended action based on gatekeeper decision
   */
  getRecommendedAction(gatekeeperResult) {
    if (gatekeeperResult.approved) {
      return {
        action: 'auto_execute',
        message: 'Safe for automatic execution',
        color: 'green'
      };
    }
    
    if (gatekeeperResult.check === 'llm_confidence') {
      return {
        action: 'manual_review',
        message: 'Low confidence - manual review recommended',
        color: 'yellow'
      };
    }
    
    if (gatekeeperResult.check === 'data_source_agreement') {
      return {
        action: 'request_more_data',
        message: 'Conflicting signals - gather more data or wait',
        color: 'orange'
      };
    }
    
    if (gatekeeperResult.check === 'user_performance' || gatekeeperResult.check === 'recent_performance') {
      return {
        action: 'reduce_position_size',
        message: 'Poor recent performance - consider smaller position sizes',
        color: 'red'
      };
    }
    
    return {
      action: 'manual_review',
      message: 'Safety check failed - manual approval required',
      color: 'red'
    };
  }
}

module.exports = ConfidenceGatekeeper;

