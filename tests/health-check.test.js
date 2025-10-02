#!/usr/bin/env node
/**
 * Backend Health Check Integration Test
 * Tests /health and /version endpoints for Railway deployment
 */

const http = require('http');
const { spawn } = require('child_process');

// Configuration
const TEST_PORT = 4000;
const TEST_URL = `http://localhost:${TEST_PORT}`;
const TIMEOUT = 10000; // 10 seconds

// Colors for output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function makeRequest(path) {
  return new Promise((resolve, reject) => {
    const req = http.get(`${TEST_URL}${path}`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const jsonData = JSON.parse(data);
          resolve({ statusCode: res.statusCode, data: jsonData });
        } catch (error) {
          resolve({ statusCode: res.statusCode, data: data });
        }
      });
    });
    
    req.on('error', reject);
    req.setTimeout(TIMEOUT, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

async function testHealthEndpoint() {
  log('\n🔍 Testing /health endpoint...', 'blue');
  
  try {
    const response = await makeRequest('/health');
    
    if (response.statusCode !== 200) {
      log(`❌ Health endpoint returned status ${response.statusCode}`, 'red');
      return false;
    }
    
    const { data } = response;
    
    // Check required fields
    const requiredFields = ['status', 'commit', 'time', 'port'];
    const missingFields = requiredFields.filter(field => !(field in data));
    
    if (missingFields.length > 0) {
      log(`❌ Missing required fields: ${missingFields.join(', ')}`, 'red');
      return false;
    }
    
    // Check status value
    if (data.status !== 'ok') {
      log(`❌ Expected status 'ok', got '${data.status}'`, 'red');
      return false;
    }
    
    // Check port matches test port
    if (data.port !== TEST_PORT) {
      log(`❌ Expected port ${TEST_PORT}, got ${data.port}`, 'red');
      return false;
    }
    
    log('✅ Health endpoint test PASSED', 'green');
    log(`   Status: ${data.status}`, 'cyan');
    log(`   Commit: ${data.commit}`, 'cyan');
    log(`   Port: ${data.port}`, 'cyan');
    log(`   Time: ${data.time}`, 'cyan');
    
    return true;
  } catch (error) {
    log(`❌ Health endpoint test FAILED: ${error.message}`, 'red');
    return false;
  }
}

async function testVersionEndpoint() {
  log('\n🔍 Testing /api/version endpoint...', 'blue');
  
  try {
    const response = await makeRequest('/api/version');
    
    if (response.statusCode !== 200) {
      log(`❌ Version endpoint returned status ${response.statusCode}`, 'red');
      return false;
    }
    
    const { data } = response;
    
    // Check if response has success field (from version routes)
    if (data.success !== true) {
      log(`❌ Version endpoint success field is not true`, 'red');
      return false;
    }
    
    const versionData = data.data;
    
    // Check required fields
    const requiredFields = ['service', 'commit', 'buildTime', 'nodeVersion'];
    const missingFields = requiredFields.filter(field => !(field in versionData));
    
    if (missingFields.length > 0) {
      log(`❌ Missing required fields: ${missingFields.join(', ')}`, 'red');
      return false;
    }
    
    log('✅ Version endpoint test PASSED', 'green');
    log(`   Service: ${versionData.service}`, 'cyan');
    log(`   Commit: ${versionData.commit}`, 'cyan');
    log(`   Build Time: ${versionData.buildTime}`, 'cyan');
    log(`   Node Version: ${versionData.nodeVersion}`, 'cyan');
    
    return true;
  } catch (error) {
    log(`❌ Version endpoint test FAILED: ${error.message}`, 'red');
    return false;
  }
}

async function waitForServer() {
  log('\n⏳ Waiting for server to start...', 'yellow');
  
  const maxAttempts = 30; // 30 seconds
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    try {
      await makeRequest('/health');
      log('✅ Server is responding', 'green');
      return true;
    } catch (error) {
      attempts++;
      if (attempts < maxAttempts) {
        log(`   Attempt ${attempts}/${maxAttempts} - waiting...`, 'yellow');
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }
  
  log('❌ Server did not start within timeout', 'red');
  return false;
}

async function runTests() {
  log('🧪 Backend Health Check Integration Test', 'cyan');
  log('==========================================', 'cyan');
  
  // Start server
  log('\n🚀 Starting backend server...', 'blue');
  const serverProcess = spawn('npm', ['start'], {
    env: { ...process.env, PORT: TEST_PORT },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  
  // Capture server output
  serverProcess.stdout.on('data', (data) => {
    const output = data.toString().trim();
    if (output.includes('Server running on port')) {
      log(`📊 ${output}`, 'green');
    }
  });
  
  serverProcess.stderr.on('data', (data) => {
    log(`⚠️ Server stderr: ${data.toString().trim()}`, 'yellow');
  });
  
  // Wait for server to start
  const serverReady = await waitForServer();
  if (!serverReady) {
    serverProcess.kill();
    process.exit(1);
  }
  
  // Run tests
  const healthTest = await testHealthEndpoint();
  const versionTest = await testVersionEndpoint();
  
  // Cleanup
  serverProcess.kill();
  
  // Results
  log('\n📊 Test Results:', 'cyan');
  log('================', 'cyan');
  log(`Health Endpoint: ${healthTest ? '✅ PASS' : '❌ FAIL'}`, healthTest ? 'green' : 'red');
  log(`Version Endpoint: ${versionTest ? '✅ PASS' : '❌ FAIL'}`, versionTest ? 'green' : 'red');
  
  const allPassed = healthTest && versionTest;
  log(`\nOverall: ${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`, allPassed ? 'green' : 'red');
  
  process.exit(allPassed ? 0 : 1);
}

// Handle process termination
process.on('SIGINT', () => {
  log('\n🛑 Test interrupted', 'yellow');
  process.exit(1);
});

process.on('SIGTERM', () => {
  log('\n🛑 Test terminated', 'yellow');
  process.exit(1);
});

// Run tests
runTests().catch(error => {
  log(`❌ Test runner error: ${error.message}`, 'red');
  process.exit(1);
});
