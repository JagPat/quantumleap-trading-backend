/**
 * Rotational Trading Engine
 * Monitors holdings for rotation opportunities: sell at profit, rebuy on dip
 * Maintains portfolio composition while optimizing realized returns
 */

const { query } = require('../../../core/database');

class RotationalEngine {
  constructor() {
    this.profitThreshold = 0.05; // 5% profit to trigger rotation
    this.rebuyDropPercentage = 0.03; // 3% drop from sell price for rebuy
    this.cacheTimeout = 300000; // 5 minutes cache
    this.cache = new Map();
  }

  /**
   * Analyze portfolio for rotation opportunities
   * @param {Array} holdings - User holdings
   * @param {object} marketData - Current market prices
   * @param {object} options - Configuration options
   * @returns {Promise<Array>} Rotation opportunities
   */
  async analyzeRotationOpportunities(holdings, marketData = {}, options = {}) {
    try {
      const opportunities = [];

      for (const holding of holdings) {
        const symbol = holding.symbol || holding.tradingsymbol;
        const currentPrice = holding.last_price || holding.ltp || marketData[symbol] || 0;
        const avgPrice = holding.average_price || holding.averagePrice || 0;
        const quantity = holding.quantity || holding.shares || 0;

        if (avgPrice === 0 || currentPrice === 0) continue;

        // Calculate profit percentage
        const profitPercent = ((currentPrice - avgPrice) / avgPrice) * 100;

        // Check if profit threshold met
        if (profitPercent >= (this.profitThreshold * 100)) {
          // Calculate rebuy target (3% below sell price)
          const sellPrice = currentPrice;
          const rebuyTarget = sellPrice * (1 - this.rebuyDropPercentage);

          // Calculate support level (technical analysis - simple moving average)
          const supportLevel = await this.calculateSupportLevel(symbol);

          // Use higher of rebuy target or support level
          const finalRebuyTarget = Math.max(rebuyTarget, supportLevel || rebuyTarget);

          opportunities.push({
            symbol,
            action: 'ROTATE',
            type: 'ROTATION',
            current_price: currentPrice,
            average_price: avgPrice,
            profit_percent: profitPercent,
            quantity,
            sell_at: sellPrice,
            rebuy_at: finalRebuyTarget,
            reasoning: `Stock up ${profitPercent.toFixed(2)}% from entry. Sell at ₹${sellPrice.toFixed(2)}, rebuy at ₹${finalRebuyTarget.toFixed(2)} for continued upside`,
            expected_impact: {
              realized_profit: (sellPrice - avgPrice) * quantity,
              rebuy_advantage: ((sellPrice - finalRebuyTarget) / finalRebuyTarget) * 100,
            },
            priority: profitPercent > 10 ? 'HIGH' : profitPercent > 7 ? 'MEDIUM' : 'LOW',
            confidence: 0.75,
          });
        }
      }

      return opportunities;

    } catch (error) {
      console.error('[RotationalEngine] Error analyzing opportunities:', error);
      throw error;
    }
  }

  /**
   * Execute a rotation: sell position with rebuy target
   * @param {string} userId - User ID
   * @param {string} configId - Config ID
   * @param {object} rotation - Rotation details
   * @returns {Promise<object>} Execution result
   */
  async executeRotation(userId, configId, rotation) {
    try {
      console.log('[RotationalEngine] Executing rotation for', rotation.symbol);

      // Store rotation cycle in database
      const result = await query(
        `INSERT INTO rotation_cycles 
         (user_id, config_id, symbol, entry_price, sell_price, rebuy_target, status, reasoning, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
         RETURNING *`,
        [
          userId,
          configId,
          rotation.symbol,
          rotation.average_price,
          rotation.sell_at,
          rotation.rebuy_at,
          'ACTIVE',
          rotation.reasoning,
        ]
      );

      const cycleId = result.rows[0].id;

      return {
        success: true,
        cycle_id: cycleId,
        symbol: rotation.symbol,
        sell_at: rotation.sell_at,
        rebuy_at: rotation.rebuy_at,
        status: 'ACTIVE',
        message: `Rotation initiated for ${rotation.symbol}. Will rebuy when price reaches ₹${rotation.rebuy_at.toFixed(2)}`,
      };

    } catch (error) {
      console.error('[RotationalEngine] Error executing rotation:', error);
      throw error;
    }
  }

  /**
   * Update rotation cycle status (sold, rebought, cancelled)
   */
  async updateRotationStatus(cycleId, status, metadata = {}) {
    try {
      const updates = [`status = $2`];
      const params = [cycleId, status];
      let paramIndex = 3;

      if (status === 'SOLD') {
        updates.push(`sold_at = NOW()`);
        if (metadata.pnl) {
          updates.push(`pnl = $${paramIndex}`);
          params.push(metadata.pnl);
          paramIndex++;
        }
      } else if (status === 'REBOUGHT') {
        updates.push(`rebought_at = NOW()`);
      }

      const sql = `UPDATE rotation_cycles SET ${updates.join(', ')} WHERE id = $1 RETURNING *`;
      const result = await query(sql, params);

      return result.rows[0];

    } catch (error) {
      console.error('[RotationalEngine] Error updating rotation:', error);
      throw error;
    }
  }

  /**
   * Get active rotations for a user
   */
  async getActiveRotations(userId, configId) {
    try {
      const result = await query(
        `SELECT * FROM rotation_cycles 
         WHERE user_id = $1 AND config_id = $2 
         AND status IN ('ACTIVE', 'SOLD')
         ORDER BY created_at DESC`,
        [userId, configId]
      );

      return result.rows;

    } catch (error) {
      console.error('[RotationalEngine] Error getting active rotations:', error);
      return [];
    }
  }

  /**
   * Get rotation history for a user
   */
  async getRotationHistory(userId, configId, days = 30) {
    try {
      const result = await query(
        `SELECT * FROM rotation_cycles 
         WHERE user_id = $1 AND config_id = $2 
         AND created_at >= NOW() - INTERVAL '${days} days'
         ORDER BY created_at DESC`,
        [userId, configId]
      );

      return result.rows;

    } catch (error) {
      console.error('[RotationalEngine] Error getting rotation history:', error);
      return [];
    }
  }

  /**
   * Cancel a rotation cycle
   */
  async cancelRotation(cycleId, reason) {
    try {
      await query(
        `UPDATE rotation_cycles 
         SET status = 'CANCELLED', reasoning = reasoning || ' [Cancelled: ' || $2 || ']'
         WHERE id = $1`,
        [cycleId, reason]
      );

      return { success: true, message: 'Rotation cancelled' };

    } catch (error) {
      console.error('[RotationalEngine] Error cancelling rotation:', error);
      throw error;
    }
  }

  /**
   * Calculate support level for a symbol (simplified technical analysis)
   */
  async calculateSupportLevel(symbol) {
    try {
      // Check cache
      const cacheKey = `support:${symbol}`;
      if (this.cache.has(cacheKey)) {
        const cached = this.cache.get(cacheKey);
        if (Date.now() - cached.timestamp < this.cacheTimeout) {
          return cached.value;
        }
      }

      // In production, this would fetch from technical analysis API
      // For now, return null (use rebuy target calculation)
      const supportLevel = null;

      // Cache result
      this.cache.set(cacheKey, {
        value: supportLevel,
        timestamp: Date.now(),
      });

      return supportLevel;

    } catch (error) {
      console.error('[RotationalEngine] Error calculating support level:', error);
      return null;
    }
  }

  /**
   * Check market conditions for active rotations
   * Monitors if rebuy targets are hit
   */
  async checkRebuyConditions(userId, configId, currentMarketPrices) {
    try {
      const activeRotations = await this.getActiveRotations(userId, configId);
      const rebuyAlerts = [];

      for (const rotation of activeRotations) {
        if (rotation.status !== 'SOLD') continue;

        const currentPrice = currentMarketPrices[rotation.symbol];
        if (!currentPrice) continue;

        // Check if rebuy target hit
        if (currentPrice <= rotation.rebuy_target) {
          rebuyAlerts.push({
            cycle_id: rotation.id,
            symbol: rotation.symbol,
            rebuy_target: rotation.rebuy_target,
            current_price: currentPrice,
            action: 'REBUY_NOW',
            reasoning: `${rotation.symbol} reached rebuy target of ₹${rotation.rebuy_target.toFixed(2)}. Current: ₹${currentPrice.toFixed(2)}`,
          });
        }
      }

      return rebuyAlerts;

    } catch (error) {
      console.error('[RotationalEngine] Error checking rebuy conditions:', error);
      return [];
    }
  }

  /**
   * Enable/disable rotation for a holding
   */
  async toggleRotation(userId, symbol, enabled) {
    try {
      // Store rotation preference in user preferences
      const result = await query(
        `INSERT INTO rotation_preferences (user_id, symbol, enabled, updated_at)
         VALUES ($1, $2, $3, NOW())
         ON CONFLICT (user_id, symbol) 
         DO UPDATE SET enabled = $3, updated_at = NOW()
         RETURNING *`,
        [userId, symbol, enabled]
      );

      return result.rows[0];

    } catch (error) {
      // Table might not exist yet - log but don't fail
      console.warn('[RotationalEngine] Could not toggle rotation preference:', error.message);
      return { enabled };
    }
  }

  /**
   * Get rotation preferences for user
   */
  async getRotationPreferences(userId) {
    try {
      const result = await query(
        `SELECT * FROM rotation_preferences WHERE user_id = $1`,
        [userId]
      );

      return result.rows;

    } catch (error) {
      console.warn('[RotationalEngine] Could not fetch rotation preferences:', error.message);
      return [];
    }
  }
}

// Singleton instance
let rotationalEngineInstance = null;

function getRotationalEngine() {
  if (!rotationalEngineInstance) {
    rotationalEngineInstance = new RotationalEngine();
  }
  return rotationalEngineInstance;
}

module.exports = {
  RotationalEngine,
  getRotationalEngine,
};

