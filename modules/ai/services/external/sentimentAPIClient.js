/**
 * Sentiment API Client
 * Aggregates sentiment from social media (Twitter/Reddit)
 * Free tier: RapidAPI or mock data
 */

const axios = require('axios');

class SentimentAPIClient {
  constructor() {
    this.apiKey = process.env.RAPIDAPI_KEY || null;
    this.cache = new Map();
    this.cacheExpiryMs = 3600000; // 1 hour
  }

  /**
   * Fetch sentiment data for a stock
   * @param {string} symbol - Stock symbol
   * @param {number} lookbackDays - Days to look back
   * @returns {Object} Sentiment score and volume
   */
  async fetchSentiment(symbol, lookbackDays = 7) {
    const cacheKey = `${symbol}-${lookbackDays}`;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheExpiryMs) {
      console.log(`[SentimentAPIClient] Cache hit for ${symbol}`);
      return cached.data;
    }

    if (!this.apiKey) {
      console.warn('[SentimentAPIClient] No API key configured, using mock data');
      return this.getMockSentiment(symbol);
    }

    try {
      // In production, use RapidAPI or similar service
      // For now, return mock data
      const sentiment = this.getMockSentiment(symbol);
      
      this.cache.set(cacheKey, { data: sentiment, timestamp: Date.now() });
      console.log(`[SentimentAPIClient] Sentiment for ${symbol}: ${sentiment.score}`);

      return sentiment;
    } catch (error) {
      console.error(`[SentimentAPIClient] Error fetching sentiment for ${symbol}:`, error.message);
      return cached?.data || this.getMockSentiment(symbol);
    }
  }

  /**
   * Mock sentiment data
   */
  getMockSentiment(symbol) {
    // Generate semi-realistic mock data
    const baseScore = 0.5 + (Math.random() * 0.4 - 0.2); // 0.3 to 0.7
    const volume = Math.floor(Math.random() * 5000) + 500; // 500-5500 mentions
    
    return {
      score: parseFloat(baseScore.toFixed(2)), // 0-1 scale, 0.5 is neutral
      sentiment: baseScore > 0.6 ? 'bullish' : baseScore < 0.4 ? 'bearish' : 'neutral',
      volume: volume,
      sources: {
        twitter: Math.floor(volume * 0.6),
        reddit: Math.floor(volume * 0.3),
        news: Math.floor(volume * 0.1)
      },
      trending: baseScore > 0.65,
      momentum: Math.random() > 0.5 ? 'increasing' : 'stable'
    };
  }

  /**
   * Analyze sentiment trend over time
   * @param {string} symbol 
   * @returns {Array} Historical sentiment scores
   */
  async getSentimentTrend(symbol) {
    const trend = [];
    const days = 7;
    
    for (let i = 0; i < days; i++) {
      trend.push({
        date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
        score: 0.5 + (Math.random() * 0.3 - 0.15)
      });
    }
    
    return trend.reverse();
  }
}

module.exports = SentimentAPIClient;

