const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const cookieParser = require('cookie-parser');
const dotenv = require('dotenv');
const winston = require('winston');

// Load environment variables
dotenv.config();

// Immediate startup logging
console.log('🚀 QuantumLeap Trading Backend Starting... (v2.0.1)');
console.log(`📊 PORT: ${process.env.PORT || 'not set'}`);
console.log(`🌍 NODE_ENV: ${process.env.NODE_ENV || 'development'}`);
console.log(`🐳 Platform: ${process.platform}`);
console.log(`📦 Node: ${process.version}`);

// Import modular architecture components
const ServiceContainer = require('./service-container');
const EventBus = require('./shared/events/eventBus');
const ModuleLoader = require('./module-loader');
const databaseConnection = require('./modules/core/database/connection');

// Import existing middleware (preserve current functionality)
const { errorHandler } = require('./middleware/errorHandler');
const { requestLogger } = require('./middleware/requestLogger');
const { requestId } = require('./middleware/requestId');

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
// Use Railway's PORT environment variable or fallback to 4000
const PORT = process.env.PORT || process.env.MODULAR_PORT || 4000;

// Initialize service container and event bus
const serviceContainer = new ServiceContainer();
const eventBus = new EventBus();

// Middleware (preserve current setup)
app.use(helmet({
  crossOriginOpenerPolicy: false, // Allow popup communication
  crossOriginEmbedderPolicy: false // Allow popup communication
}));
app.use(cors({
  origin: [
    'https://vitan-task-frontend.up.railway.app',
    'https://quantum-leap-frontend-production.up.railway.app',
    'https://quantumleap-trading-frontend.up.railway.app',
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'http://localhost:3004',
    'http://localhost:4000', // Allow modular server
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001',
    'http://127.0.0.1:3002',
    'http://127.0.0.1:3003',
    'http://127.0.0.1:3004',
    'http://127.0.0.1:4000',
    'http://127.0.0.1:5173'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'X-Force-Delete']
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(requestId);
app.use(requestLogger);

// Initialize core services
async function initializeCoreServices() {
  try {
    logger.info('Initializing core services...');
    
    // Initialize database connection and run migrations
    try {
      const dbInit = require('./core/database/init');
      const dbConnected = await dbInit.initialize();
      
      if (dbConnected) {
        const db = require('./core/database/connection');
        serviceContainer.register('database', db);
        logger.info('✅ Database initialized with all migrations');
      } else {
        // Create a limited database service for development
        const limitedDatabase = {
          query: async () => { throw new Error('Database not available'); },
          healthCheck: async () => ({ status: 'disconnected', message: 'Database not available' }),
          shutdown: async () => logger.info('Limited database service shutdown')
        };
        serviceContainer.register('database', limitedDatabase);
        logger.warn('⚠️ Database not available - running in limited mode');
      }
    } catch (dbError) {
      logger.error('❌ Database initialization failed:', dbError.message);
      
      // In production, we might want to fail here
      if (process.env.NODE_ENV === 'production' && process.env.REQUIRE_DATABASE === 'true') {
        throw dbError;
      }
      
      // Create a mock database service for development
      const mockDatabase = {
        query: async () => { throw new Error('Database connection failed'); },
        healthCheck: async () => ({ status: 'failed', message: 'Database connection failed', error: dbError.message }),
        shutdown: async () => logger.info('Mock database shutdown')
      };
      serviceContainer.register('database', mockDatabase);
      logger.warn('⚠️ Continuing without database (development mode)');
    }
    
    // Register core services in container
    serviceContainer.register('eventBus', eventBus);
    serviceContainer.register('logger', logger);
    
    logger.info('Core services initialized successfully');
    return true;
  } catch (error) {
    logger.error('Failed to initialize core services:', error);
    throw error;
  }
}

// Mount module routes
async function mountModuleRoutes(app, modules, serviceContainer) {
  try {
    logger.info('Mounting module routes...');
    
    for (const [moduleName, moduleInfo] of modules) {
      try {
        logger.info(`🔍 Checking module '${moduleName}' for routes...`);
        logger.info(`   - Module keys: ${Object.keys(moduleInfo)}`);
        logger.info(`   - Has getRoutes: ${!!moduleInfo.getRoutes}`);
        
        // Check if module has getRoutes method
        if (moduleInfo.getRoutes && typeof moduleInfo.getRoutes === 'function') {
          logger.info(`   - Calling getRoutes() for '${moduleName}'...`);
          const routes = moduleInfo.getRoutes();
          if (routes) {
            const mountPath = `/api/modules/${moduleName}`;
            app.use(mountPath, routes);
            // Update the module in service container to reflect routes status
            const containerModule = serviceContainer.getModule(moduleName);
            if (containerModule) {
              containerModule.routes = true;
            }
            logger.info(`✅ Mounted routes for module '${moduleName}' at ${mountPath}`);
          } else {
            logger.warn(`   - getRoutes() returned null/undefined for '${moduleName}'`);
            const containerModule = serviceContainer.getModule(moduleName);
            if (containerModule) {
              containerModule.routes = false;
            }
          }
        } else {
          logger.warn(`   - Module '${moduleName}' does not have getRoutes method`);
          const containerModule = serviceContainer.getModule(moduleName);
          if (containerModule) {
            containerModule.routes = false;
          }
        }
      } catch (error) {
        logger.error(`❌ Failed to mount routes for module '${moduleName}':`, error);
      }
    }
    
    logger.info('Module route mounting completed');
  } catch (error) {
    logger.error('Failed to mount module routes:', error);
    throw error;
  }
}

// Initialize modules
async function initializeModules() {
  try {
    logger.info('Initializing modules...');
    
    // Create module loader
    const moduleLoader = new ModuleLoader('./modules');
    
    // Load all modules
    const modules = await moduleLoader.loadAllModules();
    
    // Register modules with service container
    for (const [moduleName, module] of modules) {
      serviceContainer.registerModule(moduleName, module);
    }
    
    // Initialize all modules
    await serviceContainer.initializeModules(app);
    
    // Mount module routes
    await mountModuleRoutes(app, modules, serviceContainer);
    
    // Add 404 handler AFTER module routes are mounted
    app.use('*', (req, res) => {
      logger.warn('Route not found', { path: req.originalUrl });
      res.status(404).json({ 
        error: 'Route not found',
        path: req.originalUrl,
        server: 'modular',
        port: PORT
      });
    });
    
    logger.info(`Successfully initialized ${modules.size} modules`);
    return modules;
  } catch (error) {
    logger.error('Failed to initialize modules:', error);
    throw error;
  }
}

// Railway health check endpoint - MUST respond immediately
app.get('/health', (req, res) => {
  // Immediate response - no async operations
  res.status(200).json({ 
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    version: '2.0.0',
    ready: true
  });
});

// Backup health endpoints
app.get('/ping', (req, res) => {
  res.status(200).send('pong');
});

app.get('/', (req, res) => {
  res.status(200).json({
    message: 'QuantumLeap Trading Backend',
    status: 'running',
    version: '2.0.0'
  });
});

// Enhanced health check with modules (for debugging)
app.get('/health/detailed', async (req, res) => {
  try {
    logger.info('Detailed health check requested');
    
    // Get modular architecture health
    const modularHealth = await serviceContainer.healthCheck();
    
    res.status(200).json({ 
      status: 'OK', 
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: process.env.NODE_ENV || 'development',
      port: PORT,
      architecture: 'modular',
      server: 'modular',
      version: '2.0.0',
      deployment: 'railway',
      modules: modularHealth.modules,
      services: modularHealth.services
    });
  } catch (error) {
    logger.error('Detailed health check failed:', error);
    res.status(500).json({ 
      status: 'ERROR',
      error: error.message,
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      deployment: 'railway'
    });
  }
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'QuantumLeap Trading Backend API',
    version: '2.0.0',
    status: 'running',
    timestamp: new Date().toISOString(),
    endpoints: {
      health: '/health',
      test: '/api/test',
      modules: '/api/modules'
    }
  });
});

// Direct OAuth callback route (for Zerodha redirects)
app.get('/broker/callback', (req, res) => {
  try {
    console.log('🔄 Direct OAuth callback received:', req.query);
    
    const { request_token, action, type, status, state } = req.query;
    
    // Set headers to allow popup communication
    res.setHeader('Cross-Origin-Opener-Policy', 'unsafe-none');
    res.setHeader('Cross-Origin-Embedder-Policy', 'unsafe-none');
    
    // Basic validation
    if (!request_token) {
      return res.status(400).json({
        success: false,
        error: 'Missing request_token parameter'
      });
    }

    if (status !== 'success') {
      return res.status(400).json({
        success: false,
        error: 'OAuth authentication was not successful',
        details: { status, action, type }
      });
    }

    // Log successful callback
    console.log('✅ OAuth callback successful:', { request_token, state, action, type, status });
    
    // Redirect to frontend with success
    const frontendUrl = 'https://quantum-leap-frontend-production.up.railway.app';
    const redirectUrl = `${frontendUrl}/broker-callback?status=success&request_token=${request_token}&state=${state || ''}`;
    
    console.log('🔄 Redirecting to frontend:', redirectUrl);
    res.redirect(redirectUrl);

  } catch (error) {
    console.error('❌ OAuth callback error:', error);
    
    // Redirect to frontend with error
    const frontendUrl = 'https://quantum-leap-frontend-production.up.railway.app';
    const redirectUrl = `${frontendUrl}/broker-callback?status=error&error=${encodeURIComponent(error.message)}`;
    
    res.redirect(redirectUrl);
  }
});

// Simple test endpoint to verify deployment
app.get('/api/test', (req, res) => {
  res.json({
    message: 'QuantumLeap Trading Backend is running!',
    timestamp: new Date().toISOString(),
    version: '2.0.0',
    environment: process.env.NODE_ENV || 'development',
    port: PORT,
    deployment: 'railway'
  });
});

// Module management endpoints (for development/debugging)
app.get('/api/modules', (req, res) => {
  try {
    const modules = serviceContainer.getModules();
    const moduleList = Array.from(modules.entries()).map(([name, module]) => ({
      name,
      version: module.version,
      status: module.status,
      description: module.description,
      registeredAt: module.registeredAt,
      hasHealthMethod: typeof module.health === 'function',
      hasInitializeMethod: typeof module.initialize === 'function',
      dependencies: module.dependencies || [],
      provides: module.provides || []
    }));
    
    res.json({
      success: true,
      data: moduleList,
      count: moduleList.length,
      debug: {
        serviceContainerStatus: 'active',
        totalServices: serviceContainer.getServiceNames().length,
        availableServices: serviceContainer.getServiceNames()
      }
    });
  } catch (error) {
    logger.error('Failed to get modules:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Debug endpoint to see module details
app.get('/api/modules/:moduleName/debug', (req, res) => {
  try {
    const { moduleName } = req.params;
    const module = serviceContainer.getModule(moduleName);
    
    if (!module) {
      return res.status(404).json({
        success: false,
        error: `Module '${moduleName}' not found`,
        availableModules: Array.from(serviceContainer.getModules().keys())
      });
    }
    
    res.json({
      success: true,
      data: {
        name: module.name,
        version: module.version,
        status: module.status,
        description: module.description,
        registeredAt: module.registeredAt,
        initializedAt: module.initializedAt,
        startedAt: module.startedAt,
        stoppedAt: module.stoppedAt,
        error: module.error,
        methods: {
          hasHealth: typeof module.health === 'function',
          hasInitialize: typeof module.initialize === 'function',
          hasStart: typeof module.start === 'function',
          hasStop: typeof module.stop === 'function'
        },
        dependencies: module.dependencies || [],
        provides: module.provides || [],
        services: module.services || {},
        routes: module.routes ? 'registered' : 'not_registered'
      }
    });
  } catch (error) {
    logger.error(`Failed to get module debug info for ${req.params.moduleName}:`, error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/api/modules/:moduleName/health', async (req, res) => {
  try {
    const { moduleName } = req.params;
    logger.info(`Module health check requested for: ${moduleName}`);
    
    const module = serviceContainer.getModule(moduleName);
    
    if (!module) {
      logger.warn(`Module '${moduleName}' not found in service container`);
      return res.status(404).json({
        success: false,
        error: `Module '${moduleName}' not found`,
        availableModules: Array.from(serviceContainer.getModules().keys())
      });
    }
    
    logger.info(`Module '${moduleName}' found, calling health method`, {
      moduleStatus: module.status,
      hasHealthMethod: typeof module.health === 'function'
    });
    
    // Check if the module has a health method
    if (typeof module.health !== 'function') {
      logger.warn(`Module '${moduleName}' does not have a health method`);
      return res.status(500).json({
        success: false,
        error: `Module '${moduleName}' does not have a health method`,
        moduleInfo: {
          name: module.name,
          version: module.version,
          status: module.status
        }
      });
    }
    
    // Call the module's health method
    const health = await module.health();
    
    logger.info(`Module '${moduleName}' health check completed`, {
      healthStatus: health.status
    });
    
    res.json({
      success: true,
      data: health,
      moduleName,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    logger.error(`Failed to get module health for ${req.params.moduleName}:`, error);
    res.status(500).json({
      success: false,
      error: error.message,
      moduleName: req.params.moduleName,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      timestamp: new Date().toISOString()
    });
  }
});

// API info endpoint (preserve current functionality)
app.get('/', (req, res) => {
  res.json({
    message: 'WhatsTask Modular API Server',
    version: '2.0.0',
    architecture: 'modular',
    server: 'modular',
    port: PORT,
    endpoints: {
      health: '/health',
      modules: '/api/modules',
      'module-health': '/api/modules/:moduleName/health',
      'module-debug': '/api/modules/:moduleName/debug'
    },
    documentation: 'Frontend should be deployed separately',
    note: 'This is the modular server running on port 4000. The main server runs on port 3000.',
    phase: 'Phase-2: Tasks module migrated to modular architecture'
  });
});

// Error handling middleware (preserve current setup)
app.use(errorHandler);

// Note: 404 handler will be added after module routes are mounted

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
        try {
          await initializeCoreServices();
          console.log('✅ Core services initialized');
          logger.info('✅ Core services initialized');
        } catch (error) {
          console.warn('⚠️ Core services initialization failed:', error.message);
          logger.warn('⚠️ Core services initialization failed:', error.message);
        }
        
        console.log('🔧 Initializing modules...');
        try {
          await initializeModules();
          console.log('✅ Modules initialized');
          logger.info('✅ Modules initialized');
        } catch (error) {
          console.warn('⚠️ Module initialization failed:', error.message);
          logger.warn('⚠️ Module initialization failed:', error.message);
        }
        
        console.log('🚀 Backend fully ready!');
        logger.info('🚀 Backend fully ready!');
      });
    });
    
    // Handle server errors
    server.on('error', (error) => {
      console.error('❌ Server error:', error);
      logger.error('❌ Server error:', error);
      process.exit(1);
    });
    
    // Handle server listening event
    server.on('listening', () => {
      console.log(`🎯 Server is listening on ${server.address().address}:${server.address().port}`);
      logger.info(`🎯 Server is listening on ${server.address().address}:${server.address().port}`);
    });
    
    // Graceful shutdown
    process.on('SIGTERM', async () => {
      logger.info('SIGTERM received, shutting down gracefully');
      
      try {
        await serviceContainer.shutdown();
        server.close(() => {
          logger.info('Modular server closed');
          process.exit(0);
        });
      } catch (error) {
        logger.error('Error during shutdown:', error);
        process.exit(1);
      }
      
      // Force exit after 10 seconds
      setTimeout(() => {
        logger.error('Forced shutdown after timeout');
        process.exit(1);
      }, 10000);
    });
    
    process.on('SIGINT', async () => {
      logger.info('SIGINT received, shutting down gracefully');
      
      try {
        await serviceContainer.shutdown();
        server.close(() => {
          logger.info('Modular server closed');
          process.exit(0);
        });
      } catch (error) {
        logger.error('Error during shutdown:', error);
        process.exit(1);
      }
    });
    
    return server;
  } catch (error) {
    logger.error('Failed to start modular server:', error);
    process.exit(1);
  }
}

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Start the server if this file is run directly
if (require.main === module) {
  startServer().catch(error => {
    logger.error('Failed to start modular server:', error);
    process.exit(1);
  });
}

module.exports = { app, startServer, serviceContainer, eventBus };
