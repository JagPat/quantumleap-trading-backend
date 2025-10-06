/**
 * OpenAI Provider
 * Handles communication with OpenAI's API for AI analysis
 */

class OpenAIProvider {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('OpenAI API key is required');
    }
    this.apiKey = apiKey;
    this.baseURL = 'https://api.openai.com/v1';
    this.model = 'gpt-4'; // Can be configured: gpt-4, gpt-3.5-turbo, etc.
  }

  /**
   * Generic chat completion
   * @param {Array} messages - Array of {role, content} objects
   * @param {Object} options - Additional options (temperature, max_tokens, etc.)
   */
  async chat(messages, options = {}) {
    try {
      const response = await fetch(`${this.baseURL}/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: options.model || this.model,
          messages,
          temperature: options.temperature || 0.7,
          max_tokens: options.maxTokens || 2000,
          top_p: options.topP || 1.0,
          frequency_penalty: options.frequencyPenalty || 0,
          presence_penalty: options.presencePenalty || 0
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'OpenAI API request failed');
      }

      const data = await response.json();
      
      return {
        content: data.choices[0].message.content,
        usage: data.usage,
        model: data.model,
        finishReason: data.choices[0].finish_reason
      };
    } catch (error) {
      console.error('[OpenAI] Chat error:', error);
      throw error;
    }
  }

  /**
   * Analyze portfolio data
   * @param {Object} portfolioData - Holdings, positions, and summary
   * @returns {Object} Structured analysis
   */
  async analyzePortfolio(portfolioData) {
    const prompt = this._buildPortfolioPrompt(portfolioData);
    
    const messages = [
      {
        role: 'system',
        content: `You are an expert financial analyst specializing in portfolio analysis and risk assessment. 
Your task is to analyze trading portfolios and provide actionable insights.

Response Format (JSON):
{
  "summary": "Brief 2-3 sentence overview",
  "insights": ["Key insight 1", "Key insight 2", ...],
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "risk_assessment": {
    "score": 0-100,
    "level": "Low|Medium|High|Critical",
    "factors": ["Risk factor 1", ...]
  },
  "diversification": {
    "score": 0-100,
    "analysis": "Brief analysis of diversification"
  },
  "opportunities": ["Opportunity 1", "Opportunity 2", ...],
  "concerns": ["Concern 1", "Concern 2", ...]
}`
      },
      {
        role: 'user',
        content: prompt
      }
    ];

    try {
      const response = await this.chat(messages, { maxTokens: 3000 });
      
      // Try to parse JSON response
      try {
        const analysis = JSON.parse(response.content);
        return {
          ...analysis,
          provider: 'openai',
          model: response.model,
          timestamp: new Date().toISOString()
        };
      } catch (parseError) {
        // If JSON parsing fails, return structured fallback
        return {
          summary: response.content.substring(0, 500),
          insights: ['Raw analysis provided - see summary'],
          recommendations: [],
          risk_assessment: { score: 50, level: 'Medium', factors: [] },
          diversification: { score: 50, analysis: 'Unable to parse analysis' },
          opportunities: [],
          concerns: [],
          raw_response: response.content,
          provider: 'openai',
          model: response.model,
          timestamp: new Date().toISOString()
        };
      }
    } catch (error) {
      console.error('[OpenAI] Portfolio analysis error:', error);
      throw error;
    }
  }

  /**
   * Build prompt for portfolio analysis
   * @private
   */
  _buildPortfolioPrompt(portfolioData) {
    const { holdings = [], positions = [], summary = {} } = portfolioData;

    return `Analyze this trading portfolio and provide structured insights:

**Portfolio Summary:**
- Total Value: ₹${summary.total_value || 0}
- Day P&L: ₹${summary.day_pnl || 0}
- Total P&L: ₹${summary.total_pnl || 0}
- Holdings Count: ${holdings.length}
- Open Positions: ${positions.length}

**Holdings (Long-term investments):**
${holdings.slice(0, 10).map(h => `- ${h.tradingsymbol}: ${h.quantity} shares @ ₹${h.average_price} (Current: ₹${h.last_price}, P&L: ₹${h.pnl || 0})`).join('\n')}

**Positions (Intraday/Short-term):**
${positions.slice(0, 10).map(p => `- ${p.tradingsymbol}: ${p.quantity} shares @ ₹${p.average_price} (Current: ₹${p.last_price}, P&L: ₹${p.pnl || 0})`).join('\n')}

**Analysis Requirements:**
1. Assess overall portfolio health and risk level (0-100 score)
2. Evaluate diversification across sectors and instruments
3. Identify potential opportunities for improvement
4. Flag any concerning patterns or high-risk positions
5. Provide 3-5 actionable recommendations

Respond with structured JSON as specified in your system prompt.`;
  }

  /**
   * Analyze a single trade opportunity
   */
  async analyzeTrade(tradeData, portfolioContext = null) {
    const messages = [
      {
        role: 'system',
        content: 'You are an expert trade analyst. Analyze trade opportunities and provide risk/reward assessment.'
      },
      {
        role: 'user',
        content: `Analyze this trade opportunity:

Symbol: ${tradeData.symbol}
Entry Price: ₹${tradeData.entryPrice}
Target: ₹${tradeData.target || 'Not specified'}
Stop Loss: ₹${tradeData.stopLoss || 'Not specified'}
Quantity: ${tradeData.quantity}
Trade Type: ${tradeData.tradeType || 'BUY'}

${portfolioContext ? `Current Portfolio Context:\n${JSON.stringify(portfolioContext, null, 2)}` : ''}

Provide:
1. Risk/Reward ratio assessment
2. Technical analysis insights
3. Entry/Exit recommendations
4. Risk management suggestions`
      }
    ];

    const response = await this.chat(messages, { maxTokens: 1500 });
    return {
      analysis: response.content,
      provider: 'openai',
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Generate trading strategy based on goals and risk tolerance
   */
  async generateStrategy(goals, riskTolerance, marketConditions = null) {
    const messages = [
      {
        role: 'system',
        content: 'You are a professional trading strategist. Create detailed, actionable trading strategies.'
      },
      {
        role: 'user',
        content: `Generate a trading strategy:

**Goals:** ${goals}
**Risk Tolerance:** ${riskTolerance}
${marketConditions ? `**Market Conditions:** ${marketConditions}` : ''}

Include:
1. Strategy overview and objectives
2. Entry/exit rules
3. Position sizing guidelines
4. Risk management rules
5. Performance metrics to track
6. Key considerations and warnings`
      }
    ];

    const response = await this.chat(messages, { maxTokens: 2000 });
    return {
      strategy: response.content,
      provider: 'openai',
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Generate trading signals based on market conditions
   * @param {Object} params - Parameters for signal generation
   * @returns {Object} Trading signals and market analysis
   */
  async generateTradingSignals(params = {}) {
    const prompt = this._buildTradingSignalsPrompt(params);
    
    const messages = [
      {
        role: 'system',
        content: `You are an expert quantitative analyst specializing in algorithmic trading signals. 
Your task is to generate actionable trading signals based on market analysis.

Response Format (JSON):
{
  "signals": [
    {
      "symbol": "RELIANCE",
      "action": "BUY|SELL|HOLD",
      "confidence": 0.0-1.0,
      "reason": "Brief reason for signal",
      "entry_price": 2500,
      "target_price": 2600,
      "stop_loss": 2400,
      "timeframe": "1D|1W|1M"
    }
  ],
  "market_analysis": {
    "trend": "Bullish|Bearish|Sideways",
    "volatility": "Low|Medium|High",
    "sentiment": "Positive|Negative|Neutral",
    "key_levels": ["Support: 2400", "Resistance: 2600"]
  },
  "summary": "Brief market overview"
}`
      },
      {
        role: 'user',
        content: prompt
      }
    ];

    try {
      const response = await this.chat(messages, { maxTokens: 2000 });
      
      // Try to parse JSON response
      try {
        const parsed = JSON.parse(response.content);
        return {
          signals: parsed.signals || [],
          market_analysis: parsed.market_analysis || {},
          summary: parsed.summary || 'Market analysis completed',
          timestamp: new Date().toISOString()
        };
      } catch (parseError) {
        // Fallback to text response
        return {
          signals: [],
          market_analysis: { trend: 'neutral', volatility: 'medium' },
          summary: response.content,
          timestamp: new Date().toISOString()
        };
      }
    } catch (error) {
      console.error('[OpenAI] Trading signals error:', error);
      throw error;
    }
  }

  /**
   * Send message to AI assistant
   * @param {string} message - User message
   * @param {Object} context - Additional context
   * @returns {Object} AI response
   */
  async sendMessage(message, context = {}) {
    const messages = [
      {
        role: 'system',
        content: `You are Quantum Trading AI, an expert financial advisor and trading assistant. 
You help users with:
- Portfolio analysis and optimization
- Trading strategy development
- Market insights and analysis
- Risk management
- Investment education

Be helpful, accurate, and provide actionable advice. Always consider risk management in your recommendations.`
      },
      {
        role: 'user',
        content: message
      }
    ];

    try {
      const response = await this.chat(messages, { maxTokens: 1500 });
      
      return {
        reply: response.content,
        message_id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        thread_id: context.thread_id || `thread_${Date.now()}`,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('[OpenAI] Send message error:', error);
      throw error;
    }
  }

  /**
   * Build prompt for trading signals
   * @private
   */
  _buildTradingSignalsPrompt(params) {
    const { user_id, market_conditions, risk_level } = params;
    
    return `Generate trading signals for the current market conditions.

User Context:
- User ID: ${user_id || 'Unknown'}
- Market Conditions: ${market_conditions || 'Current market'}
- Risk Level: ${risk_level || 'Moderate'}

Please analyze the market and provide 3-5 actionable trading signals with specific entry/exit points, confidence levels, and reasoning. Focus on liquid stocks and ETFs.`;
  }

  /**
   * Validate API key
   * @returns {Promise<boolean>}
   */
  async validateKey() {
    try {
      const response = await this.chat([
        { role: 'user', content: 'Test' }
      ], { maxTokens: 5 });
      
      return response.content !== null;
    } catch (error) {
      console.error('[OpenAI] Key validation error:', error);
      return false;
    }
  }
}

module.exports = OpenAIProvider;

