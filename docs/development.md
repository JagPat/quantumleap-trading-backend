# Development Guide

## 🛠️ **Local Development Setup**

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/JagPat/quantumleap-trading-backend.git
   cd quantumleap-trading-backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file with your configuration:
   ```bash
   # Generate encryption key
   python scripts/generate_key.py
   ```

5. **Start the development server**:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

## 🧪 **Testing**

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=app

# Run specific test file
python -m pytest tests/test_ai_engine.py

# Run integration tests
python -m pytest tests/integration/
```

### Test Structure
```
tests/
├── conftest.py                 # Test configuration
├── test_ai_engine.py          # AI engine tests
├── test_auth.py               # Authentication tests
├── test_database.py           # Database tests
├── test_portfolio.py          # Portfolio tests
└── integration/
    └── test_end_to_end.py     # End-to-end tests
```

## 🏗️ **Architecture Overview**

### Application Structure
```
app/
├── ai_engine/          # AI provider management
│   ├── simple_router.py    # Current AI endpoints
│   └── router.py          # Alternative AI endpoints
├── auth/              # Authentication
│   └── router.py          # Auth endpoints
├── broker/            # Broker integration
│   └── router.py          # Broker endpoints
├── core/              # Core configuration
│   └── config.py          # Settings management
├── database/          # Database services
│   └── service.py         # Database operations
└── portfolio/         # Portfolio management
    ├── router.py          # Portfolio endpoints
    └── service.py         # Portfolio logic
```

### Database Schema
- `users` - User credentials (encrypted)
- `portfolio_snapshots` - Portfolio data storage
- `ai_user_preferences` - AI API keys and preferences

## 🔧 **Development Workflow**

### Adding New Features

1. **Create feature branch**:
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement feature**:
   - Add new endpoints to appropriate router
   - Add business logic to service modules
   - Update database schema if needed
   - Add comprehensive tests

3. **Test thoroughly**:
   ```bash
   python -m pytest tests/
   ```

4. **Update documentation**:
   - Update API documentation
   - Add usage examples
   - Update README if needed

5. **Submit pull request**

### Code Style Guidelines

- Use Python type hints
- Follow PEP 8 style guide
- Add docstrings to all functions
- Use meaningful variable names
- Keep functions small and focused

### Database Migrations

When adding new database tables or columns:

1. Update `app/database/service.py`
2. Add migration function in `init_database()`
3. Test migration with existing data
4. Update database tests

## 🚀 **Deployment**

### Railway Deployment

The application is configured for automatic Railway deployment:

1. **Environment Variables** (set in Railway dashboard):
   ```
   ENCRYPTION_KEY=your-encryption-key
   SESSION_SECRET=your-session-secret
   FRONTEND_URL=your-frontend-url
   ```

2. **Deployment Files**:
   - `deployment/railway.json` - Railway configuration
   - `deployment/Procfile` - Process configuration
   - `deployment/runtime.txt` - Python version
   - `deployment/.nixpacks.toml` - Build configuration

### Manual Deployment

For other platforms:

1. **Set environment variables**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Run application**: `python main.py`

## 🐛 **Debugging**

### Common Issues

1. **Database Errors**:
   - Check file permissions
   - Verify encryption key is set
   - Check disk space

2. **API Key Validation Errors**:
   - Verify API keys are valid
   - Check network connectivity
   - Review provider-specific requirements

3. **Import Errors**:
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check Python version compatibility

### Logging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Monitor application health:
- `GET /health` - Basic health check
- `GET /readyz` - Readiness check
- `GET /version` - Version and deployment info

## 📊 **Performance Monitoring**

### Key Metrics to Monitor

- API response times
- Database query performance
- AI provider response times
- Error rates and types
- Memory and CPU usage

### Optimization Tips

- Use database indexes for frequent queries
- Implement caching for expensive operations
- Monitor AI provider costs and usage
- Optimize database queries
- Use connection pooling for external APIs

## 🔐 **Security Considerations**

### Best Practices

- Never commit API keys or secrets
- Use environment variables for configuration
- Encrypt sensitive data before storage
- Validate all user inputs
- Implement proper error handling
- Use HTTPS in production
- Regular security updates

### API Key Management

- Store API keys encrypted in database
- Validate keys before use
- Implement key rotation capabilities
- Monitor for suspicious usage patterns

## 📚 **Additional Resources**

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Zerodha Kite Connect API](https://kite.trade/docs/connect/v3/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Google Gemini API](https://ai.google.dev/docs)