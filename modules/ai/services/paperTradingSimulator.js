const db = require('../../../core/database/connection');

/**
 * Paper Trading Simulator
 * Simulates order execution with realistic fills for strategy testing
 */
class PaperTradingSimulator {
  constructor() {
    this.db = db;
    // Track virtual positions per automation
    this.virtualPositions = new Map();
  }

  /**
   * Simulate order execution
   * @param {Object} order - Order details
   * @param {Object} marketData - Current market data for realistic fills
   * @returns {Object} Simulated execution result
   */
  async simulateOrder(order, marketData = null) {
    try {
      const {
        automation_id,
        symbol,
        exchange = 'NSE',
        transaction_type,
        order_type,
        quantity,
        price,
        trigger_price
      } = order;

      console.log('[PaperSimulator] Simulating order:', {
        automation_id,
        symbol,
        transaction_type,
        quantity,
        order_type
      });

      // Calculate execution price based on order type
      let executed_price = price;
      let status = 'COMPLETE';

      if (order_type === 'MARKET') {
        // Market orders: simulate slippage (0.1% - 0.3%)
        const slippage = this._calculateSlippage(marketData);
        executed_price = transaction_type === 'BUY' 
          ? price * (1 + slippage)
          : price * (1 - slippage);
      } else if (order_type === 'LIMIT') {
        // Limit orders: execute at limit price if market allows
        executed_price = price;
        // In real simulation, we'd check if market price reached the limit
        // For simplicity, assume 70% fill rate for limit orders
        if (Math.random() < 0.3) {
          status = 'PENDING';
          executed_price = null;
        }
      } else if (order_type === 'SL' || order_type === 'SL-M') {
        // Stop loss orders: trigger when price hits trigger_price
        if (marketData && marketData.last_price >= trigger_price) {
          executed_price = trigger_price;
        } else {
          status = 'PENDING';
          executed_price = null;
        }
      }

      // Calculate P&L if this is a closing trade
      let pnl = null;
      if (status === 'COMPLETE' && transaction_type === 'SELL') {
        const position = this._getVirtualPosition(automation_id, symbol);
        if (position) {
          pnl = (executed_price - position.average_price) * quantity;
        }
      }

      // Store order in database
      const query = `
        INSERT INTO automated_orders (
          automation_id,
          symbol,
          exchange,
          transaction_type,
          order_type,
          quantity,
          price,
          trigger_price,
          executed_quantity,
          executed_price,
          status,
          is_paper_trade,
          trigger_reason,
          pnl,
          executed_at,
          created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW())
        RETURNING *
      `;

      const values = [
        automation_id,
        symbol,
        exchange,
        transaction_type,
        order_type,
        quantity,
        price,
        trigger_price,
        status === 'COMPLETE' ? quantity : 0,
        executed_price,
        status,
        true, // is_paper_trade
        order.trigger_reason || 'Strategy signal',
        pnl,
        status === 'COMPLETE' ? new Date() : null
      ];

      const result = await this.db.query(query, values);

      // Update virtual position if trade completed
      if (status === 'COMPLETE') {
        this._updateVirtualPosition(automation_id, symbol, transaction_type, quantity, executed_price);
        
        // ✅ PHASE 7 HOOK 2: Trigger online learning when SELL completes (position closes)
        if (transaction_type === 'SELL' && pnl !== null) {
          try {
            const getPhase7Integrator = require('./phase7Integrator');
            const integrator = getPhase7Integrator();
            
            const pnl_percent = position ? ((executed_price - position.average_price) / position.average_price * 100) : 0;
            
            await integrator.handleTradeClose(
              {
                id: result.rows[0].id,
                symbol: symbol,
                decision_id: null, // Will be set if automation has decision_id
                user_id: automation_id // Using automation_id as user_id proxy
              },
              {
                exit_price: executed_price,
                pnl: pnl,
                pnl_percent: pnl_percent,
                exit_reason: order.trigger_reason || 'strategy_signal',
                user_override: false
              }
            );
          } catch (integrationError) {
            console.warn('[PaperSimulator] Phase 7 integration warning:', integrationError.message);
            // Don't fail trade if learning fails
          }
        }
      }

      console.log('[PaperSimulator] Order simulated successfully:', {
        orderId: result.rows[0].id,
        status,
        executed_price,
        pnl
      });

      return {
        success: true,
        order: this._formatOrder(result.rows[0]),
        execution: {
          status,
          executed_price,
          executed_quantity: status === 'COMPLETE' ? quantity : 0,
          pnl,
          timestamp: new Date().toISOString()
        }
      };

    } catch (error) {
      console.error('[PaperSimulator] Error simulating order:', error);
      throw new Error(`Paper trade simulation failed: ${error.message}`);
    }
  }

  /**
   * Calculate realistic slippage based on market conditions
   */
  _calculateSlippage(marketData) {
    // Base slippage: 0.1%
    let slippage = 0.001;

    if (marketData) {
      // Increase slippage for volatile markets
      const volatility = Math.abs(marketData.change_percent) / 100;
      slippage += volatility * 0.5;

      // Increase slippage for low volume
      if (marketData.volume && marketData.volume < 100000) {
        slippage += 0.002;
      }
    }

    // Cap slippage at 0.5%
    return Math.min(slippage, 0.005);
  }

  /**
   * Get virtual position for an automation + symbol
   */
  _getVirtualPosition(automationId, symbol) {
    const key = `${automationId}_${symbol}`;
    return this.virtualPositions.get(key);
  }

  /**
   * Update virtual position after trade
   */
  _updateVirtualPosition(automationId, symbol, transactionType, quantity, price) {
    const key = `${automationId}_${symbol}`;
    const current = this.virtualPositions.get(key) || {
      quantity: 0,
      total_cost: 0,
      average_price: 0
    };

    if (transactionType === 'BUY') {
      const newTotalCost = current.total_cost + (quantity * price);
      const newQuantity = current.quantity + quantity;
      const newAveragePrice = newTotalCost / newQuantity;

      this.virtualPositions.set(key, {
        quantity: newQuantity,
        total_cost: newTotalCost,
        average_price: newAveragePrice
      });
    } else if (transactionType === 'SELL') {
      const newQuantity = current.quantity - quantity;
      if (newQuantity <= 0) {
        this.virtualPositions.delete(key);
      } else {
        this.virtualPositions.set(key, {
          ...current,
          quantity: newQuantity
        });
      }
    }
  }

  /**
   * Get all virtual positions for an automation
   */
  async getVirtualPositions(automationId) {
    const positions = [];
    for (const [key, position] of this.virtualPositions.entries()) {
      if (key.startsWith(automationId)) {
        const symbol = key.split('_')[1];
        positions.push({
          symbol,
          ...position
        });
      }
    }
    return positions;
  }

  /**
   * Calculate total P&L for an automation's paper trades
   */
  async calculatePaperPnL(automationId) {
    try {
      const query = `
        SELECT 
          SUM(pnl) as total_pnl,
          COUNT(*) as total_trades,
          COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
          COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades
        FROM automated_orders
        WHERE automation_id = $1
          AND is_paper_trade = true
          AND status = 'COMPLETE'
          AND pnl IS NOT NULL
      `;

      const result = await this.db.query(query, [automationId]);
      const row = result.rows[0];

      return {
        total_pnl: parseFloat(row.total_pnl) || 0,
        total_trades: parseInt(row.total_trades) || 0,
        winning_trades: parseInt(row.winning_trades) || 0,
        losing_trades: parseInt(row.losing_trades) || 0,
        win_rate: row.total_trades > 0 
          ? (row.winning_trades / row.total_trades * 100).toFixed(2)
          : 0
      };
    } catch (error) {
      console.error('[PaperSimulator] Error calculating P&L:', error);
      throw error;
    }
  }

  /**
   * Reset virtual positions for an automation
   */
  clearVirtualPositions(automationId) {
    for (const key of this.virtualPositions.keys()) {
      if (key.startsWith(automationId)) {
        this.virtualPositions.delete(key);
      }
    }
  }

  /**
   * Format order for API response
   */
  _formatOrder(row) {
    return {
      id: row.id,
      automationId: row.automation_id,
      orderId: row.order_id,
      symbol: row.symbol,
      exchange: row.exchange,
      transactionType: row.transaction_type,
      orderType: row.order_type,
      quantity: row.quantity,
      price: row.price ? parseFloat(row.price) : null,
      executedPrice: row.executed_price ? parseFloat(row.executed_price) : null,
      executedQuantity: row.executed_quantity,
      status: row.status,
      isPaperTrade: row.is_paper_trade,
      triggerReason: row.trigger_reason,
      pnl: row.pnl ? parseFloat(row.pnl) : null,
      createdAt: row.created_at,
      executedAt: row.executed_at
    };
  }
}

module.exports = PaperTradingSimulator;

