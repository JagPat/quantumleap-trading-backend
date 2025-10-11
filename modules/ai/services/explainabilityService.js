/**
 * Explainability Service
 * Generates human-readable explanations for AI decisions
 * Increases trust and transparency
 */

class ExplainabilityService {
  /**
   * Explain stock selection decision
   * @param {Array} selectedStocks - AI-selected stocks
   * @param {Object} decision - Decision object with attribution
   * @returns {Object} Human-readable explanation
   */
  async explainStockSelection(selectedStocks, decision) {
    try {
      const explanations = [];
      
      // Overall selection summary
      const summary = this.generateSelectionSummary(selectedStocks, decision);
      
      // Per-stock explanations
      for (const stock of selectedStocks) {
        const stockExplanation = this.explainSingleStock(stock, decision);
        explanations.push(stockExplanation);
      }
      
      // Alternative choices (what else was considered?)
      const alternatives = this.explainAlternatives(selectedStocks, decision);
      
      // Confidence breakdown
      const confidenceBreakdown = this.explainConfidence(decision);
      
      return {
        summary,
        stockExplanations: explanations,
        alternatives,
        confidenceBreakdown,
        marketContext: this.explainMarketContext(decision),
        timestamp: new Date().toISOString()
      };
      
    } catch (error) {
      console.error('[Explainability] Error explaining stock selection:', error.message);
      return {
        summary: 'Unable to generate explanation',
        error: error.message
      };
    }
  }

  /**
   * Generate overall selection summary
   */
  generateSelectionSummary(selectedStocks, decision) {
    const totalStocks = selectedStocks.length;
    const regime = decision.market_regime || 'UNKNOWN';
    const avgAllocation = 100 / totalStocks;
    
    // Count data sources used
    const allSources = new Set();
    selectedStocks.forEach(s => {
      (s.data_sources || []).forEach(src => allSources.add(src));
    });
    
    const sourceList = Array.from(allSources).join(', ');
    
    return `AI selected ${totalStocks} stocks with an average allocation of ${avgAllocation.toFixed(1)}% each. ` +
           `The selection was based on ${sourceList} data in the context of a ${regime} market regime. ` +
           `This portfolio aims to achieve your profit target while managing risk according to your tolerance level.`;
  }

  /**
   * Explain single stock selection
   */
  explainSingleStock(stock, decision) {
    const { symbol, allocation, rationale, data_sources = [], research_summary } = stock;
    
    let explanation = `**${symbol} (${allocation}% allocation):** ${rationale}`;
    
    if (research_summary) {
      explanation += ` Research shows: ${research_summary}`;
    }
    
    if (data_sources.length > 0) {
      explanation += ` Decision influenced by: ${data_sources.join(', ')}.`;
    }
    
    return {
      symbol,
      allocation,
      explanation,
      keyFactors: this.extractKeyFactors(rationale),
      dataSources: data_sources
    };
  }

  /**
   * Extract key factors from rationale text
   */
  extractKeyFactors(rationale) {
    const factors = [];
    
    // Look for common keywords
    const keywords = {
      'earnings': 'Strong earnings',
      'upgrade': 'Analyst upgrade',
      'bullish': 'Bullish sentiment',
      'bearish': 'Bearish sentiment',
      'fundamental': 'Fundamental strength',
      'momentum': 'Price momentum',
      'liquidity': 'High liquidity',
      'diversification': 'Diversification benefit'
    };
    
    const lowerRationale = rationale.toLowerCase();
    
    for (const [keyword, factor] of Object.entries(keywords)) {
      if (lowerRationale.includes(keyword)) {
        factors.push(factor);
      }
    }
    
    return factors.length > 0 ? factors : ['General suitability for goal'];
  }

  /**
   * Explain alternatives (what else was considered?)
   */
  explainAlternatives(selectedStocks, decision) {
    // In a full implementation, this would retrieve runner-up stocks from the decision process
    // For now, provide generic explanation
    
    return {
      message: 'AI evaluated the top 100 liquid NSE stocks and your current holdings.',
      criteria: [
        'Stocks were ranked by expected contribution to your goal',
        'Diversification requirements (max 2 per sector)',
        'Risk alignment with your tolerance level',
        'Liquidity requirements for smooth execution',
        'Research momentum (news, sentiment, fundamentals)'
      ],
      notSelected: 'Other stocks were excluded due to lower expected returns, higher risk, or poor diversification fit.'
    };
  }

  /**
   * Explain confidence breakdown
   */
  explainConfidence(decision) {
    const confidence = decision.confidence || decision.regime_confidence || 0.5;
    
    let level = 'MEDIUM';
    let description = 'Moderate confidence in this decision';
    
    if (confidence >= 0.8) {
      level = 'HIGH';
      description = 'Very high confidence - strong agreement across all data sources';
    } else if (confidence >= 0.65) {
      level = 'MEDIUM-HIGH';
      description = 'Good confidence - most data sources align';
    } else if (confidence < 0.5) {
      level = 'LOW';
      description = 'Lower confidence - mixed or conflicting signals';
    }
    
    return {
      level,
      score: confidence,
      percentage: (confidence * 100).toFixed(0) + '%',
      description,
      recommendation: confidence >= 0.7 
        ? 'Proceed with standard position sizing'
        : confidence >= 0.5
        ? 'Consider reducing position sizes by 30-50%'
        : 'Manual review strongly recommended before execution'
    };
  }

  /**
   * Explain market context impact
   */
  explainMarketContext(decision) {
    const regime = decision.market_regime || 'UNKNOWN';
    
    const contextExplanations = {
      'BULL': 'In a BULL market, AI prioritizes growth-oriented stocks with strong momentum and positive sentiment.',
      'BEAR': 'In a BEAR market, AI favors defensive stocks with strong fundamentals and stable earnings.',
      'VOLATILE': 'In a VOLATILE market, AI selects high-quality stocks with lower correlation to reduce portfolio swings.',
      'CONSOLIDATION': 'In a CONSOLIDATION market, AI balances growth and value stocks while waiting for trend clarity.',
      'UNKNOWN': 'Market regime unclear - AI uses balanced approach across growth, value, and defensive stocks.'
    };
    
    return {
      regime,
      explanation: contextExplanations[regime] || contextExplanations['UNKNOWN'],
      impact: 'High' // Regime significantly impacts stock selection
    };
  }

  /**
   * Explain portfolio action
   */
  async explainPortfolioAction(action, research, regime) {
    const { type, symbol, reason, researchSignals = {}, data_sources = [] } = action;
    
    let explanation = `**${type} ${symbol}:** ${reason}`;
    
    // Add research context
    if (data_sources.length > 0) {
      const sourceDetails = [];
      
      if (data_sources.includes('news') && researchSignals.news) {
        sourceDetails.push(`news is ${researchSignals.news}`);
      }
      if (data_sources.includes('sentiment') && researchSignals.sentiment) {
        sourceDetails.push(`sentiment is ${researchSignals.sentiment}`);
      }
      if (data_sources.includes('fundamentals') && researchSignals.fundamentals) {
        sourceDetails.push(`fundamentals are ${researchSignals.fundamentals}`);
      }
      
      if (sourceDetails.length > 0) {
        explanation += ` Research shows: ${sourceDetails.join(', ')}.`;
      }
    }
    
    // Add regime context
    if (regime && regime.regime) {
      explanation += ` In the current ${regime.regime} market, this action aligns with recommended strategy.`;
    }
    
    return {
      action: type,
      symbol,
      explanation,
      primaryReason: reason,
      supportingFactors: data_sources,
      regime: regime?.regime || 'UNKNOWN'
    };
  }

  /**
   * Generate plain-English summary of decision
   */
  async generateDecisionSummary(decision) {
    const type = decision.decision_type;
    
    if (type === 'stock_selection') {
      const stocks = decision.decision_data?.selectedStocks || [];
      const stockList = stocks.map(s => `${s.symbol} (${s.allocation}%)`).join(', ');
      
      return `AI selected ${stocks.length} stocks: ${stockList}. ` +
             `Selection based on your goal and current ${decision.market_regime || 'market'} conditions.`;
    }
    
    if (type === 'portfolio_action') {
      const actions = decision.decision_data?.actions || [];
      const actionSummary = actions.map(a => `${a.type} ${a.symbol}`).join(', ');
      
      return `AI recommends ${actions.length} portfolio adjustments: ${actionSummary}. ` +
             `These actions optimize your portfolio for your goal while considering current market regime.`;
    }
    
    return 'AI decision recorded';
  }

  /**
   * Format explanation for LLM to enhance
   * (Optional: Use LLM to generate even better explanations)
   */
  async enhanceExplanationWithLLM(basicExplanation, aiProvider) {
    try {
      const prompt = `Convert this technical trading decision into a simple, user-friendly explanation:

${basicExplanation}

Make it:
1. Easy to understand for non-experts
2. Transparent about reasoning
3. Actionable (what should user do)
4. Reassuring (build trust in AI)

Keep it under 100 words.`;

      const response = await aiProvider.chat([
        { role: 'system', content: 'You are an expert at explaining complex financial decisions simply.' },
        { role: 'user', content: prompt }
      ], { temperature: 0.5, maxTokens: 200 });

      return response.content || basicExplanation;

    } catch (error) {
      console.error('[Explainability] Error enhancing explanation:', error.message);
      return basicExplanation; // Fallback to basic explanation
    }
  }
}

module.exports = ExplainabilityService;

