/**
 * Confidence Manager
 * Hybrid system for updating AI confidence scores
 * Auto-updates for small trades, manual review for large/unusual cases
 */

const db = require('../../../core/database/connection');

class ConfidenceManager {
  constructor() {
    // Thresholds for auto-update
    this.AUTO_UPDATE_CAPITAL_THRESHOLD = 10000; // $10k
    this.AUTO_UPDATE_CONFIDENCE_CHANGE_THRESHOLD = 0.10; // 10%
  }

  /**
   * Update confidence based on trade outcome
   * @param {number} decisionId - Decision ID
   * @param {Object} outcome - Trade outcome
   * @param {Object} threshold - Override thresholds
   * @returns {Promise<Object>} Update result
   */
  async updateConfidenceOnOutcome(decisionId, outcome, threshold = {}) {
    try {
      const {
        pnl,
        pnlPercent,
        capitalInvolved,
        exitReason
      } = outcome;

      // Get original decision
      const decisionQuery = `
        SELECT * FROM ai_decisions WHERE id = $1
      `;

      const decisionResult = await db.query(decisionQuery, [decisionId]);
      
      if (decisionResult.rows.length === 0) {
        console.warn('[ConfidenceManager] Decision not found:', decisionId);
        return { success: false, error: 'Decision not found' };
      }

      const decision = decisionResult.rows[0];
      const originalConfidence = decision.confidence || 0.5;

      // Calculate new confidence using Bayesian update
      const newConfidence = this.calculateNewConfidence(decision, {
        pnl,
        pnlPercent,
        exitReason
      });

      const confidenceChange = Math.abs(newConfidence - originalConfidence);

      // Determine if auto-update is allowed
      const capitalThreshold = threshold.capital || this.AUTO_UPDATE_CAPITAL_THRESHOLD;
      const changeThreshold = threshold.confidenceChange || this.AUTO_UPDATE_CONFIDENCE_CHANGE_THRESHOLD;

      const shouldAutoUpdate = 
        (capitalInvolved < capitalThreshold) && 
        (confidenceChange < changeThreshold);

      if (shouldAutoUpdate) {
        // Auto-update
        await this.applyConfidenceAdjustment(
          decisionId,
          newConfidence,
          `Auto-updated: ${pnlPercent > 0 ? 'Successful' : 'Unsuccessful'} trade (${pnlPercent.toFixed(2)}%)`,
          'system'
        );

        console.log(`[ConfidenceManager] Auto-updated confidence for decision ${decisionId}: ${originalConfidence.toFixed(2)} → ${newConfidence.toFixed(2)}`);

        return {
          success: true,
          autoUpdated: true,
          originalConfidence,
          newConfidence,
          confidenceChange
        };
      } else {
        // Flag for manual review
        await this.flagForManualReview(
          decisionId,
          confidenceChange >= changeThreshold 
            ? `Large confidence change: ${(confidenceChange * 100).toFixed(1)}%`
            : `High capital involved: $${capitalInvolved.toLocaleString()}`
        );

        console.log(`[ConfidenceManager] Flagged decision ${decisionId} for manual review`);

        return {
          success: true,
          autoUpdated: false,
          requiresReview: true,
          originalConfidence,
          proposedConfidence: newConfidence,
          confidenceChange,
          reason: confidenceChange >= changeThreshold ? 'large_change' : 'high_capital'
        };
      }

    } catch (error) {
      console.error('[ConfidenceManager] Error updating confidence:', error.message);
      return { success: false, error: error.message };
    }
  }

  /**
   * Flag decision for manual review
   * @param {number} decisionId - Decision ID
   * @param {string} reason - Reason for flagging
   * @returns {Promise<void>}
   */
  async flagForManualReview(decisionId, reason) {
    try {
      // Store flag in a review queue (can be a separate table or use metadata)
      const query = `
        INSERT INTO ai_confidence_history 
        (decision_id, original_confidence, adjusted_confidence, adjustment_reason, 
         adjustment_trigger, adjusted_by, adjusted_at)
        SELECT 
          id,
          confidence,
          confidence,
          $2,
          'manual_review',
          'system',
          NOW()
        FROM ai_decisions
        WHERE id = $1
      `;

      await db.query(query, [decisionId, `FLAGGED: ${reason}`]);
      console.log(`[ConfidenceManager] Flagged decision ${decisionId} for review: ${reason}`);

    } catch (error) {
      console.error('[ConfidenceManager] Error flagging for review:', error.message);
      throw error;
    }
  }

  /**
   * Apply confidence adjustment
   * @param {number} decisionId - Decision ID
   * @param {number} adjustment - New confidence value
   * @param {string} reason - Adjustment reason
   * @param {string} adjustedBy - Who adjusted (system or user_id)
   * @returns {Promise<void>}
   */
  async applyConfidenceAdjustment(decisionId, adjustment, reason, adjustedBy = 'system') {
    try {
      // Get current confidence
      const getCurrentQuery = `SELECT confidence FROM ai_decisions WHERE id = $1`;
      const currentResult = await db.query(getCurrentQuery, [decisionId]);
      
      if (currentResult.rows.length === 0) {
        throw new Error('Decision not found');
      }

      const originalConfidence = currentResult.rows[0].confidence;

      // Update decision confidence
      const updateQuery = `
        UPDATE ai_decisions
        SET confidence = $1
        WHERE id = $2
      `;

      await db.query(updateQuery, [adjustment, decisionId]);

      // Record in confidence history
      const historyQuery = `
        INSERT INTO ai_confidence_history 
        (decision_id, original_confidence, adjusted_confidence, adjustment_reason, 
         adjustment_trigger, adjusted_by, adjusted_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
      `;

      await db.query(historyQuery, [
        decisionId,
        originalConfidence,
        adjustment,
        reason,
        'trade_outcome',
        adjustedBy
      ]);

      console.log(`[ConfidenceManager] Applied confidence adjustment for decision ${decisionId}`);

    } catch (error) {
      console.error('[ConfidenceManager] Error applying adjustment:', error.message);
      throw error;
    }
  }

  /**
   * Get confidence evolution history
   * @param {number} decisionId - Decision ID
   * @returns {Promise<Array>} Confidence history
   */
  async getConfidenceHistory(decisionId) {
    try {
      const query = `
        SELECT * FROM ai_confidence_history
        WHERE decision_id = $1
        ORDER BY adjusted_at DESC
      `;

      const result = await db.query(query, [decisionId]);
      return result.rows;

    } catch (error) {
      console.error('[ConfidenceManager] Error fetching history:', error.message);
      return [];
    }
  }

  /**
   * Calculate new confidence using Bayesian update
   * @param {Object} decision - Original decision
   * @param {Object} outcomes - Trade outcomes
   * @returns {number} New confidence score
   */
  calculateNewConfidence(decision, outcomes) {
    const { pnl, pnlPercent, exitReason } = outcomes;
    const originalConfidence = decision.confidence || 0.5;

    // Simple Bayesian-like update
    // Positive outcome increases confidence, negative decreases it
    let adjustment = 0;

    if (pnl > 0) {
      // Successful trade
      if (pnlPercent > 10) {
        adjustment = 0.15; // Strong positive
      } else if (pnlPercent > 5) {
        adjustment = 0.10; // Moderate positive
      } else {
        adjustment = 0.05; // Weak positive
      }
    } else {
      // Unsuccessful trade
      if (pnlPercent < -10) {
        adjustment = -0.15; // Strong negative
      } else if (pnlPercent < -5) {
        adjustment = -0.10; // Moderate negative
      } else {
        adjustment = -0.05; // Weak negative
      }
    }

    // Factor in exit reason
    if (exitReason === 'stop_loss') {
      adjustment *= 0.8; // Reduce impact if stopped out (acceptable risk management)
    } else if (exitReason === 'target_reached') {
      adjustment *= 1.2; // Increase impact if target reached perfectly
    }

    // Apply adjustment with dampening factor
    const dampening = 0.7; // Don't update too aggressively
    const newConfidence = originalConfidence + (adjustment * dampening);

    // Bound between 0.1 and 0.95
    return Math.max(0.1, Math.min(0.95, newConfidence));
  }

  /**
   * Get pending manual reviews
   * @param {number} limit - Max results
   * @returns {Promise<Array>} Pending reviews
   */
  async getPendingReviews(limit = 20) {
    try {
      const query = `
        SELECT 
          h.*,
          d.decision_type,
          d.decision_data,
          d.user_id
        FROM ai_confidence_history h
        JOIN ai_decisions d ON h.decision_id = d.id
        WHERE h.adjustment_trigger = 'manual_review'
          AND h.adjustment_reason LIKE 'FLAGGED:%'
        ORDER BY h.adjusted_at DESC
        LIMIT $1
      `;

      const result = await db.query(query, [limit]);
      return result.rows;

    } catch (error) {
      console.error('[ConfidenceManager] Error fetching pending reviews:', error.message);
      return [];
    }
  }
}

// Singleton
let instance = null;

function getConfidenceManager() {
  if (!instance) {
    instance = new ConfidenceManager();
  }
  return instance;
}

module.exports = {
  ConfidenceManager,
  getConfidenceManager
};

