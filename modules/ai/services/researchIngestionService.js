/**
 * Research Ingestion Service
 * Orchestrates data collection from multiple sources
 * Stores in research_data table for AI consumption
 */

const db = require('../../../core/database/connection');
const NewsAPIClient = require('./external/newsAPIClient');
const SentimentAPIClient = require('./external/sentimentAPIClient');
const FundamentalsAPIClient = require('./external/fundamentalsAPIClient');
const MacroDataClient = require('./external/macroDataClient');

class ResearchIngestionService {
  constructor() {
    this.newsClient = new NewsAPIClient();
    this.sentimentClient = new SentimentAPIClient();
    this.fundamentalsClient = new FundamentalsAPIClient();
    this.macroClient = new MacroDataClient();
  }

  /**
   * Ingest daily research for all symbols
   * @param {Array} symbols - List of stock symbols
   * @returns {Object} Ingestion summary
   */
  async ingestDailyResearch(symbols) {
    console.log(`[ResearchIngestion] Starting daily ingestion for ${symbols.length} symbols`);
    
    const summary = {
      news: 0,
      sentiment: 0,
      fundamentals: 0,
      macro: 0,
      errors: []
    };

    try {
      // 1. Ingest Macro Data (once per day)
      await this.ingestMacroData();
      summary.macro = 1;

      // 2. Ingest stock-specific data
      for (const symbol of symbols) {
        try {
          // Fetch all data in parallel
          const [news, sentiment, fundamentals] = await Promise.all([
            this.newsClient.fetchNews(symbol, 7),
            this.sentimentClient.fetchSentiment(symbol, 7),
            this.fundamentalsClient.fetchFundamentals(symbol)
          ]);

          // Store news
          for (const article of news) {
            await this.storeResearchData({
              symbol,
              dataType: 'news',
              source: article.source,
              content: article.headline,
              metadata: {
                description: article.description,
                url: article.url,
                publishedAt: article.publishedAt,
                sentiment: article.sentiment
              },
              relevanceScore: 0.8
            });
            summary.news++;
          }

          // Store sentiment
          await this.storeResearchData({
            symbol,
            dataType: 'sentiment',
            source: 'social_media',
            content: JSON.stringify(sentiment),
            metadata: sentiment,
            relevanceScore: sentiment.score
          });
          summary.sentiment++;

          // Store fundamentals
          await this.storeResearchData({
            symbol,
            dataType: 'fundamentals',
            source: 'yahoo_finance',
            content: JSON.stringify(fundamentals),
            metadata: fundamentals,
            relevanceScore: 0.9
          });
          summary.fundamentals++;

          // Rate limiting: 500ms between symbols
          await new Promise(resolve => setTimeout(resolve, 500));

        } catch (error) {
          console.error(`[ResearchIngestion] Error for ${symbol}:`, error.message);
          summary.errors.push({ symbol, error: error.message });
        }
      }

      console.log(`[ResearchIngestion] Complete: ${JSON.stringify(summary)}`);
      return summary;

    } catch (error) {
      console.error('[ResearchIngestion] Fatal error:', error);
      throw error;
    }
  }

  /**
   * Get relevant research for a symbol
   * @param {string} symbol 
   * @param {number} lookbackDays 
   * @returns {Object} Aggregated research data
   */
  async getRelevantResearch(symbol, lookbackDays = 7) {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - lookbackDays);

      // Query database for recent research
      const query = `
        SELECT data_type, source, content, metadata, relevance_score, fetched_at
        FROM research_data
        WHERE symbol = $1 
          AND fetched_at >= $2
        ORDER BY fetched_at DESC
      `;

      const result = await db.query(query, [symbol, cutoffDate]);

      // Aggregate by type
      const research = {
        news: [],
        sentiment: null,
        fundamentals: null,
        lastUpdated: null
      };

      for (const row of result.rows) {
        switch (row.data_type) {
          case 'news':
            research.news.push({
              headline: row.content,
              ...row.metadata,
              source: row.source,
              fetchedAt: row.fetched_at
            });
            break;
          case 'sentiment':
            // Use most recent sentiment
            if (!research.sentiment || row.fetched_at > research.lastUpdated) {
              research.sentiment = row.metadata;
              research.lastUpdated = row.fetched_at;
            }
            break;
          case 'fundamentals':
            // Use most recent fundamentals
            if (!research.fundamentals || row.fetched_at > research.lastUpdated) {
              research.fundamentals = row.metadata;
              research.lastUpdated = row.fetched_at;
            }
            break;
        }
      }

      // If no data in DB, fetch fresh (first time or cache miss)
      if (research.news.length === 0 && !research.sentiment && !research.fundamentals) {
        console.log(`[ResearchIngestion] No cached data for ${symbol}, fetching fresh`);
        
        const [news, sentiment, fundamentals] = await Promise.all([
          this.newsClient.fetchNews(symbol, lookbackDays),
          this.sentimentClient.fetchSentiment(symbol, lookbackDays),
          this.fundamentalsClient.fetchFundamentals(symbol)
        ]);

        research.news = news;
        research.sentiment = sentiment;
        research.fundamentals = fundamentals;
      }

      return research;

    } catch (error) {
      console.error(`[ResearchIngestion] Error getting research for ${symbol}:`, error.message);
      // Fallback to fresh data
      const [news, sentiment, fundamentals] = await Promise.all([
        this.newsClient.fetchNews(symbol, lookbackDays),
        this.sentimentClient.fetchSentiment(symbol, lookbackDays),
        this.fundamentalsClient.fetchFundamentals(symbol)
      ]);

      return { news, sentiment, fundamentals };
    }
  }

  /**
   * Store research data in database
   */
  async storeResearchData({ symbol, dataType, source, content, metadata, relevanceScore }) {
    try {
      const query = `
        INSERT INTO research_data (symbol, data_type, source, content, metadata, relevance_score)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (symbol, data_type, source, fetched_at) 
        DO NOTHING
      `;

      await db.query(query, [
        symbol,
        dataType,
        source,
        content,
        JSON.stringify(metadata),
        relevanceScore
      ]);

    } catch (error) {
      // Ignore duplicate key errors
      if (!error.message.includes('duplicate') && !error.message.includes('conflict')) {
        console.error('[ResearchIngestion] Store error:', error.message);
      }
    }
  }

  /**
   * Ingest macro data
   */
  async ingestMacroData() {
    try {
      const macroData = await this.macroClient.fetchMacroIndicators();
      
      await this.storeResearchData({
        symbol: 'NIFTY50',
        dataType: 'macro',
        source: 'fred_rbi',
        content: JSON.stringify(macroData),
        metadata: macroData,
        relevanceScore: 1.0
      });

      console.log('[ResearchIngestion] Macro data ingested');
    } catch (error) {
      console.error('[ResearchIngestion] Macro ingestion error:', error.message);
    }
  }

  /**
   * Get macro context for market analysis
   */
  async getMacroContext() {
    try {
      const query = `
        SELECT metadata, fetched_at
        FROM research_data
        WHERE symbol = 'NIFTY50' AND data_type = 'macro'
        ORDER BY fetched_at DESC
        LIMIT 1
      `;

      const result = await db.query(query);
      
      if (result.rows.length > 0) {
        return result.rows[0].metadata;
      }

      // Fallback to fresh data
      return await this.macroClient.fetchMacroIndicators();

    } catch (error) {
      console.error('[ResearchIngestion] Error getting macro context:', error.message);
      return await this.macroClient.fetchMacroIndicators();
    }
  }

  /**
   * Clean old research data (>90 days)
   */
  async cleanupOldData() {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - 90);

      const query = `
        DELETE FROM research_data
        WHERE fetched_at < $1
      `;

      const result = await db.query(query, [cutoffDate]);
      console.log(`[ResearchIngestion] Cleaned ${result.rowCount} old records`);

      return result.rowCount;
    } catch (error) {
      console.error('[ResearchIngestion] Cleanup error:', error.message);
      return 0;
    }
  }
}

module.exports = ResearchIngestionService;

