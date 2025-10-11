/**
 * Research Aggregator Service
 * Aggregates research from multiple sources and provides LLM summarization
 */

const { getAIAgentRouter } = require('../../ai/services/aiAgentRouter');
const { query } = require('../../../core/database');

class ResearchAggregator {
  constructor() {
    this.cacheTimeout = 3600000; // 1 hour cache
    this.aiRouter = null;
  }

  async initialize() {
    if (!this.aiRouter) {
      this.aiRouter = getAIAgentRouter();
    }
  }

  /**
   * Get comprehensive research for a symbol
   */
  async getComprehensiveResearch(symbol, days = 7) {
    try {
      await this.initialize();

      console.log('[ResearchAggregator] Fetching comprehensive research for', symbol);

      // Check cache first
      const cached = await this.getCachedResearch(symbol, 'comprehensive');
      if (cached) {
        console.log('[ResearchAggregator] Returning cached research');
        return cached;
      }

      // Fetch from multiple sources
      const [news, fundamentals, technical, sentiment] = await Promise.allSettled([
        this.fetchNews(symbol, days),
        this.fetchFundamentals(symbol),
        this.analyzeTechnicals(symbol),
        this.analyzeSentiment(symbol),
      ]);

      const researchData = {
        symbol,
        news: news.status === 'fulfilled' ? news.value : [],
        fundamentals: fundamentals.status === 'fulfilled' ? fundamentals.value : {},
        technical: technical.status === 'fulfilled' ? technical.value : {},
        sentiment: sentiment.status === 'fulfilled' ? sentiment.value : { score: 0.5, label: 'Neutral' },
        timestamp: new Date().toISOString(),
      };

      // Generate LLM summary
      const summary = await this.generateSummary(researchData);
      researchData.summary = summary;
      researchData.confidence = this.calculateConfidence(researchData);

      // Cache result
      await this.cacheResearch(symbol, 'comprehensive', researchData);

      return researchData;

    } catch (error) {
      console.error('[ResearchAggregator] Error:', error);
      throw error;
    }
  }

  /**
   * Fetch news headlines for a symbol
   */
  async fetchNews(symbol, days = 7) {
    try {
      // In production, integrate with NewsAPI, Benzinga, etc.
      // For MVP, return structured mock data
      
      const mockNews = [
        {
          title: `${symbol}: Strong quarterly results announced`,
          source: 'Economic Times',
          published: new Date(Date.now() - 86400000).toISOString(),
          sentiment: 'positive',
          relevance: 0.9,
        },
        {
          title: `${symbol} sees increased institutional interest`,
          source: 'Moneycontrol',
          published: new Date(Date.now() - 172800000).toISOString(),
          sentiment: 'positive',
          relevance: 0.8,
        },
        {
          title: `Market outlook positive for ${symbol} sector`,
          source: 'Bloomberg',
          published: new Date(Date.now() - 259200000).toISOString(),
          sentiment: 'positive',
          relevance: 0.7,
        },
      ];

      console.log(`[ResearchAggregator] Fetched ${mockNews.length} news items for ${symbol}`);
      return mockNews;

    } catch (error) {
      console.error('[ResearchAggregator] News fetch error:', error);
      return [];
    }
  }

  /**
   * Fetch fundamental data
   */
  async fetchFundamentals(symbol) {
    try {
      // In production, integrate with financial data API
      // For MVP, return structured mock data
      
      const mockFundamentals = {
        pe_ratio: 25.5,
        market_cap: '₹50,000 Cr',
        roe: 18.5,
        debt_to_equity: 0.45,
        revenue_growth: 15.2,
        profit_margin: 12.8,
        dividend_yield: 1.5,
        rating: 'Buy',
        target_price: null,
      };

      console.log(`[ResearchAggregator] Fetched fundamentals for ${symbol}`);
      return mockFundamentals;

    } catch (error) {
      console.error('[ResearchAggregator] Fundamentals fetch error:', error);
      return {};
    }
  }

  /**
   * Analyze technical indicators
   */
  async analyzeTechnicals(symbol) {
    try {
      // In production, integrate with technical analysis library
      // For MVP, return structured mock data
      
      const mockTechnical = {
        trend: 'Bullish',
        rsi: 58,
        macd: 'Positive',
        support: null,
        resistance: null,
        recommendation: 'Buy',
      };

      console.log(`[ResearchAggregator] Analyzed technicals for ${symbol}`);
      return mockTechnical;

    } catch (error) {
      console.error('[ResearchAggregator] Technical analysis error:', error);
      return {};
    }
  }

  /**
   * Analyze sentiment from news and social media
   */
  async analyzeSentiment(symbol) {
    try {
      // In production, use sentiment analysis API or LLM
      // For MVP, return mock sentiment
      
      const mockSentiment = {
        score: 0.68, // 0-1 scale (0 = bearish, 1 = bullish)
        label: 'Bullish',
        confidence: 0.75,
        sources: 3,
      };

      console.log(`[ResearchAggregator] Analyzed sentiment for ${symbol}: ${mockSentiment.label}`);
      return mockSentiment;

    } catch (error) {
      console.error('[ResearchAggregator] Sentiment analysis error:', error);
      return { score: 0.5, label: 'Neutral', confidence: 0.5 };
    }
  }

  /**
   * Generate LLM summary of research
   */
  async generateSummary(researchData) {
    try {
      const { symbol, news, fundamentals, technical, sentiment } = researchData;

      // Build prompt for LLM
      const prompt = `
Summarize the following research data for ${symbol} in 2-3 concise sentences:

News Headlines:
${news.slice(0, 3).map(n => `- ${n.title}`).join('\n')}

Fundamentals:
- P/E Ratio: ${fundamentals.pe_ratio}
- ROE: ${fundamentals.roe}%
- Revenue Growth: ${fundamentals.revenue_growth}%

Technical:
- Trend: ${technical.trend}
- RSI: ${technical.rsi}
- Recommendation: ${technical.recommendation}

Sentiment: ${sentiment.label} (${(sentiment.score * 100).toFixed(0)}% confidence)

Provide a concise investment outlook.
`;

      const response = await this.aiRouter.routeRequest({
        type: 'market_analysis',
        task: 'summarize_research',
        prompt,
        maxTokens: 150,
      }, 'system');

      return response.content || 'Research summary unavailable';

    } catch (error) {
      console.error('[ResearchAggregator] Summary generation error:', error);
      return 'Research data collected but summary generation failed';
    }
  }

  /**
   * Calculate overall confidence score
   */
  calculateConfidence(researchData) {
    try {
      const { news, fundamentals, technical, sentiment } = researchData;

      let confidence = 0.5; // Base confidence

      // Boost confidence based on data quality
      if (news && news.length >= 3) confidence += 0.1;
      if (fundamentals && Object.keys(fundamentals).length > 5) confidence += 0.1;
      if (technical && technical.trend) confidence += 0.1;
      if (sentiment && sentiment.confidence > 0.7) confidence += 0.2;

      return Math.min(confidence, 1.0);

    } catch (error) {
      return 0.5;
    }
  }

  /**
   * Cache research data
   */
  async cacheResearch(symbol, researchType, data) {
    try {
      const expiresAt = new Date(Date.now() + this.cacheTimeout);

      await query(
        `INSERT INTO research_cache 
         (symbol, research_type, data, confidence, expires_at, created_at)
         VALUES ($1, $2, $3, $4, $5, NOW())`,
        [symbol, researchType, JSON.stringify(data), data.confidence || 0.5, expiresAt]
      );

      console.log(`[ResearchAggregator] Cached research for ${symbol}`);

    } catch (error) {
      // Non-critical - log but don't fail
      console.warn('[ResearchAggregator] Cache error:', error.message);
    }
  }

  /**
   * Get cached research if available
   */
  async getCachedResearch(symbol, researchType) {
    try {
      const result = await query(
        `SELECT data FROM research_cache 
         WHERE symbol = $1 AND research_type = $2 
         AND expires_at > NOW()
         ORDER BY created_at DESC LIMIT 1`,
        [symbol, researchType]
      );

      if (result.rows.length > 0) {
        return result.rows[0].data;
      }

      return null;

    } catch (error) {
      console.warn('[ResearchAggregator] Cache retrieval error:', error.message);
      return null;
    }
  }

  /**
   * Get summary only (fast endpoint)
   */
  async getSummaryOnly(symbol) {
    try {
      // Check cache first
      const cached = await this.getCachedResearch(symbol, 'summary');
      if (cached) {
        return cached;
      }

      // Generate new summary
      const research = await this.getComprehensiveResearch(symbol);
      const summary = {
        symbol,
        summary: research.summary,
        sentiment: research.sentiment,
        confidence: research.confidence,
        timestamp: research.timestamp,
      };

      // Cache summary separately
      await this.cacheResearch(symbol, 'summary', summary);

      return summary;

    } catch (error) {
      console.error('[ResearchAggregator] Summary error:', error);
      throw error;
    }
  }

  /**
   * Clear expired cache entries
   */
  async clearExpiredCache() {
    try {
      await query(`DELETE FROM research_cache WHERE expires_at < NOW()`);
      console.log('[ResearchAggregator] Cleared expired cache entries');
    } catch (error) {
      console.warn('[ResearchAggregator] Cache cleanup error:', error.message);
    }
  }
}

// Singleton instance
let researchAggregatorInstance = null;

function getResearchAggregator() {
  if (!researchAggregatorInstance) {
    researchAggregatorInstance = new ResearchAggregator();
  }
  return researchAggregatorInstance;
}

module.exports = {
  ResearchAggregator,
  getResearchAggregator,
};

