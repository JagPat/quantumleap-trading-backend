/**
 * Claude Provider (Anthropic)
 * Handles communication with Anthropic's Claude API for AI analysis
 */

const axios = require('axios');

class ClaudeProvider {
  constructor(apiKey, options = {}) {
    if (!apiKey) {
      throw new Error('Claude API key is required');
    }
    this.apiKey = apiKey;
    this.baseURL = 'https://api.anthropic.com/v1';
    this.model = options.model || 'claude-3-5-sonnet-20241022'; // Latest Claude 3.5 Sonnet
    this.version = '2023-06-01'; // Anthropic API version
  }

  /**
   * Generic chat completion
   * @param {Array} messages - Array of {role, content} objects
   * @param {Object} options - Additional options (temperature, max_tokens, etc.)
   */
  async chat(messages, options = {}) {
    try {
      const response = await axios.post(
        `${this.baseURL}/messages`,
        {
          model: this.model,
          max_tokens: options.maxTokens || options.max_tokens || 4096,
          temperature: options.temperature || 0.7,
          messages: this.convertMessages(messages),
          system: this.extractSystemMessage(messages)
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': this.apiKey,
            'anthropic-version': this.version
          }
        }
      );

      return {
        content: response.data.content[0].text,
        model: response.data.model,
        usage: {
          promptTokens: response.data.usage.input_tokens,
          completionTokens: response.data.usage.output_tokens,
          totalTokens: response.data.usage.input_tokens + response.data.usage.output_tokens
        }
      };
    } catch (error) {
      console.error('[Claude] Chat error:', error.response?.data || error.message);
      throw new Error(`Claude API error: ${error.response?.data?.error?.message || error.message}`);
    }
  }

  /**
   * Convert OpenAI-style messages to Claude format
   * Claude requires system message separate from messages array
   */
  convertMessages(messages) {
    return messages
      .filter(m => m.role !== 'system')
      .map(m => ({
        role: m.role === 'assistant' ? 'assistant' : 'user',
        content: m.content
      }));
  }

  /**
   * Extract system message for Claude
   */
  extractSystemMessage(messages) {
    const systemMsg = messages.find(m => m.role === 'system');
    return systemMsg ? systemMsg.content : undefined;
  }

  /**
   * Analyze portfolio using Claude
   */
  async analyzePortfolio(portfolioData) {
    const messages = [
      {
        role: 'system',
        content: 'You are an expert portfolio analyst. Analyze the given portfolio and provide insights.'
      },
      {
        role: 'user',
        content: `Analyze this portfolio:\n${JSON.stringify(portfolioData, null, 2)}`
      }
    ];

    const response = await this.chat(messages, { maxTokens: 2048 });
    
    return {
      analysis: response.content,
      model: response.model,
      provider: 'claude'
    };
  }

  /**
   * Generate trading strategy using Claude
   */
  async generateStrategy(params) {
    const messages = [
      {
        role: 'system',
        content: 'You are an expert trading strategist. Generate detailed, executable trading strategies.'
      },
      {
        role: 'user',
        content: `Generate a trading strategy with these parameters:\n${JSON.stringify(params, null, 2)}`
      }
    ];

    const response = await this.chat(messages, { maxTokens: 3072 });
    
    return {
      strategy: response.content,
      model: response.model,
      provider: 'claude'
    };
  }

  /**
   * Send message to AI assistant
   */
  async sendMessage(message, context = {}) {
    const messages = [
      {
        role: 'system',
        content: `You are Quantum Trading AI, an expert financial advisor and trading assistant.
        
${context.portfolioContext || ''}
${context.goalContext || ''}

Be helpful, accurate, and provide actionable advice. Always consider risk management.`
      },
      {
        role: 'user',
        content: message
      }
    ];

    const response = await this.chat(messages, { maxTokens: 1500 });
    
    return {
      reply: response.content,
      message_id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      thread_id: context.thread_id || `thread_${Date.now()}`,
      timestamp: new Date().toISOString(),
      model: response.model,
      provider: 'claude'
    };
  }
}

module.exports = ClaudeProvider;

