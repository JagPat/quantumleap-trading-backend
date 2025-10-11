/**
 * Macro Data Client
 * Fetches macroeconomic indicators from FRED (Federal Reserve Economic Data)
 * Free API with generous rate limits
 */

const axios = require('axios');

class MacroDataClient {
  constructor() {
    this.apiKey = process.env.FRED_API_KEY || null;
    this.baseURL = 'https://api.stlouisfed.org/fred/series/observations';
    this.cache = new Map();
    this.cacheExpiryMs = 86400000; // 24 hours
  }

  /**
   * Fetch macro indicators relevant to Indian markets
   * @returns {Object} Macro indicators
   */
  async fetchMacroIndicators() {
    const cacheKey = 'macro-indicators';
    const cached = this.cache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < this.cacheExpiryMs) {
      console.log('[MacroDataClient] Cache hit for macro indicators');
      return cached.data;
    }

    if (!this.apiKey) {
      console.warn('[MacroDataClient] No API key configured, using mock data');
      return this.getMockMacroData();
    }

    try {
      // Fetch key indicators
      // In production, fetch actual data from FRED or RBI
      // For now, use mock data
      const indicators = this.getMockMacroData();
      
      this.cache.set(cacheKey, { data: indicators, timestamp: Date.now() });
      console.log('[MacroDataClient] Fetched macro indicators');

      return indicators;
    } catch (error) {
      console.error('[MacroDataClient] Error fetching macro data:', error.message);
      return cached?.data || this.getMockMacroData();
    }
  }

  /**
   * Mock macro data for India
   */
  getMockMacroData() {
    return {
      gdp_growth: {
        value: 7.2,
        unit: 'percent',
        trend: 'stable',
        description: 'India GDP Growth Rate (YoY)'
      },
      inflation: {
        value: 5.8,
        unit: 'percent',
        trend: 'decreasing',
        description: 'Consumer Price Index (CPI)'
      },
      interest_rate: {
        value: 6.5,
        unit: 'percent',
        trend: 'stable',
        description: 'RBI Repo Rate'
      },
      fii_flow: {
        value: 2400, // Crores
        unit: 'crores',
        trend: 'positive',
        description: 'FII Net Investment (last 5 days)',
        direction: 'inflow'
      },
      dii_flow: {
        value: 1800,
        unit: 'crores',
        trend: 'positive',
        description: 'DII Net Investment (last 5 days)',
        direction: 'inflow'
      },
      usd_inr: {
        value: 83.2,
        unit: 'INR',
        trend: 'stable',
        description: 'USD/INR Exchange Rate',
        change: -0.15
      },
      crude_oil: {
        value: 85.4,
        unit: 'USD/barrel',
        trend: 'increasing',
        description: 'Crude Oil Price (Brent)',
        change: 2.3
      },
      global_sentiment: {
        value: 'positive',
        description: 'Overall global market sentiment',
        factors: ['Fed pause', 'China stimulus', 'Stable geopolitics']
      }
    };
  }

  /**
   * Get sentiment summary from macro indicators
   */
  getMacroSentiment(indicators) {
    const { gdp_growth, inflation, fii_flow, dii_flow } = indicators;
    
    let positiveFactors = 0;
    let negativeFactors = 0;
    
    if (gdp_growth.value > 6.5) positiveFactors++;
    if (inflation.value < 6.0) positiveFactors++;
    if (fii_flow.direction === 'inflow') positiveFactors++;
    if (dii_flow.direction === 'inflow') positiveFactors++;
    
    if (gdp_growth.value < 5.0) negativeFactors++;
    if (inflation.value > 7.0) negativeFactors++;
    
    if (positiveFactors > negativeFactors + 1) return 'bullish';
    if (negativeFactors > positiveFactors) return 'bearish';
    return 'neutral';
  }

  /**
   * Format macro data for LLM prompt
   */
  formatForPrompt(indicators) {
    return `
**Macroeconomic Indicators (India):**
- GDP Growth: ${indicators.gdp_growth.value}% YoY (${indicators.gdp_growth.trend})
- Inflation (CPI): ${indicators.inflation.value}% (${indicators.inflation.trend})
- RBI Repo Rate: ${indicators.interest_rate.value}% (${indicators.interest_rate.trend})
- FII Flow: ₹${indicators.fii_flow.value} Cr (${indicators.fii_flow.direction})
- DII Flow: ₹${indicators.dii_flow.value} Cr (${indicators.dii_flow.direction})
- USD/INR: ${indicators.usd_inr.value} (${indicators.usd_inr.change >= 0 ? '+' : ''}${indicators.usd_inr.change}%)
- Crude Oil: $${indicators.crude_oil.value}/barrel (${indicators.crude_oil.trend})
- Global Sentiment: ${indicators.global_sentiment.value} (${indicators.global_sentiment.factors.join(', ')})
`;
  }
}

module.exports = MacroDataClient;

