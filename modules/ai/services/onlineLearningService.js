/**
 * Online Learning Service
 * Updates AI learning in real-time when trades close
 * Adjusts data source weights based on outcomes
 */

const TradeOutcomeTracker = require('./tradeOutcomeTracker');
const DecisionAttributionTracker = require('./decisionAttributionTracker');
const FeedbackIntegrationService = require('./feedbackIntegrationService');
const db = require('../../../core/database/connection');

class OnlineLearningService {
  constructor() {
    this.outcomeTracker = new TradeOutcomeTracker();
    this.attributionTracker = new DecisionAttributionTracker();
    this.feedbackService = new FeedbackIntegrationService();
  }

  /**
   * Called when a trade closes
   * Triggers real-time learning and weight adjustments
   * @param {Object} trade - Trade details
   * @param {Object} outcome - Outcome details (exit_price, pnl, exit_reason)
   */
  async onTradeClose(trade, outcome) {
    console.log(`[OnlineLearning] Processing trade close: ${trade.symbol}, PnL: ${outcome.pnl}`);

    try {
      // 1. Record outcome in database
      await this.outcomeTracker.updateTradeOutcome(trade.id, outcome);
      
      // 2. Get the original AI decision
      const decision = await this.attributionTracker.getDecision(trade.decision_id);
      
      if (!decision) {
        console.warn('[OnlineLearning] No decision found for trade, skipping attribution update');
        return;
      }
      
      // 3. Analyze attribution accuracy
      await this.analyzeAttributionAccuracy(decision, outcome);
      
      // 4. Update data source weights based on outcome
      await this.updateDataSourceWeights(decision, outcome);
      
      // 5. Generate fresh insights (every 5 trades or significant outcome)
      if (Math.abs(outcome.pnl_percent) > 10 || trade.id % 5 === 0) {
        console.log('[OnlineLearning] Regenerating insights after significant trade');
        await this.feedbackService.generateLearningInsights(7); // Last week
      }
      
      // 6. Check if confidence thresholds should be adjusted
      await this.checkConfidenceAdjustment(trade.user_id);
      
      console.log(`[OnlineLearning] Learning complete for trade ${trade.id}`);
      
    } catch (error) {
      console.error('[OnlineLearning] Error in trade close processing:', error.message);
      // Don't throw - learning failures shouldn't break trade execution
    }
  }

  /**
   * Analyze how accurate the attribution was
   * Did the data sources predict the outcome correctly?
   */
  async analyzeAttributionAccuracy(decision, outcome) {
    try {
      const attributions = decision.attributions || [];
      const isProfitable = outcome.pnl > 0;
      
      for (const attribution of attributions) {
        if (!attribution.data_source) continue;
        
        // Determine if this data source was "correct"
        const wasAccurate = await this.assessDataSourceAccuracy(
          attribution.data_source,
          attribution.content_summary,
          outcome,
          decision
        );
        
        console.log(`[OnlineLearning] ${attribution.data_source} was ${wasAccurate ? 'ACCURATE' : 'INACCURATE'} for ${decision.decision_type}`);
        
        // Store accuracy record
        await this.recordAccuracyMetric(attribution.decision_id, attribution.data_source, wasAccurate, outcome);
      }
      
    } catch (error) {
      console.error('[OnlineLearning] Error analyzing attribution accuracy:', error.message);
    }
  }

  /**
   * Assess if a data source was accurate
   */
  async assessDataSourceAccuracy(dataSource, contentSummary, outcome, decision) {
    const isProfitable = outcome.pnl > 0;
    const decisionType = decision.decision_type;
    
    // For stock_selection: profitable trades = accurate data source
    if (decisionType === 'stock_selection') {
      return isProfitable;
    }
    
    // For portfolio_action: depends on action type
    if (decisionType === 'portfolio_action') {
      const actionData = decision.decision_data?.actions || [];
      const action = actionData.find(a => a.symbol === outcome.symbol);
      
      if (!action) return isProfitable; // Default
      
      // ACCUMULATE was accurate if profitable
      if (action.type === 'accumulate' || action.type === 'ACCUMULATE') {
        return isProfitable;
      }
      
      // DILUTE/EXIT was accurate if it prevented losses
      if (action.type === 'dilute' || action.type === 'exit' || action.type === 'DILUTE' || action.type === 'EXIT') {
        return outcome.exit_reason === 'user_override' || !isProfitable; // Accurate if we avoided loss
      }
    }
    
    return isProfitable; // Default: profitable = accurate
  }

  /**
   * Record accuracy metric
   */
  async recordAccuracyMetric(decisionId, dataSource, wasAccurate, outcome) {
    try {
      // Store in ai_usage_metrics table for tracking
      await db.query(`
        INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
        VALUES ($1, $2, $3, $4, NOW())
      `, [
        'system', // System-level metric
        'data_source_accuracy',
        wasAccurate ? 'accurate' : 'inaccurate',
        JSON.stringify({
          decision_id: decisionId,
          data_source: dataSource,
          pnl: outcome.pnl,
          pnl_percent: outcome.pnl_percent
        })
      ]);
      
    } catch (error) {
      console.error('[OnlineLearning] Error recording accuracy metric:', error.message);
    }
  }

  /**
   * Update data source weights based on outcome
   */
  async updateDataSourceWeights(decision, outcome) {
    try {
      const isProfitable = outcome.pnl > 0;
      const multiplier = isProfitable ? 1.05 : 0.95; // 5% boost or penalty
      
      // Update attribution weights in database
      await this.attributionTracker.updateAttributionWeights(decision.id, outcome);
      
      console.log(`[OnlineLearning] Updated data source weights (outcome: ${isProfitable ? 'profit' : 'loss'}, multiplier: ${multiplier})`);
      
    } catch (error) {
      console.error('[OnlineLearning] Error updating data source weights:', error.message);
    }
  }

  /**
   * Check if confidence thresholds should be adjusted for this user
   */
  async checkConfidenceAdjustment(userId) {
    try {
      // Get user's recent performance
      const performance = await this.outcomeTracker.getUserPerformanceSummary(userId, 30);
      
      if (!performance || performance.totalTrades < 10) {
        return; // Not enough data yet
      }
      
      // Adjust thresholds based on performance
      const thresholds = await this.feedbackService.adjustConfidenceThresholds(userId);
      
      console.log(`[OnlineLearning] Confidence threshold for user ${userId}: ${thresholds.threshold} (${thresholds.reason})`);
      
      // Store updated threshold in user preferences or separate table
      await this.storeConfidenceThreshold(userId, thresholds.threshold, thresholds.reason);
      
    } catch (error) {
      console.error('[OnlineLearning] Error checking confidence adjustment:', error.message);
    }
  }

  /**
   * Store user-specific confidence threshold
   */
  async storeConfidenceThreshold(userId, threshold, reason) {
    try {
      // Store in ai_preferences or create separate threshold table
      await db.query(`
        INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
        VALUES ($1, $2, $3, $4, NOW())
      `, [
        userId,
        'confidence_threshold_adjustment',
        threshold.toString(),
        JSON.stringify({ reason })
      ]);
      
    } catch (error) {
      console.error('[OnlineLearning] Error storing confidence threshold:', error.message);
    }
  }

  /**
   * Trigger immediate insight regeneration
   * Used after significant trades or market events
   */
  async triggerImmediateInsightUpdate() {
    console.log('[OnlineLearning] Triggering immediate insight regeneration');
    
    try {
      await this.feedbackService.generateLearningInsights(7);
      console.log('[OnlineLearning] Insights regenerated successfully');
    } catch (error) {
      console.error('[OnlineLearning] Error regenerating insights:', error.message);
    }
  }

  /**
   * Get real-time learning status
   */
  async getLearningStatus() {
    try {
      // Count recent learning activities
      const query = `
        SELECT 
          metric_type,
          COUNT(*) as count
        FROM ai_usage_metrics
        WHERE created_at >= NOW() - INTERVAL '24 hours'
          AND metric_type IN ('data_source_accuracy', 'confidence_threshold_adjustment')
        GROUP BY metric_type
      `;
      
      const result = await db.query(query);
      
      const status = {
        last24Hours: {},
        isLearning: result.rows.length > 0
      };
      
      for (const row of result.rows) {
        status.last24Hours[row.metric_type] = parseInt(row.count);
      }
      
      return status;
      
    } catch (error) {
      console.error('[OnlineLearning] Error getting learning status:', error.message);
      return { isLearning: false, last24Hours: {} };
    }
  }
}

module.exports = OnlineLearningService;

