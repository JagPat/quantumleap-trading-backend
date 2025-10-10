const db = require('../../../core/database/connection');
const BrokerService = require('../../auth/services/brokerService');
const PaperTradingSimulator = require('./paperTradingSimulator');
const EventBus = require('../../../shared/events/eventBus');

/**
 * Strategy Execution Engine
 * Monitors approved strategies and executes orders based on market conditions
 */
class StrategyExecutionEngine {
  constructor() {
    this.db = db;
    this.brokerService = new BrokerService();
    this.paperSimulator = new PaperTradingSimulator();
    this.eventBus = EventBus;
    this.isMonitoring = false;
    this.monitoringInterval = null;
    this.checkIntervalMs = 30000; // Check every 30 seconds
  }

  /**
   * Start monitoring active strategies
   */
  async startMonitoring() {
    if (this.isMonitoring) {
      console.log('[ExecutionEngine] Monitoring already active');
      return;
    }

    console.log('[ExecutionEngine] Starting strategy monitoring...');
    this.isMonitoring = true;

    // Initial check
    await this.checkAllActiveStrategies();

    // Set up interval
    this.monitoringInterval = setInterval(async () => {
      await this.checkAllActiveStrategies();
    }, this.checkIntervalMs);

    console.log(`[ExecutionEngine] Monitoring started (interval: ${this.checkIntervalMs}ms)`);
  }

  /**
   * Stop monitoring
   */
  stopMonitoring() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
    this.isMonitoring = false;
    console.log('[ExecutionEngine] Monitoring stopped');
  }

  /**
   * Check all active strategies
   */
  async checkAllActiveStrategies() {
    try {
      const activeAutomations = await this.getActiveAutomations();
      
      console.log(`[ExecutionEngine] Checking ${activeAutomations.length} active automations`);

      for (const automation of activeAutomations) {
        try {
          await this.processStrategy(automation);
        } catch (error) {
          console.error(`[ExecutionEngine] Error processing automation ${automation.id}:`, error);
          // Continue processing other strategies even if one fails
        }
      }
    } catch (error) {
      console.error('[ExecutionEngine] Error in monitoring loop:', error);
    }
  }

  /**
   * Get all active strategy automations
   */
  async getActiveAutomations() {
    const query = `
      SELECT * FROM strategy_automations
      WHERE status = 'approved'
        AND is_active = true
      ORDER BY created_at ASC
    `;

    const result = await this.db.query(query);
    return result.rows.map(row => this._transformAutomation(row));
  }

  /**
   * Process a single strategy
   */
  async processStrategy(automation) {
    console.log(`[ExecutionEngine] Processing strategy: ${automation.id}`);

    // Check risk constraints first
    const constraintsCheck = await this.checkRiskConstraints(automation);
    if (!constraintsCheck.canTrade) {
      console.log(`[ExecutionEngine] Risk constraints violated for ${automation.id}:`, constraintsCheck.reason);
      
      // Emit event if constraints violated
      this.eventBus.emit('strategy.constraints.violated', {
        automation_id: automation.id,
        reason: constraintsCheck.reason
      });
      
      return;
    }

    // Get market data for symbols
    const marketData = await this.fetchMarketData(automation.symbols);

    // Evaluate strategy to generate signals
    const signal = await this.evaluateStrategy(automation, marketData);

    if (signal && signal.shouldTrade) {
      console.log(`[ExecutionEngine] Trade signal generated for ${automation.id}:`, signal);
      
      // Execute the order
      await this.executeOrder(automation, signal, marketData);
    }
  }

  /**
   * Check if risk constraints allow trading
   */
  async checkRiskConstraints(automation) {
    try {
      // Get broker config for constraints
      const config = await this.brokerService.brokerConfig.findByConfigId(automation.configId);
      
      if (!config) {
        return { canTrade: false, reason: 'Broker configuration not found' };
      }

      // Check daily loss limit
      if (config.max_daily_loss) {
        const dailyLoss = await this._getDailyLoss(automation.id);
        if (dailyLoss >= config.max_daily_loss) {
          return { 
            canTrade: false, 
            reason: `Daily loss limit reached: ₹${dailyLoss.toFixed(2)} / ₹${config.max_daily_loss}` 
          };
        }
      }

      // Check daily trade count limit
      if (config.max_trades_per_day) {
        const dailyTrades = await this._getDailyTradeCount(automation.id);
        if (dailyTrades >= config.max_trades_per_day) {
          return { 
            canTrade: false, 
            reason: `Daily trade limit reached: ${dailyTrades} / ${config.max_trades_per_day}` 
          };
        }
      }

      // Check automation's own max loss
      const totalLoss = await this._getTotalLoss(automation.id);
      const totalLossPercent = (totalLoss / automation.profitTargetPercent) * 100;
      
      if (totalLossPercent >= automation.maxLossPercent) {
        // Stop the automation
        await this.pauseAutomation(automation.id, 'Max loss limit reached');
        return { 
          canTrade: false, 
          reason: `Strategy max loss reached: ${totalLossPercent.toFixed(2)}%` 
        };
      }

      return { canTrade: true };

    } catch (error) {
      console.error('[ExecutionEngine] Error checking constraints:', error);
      return { canTrade: false, reason: `Error: ${error.message}` };
    }
  }

  /**
   * Fetch market data for symbols
   */
  async fetchMarketData(symbols) {
    if (!symbols || symbols.length === 0) {
      return {};
    }

    try {
      const query = `
        SELECT * FROM market_data
        WHERE symbol = ANY($1)
          AND timestamp > NOW() - INTERVAL '5 minutes'
      `;

      const result = await this.db.query(query, [symbols]);
      
      const marketData = {};
      result.rows.forEach(row => {
        marketData[row.symbol] = {
          symbol: row.symbol,
          last_price: parseFloat(row.last_price),
          open_price: parseFloat(row.open_price),
          high_price: parseFloat(row.high_price),
          low_price: parseFloat(row.low_price),
          volume: parseInt(row.volume),
          change_percent: parseFloat(row.change_percent),
          timestamp: row.timestamp
        };
      });

      return marketData;
    } catch (error) {
      console.error('[ExecutionEngine] Error fetching market data:', error);
      return {};
    }
  }

  /**
   * Evaluate strategy against market data
   * This is a simplified version - real implementation would parse strategy rules
   */
  async evaluateStrategy(automation, marketData) {
    try {
      const { strategyRules, symbols } = automation;

      if (!strategyRules) {
        console.log(`[ExecutionEngine] No strategy rules for automation ${automation.id}`);
        return { shouldTrade: false };
      }

      // For now, implement a basic momentum strategy
      // In production, this would parse and execute the actual strategy rules from AI
      
      for (const symbol of symbols) {
        const data = marketData[symbol];
        
        if (!data) {
          continue; // No market data for this symbol
        }

        // Simple momentum signal: buy if price up >2%, sell if down >2%
        const changePercent = data.change_percent;
        
        if (changePercent > 2) {
          // Bullish signal - BUY
          return {
            shouldTrade: true,
            action: 'BUY',
            symbol: symbol,
            exchange: 'NSE',
            price: data.last_price,
            quantity: this._calculatePositionSize(automation, data.last_price),
            reason: `Momentum signal: ${symbol} up ${changePercent.toFixed(2)}%`
          };
        } else if (changePercent < -2) {
          // Bearish signal - SELL (if we have position)
          return {
            shouldTrade: true,
            action: 'SELL',
            symbol: symbol,
            exchange: 'NSE',
            price: data.last_price,
            quantity: this._calculatePositionSize(automation, data.last_price),
            reason: `Momentum signal: ${symbol} down ${changePercent.toFixed(2)}%`
          };
        }
      }

      return { shouldTrade: false };

    } catch (error) {
      console.error('[ExecutionEngine] Error evaluating strategy:', error);
      return { shouldTrade: false };
    }
  }

  /**
   * Execute an order (paper or live)
   */
  async executeOrder(automation, signal, marketData) {
    try {
      const order = {
        automation_id: automation.id,
        symbol: signal.symbol,
        exchange: signal.exchange || 'NSE',
        transaction_type: signal.action,
        order_type: signal.orderType || 'MARKET',
        quantity: signal.quantity,
        price: signal.price,
        trigger_price: signal.triggerPrice,
        trigger_reason: signal.reason
      };

      console.log(`[ExecutionEngine] Executing order for automation ${automation.id}:`, order);

      let result;

      if (automation.tradingMode === 'paper') {
        // Paper trade
        result = await this.paperSimulator.simulateOrder(order, marketData[signal.symbol]);
      } else {
        // Live trade
        result = await this.placeLiveOrder(automation, order);
      }

      // Emit event
      this.eventBus.emit('strategy.order.placed', {
        automation_id: automation.id,
        order: result.order,
        is_paper: automation.tradingMode === 'paper'
      });

      return result;

    } catch (error) {
      console.error('[ExecutionEngine] Error executing order:', error);
      throw error;
    }
  }

  /**
   * Place live order via broker
   */
  async placeLiveOrder(automation, order) {
    try {
      // Get access token
      const tokenManager = this.brokerService.tokenManager;
      const accessToken = await tokenManager.getValidAccessToken(automation.configId);

      // Get API key
      const credentials = await this.brokerService.brokerConfig.getCredentials(automation.configId);

      // Place order via Kite
      const kiteResult = await this.brokerService.kiteClient.placeOrder(
        accessToken,
        credentials.apiKey,
        order
      );

      if (!kiteResult.success) {
        throw new Error(kiteResult.message || 'Order placement failed');
      }

      // Store in database
      const query = `
        INSERT INTO automated_orders (
          automation_id,
          order_id,
          symbol,
          exchange,
          transaction_type,
          order_type,
          quantity,
          price,
          executed_price,
          status,
          is_paper_trade,
          trigger_reason,
          created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
        RETURNING *
      `;

      const values = [
        automation.id,
        kiteResult.order_id,
        order.symbol,
        order.exchange,
        order.transaction_type,
        order.order_type,
        order.quantity,
        order.price,
        kiteResult.executed_price,
        kiteResult.status,
        false, // is_paper_trade
        order.trigger_reason
      ];

      const result = await this.db.query(query, values);

      return {
        success: true,
        order: this.paperSimulator._formatOrder(result.rows[0]),
        broker_order_id: kiteResult.order_id
      };

    } catch (error) {
      console.error('[ExecutionEngine] Error placing live order:', error);
      throw error;
    }
  }

  /**
   * Calculate position size based on risk tolerance
   */
  _calculatePositionSize(automation, price) {
    // Simple position sizing: risk 1-3% of capital per trade based on risk tolerance
    const riskPerTrade = {
      low: 0.01,      // 1%
      moderate: 0.02,  // 2%
      high: 0.03      // 3%
    }[automation.riskTolerance] || 0.02;

    // Assume capital = profit target amount (simplified)
    const estimatedCapital = 100000; // ₹1 lakh default
    const riskAmount = estimatedCapital * riskPerTrade;
    
    const quantity = Math.floor(riskAmount / price);
    
    return Math.max(1, quantity); // At least 1 share
  }

  /**
   * Get daily loss for an automation
   */
  async _getDailyLoss(automationId) {
    const query = `
      SELECT SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as daily_loss
      FROM automated_orders
      WHERE automation_id = $1
        AND created_at >= CURRENT_DATE
        AND status = 'COMPLETE'
    `;

    const result = await this.db.query(query, [automationId]);
    return parseFloat(result.rows[0]?.daily_loss) || 0;
  }

  /**
   * Get daily trade count for an automation
   */
  async _getDailyTradeCount(automationId) {
    const query = `
      SELECT COUNT(*) as trade_count
      FROM automated_orders
      WHERE automation_id = $1
        AND created_at >= CURRENT_DATE
    `;

    const result = await this.db.query(query, [automationId]);
    return parseInt(result.rows[0]?.trade_count) || 0;
  }

  /**
   * Get total loss for an automation
   */
  async _getTotalLoss(automationId) {
    const query = `
      SELECT SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as total_loss
      FROM automated_orders
      WHERE automation_id = $1
        AND status = 'COMPLETE'
    `;

    const result = await this.db.query(query, [automationId]);
    return parseFloat(result.rows[0]?.total_loss) || 0;
  }

  /**
   * Pause an automation
   */
  async pauseAutomation(automationId, reason) {
    const query = `
      UPDATE strategy_automations
      SET is_active = false,
          status = 'paused',
          updated_at = NOW()
      WHERE id = $1
      RETURNING *
    `;

    await this.db.query(query, [automationId]);

    console.log(`[ExecutionEngine] Automation ${automationId} paused: ${reason}`);

    // Emit event
    this.eventBus.emit('strategy.stopped', {
      automation_id: automationId,
      reason
    });
  }

  /**
   * Activate an approved automation
   */
  async activateAutomation(automationId) {
    const query = `
      UPDATE strategy_automations
      SET is_active = true,
          status = 'active',
          started_at = NOW(),
          updated_at = NOW()
      WHERE id = $1
        AND status = 'approved'
      RETURNING *
    `;

    const result = await this.db.query(query, [automationId]);

    if (result.rows.length === 0) {
      throw new Error('Automation not found or not in approved status');
    }

    console.log(`[ExecutionEngine] Automation ${automationId} activated`);

    return this._transformAutomation(result.rows[0]);
  }

  /**
   * Transform database row to camelCase
   */
  _transformAutomation(row) {
    return {
      id: row.id,
      userId: row.user_id,
      configId: row.config_id,
      name: row.name,
      profitTargetPercent: parseFloat(row.profit_target_percent),
      timeframeDays: row.timeframe_days,
      maxLossPercent: parseFloat(row.max_loss_percent),
      riskTolerance: row.risk_tolerance,
      symbols: row.symbols || [],
      strategyRules: row.strategy_rules,
      status: row.status,
      tradingMode: row.trading_mode,
      isActive: row.is_active,
      aiConfidenceScore: row.ai_confidence_score ? parseFloat(row.ai_confidence_score) : null,
      approvedAt: row.approved_at,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      createdAt: row.created_at,
      updatedAt: row.updated_at
    };
  }
}

// Singleton instance
let executionEngineInstance = null;

function getExecutionEngine() {
  if (!executionEngineInstance) {
    executionEngineInstance = new StrategyExecutionEngine();
  }
  return executionEngineInstance;
}

module.exports = getExecutionEngine;

