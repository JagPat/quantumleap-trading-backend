/**
 * Portfolio Snapshot Service
 * Automatically captures historical portfolio snapshots for AI learning
 */

const db = require('../../../core/database/connection');

class PortfolioSnapshotService {
  constructor() {
    this.snapshotInterval = 3600000; // 1 hour default
  }

  /**
   * Capture a portfolio snapshot
   * @param {string} userId - User ID
   * @param {string} configId - Config ID
   * @param {object} options - Snapshot options
   * @returns {Promise<object>} Snapshot result
   */
  async captureSnapshot(userId, configId, options = {}) {
    try {
      console.log('[SnapshotService] Capturing portfolio snapshot for user:', userId);

      // Get current holdings
      const holdingsResult = await db.query(
        `SELECT * FROM holdings 
         WHERE user_id = $1 AND config_id = $2
         ORDER BY last_updated DESC`,
        [userId, configId]
      );

      if (holdingsResult.rows.length === 0) {
        console.log('[SnapshotService] No holdings found, skipping snapshot');
        return null;
      }

      const holdings = holdingsResult.rows;

      // Calculate portfolio metrics
      const totalValue = holdings.reduce((sum, h) => sum + (h.current_value || 0), 0);
      const investedValue = holdings.reduce((sum, h) => sum + (h.average_price || 0) * (h.quantity || 0), 0);
      const totalPnl = totalValue - investedValue;
      const totalPnlPercent = investedValue > 0 ? (totalPnl / investedValue) * 100 : 0;

      // Calculate sector allocation
      const sectorAllocation = this.calculateSectorAllocation(holdings, totalValue);

      // Calculate concentration risk (% in top 5)
      const concentrationRisk = this.calculateConcentrationRisk(holdings, totalValue);

      // Prepare holdings JSON
      const holdingsJson = holdings.reduce((acc, h) => {
        acc[h.symbol || h.tradingsymbol] = {
          symbol: h.symbol || h.tradingsymbol,
          quantity: h.quantity,
          average_price: h.average_price,
          last_price: h.last_price || h.ltp,
          current_value: h.current_value,
          pnl: h.pnl,
          pnl_percent: h.pnl_percent,
          sector: h.sector || 'Unknown'
        };
        return acc;
      }, {});

      // Insert snapshot
      const result = await db.query(
        `INSERT INTO portfolio_snapshots 
         (user_id, config_id, holdings, total_value, invested_value, 
          total_pnl, total_pnl_percent, holdings_count, unique_symbols,
          snapshot_type, trigger_event, sector_allocation, concentration_risk,
          ai_action_id, ai_suggestion_applied)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
         RETURNING id, snapshot_date`,
        [
          userId,
          configId,
          JSON.stringify(holdingsJson),
          totalValue,
          investedValue,
          totalPnl,
          totalPnlPercent,
          holdings.length,
          holdings.length, // Unique symbols (same as count for now)
          options.snapshotType || 'auto',
          options.triggerEvent || 'sync',
          JSON.stringify(sectorAllocation),
          concentrationRisk,
          options.aiActionId || null,
          options.aiSuggestionApplied || false
        ]
      );

      console.log('[SnapshotService] Snapshot captured:', result.rows[0].id);

      return {
        success: true,
        snapshotId: result.rows[0].id,
        snapshotDate: result.rows[0].snapshot_date,
        totalValue,
        holdingsCount: holdings.length
      };

    } catch (error) {
      console.error('[SnapshotService] Error capturing snapshot:', error);
      throw error;
    }
  }

  /**
   * Calculate sector allocation
   */
  calculateSectorAllocation(holdings, totalValue) {
    const sectorTotals = {};

    holdings.forEach(h => {
      const sector = h.sector || 'Unknown';
      const value = h.current_value || 0;
      sectorTotals[sector] = (sectorTotals[sector] || 0) + value;
    });

    const allocation = {};
    Object.keys(sectorTotals).forEach(sector => {
      allocation[sector] = totalValue > 0 
        ? ((sectorTotals[sector] / totalValue) * 100).toFixed(2)
        : 0;
    });

    return allocation;
  }

  /**
   * Calculate concentration risk (% in top 5 holdings)
   */
  calculateConcentrationRisk(holdings, totalValue) {
    if (totalValue === 0 || holdings.length === 0) return 0;

    // Sort by value descending
    const sorted = [...holdings].sort((a, b) => 
      (b.current_value || 0) - (a.current_value || 0)
    );

    // Sum top 5
    const top5Value = sorted.slice(0, 5).reduce((sum, h) => 
      sum + (h.current_value || 0), 0
    );

    return ((top5Value / totalValue) * 100).toFixed(2);
  }

  /**
   * Get historical snapshots for analysis
   */
  async getSnapshots(userId, configId, options = {}) {
    try {
      const days = options.days || 30;
      const limit = options.limit || 100;

      const result = await db.query(
        `SELECT * FROM portfolio_snapshots
         WHERE user_id = $1 AND config_id = $2
           AND snapshot_date >= NOW() - INTERVAL '${days} days'
         ORDER BY snapshot_date DESC
         LIMIT $3`,
        [userId, configId, limit]
      );

      return result.rows;

    } catch (error) {
      console.error('[SnapshotService] Error getting snapshots:', error);
      throw error;
    }
  }

  /**
   * Analyze portfolio evolution
   */
  async analyzeEvolution(userId, configId, days = 30) {
    try {
      const snapshots = await this.getSnapshots(userId, configId, { days });

      if (snapshots.length < 2) {
        return {
          message: 'Not enough data for evolution analysis',
          snapshotCount: snapshots.length
        };
      }

      const latest = snapshots[0];
      const oldest = snapshots[snapshots.length - 1];

      return {
        period: {
          from: oldest.snapshot_date,
          to: latest.snapshot_date,
          days: Math.ceil((new Date(latest.snapshot_date) - new Date(oldest.snapshot_date)) / (1000 * 60 * 60 * 24))
        },
        returns: {
          absolute: latest.total_value - oldest.total_value,
          percentage: oldest.total_value > 0 
            ? ((latest.total_value - oldest.total_value) / oldest.total_value * 100).toFixed(2)
            : 0
        },
        holdings: {
          initial: oldest.holdings_count,
          current: latest.holdings_count,
          change: latest.holdings_count - oldest.holdings_count
        },
        diversification: {
          initial: oldest.sector_allocation,
          current: latest.sector_allocation
        },
        concentration: {
          initial: oldest.concentration_risk,
          current: latest.concentration_risk,
          change: (latest.concentration_risk - oldest.concentration_risk).toFixed(2)
        }
      };

    } catch (error) {
      console.error('[SnapshotService] Error analyzing evolution:', error);
      throw error;
    }
  }
}

// Singleton
let instance = null;

function getSnapshotService() {
  if (!instance) {
    instance = new PortfolioSnapshotService();
  }
  return instance;
}

module.exports = {
  PortfolioSnapshotService,
  getSnapshotService
};
