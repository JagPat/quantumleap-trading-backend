const db = require('../../../core/database/connection');

/**
 * Portfolio Rebalancing Service
 * Analyzes portfolio drift and generates rebalancing trades
 * Includes tax optimization and cost estimation
 */
class RebalancingService {
  constructor() {
    this.taxRates = {
      shortTerm: 0.15, // 15% STCG
      longTerm: 0.10,  // 10% LTCG (above 1L exemption)
      exemption: 100000 // ₹1L exemption for LTCG
    };
    this.brokerageRate = 0.0003; // 0.03% brokerage
  }

  /**
   * Analyze portfolio for rebalancing opportunities
   * @param {number} userId - User ID
   * @param {Array} holdings - Current holdings
   * @returns {Object} Analysis with proposed trades
   */
  async analyzePortfolio(userId, holdings) {
    try {
      console.log(`[RebalancingService] Analyzing portfolio for user ${userId}`);

      // Calculate current portfolio value
      const totalValue = holdings.reduce((sum, h) => sum + parseFloat(h.currentValue || 0), 0);

      if (totalValue === 0) {
        return {
          needsRebalancing: false,
          maxDrift: 0,
          allocation: [],
          proposedTrades: [],
          taxImpact: null
        };
      }

      // Calculate current and target weights
      const allocation = holdings.map(h => {
        const currentValue = parseFloat(h.currentValue || 0);
        const currentWeight = (currentValue / totalValue) * 100;
        const targetWeight = parseFloat(h.targetWeight || 0);
        const drift = targetWeight > 0 ? Math.abs(currentWeight - targetWeight) : 0;

        return {
          symbol: h.symbol,
          quantity: h.quantity,
          currentValue,
          currentWeight,
          targetWeight,
          drift,
          avgPrice: h.avgPrice || 0,
          purchaseDate: h.purchaseDate || null
        };
      });

      // Find max drift
      const maxDrift = Math.max(...allocation.map(a => a.drift));

      // Determine if rebalancing is needed (threshold: 5%)
      const needsRebalancing = maxDrift >= 5;

      // Generate proposed trades
      const proposedTrades = needsRebalancing 
        ? this.generateTrades(allocation, totalValue)
        : [];

      // Calculate tax impact
      const taxImpact = proposedTrades.length > 0
        ? this.calculateTaxImpact(proposedTrades, allocation)
        : null;

      return {
        needsRebalancing,
        maxDrift,
        totalValue,
        allocation: allocation.map(a => ({
          symbol: a.symbol,
          currentWeight: a.currentWeight,
          targetWeight: a.targetWeight,
          drift: a.drift
        })),
        proposedTrades,
        taxImpact
      };
    } catch (error) {
      console.error('[RebalancingService] Analysis error:', error);
      throw error;
    }
  }

  /**
   * Generate rebalancing trades
   * @param {Array} allocation - Current allocation
   * @param {number} totalValue - Total portfolio value
   * @returns {Array} Proposed trades
   */
  generateTrades(allocation, totalValue) {
    const trades = [];

    allocation.forEach(holding => {
      if (holding.targetWeight === 0) return; // Skip if no target set

      const targetValue = (holding.targetWeight / 100) * totalValue;
      const difference = targetValue - holding.currentValue;

      // Only create trade if difference is significant (>₹1000 or >5% drift)
      if (Math.abs(difference) > 1000 || holding.drift > 5) {
        const price = holding.currentValue / holding.quantity; // Current price estimate
        const quantity = Math.floor(Math.abs(difference) / price);

        if (quantity > 0) {
          trades.push({
            symbol: holding.symbol,
            action: difference > 0 ? 'BUY' : 'SELL',
            quantity,
            price,
            estimatedValue: quantity * price,
            reason: `Rebalance to target ${holding.targetWeight.toFixed(1)}%`,
            currentWeight: holding.currentWeight,
            targetWeight: holding.targetWeight,
            drift: holding.drift
          });
        }
      }
    });

    return trades;
  }

  /**
   * Calculate tax impact of proposed trades
   * @param {Array} trades - Proposed trades
   * @param {Array} allocation - Current allocation
   * @returns {Object} Tax impact breakdown
   */
  calculateTaxImpact(trades, allocation) {
    let shortTermGains = 0;
    let longTermGains = 0;
    let totalBrokerage = 0;

    trades.forEach(trade => {
      if (trade.action === 'SELL') {
        const holding = allocation.find(h => h.symbol === trade.symbol);
        if (holding) {
          const saleValue = trade.quantity * trade.price;
          const costBasis = trade.quantity * holding.avgPrice;
          const gain = saleValue - costBasis;

          // Determine if short-term or long-term
          const isLongTerm = this.isLongTermHolding(holding.purchaseDate);

          if (isLongTerm) {
            longTermGains += Math.max(0, gain);
          } else {
            shortTermGains += Math.max(0, gain);
          }
        }
      }

      // Calculate brokerage
      const tradeValue = trade.quantity * trade.price;
      totalBrokerage += tradeValue * this.brokerageRate;
    });

    // Calculate tax
    const shortTermTax = shortTermGains * this.taxRates.shortTerm;
    const longTermTaxable = Math.max(0, longTermGains - this.taxRates.exemption);
    const longTermTax = longTermTaxable * this.taxRates.longTerm;
    const totalTax = shortTermTax + longTermTax;

    return {
      shortTermGains: Math.round(shortTermGains),
      longTermGains: Math.round(longTermGains),
      estimatedTax: Math.round(totalTax),
      brokerage: Math.round(totalBrokerage),
      totalCost: Math.round(totalTax + totalBrokerage),
      breakdown: {
        shortTermTax: Math.round(shortTermTax),
        longTermTax: Math.round(longTermTax),
        exemptionUsed: Math.min(longTermGains, this.taxRates.exemption)
      }
    };
  }

  /**
   * Check if holding is long-term (>1 year)
   * @param {string|Date} purchaseDate - Purchase date
   * @returns {boolean} Whether holding is long-term
   */
  isLongTermHolding(purchaseDate) {
    if (!purchaseDate) return false;

    const purchase = new Date(purchaseDate);
    const now = new Date();
    const daysDiff = (now - purchase) / (1000 * 60 * 60 * 24);

    return daysDiff >= 365;
  }

  /**
   * Execute rebalancing trades
   * @param {number} userId - User ID
   * @param {number} configId - Broker config ID
   * @param {Array} trades - Trades to execute
   * @returns {Object} Execution result
   */
  async executeRebalancing(userId, configId, trades) {
    try {
      console.log(`[RebalancingService] Executing ${trades.length} rebalancing trades for user ${userId}`);

      // Store rebalancing event
      const rebalancingQuery = `
        INSERT INTO rebalancing_events (
          user_id,
          config_id,
          trades_count,
          total_value,
          max_drift,
          status,
          created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        RETURNING id
      `;

      const totalValue = trades.reduce((sum, t) => sum + t.estimatedValue, 0);
      const maxDrift = Math.max(...trades.map(t => t.drift || 0));

      const result = await db.query(rebalancingQuery, [
        userId,
        configId,
        trades.length,
        totalValue,
        maxDrift,
        'pending'
      ]);

      const rebalancingId = result.rows[0].id;

      // Store individual trades
      const tradeInserts = trades.map(trade => {
        return db.query(`
          INSERT INTO rebalancing_trades (
            rebalancing_id,
            symbol,
            action,
            quantity,
            price,
            estimated_value,
            status
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7)
        `, [
          rebalancingId,
          trade.symbol,
          trade.action,
          trade.quantity,
          trade.price,
          trade.estimatedValue,
          'pending'
        ]);
      });

      await Promise.all(tradeInserts);

      console.log(`[RebalancingService] Rebalancing ${rebalancingId} created with ${trades.length} trades`);

      return {
        success: true,
        rebalancingId,
        tradesCount: trades.length,
        status: 'pending',
        message: 'Rebalancing trades submitted successfully'
      };
    } catch (error) {
      console.error('[RebalancingService] Execution error:', error);
      throw error;
    }
  }

  /**
   * Get rebalancing history
   * @param {number} userId - User ID
   * @param {number} limit - Max results
   * @returns {Array} Rebalancing history
   */
  async getHistory(userId, limit = 10) {
    try {
      const query = `
        SELECT 
          r.*,
          COUNT(t.id) as trades_count,
          SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_trades
        FROM rebalancing_events r
        LEFT JOIN rebalancing_trades t ON t.rebalancing_id = r.id
        WHERE r.user_id = $1
        GROUP BY r.id
        ORDER BY r.created_at DESC
        LIMIT $2
      `;

      const result = await db.query(query, [userId, limit]);

      return result.rows.map(row => ({
        id: row.id,
        tradesCount: row.trades_count,
        completedTrades: row.completed_trades,
        totalValue: parseFloat(row.total_value),
        maxDrift: parseFloat(row.max_drift),
        status: row.status,
        createdAt: row.created_at
      }));
    } catch (error) {
      console.error('[RebalancingService] Get history error:', error);
      throw error;
    }
  }

  /**
   * Get/update user rebalancing settings
   * @param {number} userId - User ID
   * @returns {Object} Rebalancing settings
   */
  async getSettings(userId) {
    try {
      const query = `
        SELECT 
          rebalancing_enabled,
          drift_threshold,
          tax_optimization_enabled,
          auto_rebalance_frequency
        FROM user_preferences
        WHERE user_id = $1
      `;

      const result = await db.query(query, [userId]);

      if (result.rows.length === 0) {
        // Return defaults
        return {
          rebalancingEnabled: false,
          driftThreshold: 10,
          taxOptimization: true,
          autoRebalanceFrequency: 'monthly'
        };
      }

      const row = result.rows[0];
      return {
        rebalancingEnabled: row.rebalancing_enabled || false,
        driftThreshold: row.drift_threshold || 10,
        taxOptimization: row.tax_optimization_enabled !== false,
        autoRebalanceFrequency: row.auto_rebalance_frequency || 'monthly'
      };
    } catch (error) {
      console.error('[RebalancingService] Get settings error:', error);
      throw error;
    }
  }

  /**
   * Update user rebalancing settings
   * @param {number} userId - User ID
   * @param {Object} settings - New settings
   */
  async updateSettings(userId, settings) {
    try {
      const query = `
        INSERT INTO user_preferences (
          user_id,
          rebalancing_enabled,
          drift_threshold,
          tax_optimization_enabled,
          auto_rebalance_frequency,
          updated_at
        )
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET
          rebalancing_enabled = EXCLUDED.rebalancing_enabled,
          drift_threshold = EXCLUDED.drift_threshold,
          tax_optimization_enabled = EXCLUDED.tax_optimization_enabled,
          auto_rebalance_frequency = EXCLUDED.auto_rebalance_frequency,
          updated_at = NOW()
      `;

      await db.query(query, [
        userId,
        settings.rebalancingEnabled,
        settings.driftThreshold || 10,
        settings.taxOptimization !== false,
        settings.autoRebalanceFrequency || 'monthly'
      ]);

      console.log(`[RebalancingService] Settings updated for user ${userId}`);
      return true;
    } catch (error) {
      console.error('[RebalancingService] Update settings error:', error);
      throw error;
    }
  }
}

// Singleton instance
let rebalancingServiceInstance = null;

/**
 * Get Rebalancing Service instance
 * @returns {RebalancingService}
 */
function getRebalancingService() {
  if (!rebalancingServiceInstance) {
    rebalancingServiceInstance = new RebalancingService();
  }
  return rebalancingServiceInstance;
}

module.exports = {
  RebalancingService,
  getRebalancingService
};

