#!/usr/bin/env node

/**
 * Railway Debug Script
 * Minimal server to test Railway deployment issues
 */

const express = require('express');
const app = express();
const PORT = process.env.PORT || 4000;

console.log('🚀 Railway Debug Server Starting...');
console.log(`📊 PORT: ${PORT}`);
console.log(`🌍 NODE_ENV: ${process.env.NODE_ENV || 'development'}`);
console.log(`🐳 Platform: ${process.platform}`);
console.log(`📦 Node: ${process.version}`);

// Minimal health endpoint
app.get('/health', (req, res) => {
  console.log('❤️ Health check requested');
  res.status(200).json({ 
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    port: PORT,
    message: 'Railway debug server is healthy'
  });
});

// Root endpoint
app.get('/', (req, res) => {
  console.log('🏠 Root endpoint requested');
  res.status(200).json({
    message: 'Railway Debug Server',
    status: 'running',
    port: PORT,
    timestamp: new Date().toISOString()
  });
});

// Test endpoint
app.get('/test', (req, res) => {
  console.log('🧪 Test endpoint requested');
  res.status(200).json({
    message: 'Test successful',
    timestamp: new Date().toISOString()
  });
});

// Error handling
app.use((err, req, res, next) => {
  console.error('❌ Error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// 404 handler
app.use('*', (req, res) => {
  console.log(`❓ 404: ${req.originalUrl}`);
  res.status(404).json({ error: 'Not found', path: req.originalUrl });
});

// Start server
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Railway Debug Server listening on port ${PORT}`);
  console.log(`❤️ Health: http://0.0.0.0:${PORT}/health`);
  console.log(`🧪 Test: http://0.0.0.0:${PORT}/test`);
  
  // Self-test after startup
  setTimeout(() => {
    const http = require('http');
    const req = http.request({
      hostname: 'localhost',
      port: PORT,
      path: '/health',
      method: 'GET'
    }, (res) => {
      console.log(`✅ Self-test health check: ${res.statusCode}`);
    });
    req.on('error', (err) => {
      console.error('❌ Self-test failed:', err.message);
    });
    req.end();
  }, 1000);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('📴 SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('📴 SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

// Unhandled errors
process.on('uncaughtException', (err) => {
  console.error('💥 Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

console.log('🎯 Railway Debug Server initialized');