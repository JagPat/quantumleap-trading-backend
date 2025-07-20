# QuantumLeap Trading Backend

A FastAPI-based backend service for the QuantumLeap Trading Platform with BYOAI (Bring Your Own AI) capabilities.

## 🚀 **Features**

- **BYOAI System**: Support for OpenAI, Claude, Gemini, and Grok
- **Portfolio Management**: Real-time portfolio tracking and analysis
- **Broker Integration**: Zerodha Kite Connect API integration
- **AI-Powered Analysis**: Market analysis, strategy generation, and trading signals
- **Secure Storage**: Encrypted credential storage with SQLite
- **RESTful API**: Clean, well-documented API endpoints

## 🏗️ **Architecture**

```
app/
├── ai_engine/          # AI provider management and orchestration
├── auth/              # Authentication and OAuth handling
├── broker/            # Broker API integration
├── core/              # Core configuration and utilities
├── database/          # Database services and models
├── portfolio/         # Portfolio management and analytics
└── trading/           # Trading operations and strategies
```

## 📚 **Documentation**

- [AI Engine Architecture](docs/AI_ENGINE_ARCHITECTURE.md) - Comprehensive AI system design
- [API Documentation](docs/README.md) - Detailed API reference
- [Development Guide](docs/development.md) - Setup and development instructions

## 🧪 **Testing**

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m pytest tests/test_ai_engine.py
python -m pytest tests/test_portfolio.py
```

## 🛠️ **Development**

### Prerequisites
- Python 3.8+
- pip package manager

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env.example .env
# Edit .env with your configuration

# Run the server
python main.py
```

### API Documentation
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 🚀 **Deployment**

The application is configured for Railway deployment with automatic builds.

### Environment Variables
- `ENCRYPTION_KEY` - Database encryption key
- `SESSION_SECRET` - OAuth session secret
- `FRONTEND_URL` - Frontend URL for CORS

## 📁 **Project Structure**

```
quantumleap-trading-backend/
├── app/                    # Main application
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── deployment/             # Deployment configurations
├── main.py                 # Application entry point
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## 🔐 **Security**

- All sensitive data is encrypted before storage
- API keys are validated before use
- Comprehensive error handling without data exposure
- CORS configuration for production deployment

## 📊 **API Endpoints**

### Health & Status
- `GET /health` - Health check
- `GET /version` - Version information
- `GET /readyz` - Readiness check

### AI Engine
- `GET /api/ai/status` - AI engine status
- `GET /api/ai/preferences` - Get AI preferences
- `POST /api/ai/preferences` - Save AI preferences
- `POST /api/ai/validate-key` - Validate API keys

### Portfolio
- `GET /api/portfolio/latest-simple` - Get latest portfolio
- `POST /api/portfolio/fetch-live-simple` - Fetch live portfolio
- `GET /api/portfolio/status` - Portfolio service status

### Broker
- `GET /api/broker/status` - Broker connection status
- `POST /api/broker/session/create` - Create session
- `POST /api/broker/session/validate` - Validate session

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License.