const db = require('../../../core/database/connection');
const OpenAIProvider = require('./providers/openai');
const AIPreferencesService = require('./preferences');

/**
 * Goal Suggestion Engine
 * Analyzes user portfolio and history to suggest optimal trading goals
 * Reduces manual input by providing AI-generated goal templates
 */
class GoalSuggestionEngine {
  constructor() {
    this.db = db;
    this.preferencesService = new AIPreferencesService();
  }

  /**
   * Suggest trading goals based on portfolio and history
   * @param {string} userId - User ID
   * @param {string} configId - Broker config ID
   * @param {Object} portfolioData - Current portfolio data
   * @returns {Object} 3 goal suggestions (conservative, moderate, aggressive)
   */
  async suggestGoals(userId, configId, portfolioData) {
    try {
      console.log('[GoalSuggestionEngine] Generating goal suggestions for user:', userId);

      // Get user's AI preferences
      const preferences = await this.preferencesService.getPreferences(userId);
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      // Analyze user's trading history
      const history = await this.getUserTradingHistory(userId);
      
      // Analyze portfolio composition
      const portfolioAnalysis = this.analyzePortfolio(portfolioData);

      // Get past strategy performance
      const pastStrategies = await this.getPastStrategyPerformance(userId);

      // Generate AI suggestions
      const aiProvider = new OpenAIProvider(preferences.openai_api_key);
      const suggestions = await this.generateSuggestions(
        aiProvider,
        portfolioAnalysis,
        history,
        pastStrategies
      );

      console.log('[GoalSuggestionEngine] Generated 3 goal suggestions');

      return {
        success: true,
        suggestions: suggestions,
        portfolio_analysis: portfolioAnalysis,
        based_on: {
          portfolio_value: portfolioAnalysis.totalValue,
          holdings_count: portfolioAnalysis.holdingsCount,
          past_strategies: pastStrategies.count,
          historical_trades: history.totalTrades
        }
      };

    } catch (error) {
      console.error('[GoalSuggestionEngine] Error generating suggestions:', error);
      throw error;
    }
  }

  /**
   * Analyze portfolio composition and risk
   */
  analyzePortfolio(portfolioData) {
    const holdings = portfolioData.holdings || [];
    const summary = portfolioData.summary || {};

    const totalValue = summary.total_value || summary.totalValue || 0;
    const totalPnL = summary.total_pnl || summary.totalPnl || 0;
    const pnlPercent = totalValue > 0 ? (totalPnL / (totalValue - totalPnL)) * 100 : 0;

    // Calculate concentration risk
    const holdingValues = holdings.map(h => h.current_value || h.currentValue || 0);
    const maxHoldingValue = Math.max(...holdingValues, 0);
    const concentrationRisk = totalValue > 0 ? (maxHoldingValue / totalValue) * 100 : 0;

    // Identify top holdings
    const topHoldings = holdings
      .sort((a, b) => (b.current_value || b.currentValue || 0) - (a.current_value || a.currentValue || 0))
      .slice(0, 5)
      .map(h => h.symbol);

    return {
      totalValue,
      totalPnL,
      pnlPercent,
      holdingsCount: holdings.length,
      concentrationRisk,
      topHoldings,
      riskProfile: concentrationRisk > 30 ? 'high' : concentrationRisk > 15 ? 'moderate' : 'low'
    };
  }

  /**
   * Get user's trading history
   */
  async getUserTradingHistory(userId) {
    try {
      const query = `
        SELECT 
          COUNT(*) as total_trades,
          SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as completed_trades,
          AVG(CASE WHEN net_amount > 0 THEN net_amount ELSE NULL END) as avg_profit,
          AVG(CASE WHEN net_amount < 0 THEN net_amount ELSE NULL END) as avg_loss
        FROM trades
        WHERE user_id = $1
          AND created_at > NOW() - INTERVAL '90 days'
      `;

      const result = await this.db.query(query, [userId]);
      const row = result.rows[0];

      return {
        totalTrades: parseInt(row.total_trades) || 0,
        completedTrades: parseInt(row.completed_trades) || 0,
        avgProfit: parseFloat(row.avg_profit) || 0,
        avgLoss: parseFloat(row.avg_loss) || 0,
        hasHistory: parseInt(row.total_trades) > 0
      };
    } catch (error) {
      console.warn('[GoalSuggestionEngine] Error fetching trading history:', error);
      return {
        totalTrades: 0,
        completedTrades: 0,
        avgProfit: 0,
        avgLoss: 0,
        hasHistory: false
      };
    }
  }

  /**
   * Get past strategy performance
   */
  async getPastStrategyPerformance(userId) {
    try {
      const query = `
        SELECT 
          COUNT(*) as total_strategies,
          AVG(profit_target_percent) as avg_profit_target,
          AVG(timeframe_days) as avg_timeframe,
          AVG(max_loss_percent) as avg_max_loss,
          COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
          risk_tolerance as most_common_risk
        FROM strategy_automations
        WHERE user_id = $1
        GROUP BY risk_tolerance
        ORDER BY COUNT(*) DESC
        LIMIT 1
      `;

      const result = await this.db.query(query, [userId]);
      
      if (result.rows.length === 0) {
        return {
          count: 0,
          avgProfitTarget: 10,
          avgTimeframe: 60,
          avgMaxLoss: 5,
          mostCommonRisk: 'moderate',
          hasHistory: false
        };
      }

      const row = result.rows[0];
      return {
        count: parseInt(row.total_strategies) || 0,
        avgProfitTarget: parseFloat(row.avg_profit_target) || 10,
        avgTimeframe: parseInt(row.avg_timeframe) || 60,
        avgMaxLoss: parseFloat(row.avg_max_loss) || 5,
        mostCommonRisk: row.most_common_risk || 'moderate',
        completedCount: parseInt(row.completed_count) || 0,
        hasHistory: true
      };
    } catch (error) {
      console.warn('[GoalSuggestionEngine] Error fetching past strategies:', error);
      return {
        count: 0,
        avgProfitTarget: 10,
        avgTimeframe: 60,
        avgMaxLoss: 5,
        mostCommonRisk: 'moderate',
        hasHistory: false
      };
    }
  }

  /**
   * Generate AI-powered goal suggestions
   */
  async generateSuggestions(aiProvider, portfolioAnalysis, history, pastStrategies) {
    const prompt = `
You are a trading strategy advisor. Analyze this user's profile and suggest 3 realistic trading goals.

**Portfolio Profile:**
- Total Value: ₹${portfolioAnalysis.totalValue.toLocaleString()}
- Current P&L: ₹${portfolioAnalysis.totalPnL.toLocaleString()} (${portfolioAnalysis.pnlPercent.toFixed(2)}%)
- Holdings: ${portfolioAnalysis.holdingsCount} stocks
- Concentration Risk: ${portfolioAnalysis.concentrationRisk.toFixed(1)}% (${portfolioAnalysis.riskProfile})
- Top Holdings: ${portfolioAnalysis.topHoldings.join(', ')}

**Trading History (Last 90 days):**
- Total Trades: ${history.totalTrades}
- Completed: ${history.completedTrades}
- Avg Profit: ₹${history.avgProfit.toFixed(0)}
- Avg Loss: ₹${history.avgLoss.toFixed(0)}

**Past Strategy Preferences:**
- Previous Strategies: ${pastStrategies.count}
- Preferred Risk: ${pastStrategies.mostCommonRisk}
- Avg Profit Target: ${pastStrategies.avgProfitTarget.toFixed(1)}%
- Avg Timeframe: ${pastStrategies.avgTimeframe} days

**Task:** Suggest 3 trading goals tailored to this user:
1. **Conservative**: Lower risk, longer timeframe, safer targets
2. **Moderate**: Balanced risk/reward, medium timeframe
3. **Aggressive**: Higher risk, shorter timeframe, ambitious targets

For each suggestion, provide:
- name: Strategy name (e.g., "Conservative Growth Q1")
- profitTarget: Percentage (realistic based on portfolio)
- timeframe: Days (appropriate for target)
- maxLoss: Percentage (safe limit)
- riskTolerance: "low" | "moderate" | "high"
- symbols: Array of 3-5 symbols from top holdings or sector diversification
- reasoning: Brief explanation why this goal suits the user

**IMPORTANT**: Respond ONLY with valid JSON in this exact format:
{
  "conservative": { "name": "...", "profitTarget": 5, "timeframe": 90, "maxLoss": 2, "riskTolerance": "low", "symbols": ["SYMBOL1", "SYMBOL2"], "reasoning": "..." },
  "moderate": { "name": "...", "profitTarget": 10, "timeframe": 60, "maxLoss": 5, "riskTolerance": "moderate", "symbols": ["SYMBOL1", "SYMBOL2"], "reasoning": "..." },
  "aggressive": { "name": "...", "profitTarget": 15, "timeframe": 30, "maxLoss": 8, "riskTolerance": "high", "symbols": ["SYMBOL1", "SYMBOL2"], "reasoning": "..." }
}
`;

    try {
      const response = await aiProvider.chat(prompt, {
        temperature: 0.7,
        model: 'gpt-3.5-turbo',
        response_format: { type: 'json_object' }
      });

      const suggestions = JSON.parse(response.content || response.reply || '{}');

      // Format suggestions as array
      return [
        { ...suggestions.conservative, template: 'conservative' },
        { ...suggestions.moderate, template: 'moderate' },
        { ...suggestions.aggressive, template: 'aggressive' }
      ];

    } catch (parseError) {
      console.warn('[GoalSuggestionEngine] Failed to parse AI response, using defaults');
      
      // Fallback to intelligent defaults based on portfolio
      return this.generateDefaultSuggestions(portfolioAnalysis, pastStrategies);
    }
  }

  /**
   * Generate default suggestions if AI fails
   */
  generateDefaultSuggestions(portfolioAnalysis, pastStrategies) {
    const { totalValue, topHoldings, riskProfile } = portfolioAnalysis;
    
    // Scale targets based on portfolio size
    const sizeMultiplier = totalValue > 10000000 ? 0.8 : totalValue > 1000000 ? 1.0 : 1.2;

    return [
      {
        template: 'conservative',
        name: 'Conservative Growth Strategy',
        profitTarget: Math.round(5 * sizeMultiplier),
        timeframe: 90,
        maxLoss: 2,
        riskTolerance: 'low',
        symbols: topHoldings.slice(0, 3),
        reasoning: 'Low-risk approach focusing on your best-performing holdings with extended timeframe'
      },
      {
        template: 'moderate',
        name: 'Balanced Growth Strategy',
        profitTarget: Math.round(10 * sizeMultiplier),
        timeframe: 60,
        maxLoss: 5,
        riskTolerance: 'moderate',
        symbols: topHoldings.slice(0, 4),
        reasoning: 'Balanced risk-reward targeting steady growth across your top holdings'
      },
      {
        template: 'aggressive',
        name: 'Aggressive Growth Strategy',
        profitTarget: Math.round(15 * sizeMultiplier),
        timeframe: 30,
        maxLoss: 8,
        riskTolerance: 'high',
        symbols: topHoldings.slice(0, 5),
        reasoning: 'Higher risk for faster returns, suitable for active portfolio management'
      }
    ];
  }
}

module.exports = GoalSuggestionEngine;

