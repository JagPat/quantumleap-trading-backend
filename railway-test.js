#!/usr/bin/env node

// Railway deployment test script
console.log('🚀 Railway Test Script Starting...');
console.log(`📊 PORT: ${process.env.PORT || 'not set'}`);
console.log(`🌍 NODE_ENV: ${process.env.NODE_ENV || 'development'}`);

const express = require('express');
const app = express();
const PORT = process.env.PORT || 4000;

// Immediate health endpoint
app.get('/health', (req, res) => {
  console.log('❤️ Health check requested');
  res.status(200).json({ 
    status: 'OK',
    timestamp: new Date().toISOString(),
    port: PORT,
    test: true
  });
});

app.get('/', (req, res) => {
  res.json({ message: 'Railway test server running', port: PORT });
});

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Railway test server running on port ${PORT}`);
  console.log(`❤️ Health: http://0.0.0.0:${PORT}/health`);
  
  // Self-test
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

server.on('error', (error) => {
  console.error('❌ Server error:', error);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down');
  server.close(() => {
    process.exit(0);
  });
});