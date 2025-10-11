/**
 * Feedback Integration Service
 * Generates learning insights from trade outcomes
 * Feeds insights back into future AI decisions
 */

const db = require('../../../core/database/connection');
const TradeOutcomeTracker = require('./tradeOutcomeTracker');
const DecisionAttributionTracker = require('./decisionAttributionTracker');

class FeedbackIntegrationService {
  constructor() {
    this.outcomeTracker = new TradeOutcomeTracker();
    this.attributionTracker = new DecisionAttributionTracker();
  }

  /**
   * Generate learning insights from recent outcomes
   * @param {number} lookbackDays - Days to analyze
   * @returns {Array} Generated insights
   */
  async generateLearningInsights(lookbackDays = 30) {
    console.log(`[FeedbackIntegration] Generating insights from last ${lookbackDays} days...`);

    try {
      const insights = [];

      // 1. Data Source Performance Insights
      const dataSourceInsights = await this.analyzeDataSourcePerformance(lookbackDays);
      insights.push(...dataSourceInsights);

      // 2. Symbol/Sector Performance Insights
      const symbolInsights = await this.analyzeSymbolPerformance(lookbackDays);
      insights.push(...symbolInsights);

      // 3. Market Regime Performance Insights
      const regimeInsights = await this.analyzeRegimePerformance(lookbackDays);
      insights.push(...regimeInsights);

      // 4. Timing Insights (holding period vs performance)
      const timingInsights = await this.analyzeTimingPerformance(lookbackDays);
      insights.push(...timingInsights);

      // 5. User Override Insights
      const overrideInsights = await this.analyzeUserOverrides(lookbackDays);
      insights.push(...overrideInsights);

      // Store insights in database
      for (const insight of insights) {
        await this.storeInsight(insight, lookbackDays);
      }

      console.log(`[FeedbackIntegration] Generated ${insights.length} insights`);
      return insights;

    } catch (error) {
      console.error('[FeedbackIntegration] Error generating insights:', error.message);
      return [];
    }
  }

  /**
   * Analyze data source performance
   */
  async analyzeDataSourcePerformance(lookbackDays) {
    const insights = [];
    const dataSources = ['news', 'sentiment', 'fundamentals', 'technical', 'regime'];

    for (const source of dataSources) {
      const performance = await this.outcomeTracker.getPerformanceByDataSource(source, lookbackDays);
      
      if (performance && performance.tradeCount >= 5) {
        let insightText = '';
        let confidence = performance.confidence;

        if (performance.recommendation === 'highly_recommended') {
          insightText = `${source} data has been highly effective, with ${(performance.winRate * 100).toFixed(0)}% win rate and +${performance.avgPnLPercent.toFixed(2)}% avg return. Prioritize ${source} signals.`;
        } else if (performance.recommendation === 'recommended') {
          insightText = `${source} data shows positive results (${(performance.winRate * 100).toFixed(0)}% win rate). Continue using with moderate weight.`;
        } else if (performance.recommendation === 'use_with_caution') {
          insightText = `${source} data has mixed results (${(performance.winRate * 100).toFixed(0)}% win rate). Use only when corroborated by other sources.`;
        } else if (performance.recommendation === 'not_recommended') {
          insightText = `${source} data has underperformed (${(performance.winRate * 100).toFixed(0)}% win rate, ${performance.avgPnLPercent.toFixed(2)}% avg return). Reduce reliance on ${source}.`;
          confidence = Math.max(confidence, 0.7); // High confidence in negative signal
        }

        if (insightText) {
          insights.push({
            insightType: 'data_source_performance',
            insightText,
            confidence,
            sampleSize: performance.tradeCount,
            metadata: { source, performance }
          });
        }
      }
    }

    return insights;
  }

  /**
   * Analyze symbol/sector performance
   */
  async analyzeSymbolPerformance(lookbackDays) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          symbol,
          COUNT(*) as trade_count,
          COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
          AVG(pnl_percent) as avg_return,
          SUM(pnl) as total_pnl
        FROM trade_outcomes
        WHERE closed_at >= $1 AND closed_at IS NOT NULL
        GROUP BY symbol
        HAVING COUNT(*) >= 3
        ORDER BY avg_return DESC
      `;

      const result = await db.query(query, [cutoffDate]);
      const insights = [];

      // Top performers
      const topPerformers = result.rows.slice(0, 5);
      for (const stock of topPerformers) {
        const winRate = parseInt(stock.winning_trades) / parseInt(stock.trade_count);
        if (winRate >= 0.6 && parseFloat(stock.avg_return) > 2) {
          insights.push({
            insightType: 'symbol_performance',
            insightText: `${stock.symbol} has performed well with ${(winRate * 100).toFixed(0)}% win rate and +${parseFloat(stock.avg_return).toFixed(2)}% avg return. Consider accumulating on dips.`,
            confidence: Math.min(parseInt(stock.trade_count) / 10, 0.9),
            sampleSize: parseInt(stock.trade_count),
            metadata: { symbol: stock.symbol, performance: stock }
          });
        }
      }

      // Poor performers
      const poorPerformers = result.rows.slice(-5);
      for (const stock of poorPerformers) {
        const winRate = parseInt(stock.winning_trades) / parseInt(stock.trade_count);
        if (winRate < 0.4 || parseFloat(stock.avg_return) < -1) {
          insights.push({
            insightType: 'symbol_performance',
            insightText: `${stock.symbol} has underperformed with ${(winRate * 100).toFixed(0)}% win rate and ${parseFloat(stock.avg_return).toFixed(2)}% avg return. Avoid or require stronger signals.`,
            confidence: Math.min(parseInt(stock.trade_count) / 10, 0.9),
            sampleSize: parseInt(stock.trade_count),
            metadata: { symbol: stock.symbol, performance: stock }
          });
        }
      }

      return insights;

    } catch (error) {
      console.error('[FeedbackIntegration] Error analyzing symbol performance:', error.message);
      return [];
    }
  }

  /**
   * Analyze performance by market regime
   */
  async analyzeRegimePerformance(lookbackDays) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          d.market_regime,
          COUNT(*) as trade_count,
          COUNT(*) FILTER (WHERE t.pnl > 0) as winning_trades,
          AVG(t.pnl_percent) as avg_return
        FROM trade_outcomes t
        JOIN ai_decisions d ON t.decision_id = d.id
        WHERE t.closed_at >= $1 AND t.closed_at IS NOT NULL
        GROUP BY d.market_regime
        HAVING COUNT(*) >= 5
      `;

      const result = await db.query(query, [cutoffDate]);
      const insights = [];

      for (const regime of result.rows) {
        const winRate = parseInt(regime.winning_trades) / parseInt(regime.trade_count);
        const avgReturn = parseFloat(regime.avg_return);

        let insightText = '';
        if (winRate >= 0.6) {
          insightText = `Strategies perform well in ${regime.market_regime} regime (${(winRate * 100).toFixed(0)}% win rate, +${avgReturn.toFixed(2)}% avg). Increase position sizing in this regime.`;
        } else if (winRate < 0.4) {
          insightText = `Strategies struggle in ${regime.market_regime} regime (${(winRate * 100).toFixed(0)}% win rate, ${avgReturn.toFixed(2)}% avg). Use more conservative approach or avoid trading.`;
        }

        if (insightText) {
          insights.push({
            insightType: 'regime_performance',
            insightText,
            confidence: Math.min(parseInt(regime.trade_count) / 10, 0.9),
            sampleSize: parseInt(regime.trade_count),
            metadata: { regime: regime.market_regime, winRate, avgReturn }
          });
        }
      }

      return insights;

    } catch (error) {
      console.error('[FeedbackIntegration] Error analyzing regime performance:', error.message);
      return [];
    }
  }

  /**
   * Analyze holding period vs performance
   */
  async analyzeTimingPerformance(lookbackDays) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          CASE 
            WHEN holding_period_hours < 24 THEN 'intraday'
            WHEN holding_period_hours < 168 THEN 'short_term'
            WHEN holding_period_hours < 720 THEN 'medium_term'
            ELSE 'long_term'
          END as holding_category,
          COUNT(*) as trade_count,
          COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
          AVG(pnl_percent) as avg_return
        FROM trade_outcomes
        WHERE closed_at >= $1 AND closed_at IS NOT NULL
        GROUP BY holding_category
        HAVING COUNT(*) >= 5
      `;

      const result = await db.query(query, [cutoffDate]);
      const insights = [];

      for (const timing of result.rows) {
        const winRate = parseInt(timing.winning_trades) / parseInt(timing.trade_count);
        const avgReturn = parseFloat(timing.avg_return);

        if (winRate >= 0.6 && avgReturn > 2) {
          insights.push({
            insightType: 'timing_performance',
            insightText: `${timing.holding_category.replace('_', ' ')} trades have high success rate (${(winRate * 100).toFixed(0)}% win rate, +${avgReturn.toFixed(2)}% avg). Focus on this timeframe.`,
            confidence: Math.min(parseInt(timing.trade_count) / 10, 0.8),
            sampleSize: parseInt(timing.trade_count),
            metadata: { category: timing.holding_category, winRate, avgReturn }
          });
        }
      }

      return insights;

    } catch (error) {
      console.error('[FeedbackIntegration] Error analyzing timing performance:', error.message);
      return [];
    }
  }

  /**
   * Analyze user overrides
   */
  async analyzeUserOverrides(lookbackDays) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      const query = `
        SELECT 
          user_override,
          COUNT(*) as trade_count,
          COUNT(*) FILTER (WHERE pnl > 0) as winning_trades,
          AVG(pnl_percent) as avg_return
        FROM trade_outcomes
        WHERE closed_at >= $1 AND closed_at IS NOT NULL
        GROUP BY user_override
      `;

      const result = await db.query(query, [cutoffDate]);
      const insights = [];

      const aiTrades = result.rows.find(r => r.user_override === false);
      const userTrades = result.rows.find(r => r.user_override === true);

      if (aiTrades && userTrades) {
        const aiWinRate = parseInt(aiTrades.winning_trades) / parseInt(aiTrades.trade_count);
        const userWinRate = parseInt(userTrades.winning_trades) / parseInt(userTrades.trade_count);

        if (aiWinRate > userWinRate + 0.1) {
          insights.push({
            insightType: 'override_analysis',
            insightText: `AI decisions outperform manual overrides (${(aiWinRate * 100).toFixed(0)}% vs ${(userWinRate * 100).toFixed(0)}% win rate). Trust AI recommendations more.`,
            confidence: 0.8,
            sampleSize: parseInt(aiTrades.trade_count) + parseInt(userTrades.trade_count),
            metadata: { aiWinRate, userWinRate }
          });
        } else if (userWinRate > aiWinRate + 0.1) {
          insights.push({
            insightType: 'override_analysis',
            insightText: `Manual overrides outperform AI (${(userWinRate * 100).toFixed(0)}% vs ${(aiWinRate * 100).toFixed(0)}% win rate). Your judgment adds value - continue overriding when confident.`,
            confidence: 0.8,
            sampleSize: parseInt(aiTrades.trade_count) + parseInt(userTrades.trade_count),
            metadata: { aiWinRate, userWinRate }
          });
        }
      }

      return insights;

    } catch (error) {
      console.error('[FeedbackIntegration] Error analyzing user overrides:', error.message);
      return [];
    }
  }

  /**
   * Store insight in database
   */
  async storeInsight(insight, lookbackDays) {
    try {
      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + lookbackDays); // Insights expire after same period

      const query = `
        INSERT INTO learning_insights
        (insight_type, insight_text, confidence, sample_size, metadata, generated_at, expires_at)
        VALUES ($1, $2, $3, $4, $5, NOW(), $6)
        ON CONFLICT (insight_type, insight_text) 
        DO UPDATE SET 
          confidence = $3,
          sample_size = $4,
          metadata = $5,
          generated_at = NOW(),
          expires_at = $6
      `;

      await db.query(query, [
        insight.insightType,
        insight.insightText,
        insight.confidence,
        insight.sampleSize,
        JSON.stringify(insight.metadata),
        expiresAt
      ]);

    } catch (error) {
      // Ignore duplicate errors, update existing
      if (!error.message.includes('duplicate') && !error.message.includes('conflict')) {
        console.error('[FeedbackIntegration] Error storing insight:', error.message);
      }
    }
  }

  /**
   * Get contextual learnings for current decision
   * @param {string} symbol - Optional symbol to filter
   * @param {string} taskType - 'stock_selection', 'portfolio_action', etc.
   */
  async getContextualLearnings(symbol = null, taskType = 'general') {
    try {
      let query = `
        SELECT 
          insight_type,
          insight_text,
          confidence,
          sample_size,
          metadata
        FROM learning_insights
        WHERE expires_at > NOW()
      `;

      const params = [];

      if (symbol) {
        query += ` AND (metadata->>'symbol' = $1 OR insight_type IN ('data_source_performance', 'regime_performance'))`;
        params.push(symbol);
      }

      if (taskType !== 'general') {
        // Filter by relevant insight types
        if (taskType === 'stock_selection') {
          query += ` AND insight_type IN ('data_source_performance', 'symbol_performance', 'regime_performance')`;
        } else if (taskType === 'portfolio_action') {
          query += ` AND insight_type IN ('symbol_performance', 'regime_performance', 'timing_performance')`;
        }
      }

      query += ` ORDER BY confidence DESC, generated_at DESC LIMIT 10`;

      const result = await db.query(query, params);
      
      return result.rows.map(row => ({
        type: row.insight_type,
        insight: row.insight_text,
        confidence: parseFloat(row.confidence),
        sampleSize: parseInt(row.sample_size),
        metadata: row.metadata
      }));

    } catch (error) {
      console.error('[FeedbackIntegration] Error getting contextual learnings:', error.message);
      return [];
    }
  }

  /**
   * Format learnings for LLM prompt
   */
  formatLearningsForPrompt(learnings) {
    if (!learnings || learnings.length === 0) {
      return 'No historical learnings available yet.';
    }

    return learnings.map(l => {
      return `- ${l.insight} (Confidence: ${(l.confidence * 100).toFixed(0)}%, based on ${l.sampleSize} trades)`;
    }).join('\n');
  }

  /**
   * Adjust confidence thresholds based on recent performance
   */
  async adjustConfidenceThresholds(userId) {
    try {
      const performance = await this.outcomeTracker.getUserPerformanceSummary(userId, 30);
      
      if (!performance || performance.totalTrades < 10) {
        return { threshold: 0.7, reason: 'Insufficient data, using default threshold' };
      }

      // If win rate is high, we can be more aggressive (lower threshold)
      if (performance.winRate >= 0.65) {
        return { threshold: 0.6, reason: 'High historical win rate allows lower confidence threshold' };
      }
      
      // If win rate is low, be more conservative (higher threshold)
      if (performance.winRate < 0.45) {
        return { threshold: 0.8, reason: 'Low historical win rate requires higher confidence threshold' };
      }

      return { threshold: 0.7, reason: 'Standard threshold based on moderate performance' };

    } catch (error) {
      console.error('[FeedbackIntegration] Error adjusting confidence thresholds:', error.message);
      return { threshold: 0.7, reason: 'Error, using default threshold' };
    }
  }
}

module.exports = FeedbackIntegrationService;

