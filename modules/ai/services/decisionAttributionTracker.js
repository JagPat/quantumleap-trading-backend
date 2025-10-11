/**
 * Decision Attribution Tracker
 * Records AI decisions and tracks which data sources influenced them
 * Enables learning from outcomes
 */

const db = require('../../../core/database/connection');

class DecisionAttributionTracker {
  /**
   * Record stock selection decision
   * @param {string} userId 
   * @param {Object} goal 
   * @param {Array} selectedStocks 
   * @param {Object} context - Regime, research data, etc
   * @returns {number} Decision ID
   */
  async recordStockSelection(userId, goal, selectedStocks, context) {
    try {
      const { regime, researchData } = context;

      // 1. Store main decision
      const decisionQuery = `
        INSERT INTO ai_decisions 
        (user_id, decision_type, decision_data, market_regime, regime_confidence, created_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        RETURNING id
      `;

      const decisionData = {
        goal: {
          name: goal.name || 'Unnamed Goal',
          profitTarget: goal.profitTarget,
          timeframe: goal.timeframe,
          riskTolerance: goal.riskTolerance
        },
        selectedStocks: selectedStocks.map(s => ({
          symbol: s.symbol,
          allocation: s.allocation,
          rationale: s.rationale,
          data_sources: s.data_sources || []
        }))
      };

      const decisionResult = await db.query(decisionQuery, [
        userId,
        'stock_selection',
        JSON.stringify(decisionData),
        regime?.regime || 'UNKNOWN',
        regime?.confidence || 0.5
      ]);

      const decisionId = decisionResult.rows[0].id;

      // 2. Store attributions for each selected stock
      for (const stock of selectedStocks) {
        const dataSources = stock.data_sources || ['technical'];
        
        for (const source of dataSources) {
          // Find relevant research for this data source
          const sourceDetail = this.extractSourceDetail(source, stock, researchData);
          
          await this.recordAttribution(decisionId, {
            dataSource: source,
            sourceDetail: sourceDetail,
            attributionWeight: 1.0 / dataSources.length, // Equal weight initially
            contentSummary: stock.research_summary || stock.rationale
          });
        }
      }

      console.log(`[AttributionTracker] Recorded decision ${decisionId} for user ${userId}`);
      return decisionId;

    } catch (error) {
      console.error('[AttributionTracker] Error recording stock selection:', error.message);
      throw error;
    }
  }

  /**
   * Record portfolio action decision
   */
  async recordPortfolioAction(userId, actions, regime, holdingsResearch) {
    try {
      // Store main decision
      const decisionQuery = `
        INSERT INTO ai_decisions 
        (user_id, decision_type, decision_data, market_regime, regime_confidence, created_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        RETURNING id
      `;

      const decisionData = {
        actions: actions.map(a => ({
          type: a.type,
          symbol: a.symbol,
          rationale: a.rationale,
          currentAllocation: a.currentAllocation,
          idealAllocation: a.idealAllocation
        }))
      };

      const decisionResult = await db.query(decisionQuery, [
        userId,
        'portfolio_action',
        JSON.stringify(decisionData),
        regime?.regime || 'UNKNOWN',
        regime?.confidence || 0.5
      ]);

      const decisionId = decisionResult.rows[0].id;

      // Store attributions for each action
      for (const action of actions) {
        const research = holdingsResearch?.find(h => h.symbol === action.symbol)?.research;
        
        if (research) {
          // Determine which data sources influenced this action
          const sources = this.determineInfluencingSources(action, research);
          
          for (const source of sources) {
            await this.recordAttribution(decisionId, {
              dataSource: source.type,
              sourceDetail: source.detail,
              attributionWeight: source.weight,
              contentSummary: action.rationale
            });
          }
        }
      }

      console.log(`[AttributionTracker] Recorded portfolio action decision ${decisionId}`);
      return decisionId;

    } catch (error) {
      console.error('[AttributionTracker] Error recording portfolio action:', error.message);
      throw error;
    }
  }

  /**
   * Record individual attribution
   */
  async recordAttribution(decisionId, { dataSource, sourceDetail, attributionWeight, contentSummary }) {
    try {
      const query = `
        INSERT INTO ai_decision_attributions
        (decision_id, data_source, source_detail, attribution_weight, content_summary)
        VALUES ($1, $2, $3, $4, $5)
      `;

      await db.query(query, [
        decisionId,
        dataSource,
        sourceDetail,
        attributionWeight,
        contentSummary
      ]);

    } catch (error) {
      console.error('[AttributionTracker] Error recording attribution:', error.message);
    }
  }

  /**
   * Get decision history for a user/symbol
   */
  async getDecisionHistory(userId, symbol = null, limit = 10) {
    try {
      let query = `
        SELECT 
          d.id,
          d.decision_type,
          d.decision_data,
          d.market_regime,
          d.regime_confidence,
          d.created_at,
          json_agg(
            json_build_object(
              'data_source', a.data_source,
              'source_detail', a.source_detail,
              'attribution_weight', a.attribution_weight
            )
          ) as attributions
        FROM ai_decisions d
        LEFT JOIN ai_decision_attributions a ON d.id = a.decision_id
        WHERE d.user_id = $1
      `;

      const params = [userId];

      if (symbol) {
        query += ` AND d.decision_data::text LIKE $2`;
        params.push(`%${symbol}%`);
      }

      query += `
        GROUP BY d.id
        ORDER BY d.created_at DESC
        LIMIT $${params.length + 1}
      `;
      params.push(limit);

      const result = await db.query(query, params);
      return result.rows;

    } catch (error) {
      console.error('[AttributionTracker] Error getting decision history:', error.message);
      return [];
    }
  }

  /**
   * Get decision by ID with full attribution
   */
  async getDecision(decisionId) {
    try {
      const query = `
        SELECT 
          d.*,
          json_agg(
            json_build_object(
              'data_source', a.data_source,
              'source_detail', a.source_detail,
              'attribution_weight', a.attribution_weight,
              'content_summary', a.content_summary
            )
          ) as attributions
        FROM ai_decisions d
        LEFT JOIN ai_decision_attributions a ON d.id = a.decision_id
        WHERE d.id = $1
        GROUP BY d.id
      `;

      const result = await db.query(query, [decisionId]);
      
      if (result.rows.length === 0) {
        return null;
      }

      return result.rows[0];

    } catch (error) {
      console.error('[AttributionTracker] Error getting decision:', error.message);
      return null;
    }
  }

  /**
   * Extract source detail from research data
   */
  extractSourceDetail(source, stock, researchData) {
    if (!researchData) return `Used ${source} for ${stock.symbol}`;

    const stockResearch = researchData.find(r => r.symbol === stock.symbol);
    if (!stockResearch) return `Used ${source} for ${stock.symbol}`;

    switch (source) {
      case 'news':
        const topNews = stockResearch.research?.news?.[0];
        return topNews?.headline || 'Recent news sentiment';
      
      case 'sentiment':
        const sentiment = stockResearch.research?.sentiment;
        return sentiment 
          ? `Sentiment: ${sentiment.sentiment} (${sentiment.score}, ${sentiment.volume} mentions)`
          : 'Social sentiment analysis';
      
      case 'fundamentals':
        const fundamentals = stockResearch.research?.fundamentals;
        return fundamentals
          ? `PE: ${fundamentals.pe}, ROE: ${fundamentals.roe}%, Trend: ${fundamentals.trend}`
          : 'Fundamental analysis';
      
      case 'regime':
        return `Market regime context`;
      
      default:
        return `${source} analysis for ${stock.symbol}`;
    }
  }

  /**
   * Determine which data sources influenced a portfolio action
   */
  determineInfluencingSources(action, research) {
    const sources = [];

    // Check if news influenced
    if (research?.news && research.news.length > 0) {
      const newsImpact = this.assessNewsImpact(action, research.news);
      if (newsImpact > 0.3) {
        sources.push({
          type: 'news',
          detail: research.news[0].headline,
          weight: newsImpact
        });
      }
    }

    // Check if sentiment influenced
    if (research?.sentiment) {
      const sentimentImpact = this.assessSentimentImpact(action, research.sentiment);
      if (sentimentImpact > 0.3) {
        sources.push({
          type: 'sentiment',
          detail: `${research.sentiment.sentiment} (${research.sentiment.score})`,
          weight: sentimentImpact
        });
      }
    }

    // Check if fundamentals influenced
    if (research?.fundamentals) {
      const fundamentalImpact = this.assessFundamentalImpact(action, research.fundamentals);
      if (fundamentalImpact > 0.3) {
        sources.push({
          type: 'fundamentals',
          detail: `Trend: ${research.fundamentals.trend}`,
          weight: fundamentalImpact
        });
      }
    }

    // Normalize weights
    const totalWeight = sources.reduce((sum, s) => sum + s.weight, 0);
    if (totalWeight > 0) {
      sources.forEach(s => s.weight /= totalWeight);
    }

    return sources.length > 0 ? sources : [{ type: 'technical', detail: 'Technical analysis', weight: 1.0 }];
  }

  /**
   * Assess impact of news on action decision
   */
  assessNewsImpact(action, news) {
    // Simple heuristic: positive news → accumulate, negative → dilute/exit
    const recentNews = news.slice(0, 3);
    const positiveCount = recentNews.filter(n => n.sentiment === 'positive').length;
    const negativeCount = recentNews.filter(n => n.sentiment === 'negative').length;

    if (action.type === 'accumulate' && positiveCount > negativeCount) return 0.7;
    if ((action.type === 'dilute' || action.type === 'exit') && negativeCount > positiveCount) return 0.7;
    
    return 0.4; // Moderate impact
  }

  /**
   * Assess impact of sentiment on action decision
   */
  assessSentimentImpact(action, sentiment) {
    const score = sentiment.score || 0.5;
    
    if (action.type === 'accumulate' && score > 0.6) return 0.8;
    if ((action.type === 'dilute' || action.type === 'exit') && score < 0.4) return 0.8;
    
    return 0.3;
  }

  /**
   * Assess impact of fundamentals on action decision
   */
  assessFundamentalImpact(action, fundamentals) {
    const trend = fundamentals.trend;
    
    if (action.type === 'accumulate' && trend === 'improving') return 0.9;
    if (action.type === 'exit' && trend === 'deteriorating') return 0.9;
    if (action.type === 'dilute' && trend === 'stable') return 0.5;
    
    return 0.4;
  }

  /**
   * Update attribution weights based on outcome
   * Called after trade closes to refine which data sources were accurate
   */
  async updateAttributionWeights(decisionId, outcome) {
    try {
      const decision = await this.getDecision(decisionId);
      if (!decision) return;

      const isProfitable = outcome.pnl > 0;
      const multiplier = isProfitable ? 1.1 : 0.9; // Boost if profitable, penalize if not

      // Update each attribution weight
      for (const attribution of decision.attributions) {
        if (!attribution.data_source) continue;

        const newWeight = attribution.attribution_weight * multiplier;
        
        await db.query(`
          UPDATE ai_decision_attributions
          SET attribution_weight = $1
          WHERE decision_id = $2 AND data_source = $3
        `, [newWeight, decisionId, attribution.data_source]);
      }

      console.log(`[AttributionTracker] Updated weights for decision ${decisionId} (outcome: ${isProfitable ? 'profit' : 'loss'})`);

    } catch (error) {
      console.error('[AttributionTracker] Error updating attribution weights:', error.message);
    }
  }
}

module.exports = DecisionAttributionTracker;

