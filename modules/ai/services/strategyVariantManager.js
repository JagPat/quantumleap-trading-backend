/**
 * Strategy Variant Manager
 * A/B testing and strategy evolution infrastructure
 * Enables systematic testing of strategy improvements
 */

const db = require('../../../core/database/connection');

class StrategyVariantManager {
  /**
   * Create a new strategy variant for A/B testing
   * @param {number} baseStrategyId - Base strategy ID
   * @param {Object} variantConfig - Variant configuration
   * @returns {Promise<number>} Variant ID
   */
  async createVariant(baseStrategyId, variantConfig) {
    try {
      const {
        variantName,
        config,
        testGroup
      } = variantConfig;

      console.log('[VariantManager] Creating variant:', variantName);

      const query = `
        INSERT INTO strategy_variants 
        (base_strategy_id, variant_name, variant_config, test_group, is_active, created_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        RETURNING id
      `;

      const result = await db.query(query, [
        baseStrategyId,
        variantName,
        JSON.stringify(config),
        testGroup,
        true
      ]);

      const variantId = result.rows[0].id;
      console.log('[VariantManager] Variant created:', variantId);

      return variantId;

    } catch (error) {
      console.error('[VariantManager] Error creating variant:', error.message);
      throw error;
    }
  }

  /**
   * Assign user to A/B test group
   * @param {string} userId - User ID
   * @param {string} testName - Test identifier
   * @returns {Promise<Object>} Assignment result
   */
  async assignUserToTestGroup(userId, testName) {
    try {
      // Get active variants for this test
      const variantsQuery = `
        SELECT * FROM strategy_variants
        WHERE test_group = $1 AND is_active = TRUE
        ORDER BY id
      `;

      const variantsResult = await db.query(variantsQuery, [testName]);
      
      if (variantsResult.rows.length === 0) {
        return { 
          error: 'No active variants found for test',
          testName 
        };
      }

      // Simple hash-based assignment for consistency
      const userHash = this.hashUserId(userId);
      const variantIndex = userHash % variantsResult.rows.length;
      const assignedVariant = variantsResult.rows[variantIndex];

      console.log(`[VariantManager] Assigned user ${userId} to variant: ${assignedVariant.variant_name}`);

      return {
        userId,
        testName,
        variantId: assignedVariant.id,
        variantName: assignedVariant.variant_name,
        variantConfig: assignedVariant.variant_config
      };

    } catch (error) {
      console.error('[VariantManager] Error assigning to test group:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Simple hash function for user ID
   * @param {string} userId - User ID
   * @returns {number} Hash value
   */
  hashUserId(userId) {
    let hash = 0;
    for (let i = 0; i < userId.length; i++) {
      const char = userId.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  /**
   * Compare performance of variants in a test
   * @param {Array<number>} variantIds - Variant IDs to compare
   * @param {string} metricType - Metric to compare (pnl, winRate, alpha)
   * @returns {Promise<Object>} Comparison result
   */
  async compareVariantPerformance(variantIds, metricType = 'pnl') {
    try {
      const query = `
        SELECT 
          se.strategy_id,
          sv.variant_name,
          sv.id as variant_id,
          COUNT(se.id) as executions_count,
          AVG(CAST(se.outcome_summary->>'pnl' AS NUMERIC)) as avg_pnl,
          AVG(CAST(se.outcome_summary->>'pnl_percent' AS NUMERIC)) as avg_pnl_percent,
          AVG(se.ai_confidence_score) as avg_confidence,
          COUNT(*) FILTER (WHERE CAST(se.outcome_summary->>'pnl' AS NUMERIC) > 0) as winning_executions
        FROM strategy_executions se
        JOIN strategy_variants sv ON se.strategy_id = sv.id
        WHERE sv.id = ANY($1)
          AND se.status = 'closed'
        GROUP BY se.strategy_id, sv.variant_name, sv.id
      `;

      const result = await db.query(query, [variantIds]);

      // Calculate statistical significance (simplified)
      const variants = result.rows.map(row => ({
        variantId: row.variant_id,
        variantName: row.variant_name,
        executionsCount: parseInt(row.executions_count),
        avgPnl: parseFloat(row.avg_pnl) || 0,
        avgPnlPercent: parseFloat(row.avg_pnl_percent) || 0,
        avgConfidence: parseFloat(row.avg_confidence) || 0,
        winRate: row.executions_count > 0 
          ? (parseInt(row.winning_executions) / parseInt(row.executions_count)) * 100 
          : 0
      }));

      // Determine winner based on metric
      let winner = null;
      if (variants.length > 0) {
        winner = variants.reduce((best, current) => {
          if (metricType === 'pnl') {
            return current.avgPnl > best.avgPnl ? current : best;
          } else if (metricType === 'winRate') {
            return current.winRate > best.winRate ? current : best;
          } else {
            return current.avgPnlPercent > best.avgPnlPercent ? current : best;
          }
        });
      }

      return {
        metricType,
        variants,
        winner: winner ? {
          variantId: winner.variantId,
          variantName: winner.variantName,
          performance: winner[metricType === 'winRate' ? 'winRate' : metricType === 'pnl' ? 'avgPnl' : 'avgPnlPercent']
        } : null,
        sampleSize: variants.reduce((sum, v) => sum + v.executionsCount, 0)
      };

    } catch (error) {
      console.error('[VariantManager] Error comparing variants:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Promote winning variant
   * @param {string} testName - Test identifier
   * @returns {Promise<Object>} Promotion result
   */
  async promoteWinningVariant(testName) {
    try {
      // Get all variants in test
      const variantsQuery = `
        SELECT id FROM strategy_variants
        WHERE test_group = $1 AND is_active = TRUE
      `;

      const variantsResult = await db.query(variantsQuery, [testName]);
      const variantIds = variantsResult.rows.map(row => row.id);

      if (variantIds.length === 0) {
        return { error: 'No active variants found' };
      }

      // Compare performance
      const comparison = await this.compareVariantPerformance(variantIds, 'pnl');
      
      if (!comparison.winner) {
        return { error: 'Could not determine winner' };
      }

      // Archive non-winning variants
      const archiveQuery = `
        UPDATE strategy_variants
        SET is_active = FALSE
        WHERE test_group = $1 AND id != $2
      `;

      await db.query(archiveQuery, [testName, comparison.winner.variantId]);

      console.log(`[VariantManager] Promoted variant: ${comparison.winner.variantName}`);

      return {
        success: true,
        testName,
        winner: comparison.winner,
        archivedCount: variantIds.length - 1
      };

    } catch (error) {
      console.error('[VariantManager] Error promoting winner:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Archive underperforming variant
   * @param {number} variantId - Variant ID
   * @returns {Promise<void>}
   */
  async archiveUnderperformingVariant(variantId) {
    try {
      const query = `
        UPDATE strategy_variants
        SET is_active = FALSE
        WHERE id = $1
      `;

      await db.query(query, [variantId]);
      console.log(`[VariantManager] Archived variant: ${variantId}`);

    } catch (error) {
      console.error('[VariantManager] Error archiving variant:', error.message);
      throw error;
    }
  }

  /**
   * Get active variants for a test
   * @param {string} testName - Test identifier
   * @returns {Promise<Array>} Active variants
   */
  async getActiveVariants(testName) {
    try {
      const query = `
        SELECT * FROM strategy_variants
        WHERE test_group = $1 AND is_active = TRUE
        ORDER BY created_at DESC
      `;

      const result = await db.query(query, [testName]);
      return result.rows;

    } catch (error) {
      console.error('[VariantManager] Error fetching variants:', error.message);
      return [];
    }
  }

  /**
   * Update variant performance metrics
   * @param {number} variantId - Variant ID
   * @param {Object} metrics - Performance metrics
   * @returns {Promise<void>}
   */
  async updateVariantMetrics(variantId, metrics) {
    try {
      const query = `
        UPDATE strategy_variants
        SET performance_metrics = $1
        WHERE id = $2
      `;

      await db.query(query, [JSON.stringify(metrics), variantId]);
      console.log(`[VariantManager] Updated metrics for variant: ${variantId}`);

    } catch (error) {
      console.error('[VariantManager] Error updating metrics:', error.message);
      throw error;
    }
  }
}

// Singleton
let instance = null;

function getStrategyVariantManager() {
  if (!instance) {
    instance = new StrategyVariantManager();
  }
  return instance;
}

module.exports = {
  StrategyVariantManager,
  getStrategyVariantManager
};

