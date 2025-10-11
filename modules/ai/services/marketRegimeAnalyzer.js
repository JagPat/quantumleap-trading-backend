/**
 * Market Regime Analyzer
 * Uses LLM to detect current market regime based on indicators + news
 * Regimes: BULL, BEAR, VOLATILE, CONSOLIDATION
 */

const db = require('../../../core/database/connection');
const getProviderFactory = require('./providers/providerFactory');
const ResearchIngestionService = require('./researchIngestionService');

class MarketRegimeAnalyzer {
  constructor() {
    this.providerFactory = getProviderFactory();
    this.researchService = new ResearchIngestionService();
    this.cacheExpiryMs = 14400000; // 4 hours
  }

  /**
   * Detect current market regime using LLM
   * @returns {Object} Regime data with confidence and reasoning
   */
  async detectCurrentRegime() {
    console.log('[MarketRegimeAnalyzer] Detecting current regime...');

    try {
      // 1. Fetch market indicators (mock for now, integrate with real data later)
      const indicators = await this.fetchMarketIndicators();
      
      // 2. Fetch recent macro news
      const macroContext = await this.researchService.getMacroContext();
      
      // 3. Build LLM prompt
      const prompt = this.buildRegimeDetectionPrompt(indicators, macroContext);
      
      // 4. Get LLM analysis
      const aiProvider = await this.providerFactory.getProvider('openai', 'system'); // System user
      
      const response = await aiProvider.chat([
        { role: 'system', content: 'You are an expert market analyst specializing in regime detection.' },
        { role: 'user', content: prompt }
      ], {
        temperature: 0.3,
        maxTokens: 1024
      });

      // 5. Parse response
      const regimeData = this.parseRegimeResponse(response);
      
      // 6. Store in database
      await this.storeRegime(regimeData);
      
      console.log(`[MarketRegimeAnalyzer] Detected regime: ${regimeData.regime} (confidence: ${regimeData.confidence})`);
      
      return regimeData;

    } catch (error) {
      console.error('[MarketRegimeAnalyzer] Error detecting regime:', error.message);
      // Fallback to rule-based detection
      return this.fallbackRegimeDetection();
    }
  }

  /**
   * Build LLM prompt for regime detection
   */
  buildRegimeDetectionPrompt(indicators, macroContext) {
    const macroClient = require('./external/macroDataClient');
    const client = new macroClient();
    const macroFormatted = client.formatForPrompt(macroContext);

    return `Analyze the current Indian stock market regime based on the following data:

**Market Indicators (as of ${new Date().toISOString().split('T')[0]}):**
- Nifty 50: ${indicators.nifty50.value} (${indicators.nifty50.change >= 0 ? '+' : ''}${indicators.nifty50.change}% today, ${indicators.nifty50.weekChange >= 0 ? '+' : ''}${indicators.nifty50.weekChange}% this week)
- VIX (India VIX): ${indicators.vix.value} (${indicators.vix.trend})
- Advance/Decline Ratio: ${indicators.advanceDecline} (${indicators.breadth})
- FII Activity: ${indicators.fiiActivity} (${indicators.fiiTrend})
- 50-Day SMA: ${indicators.sma50} (Price ${indicators.priceVsSMA50})
- 200-Day SMA: ${indicators.sma200} (Price ${indicators.priceVsSMA200})

${macroFormatted}

**Recent Market Events:**
${indicators.recentEvents.map(e => `- ${e}`).join('\n')}

Based on this comprehensive data, determine the current market regime:

**Regime Options:**
1. **BULL**: Strong uptrend, positive momentum, low VIX, broad participation, FII buying
2. **BEAR**: Downtrend, negative momentum, selling pressure, weak breadth
3. **VOLATILE**: High VIX, choppy price action, conflicting signals, uncertainty
4. **CONSOLIDATION**: Sideways/range-bound, low momentum, waiting for catalyst

Respond in JSON format ONLY:
{
  "regime": "BULL|BEAR|VOLATILE|CONSOLIDATION",
  "confidence": 0.0-1.0,
  "reasoning": "Detailed explanation of why this regime was selected",
  "expected_duration_days": estimated days this regime will persist,
  "key_risks": ["risk1", "risk2"],
  "key_opportunities": ["opportunity1", "opportunity2"],
  "sector_preferences": ["sector1", "sector2"],
  "recommended_strategy": "aggressive|moderate|defensive"
}`;
  }

  /**
   * Fetch current market indicators
   */
  async fetchMarketIndicators() {
    // In production, fetch from live market data API
    // For now, return mock data
    return {
      nifty50: {
        value: 22450,
        change: 0.8,
        weekChange: 5.2
      },
      vix: {
        value: 12.5,
        trend: 'decreasing'
      },
      advanceDecline: 2.1,
      breadth: 'strong',
      fiiActivity: 'Net buyers ₹2,400 Cr (3 days)',
      fiiTrend: 'positive',
      sma50: 22100,
      priceVsSMA50: 'above',
      sma200: 21500,
      priceVsSMA200: 'above',
      recentEvents: [
        'RBI held rates at 6.5%, growth outlook raised',
        'Q2 GDP growth at 7.8%, exceeding expectations',
        'Global sentiment positive after Fed pause',
        'Strong FII inflows continuing for 5 consecutive days'
      ]
    };
  }

  /**
   * Parse LLM response
   */
  parseRegimeResponse(response) {
    try {
      const content = response.content || response.reply || '';
      
      // Try to extract JSON
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        
        return {
          regime: parsed.regime || 'CONSOLIDATION',
          confidence: parseFloat(parsed.confidence) || 0.5,
          reasoning: parsed.reasoning || 'Unable to determine regime',
          expectedDurationDays: parseInt(parsed.expected_duration_days) || 7,
          keyRisks: parsed.key_risks || [],
          keyOpportunities: parsed.key_opportunities || [],
          sectorPreferences: parsed.sector_preferences || [],
          recommendedStrategy: parsed.recommended_strategy || 'moderate',
          detectedAt: new Date(),
          validUntil: new Date(Date.now() + 14400000) // 4 hours
        };
      }
      
      throw new Error('No JSON found in response');
    } catch (error) {
      console.error('[MarketRegimeAnalyzer] Parse error:', error.message);
      return this.fallbackRegimeDetection();
    }
  }

  /**
   * Rule-based fallback regime detection
   */
  fallbackRegimeDetection() {
    console.log('[MarketRegimeAnalyzer] Using fallback regime detection');
    
    return {
      regime: 'CONSOLIDATION',
      confidence: 0.6,
      reasoning: 'Fallback detection: Market in consolidation based on neutral indicators',
      expectedDurationDays: 7,
      keyRisks: ['Low confidence in detection'],
      keyOpportunities: ['Range-bound trading opportunities'],
      sectorPreferences: ['Defensive', 'Large-cap'],
      recommendedStrategy: 'moderate',
      detectedAt: new Date(),
      validUntil: new Date(Date.now() + 14400000)
    };
  }

  /**
   * Store regime in database
   */
  async storeRegime(regimeData) {
    try {
      const query = `
        INSERT INTO market_regimes 
        (regime_type, confidence, indicators, llm_reasoning, detected_at, valid_until)
        VALUES ($1, $2, $3, $4, $5, $6)
      `;

      await db.query(query, [
        regimeData.regime,
        regimeData.confidence,
        JSON.stringify({
          keyRisks: regimeData.keyRisks,
          keyOpportunities: regimeData.keyOpportunities,
          sectorPreferences: regimeData.sectorPreferences,
          recommendedStrategy: regimeData.recommendedStrategy,
          expectedDurationDays: regimeData.expectedDurationDays
        }),
        regimeData.reasoning,
        regimeData.detectedAt,
        regimeData.validUntil
      ]);

      console.log('[MarketRegimeAnalyzer] Regime stored in database');
    } catch (error) {
      console.error('[MarketRegimeAnalyzer] Store error:', error.message);
    }
  }

  /**
   * Get active regime (cached if still valid)
   */
  async getActiveRegime() {
    try {
      const query = `
        SELECT regime_type, confidence, indicators, llm_reasoning, detected_at, valid_until
        FROM market_regimes
        WHERE valid_until > NOW()
        ORDER BY detected_at DESC
        LIMIT 1
      `;

      const result = await db.query(query);

      if (result.rows.length > 0) {
        const row = result.rows[0];
        console.log(`[MarketRegimeAnalyzer] Using cached regime: ${row.regime_type}`);
        
        return {
          regime: row.regime_type,
          confidence: parseFloat(row.confidence),
          reasoning: row.llm_reasoning,
          ...row.indicators,
          detectedAt: row.detected_at,
          validUntil: row.valid_until
        };
      }

      // No valid cached regime, detect fresh
      console.log('[MarketRegimeAnalyzer] No valid cached regime, detecting fresh');
      return await this.detectCurrentRegime();

    } catch (error) {
      console.error('[MarketRegimeAnalyzer] Error getting active regime:', error.message);
      return this.fallbackRegimeDetection();
    }
  }

  /**
   * Format regime for LLM prompt inclusion
   */
  formatForPrompt(regime) {
    return `**Current Market Regime:** ${regime.regime} (Confidence: ${(regime.confidence * 100).toFixed(0)}%)
**Regime Analysis:** ${regime.reasoning}
**Sector Preferences:** ${regime.sectorPreferences?.join(', ') || 'Balanced'}
**Recommended Strategy:** ${regime.recommendedStrategy || 'Moderate'}
**Key Risks:** ${regime.keyRisks?.join('; ') || 'Standard market risks'}
**Valid Until:** ${regime.validUntil ? new Date(regime.validUntil).toLocaleString() : 'TBD'}`;
  }
}

module.exports = MarketRegimeAnalyzer;

