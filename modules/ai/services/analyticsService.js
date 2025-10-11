/**
 * AI Analytics Service
 * Tracks AI usage metrics for monitoring and optimization
 */

const db = require('../../../core/database/connection');

class AIAnalyticsService {
  constructor() {
    this.db = db;
  }

  /**
   * Track stock selection mode (ai_selected vs user_provided)
   */
  async trackStockSelectionMode(userId, mode, metadata = {}) {
    try {
      await this.db.query(
        `INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
         VALUES ($1, 'stock_selection_mode', $2, $3, NOW())`,
        [userId, mode, JSON.stringify(metadata)]
      );
      
      console.log(`[AIAnalytics] Tracked stock selection: ${mode} for user: ${userId}`);
    } catch (error) {
      console.error('[AIAnalytics] Error tracking stock selection:', error);
      // Don't throw - analytics shouldn't break main flow
    }
  }

  /**
   * Track trading mode (manual vs auto)
   */
  async trackTradingMode(userId, mode) {
    try {
      await this.db.query(
        `INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, created_at)
         VALUES ($1, 'trading_mode', $2, NOW())`,
        [userId, mode]
      );
      
      console.log(`[AIAnalytics] Tracked trading mode: ${mode} for user: ${userId}`);
    } catch (error) {
      console.error('[AIAnalytics] Error tracking trading mode:', error);
    }
  }

  /**
   * Track portfolio action acceptance
   */
  async trackPortfolioActionAcceptance(userId, actionType, accepted, metadata = {}) {
    try {
      await this.db.query(
        `INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
         VALUES ($1, 'portfolio_action', $2, $3, NOW())`,
        [userId, accepted ? 'accepted' : 'rejected', JSON.stringify({ actionType, ...metadata })]
      );
      
      console.log(`[AIAnalytics] Tracked portfolio action: ${actionType} ${accepted ? 'accepted' : 'rejected'}`);
    } catch (error) {
      console.error('[AIAnalytics] Error tracking portfolio action:', error);
    }
  }

  /**
   * Track AI provider usage
   */
  async trackProviderUsage(userId, provider, taskType, metadata = {}) {
    try {
      await this.db.query(
        `INSERT INTO ai_usage_metrics (user_id, metric_type, metric_value, metadata, created_at)
         VALUES ($1, 'provider_usage', $2, $3, NOW())`,
        [userId, provider, JSON.stringify({ taskType, ...metadata })]
      );
      
      console.log(`[AIAnalytics] Tracked provider usage: ${provider} for ${taskType}`);
    } catch (error) {
      console.error('[AIAnalytics] Error tracking provider usage:', error);
    }
  }

  /**
   * Get aggregated usage statistics
   * @param {string} userId - Optional user ID (null for system-wide stats)
   * @param {number} dateRange - Days to look back (default 30)
   */
  async getUsageStats(userId = null, dateRange = 30) {
    try {
      const stats = await this.db.query(`
        SELECT 
          metric_type,
          metric_value,
          COUNT(*) as count,
          DATE(created_at) as date
        FROM ai_usage_metrics
        WHERE ($1::TEXT IS NULL OR user_id = $1)
          AND created_at >= NOW() - INTERVAL '${parseInt(dateRange)} days'
        GROUP BY metric_type, metric_value, DATE(created_at)
        ORDER BY date DESC, metric_type, metric_value
      `, [userId]);

      return this.formatStats(stats.rows);
    } catch (error) {
      console.error('[AIAnalytics] Error getting usage stats:', error);
      return {
        stock_selection: {},
        trading_mode: {},
        portfolio_actions: {},
        provider_usage: {}
      };
    }
  }

  /**
   * Format raw stats into organized structure
   */
  formatStats(rows) {
    const formatted = {
      stock_selection: { ai_selected: 0, user_provided: 0 },
      trading_mode: { manual: 0, auto: 0 },
      portfolio_actions: { accepted: 0, rejected: 0 },
      provider_usage: { openai: 0, claude: 0, mistral: 0 },
      byDate: {}
    };

    for (const row of rows) {
      const { metric_type, metric_value, count, date } = row;
      
      switch(metric_type) {
        case 'stock_selection_mode':
          formatted.stock_selection[metric_value] = (formatted.stock_selection[metric_value] || 0) + parseInt(count);
          break;
        case 'trading_mode':
          formatted.trading_mode[metric_value] = (formatted.trading_mode[metric_value] || 0) + parseInt(count);
          break;
        case 'portfolio_action':
          formatted.portfolio_actions[metric_value] = (formatted.portfolio_actions[metric_value] || 0) + parseInt(count);
          break;
        case 'provider_usage':
          formatted.provider_usage[metric_value] = (formatted.provider_usage[metric_value] || 0) + parseInt(count);
          break;
      }
      
      // Track by date
      if (!formatted.byDate[date]) {
        formatted.byDate[date] = {};
      }
      formatted.byDate[date][metric_type] = formatted.byDate[date][metric_type] || {};
      formatted.byDate[date][metric_type][metric_value] = parseInt(count);
    }

    // Calculate percentages
    const totalStockSelections = formatted.stock_selection.ai_selected + formatted.stock_selection.user_provided;
    const totalActions = formatted.portfolio_actions.accepted + formatted.portfolio_actions.rejected;
    
    formatted.percentages = {
      ai_stock_selection: totalStockSelections > 0 
        ? ((formatted.stock_selection.ai_selected / totalStockSelections) * 100).toFixed(1) + '%'
        : 'N/A',
      manual_mode: formatted.trading_mode.manual + formatted.trading_mode.auto > 0
        ? ((formatted.trading_mode.manual / (formatted.trading_mode.manual + formatted.trading_mode.auto)) * 100).toFixed(1) + '%'
        : 'N/A',
      action_approval_rate: totalActions > 0
        ? ((formatted.portfolio_actions.accepted / totalActions) * 100).toFixed(1) + '%'
        : 'N/A'
    };

    return formatted;
  }

  /**
   * Get metrics summary for dashboard
   */
  async getDashboardMetrics(userId) {
    const stats = await this.getUsageStats(userId, 30);
    
    return {
      ai_stock_selections: stats.percentages.ai_stock_selection,
      manual_mode_usage: stats.percentages.manual_mode,
      action_approval_rate: stats.percentages.action_approval_rate,
      total_strategies: stats.stock_selection.ai_selected + stats.stock_selection.user_provided,
      most_used_provider: this.getMostUsedProvider(stats.provider_usage)
    };
  }

  /**
   * Get most used provider
   */
  getMostUsedProvider(providerStats) {
    const providers = Object.entries(providerStats);
    if (providers.length === 0) return 'None';
    
    const sorted = providers.sort((a, b) => b[1] - a[1]);
    return sorted[0][0];
  }
}

// Export singleton
let instance = null;

const getAIAnalyticsService = () => {
  if (!instance) {
    instance = new AIAnalyticsService();
  }
  return instance;
};

module.exports = getAIAnalyticsService;

