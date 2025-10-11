/**
 * News API Client
 * Free tier: NewsAPI.org (100 requests/day)
 * 
 * Fetches financial news for Indian stocks
 */

const axios = require('axios');

class NewsAPIClient {
  constructor() {
    this.apiKey = process.env.NEWSAPI_KEY || null;
    this.baseURL = 'https://newsapi.org/v2';
    this.cache = new Map();
    this.cacheExpiryMs = 3600000; // 1 hour
    this.requestCount = 0;
    this.dailyLimit = 100;
  }

  /**
   * Fetch news for a stock symbol
   * @param {string} symbol - Stock symbol (e.g., 'RELIANCE')
   * @param {number} lookbackDays - Days to look back
   * @returns {Array} News articles
   */
  async fetchNews(symbol, lookbackDays = 7) {
    if (!this.apiKey) {
      console.warn('[NewsAPIClient] No API key configured, using mock data');
      return this.getMockNews(symbol);
    }

    const cacheKey = `${symbol}-${lookbackDays}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheExpiryMs) {
      console.log(`[NewsAPIClient] Cache hit for ${symbol}`);
      return cached.data;
    }

    if (this.requestCount >= this.dailyLimit) {
      console.warn('[NewsAPIClient] Daily limit reached, using cached/mock data');
      return cached?.data || this.getMockNews(symbol);
    }

    try {
      const fromDate = new Date();
      fromDate.setDate(fromDate.getDate() - lookbackDays);

      const response = await axios.get(`${this.baseURL}/everything`, {
        params: {
          q: `${symbol} AND (NSE OR BSE OR India OR Mumbai)`,
          from: fromDate.toISOString().split('T')[0],
          language: 'en',
          sortBy: 'relevancy',
          pageSize: 10,
          apiKey: this.apiKey
        },
        timeout: 5000
      });

      this.requestCount++;

      const articles = response.data.articles.map(article => ({
        headline: article.title,
        description: article.description,
        source: article.source.name,
        url: article.url,
        publishedAt: article.publishedAt,
        sentiment: this.estimateSentiment(article.title + ' ' + article.description)
      }));

      this.cache.set(cacheKey, { data: articles, timestamp: Date.now() });
      console.log(`[NewsAPIClient] Fetched ${articles.length} articles for ${symbol}`);

      return articles;
    } catch (error) {
      console.error(`[NewsAPIClient] Error fetching news for ${symbol}:`, error.message);
      return cached?.data || this.getMockNews(symbol);
    }
  }

  /**
   * Estimate sentiment from text (simple keyword-based)
   * @param {string} text 
   * @returns {string} 'positive', 'negative', or 'neutral'
   */
  estimateSentiment(text) {
    if (!text) return 'neutral';
    
    const lowerText = text.toLowerCase();
    const positiveWords = ['surge', 'rally', 'gain', 'profit', 'growth', 'beat', 'upgrade', 'strong', 'success', 'high'];
    const negativeWords = ['fall', 'drop', 'loss', 'decline', 'cut', 'downgrade', 'weak', 'fail', 'low', 'concern'];
    
    const positiveCount = positiveWords.filter(word => lowerText.includes(word)).length;
    const negativeCount = negativeWords.filter(word => lowerText.includes(word)).length;
    
    if (positiveCount > negativeCount) return 'positive';
    if (negativeCount > positiveCount) return 'negative';
    return 'neutral';
  }

  /**
   * Mock news for testing/fallback
   */
  getMockNews(symbol) {
    return [
      {
        headline: `${symbol} reports strong Q2 earnings`,
        description: 'Company exceeds market expectations with robust performance',
        source: 'Economic Times',
        url: '#',
        publishedAt: new Date().toISOString(),
        sentiment: 'positive'
      },
      {
        headline: `Analysts upgrade ${symbol} to Buy`,
        description: 'Brokerage firms revise target price upward citing growth prospects',
        source: 'Moneycontrol',
        url: '#',
        publishedAt: new Date(Date.now() - 86400000).toISOString(),
        sentiment: 'positive'
      }
    ];
  }

  /**
   * Reset daily request counter (call at midnight)
   */
  resetDailyCounter() {
    this.requestCount = 0;
  }
}

module.exports = NewsAPIClient;

