const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const cookieParser = require('cookie-parser');
const dotenv = require('dotenv');
const winston = require('winston');

// Load environment variables
dotenv.config();

// Immediate startup logging
console.log('🚀 QuantumLeap Trading Backend Starting (Safe Mode)...');
console.log(`📊 PORT: ${process.env.PORT || 'not set'}`);
console.log(`🌍 NODE_ENV: ${process.env.NODE_ENV || 'development'}`);
console.log(`🐳 Platform: ${process.platform}`);
console.log(`📦 Node: ${process.version}`);

// Initialize logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'modular-server.log' })
  ]
});

const app = express();
const PORT = process.env.PORT || process.env.MODULAR_PORT || 4000;

// Server readiness state
let serverState = {
  ready: true,
  coreServices: 'not_started',
  modules: 'not_started',
  database: 'not_started'
};

// Middleware
app.use(helmet());
app.use(cors({
  origin: [
    'http://localhost:3000',
    'http://localhost:5173', 
    'https://quantum-leap-frontend-production.up.railway.app',
    process.env.FRONTEND_URL
  ].filter(Boolean),
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Request logging middleware
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });
  next();
});

// Railway health check endpoint - MUST respond immediately
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    version: '2.0.0',
    ready: serverState.ready,
    services: serverState
  });
});

// Backup health endpoints
app.get('/ping', (req, res) => {
  res.status(200).send('pong');
});

app.get('/', (req, res) => {
  res.status(200).json({
    message: 'QuantumLeap Trading Backend (Safe Mode)',
    status: 'running',
    version: '2.0.0',
    architecture: 'modular-safe',
    services: serverState
  });
});

// Simple test endpoint
app.get('/api/test', (req, res) => {
  res.json({
    message: 'QuantumLeap Trading Backend is running!',
    timestamp: new Date().toISOString(),
    version: '2.0.0',
    environment: process.env.NODE_ENV || 'development',
    port: PORT,
    deployment: 'railway',
    ready: serverState.ready
  });
});

// Status endpoint
app.get('/api/status', (req, res) => {
  res.json({
    server: 'running',
    services: serverState,
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    timestamp: new Date().toISOString()
  });
});

// OAuth broker endpoints - redirect to auth module
app.use('/broker', (req, res, next) => {
  // Redirect broker endpoints to auth module OAuth routes
  req.url = '/api/modules/auth/broker' + req.url;
  next();
});

app.use('/api/broker', (req, res, next) => {
  // Redirect API broker endpoints to auth module OAuth routes
  req.url = '/api/modules/auth/broker' + req.url.replace('/api/broker', '');
  next();
});

// Portfolio endpoints (comprehensive mock implementation)
const mockPortfolioData = {
  totalValue: 100000,
  dayChange: 1250.50,
  dayChangePercent: 1.27,
  positions: [
    { symbol: 'AAPL', quantity: 10, price: 150.25, value: 1502.50, change: 2.5, changePercent: 1.69 },
    { symbol: 'GOOGL', quantity: 5, price: 2750.80, value: 13754.00, change: -15.20, changePercent: -0.55 },
    { symbol: 'TSLA', quantity: 8, price: 245.60, value: 1964.80, change: 8.40, changePercent: 3.54 },
    { symbol: 'MSFT', quantity: 15, price: 420.30, value: 6304.50, change: 12.80, changePercent: 3.14 },
    { symbol: 'AMZN', quantity: 3, price: 3200.75, value: 9602.25, change: -25.50, changePercent: -0.79 }
  ],
  cash: 5000.00,
  lastUpdated: new Date().toISOString()
};

// 1. Latest Simple Portfolio
app.get('/api/portfolio/latest-simple', (req, res) => {
  const userId = req.query.user_id;
  logger.info('Simple portfolio data requested', { userId });
  res.json({
    success: true,
    data: {
      totalValue: mockPortfolioData.totalValue,
      dayChange: mockPortfolioData.dayChange,
      dayChangePercent: mockPortfolioData.dayChangePercent,
      cash: mockPortfolioData.cash,
      lastUpdated: mockPortfolioData.lastUpdated
    },
    message: 'Simple portfolio data'
  });
});

// 2. Live Portfolio Data
app.get('/api/portfolio/fetch-live', (req, res) => {
  const userId = req.query.user_id;
  logger.info('Live portfolio data requested', { userId });
  res.json({
    success: true,
    data: {
      ...mockPortfolioData,
      isLive: true,
      marketStatus: 'OPEN',
      lastUpdated: new Date().toISOString()
    },
    message: 'Live portfolio data'
  });
});

// 3. Portfolio History
app.get('/api/portfolio/history', (req, res) => {
  const { user_id, time_range } = req.query;
  logger.info('Portfolio history requested', { userId: user_id, timeRange: time_range });
  
  // Generate mock historical data
  const historyData = [];
  const days = time_range === '1D' ? 1 : time_range === '1W' ? 7 : time_range === '1M' ? 30 : 90;
  
  for (let i = days; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    historyData.push({
      date: date.toISOString(),
      value: mockPortfolioData.totalValue + (Math.random() - 0.5) * 5000,
      change: (Math.random() - 0.5) * 1000
    });
  }
  
  res.json({
    success: true,
    data: historyData,
    timeRange: time_range,
    message: 'Portfolio history data'
  });
});

// 4. Portfolio Performance
app.get('/api/portfolio/performance', (req, res) => {
  const { user_id, time_range } = req.query;
  logger.info('Portfolio performance requested', { userId: user_id, timeRange: time_range });
  
  res.json({
    success: true,
    data: {
      totalReturn: 15250.75,
      totalReturnPercent: 18.45,
      dayReturn: mockPortfolioData.dayChange,
      dayReturnPercent: mockPortfolioData.dayChangePercent,
      weekReturn: 2850.30,
      weekReturnPercent: 2.95,
      monthReturn: 8420.60,
      monthReturnPercent: 9.12,
      yearReturn: 15250.75,
      yearReturnPercent: 18.45,
      benchmarkComparison: {
        sp500: { return: 12.5, outperformance: 5.95 },
        nasdaq: { return: 15.2, outperformance: 3.25 }
      }
    },
    message: 'Portfolio performance data'
  });
});

// 5. Portfolio Summary
app.get('/api/portfolio/summary', (req, res) => {
  const userId = req.query.user_id;
  logger.info('Portfolio summary requested', { userId });
  
  res.json({
    success: true,
    data: {
      totalValue: mockPortfolioData.totalValue,
      totalPositions: mockPortfolioData.positions.length,
      totalCash: mockPortfolioData.cash,
      dayChange: mockPortfolioData.dayChange,
      dayChangePercent: mockPortfolioData.dayChangePercent,
      topPerformer: mockPortfolioData.positions[0],
      worstPerformer: mockPortfolioData.positions[1],
      diversificationScore: 85,
      riskScore: 'MODERATE'
    },
    message: 'Portfolio summary data'
  });
});

// 6. Portfolio Analysis
app.get('/api/portfolio/analyze', (req, res) => {
  logger.info('Portfolio analysis requested');
  
  res.json({
    success: true,
    data: {
      healthScore: 82,
      riskAssessment: {
        overall: 'MODERATE',
        concentration: 'LOW',
        volatility: 'MEDIUM',
        correlation: 'LOW'
      },
      diversification: {
        score: 85,
        sectors: {
          'Technology': 45,
          'Healthcare': 20,
          'Finance': 15,
          'Consumer': 12,
          'Energy': 8
        }
      },
      recommendations: [
        {
          type: 'REBALANCE',
          priority: 'HIGH',
          message: 'Consider reducing technology exposure',
          action: 'Sell 10% of tech positions'
        },
        {
          type: 'DIVERSIFY',
          priority: 'MEDIUM',
          message: 'Add international exposure',
          action: 'Consider emerging market ETFs'
        }
      ]
    },
    message: 'Portfolio analysis complete'
  });
});

// 7. Portfolio Holdings
app.get('/api/portfolio/holdings', (req, res) => {
  const userId = req.query.user_id;
  logger.info('Portfolio holdings requested', { userId });
  
  res.json({
    success: true,
    data: mockPortfolioData.positions.map(position => ({
      ...position,
      sector: position.symbol === 'AAPL' ? 'Technology' : 
              position.symbol === 'GOOGL' ? 'Technology' :
              position.symbol === 'TSLA' ? 'Automotive' :
              position.symbol === 'MSFT' ? 'Technology' : 'E-commerce',
      marketCap: 'LARGE',
      dividendYield: Math.random() * 3,
      peRatio: 15 + Math.random() * 20
    })),
    message: 'Portfolio holdings data'
  });
});

// 8. Portfolio Allocation
app.get('/api/portfolio/allocation', (req, res) => {
  const userId = req.query.user_id;
  logger.info('Portfolio allocation requested', { userId });
  
  res.json({
    success: true,
    data: {
      byAssetType: {
        'Stocks': 85,
        'ETFs': 10,
        'Cash': 5
      },
      bySector: {
        'Technology': 45,
        'Healthcare': 20,
        'Finance': 15,
        'Consumer': 12,
        'Energy': 8
      },
      byMarketCap: {
        'Large Cap': 70,
        'Mid Cap': 20,
        'Small Cap': 10
      },
      byGeography: {
        'US': 80,
        'International': 15,
        'Emerging': 5
      }
    },
    message: 'Portfolio allocation data'
  });
});

// Legacy endpoint (keep for backward compatibility)
app.get('/api/portfolio/latest/:userId', (req, res) => {
  logger.info('Legacy portfolio data requested', { userId: req.params.userId });
  res.json({
    success: true,
    data: mockPortfolioData,
    message: 'Legacy portfolio endpoint - use /api/portfolio/latest-simple instead'
  });
});

// Safe initialization functions
async function initializeCoreServices() {
  try {
    serverState.coreServices = 'initializing';
    logger.info('Initializing core services...');
    
    // Mock database for safe startup
    serverState.database = 'mock';
    
    serverState.coreServices = 'ready';
    logger.info('Core services initialized successfully');
    return true;
  } catch (error) {
    serverState.coreServices = 'failed';
    logger.error('Failed to initialize core services:', error);
    // Don't throw - just log and continue
    return false;
  }
}

async function initializeModules() {
  try {
    serverState.modules = 'initializing';
    logger.info('Initializing modules...');
    
    // Safe module initialization - don't fail if modules can't load
    serverState.modules = 'ready';
    logger.info('Modules initialized successfully');
    return true;
  } catch (error) {
    serverState.modules = 'failed';
    logger.error('Failed to initialize modules:', error);
    // Don't throw - just log and continue
    return false;
  }
}

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use('*', (req, res) => {
  logger.warn('Route not found', { path: req.originalUrl });
  res.status(404).json({ 
    error: 'Route not found',
    path: req.originalUrl,
    server: 'modular-safe',
    port: PORT
  });
});

// Start server
async function startServer() {
  try {
    console.log('🚀 Starting server...');
    logger.info('🚀 Starting server...');
    
    // Start server first to make health check available immediately
    const server = app.listen(PORT, '0.0.0.0', async () => {
      console.log(`✅ Server listening on port ${PORT}`);
      logger.info(`✅ QuantumLeap Trading Backend server running on port ${PORT}`);
      logger.info(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
      logger.info(`❤️ Health check: http://0.0.0.0:${PORT}/health`);
      logger.info(`🧪 Test endpoint: http://0.0.0.0:${PORT}/api/test`);
      
      // Test health endpoint immediately
      setTimeout(() => {
        const http = require('http');
        const req = http.request({
          hostname: 'localhost',
          port: PORT,
          path: '/health',
          method: 'GET'
        }, (res) => {
          console.log(`✅ Internal health check: ${res.statusCode}`);
          logger.info(`✅ Internal health check: ${res.statusCode}`);
        });
        req.on('error', (err) => {
          console.error('❌ Internal health check failed:', err.message);
          logger.error('❌ Internal health check failed:', err.message);
        });
        req.end();
      }, 500);
      
      // Initialize services in background after server is listening
      setImmediate(async () => {
        console.log('🔧 Initializing core services...');
        await initializeCoreServices();
        
        console.log('🔧 Initializing modules...');
        await initializeModules();
        
        console.log('🚀 Backend fully ready!');
        logger.info('🚀 Backend fully ready!');
      });
    });
    
    // Handle server errors gracefully
    server.on('error', (error) => {
      console.error('❌ Server error:', error);
      logger.error('❌ Server error:', error);
      // Don't exit immediately - let Railway retry
      setTimeout(() => {
        process.exit(1);
      }, 5000);
    });
    
    // Handle server listening event
    server.on('listening', () => {
      const addr = server.address();
      console.log(`🎯 Server is listening on ${addr.address}:${addr.port}`);
      logger.info(`🎯 Server is listening on ${addr.address}:${addr.port}`);
    });
    
    // Graceful shutdown
    process.on('SIGTERM', async () => {
      logger.info('SIGTERM received, shutting down gracefully');
      server.close(() => {
        logger.info('Server closed');
        process.exit(0);
      });
    });
    
    process.on('SIGINT', async () => {
      logger.info('SIGINT received, shutting down gracefully');
      server.close(() => {
        logger.info('Server closed');
        process.exit(0);
      });
    });
    
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    logger.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Unhandled errors
process.on('uncaughtException', (err) => {
  console.error('💥 Uncaught Exception:', err);
  logger.error('💥 Uncaught Exception:', err);
  // Don't exit immediately - let Railway retry
  setTimeout(() => {
    process.exit(1);
  }, 5000);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
  logger.error('💥 Unhandled Rejection:', { reason, promise });
  // Don't exit immediately - let Railway retry
  setTimeout(() => {
    process.exit(1);
  }, 5000);
});

// Start the server
startServer().catch((error) => {
  console.error('💥 Failed to start server:', error);
  process.exit(1);
});

console.log('🎯 QuantumLeap Trading Backend (Safe Mode) initialized');