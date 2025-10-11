/**
 * User Override Tracker
 * Comprehensive tracking of user override behavior
 * Enables AI to learn from user decisions and calculate counterfactuals
 */

const db = require('../../../core/database/connection');

class UserOverrideTracker {
  /**
   * Record user override
   * @param {string} userId - User ID
   * @param {number} decisionId - Original AI decision ID
   * @param {Object} overrideDetails - Override information
   * @returns {Promise<number>} Override ID
   */
  async recordOverride(userId, decisionId, overrideDetails) {
    try {
      const {
        executionId,
        overrideType,
        aiRecommendation,
        userAlternative,
        reasonCategory,
        reasonText
      } = overrideDetails;

      console.log('[OverrideTracker] Recording override for user:', userId);

      const query = `
        INSERT INTO user_overrides 
        (user_id, decision_id, execution_id, override_type, ai_recommendation,
         user_alternative, override_reason_category, override_reason_text, override_timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
        RETURNING id
      `;

      const result = await db.query(query, [
        userId,
        decisionId,
        executionId || null,
        overrideType,
        JSON.stringify(aiRecommendation),
        JSON.stringify(userAlternative || {}),
        reasonCategory,
        reasonText
      ]);

      const overrideId = result.rows[0].id;
      console.log('[OverrideTracker] Override recorded:', overrideId);

      return overrideId;

    } catch (error) {
      console.error('[OverrideTracker] Error recording override:', error.message);
      throw error;
    }
  }

  /**
   * Track outcome of user override
   * @param {number} overrideId - Override ID
   * @param {Object} outcome - Outcome data
   * @returns {Promise<void>}
   */
  async trackOverrideOutcome(overrideId, outcome) {
    try {
      const {
        outcomePnl,
        outcomePnlPercent,
        aiWouldHavePnl
      } = outcome;

      console.log('[OverrideTracker] Tracking outcome for override:', overrideId);

      const query = `
        UPDATE user_overrides
        SET 
          outcome_tracked = TRUE,
          outcome_pnl = $1,
          outcome_pnl_percent = $2,
          ai_would_have_pnl = $3
        WHERE id = $4
        RETURNING *
      `;

      const result = await db.query(query, [
        outcomePnl,
        outcomePnlPercent,
        aiWouldHavePnl,
        overrideId
      ]);

      if (result.rows.length > 0) {
        console.log('[OverrideTracker] Outcome tracked successfully');
        return result.rows[0];
      }

      return null;

    } catch (error) {
      console.error('[OverrideTracker] Error tracking outcome:', error.message);
      throw error;
    }
  }

  /**
   * Calculate counterfactual: what would have happened if user followed AI
   * @param {number} overrideId - Override ID
   * @returns {Promise<Object>} Counterfactual analysis
   */
  async calculateCounterfactual(overrideId) {
    try {
      const query = `
        SELECT * FROM user_overrides WHERE id = $1
      `;

      const result = await db.query(query, [overrideId]);
      
      if (result.rows.length === 0) {
        return { error: 'Override not found' };
      }

      const override = result.rows[0];

      if (!override.outcome_tracked) {
        return { 
          status: 'pending',
          message: 'Outcome not yet tracked' 
        };
      }

      const userReturn = override.outcome_pnl_percent;
      const aiReturn = (override.ai_would_have_pnl / override.outcome_pnl) * override.outcome_pnl_percent;
      const difference = userReturn - aiReturn;

      return {
        overrideId,
        overrideType: override.override_type,
        userDecision: override.user_alternative,
        aiRecommendation: override.ai_recommendation,
        userReturn: parseFloat(userReturn?.toFixed(2) || 0),
        aiWouldHaveReturn: parseFloat(aiReturn?.toFixed(2) || 0),
        difference: parseFloat(difference?.toFixed(2) || 0),
        userOutperformed: difference > 0,
        reasonCategory: override.override_reason_category,
        reasonText: override.override_reason_text
      };

    } catch (error) {
      console.error('[OverrideTracker] Error calculating counterfactual:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Analyze user's override pattern
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Pattern analysis
   */
  async getUserOverridePattern(userId) {
    try {
      const query = `
        SELECT 
          override_type,
          override_reason_category,
          COUNT(*) as count,
          COUNT(*) FILTER (WHERE outcome_tracked = TRUE) as tracked_count,
          AVG(outcome_pnl_percent) FILTER (WHERE outcome_tracked = TRUE) as avg_user_return,
          AVG(ai_would_have_pnl) FILTER (WHERE outcome_tracked = TRUE) as avg_ai_would_have
        FROM user_overrides
        WHERE user_id = $1
        GROUP BY override_type, override_reason_category
        ORDER BY count DESC
      `;

      const result = await db.query(query, [userId]);

      // Calculate overall pattern
      const totalQuery = `
        SELECT 
          COUNT(*) as total_overrides,
          COUNT(*) FILTER (WHERE outcome_tracked = TRUE) as tracked_overrides,
          COUNT(*) FILTER (WHERE outcome_pnl_percent > 0) as winning_overrides,
          AVG(outcome_pnl_percent) as avg_return
        FROM user_overrides
        WHERE user_id = $1 AND outcome_tracked = TRUE
      `;

      const totalResult = await db.query(totalQuery, [userId]);
      const totals = totalResult.rows[0];

      return {
        userId,
        totalOverrides: parseInt(totals.total_overrides) || 0,
        trackedOverrides: parseInt(totals.tracked_overrides) || 0,
        winningOverrides: parseInt(totals.winning_overrides) || 0,
        winRate: totals.tracked_overrides > 0 
          ? (parseInt(totals.winning_overrides) / parseInt(totals.tracked_overrides)) * 100 
          : 0,
        avgReturn: parseFloat(totals.avg_return) || 0,
        patterns: result.rows.map(row => ({
          type: row.override_type,
          reason: row.override_reason_category,
          count: parseInt(row.count),
          tracked: parseInt(row.tracked_count),
          avgUserReturn: parseFloat(row.avg_user_return) || 0,
          avgAIWouldHave: parseFloat(row.avg_ai_would_have) || 0
        }))
      };

    } catch (error) {
      console.error('[OverrideTracker] Error analyzing pattern:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Compare AI vs user override performance
   * @param {string} userId - User ID
   * @param {number} days - Lookback period
   * @returns {Promise<Object>} Performance comparison
   */
  async getOverridePerformanceComparison(userId, days = 30) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);

      const query = `
        SELECT 
          COUNT(*) as total_overrides,
          COUNT(*) FILTER (WHERE outcome_tracked = TRUE) as tracked_overrides,
          AVG(outcome_pnl) FILTER (WHERE outcome_tracked = TRUE) as avg_user_pnl,
          AVG(ai_would_have_pnl) FILTER (WHERE outcome_tracked = TRUE) as avg_ai_pnl,
          AVG(outcome_pnl_percent) FILTER (WHERE outcome_tracked = TRUE) as avg_user_return,
          COUNT(*) FILTER (WHERE outcome_pnl > ai_would_have_pnl) as user_outperformed_count,
          SUM(outcome_pnl - ai_would_have_pnl) FILTER (WHERE outcome_tracked = TRUE) as total_difference
        FROM user_overrides
        WHERE user_id = $1 
          AND override_timestamp >= $2
          AND outcome_tracked = TRUE
      `;

      const result = await db.query(query, [userId, cutoffDate]);
      
      if (result.rows.length === 0 || result.rows[0].tracked_overrides === '0') {
        return {
          userId,
          period: `Last ${days} days`,
          noData: true,
          message: 'Not enough tracked overrides for comparison'
        };
      }

      const stats = result.rows[0];
      const trackedOverrides = parseInt(stats.tracked_overrides);
      const userOutperformed = parseInt(stats.user_outperformed_count);

      return {
        userId,
        period: `Last ${days} days`,
        totalOverrides: parseInt(stats.total_overrides),
        trackedOverrides,
        avgUserPnl: parseFloat(stats.avg_user_pnl),
        avgAIPnl: parseFloat(stats.avg_ai_pnl),
        avgUserReturn: parseFloat(stats.avg_user_return),
        userOutperformedCount: userOutperformed,
        userOutperformedPercent: (userOutperformed / trackedOverrides) * 100,
        totalDifference: parseFloat(stats.total_difference),
        verdict: stats.total_difference > 0 
          ? 'User overrides are profitable' 
          : 'AI recommendations would have been better'
      };

    } catch (error) {
      console.error('[OverrideTracker] Error comparing performance:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get recent overrides for a user
   * @param {string} userId - User ID
   * @param {number} limit - Max results
   * @returns {Promise<Array>} Recent overrides
   */
  async getRecentOverrides(userId, limit = 20) {
    try {
      const query = `
        SELECT * FROM user_overrides
        WHERE user_id = $1
        ORDER BY override_timestamp DESC
        LIMIT $2
      `;

      const result = await db.query(query, [userId, limit]);
      return result.rows;

    } catch (error) {
      console.error('[OverrideTracker] Error fetching recent overrides:', error.message);
      return [];
    }
  }
}

// Singleton
let instance = null;

function getUserOverrideTracker() {
  if (!instance) {
    instance = new UserOverrideTracker();
  }
  return instance;
}

module.exports = {
  UserOverrideTracker,
  getUserOverrideTracker
};

