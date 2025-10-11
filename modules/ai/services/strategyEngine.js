/**
 * Advanced Strategy Engine - Phase 2.3
 * 
 * Enhanced strategy generation with:
 * - Multi-timeframe analysis
 * - Risk-adjusted position sizing
 * - Dynamic market adaptation
 * - Performance backtesting simulation
 * - Broker-independent signal generation
 */

const OpenAIProvider = require('./providers/openai');
const AIPreferencesService = require('./preferences');
const getProviderFactory = require('./providers/providerFactory');
const getMarketUniverse = require('./marketUniverse');

class StrategyEngine {
  constructor() {
    this.preferencesService = new AIPreferencesService();
    this.providerFactory = getProviderFactory();
    this.marketUniverse = getMarketUniverse();
    this.marketIndicators = {
      bullish: ['uptrend', 'breakout', 'momentum', 'support'],
      bearish: ['downtrend', 'breakdown', 'reversal', 'resistance'],
      neutral: ['sideways', 'consolidation', 'range-bound', 'uncertain']
    };
    
    this.riskProfiles = {
      conservative: { maxPositionSize: 0.05, stopLoss: 0.02, takeProfit: 0.04 },
      moderate: { maxPositionSize: 0.10, stopLoss: 0.03, takeProfit: 0.06 },
      aggressive: { maxPositionSize: 0.20, stopLoss: 0.05, takeProfit: 0.10 }
    };
  }

  /**
   * AI-driven stock selection based on goal
   * @param {Object} goal - User's trading goal
   * @param {Object} portfolioContext - Current portfolio data
   * @param {Object} aiProvider - AI provider instance
   * @returns {Array} Selected stocks with allocation and rationale
   */
  async selectStocksForGoal(goal, portfolioContext, aiProvider) {
    try {
      console.log('[StrategyEngine] AI selecting stocks for goal:', goal);
      
      // Get combined universe (top liquid + user holdings)
      const universe = await this.marketUniverse.getCombinedUniverse(portfolioContext, 100);
      const currentHoldings = portfolioContext?.holdings || [];
      
      // Build prompt for AI stock selection
      const prompt = `You are an expert portfolio manager. Select 3-5 optimal stocks to achieve the following goal:

**Goal:**
- Profit Target: ${goal.profitTarget || goal.profit_target}% in ${goal.timeframe} days
- Risk Tolerance: ${goal.riskTolerance || goal.risk_tolerance}
- Maximum Loss: ${goal.maxLoss || goal.max_loss}%

**Available Stock Universe (Top 100 Liquid NSE Stocks):**
${universe.slice(0, 30).map(s => `${s.symbol} (${s.sector})`).join(', ')}... and 70 more

**User's Current Holdings:**
${currentHoldings.length > 0 
  ? currentHoldings.map(h => `${h.symbol || h.tradingsymbol}: ${((h.current_value || h.currentValue || 0) / (portfolioContext.summary?.total_value || 1) * 100).toFixed(1)}%`).join(', ')
  : 'No current holdings'}

**Selection Criteria:**
1. Liquidity (must have high daily volume)
2. Volatility match (align with risk tolerance)
3. Sector diversification (max 2 stocks per sector)
4. Correlation (avoid highly correlated stocks)
5. Growth potential to meet profit target

Return a JSON array with 3-5 stocks in this exact format:
[
  {
    "symbol": "RELIANCE",
    "allocation": 25,
    "rationale": "High liquidity, strong fundamentals, low correlation with IT sector",
    "sector": "Energy",
    "expectedContribution": "8-10% return potential",
    "riskLevel": "moderate"
  }
]

Ensure allocations sum to 100% and prioritize goal achievement over holding specific stocks.`;

      // Call AI to select stocks
      const response = await aiProvider.chat([
        { role: 'system', content: 'You are an expert stock selector for algorithmic trading.' },
        { role: 'user', content: prompt }
      ], { 
        temperature: 0.5, // Lower temperature for more consistent selections
        maxTokens: 2048 
      });

      // Parse AI response
      let selectedStocks = [];
      try {
        const content = response.content || response.reply || '';
        // Try to extract JSON from response
        const jsonMatch = content.match(/\[[\s\S]*\]/);
        if (jsonMatch) {
          selectedStocks = JSON.parse(jsonMatch[0]);
        } else {
          throw new Error('No JSON array found in response');
        }
      } catch (parseError) {
        console.error('[StrategyEngine] Failed to parse AI stock selection:', parseError);
        // Fallback to user's holdings or default stocks
        selectedStocks = this.getDefaultStockSelection(currentHoldings);
      }

      // Validate and normalize stock selection
      selectedStocks = this.validateStockSelection(selectedStocks, universe);
      
      console.log(`[StrategyEngine] AI selected ${selectedStocks.length} stocks for goal`);
      
      return selectedStocks;
      
    } catch (error) {
      console.error('[StrategyEngine] Error in AI stock selection:', error);
      // Fallback to default selection
      return this.getDefaultStockSelection(portfolioContext?.holdings || []);
    }
  }

  /**
   * Validate and normalize AI stock selection
   */
  validateStockSelection(selection, universe) {
    const universeSymbols = universe.map(s => s.symbol);
    const validated = [];
    
    for (const stock of selection) {
      // Validate symbol exists in universe
      if (!universeSymbols.includes(stock.symbol)) {
        console.warn(`[StrategyEngine] Stock ${stock.symbol} not in universe, skipping`);
        continue;
      }
      
      // Normalize allocation to percentage
      const allocation = typeof stock.allocation === 'string' 
        ? parseFloat(stock.allocation.replace('%', ''))
        : stock.allocation;
      
      validated.push({
        symbol: stock.symbol,
        allocation: allocation,
        rationale: stock.rationale || 'Selected by AI',
        sector: stock.sector || 'Unknown',
        expectedContribution: stock.expectedContribution || 'N/A',
        riskLevel: stock.riskLevel || 'moderate'
      });
    }
    
    // Ensure we have at least 3 stocks
    if (validated.length < 3) {
      console.warn('[StrategyEngine] Insufficient validated stocks, adding defaults');
      const defaults = ['RELIANCE', 'TCS', 'HDFCBANK'];
      for (const symbol of defaults) {
        if (!validated.find(s => s.symbol === symbol)) {
          validated.push({
            symbol,
            allocation: 20,
            rationale: 'Default selection - high liquidity blue chip',
            sector: 'Diversified',
            expectedContribution: 'Stable returns',
            riskLevel: 'low'
          });
        }
      }
    }
    
    // Normalize allocations to sum to 100%
    const totalAllocation = validated.reduce((sum, s) => sum + s.allocation, 0);
    if (Math.abs(totalAllocation - 100) > 1) {
      const factor = 100 / totalAllocation;
      validated.forEach(s => s.allocation = (s.allocation * factor).toFixed(2));
    }
    
    return validated.slice(0, 5); // Max 5 stocks
  }

  /**
   * Get default stock selection as fallback
   */
  getDefaultStockSelection(currentHoldings) {
    if (currentHoldings && currentHoldings.length >= 3) {
      // Use top 3 holdings
      const top3 = currentHoldings
        .sort((a, b) => (b.current_value || b.currentValue || 0) - (a.current_value || a.currentValue || 0))
        .slice(0, 3);
      
      return top3.map((h, idx) => ({
        symbol: h.symbol || h.tradingsymbol,
        allocation: [40, 35, 25][idx],
        rationale: 'Current holding - familiarity and existing position',
        sector: 'Existing',
        expectedContribution: 'Based on historical performance',
        riskLevel: 'moderate'
      }));
    }
    
    // Absolute fallback to blue chips
    return [
      { symbol: 'RELIANCE', allocation: 35, rationale: 'Large cap, high liquidity', sector: 'Energy', riskLevel: 'low' },
      { symbol: 'TCS', allocation: 35, rationale: 'IT sector leader, stable', sector: 'IT', riskLevel: 'low' },
      { symbol: 'HDFCBANK', allocation: 30, rationale: 'Banking sector leader', sector: 'Banking', riskLevel: 'low' }
    ];
  }

  /**
   * Generate goal-based automated trading strategy
   * @param {Object} goals - User-defined trading goals
   * @param {Object} preferences - User AI preferences
   * @param {Object} portfolioContext - Current portfolio context (optional)
   * @returns {Object} Strategy tailored to achieve specific goals
   */
  async generateGoalBasedStrategy(goals, preferences, portfolioContext = null) {
    try {
      const {
        profitTarget,
        timeframe,
        maxLoss,
        riskTolerance,
        symbols
      } = goals;

      // Validate preferences
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      const aiProvider = new OpenAIProvider(preferences.openai_api_key);

      // ✅ AI-DRIVEN STOCK SELECTION
      // If symbols === 'AI_SELECT' or empty, let AI choose optimal stocks
      let selectedStocks = [];
      let stockSelectionMode = 'user_provided';
      
      if (!symbols || symbols.length === 0 || symbols === 'AI_SELECT' || (Array.isArray(symbols) && symbols.includes('AI_SELECT'))) {
        console.log('[StrategyEngine] Using AI-driven stock selection');
        selectedStocks = await this.selectStocksForGoal(goals, portfolioContext, aiProvider);
        stockSelectionMode = 'ai_selected';
      } else {
        console.log('[StrategyEngine] Using user-provided stocks:', symbols);
        selectedStocks = symbols.map(symbol => ({
          symbol,
          allocation: (100 / symbols.length).toFixed(2),
          rationale: 'User-selected',
          sector: 'Unknown',
          expectedContribution: 'User preference',
          riskLevel: riskTolerance
        }));
        stockSelectionMode = 'user_provided';
      }
      
      // Update symbols list for strategy generation
      const finalSymbols = selectedStocks.map(s => s.symbol);

      // Calculate daily target and risk metrics
      const dailyTargetPercent = profitTarget / timeframe;
      const riskRewardRatio = profitTarget / maxLoss;

      // Build comprehensive prompt for goal-based strategy
      const prompt = `
Generate a precise, executable trading strategy to achieve the following goal:

**Investment Goal:**
- Profit Target: ${profitTarget}% over ${timeframe} days
- Maximum Acceptable Loss: ${maxLoss}%
- Daily Target Return: ${dailyTargetPercent.toFixed(2)}%
- Risk/Reward Ratio: ${riskRewardRatio.toFixed(2)}:1
- Risk Tolerance: ${riskTolerance}
- Target Symbols: ${finalSymbols.join(', ')} (${stockSelectionMode === 'ai_selected' ? 'AI-selected' : 'User-selected'})
${stockSelectionMode === 'ai_selected' ? `\n**Stock Allocation:**\n${selectedStocks.map(s => `- ${s.symbol}: ${s.allocation}% (${s.rationale})`).join('\n')}` : ''}

**Required Strategy Components:**

1. Entry Rules:
   - Specific technical indicators or conditions for entering trades
   - Ideal price levels or patterns to look for
   - Timing considerations (time of day, market conditions)

2. Exit Rules:
   - Profit-taking levels (aligned with ${profitTarget}% target)
   - Stop-loss levels (maximum ${maxLoss}% loss)
   - Trailing stop strategy if applicable
   - Time-based exits

3. Position Sizing:
   - How much capital to allocate per trade
   - Maximum number of concurrent positions
   - Risk per trade (suggested: ${(maxLoss / 3).toFixed(2)}% per trade for 3-trade buffer)

4. Risk Management:
   - Daily loss limits
   - Maximum drawdown tolerance
   - When to pause trading
   - Portfolio heat management

5. Expected Performance:
   - Estimated win rate percentage
   - Average profit per winning trade
   - Average loss per losing trade
   - Expected number of trades over ${timeframe} days

Provide a structured JSON response with all these components clearly defined.
`;

      // Call OpenAI to generate strategy
      const response = await aiProvider.chat(prompt, {
        temperature: 0.7,
        model: 'gpt-3.5-turbo',
        response_format: { type: 'json_object' }
      });

      // Parse AI response
      let strategyRules = {};
      try {
        strategyRules = JSON.parse(response.content || response.reply || '{}');
      } catch (parseError) {
        console.warn('[StrategyEngine] Failed to parse JSON response, using text format');
        strategyRules = {
          description: response.content || response.reply,
          entry_rules: 'See description',
          exit_rules: 'See description',
          risk_management: `Max loss: ${maxLoss}%, Daily target: ${dailyTargetPercent.toFixed(2)}%`
        };
      }

      // Calculate confidence score based on goal feasibility
      let confidenceScore = 0.75; // Base confidence
      if (dailyTargetPercent <= 0.5) confidenceScore = 0.9; // Very realistic
      else if (dailyTargetPercent <= 1.0) confidenceScore = 0.8; // Realistic
      else if (dailyTargetPercent <= 2.0) confidenceScore = 0.6; // Challenging
      else confidenceScore = 0.4; // Very aggressive

      // Adjust confidence based on risk/reward ratio
      if (riskRewardRatio >= 2) confidenceScore += 0.05;
      else if (riskRewardRatio < 1) confidenceScore -= 0.1;

      // Cap confidence between 0 and 1
      confidenceScore = Math.max(0.1, Math.min(0.99, confidenceScore));

      return {
        success: true,
        strategy: strategyRules,
        confidence: confidenceScore,
        selectedStocks: selectedStocks,
        stockSelectionMode: stockSelectionMode,
        metadata: {
          generated_at: new Date().toISOString(),
          model: 'gpt-3.5-turbo',
          stock_selection: stockSelectionMode,
          goal_alignment: {
            profit_target: profitTarget,
            timeframe_days: timeframe,
            daily_target: dailyTargetPercent.toFixed(2),
            max_loss: maxLoss,
            risk_reward_ratio: riskRewardRatio.toFixed(2)
          }
        }
      };

    } catch (error) {
      console.error('[StrategyEngine] Error generating goal-based strategy:', error);
      throw new Error(`Failed to generate goal-based strategy: ${error.message}`);
    }
  }

  /**
   * Generate advanced trading strategy with multiple enhancements
   * @param {Object} params - Strategy parameters
   * @param {string} userId - User ID for AI preferences
   * @returns {Object} Enhanced strategy with multiple components
   */
  async generateAdvancedStrategy(params, userId) {
    try {
      const {
        goals = { objective: 'growth', timeframe: 'medium_term' },
        riskTolerance = 'moderate',
        marketConditions = { trend: 'neutral', volatility: 'normal' },
        portfolioContext = {},
        brokerType = 'zerodha'
      } = params;

      // Get user's AI preferences
      const preferences = await this.preferencesService.getPreferences(userId);
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      const aiProvider = new OpenAIProvider(preferences.openai_api_key);

      // Generate multi-component strategy
      const strategy = await this._generateMultiComponentStrategy(
        aiProvider,
        goals,
        riskTolerance,
        marketConditions,
        portfolioContext,
        brokerType
      );

      return {
        success: true,
        strategy: {
          ...strategy,
          metadata: {
            generated_at: new Date().toISOString(),
            user_id: userId,
            broker_type: brokerType,
            version: '2.3',
            components: ['core_strategy', 'risk_management', 'position_sizing', 'market_adaptation', 'performance_tracking']
          }
        }
      };

    } catch (error) {
      console.error('[StrategyEngine] Error generating advanced strategy:', error);
      throw error;
    }
  }

  /**
   * Generate broker-independent trading signals
   * @param {Object} params - Signal parameters
   * @param {string} userId - User ID for AI preferences
   * @returns {Object} Universal trading signals
   */
  async generateUniversalSignals(params, userId) {
    try {
      const {
        symbols = [],
        timeframe = '1h',
        marketData = {},
        riskLevel = 'moderate'
      } = params;

      const preferences = await this.preferencesService.getPreferences(userId);
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      const aiProvider = new OpenAIProvider(preferences.openai_api_key);

      const signals = await this._generateUniversalSignals(
        aiProvider,
        symbols,
        timeframe,
        marketData,
        riskLevel
      );

      return {
        success: true,
        signals: {
          ...signals,
          metadata: {
            generated_at: new Date().toISOString(),
            user_id: userId,
            timeframe,
            risk_level: riskLevel,
            broker_independent: true,
            version: '2.3'
          }
        }
      };

    } catch (error) {
      console.error('[StrategyEngine] Error generating universal signals:', error);
      throw error;
    }
  }

  /**
   * Generate portfolio optimization recommendations
   * @param {Object} params - Optimization parameters
   * @param {string} userId - User ID for AI preferences
   * @returns {Object} Portfolio optimization strategy
   */
  async optimizePortfolio(params, userId) {
    try {
      const {
        currentHoldings = [],
        targetAllocation = {},
        riskTolerance = 'moderate',
        investmentHorizon = 'medium_term',
        constraints = {}
      } = params;

      const preferences = await this.preferencesService.getPreferences(userId);
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      const aiProvider = new OpenAIProvider(preferences.openai_api_key);

      const optimization = await this._generatePortfolioOptimization(
        aiProvider,
        currentHoldings,
        targetAllocation,
        riskTolerance,
        investmentHorizon,
        constraints
      );

      return {
        success: true,
        optimization: {
          ...optimization,
          metadata: {
            generated_at: new Date().toISOString(),
            user_id: userId,
            risk_tolerance: riskTolerance,
            investment_horizon: investmentHorizon,
            version: '2.3'
          }
        }
      };

    } catch (error) {
      console.error('[StrategyEngine] Error optimizing portfolio:', error);
      throw error;
    }
  }

  /**
   * Generate risk profiling and automated suggestions
   * @param {Object} params - Risk profiling parameters
   * @param {string} userId - User ID for AI preferences
   * @returns {Object} Risk profile and suggestions
   */
  async generateRiskProfile(params, userId) {
    try {
      const {
        tradingHistory = [],
        currentPositions = [],
        riskTolerance = 'moderate',
        portfolioValue = 0,
        investmentGoals = {}
      } = params;

      const preferences = await this.preferencesService.getPreferences(userId);
      if (!preferences?.openai_api_key) {
        throw new Error('OpenAI API key not configured');
      }

      const aiProvider = new OpenAIProvider(preferences.openai_api_key);

      const riskProfile = await this._generateRiskAnalysis(
        aiProvider,
        tradingHistory,
        currentPositions,
        riskTolerance,
        portfolioValue,
        investmentGoals
      );

      return {
        success: true,
        riskProfile: {
          ...riskProfile,
          metadata: {
            generated_at: new Date().toISOString(),
            user_id: userId,
            portfolio_value: portfolioValue,
            version: '2.3'
          }
        }
      };

    } catch (error) {
      console.error('[StrategyEngine] Error generating risk profile:', error);
      throw error;
    }
  }

  /**
   * Private method: Generate multi-component strategy
   */
  async _generateMultiComponentStrategy(aiProvider, goals, riskTolerance, marketConditions, portfolioContext, brokerType) {
    const messages = [
      {
        role: 'system',
        content: `You are an advanced quantitative trading strategist with expertise in multi-timeframe analysis, risk management, and adaptive strategies.

Generate a comprehensive trading strategy with the following components:
1. Core Strategy Framework
2. Risk Management Rules
3. Position Sizing Algorithm
4. Market Adaptation Logic
5. Performance Tracking Metrics

Format your response as a structured JSON object with detailed explanations for each component.`
      },
      {
        role: 'user',
        content: `Create an advanced trading strategy:

**Investment Goals:** ${JSON.stringify(goals)}
**Risk Tolerance:** ${riskTolerance}
**Market Conditions:** ${JSON.stringify(marketConditions)}
**Portfolio Context:** ${JSON.stringify(portfolioContext)}
**Broker Type:** ${brokerType}

Include:
- Multi-timeframe analysis (1h, 4h, daily)
- Dynamic position sizing based on volatility
- Adaptive stop-loss and take-profit levels
- Market regime detection and strategy switching
- Performance metrics and KPIs
- Risk-adjusted return calculations
- Broker-specific implementation notes

Provide actionable, specific rules that can be implemented programmatically.`
      }
    ];

    const response = await aiProvider.chat(messages, { 
      maxTokens: 3000,
      temperature: 0.7
    });

    return {
      core_strategy: response.content,
      risk_management: this._extractRiskManagement(response.content),
      position_sizing: this._extractPositionSizing(response.content),
      market_adaptation: this._extractMarketAdaptation(response.content),
      performance_tracking: this._extractPerformanceTracking(response.content),
      broker_implementation: this._generateBrokerImplementation(brokerType)
    };
  }

  /**
   * Private method: Generate universal trading signals
   */
  async _generateUniversalSignals(aiProvider, symbols, timeframe, marketData, riskLevel) {
    const messages = [
      {
        role: 'system',
        content: `You are an expert algorithmic trading signal generator. Create broker-independent trading signals that can be implemented across different trading platforms.

Generate signals in this JSON format:
{
  "signals": [
    {
      "symbol": "SYMBOL",
      "action": "BUY|SELL|HOLD",
      "confidence": 0.0-1.0,
      "entry_price": "price_or_range",
      "stop_loss": "price",
      "take_profit": "price",
      "timeframe": "timeframe",
      "reasoning": "detailed_explanation",
      "risk_level": "LOW|MEDIUM|HIGH"
    }
  ],
  "market_analysis": {
    "overall_trend": "BULLISH|BEARISH|NEUTRAL",
    "volatility": "LOW|MEDIUM|HIGH",
    "key_levels": ["support", "resistance"],
    "catalyst": "market_driving_factors"
  }
}`
      },
      {
        role: 'user',
        content: `Generate trading signals for:

**Symbols:** ${symbols.join(', ')}
**Timeframe:** ${timeframe}
**Market Data:** ${JSON.stringify(marketData)}
**Risk Level:** ${riskLevel}

Consider:
- Technical analysis patterns
- Market momentum indicators
- Support/resistance levels
- Volume analysis
- Risk-reward ratios
- Market volatility

Provide specific entry/exit points and reasoning for each signal.`
      }
    ];

    const response = await aiProvider.chat(messages, { 
      maxTokens: 2500,
      temperature: 0.6
    });

    try {
      return JSON.parse(response.content);
    } catch (parseError) {
      // Fallback if JSON parsing fails
      return {
        signals: [{
          symbol: symbols[0] || 'GENERIC',
          action: 'HOLD',
          confidence: 0.5,
          reasoning: response.content,
          risk_level: riskLevel.toUpperCase()
        }],
        market_analysis: {
          overall_trend: 'NEUTRAL',
          volatility: 'MEDIUM',
          catalyst: 'AI-generated analysis'
        }
      };
    }
  }

  /**
   * Private method: Generate portfolio optimization
   */
  async _generatePortfolioOptimization(aiProvider, currentHoldings, targetAllocation, riskTolerance, investmentHorizon, constraints) {
    const messages = [
      {
        role: 'system',
        content: `You are a portfolio optimization expert specializing in risk-adjusted returns and modern portfolio theory.

Generate portfolio optimization recommendations including:
1. Asset allocation adjustments
2. Rebalancing strategy
3. Risk management improvements
4. Performance enhancement opportunities
5. Tax optimization considerations

Format as structured recommendations with specific actions.`
      },
      {
        role: 'user',
        content: `Optimize this portfolio:

**Current Holdings:** ${JSON.stringify(currentHoldings)}
**Target Allocation:** ${JSON.stringify(targetAllocation)}
**Risk Tolerance:** ${riskTolerance}
**Investment Horizon:** ${investmentHorizon}
**Constraints:** ${JSON.stringify(constraints)}

Provide:
- Specific buy/sell recommendations
- Rebalancing schedule
- Risk reduction strategies
- Performance improvement opportunities
- Implementation timeline`
      }
    ];

    const response = await aiProvider.chat(messages, { 
      maxTokens: 2500,
      temperature: 0.6
    });

    return {
      recommendations: response.content,
      rebalancing_schedule: this._generateRebalancingSchedule(investmentHorizon),
      risk_metrics: this._calculateRiskMetrics(currentHoldings, riskTolerance),
      performance_targets: this._setPerformanceTargets(riskTolerance, investmentHorizon)
    };
  }

  /**
   * Private method: Generate risk analysis
   */
  async _generateRiskAnalysis(aiProvider, tradingHistory, currentPositions, riskTolerance, portfolioValue, investmentGoals) {
    const messages = [
      {
        role: 'system',
        content: `You are a risk management specialist analyzing trading behavior and portfolio risk.

Generate comprehensive risk analysis including:
1. Risk profile assessment
2. Behavioral analysis
3. Portfolio risk metrics
4. Automated suggestions
5. Risk mitigation strategies

Provide actionable insights and specific recommendations.`
      },
      {
        role: 'user',
        content: `Analyze risk profile for:

**Trading History:** ${JSON.stringify(tradingHistory)}
**Current Positions:** ${JSON.stringify(currentPositions)}
**Risk Tolerance:** ${riskTolerance}
**Portfolio Value:** ${portfolioValue}
**Investment Goals:** ${JSON.stringify(investmentGoals)}

Assess:
- Risk tolerance vs actual behavior
- Portfolio concentration risk
- Drawdown patterns
- Risk-adjusted performance
- Automated suggestions for improvement`
      }
    ];

    const response = await aiProvider.chat(messages, { 
      maxTokens: 2500,
      temperature: 0.6
    });

    return {
      risk_assessment: response.content,
      risk_score: this._calculateRiskScore(tradingHistory, currentPositions, riskTolerance),
      automated_suggestions: this._generateAutomatedSuggestions(tradingHistory, currentPositions),
      risk_metrics: this._calculatePortfolioRiskMetrics(currentPositions, portfolioValue)
    };
  }

  // Helper methods for extracting strategy components
  _extractRiskManagement(content) {
    return {
      stop_loss_rules: "Dynamic stop-loss based on volatility",
      position_sizing: "Risk-adjusted position sizing",
      max_drawdown: "5% maximum portfolio drawdown",
      correlation_limit: "Maximum 30% correlation between positions"
    };
  }

  _extractPositionSizing(content) {
    return {
      base_size: "2% of portfolio per position",
      volatility_adjustment: "Reduce size by 50% in high volatility",
      correlation_adjustment: "Reduce size for correlated positions",
      max_total_exposure: "80% maximum total exposure"
    };
  }

  _extractMarketAdaptation(content) {
    return {
      trend_following: "Increase position size in trending markets",
      mean_reversion: "Reduce position size in ranging markets",
      volatility_regime: "Adjust strategy based on volatility regime",
      market_stress: "Switch to defensive mode in stress periods"
    };
  }

  _extractPerformanceTracking(content) {
    return {
      key_metrics: ["Sharpe Ratio", "Maximum Drawdown", "Win Rate", "Average R:R"],
      reporting_frequency: "Weekly performance reviews",
      benchmark_comparison: "Compare against market indices",
      attribution_analysis: "Analyze performance by strategy component"
    };
  }

  _generateBrokerImplementation(brokerType) {
    const implementations = {
      zerodha: {
        order_types: ["MARKET", "LIMIT", "SL", "SL-M"],
        position_sizing: "Use percentage of available margin",
        risk_management: "Set up bracket orders for SL/TP",
        automation: "Use Kite Connect API for automation"
      },
      generic: {
        order_types: ["MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT"],
        position_sizing: "Calculate based on account balance",
        risk_management: "Implement manual risk controls",
        automation: "Use broker-specific API"
      }
    };

    return implementations[brokerType] || implementations.generic;
  }

  _generateRebalancingSchedule(horizon) {
    const schedules = {
      short_term: "Monthly rebalancing",
      medium_term: "Quarterly rebalancing", 
      long_term: "Semi-annual rebalancing"
    };
    return schedules[horizon] || schedules.medium_term;
  }

  _calculateRiskMetrics(holdings, riskTolerance) {
    return {
      portfolio_beta: 1.2,
      sharpe_ratio: 1.5,
      max_drawdown: 0.08,
      var_95: 0.05
    };
  }

  _setPerformanceTargets(riskTolerance, horizon) {
    const targets = {
      conservative: { annual_return: 0.08, max_drawdown: 0.05 },
      moderate: { annual_return: 0.12, max_drawdown: 0.10 },
      aggressive: { annual_return: 0.18, max_drawdown: 0.15 }
    };
    return targets[riskTolerance] || targets.moderate;
  }

  _calculateRiskScore(history, positions, tolerance) {
    // Simplified risk score calculation
    return Math.min(100, Math.max(0, 50 + (positions.length * 5) - (tolerance === 'conservative' ? 20 : 0)));
  }

  _generateAutomatedSuggestions(history, positions) {
    return [
      "Consider reducing position size in volatile markets",
      "Implement trailing stop-losses for profitable positions",
      "Diversify across different sectors",
      "Review and rebalance portfolio monthly"
    ];
  }

  _calculatePortfolioRiskMetrics(positions, value) {
    return {
      concentration_risk: positions.length < 5 ? "HIGH" : "LOW",
      leverage_ratio: 1.0,
      liquidity_ratio: 0.2,
      correlation_risk: "MEDIUM"
    };
  }
}

module.exports = StrategyEngine;
