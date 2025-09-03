#!/usr/bin/env node

// Simple startup verification script
console.log('🚀 Starting QuantumLeap Trading Backend...');
console.log('📊 Environment Check:');
console.log(`   NODE_ENV: ${process.env.NODE_ENV || 'development'}`);
console.log(`   PORT: ${process.env.PORT || 'not set'}`);
console.log(`   Platform: ${process.platform}`);
console.log(`   Node Version: ${process.version}`);

// Test basic server functionality
const express = require('express');
const app = express();
const PORT = process.env.PORT || 4000;

app.get('/startup-test', (req, res) => {
  res.json({
    message: 'Startup test successful',
    timestamp: new Date().toISOString(),
    port: PORT
  });
});

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Test server running on port ${PORT}`);
  console.log('🔍 Testing health endpoint...');
  
  // Test health endpoint
  setTimeout(() => {
    const http = require('http');
    const options = {
      hostname: 'localhost',
      port: PORT,
      path: '/startup-test',
      method: 'GET'
    };

    const req = http.request(options, (res) => {
      console.log(`✅ Health check response: ${res.statusCode}`);
      server.close(() => {
        console.log('✅ Startup verification complete');
        process.exit(0);
      });
    });

    req.on('error', (err) => {
      console.error('❌ Health check failed:', err.message);
      server.close(() => {
        process.exit(1);
      });
    });

    req.end();
  }, 1000);
});