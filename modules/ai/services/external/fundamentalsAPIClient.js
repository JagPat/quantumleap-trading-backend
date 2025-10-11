/**
 * Fundamentals API Client
 * Fetches fundamental data from Yahoo Finance
 * Free tier with rate limiting
 */

const axios = require('axios');

class FundamentalsAPIClient {
  constructor() {
    this.cache = new Map();
    this.cacheExpiryMs = 86400000; // 24 hours (fundamentals change slowly)
    this.yahooFinanceAPI = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary';
  }

  /**
   * Fetch fundamental data for a stock
   * @param {string} symbol - Stock symbol
   * @returns {Object} Fundamental metrics
   */
  async fetchFundamentals(symbol) {
    const cacheKey = symbol;
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheExpiryMs) {
      console.log(`[FundamentalsAPIClient] Cache hit for ${symbol}`);
      return cached.data;
    }

    try {
      // Convert NSE symbol to Yahoo Finance format (e.g., RELIANCE -> RELIANCE.NS)
      const yahooSymbol = `${symbol}.NS`;
      
      const response = await axios.get(this.yahooFinanceAPI + `/${yahooSymbol}`, {
        params: {
          modules: 'defaultKeyStatistics,financialData,earningsTrend'
        },
        timeout: 5000
      });

      const data = response.data?.quoteSummary?.result?.[0];
      
      if (!data) {
        console.warn(`[FundamentalsAPIClient] No data for ${symbol}, using mock`);
        return this.getMockFundamentals(symbol);
      }

      const fundamentals = {
        pe: data.defaultKeyStatistics?.trailingPE?.raw || null,
        pb: data.defaultKeyStatistics?.priceToBook?.raw || null,
        roe: data.financialData?.returnOnEquity?.raw 
          ? (data.financialData.returnOnEquity.raw * 100).toFixed(2) 
          : null,
        debtToEquity: data.financialData?.debtToEquity?.raw || null,
        marketCap: data.defaultKeyStatistics?.marketCap?.raw || null,
        earningsGrowth: data.earningsTrend?.trend?.[0]?.growth?.raw 
          ? (data.earningsTrend.trend[0].growth.raw * 100).toFixed(2)
          : null,
        revenueGrowth: data.financialData?.revenueGrowth?.raw
          ? (data.financialData.revenueGrowth.raw * 100).toFixed(2)
          : null,
        profitMargin: data.financialData?.profitMargins?.raw
          ? (data.financialData.profitMargins.raw * 100).toFixed(2)
          : null,
        currentPrice: data.financialData?.currentPrice?.raw || null,
        targetPrice: data.financialData?.targetMeanPrice?.raw || null,
        trend: this.determineTrend(data)
      };

      this.cache.set(cacheKey, { data: fundamentals, timestamp: Date.now() });
      console.log(`[FundamentalsAPIClient] Fetched fundamentals for ${symbol}`);

      return fundamentals;
    } catch (error) {
      console.error(`[FundamentalsAPIClient] Error fetching fundamentals for ${symbol}:`, error.message);
      return cached?.data || this.getMockFundamentals(symbol);
    }
  }

  /**
   * Determine fundamental trend
   */
  determineTrend(data) {
    const earningsGrowth = data.earningsTrend?.trend?.[0]?.growth?.raw || 0;
    const revenueGrowth = data.financialData?.revenueGrowth?.raw || 0;
    
    const avgGrowth = (earningsGrowth + revenueGrowth) / 2;
    
    if (avgGrowth > 0.1) return 'improving';
    if (avgGrowth < -0.05) return 'deteriorating';
    return 'stable';
  }

  /**
   * Mock fundamentals for testing/fallback
   */
  getMockFundamentals(symbol) {
    // Generate semi-realistic mock data
    const basePE = 20 + Math.random() * 30; // 20-50
    const baseROE = 10 + Math.random() * 20; // 10-30%
    
    return {
      pe: parseFloat(basePE.toFixed(2)),
      pb: parseFloat((basePE / 3).toFixed(2)),
      roe: parseFloat(baseROE.toFixed(2)),
      debtToEquity: parseFloat((Math.random() * 1.5).toFixed(2)),
      marketCap: Math.floor(Math.random() * 500000) + 50000, // Cr
      earningsGrowth: parseFloat((Math.random() * 30 - 10).toFixed(2)), // -10% to 20%
      revenueGrowth: parseFloat((Math.random() * 25 - 5).toFixed(2)), // -5% to 20%
      profitMargin: parseFloat((10 + Math.random() * 15).toFixed(2)), // 10-25%
      currentPrice: parseFloat((1000 + Math.random() * 2000).toFixed(2)),
      targetPrice: parseFloat((1100 + Math.random() * 2100).toFixed(2)),
      trend: Math.random() > 0.6 ? 'improving' : Math.random() > 0.3 ? 'stable' : 'deteriorating'
    };
  }

  /**
   * Batch fetch for multiple symbols
   */
  async fetchBatch(symbols) {
    const results = {};
    
    for (const symbol of symbols) {
      results[symbol] = await this.fetchFundamentals(symbol);
      // Rate limiting: 1 request per second
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    return results;
  }
}

module.exports = FundamentalsAPIClient;

