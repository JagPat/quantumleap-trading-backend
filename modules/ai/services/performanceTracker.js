const db = require('../../../core/database/connection');
const { Parser } = require('json2csv');

/**
 * Performance Tracker Service
 * Calculates performance metrics and generates reports for strategy automations
 */
class PerformanceTracker {
  constructor() {
    this.db = db;
  }

  /**
   * Calculate and store daily performance for an automation
   */
  async calculateDailyPerformance(automationId, date = null) {
    try {
      const targetDate = date || new Date().toISOString().split('T')[0];

      console.log('[PerformanceTracker] Calculating daily performance:', {
        automationId,
        date: targetDate
      });

      // Get all completed orders for the day
      const ordersQuery = `
        SELECT 
          COUNT(*) as trades_count,
          SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
          SUM(pnl) FILTER (WHERE status = 'COMPLETE') as realized_pnl
        FROM automated_orders
        WHERE automation_id = $1
          AND DATE(created_at) = $2
          AND status = 'COMPLETE'
      `;

      const ordersResult = await this.db.query(ordersQuery, [automationId, targetDate]);
      const ordersData = ordersResult.rows[0];

      // Calculate cumulative P&L
      const cumulativeQuery = `
        SELECT SUM(pnl) as total_pnl
        FROM automated_orders
        WHERE automation_id = $1
          AND DATE(created_at) <= $2
          AND status = 'COMPLETE'
      `;

      const cumulativeResult = await this.db.query(cumulativeQuery, [automationId, targetDate]);
      const totalPnl = parseFloat(cumulativeResult.rows[0]?.total_pnl) || 0;

      // Calculate goal progress
      const automation = await this._getAutomation(automationId);
      const goalProgressPercent = automation ? (totalPnl / automation.profit_target_percent * 100) : 0;

      // Calculate max drawdown (simplified)
      const maxDrawdown = await this._calculateMaxDrawdown(automationId, targetDate);

      // Insert or update performance record
      const upsertQuery = `
        INSERT INTO automation_performance (
          automation_id,
          date,
          total_pnl,
          realized_pnl,
          unrealized_pnl,
          trades_count,
          winning_trades,
          losing_trades,
          max_drawdown,
          goal_progress_percent,
          created_at,
          updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
        ON CONFLICT (automation_id, date)
        DO UPDATE SET
          total_pnl = $3,
          realized_pnl = $4,
          unrealized_pnl = $5,
          trades_count = $6,
          winning_trades = $7,
          losing_trades = $8,
          max_drawdown = $9,
          goal_progress_percent = $10,
          updated_at = NOW()
        RETURNING *
      `;

      const values = [
        automationId,
        targetDate,
        totalPnl,
        parseFloat(ordersData.realized_pnl) || 0,
        0, // unrealized_pnl (would need open positions calculation)
        parseInt(ordersData.trades_count) || 0,
        parseInt(ordersData.winning_trades) || 0,
        parseInt(ordersData.losing_trades) || 0,
        maxDrawdown,
        goalProgressPercent
      ];

      const result = await this.db.query(upsertQuery, values);

      console.log('[PerformanceTracker] Daily performance calculated:', {
        automationId,
        date: targetDate,
        totalPnl,
        goalProgress: goalProgressPercent.toFixed(2)
      });

      return {
        success: true,
        performance: this._formatPerformance(result.rows[0])
      };

    } catch (error) {
      console.error('[PerformanceTracker] Error calculating daily performance:', error);
      throw error;
    }
  }

  /**
   * Get performance summary for an automation
   */
  async getPerformanceSummary(automationId) {
    try {
      const query = `
        SELECT 
          a.*,
          ap.total_pnl,
          ap.trades_count,
          ap.winning_trades,
          ap.losing_trades,
          ap.max_drawdown,
          ap.goal_progress_percent,
          ap.date as last_updated_date
        FROM strategy_automations a
        LEFT JOIN LATERAL (
          SELECT * FROM automation_performance
          WHERE automation_id = a.id
          ORDER BY date DESC
          LIMIT 1
        ) ap ON true
        WHERE a.id = $1
      `;

      const result = await this.db.query(query, [automationId]);

      if (result.rows.length === 0) {
        throw new Error('Automation not found');
      }

      const row = result.rows[0];
      const automation = this._transformAutomation(row);

      // Calculate additional metrics
      const winRate = row.trades_count > 0
        ? (row.winning_trades / row.trades_count * 100).toFixed(2)
        : 0;

      const daysElapsed = row.started_at
        ? Math.floor((Date.now() - new Date(row.started_at)) / (1000 * 60 * 60 * 24))
        : 0;

      const daysRemaining = automation.timeframeDays - daysElapsed;

      return {
        success: true,
        automation,
        performance: {
          totalPnl: row.total_pnl ? parseFloat(row.total_pnl) : 0,
          tradesCount: row.trades_count || 0,
          winningTrades: row.winning_trades || 0,
          losingTrades: row.losing_trades || 0,
          winRate: parseFloat(winRate),
          maxDrawdown: row.max_drawdown ? parseFloat(row.max_drawdown) : 0,
          goalProgress: row.goal_progress_percent ? parseFloat(row.goal_progress_percent) : 0,
          daysElapsed,
          daysRemaining,
          status: automation.status,
          isActive: automation.isActive
        }
      };

    } catch (error) {
      console.error('[PerformanceTracker] Error getting performance summary:', error);
      throw error;
    }
  }

  /**
   * Generate CSV export of performance data
   */
  async generatePerformanceReport(automationId, format = 'csv') {
    try {
      // Get automation details
      const automation = await this._getAutomation(automationId);
      if (!automation) {
        throw new Error('Automation not found');
      }

      // Get all orders
      const ordersQuery = `
        SELECT *
        FROM automated_orders
        WHERE automation_id = $1
        ORDER BY created_at DESC
      `;

      const ordersResult = await this.db.query(ordersQuery, [automationId]);
      const orders = ordersResult.rows;

      // Get daily performance
      const performanceQuery = `
        SELECT *
        FROM automation_performance
        WHERE automation_id = $1
        ORDER BY date DESC
      `;

      const performanceResult = await this.db.query(performanceQuery, [automationId]);
      const performance = performanceResult.rows;

      if (format === 'csv') {
        return this._generateCSV(automation, orders, performance);
      } else {
        return {
          automation,
          orders,
          performance
        };
      }

    } catch (error) {
      console.error('[PerformanceTracker] Error generating report:', error);
      throw error;
    }
  }

  /**
   * Generate CSV report
   */
  _generateCSV(automation, orders, performance) {
    const ordersData = orders.map(order => ({
      Date: order.created_at,
      Symbol: order.symbol,
      Action: order.transaction_type,
      Quantity: order.quantity,
      Price: order.price,
      ExecutedPrice: order.executed_price,
      Status: order.status,
      PnL: order.pnl || 0,
      IsPaperTrade: order.is_paper_trade ? 'Yes' : 'No',
      TriggerReason: order.trigger_reason
    }));

    const parser = new Parser({
      fields: [
        'Date', 'Symbol', 'Action', 'Quantity', 'Price', 
        'ExecutedPrice', 'Status', 'PnL', 'IsPaperTrade', 'TriggerReason'
      ]
    });

    const csv = parser.parse(ordersData);

    return {
      success: true,
      format: 'csv',
      data: csv,
      filename: `strategy_${automation.name.replace(/\s+/g, '_')}_${Date.now()}.csv`
    };
  }

  /**
   * Update goal progress
   */
  async updateGoalProgress(automationId) {
    try {
      const summary = await this.getPerformanceSummary(automationId);
      
      if (!summary.success) {
        return { success: false };
      }

      const { performance, automation } = summary;

      // Check if goal reached
      if (performance.goalProgress >= 100) {
        await this._markGoalReached(automationId);
        return {
          success: true,
          goalReached: true,
          performance
        };
      }

      // Check if max loss reached
      if (performance.totalPnl < 0 && Math.abs(performance.totalPnl) >= automation.maxLossPercent) {
        await this._markMaxLossReached(automationId);
        return {
          success: true,
          maxLossReached: true,
          performance
        };
      }

      return {
        success: true,
        performance
      };

    } catch (error) {
      console.error('[PerformanceTracker] Error updating goal progress:', error);
      throw error;
    }
  }

  /**
   * Mark goal as reached
   */
  async _markGoalReached(automationId) {
    const query = `
      UPDATE strategy_automations
      SET status = 'completed',
          is_active = false,
          completed_at = NOW(),
          updated_at = NOW()
      WHERE id = $1
    `;

    await this.db.query(query, [automationId]);

    console.log(`[PerformanceTracker] Goal reached for automation ${automationId}`);

    // Emit event
    const EventBus = require('../../../shared/events/eventBus');
    EventBus.emit('strategy.goal.reached', {
      automation_id: automationId,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Mark max loss reached
   */
  async _markMaxLossReached(automationId) {
    const query = `
      UPDATE strategy_automations
      SET status = 'paused',
          is_active = false,
          updated_at = NOW()
      WHERE id = $1
    `;

    await this.db.query(query, [automationId]);

    console.log(`[PerformanceTracker] Max loss reached for automation ${automationId}`);

    // Emit event
    const EventBus = require('../../../shared/events/eventBus');
    EventBus.emit('strategy.stopped', {
      automation_id: automationId,
      reason: 'Max loss limit reached',
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Calculate maximum drawdown
   */
  async _calculateMaxDrawdown(automationId, endDate) {
    const query = `
      SELECT 
        SUM(pnl) OVER (ORDER BY created_at) as cumulative_pnl
      FROM automated_orders
      WHERE automation_id = $1
        AND DATE(created_at) <= $2
        AND status = 'COMPLETE'
      ORDER BY created_at
    `;

    const result = await this.db.query(query, [automationId, endDate]);
    
    if (result.rows.length === 0) {
      return 0;
    }

    let peak = 0;
    let maxDrawdown = 0;

    result.rows.forEach(row => {
      const cumPnl = parseFloat(row.cumulative_pnl) || 0;
      if (cumPnl > peak) {
        peak = cumPnl;
      }
      const drawdown = peak - cumPnl;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    });

    return maxDrawdown;
  }

  /**
   * Get automation by ID
   */
  async _getAutomation(automationId) {
    const query = `SELECT * FROM strategy_automations WHERE id = $1`;
    const result = await this.db.query(query, [automationId]);
    
    if (result.rows.length === 0) {
      return null;
    }

    return this._transformAutomation(result.rows[0]);
  }

  /**
   * Transform automation row
   */
  _transformAutomation(row) {
    return {
      id: row.id,
      userId: row.user_id,
      configId: row.config_id,
      name: row.name,
      profit_target_percent: parseFloat(row.profit_target_percent),
      timeframeDays: row.timeframe_days,
      maxLossPercent: parseFloat(row.max_loss_percent),
      riskTolerance: row.risk_tolerance,
      symbols: row.symbols || [],
      status: row.status,
      isActive: row.is_active,
      startedAt: row.started_at,
      createdAt: row.created_at
    };
  }

  /**
   * Format performance row
   */
  _formatPerformance(row) {
    return {
      id: row.id,
      automationId: row.automation_id,
      date: row.date,
      totalPnl: parseFloat(row.total_pnl) || 0,
      realizedPnl: parseFloat(row.realized_pnl) || 0,
      unrealizedPnl: parseFloat(row.unrealized_pnl) || 0,
      tradesCount: row.trades_count || 0,
      winningTrades: row.winning_trades || 0,
      losingTrades: row.losing_trades || 0,
      maxDrawdown: parseFloat(row.max_drawdown) || 0,
      goalProgressPercent: parseFloat(row.goal_progress_percent) || 0,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
}

module.exports = PerformanceTracker;

