/**
 * Trade Outcome Tracker
 * Records trade execution and outcomes
 * Links trades back to AI decisions for learning
 */

const db = require('../../../core/database/connection');

class TradeOutcomeTracker {
  /**
   * Record trade execution
   * @param {number} tradeId - From strategy_trades table
   * @param {Object} executionDetails 
   * @param {number} decisionId - From ai_decisions table
   */
  async recordTradeExecution(tradeId, executionDetails, decisionId = null) {
    try {
      const query = `
        INSERT INTO trade_outcomes
        (trade_id, decision_id, symbol, entry_price, quantity, executed_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        RETURNING id
      `;

      const result = await db.query(query, [
        tradeId,
        decisionId,
        executionDetails.symbol,
        executionDetails.entry_price,
        executionDetails.quantity
      ]);

      console.log(`[OutcomeTracker] Recorded execution for trade ${tradeId}, outcome ID: ${result.rows[0].id}`);
      return result.rows[0].id;

    } catch (error) {
      console.error('[OutcomeTracker] Error recording execution:', error.message);
      throw error;
    }
  }

  /**
   * Update trade outcome when position closes
   */
  async updateTradeOutcome(tradeId, outcome) {
    try {
      const {
        exit_price,
        pnl,
        exit_reason,
        user_override = false,
        override_reason = null
      } = outcome;

      // Get entry details to calculate metrics
      const entryQuery = `
        SELECT entry_price, quantity, executed_at
        FROM trade_outcomes
        WHERE trade_id = $1
      `;
      
      const entryResult = await db.query(entryQuery, [tradeId]);
      
      if (entryResult.rows.length === 0) {
        console.warn(`[OutcomeTracker] No entry record found for trade ${tradeId}`);
        return;
      }

      const entry = entryResult.rows[0];
      
      // Calculate metrics
      const pnl_percent = ((exit_price - entry.entry_price) / entry.entry_price) * 100;
      const holding_period_hours = Math.floor((Date.now() - new Date(entry.executed_at).getTime()) / 3600000);

      // Update outcome
      const updateQuery = `
        UPDATE trade_outcomes
        SET 
          exit_price = $1,
          pnl = $2,
          pnl_percent = $3,
          holding_period_hours = $4,
          exit_reason = $5,
          user_override = $6,
          override_reason = $7,
          closed_at = NOW()
        WHERE trade_id = $8
        RETURNING id, decision_id
      `;

      const result = await db.query(updateQuery, [
        exit_price,
        pnl,
        pnl_percent,
        holding_period_hours,
        exit_reason,
        user_override,
        override_reason,
        tradeId
      ]);

      if (result.rows.length > 0) {
        console.log(`[OutcomeTracker] Updated outcome for trade ${tradeId}: PnL=${pnl}, ${pnl_percent.toFixed(2)}%`);
        
        // Trigger learning update if linked to a decision
        if (result.rows[0].decision_id) {
          const DecisionAttributionTracker = require('./decisionAttributionTracker');
          const attributionTracker = new DecisionAttributionTracker();
          await attributionTracker.updateAttributionWeights(result.rows[0].decision_id, {
            pnl,
            pnl_percent,
            exit_reason
          });
        }
      }

      return result.rows[0]?.id;

    } catch (error) {
      console.error('[OutcomeTracker] Error updating outcome:', error.message);
      throw error;
    }
  }

  /**
   * Calculate decision quality based on all trades from that decision
   */
  async calculateDecisionQuality(decisionId) {
    try {
      const query = `
        SELECT 
          COUNT(*) as total_trades,
          COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
          AVG(pnl) as avg_pnl,
          AVG(pnl_percent) as avg_pnl_percent,
          SUM(pnl) as total_pnl,
          AVG(holding_period_hours) as avg_holding_period,
          STDDEV(pnl_percent) as volatility,
          MAX(pnl_percent) as best_trade,
          MIN(pnl_percent) as worst_trade
        FROM trade_outcomes
        WHERE decision_id = $1 AND closed_at IS NOT NULL
      `;

      const result = await db.query(query, [decisionId]);
      const stats = result.rows[0];

      if (!stats || stats.total_trades === 0) {
        return null;
      }

      const winRate = parseInt(stats.winning_trades) / parseInt(stats.total_trades);
      const avgReturn = parseFloat(stats.avg_pnl_percent) || 0;
      const volatility = parseFloat(stats.volatility) || 1;
      
      // Calculate Sharpe-like ratio (simplified)
      const sharpeRatio = volatility > 0 ? avgReturn / volatility : 0;

      return {
        decisionId,
        totalTrades: parseInt(stats.total_trades),
        winningTrades: parseInt(stats.winning_trades),
        winRate: winRate,
        avgPnL: parseFloat(stats.avg_pnl) || 0,
        avgPnLPercent: avgReturn,
        totalPnL: parseFloat(stats.total_pnl) || 0,
        avgHoldingPeriodHours: parseInt(stats.avg_holding_period) || 0,
        volatility: volatility,
        sharpeRatio: sharpeRatio,
        bestTrade: parseFloat(stats.best_trade) || 0,
        worstTrade: parseFloat(stats.worst_trade) || 0,
        quality: this.assessQuality(winRate, avgReturn, sharpeRatio)
      };

    } catch (error) {
      console.error('[OutcomeTracker] Error calculating decision quality:', error.message);
      return null;
    }
  }

  /**
   * Assess overall quality of decision
   */
  assessQuality(winRate, avgReturn, sharpeRatio) {
    let score = 0;
    
    // Win rate contribution (40%)
    score += winRate * 40;
    
    // Average return contribution (40%)
    if (avgReturn > 5) score += 40;
    else if (avgReturn > 2) score += 30;
    else if (avgReturn > 0) score += 20;
    
    // Risk-adjusted return (20%)
    if (sharpeRatio > 1.5) score += 20;
    else if (sharpeRatio > 1.0) score += 15;
    else if (sharpeRatio > 0.5) score += 10;
    
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'fair';
    return 'poor';
  }

  /**
   * Get performance by data source
   * Analyzes which data sources lead to better outcomes
   */
  async getPerformanceByDataSource(dataSource, lookbackDays = 30) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          a.data_source,
          COUNT(DISTINCT t.id) as trade_count,
          COUNT(*) FILTER (WHERE t.pnl > 0) as winning_trades,
          AVG(t.pnl) as avg_pnl,
          AVG(t.pnl_percent) as avg_pnl_percent,
          SUM(t.pnl) as total_pnl,
          AVG(a.attribution_weight) as avg_attribution_weight
        FROM trade_outcomes t
        JOIN ai_decisions d ON t.decision_id = d.id
        JOIN ai_decision_attributions a ON d.id = a.decision_id
        WHERE a.data_source = $1
          AND t.closed_at >= $2
          AND t.closed_at IS NOT NULL
        GROUP BY a.data_source
      `;

      const result = await db.query(query, [dataSource, cutoffDate]);

      if (result.rows.length === 0) {
        return {
          dataSource,
          tradeCount: 0,
          winRate: 0,
          avgPnL: 0,
          avgPnLPercent: 0,
          totalPnL: 0,
          confidence: 0,
          recommendation: 'insufficient_data'
        };
      }

      const stats = result.rows[0];
      const winRate = parseInt(stats.winning_trades) / parseInt(stats.trade_count);

      return {
        dataSource,
        tradeCount: parseInt(stats.trade_count),
        winningTrades: parseInt(stats.winning_trades),
        winRate: winRate,
        avgPnL: parseFloat(stats.avg_pnl),
        avgPnLPercent: parseFloat(stats.avg_pnl_percent),
        totalPnL: parseFloat(stats.total_pnl),
        avgAttributionWeight: parseFloat(stats.avg_attribution_weight),
        confidence: Math.min(parseInt(stats.trade_count) / 20, 1.0), // More trades = higher confidence
        recommendation: this.recommendDataSource(winRate, parseFloat(stats.avg_pnl_percent), parseInt(stats.trade_count))
      };

    } catch (error) {
      console.error('[OutcomeTracker] Error getting performance by data source:', error.message);
      return null;
    }
  }

  /**
   * Recommend whether to continue using a data source
   */
  recommendDataSource(winRate, avgReturn, tradeCount) {
    if (tradeCount < 10) return 'needs_more_data';
    
    if (winRate > 0.6 && avgReturn > 2) return 'highly_recommended';
    if (winRate > 0.5 && avgReturn > 0) return 'recommended';
    if (winRate > 0.4 || avgReturn > 0) return 'use_with_caution';
    return 'not_recommended';
  }

  /**
   * Get recent closed trades
   */
  async getRecentClosedTrades(daysBack = 1) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysBack);

      const query = `
        SELECT 
          t.*,
          d.decision_type,
          d.decision_data,
          d.market_regime
        FROM trade_outcomes t
        LEFT JOIN ai_decisions d ON t.decision_id = d.id
        WHERE t.closed_at >= $1
          AND t.closed_at IS NOT NULL
        ORDER BY t.closed_at DESC
      `;

      const result = await db.query(query, [cutoffDate]);
      return result.rows;

    } catch (error) {
      console.error('[OutcomeTracker] Error getting recent closed trades:', error.message);
      return [];
    }
  }

  /**
   * Get performance summary for a user
   */
  async getUserPerformanceSummary(userId, lookbackDays = 30) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          COUNT(*) as total_trades,
          COUNT(*) FILTER (WHERE t.pnl > 0) as winning_trades,
          AVG(t.pnl) as avg_pnl,
          AVG(t.pnl_percent) as avg_pnl_percent,
          SUM(t.pnl) as total_pnl,
          AVG(t.holding_period_hours) as avg_holding_period
        FROM trade_outcomes t
        JOIN ai_decisions d ON t.decision_id = d.id
        WHERE d.user_id = $1
          AND t.closed_at >= $2
          AND t.closed_at IS NOT NULL
      `;

      const result = await db.query(query, [userId, cutoffDate]);
      const stats = result.rows[0];

      if (!stats || parseInt(stats.total_trades) === 0) {
        return {
          userId,
          period: `Last ${lookbackDays} days`,
          totalTrades: 0,
          winRate: 0,
          totalPnL: 0,
          avgPnLPercent: 0
        };
      }

      return {
        userId,
        period: `Last ${lookbackDays} days`,
        totalTrades: parseInt(stats.total_trades),
        winningTrades: parseInt(stats.winning_trades),
        winRate: parseInt(stats.winning_trades) / parseInt(stats.total_trades),
        avgPnL: parseFloat(stats.avg_pnl),
        avgPnLPercent: parseFloat(stats.avg_pnl_percent),
        totalPnL: parseFloat(stats.total_pnl),
        avgHoldingPeriodHours: parseInt(stats.avg_holding_period)
      };

    } catch (error) {
      console.error('[OutcomeTracker] Error getting user performance summary:', error.message);
      return null;
    }
  }

  /**
   * Get outcomes for a specific symbol
   */
  async getSymbolOutcomes(symbol, limit = 20) {
    try {
      const query = `
        SELECT *
        FROM trade_outcomes
        WHERE symbol = $1 AND closed_at IS NOT NULL
        ORDER BY closed_at DESC
        LIMIT $2
      `;

      const result = await db.query(query, [symbol, limit]);
      return result.rows;

    } catch (error) {
      console.error('[OutcomeTracker] Error getting symbol outcomes:', error.message);
      return [];
    }
  }
}

module.exports = TradeOutcomeTracker;

