/**
 * Market Universe Service
 * Manages top liquid stocks for AI-driven stock selection
 * Caches market data and provides filtered universe for AI analysis
 */

const db = require('../../../core/database/connection');

class MarketUniverseService {
  constructor() {
    this.db = db;
    this.cachedUniverse = null;
    this.cacheExpiry = null;
    this.cacheDurationMs = 24 * 60 * 60 * 1000; // 24 hours
    
    // Top 100 liquid NSE stocks (hardcoded for initial implementation)
    // In production, this should be fetched from market data API
    this.topLiquidStocks = [
      { symbol: 'RELIANCE', sector: 'Energy', marketCap: 'large', avgVolume: 10000000 },
      { symbol: 'TCS', sector: 'IT', marketCap: 'large', avgVolume: 5000000 },
      { symbol: 'HDFCBANK', sector: 'Banking', marketCap: 'large', avgVolume: 8000000 },
      { symbol: 'INFY', sector: 'IT', marketCap: 'large', avgVolume: 6000000 },
      { symbol: 'ICICIBANK', sector: 'Banking', marketCap: 'large', avgVolume: 7000000 },
      { symbol: 'HINDUNILVR', sector: 'FMCG', marketCap: 'large', avgVolume: 2000000 },
      { symbol: 'ITC', sector: 'FMCG', marketCap: 'large', avgVolume: 9000000 },
      { symbol: 'SBIN', sector: 'Banking', marketCap: 'large', avgVolume: 15000000 },
      { symbol: 'BHARTIARTL', sector: 'Telecom', marketCap: 'large', avgVolume: 8000000 },
      { symbol: 'KOTAKBANK', sector: 'Banking', marketCap: 'large', avgVolume: 4000000 },
      { symbol: 'LT', sector: 'Infrastructure', marketCap: 'large', avgVolume: 3000000 },
      { symbol: 'AXISBANK', sector: 'Banking', marketCap: 'large', avgVolume: 6000000 },
      { symbol: 'ASIANPAINT', sector: 'Paint', marketCap: 'large', avgVolume: 1500000 },
      { symbol: 'MARUTI', sector: 'Auto', marketCap: 'large', avgVolume: 2500000 },
      { symbol: 'SUNPHARMA', sector: 'Pharma', marketCap: 'large', avgVolume: 3500000 },
      { symbol: 'TITAN', sector: 'Consumer', marketCap: 'large', avgVolume: 2000000 },
      { symbol: 'BAJFINANCE', sector: 'NBFC', marketCap: 'large', avgVolume: 2500000 },
      { symbol: 'NESTLEIND', sector: 'FMCG', marketCap: 'large', avgVolume: 500000 },
      { symbol: 'HCLTECH', sector: 'IT', marketCap: 'large', avgVolume: 3000000 },
      { symbol: 'WIPRO', sector: 'IT', marketCap: 'large', avgVolume: 5000000 },
      { symbol: 'ULTRACEMCO', sector: 'Cement', marketCap: 'large', avgVolume: 1000000 },
      { symbol: 'ADANIENT', sector: 'Diversified', marketCap: 'large', avgVolume: 8000000 },
      { symbol: 'TATAMOTORS', sector: 'Auto', marketCap: 'large', avgVolume: 12000000 },
      { symbol: 'ONGC', sector: 'Energy', marketCap: 'large', avgVolume: 10000000 },
      { symbol: 'NTPC', sector: 'Power', marketCap: 'large', avgVolume: 8000000 },
      { symbol: 'POWERGRID', sector: 'Power', marketCap: 'large', avgVolume: 5000000 },
      { symbol: 'M&M', sector: 'Auto', marketCap: 'large', avgVolume: 3000000 },
      { symbol: 'BAJAJFINSV', sector: 'NBFC', marketCap: 'large', avgVolume: 1500000 },
      { symbol: 'TECHM', sector: 'IT', marketCap: 'large', avgVolume: 2500000 },
      { symbol: 'DRREDDY', sector: 'Pharma', marketCap: 'large', avgVolume: 1000000 }
      // ... Add remaining 70 stocks
    ];
  }

  /**
   * Get top N liquid stocks
   * @param {number} limit - Number of stocks to return
   * @param {Object} filters - Optional filters (sector, marketCap, minVolume)
   * @returns {Array} List of stocks
   */
  async getTopLiquid(limit = 100, filters = {}) {
    try {
      let universe = this.topLiquidStocks;

      // Apply filters
      if (filters.sector) {
        universe = universe.filter(s => s.sector === filters.sector);
      }
      
      if (filters.marketCap) {
        universe = universe.filter(s => s.marketCap === filters.marketCap);
      }
      
      if (filters.minVolume) {
        universe = universe.filter(s => s.avgVolume >= filters.minVolume);
      }

      // Sort by average volume (liquidity proxy) and take top N
      const sorted = universe
        .sort((a, b) => b.avgVolume - a.avgVolume)
        .slice(0, limit);

      console.log(`[MarketUniverse] Returning ${sorted.length} stocks (limit: ${limit})`);
      
      return sorted;
    } catch (error) {
      console.error('[MarketUniverse] Error getting top liquid stocks:', error);
      throw error;
    }
  }

  /**
   * Get combined universe: top liquid + user's current holdings
   * @param {Object} portfolioData - User's current portfolio
   * @param {number} topN - Number of top liquid stocks to include
   * @returns {Array} Combined universe
   */
  async getCombinedUniverse(portfolioData, topN = 100) {
    const topLiquid = await this.getTopLiquid(topN);
    const holdings = portfolioData?.holdings || [];
    
    // Extract symbols from holdings
    const holdingSymbols = holdings.map(h => h.symbol || h.tradingsymbol);
    
    // Combine top liquid with holdings (avoid duplicates)
    const topLiquidSymbols = topLiquid.map(s => s.symbol);
    const uniqueHoldings = holdings.filter(h => 
      !topLiquidSymbols.includes(h.symbol || h.tradingsymbol)
    );
    
    const combined = [
      ...topLiquid,
      ...uniqueHoldings.map(h => ({
        symbol: h.symbol || h.tradingsymbol,
        sector: 'User Holding',
        marketCap: 'unknown',
        avgVolume: 0,
        isUserHolding: true
      }))
    ];

    console.log(`[MarketUniverse] Combined universe: ${topLiquid.length} liquid + ${uniqueHoldings.length} holdings = ${combined.length} total`);
    
    return combined;
  }

  /**
   * Filter stocks by sector diversification
   * Ensures no single sector dominates the selection
   */
  filterForDiversification(stocks, maxPerSector = 2) {
    const sectorCounts = {};
    const diversified = [];

    for (const stock of stocks) {
      const sector = stock.sector;
      const count = sectorCounts[sector] || 0;
      
      if (count < maxPerSector) {
        diversified.push(stock);
        sectorCounts[sector] = count + 1;
      }
    }

    return diversified;
  }

  /**
   * Get stocks by sector
   */
  async getStocksBySector(sector, limit = 10) {
    const universe = await this.getTopLiquid(100);
    return universe
      .filter(s => s.sector === sector)
      .slice(0, limit);
  }

  /**
   * Get available sectors
   */
  getAvailableSectors() {
    const sectors = [...new Set(this.topLiquidStocks.map(s => s.sector))];
    return sectors.sort();
  }

  /**
   * Search stocks by name or symbol
   */
  searchStocks(query, limit = 10) {
    const queryUpper = query.toUpperCase();
    return this.topLiquidStocks
      .filter(s => 
        s.symbol.toUpperCase().includes(queryUpper) ||
        s.sector.toUpperCase().includes(queryUpper)
      )
      .slice(0, limit);
  }

  /**
   * Get stock info by symbol
   */
  getStockInfo(symbol) {
    return this.topLiquidStocks.find(s => s.symbol === symbol.toUpperCase());
  }

  /**
   * Validate if stocks are in tradable universe
   */
  validateStocks(symbols) {
    const valid = [];
    const invalid = [];
    
    for (const symbol of symbols) {
      const info = this.getStockInfo(symbol);
      if (info) {
        valid.push(symbol);
      } else {
        invalid.push(symbol);
      }
    }
    
    return { valid, invalid };
  }
}

// Export singleton instance
let instance = null;

const getMarketUniverse = () => {
  if (!instance) {
    instance = new MarketUniverseService();
  }
  return instance;
};

module.exports = getMarketUniverse;

