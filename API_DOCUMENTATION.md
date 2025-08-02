# Quantum Leap Trading Platform API Documentation

## Overview
The Quantum Leap Trading Platform provides a comprehensive REST API for trading operations, AI analysis, and database optimization.

## Base URL
- Production: `https://your-railway-app.railway.app`
- Development: `http://localhost:8000`

## Authentication
Currently using basic authentication. JWT implementation coming soon.

## Core Endpoints

### Health Check
- `GET /` - Root endpoint with system status
- `GET /health` - Comprehensive health check

### Database Optimization Endpoints

#### Performance Monitoring
- `GET /api/database/performance` - Get database performance metrics
- `GET /api/database/dashboard` - Get performance dashboard data
- `GET /api/database/health` - Get database health status
- `GET /api/database/metrics/history?hours=24` - Get metrics history
- `GET /api/database/trading-metrics` - Get trading-specific metrics

#### Database Management
- `POST /api/database/backup` - Create database backup
- `POST /api/database/cleanup?days_to_keep=90` - Clean up old data

### Trading Engine Endpoints

#### Orders
- `GET /api/trading/orders/{user_id}?limit=100` - Get user orders
- `POST /api/trading/orders` - Create new order
- `PUT /api/trading/orders/{order_id}` - Update order
- `DELETE /api/trading/orders/{order_id}` - Cancel order

#### Positions
- `GET /api/trading/positions/{user_id}?include_closed=false` - Get user positions
- `POST /api/trading/positions/close` - Close position

#### Executions
- `GET /api/trading/executions/{user_id}?limit=100` - Get user executions

#### Signals
- `GET /api/trading/signals/{user_id}` - Get active trading signals
- `POST /api/trading/signals` - Create trading signal

### AI Analysis Endpoints
- `POST /api/ai/analyze` - Analyze portfolio with AI
- `GET /api/ai/recommendations/{user_id}` - Get AI recommendations

### Portfolio Endpoints
- `GET /api/portfolio/{user_id}` - Get portfolio summary
- `GET /api/portfolio/{user_id}/performance` - Get performance metrics

## Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-08-02T15:30:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2025-08-02T15:30:00Z"
}
```

## Performance Features

### Database Optimization
- Optimized query execution with caching
- Real-time performance monitoring
- Automated backup and recovery
- Performance regression testing

### Monitoring
- Real-time metrics collection
- Performance dashboards
- Alert system with configurable thresholds
- Health checks and status monitoring

## Error Handling
- Comprehensive error logging
- Graceful degradation for missing components
- Automatic retry mechanisms
- Circuit breaker patterns

## Rate Limiting
- API rate limiting implemented
- Per-user request limits
- Burst protection

## Security
- CORS configuration
- Input validation
- SQL injection protection
- Error message sanitization

## Deployment
The application is containerized and optimized for Railway deployment with:
- Health checks
- Graceful shutdown
- Environment-based configuration
- Automatic restarts on failure
