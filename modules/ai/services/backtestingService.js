const db = require('../../../core/database/connection');

/**
 * Backtesting Service
 * Simulates strategy performance over historical data
 */
class BacktestingService {
  /**
   * Run backtest for a strategy
   * @param {number} strategyId - Strategy ID
   * @param {string} timeframe - Timeframe (1Y/3Y/5Y)
   * @param {number} days - Number of days
   * @returns {Object} Backtest results
   */
  async runBacktest(strategyId, timeframe, days) {
    try {
      console.log(`[BacktestingService] Running backtest for strategy ${strategyId} over ${timeframe}`);

      // Get strategy details
      const strategyQuery = `SELECT * FROM strategy_automations WHERE id = $1`;
      const strategyResult = await db.query(strategyQuery, [strategyId]);
      
      if (strategyResult.rows.length === 0) {
        throw new Error('Strategy not found');
      }

      const strategy = strategyResult.rows[0];

      // Simulate backtest results (simplified for MVP)
      const results = this.generateBacktestResults(strategy, days);
      const benchmark = this.generateBenchmarkResults(days);

      return {
        results,
        benchmark,
        strategyId,
        timeframe,
        executedAt: new Date().toISOString()
      };
    } catch (error) {
      console.error('[BacktestingService] Error:', error);
      throw error;
    }
  }

  /**
   * Generate simulated backtest results
   * @param {Object} strategy - Strategy object
   * @param {number} days - Number of days
   * @returns {Object} Backtest results
   */
  generateBacktestResults(strategy, days) {
    // Simulate realistic performance metrics
    const baseReturn = Math.random() * 40 - 10; // -10% to +30%
    const volatility = 0.15 + Math.random() * 0.15; // 15-30% volatility
    const sharpeRatio = (baseReturn / 100) / volatility;
    const maxDrawdown = -(10 + Math.random() * 20); // -10% to -30%
    
    const totalTrades = Math.floor(days / 10); // ~1 trade per 10 days
    const winRate = 45 + Math.random() * 25; // 45-70%
    const winningTrades = Math.floor(totalTrades * (winRate / 100));
    const losingTrades = totalTrades - winningTrades;

    // Generate equity curve
    const equityCurve = [];
    let currentValue = 100;
    const dailyReturn = baseReturn / days / 100;
    
    for (let i = 0; i < Math.min(days, 365); i++) {
      const randomness = (Math.random() - 0.5) * volatility * 0.1;
      currentValue = currentValue * (1 + dailyReturn + randomness);
      
      if (i % Math.ceil(days / 50) === 0) { // 50 data points
        equityCurve.push({
          date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          value: currentValue.toFixed(2)
        });
      }
    }

    // Generate trade distribution
    const tradeDistribution = [
      { range: '<-5%', count: Math.floor(losingTrades * 0.2) },
      { range: '-5% to -2%', count: Math.floor(losingTrades * 0.5) },
      { range: '-2% to 0%', count: Math.floor(losingTrades * 0.3) },
      { range: '0% to 2%', count: Math.floor(winningTrades * 0.3) },
      { range: '2% to 5%', count: Math.floor(winningTrades * 0.5) },
      { range: '>5%', count: Math.floor(winningTrades * 0.2) },
    ];

    return {
      totalReturn: baseReturn,
      sharpeRatio: sharpeRatio.toFixed(2),
      maxDrawdown: maxDrawdown.toFixed(2),
      winRate: winRate.toFixed(1),
      totalTrades,
      winningTrades,
      losingTrades,
      equityCurve,
      tradeDistribution
    };
  }

  /**
   * Generate benchmark (NIFTY 50) results
   * @param {number} days - Number of days
   * @returns {Object} Benchmark results
   */
  generateBenchmarkResults(days) {
    // NIFTY 50 typically returns 10-15% annually
    const annualReturn = 10 + Math.random() * 5;
    const totalReturn = annualReturn * (days / 365);

    const equityCurve = [];
    let currentValue = 100;
    const dailyReturn = totalReturn / days / 100;
    
    for (let i = 0; i < Math.min(days, 365); i++) {
      const randomness = (Math.random() - 0.5) * 0.02; // Lower volatility
      currentValue = currentValue * (1 + dailyReturn + randomness);
      
      if (i % Math.ceil(days / 50) === 0) {
        equityCurve.push({
          date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          value: currentValue.toFixed(2)
        });
      }
    }

    return {
      name: 'NIFTY 50',
      totalReturn: totalReturn.toFixed(2),
      equityCurve
    };
  }

  /**
   * Compare multiple strategies
   * @param {Array} strategyIds - Array of strategy IDs
   * @param {string} timeframe - Timeframe
   * @returns {Array} Comparison results
   */
  async compareStrategies(strategyIds, timeframe) {
    try {
      const days = timeframe === '5Y' ? 1825 : timeframe === '3Y' ? 1095 : 365;
      
      const comparisons = await Promise.all(
        strategyIds.map(async (id) => {
          const result = await this.runBacktest(id, timeframe, days);
          return {
            strategyId: id,
            totalReturn: result.results.totalReturn,
            sharpeRatio: result.results.sharpeRatio,
            maxDrawdown: result.results.maxDrawdown,
            winRate: result.results.winRate
          };
        })
      );

      return comparisons;
    } catch (error) {
      console.error('[BacktestingService] Compare error:', error);
      throw error;
    }
  }
}

// Singleton
let backtestingServiceInstance = null;

function getBacktestingService() {
  if (!backtestingServiceInstance) {
    backtestingServiceInstance = new BacktestingService();
  }
  return backtestingServiceInstance;
}

module.exports = {
  BacktestingService,
  getBacktestingService
};

