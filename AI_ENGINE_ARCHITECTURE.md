# AI Engine Architecture Documentation

## Overview
The AI Engine is a comprehensive, scalable system for AI-powered trading analysis, strategy generation, and signal generation. It acts as the "thinking brain" between raw market data and trading execution.

## Architecture Principles
- **Clean Separation**: AI logic completely isolated from broker and portfolio modules
- **Provider Agnostic**: Unified interface supporting OpenAI, Claude, and Gemini
- **Graceful Degradation**: System functions even when AI providers are unavailable
- **Cost Optimization**: Intelligent provider selection and usage tracking
- **Security First**: No hardcoded API keys, environment-based configuration

## Module Structure

```
app/ai_engine/
├── __init__.py              # Module initialization
├── router.py                # FastAPI endpoints
├── orchestrator.py          # Provider selection and coordination
├── preprocessor.py          # Data cleaning and prompt generation
├── providers/               # AI provider clients
│   ├── __init__.py
│   ├── base_provider.py     # Common interface
│   ├── openai_client.py     # OpenAI integration
│   ├── claude_client.py     # Anthropic Claude integration
│   └── gemini_client.py     # Google Gemini integration
├── memory/                  # Storage and logging
│   ├── __init__.py
│   └── strategy_store.py    # SQLite-based storage
└── schemas/                 # Data validation
    ├── __init__.py
    ├── requests.py          # Request models
    └── responses.py         # Response models
```

## Core Components

### 1. AI Orchestrator (`orchestrator.py`)
**Purpose**: Central coordinator for all AI operations

**Responsibilities**:
- Choose optimal AI provider for each task
- Load balance across available providers
- Handle provider fallbacks and errors
- Track usage and performance metrics
- Optimize costs through intelligent routing

**Key Features**:
- Provider preference strategies by analysis type
- Round-robin load balancing
- Real-time availability checking
- Comprehensive usage tracking

### 2. Data Preprocessor (`preprocessor.py`)
**Purpose**: Prepare raw data for AI consumption

**Responsibilities**:
- Clean and normalize portfolio data
- Format market data for analysis
- Generate context-rich prompts
- Handle data validation and sanitization

**Key Features**:
- Portfolio context preparation with risk metrics
- Market context formatting with timeframe support
- Dynamic prompt generation for different analysis types
- Data structure validation and error handling

### 3. AI Providers (`providers/`)
**Purpose**: Isolated client wrappers for different AI services

**Base Interface** (`base_provider.py`):
- Common interface for all providers
- Standardized error handling
- Consistent response validation
- Availability checking

**Provider Implementations**:
- **OpenAI Client**: GPT-4 for complex analysis, structured output support
- **Claude Client**: Strong analytical capabilities, large context window
- **Gemini Client**: Cost-effective option with multimodal capabilities

### 4. Strategy Store (`memory/strategy_store.py`)
**Purpose**: Persistent storage for AI operations

**Database Schema**:
- `ai_sessions`: Track AI session metadata
- `ai_interactions`: Log prompts and responses
- `generated_strategies`: Store AI-generated strategies
- `strategy_performance`: Track strategy performance metrics

**Features**:
- Session management and tracking
- Interaction logging for cost monitoring
- Strategy storage and retrieval
- Performance analytics and reporting

### 5. API Router (`router.py`)
**Purpose**: FastAPI endpoints for AI operations

**Endpoints**:
- `GET /api/ai/status` - AI engine status and provider availability
- `POST /api/ai/analysis` - Generate market analysis
- `POST /api/ai/strategy` - Generate trading strategies
- `POST /api/ai/signals` - Generate trading signals
- `GET /api/ai/strategies/{user_id}` - Get user strategies
- `GET /api/ai/sessions/{user_id}` - Get session history
- `GET /api/ai/statistics` - Usage statistics

## Data Flow

### Analysis Request Flow
```
1. User Request → API Router
2. Router → Authentication Check
3. Router → Orchestrator.generate_market_analysis()
4. Orchestrator → Choose Provider (based on analysis type)
5. Orchestrator → Preprocessor.prepare_market_context()
6. Orchestrator → Preprocessor.generate_analysis_prompt()
7. Orchestrator → Provider.generate_analysis()
8. Provider → AI Service (OpenAI/Claude/Gemini)
9. AI Service → Provider (with response)
10. Provider → Orchestrator (with processed response)
11. Orchestrator → Strategy Store (log interaction)
12. Orchestrator → Router (with final response)
13. Router → User (JSON response)
```

### Strategy Generation Flow
```
1. User Request → API Router
2. Router → Get Portfolio Data
3. Router → Orchestrator.generate_trading_strategy()
4. Orchestrator → Preprocessor.prepare_portfolio_context()
5. Orchestrator → Preprocessor.generate_strategy_prompt()
6. Orchestrator → Provider.generate_strategy()
7. Provider → AI Service (with enhanced prompts)
8. AI Service → Provider (with strategy JSON)
9. Provider → Orchestrator (with validated strategy)
10. Orchestrator → Strategy Store (store strategy)
11. Orchestrator → Router (with strategy + ID)
12. Router → User (complete strategy response)
```

## Provider Selection Strategy

### Analysis Type Preferences
- **Technical Analysis**: Claude → OpenAI → Gemini
- **Fundamental Analysis**: OpenAI → Claude → Gemini  
- **Sentiment Analysis**: Claude → Gemini → OpenAI
- **Strategy Generation**: OpenAI → Claude → Gemini
- **Portfolio Optimization**: Claude → OpenAI → Gemini

### Load Balancing
- Round-robin selection among available providers
- Least-recently-used algorithm for optimal distribution
- Usage tracking for performance monitoring
- Automatic failover on provider errors

## Security & Configuration

### API Key Management
```python
# Environment Variables Required:
OPENAI_API_KEY=sk-...        # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-... # Claude API key  
GOOGLE_API_KEY=AI...         # Gemini API key (or GEMINI_API_KEY)
```

### Security Features
- No hardcoded API keys anywhere in code
- Provider availability gracefully handled
- Comprehensive error logging (no sensitive data)
- User-scoped data access controls
- Input validation and sanitization

## Usage Examples

### Market Analysis Request
```python
POST /api/ai/analysis
{
    "user_id": "EBW183",
    "analysis_type": "technical",
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "timeframe": "1d",
    "provider": "auto"
}
```

### Strategy Generation Request
```python
POST /api/ai/strategy
{
    "user_id": "EBW183", 
    "strategy_prompt": "Create a momentum trading strategy for IT stocks",
    "risk_tolerance": "medium",
    "provider": "openai"
}
```

### Trading Signals Request
```python
POST /api/ai/signals
{
    "user_id": "EBW183",
    "symbols": ["RELIANCE", "HDFC", "ICICIBANK"],
    "signal_type": "buy_sell",
    "live_data": true
}
```

## Integration with Existing System

### Authentication
- Uses existing `get_current_user_from_auth_header` dependency
- User ID extracted from authenticated user context
- Same security model as portfolio and auth modules

### Portfolio Integration
- Automatically fetches user's portfolio data for context
- Integrates with existing portfolio service
- Uses portfolio data for strategy generation and analysis

### Database Integration
- Separate SQLite database (`ai_engine.db`) for AI operations
- Independent of main trading database
- Comprehensive logging and session tracking

## Performance & Monitoring

### Usage Tracking
- Request counts by provider and operation type
- Token usage monitoring for cost optimization
- Processing time tracking for performance analysis
- Session and interaction logging for debugging

### Cost Optimization
- Provider selection based on cost and performance
- Token usage tracking across all providers
- Usage statistics for budget planning
- Efficient prompt engineering to minimize costs

## Error Handling

### Graceful Degradation
- System continues to function when AI providers are unavailable
- Fallback to alternative providers when primary fails
- Comprehensive error messages without exposing sensitive data
- Logging for debugging and monitoring

### Provider Errors
- Network timeouts handled gracefully
- API rate limits respected with backoff
- Invalid responses processed with fallbacks
- Error reporting with provider-specific context

## Development Guidelines

### Adding New Providers
1. Create new client in `providers/` inheriting from `BaseAIProvider`
2. Implement required methods: `generate_analysis`, `generate_strategy`, `generate_signals`
3. Add provider to `AIProvider` enum in `schemas/requests.py`
4. Update orchestrator provider initialization
5. Add provider preferences for different analysis types

### Extending Functionality
1. Add new request/response schemas in `schemas/`
2. Implement new methods in orchestrator
3. Add new endpoints in router
4. Update provider interface if needed
5. Add tests and documentation

### Best Practices
- Always use the orchestrator, never call providers directly
- Log all interactions for monitoring and debugging
- Use Pydantic schemas for all data validation
- Handle errors gracefully with user-friendly messages
- Monitor token usage and costs regularly

## Testing & Deployment

### Local Development
1. Install AI provider libraries: `pip install openai anthropic google-generativeai`
2. Set environment variables for API keys
3. Run backend: `python main.py`
4. Test endpoints using `/docs` or API client

### Production Deployment
1. Set environment variables on Railway
2. Monitor AI provider costs and usage
3. Set up alerts for provider availability
4. Regular monitoring of token usage and performance

## Future Enhancements

### Planned Features
- Real-time market data integration
- Advanced backtesting with historical data
- Multi-model ensemble predictions
- Custom model fine-tuning
- Advanced risk management algorithms

### Scalability Considerations
- Provider connection pooling
- Caching for repeated analyses
- Asynchronous processing for long-running tasks
- Horizontal scaling with multiple orchestrator instances

This AI Engine provides a robust, scalable foundation for AI-powered trading analysis and strategy generation while maintaining clean architecture principles and operational excellence. 