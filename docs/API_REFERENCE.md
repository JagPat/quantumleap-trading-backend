# QuantumLeap Trading Backend - AI Engine API Reference

## Overview

The QuantumLeap AI Engine provides comprehensive AI-powered trading capabilities including signal generation, strategy creation, portfolio analysis, risk management, cost optimization, and learning systems.

## Base URL
```
Production: https://web-production-de0bc.up.railway.app
```

## Authentication

All API endpoints require user identification through headers:

```http
X-User-ID: your_user_id
Content-Type: application/json
```

## API Endpoints

### 1. AI Chat Engine (`/api/ai/chat`)

#### Send Message
```http
POST /api/ai/chat/message
```

**Request Body:**
```json
{
  "message": "How is my portfolio performing?",
  "thread_id": "optional_thread_id",
  "context": {
    "additional": "context"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "reply": "Your portfolio is performing well...",
  "thread_id": "chat_user_1234567890",
  "message_id": "msg_123",
  "provider_used": "openai",
  "tokens_used": 150,
  "cost_cents": 30
}
```

#### Get Chat Sessions
```http
GET /api/ai/chat/sessions
```

**Response:**
```json
[
  {
    "id": 1,
    "thread_id": "chat_user_1234567890",
    "session_name": null,
    "created_at": "2025-07-21T10:30:00Z",
    "updated_at": "2025-07-21T11:00:00Z",
    "is_active": true
  }
]
```

### 2. Signal Generation (`/api/ai/signals`)

#### Get Current Signals
```http
GET /api/ai/signals
```

**Query Parameters:**
- `active_only` (boolean): Only return active signals
- `limit` (integer): Maximum number of signals to return

**Response:**
```json
{
  "status": "success",
  "signals": [
    {
      "id": "signal_123",
      "symbol": "RELIANCE",
      "signal_type": "buy",
      "confidence_score": 0.85,
      "reasoning": "Strong technical indicators and positive sentiment",
      "target_price": 2650.0,
      "stop_loss": 2400.0,
      "take_profit": 2800.0,
      "position_size": 0.08,
      "expires_at": "2025-07-22T10:30:00Z",
      "created_at": "2025-07-21T10:30:00Z"
    }
  ]
}
```

#### Generate New Signals
```http
POST /api/ai/signals/generate
```

**Request Body:**
```json
{
  "symbols": ["RELIANCE", "TCS", "HDFCBANK"],
  "signal_type": "buy",
  "portfolio_data": {
    "total_value": 1000000,
    "holdings": []
  }
}
```

### 3. Strategy Generation (`/api/ai/strategies`)

#### Generate Strategy
```http
POST /api/ai/strategy/generate
```

**Request Body:**
```json
{
  "parameters": {
    "strategy_type": "momentum",
    "risk_tolerance": "medium",
    "time_horizon": "medium",
    "target_symbols": ["NIFTY50"],
    "capital_allocation": 0.8,
    "max_drawdown": 0.15
  },
  "portfolio_data": {
    "total_value": 1000000,
    "holdings": []
  }
}
```

**Response:**
```json
{
  "status": "success",
  "strategy": {
    "id": "strategy_123",
    "name": "Momentum Strategy - Medium Risk",
    "type": "momentum",
    "description": "A momentum-based strategy targeting medium-term gains",
    "entry_rules": [
      "RSI > 60 and price above 20-day MA",
      "Volume > 1.5x average volume"
    ],
    "exit_rules": [
      "RSI < 40 or price below 20-day MA",
      "Stop loss at 8% below entry"
    ],
    "risk_management": {
      "max_position_size": 0.1,
      "stop_loss_percentage": 0.08,
      "take_profit_percentage": 0.15
    },
    "is_active": false,
    "created_at": "2025-07-21T10:30:00Z"
  }
}
```

### 4. Analysis Engine (`/api/ai/analysis`)

#### Request Analysis
```http
POST /api/ai/analysis/request
```

**Request Body:**
```json
{
  "analysis_type": "technical",
  "symbols": ["RELIANCE", "TCS"],
  "timeframe": "1d",
  "parameters": {
    "indicators": ["RSI", "MACD", "SMA"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_type": "technical",
  "symbols": ["RELIANCE", "TCS"],
  "results": {
    "RELIANCE": {
      "trend": "bullish",
      "indicators": {
        "RSI": 65.5,
        "MACD": "positive_crossover",
        "SMA_20": 2580.0
      },
      "recommendation": "buy",
      "confidence": 0.78
    }
  },
  "confidence_score": 0.78,
  "provider_used": "openai",
  "created_at": "2025-07-21T10:30:00Z"
}
```

### 5. Risk Management (`/api/ai/risk-cost`)

#### Assess Portfolio Risk
```http
POST /api/ai/risk-cost/portfolio/assess
```

**Request Body:**
```json
{
  "portfolio_data": {
    "total_value": 1000000,
    "holdings": [
      {
        "symbol": "RELIANCE",
        "current_value": 200000,
        "sector": "Energy"
      }
    ]
  }
}
```

**Response:**
```json
{
  "user_id": "test_user",
  "overall_risk": "medium",
  "risk_score": 45,
  "risk_factors": [
    {
      "risk_type": "concentration",
      "risk_level": "medium",
      "max_concentration": 0.2,
      "recommendations": ["Consider reducing position sizes"]
    }
  ],
  "recommendations": ["Diversify portfolio across more positions"],
  "portfolio_summary": {
    "total_value": 1000000,
    "holdings_count": 5,
    "diversification_score": 65
  }
}
```

#### Validate Trade Risk
```http
POST /api/ai/risk-cost/trade/validate
```

**Request Body:**
```json
{
  "trade_data": {
    "symbol": "TCS",
    "amount": 80000,
    "type": "buy"
  },
  "portfolio_data": {
    "total_value": 1000000,
    "holdings": []
  }
}
```

### 6. Cost Optimization (`/api/ai/risk-cost`)

#### Check Cost Limits
```http
POST /api/ai/risk-cost/cost/check-limits
```

**Request Body:**
```json
{
  "provider": "openai",
  "estimated_cost_cents": 200
}
```

**Response:**
```json
{
  "within_limits": true,
  "current_cost_cents": 500,
  "estimated_cost_cents": 200,
  "projected_cost_cents": 700,
  "daily_limit_cents": 1000,
  "usage_percentage": 0.7,
  "alert_level": "medium",
  "remaining_budget_cents": 300
}
```

#### Get Cost Report
```http
GET /api/ai/risk-cost/cost/report?days=30
```

**Response:**
```json
{
  "user_id": "test_user",
  "report_period_days": 30,
  "summary": {
    "total_cost_cents": 1500,
    "total_requests": 50,
    "total_tokens": 10000,
    "daily_average_cents": 50,
    "monthly_projection_cents": 1500
  },
  "provider_breakdown": [
    {
      "provider": "openai",
      "requests": 25,
      "total_cost_cents": 800,
      "success_rate": 95.0
    }
  ],
  "optimization_suggestions": [
    {
      "type": "provider_optimization",
      "message": "Consider using claude more often"
    }
  ]
}
```

### 7. Learning System (`/api/ai/learning`)

#### Submit Feedback
```http
POST /api/ai/learning/feedback
```

**Request Body:**
```json
{
  "feedback_type": "signal_accuracy",
  "item_id": "signal_123",
  "rating": 4,
  "comments": "Signal was accurate",
  "metadata": {
    "provider_used": "openai"
  }
}
```

#### Record Trade Outcome
```http
POST /api/ai/learning/trade-outcome
```

**Request Body:**
```json
{
  "signal_id": "signal_123",
  "outcome_type": "profit",
  "pnl_amount": 2000.0,
  "execution_price": 105.50,
  "metadata": {
    "execution_time": "2025-07-21T10:30:00Z"
  }
}
```

#### Get Learning Insights
```http
GET /api/ai/learning/insights
```

**Response:**
```json
{
  "user_id": "test_user",
  "insights": [
    {
      "type": "best_provider",
      "message": "claude has the highest accuracy (85%)",
      "data": {
        "overall_accuracy": 0.85
      }
    }
  ],
  "recommendations": [
    "Consider using claude more frequently for better results"
  ],
  "learning_status": {
    "total_feedback": 15,
    "learning_active": true,
    "providers_analyzed": 3
  }
}
```

### 8. Error Monitoring (`/api/ai/monitoring`)

#### Get System Health
```http
GET /api/ai/monitoring/health/system
```

**Response:**
```json
{
  "health_status": "healthy",
  "error_counts_1h": {
    "medium": 2,
    "low": 5
  },
  "active_alerts": 0,
  "total_errors_24h": 12,
  "timestamp": "2025-07-21T10:30:00Z"
}
```

#### Get Error Summary
```http
GET /api/ai/monitoring/errors/summary?hours=24
```

**Response:**
```json
{
  "user_id": "test_user",
  "period_hours": 24,
  "total_errors": 5,
  "error_breakdown": [
    {
      "category": "api_error",
      "severity": "medium",
      "count": 3,
      "last_occurrence": "2025-07-21T09:30:00Z"
    }
  ],
  "active_alerts": [],
  "health_status": "healthy"
}
```

## Error Handling

All endpoints return consistent error responses:

```json
{
  "status": "error",
  "message": "Detailed error message",
  "error_code": "OPTIONAL_ERROR_CODE",
  "retry_after": 60
}
```

## Rate Limiting

- Default rate limit: 100 requests per minute per user
- Cost-based limiting: Requests may be throttled based on AI provider costs
- Rate limit headers are included in responses

## Data Models

### Signal Model
```json
{
  "id": "string",
  "symbol": "string",
  "signal_type": "buy|sell|hold",
  "confidence_score": "number (0.0-1.0)",
  "reasoning": "string",
  "target_price": "number|null",
  "stop_loss": "number|null",
  "take_profit": "number|null",
  "position_size": "number|null",
  "expires_at": "datetime|null",
  "created_at": "datetime"
}
```

### Portfolio Model
```json
{
  "total_value": "number",
  "holdings": [
    {
      "symbol": "string",
      "current_value": "number",
      "sector": "string"
    }
  ]
}
```

### Strategy Model
```json
{
  "id": "string",
  "name": "string",
  "type": "momentum|mean_reversion|breakout|scalping|swing|long_term",
  "description": "string",
  "entry_rules": ["string"],
  "exit_rules": ["string"],
  "risk_management": "object",
  "parameters": "object",
  "is_active": "boolean",
  "created_at": "datetime"
}
```

## WebSocket Support

Real-time updates are available through WebSocket connections:

```javascript
const ws = new WebSocket('wss://web-production-de0bc.up.railway.app/ws');

// Subscribe to signals
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'signals',
  user_id: 'your_user_id'
}));
```

## SDK Examples

### Python
```python
import requests

class QuantumLeapClient:
    def __init__(self, base_url, user_id):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'X-User-ID': user_id
        }
    
    def get_signals(self):
        response = requests.get(
            f"{self.base_url}/api/ai/signals",
            headers=self.headers
        )
        return response.json()
    
    def generate_strategy(self, parameters):
        response = requests.post(
            f"{self.base_url}/api/ai/strategy/generate",
            json={"parameters": parameters},
            headers=self.headers
        )
        return response.json()

# Usage
client = QuantumLeapClient(
    "https://web-production-de0bc.up.railway.app",
    "your_user_id"
)
signals = client.get_signals()
```

### JavaScript
```javascript
class QuantumLeapClient {
    constructor(baseUrl, userId) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json',
            'X-User-ID': userId
        };
    }
    
    async getSignals() {
        const response = await fetch(`${this.baseUrl}/api/ai/signals`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async generateStrategy(parameters) {
        const response = await fetch(`${this.baseUrl}/api/ai/strategy/generate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ parameters })
        });
        return response.json();
    }
}

// Usage
const client = new QuantumLeapClient(
    'https://web-production-de0bc.up.railway.app',
    'your_user_id'
);
const signals = await client.getSignals();
```

## Support

For API support and questions:
- Documentation: [GitHub Repository](https://github.com/JagPat/quantumleap-trading-backend)
- Issues: Create an issue on GitHub
- Email: Support contact information