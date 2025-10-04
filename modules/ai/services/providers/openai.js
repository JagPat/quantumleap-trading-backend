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

