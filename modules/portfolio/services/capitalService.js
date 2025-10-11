/**
 * Capital Service
 * Fetches capital data from Zerodha API and calculates potential liquidity
 */

const db = require('../../../core/database/connection');

class CapitalService {
  constructor() {
    this.cacheTimeout = 60000; // 1 minute cache
    this.cache = new Map();
  }

  /**
   * Get comprehensive capital breakdown for a user
   * @param {string} userId - User ID
   * @param {string} configId - Broker config ID
   * @param {object} brokerClient - Zerodha API client (optional)
   * @returns {Promise<object>} Capital data
   */
  async getCapitalBreakdown(userId, configId, brokerClient = null) {
    try {
      const cacheKey = `${userId}:${configId}`;
      
      // Check cache
      if (this.cache.has(cacheKey)) {
        const cached = this.cache.get(cacheKey);
        if (Date.now() - cached.timestamp < this.cacheTimeout) {
          console.log('[CapitalService] Returning cached capital data');
          return cached.data;
        }
      }

      let capitalData = {
        available_balance: 0,
        potential_liquidity: 0,
        total_actionable: 0,
        breakdown: {
          holdings_value: 0,
          cash: 0,
          margin: 0,
        },
        source: 'calculated',
        timestamp: new Date().toISOString(),
      };

      // Try to fetch from Zerodha API if broker client available
      if (brokerClient) {
        try {
          console.log('[CapitalService] Fetching capital from Zerodha API');
          const margins = await brokerClient.getMargins();
          
          if (margins && margins.equity) {
            capitalData.available_balance = margins.equity.available.live_balance || 0;
            capitalData.breakdown.cash = margins.equity.available.cash || 0;
            capitalData.breakdown.margin = margins.equity.available.collateral || 0;
            capitalData.source = 'zerodha';
          }
        } catch (brokerError) {
          console.warn('[CapitalService] Zerodha API error, using calculation:', brokerError.message);
        }
      }

      // If no broker data, calculate from portfolio
      if (capitalData.source === 'calculated') {
        const portfolioData = await this.getPortfolioSummary(userId, configId);
        
        if (portfolioData) {
          const totalValue = portfolioData.total_value || 0;
          capitalData.breakdown.holdings_value = totalValue;
          
          // Estimate available balance (20% of total value as cash)
          capitalData.available_balance = totalValue * 0.2;
          capitalData.breakdown.cash = capitalData.available_balance;
        }
      }

      // Calculate potential liquidity from holdings
      capitalData.potential_liquidity = await this.calculatePotentialLiquidity(
        userId, 
        configId
      );

      // Total actionable capital
      capitalData.total_actionable = 
        capitalData.available_balance + capitalData.potential_liquidity;

      // Cache result
      this.cache.set(cacheKey, {
        data: capitalData,
        timestamp: Date.now(),
      });

      // Store snapshot in database
      await this.storeCapitalSnapshot(userId, configId, capitalData);

      return capitalData;

    } catch (error) {
      console.error('[CapitalService] Error getting capital breakdown:', error);
      throw error;
    }
  }

  /**
   * Calculate potential liquidity from holdings
   * Identifies holdings that can be partially liquidated for rebalancing
   */
  async calculatePotentialLiquidity(userId, configId) {
    try {
      const portfolioData = await this.getPortfolioSummary(userId, configId);
      
      if (!portfolioData || !portfolioData.holdings) {
        return 0;
      }

      // Calculate: Sum of holdings that are over-weighted
      // Assumption: Holdings above 10% weight can be partially liquidated
      const totalValue = portfolioData.total_value || 1;
      let potentialLiquidity = 0;

      for (const holding of portfolioData.holdings) {
        const holdingValue = holding.current_value || holding.currentValue || 0;
        const weight = (holdingValue / totalValue) * 100;

        if (weight > 10) {
          // Can liquidate portion above 10%
          const excessWeight = weight - 10;
          const liquidatableValue = (excessWeight / 100) * totalValue;
          potentialLiquidity += liquidatableValue;
        }
      }

      return potentialLiquidity;

    } catch (error) {
      console.error('[CapitalService] Error calculating liquidity:', error);
      return 0;
    }
  }

  /**
   * Get portfolio summary (uses existing portfolio module)
   */
  async getPortfolioSummary(userId, configId) {
    try {
      // Query portfolio summary from database
      const result = await db.query(
        `SELECT data FROM portfolio_snapshots 
         WHERE user_id = $1 AND config_id = $2 
         ORDER BY created_at DESC LIMIT 1`,
        [userId, configId]
      );

      if (result.rows.length > 0) {
        return result.rows[0].data;
      }

      return null;
    } catch (error) {
      console.error('[CapitalService] Error getting portfolio summary:', error);
      return null;
    }
  }

  /**
   * Store capital snapshot in database
   */
  async storeCapitalSnapshot(userId, configId, capitalData) {
    try {
      await db.query(
        `INSERT INTO capital_snapshots 
         (user_id, config_id, available_balance, potential_liquidity, total_actionable, broker_data, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
        [
          userId,
          configId,
          capitalData.available_balance,
          capitalData.potential_liquidity,
          capitalData.total_actionable,
          JSON.stringify(capitalData.breakdown),
        ]
      );
    } catch (error) {
      // Non-critical error - log but don't throw
      console.warn('[CapitalService] Could not store capital snapshot:', error.message);
    }
  }

  /**
   * Get historical capital snapshots
   */
  async getCapitalHistory(userId, configId, days = 30) {
    try {
      const result = await db.query(
        `SELECT * FROM capital_snapshots 
         WHERE user_id = $1 AND config_id = $2 
         AND created_at >= NOW() - INTERVAL '${days} days'
         ORDER BY created_at DESC`,
        [userId, configId]
      );

      return result.rows;
    } catch (error) {
      console.error('[CapitalService] Error getting capital history:', error);
      return [];
    }
  }

  /**
   * Clear cache for a user
   */
  clearCache(userId, configId) {
    const cacheKey = `${userId}:${configId}`;
    this.cache.delete(cacheKey);
  }
}

// Singleton instance
let capitalServiceInstance = null;

function getCapitalService() {
  if (!capitalServiceInstance) {
    capitalServiceInstance = new CapitalService();
  }
  return capitalServiceInstance;
}

module.exports = {
  CapitalService,
  getCapitalService,
};

