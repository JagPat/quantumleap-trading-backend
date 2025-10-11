/**
 * Daily Learning Job
 * Scheduled task that runs daily at 6:00 AM IST
 * 
 * Responsibilities:
 * 1. Ingest research data for top 100 stocks
 * 2. Detect current market regime
 * 3. Analyze yesterday's closed trades
 * 4. Generate learning insights
 * 5. Clean old data (>90 days)
 */

const ResearchIngestionService = require('../services/researchIngestionService');
const MarketRegimeAnalyzer = require('../services/marketRegimeAnalyzer');
const TradeOutcomeTracker = require('../services/tradeOutcomeTracker');
const FeedbackIntegrationService = require('../services/feedbackIntegrationService');
const getMarketUniverse = require('../services/marketUniverse');

class DailyLearningJob {
  constructor() {
    this.researchService = new ResearchIngestionService();
    this.regimeAnalyzer = new MarketRegimeAnalyzer();
    this.outcomeTracker = new TradeOutcomeTracker();
    this.feedbackService = new FeedbackIntegrationService();
    this.marketUniverse = getMarketUniverse();
  }

  /**
   * Execute daily learning cycle
   */
  async run() {
    const startTime = Date.now();
    console.log('═══════════════════════════════════════════════════════');
    console.log('[DailyLearningJob] 🌅 Starting daily learning cycle...');
    console.log(`[DailyLearningJob] Timestamp: ${new Date().toISOString()}`);
    console.log('═══════════════════════════════════════════════════════');

    const report = {
      startedAt: new Date().toISOString(),
      steps: {},
      errors: [],
      summary: {}
    };

    try {
      // Step 1: Ingest Research Data
      console.log('\n📊 [Step 1/5] Ingesting research data...');
      const symbols = this.marketUniverse.getTopLiquidStocks(100).map(s => s.symbol);
      
      const ingestionResult = await this.researchService.ingestDailyResearch(symbols);
      report.steps.research_ingestion = {
        status: 'success',
        news_articles: ingestionResult.news,
        sentiment_records: ingestionResult.sentiment,
        fundamental_updates: ingestionResult.fundamentals,
        macro_updates: ingestionResult.macro,
        errors: ingestionResult.errors
      };
      console.log(`✅ Ingested: ${ingestionResult.news} news, ${ingestionResult.sentiment} sentiment, ${ingestionResult.fundamentals} fundamentals`);
      
      // Step 2: Detect Market Regime
      console.log('\n🎯 [Step 2/5] Detecting market regime...');
      const regime = await this.regimeAnalyzer.detectCurrentRegime();
      report.steps.regime_detection = {
        status: 'success',
        regime: regime.regime,
        confidence: regime.confidence,
        reasoning: regime.reasoning,
        validUntil: regime.validUntil
      };
      console.log(`✅ Regime: ${regime.regime} (${(regime.confidence * 100).toFixed(0)}% confidence)`);
      console.log(`   Reasoning: ${regime.reasoning.substring(0, 100)}...`);
      
      // Step 3: Analyze Yesterday's Closed Trades
      console.log('\n📈 [Step 3/5] Analyzing closed trades...');
      const closedTrades = await this.outcomeTracker.getRecentClosedTrades(1); // Yesterday
      report.steps.trade_analysis = {
        status: 'success',
        trades_analyzed: closedTrades.length,
        profitable_trades: closedTrades.filter(t => t.pnl > 0).length
      };
      
      if (closedTrades.length > 0) {
        const totalPnL = closedTrades.reduce((sum, t) => sum + parseFloat(t.pnl || 0), 0);
        console.log(`✅ Analyzed ${closedTrades.length} trades, Total PnL: ₹${totalPnL.toFixed(2)}`);
        
        // Process each trade outcome
        for (const trade of closedTrades) {
          // Attribution accuracy already updated via onTradeClose hook
          console.log(`   - ${trade.symbol}: ${trade.pnl > 0 ? '✅' : '❌'} ₹${trade.pnl.toFixed(2)} (${trade.pnl_percent?.toFixed(2)}%)`);
        }
      } else {
        console.log('ℹ️  No trades closed yesterday');
      }
      
      // Step 4: Generate Learning Insights
      console.log('\n🧠 [Step 4/5] Generating learning insights...');
      const insights = await this.feedbackService.generateLearningInsights(30); // Last 30 days
      report.steps.learning_insights = {
        status: 'success',
        insights_generated: insights.length,
        insight_types: this.countInsightTypes(insights)
      };
      console.log(`✅ Generated ${insights.length} learning insights`);
      
      // Display top insights
      insights.slice(0, 5).forEach((insight, idx) => {
        console.log(`   ${idx + 1}. [${insight.insightType}] ${insight.insightText.substring(0, 80)}...`);
      });
      
      // Step 5: Clean Old Data
      console.log('\n🧹 [Step 5/5] Cleaning old data...');
      const cleanupCount = await this.researchService.cleanupOldData();
      report.steps.cleanup = {
        status: 'success',
        records_deleted: cleanupCount
      };
      console.log(`✅ Cleaned ${cleanupCount} old research records (>90 days)`);
      
      // Generate summary
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      report.completedAt = new Date().toISOString();
      report.duration_seconds = duration;
      report.summary = {
        total_steps: 5,
        successful_steps: 5,
        errors: report.errors.length,
        status: 'success'
      };
      
      console.log('\n═══════════════════════════════════════════════════════');
      console.log(`[DailyLearningJob] ✅ Daily learning cycle COMPLETE`);
      console.log(`[DailyLearningJob] Duration: ${duration}s`);
      console.log(`[DailyLearningJob] Next run: Tomorrow 6:00 AM IST`);
      console.log('═══════════════════════════════════════════════════════\n');
      
      return report;
      
    } catch (error) {
      console.error('[DailyLearningJob] ❌ Error in daily learning cycle:', error.message);
      report.errors.push({
        step: 'unknown',
        error: error.message,
        timestamp: new Date().toISOString()
      });
      report.summary = {
        total_steps: 5,
        successful_steps: Object.keys(report.steps).length,
        errors: report.errors.length,
        status: 'partial_failure'
      };
      
      return report;
    }
  }

  /**
   * Count insight types for reporting
   */
  countInsightTypes(insights) {
    const counts = {};
    for (const insight of insights) {
      counts[insight.insightType] = (counts[insight.insightType] || 0) + 1;
    }
    return counts;
  }

  /**
   * Trigger on-demand learning (for testing or manual triggers)
   */
  async runOnDemand(options = {}) {
    console.log('[DailyLearningJob] Running on-demand learning cycle...');
    
    const config = {
      symbols: options.symbols || this.marketUniverse.getTopLiquidStocks(20).map(s => s.symbol), // Fewer for on-demand
      lookbackDays: options.lookbackDays || 7,
      skipCleanup: options.skipCleanup || false
    };
    
    const report = {
      mode: 'on_demand',
      startedAt: new Date().toISOString(),
      config,
      results: {}
    };
    
    try {
      // Quick research ingest for selected symbols
      const ingestionResult = await this.researchService.ingestDailyResearch(config.symbols);
      report.results.ingestion = ingestionResult;
      
      // Detect regime
      const regime = await this.regimeAnalyzer.detectCurrentRegime();
      report.results.regime = {
        regime: regime.regime,
        confidence: regime.confidence
      };
      
      // Generate insights
      const insights = await this.feedbackService.generateLearningInsights(config.lookbackDays);
      report.results.insights = {
        count: insights.length,
        insights: insights.slice(0, 10) // Top 10
      };
      
      report.status = 'success';
      report.completedAt = new Date().toISOString();
      
      console.log(`[DailyLearningJob] On-demand learning complete: ${insights.length} insights generated`);
      
      return report;
      
    } catch (error) {
      console.error('[DailyLearningJob] On-demand learning error:', error.message);
      report.status = 'error';
      report.error = error.message;
      return report;
    }
  }

  /**
   * Get job execution history
   */
  async getExecutionHistory(limit = 10) {
    try {
      // Query ai_usage_metrics for job execution records
      const query = `
        SELECT metadata, created_at
        FROM ai_usage_metrics
        WHERE metric_type = 'daily_learning_job'
        ORDER BY created_at DESC
        LIMIT $1
      `;
      
      const result = await db.query(query, [limit]);
      return result.rows.map(row => ({
        ...row.metadata,
        executedAt: row.created_at
      }));
      
    } catch (error) {
      console.error('[DailyLearningJob] Error getting execution history:', error.message);
      return [];
    }
  }

  /**
   * Store job execution record
   */
  async recordExecution(report) {
    try {
      await db.query(`
        INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
        VALUES ($1, $2, $3, $4, NOW())
      `, [
        'system',
        'daily_learning_job',
        report.summary?.status || 'unknown',
        JSON.stringify(report)
      ]);
      
    } catch (error) {
      console.error('[DailyLearningJob] Error recording execution:', error.message);
    }
  }
}

module.exports = DailyLearningJob;

