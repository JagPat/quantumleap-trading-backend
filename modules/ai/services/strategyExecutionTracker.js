/**
 * Strategy Execution Tracker
 * Logs every strategy execution with full context for AI learning
 * Enables performance tracking and benchmarking
 */

const db = require('../../../core/database/connection');

class StrategyExecutionTracker {
  /**
   * Record start of strategy execution
   * @param {number} strategyId - Strategy automation ID
   * @param {string} userId - User ID
   * @param {Object} executionDetails - Execution context
   * @returns {Promise<number>} Execution ID
   */
  async recordExecution(strategyId, userId, executionDetails) {
    try {
      const {
        configId,
        executionType = 'auto',
        capitalAllocated,
        assetsInvolved,
        aiConfidenceScore,
        marketRegime,
        regimeConfidence,
        decisionId,
        attributionMetadata
      } = executionDetails;

      console.log('[ExecutionTracker] Recording execution for strategy:', strategyId);

      const query = `
        INSERT INTO strategy_executions 
        (strategy_id, user_id, config_id, execution_type, capital_allocated, 
         assets_involved, ai_confidence_score, market_regime, regime_confidence,
         decision_id, attribution_metadata, status, executed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
        RETURNING id
      `;

      const result = await db.query(query, [
        strategyId,
        userId,
        configId,
        executionType,
        capitalAllocated,
        JSON.stringify(assetsInvolved || []),
        aiConfidenceScore,
        marketRegime,
        regimeConfidence,
        decisionId,
        JSON.stringify(attributionMetadata || {}),
        'active'
      ]);

      const executionId = result.rows[0].id;
      console.log('[ExecutionTracker] Execution recorded:', executionId);

      return executionId;

    } catch (error) {
      console.error('[ExecutionTracker] Error recording execution:', error.message);
      throw error;
    }
  }

  /**
   * Update execution outcome when strategy closes
   * @param {number} executionId - Execution ID
   * @param {Object} outcome - Outcome summary
   * @returns {Promise<void>}
   */
  async updateExecutionOutcome(executionId, outcome) {
    try {
      const {
        status = 'closed',
        outcomeSummary
      } = outcome;

      console.log('[ExecutionTracker] Updating execution outcome:', executionId);

      const query = `
        UPDATE strategy_executions
        SET 
          status = $1,
          outcome_summary = $2,
          closed_at = NOW()
        WHERE id = $3
        RETURNING *
      `;

      const result = await db.query(query, [
        status,
        JSON.stringify(outcomeSummary),
        executionId
      ]);

      if (result.rows.length > 0) {
        console.log('[ExecutionTracker] Execution updated successfully');
        return result.rows[0];
      }

      console.warn('[ExecutionTracker] Execution not found:', executionId);
      return null;

    } catch (error) {
      console.error('[ExecutionTracker] Error updating execution:', error.message);
      throw error;
    }
  }

  /**
   * Get execution history for a strategy
   * @param {number} strategyId - Strategy ID
   * @param {number} limit - Max results
   * @returns {Promise<Array>} Execution history
   */
  async getExecutionHistory(strategyId, limit = 50) {
    try {
      const query = `
        SELECT * FROM strategy_executions
        WHERE strategy_id = $1
        ORDER BY executed_at DESC
        LIMIT $2
      `;

      const result = await db.query(query, [strategyId, limit]);
      return result.rows;

    } catch (error) {
      console.error('[ExecutionTracker] Error fetching history:', error.message);
      return [];
    }
  }

  /**
   * Get aggregated performance metrics for a strategy
   * @param {number} strategyId - Strategy ID
   * @returns {Promise<Object>} Performance metrics
   */
  async getExecutionPerformance(strategyId) {
    try {
      const query = `
        SELECT 
          COUNT(*) as total_executions,
          COUNT(*) FILTER (WHERE status = 'closed') as closed_executions,
          COUNT(*) FILTER (WHERE status = 'active') as active_executions,
          AVG(ai_confidence_score) as avg_confidence,
          AVG(CAST(outcome_summary->>'total_pnl' AS NUMERIC)) as avg_pnl,
          AVG(CAST(outcome_summary->>'pnl_percent' AS NUMERIC)) as avg_pnl_percent,
          COUNT(*) FILTER (WHERE CAST(outcome_summary->>'pnl' AS NUMERIC) > 0) as winning_executions,
          SUM(capital_allocated) as total_capital_deployed
        FROM strategy_executions
        WHERE strategy_id = $1 AND status = 'closed'
      `;

      const result = await db.query(query, [strategyId]);
      
      if (result.rows.length > 0) {
        const metrics = result.rows[0];
        const winRate = metrics.closed_executions > 0 
          ? (metrics.winning_executions / metrics.closed_executions) * 100 
          : 0;

        return {
          totalExecutions: parseInt(metrics.total_executions) || 0,
          closedExecutions: parseInt(metrics.closed_executions) || 0,
          activeExecutions: parseInt(metrics.active_executions) || 0,
          avgConfidence: parseFloat(metrics.avg_confidence) || 0,
          avgPnl: parseFloat(metrics.avg_pnl) || 0,
          avgPnlPercent: parseFloat(metrics.avg_pnl_percent) || 0,
          winRate: parseFloat(winRate.toFixed(2)),
          totalCapitalDeployed: parseFloat(metrics.total_capital_deployed) || 0
        };
      }

      return {
        totalExecutions: 0,
        closedExecutions: 0,
        activeExecutions: 0,
        avgConfidence: 0,
        avgPnl: 0,
        avgPnlPercent: 0,
        winRate: 0,
        totalCapitalDeployed: 0
      };

    } catch (error) {
      console.error('[ExecutionTracker] Error calculating performance:', error.message);
      return null;
    }
  }

  /**
   * Compare execution to market benchmark
   * @param {number} executionId - Execution ID
   * @param {string} benchmarkType - Benchmark to compare against
   * @returns {Promise<Object>} Comparison result
   */
  async compareExecutionToBaseline(executionId, benchmarkType = 'NIFTY50') {
    try {
      // Get execution details
      const execQuery = `
        SELECT 
          executed_at,
          closed_at,
          outcome_summary
        FROM strategy_executions
        WHERE id = $1
      `;

      const execResult = await db.query(execQuery, [executionId]);
      
      if (execResult.rows.length === 0) {
        return { error: 'Execution not found' };
      }

      const execution = execResult.rows[0];
      const executionPnlPercent = execution.outcome_summary?.pnl_percent || 0;

      // Get benchmark performance for same period
      const benchmarkQuery = `
        SELECT 
          AVG(daily_return_percent) as avg_daily_return,
          SUM(daily_return_percent) as period_return
        FROM performance_benchmarks
        WHERE benchmark_type = $1
          AND date >= $2::date
          AND date <= $3::date
      `;

      const benchmarkResult = await db.query(benchmarkQuery, [
        benchmarkType,
        execution.executed_at,
        execution.closed_at || new Date()
      ]);

      const benchmarkReturn = benchmarkResult.rows[0]?.period_return || 0;
      const alpha = executionPnlPercent - benchmarkReturn;

      return {
        executionReturn: parseFloat(executionPnlPercent.toFixed(2)),
        benchmarkReturn: parseFloat(benchmarkReturn.toFixed(2)),
        alpha: parseFloat(alpha.toFixed(2)),
        outperformed: alpha > 0
      };

    } catch (error) {
      console.error('[ExecutionTracker] Error comparing to baseline:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Get active executions for a user
   * @param {string} userId - User ID
   * @returns {Promise<Array>} Active executions
   */
  async getActiveExecutions(userId) {
    try {
      const query = `
        SELECT * FROM strategy_executions
        WHERE user_id = $1 AND status = 'active'
        ORDER BY executed_at DESC
      `;

      const result = await db.query(query, [userId]);
      return result.rows;

    } catch (error) {
      console.error('[ExecutionTracker] Error fetching active executions:', error.message);
      return [];
    }
  }
}

// Singleton
let instance = null;

function getStrategyExecutionTracker() {
  if (!instance) {
    instance = new StrategyExecutionTracker();
  }
  return instance;
}

module.exports = {
  StrategyExecutionTracker,
  getStrategyExecutionTracker
};

