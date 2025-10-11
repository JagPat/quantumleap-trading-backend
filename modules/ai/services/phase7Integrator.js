/**
 * Phase 7 Integration Helper
 * Provides integration points for executionEngine hooks
 * 
 * Usage: Call these methods from executionEngine when:
 * - Trade is executed (recordExecution)
 * - Trade closes (handleTradeClose)
 * - Auto-trade needs approval (checkAutoTradeApproval)
 */

const OnlineLearningService = require('./onlineLearningService');
const ConfidenceGatekeeper = require('./confidenceGatekeeper');
const ExplainabilityService = require('./explainabilityService');
const DecisionAttributionTracker = require('./decisionAttributionTracker');
const TradeOutcomeTracker = require('./tradeOutcomeTracker');

class Phase7Integrator {
  constructor() {
    this.onlineLearning = new OnlineLearningService();
    this.gatekeeper = new ConfidenceGatekeeper();
    this.explainer = new ExplainabilityService();
    this.attributionTracker = new DecisionAttributionTracker();
    this.outcomeTracker = new TradeOutcomeTracker();
  }

  /**
   * Hook 1: Record trade execution with decision linkage
   * Call this when a trade is executed
   * 
   * @param {number} tradeId - From strategy_trades table
   * @param {Object} executionDetails - { symbol, entry_price, quantity }
   * @param {number} decisionId - From ai_decisions table (if available)
   */
  async recordTradeExecution(tradeId, executionDetails, decisionId = null) {
    try {
      await this.outcomeTracker.recordTradeExecution(tradeId, executionDetails, decisionId);
      console.log(`[Phase7Integrator] ✅ Trade execution recorded: ${tradeId}`);
    } catch (error) {
      console.error('[Phase7Integrator] Error recording execution:', error.message);
      // Don't throw - this is a learning hook, shouldn't break execution
    }
  }

  /**
   * Hook 2: Handle trade closure and trigger online learning
   * Call this when a position is closed (take profit, stop loss, manual exit)
   * 
   * @param {Object} trade - Trade object with { id, symbol, decision_id, user_id }
   * @param {Object} outcome - { exit_price, pnl, pnl_percent, exit_reason, user_override }
   */
  async handleTradeClose(trade, outcome) {
    try {
      console.log(`[Phase7Integrator] Processing trade close for learning: ${trade.symbol}`);
      
      // Trigger online learning
      await this.onlineLearning.onTradeClose(trade, outcome);
      
      console.log(`[Phase7Integrator] ✅ Online learning complete for trade ${trade.id}`);
    } catch (error) {
      console.error('[Phase7Integrator] Error in trade close handling:', error.message);
      // Don't throw - learning is non-critical
    }
  }

  /**
   * Hook 3: Check if auto-trade should be approved
   * Call this before executing auto-trades
   * 
   * @param {Object} decision - AI decision object
   * @param {string} userId - User ID
   * @returns {Object} { approved, requiresApproval, reason, checks }
   */
  async checkAutoTradeApproval(decision, userId) {
    try {
      const gatekeeperResult = await this.gatekeeper.shouldRequireManualApproval(decision, userId);
      
      if (!gatekeeperResult.approved) {
        console.log(`[Phase7Integrator] ⚠️  Auto-trade blocked: ${gatekeeperResult.reason}`);
      } else {
        console.log(`[Phase7Integrator] ✅ Auto-trade approved`);
      }
      
      return gatekeeperResult;
    } catch (error) {
      console.error('[Phase7Integrator] Error in approval check:', error.message);
      
      // Fail-safe: if error, require manual approval
      return {
        approved: false,
        requiresApproval: true,
        reason: 'Safety check error - manual approval required',
        check: 'system_error'
      };
    }
  }

  /**
   * Hook 4: Generate explanation for API response
   * Call this when returning strategy/action to frontend
   * 
   * @param {Array} selectedStocks - AI-selected stocks
   * @param {Object} decision - Decision object
   * @returns {Object} Human-readable explanation
   */
  async generateExplanation(selectedStocks, decision) {
    try {
      const explanation = await this.explainer.explainStockSelection(selectedStocks, decision);
      return explanation;
    } catch (error) {
      console.error('[Phase7Integrator] Error generating explanation:', error.message);
      return {
        summary: 'Explanation unavailable',
        error: error.message
      };
    }
  }

  /**
   * Helper: Link strategy automation to AI decision
   * Call this after creating a strategy automation
   * 
   * @param {string} userId 
   * @param {number} automationId 
   * @param {Object} goal 
   * @param {Array} selectedStocks 
   * @param {Object} researchContext - From strategyEngine (regime, research, learnings)
   * @returns {number} Decision ID
   */
  async linkStrategyToDecision(userId, automationId, goal, selectedStocks, researchContext) {
    try {
      const decisionId = await this.attributionTracker.recordStockSelection(
        userId,
        goal,
        selectedStocks,
        researchContext || {}
      );
      
      console.log(`[Phase7Integrator] ✅ Linked automation ${automationId} to decision ${decisionId}`);
      return decisionId;
    } catch (error) {
      console.error('[Phase7Integrator] Error linking decision:', error.message);
      return null;
    }
  }

  /**
   * Get learning status for health check
   */
  async getLearningHealth() {
    try {
      const status = await this.onlineLearning.getLearningStatus();
      return {
        status: 'healthy',
        isLearning: status.isLearning,
        last24Hours: status.last24Hours,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

// Singleton instance
let instance;
function getPhase7Integrator() {
  if (!instance) {
    instance = new Phase7Integrator();
  }
  return instance;
}

module.exports = getPhase7Integrator;

