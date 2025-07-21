# QuantumLeap Trading Backend

A comprehensive AI-powered trading and portfolio management backend system built with FastAPI, featuring advanced AI capabilities, risk management, and cost optimization.

## 🚀 Features

### Core AI Engine
- **Multi-Provider AI Support**: OpenAI, Claude, Gemini, and Grok integration
- **Intelligent Provider Selection**: Automatic provider selection based on performance and cost
- **Real-time Chat Engine**: Context-aware AI conversations about your portfolio
- **Signal Generation**: AI-generated trading signals with confidence scoring and validation
- **Strategy Creation**: Automated trading strategy generation, backtesting, and optimization
- **Portfolio Analysis**: Technical, fundamental, and sentiment analysis

### Advanced Capabilities
- **Risk Management**: Portfolio risk assessment, position sizing, and trade validation
- **Cost Optimization**: AI provider cost tracking, budget management, and optimization
- **Learning System**: Adaptive AI that learns from feedback and trading outcomes
- **Error Handling**: Comprehensive error tracking, monitoring, and recovery
- **Performance Monitoring**: Real-time system health and performance metrics

### Integrations
- **Broker Integration**: Zerodha Kite API for live trading
- **Database**: SQLite with encrypted sensitive data storage
- **Authentication**: Secure user management and API key handling

## 📋 Quick Start

### Prerequisites

- Python 3.8+
- SQLite (included)
- At least one AI Provider API Key

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/JagPat/quantumleap-trading-backend.git
cd quantumleap-trading-backend
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp env.example .env
# Edit .env with your configuration
```

4. **Initialize the database:**
```bash
python -c "from app.database.service import init_database; init_database()"
```

5. **Run the application:**
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## 📚 Documentation

- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Comprehensive API Reference**: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Architecture Documentation**: [docs/AI_ENGINE_ARCHITECTURE.md](docs/AI_ENGINE_ARCHITECTURE.md)

## 🏗️ Architecture

```
app/
├── ai_engine/              # AI processing components
│   ├── providers/          # AI provider implementations
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   ├── gemini_provider.py
│   │   └── grok_provider.py
│   ├── chat_engine.py      # Real-time chat system
│   ├── signal_*.py         # Signal generation system
│   ├── strategy_*.py       # Strategy creation system
│   ├── analysis_*.py       # Portfolio analysis engine
│   ├── cost_optimizer.py   # Cost optimization system
│   ├── risk_manager.py     # Risk management system
│   ├── learning_system.py  # Adaptive learning system
│   ├── error_handler.py    # Error handling and monitoring
│   └── orchestrator.py     # AI provider orchestration
├── auth/                   # Authentication system
├── broker/                 # Broker integrations
├── database/               # Database operations
├── portfolio/              # Portfolio management
└── core/                   # Core utilities and configuration
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
DATABASE_PATH=./quantum_leap.db
ENCRYPTION_KEY=your-32-character-encryption-key

# AI Providers (configure at least one)
OPENAI_API_KEY=sk-your-openai-key
CLAUDE_API_KEY=your-claude-key
GEMINI_API_KEY=your-gemini-key
GROK_API_KEY=your-grok-key

# Broker Integration
ZERODHA_API_KEY=your-zerodha-key
ZERODHA_API_SECRET=your-zerodha-secret

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
```

### AI Provider Setup

| Provider | Setup Link | Features |
|----------|------------|----------|
| **OpenAI** | [Platform](https://platform.openai.com/) | GPT-4, GPT-3.5, Function calling |
| **Claude** | [Console](https://console.anthropic.com/) | Claude-3, Long context, Analysis |
| **Gemini** | [AI Studio](https://makersuite.google.com/) | Gemini Pro, Multimodal, Fast |
| **Grok** | [xAI Platform](https://x.ai/) | Real-time data, Twitter integration |

## 🔧 Usage Examples

### Generate Trading Signals

```python
import requests

# Get current signals
response = requests.get(
    "http://localhost:8000/api/ai/signals",
    headers={"X-User-ID": "your_user_id"}
)
signals = response.json()

# Generate new signals
response = requests.post(
    "http://localhost:8000/api/ai/signals/generate",
    json={
        "symbols": ["RELIANCE", "TCS", "HDFCBANK"],
        "signal_type": "buy"
    },
    headers={"X-User-ID": "your_user_id"}
)
```

### Create Trading Strategy

```python
strategy_params = {
    "strategy_type": "momentum",
    "risk_tolerance": "medium",
    "time_horizon": "medium",
    "target_symbols": ["NIFTY50"],
    "capital_allocation": 0.8,
    "max_drawdown": 0.15
}

response = requests.post(
    "http://localhost:8000/api/ai/strategy/generate",
    json={"parameters": strategy_params},
    headers={"X-User-ID": "your_user_id"}
)
strategy = response.json()
```

### AI Chat Interaction

```python
# Send message to AI
response = requests.post(
    "http://localhost:8000/api/ai/chat/message",
    json={
        "message": "Analyze my portfolio risk and suggest improvements",
        "context": {"include_recommendations": True}
    },
    headers={"X-User-ID": "your_user_id"}
)
chat_response = response.json()
```

### Risk Assessment

```python
# Assess portfolio risk
portfolio_data = {
    "total_value": 1000000,
    "holdings": [
        {"symbol": "RELIANCE", "current_value": 200000, "sector": "Energy"},
        {"symbol": "TCS", "current_value": 150000, "sector": "IT"}
    ]
}

response = requests.post(
    "http://localhost:8000/api/ai/risk-cost/portfolio/assess",
    json={"portfolio_data": portfolio_data},
    headers={"X-User-ID": "your_user_id"}
)
risk_assessment = response.json()
```

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage
python scripts/run_tests.py --type all --coverage --verbose

# Run specific test categories
python scripts/run_tests.py --type unit          # Unit tests only
python scripts/run_tests.py --type integration  # Integration tests only
python scripts/run_tests.py --type existing     # Existing tests only

# Run specific component tests
python scripts/run_tests.py --type cost_optimizer
python scripts/run_tests.py --type risk_manager
python scripts/run_tests.py --type learning_system
```

### Test Coverage

The test suite includes:
- **Unit Tests**: Individual component functionality
- **Integration Tests**: Cross-component workflows
- **Error Handling Tests**: Failure scenarios and recovery
- **Performance Tests**: Response times and load handling
- **Database Tests**: Data persistence and retrieval

## 🚀 Deployment

### Railway (Production)

1. **Connect Repository**: Link your GitHub repo to Railway
2. **Set Environment Variables**: Configure in Railway dashboard
3. **Auto-Deploy**: Pushes to main branch trigger deployment

Current Production URL: `https://web-production-de0bc.up.railway.app`

### Docker Deployment

```bash
# Build image
docker build -t quantumleap-backend .

# Run container
docker run -p 8000:8000 --env-file .env quantumleap-backend
```

### Manual Deployment

```bash
# Production server
pip install -r requirements.txt
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📊 Monitoring & Health

### System Health Endpoints

```bash
# Overall system health
GET /health

# AI engine health
GET /api/ai/monitoring/health/system

# User-specific health
GET /api/ai/monitoring/health/user

# Error summary
GET /api/ai/monitoring/errors/summary

# Performance metrics
GET /api/ai/monitoring/performance/ai-providers
```

### Key Metrics Tracked

- **Response Times**: API endpoint performance
- **Success Rates**: AI provider reliability
- **Cost Tracking**: AI usage and spending
- **Error Rates**: System stability monitoring
- **User Activity**: Engagement and usage patterns

## 🔒 Security Features

- **API Key Encryption**: Sensitive data encrypted at rest
- **User Isolation**: Per-user data separation
- **Rate Limiting**: Prevents abuse and controls costs
- **Error Handling**: Graceful failure without data exposure
- **Audit Logging**: Comprehensive activity tracking

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature-name`
3. **Implement** your changes with tests
4. **Test** your changes: `python scripts/run_tests.py`
5. **Commit** your changes: `git commit -am 'Add feature'`
6. **Push** to branch: `git push origin feature-name`
7. **Create** a Pull Request

### Development Guidelines

- Write comprehensive tests for new features
- Follow existing code style and patterns
- Update documentation for API changes
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **API Reference**: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Issues**: [GitHub Issues](https://github.com/JagPat/quantumleap-trading-backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JagPat/quantumleap-trading-backend/discussions)

## 🎯 Roadmap

- [ ] WebSocket real-time updates
- [ ] Advanced backtesting engine
- [ ] Mobile app API endpoints
- [ ] Multi-broker support
- [ ] Advanced ML models
- [ ] Social trading features

---

**Built with ❤️ for traders who want AI-powered insights and automation.**