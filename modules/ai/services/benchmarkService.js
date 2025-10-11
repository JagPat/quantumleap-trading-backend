/**
 * Benchmark Service
 * Fetches and manages market benchmark data for performance comparison
 * Supports NIFTY50, BANKNIFTY, and sector indices
 */

const db = require('../../../core/database/connection');

class BenchmarkService {
  constructor() {
    this.supportedBenchmarks = [
      'NIFTY50',
      'BANKNIFTY',
      'NIFTYIT',
      'NIFTYPHARMA',
      'NIFTYAUTO',
      'NIFTYFINSERVICE',
      'NIFTYFMCG'
    ];
  }

  /**
   * Fetch benchmark data for a date range
   * @param {string} type - Benchmark type
   * @param {Object} dateRange - Start and end dates
   * @returns {Promise<Array>} Benchmark data
   */
  async fetchBenchmarkData(type, dateRange) {
    try {
      const { startDate, endDate } = dateRange;

      const query = `
        SELECT * FROM performance_benchmarks
        WHERE benchmark_type = $1
          AND date >= $2::date
          AND date <= $3::date
        ORDER BY date DESC
      `;

      const result = await db.query(query, [type, startDate, endDate]);

      if (result.rows.length === 0) {
        console.log(`[BenchmarkService] No data found for ${type}, will need to fetch from external API`);
        // TODO: Integrate with NSE API or other market data provider
        return [];
      }

      return result.rows;

    } catch (error) {
      console.error('[BenchmarkService] Error fetching benchmark data:', error.message);
      return [];
    }
  }

  /**
   * Calculate benchmark returns for a period
   * @param {string} type - Benchmark type
   * @param {number} period - Days lookback
   * @returns {Promise<Object>} Return metrics
   */
  async calculateBenchmarkReturns(type, period = 30) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - period);

      const query = `
        SELECT 
          MIN(date) as start_date,
          MAX(date) as end_date,
          (SELECT close_value FROM performance_benchmarks 
           WHERE benchmark_type = $1 AND date >= $2::date 
           ORDER BY date ASC LIMIT 1) as start_value,
          (SELECT close_value FROM performance_benchmarks 
           WHERE benchmark_type = $1 AND date >= $2::date 
           ORDER BY date DESC LIMIT 1) as end_value,
          AVG(daily_return_percent) as avg_daily_return,
          STDDEV(daily_return_percent) as volatility,
          COUNT(*) as trading_days
        FROM performance_benchmarks
        WHERE benchmark_type = $1
          AND date >= $2::date
      `;

      const result = await db.query(query, [type, cutoffDate]);

      if (result.rows.length === 0 || !result.rows[0].start_value) {
        return {
          benchmark: type,
          period,
          error: 'Insufficient data'
        };
      }

      const stats = result.rows[0];
      const periodReturn = ((stats.end_value - stats.start_value) / stats.start_value) * 100;

      return {
        benchmark: type,
        period,
        startDate: stats.start_date,
        endDate: stats.end_date,
        startValue: parseFloat(stats.start_value),
        endValue: parseFloat(stats.end_value),
        periodReturn: parseFloat(periodReturn.toFixed(2)),
        avgDailyReturn: parseFloat(stats.avg_daily_return) || 0,
        volatility: parseFloat(stats.volatility) || 0,
        tradingDays: parseInt(stats.trading_days)
      };

    } catch (error) {
      console.error('[BenchmarkService] Error calculating returns:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Compare strategy performance to benchmark
   * @param {number} executionId - Strategy execution ID
   * @param {string} benchmarkType - Benchmark to compare against
   * @returns {Promise<Object>} Comparison result
   */
  async compareStrategyToBenchmark(executionId, benchmarkType = 'NIFTY50') {
    try {
      // Get execution details
      const execQuery = `
        SELECT 
          executed_at,
          closed_at,
          outcome_summary
        FROM strategy_executions
        WHERE id = $1
      `;

      const execResult = await db.query(execQuery, [executionId]);
      
      if (execResult.rows.length === 0) {
        return { error: 'Execution not found' };
      }

      const execution = execResult.rows[0];
      
      if (!execution.outcome_summary) {
        return { error: 'Execution not yet closed' };
      }

      const strategyReturn = execution.outcome_summary.pnl_percent || 0;

      // Get benchmark return for same period
      const benchmarkQuery = `
        SELECT 
          (SELECT close_value FROM performance_benchmarks 
           WHERE benchmark_type = $1 AND date >= $2::date 
           ORDER BY date ASC LIMIT 1) as start_value,
          (SELECT close_value FROM performance_benchmarks 
           WHERE benchmark_type = $1 AND date <= $3::date 
           ORDER BY date DESC LIMIT 1) as end_value
      `;

      const benchmarkResult = await db.query(benchmarkQuery, [
        benchmarkType,
        execution.executed_at,
        execution.closed_at || new Date()
      ]);

      if (!benchmarkResult.rows[0]?.start_value) {
        return { 
          error: 'Benchmark data not available for this period',
          strategyReturn 
        };
      }

      const benchData = benchmarkResult.rows[0];
      const benchmarkReturn = ((benchData.end_value - benchData.start_value) / benchData.start_value) * 100;
      const alpha = strategyReturn - benchmarkReturn;

      return {
        executionId,
        benchmarkType,
        strategyReturn: parseFloat(strategyReturn.toFixed(2)),
        benchmarkReturn: parseFloat(benchmarkReturn.toFixed(2)),
        alpha: parseFloat(alpha.toFixed(2)),
        outperformed: alpha > 0
      };

    } catch (error) {
      console.error('[BenchmarkService] Error comparing to benchmark:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Calculate alpha and beta for a strategy
   * @param {number} executionId - Execution ID
   * @param {string} benchmarkType - Benchmark type
   * @returns {Promise<Object>} Alpha/Beta metrics
   */
  async getAlphaBeta(executionId, benchmarkType = 'NIFTY50') {
    try {
      const comparison = await this.compareStrategyToBenchmark(executionId, benchmarkType);
      
      if (comparison.error) {
        return comparison;
      }

      // Simple alpha calculation (already done in comparison)
      const alpha = comparison.alpha;

      // Beta calculation would require correlation analysis
      // For MVP, we'll use a simplified approach
      const beta = comparison.strategyReturn / comparison.benchmarkReturn;

      return {
        executionId,
        benchmarkType,
        alpha: parseFloat(alpha.toFixed(2)),
        beta: parseFloat(beta.toFixed(2)),
        interpretation: {
          alpha: alpha > 0 ? 'Outperforming market' : 'Underperforming market',
          beta: beta > 1 ? 'More volatile than market' : 'Less volatile than market'
        }
      };

    } catch (error) {
      console.error('[BenchmarkService] Error calculating alpha/beta:', error.message);
      return { error: error.message };
    }
  }

  /**
   * Store benchmark data (for cron job/manual updates)
   * @param {string} type - Benchmark type
   * @param {Date} date - Date
   * @param {Object} data - Market data
   * @returns {Promise<void>}
   */
  async storeBenchmarkData(type, date, data) {
    try {
      const {
        openValue,
        closeValue,
        dailyReturnPercent
      } = data;

      const query = `
        INSERT INTO performance_benchmarks 
        (benchmark_type, date, open_value, close_value, daily_return_percent)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (benchmark_type, date) 
        DO UPDATE SET 
          open_value = EXCLUDED.open_value,
          close_value = EXCLUDED.close_value,
          daily_return_percent = EXCLUDED.daily_return_percent
      `;

      await db.query(query, [
        type,
        date,
        openValue,
        closeValue,
        dailyReturnPercent
      ]);

      console.log(`[BenchmarkService] Stored benchmark data for ${type} on ${date}`);

    } catch (error) {
      console.error('[BenchmarkService] Error storing benchmark data:', error.message);
      throw error;
    }
  }

  /**
   * Calculate rolling period returns (30d, 90d)
   * Should be called daily to update period returns
   * @returns {Promise<void>}
   */
  async calculateRollingReturns() {
    try {
      console.log('[BenchmarkService] Calculating rolling returns...');

      for (const benchmark of this.supportedBenchmarks) {
        // Calculate 30-day returns
        const returns30 = await this.calculateBenchmarkReturns(benchmark, 30);
        
        // Calculate 90-day returns
        const returns90 = await this.calculateBenchmarkReturns(benchmark, 90);

        // Update latest record
        const updateQuery = `
          UPDATE performance_benchmarks
          SET 
            period_return_30d = $1,
            period_return_90d = $2
          WHERE benchmark_type = $3
            AND date = (SELECT MAX(date) FROM performance_benchmarks WHERE benchmark_type = $3)
        `;

        await db.query(updateQuery, [
          returns30.periodReturn || 0,
          returns90.periodReturn || 0,
          benchmark
        ]);
      }

      console.log('[BenchmarkService] Rolling returns calculated successfully');

    } catch (error) {
      console.error('[BenchmarkService] Error calculating rolling returns:', error.message);
      throw error;
    }
  }

  /**
   * Get supported benchmarks
   * @returns {Array<string>} Benchmark types
   */
  getSupportedBenchmarks() {
    return this.supportedBenchmarks;
  }
}

// Singleton
let instance = null;

function getBenchmarkService() {
  if (!instance) {
    instance = new BenchmarkService();
  }
  return instance;
}

module.exports = {
  BenchmarkService,
  getBenchmarkService
};

