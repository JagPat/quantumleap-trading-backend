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

// Broker endpoints (mock implementation for frontend compatibility)
app.get('/broker/test-oauth', (req, res) => {
  logger.info('Broker OAuth test requested', { query: req.query });
  res.json({
    success: true,
    message: 'OAuth test endpoint - mock implementation',
    timestamp: new Date().toISOString(),
    query: req.query
  });
});

app.post('/broker/test-oauth', (req, res) => {
  logger.info('Broker OAuth setup requested', { body: req.body });
  res.json({
    success: true,
    message: 'OAuth setup completed - mock implementation',
    timestamp: new Date().toISOString(),
    data: {
      oauth_url: 'https://mock-broker-oauth.example.com/auth',
      state: 'mock_state_' + Date.now()
    }
  });
});

// Broker config endpoints
app.get('/api/broker/configs', (req, res) => {
  logger.info('Broker configs requested');
  res.json({
    success: true,
    data: [],
    message: 'No broker configurations found - mock implementation'
  });
});

app.post('/api/broker/configs', (req, res) => {
  logger.info('Broker config creation requested', { body: req.body });
  res.json({
    success: true,
    data: {
      id: 'mock_config_' + Date.now(),
      ...req.body,
      created_at: new Date().toISOString(),
      is_connected: false
    },
    message: 'Broker configuration created - mock implementation'
  });
});

// Portfolio endpoints (mock implementation)
app.get('/api/portfolio/latest/:userId', (req, res) => {
  logger.info('Portfolio data requested', { userId: req.params.userId });
  res.json({
    success: true,
    data: {
      totalValue: 100000,
      dayChange: 1250.50,
      dayChangePercent: 1.27,
      positions: [
        { symbol: 'AAPL', quantity: 10, price: 150.25, value: 1502.50 },
        { symbol: 'GOOGL', quantity: 5, price: 2750.80, value: 13754.00 },
        { symbol: 'TSLA', quantity: 8, price: 245.60, value: 1964.80 }
      ],
      cash: 5000.00,
      lastUpdated: new Date().toISOString()
    },
    message: 'Mock portfolio data'
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