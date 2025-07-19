# Trading Recommendations Function: OpenAI Assistants API Integration

## 🎯 **Refined Function Schema**

### **Enhanced generate_trading_recommendations Function**
```json
{
  "name": "generate_trading_recommendations",
  "description": "Analyze portfolio data, market signals, technical indicators, user-defined risk parameters, and historical performance to generate structured and actionable trading recommendations for each asset or aggregate portfolio position.",
  "strict": true,
  "parameters": {
    "type": "object",
    "properties": {
      "portfolio": {
        "type": "array",
        "description": "Array of assets or positions to be analyzed. Each object includes an asset symbol or name and position details.",
        "items": {
          "type": "object",
          "properties": {
            "symbol": {
              "type": "string",
              "description": "Ticker symbol or asset name (e.g., 'RELIANCE', 'TCS', 'HDFCBANK')"
            },
            "qty": {
              "type": "number",
              "description": "Position size for the asset"
            },
            "current_price": {
              "type": "number",
              "description": "Current market price of the asset"
            },
            "avg_cost": {
              "type": "number",
              "description": "Average cost basis of the position"
            },
            "unrealized_pnl": {
              "type": "number",
              "description": "Unrealized profit/loss for the position"
            },
            "sector": {
              "type": "string",
              "description": "Sector classification of the asset"
            }
          },
          "required": ["symbol", "qty", "current_price", "avg_cost"],
          "additionalProperties": false
        }
      },
      "market_signals": {
        "type": "object",
        "description": "Current market trends, volatility, sentiment, and other relevant signals.",
        "properties": {
          "trend": {
            "type": "string",
            "description": "Current overall market trend",
            "enum": ["bullish", "bearish", "sideways"]
          },
          "volatility": {
            "type": "string",
            "description": "Market volatility status",
            "enum": ["low", "moderate", "high"]
          },
          "sentiment": {
            "type": "string",
            "description": "Prevailing market sentiment",
            "enum": ["positive", "negative", "neutral"]
          },
          "newsflow": {
            "type": "string",
            "description": "Summary of recent news impacting the market or specified assets"
          },
          "key_levels": {
            "type": "object",
            "description": "Important support and resistance levels",
            "properties": {
              "support": {
                "type": "number",
                "description": "Key support level"
              },
              "resistance": {
                "type": "number",
                "description": "Key resistance level"
              }
            }
          },
          "sector_performance": {
            "type": "object",
            "description": "Performance of different sectors",
            "additionalProperties": {
              "type": "string",
              "enum": ["outperforming", "underperforming", "neutral"]
            }
          }
        },
        "required": ["trend", "volatility", "sentiment", "newsflow"],
        "additionalProperties": false
      },
      "technical_indicators": {
        "type": "object",
        "description": "Technical indicators and signals relevant to analysis.",
        "properties": {
          "rsi": {
            "type": "object",
            "description": "Relative Strength Index values",
            "properties": {
              "nifty50": {"type": "number"},
              "banknifty": {"type": "number"},
              "portfolio_avg": {"type": "number"}
            }
          },
          "macd": {
            "type": "object",
            "description": "MACD indicator values",
            "properties": {
              "signal": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
              "strength": {"type": "string", "enum": ["strong", "moderate", "weak"]}
            }
          },
          "moving_averages": {
            "type": "object",
            "description": "Moving average crossovers",
            "properties": {
              "sma_20": {"type": "number"},
              "sma_50": {"type": "number"},
              "ema_12": {"type": "number"},
              "ema_26": {"type": "number"}
            }
          },
          "volume_analysis": {
            "type": "object",
            "description": "Volume-based indicators",
            "properties": {
              "volume_trend": {"type": "string", "enum": ["increasing", "decreasing", "stable"]},
              "vwap": {"type": "number"},
              "volume_ratio": {"type": "number"}
            }
          }
        },
        "required": ["rsi", "macd", "moving_averages"],
        "additionalProperties": false
      },
      "risk_parameters": {
        "type": "object",
        "description": "User-defined risk profile and tolerance.",
        "properties": {
          "risk_level": {
            "type": "string",
            "description": "Overall user risk level",
            "enum": ["conservative", "moderate", "aggressive"]
          },
          "max_drawdown": {
            "type": "number",
            "description": "Maximum acceptable portfolio drawdown percentage"
          },
          "stop_loss": {
            "type": "number",
            "description": "Stop-loss percentage per position"
          },
          "position_sizing": {
            "type": "string",
            "description": "Position sizing strategy",
            "enum": ["fixed_amount", "percentage_of_portfolio", "kelly_criterion"]
          },
          "max_position_size": {
            "type": "number",
            "description": "Maximum position size as percentage of portfolio"
          },
          "correlation_limit": {
            "type": "number",
            "description": "Maximum correlation between positions"
          }
        },
        "required": ["risk_level", "max_drawdown", "stop_loss"],
        "additionalProperties": false
      },
      "historical_performance": {
        "type": "object",
        "description": "Historical trading performance metrics.",
        "properties": {
          "win_rate": {
            "type": "number",
            "description": "Percentage of profitable trades"
          },
          "avg_win": {
            "type": "number",
            "description": "Average profit per winning trade"
          },
          "avg_loss": {
            "type": "number",
            "description": "Average loss per losing trade"
          },
          "profit_factor": {
            "type": "number",
            "description": "Ratio of gross profit to gross loss"
          },
          "sharpe_ratio": {
            "type": "number",
            "description": "Risk-adjusted return metric"
          },
          "max_drawdown_historical": {
            "type": "number",
            "description": "Historical maximum drawdown"
          },
          "total_trades": {
            "type": "number",
            "description": "Total number of trades"
          }
        },
        "required": ["win_rate", "avg_win", "avg_loss"],
        "additionalProperties": false
      }
    },
    "required": ["portfolio", "market_signals", "technical_indicators", "risk_parameters", "historical_performance"],
    "additionalProperties": false
  }
}
```

---

## 📊 **Expected Response Format**

### **Structured Trading Recommendations Response**
```json
{
  "recommendations": [
    {
      "symbol": "RELIANCE",
      "action": "HOLD",
      "confidence": 0.75,
      "reasoning": "Strong technical support at current levels, RSI oversold",
      "entry_price": 2450,
      "stop_loss": 2400,
      "target": 2550,
      "timeframe": "1-2 weeks",
      "position_size": "5% of portfolio",
      "risk_reward": 2.0
    },
    {
      "symbol": "TCS",
      "action": "BUY",
      "confidence": 0.85,
      "reasoning": "Breakout above resistance with high volume",
      "entry_price": 3850,
      "stop_loss": 3750,
      "target": 4000,
      "timeframe": "3-5 days",
      "position_size": "3% of portfolio",
      "risk_reward": 1.5
    }
  ],
  "portfolio_analysis": {
    "overall_health": 7.5,
    "risk_level": "moderate",
    "diversification_score": 8.0,
    "sector_exposure": {
      "technology": "25%",
      "banking": "30%",
      "energy": "20%",
      "others": "25%"
    }
  },
  "market_context": {
    "trend": "bullish",
    "volatility": "moderate",
    "key_levels": {
      "support": 19200,
      "resistance": 19800
    }
  },
  "risk_assessment": {
    "portfolio_risk": "medium",
    "max_potential_loss": "8%",
    "expected_return": "12-15%",
    "var_95": "5%"
  }
}
```

---

## 🔧 **Integration with OpenAI Assistants API**

### **1. Function Definition in Assistant**
```python
# Define the function for OpenAI Assistant
trading_function = {
    "type": "function",
    "function": {
        "name": "generate_trading_recommendations",
        "description": "Generate structured trading recommendations based on portfolio and market data",
        "parameters": {
            # Your refined schema here
        }
    }
}

# Add to assistant tools
assistant = await client.beta.assistants.create(
    name="Quantum Leap Trading Assistant",
    instructions="You are an expert AI trading assistant...",
    model="gpt-4",
    tools=[
        {"type": "code_interpreter"},
        trading_function,
        {"type": "function", "function": "analyze_portfolio"},
        {"type": "function", "function": "get_market_data"}
    ]
)
```

### **2. Backend Integration**
```python
class TradingRecommendationsService:
    def __init__(self, openai_client):
        self.client = openai_client
        self.assistant_id = "asst_quantum_trading"
    
    async def generate_recommendations(self, user_id: str, portfolio_data: dict) -> dict:
        """Generate trading recommendations using OpenAI Assistant"""
        
        # Prepare function parameters
        function_params = {
            "portfolio": self.format_portfolio_data(portfolio_data),
            "market_signals": await self.get_market_signals(),
            "technical_indicators": await self.get_technical_indicators(),
            "risk_parameters": await self.get_user_risk_parameters(user_id),
            "historical_performance": await self.get_historical_performance(user_id)
        }
        
        # Create thread and run assistant
        thread = await self.client.beta.threads.create()
        
        # Add user message with function call
        await self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Generate trading recommendations for my portfolio"
        )
        
        # Run assistant with function calling
        run = await self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions="Use the generate_trading_recommendations function to analyze the portfolio"
        )
        
        # Wait for completion and extract recommendations
        response = await self.wait_for_run_completion(thread.id, run.id)
        return self.parse_recommendations_response(response)
    
    def format_portfolio_data(self, portfolio_data: dict) -> list:
        """Format portfolio data for function parameters"""
        formatted = []
        for holding in portfolio_data.get('holdings', []):
            formatted.append({
                "symbol": holding['tradingsymbol'],
                "qty": holding['quantity'],
                "current_price": holding['last_price'],
                "avg_cost": holding['average_price'],
                "unrealized_pnl": holding['pnl'],
                "sector": holding.get('sector', 'unknown')
            })
        return formatted
```

### **3. Frontend Integration**
```javascript
// React hook for trading recommendations
const useTradingRecommendations = () => {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const generateRecommendations = async (portfolioData) => {
    setLoading(true);
    try {
      const response = await railwayAPI.request('/ai/trading/recommendations', {
        method: 'POST',
        body: JSON.stringify({ portfolio_data: portfolioData })
      });
      
      setRecommendations(response.data.recommendations);
    } catch (error) {
      console.error('Failed to generate recommendations:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return { recommendations, loading, generateRecommendations };
};

// Component to display recommendations
const TradingRecommendationsPanel = ({ portfolioData }) => {
  const { recommendations, loading, generateRecommendations } = useTradingRecommendations();
  
  useEffect(() => {
    if (portfolioData) {
      generateRecommendations(portfolioData);
    }
  }, [portfolioData]);
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Trading Recommendations</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div>Generating recommendations...</div>
        ) : (
          <div className="space-y-4">
            {recommendations?.map((rec, index) => (
              <div key={index} className="p-4 border rounded-lg">
                <div className="flex justify-between items-center">
                  <h3 className="font-bold">{rec.symbol}</h3>
                  <Badge className={getActionColor(rec.action)}>
                    {rec.action}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 mt-2">{rec.reasoning}</p>
                <div className="grid grid-cols-2 gap-4 mt-3">
                  <div>
                    <span className="text-xs text-gray-500">Entry:</span>
                    <span className="ml-2 font-medium">₹{rec.entry_price}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Target:</span>
                    <span className="ml-2 font-medium">₹{rec.target}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Stop Loss:</span>
                    <span className="ml-2 font-medium">₹{rec.stop_loss}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500">Confidence:</span>
                    <span className="ml-2 font-medium">{rec.confidence * 100}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
```

---

## 🎯 **Key Benefits of This Integration**

### **1. Structured Analysis**
- ✅ **Comprehensive Input**: Portfolio, market signals, technical indicators, risk parameters
- ✅ **Structured Output**: Clear recommendations with specific actions and metrics
- ✅ **Risk Management**: Built-in risk assessment and position sizing

### **2. AI-Powered Insights**
- ✅ **Contextual Analysis**: Considers market conditions and user preferences
- ✅ **Technical Validation**: Uses multiple technical indicators
- ✅ **Risk-Adjusted Recommendations**: Respects user risk tolerance

### **3. User Experience**
- ✅ **Actionable Recommendations**: Specific entry, exit, and position sizes
- ✅ **Confidence Levels**: Clear indication of recommendation strength
- ✅ **Timeframes**: Specific holding periods for each recommendation

### **4. Integration Benefits**
- ✅ **OpenAI Assistants API**: Leverages persistent conversations and tools
- ✅ **BYOAI Architecture**: Maintains user control over AI providers
- ✅ **Real-time Data**: Integrates with live portfolio and market data
- ✅ **Learning System**: Improves recommendations based on historical performance

---

This function schema provides a robust foundation for generating intelligent, actionable trading recommendations that integrate seamlessly with your Quantum Leap Trading platform and OpenAI Assistants API. 