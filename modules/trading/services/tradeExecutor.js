/**
 * Trade Executor Service
 * Handles trade execution with validation, broker integration, and audit logging
 */

const db = require('../../../core/database/connection');
const { getCapitalService } = require('../../portfolio/services/capitalService');
const { getDecisionAttributionTracker } = require('../../ai/services/decisionAttributionTracker');

class TradeExecutor {
  constructor() {
    this.capitalService = null;
    this.attributionTracker = null;
  }

  async initialize() {
    if (!this.capitalService) {
      this.capitalService = getCapitalService();
    }
    if (!this.attributionTracker) {
      this.attributionTracker = getDecisionAttributionTracker();
    }
  }

  /**
   * Validate trade before execution
   */
  async validateTrade(userId, configId, tradeDetails) {
    try {
      await this.initialize();

      const { symbol, action, quantity, targetValue, orderType = 'MARKET' } = tradeDetails;
      const validationResult = {
        valid: true,
        errors: [],
        warnings: [],
        capitalCheck: null,
        brokerCheck: null,
      };

      // Get current capital
      const capitalData = await this.capitalService.getCapitalBreakdown(userId, configId);

      // Validate capital availability
      if (action === 'ACCUMULATE' || action === 'BUY') {
        const requiredCapital = targetValue || 0;
        
        if (requiredCapital > capitalData.total_actionable) {
          validationResult.valid = false;
          validationResult.errors.push(
            `Insufficient capital. Required: ₹${requiredCapital.toLocaleString('en-IN')}, Available: ₹${capitalData.total_actionable.toLocaleString('en-IN')}`
          );
        } else if (requiredCapital > capitalData.available_balance) {
          validationResult.warnings.push(
            `Using potential liquidity. Consider rebalancing first for better execution.`
          );
        }

        validationResult.capitalCheck = {
          required: requiredCapital,
          available: capitalData.available_balance,
          total_actionable: capitalData.total_actionable,
          sufficient: requiredCapital <= capitalData.total_actionable,
        };
      }

      // Validate quantity
      if (quantity && quantity <= 0) {
        validationResult.valid = false;
        validationResult.errors.push('Quantity must be greater than 0');
      }

      // Validate order type
      const validOrderTypes = ['MARKET', 'LIMIT', 'SL', 'SL-M'];
      if (!validOrderTypes.includes(orderType)) {
        validationResult.valid = false;
        validationResult.errors.push(`Invalid order type. Must be one of: ${validOrderTypes.join(', ')}`);
      }

      return validationResult;

    } catch (error) {
      console.error('[TradeExecutor] Validation error:', error);
      return {
        valid: false,
        errors: [error.message],
        warnings: [],
      };
    }
  }

  /**
   * Prepare trade for execution
   */
  async prepareTrade(userId, configId, tradeDetails) {
    try {
      const { symbol, action, quantity, targetValue, orderType, limitPrice, reasoning } = tradeDetails;

      // Validate first
      const validation = await this.validateTrade(userId, configId, tradeDetails);
      if (!validation.valid) {
        return {
          success: false,
          error: validation.errors.join(', '),
          validation,
        };
      }

      // Store trade preparation
      const result = await db.query(
        `INSERT INTO pending_trades 
         (user_id, config_id, symbol, action, quantity, target_value, order_type, limit_price, reasoning, status, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'PENDING', NOW())
         RETURNING *`,
        [userId, configId, symbol, action, quantity, targetValue, orderType, limitPrice, reasoning]
      );

      const tradeId = result.rows[0].id;

      return {
        success: true,
        trade_id: tradeId,
        trade: result.rows[0],
        validation,
        message: 'Trade prepared for execution. Review and confirm.',
      };

    } catch (error) {
      console.error('[TradeExecutor] Preparation error:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Execute trade via broker API
   */
  async executeTrade(tradeId, brokerClient = null) {
    try {
      await this.initialize();

      // Get trade details
      const tradeResult = await db.query(
        `SELECT * FROM pending_trades WHERE id = $1`,
        [tradeId]
      );

      if (tradeResult.rows.length === 0) {
        return {
          success: false,
          error: 'Trade not found',
        };
      }

      const trade = tradeResult.rows[0];

      // Check if already executed
      if (trade.status !== 'PENDING') {
        return {
          success: false,
          error: `Trade already ${trade.status}`,
        };
      }

      // Execute via broker (if available)
      let orderId = null;
      let executionStatus = 'SIMULATED';

      if (brokerClient) {
        try {
          // Actual broker order placement
          const orderResult = await brokerClient.placeOrder({
            tradingsymbol: trade.symbol,
            exchange: 'NSE',
            transaction_type: trade.action === 'ACCUMULATE' || trade.action === 'BUY' ? 'BUY' : 'SELL',
            quantity: trade.quantity,
            order_type: trade.order_type,
            product: 'CNC',
            price: trade.limit_price,
          });

          orderId = orderResult.order_id;
          executionStatus = 'EXECUTED';

        } catch (brokerError) {
          console.error('[TradeExecutor] Broker execution error:', brokerError);
          return {
            success: false,
            error: `Broker execution failed: ${brokerError.message}`,
          };
        }
      }

      // Update trade status
      await db.query(
        `UPDATE pending_trades 
         SET status = $1, order_id = $2, executed_at = NOW()
         WHERE id = $3`,
        [executionStatus, orderId, tradeId]
      );

      // Log decision attribution
      if (this.attributionTracker) {
        await this.attributionTracker.recordDecision({
          user_id: trade.user_id,
          decision_type: 'TRADE_EXECUTION',
          symbol: trade.symbol,
          action: trade.action,
          reasoning: trade.reasoning,
          metadata: {
            trade_id: tradeId,
            order_id: orderId,
            quantity: trade.quantity,
            order_type: trade.order_type,
          },
        });
      }

      return {
        success: true,
        trade_id: tradeId,
        order_id: orderId,
        status: executionStatus,
        message: brokerClient 
          ? `Trade executed successfully. Order ID: ${orderId}`
          : 'Trade simulated successfully (no broker connection)',
      };

    } catch (error) {
      console.error('[TradeExecutor] Execution error:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Cancel pending trade
   */
  async cancelTrade(tradeId, reason) {
    try {
      await db.query(
        `UPDATE pending_trades 
         SET status = 'CANCELLED', reasoning = reasoning || ' [Cancelled: ' || $2 || ']'
         WHERE id = $1 AND status = 'PENDING'`,
        [tradeId, reason]
      );

      return {
        success: true,
        message: 'Trade cancelled successfully',
      };

    } catch (error) {
      console.error('[TradeExecutor] Cancel error:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get pending trades for user
   */
  async getPendingTrades(userId, configId) {
    try {
      const result = await db.query(
        `SELECT * FROM pending_trades 
         WHERE user_id = $1 AND config_id = $2 
         AND status = 'PENDING'
         ORDER BY created_at DESC`,
        [userId, configId]
      );

      return result.rows;

    } catch (error) {
      console.error('[TradeExecutor] Error fetching pending trades:', error);
      return [];
    }
  }

  /**
   * Get trade history
   */
  async getTradeHistory(userId, configId, days = 30) {
    try {
      const result = await db.query(
        `SELECT * FROM pending_trades 
         WHERE user_id = $1 AND config_id = $2 
         AND created_at >= NOW() - INTERVAL '${days} days'
         ORDER BY created_at DESC`,
        [userId, configId]
      );

      return result.rows;

    } catch (error) {
      console.error('[TradeExecutor] Error fetching trade history:', error);
      return [];
    }
  }
}

// Singleton instance
let tradeExecutorInstance = null;

function getTradeExecutor() {
  if (!tradeExecutorInstance) {
    tradeExecutorInstance = new TradeExecutor();
  }
  return tradeExecutorInstance;
}

module.exports = {
  TradeExecutor,
  getTradeExecutor,
};

