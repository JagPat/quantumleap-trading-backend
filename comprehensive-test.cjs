const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Comprehensive test for QuantumLeap Trading frontend
async function runComprehensiveTests() {
  console.log('🚀 Starting Comprehensive Frontend Tests...\n');
  
  const results = {
    totalTests: 0,
    passedTests: 0,
    failedTests: 0,
    errors: [],
    routes: [],
    consoleErrors: []
  };

  const browser = await puppeteer.launch({ 
    headless: true, 
    defaultViewport: { width: 1920, height: 1080 }
  });
  
  const page = await browser.newPage();
  
  // Capture console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      results.consoleErrors.push({
        text: msg.text(),
        url: page.url(),
        timestamp: new Date().toISOString()
      });
    }
  });

  // Capture JavaScript errors
  page.on('pageerror', (error) => {
    results.errors.push({
      message: error.message,
      stack: error.stack,
      url: page.url(),
      timestamp: new Date().toISOString()
    });
  });

  const baseUrl = 'http://localhost:3000';
  
  // Define all routes to test
  const routes = [
    { path: '/', name: 'Home/Dashboard' },
    { path: '/portfolio', name: 'Portfolio' },
    { path: '/trading', name: 'Trading' },
    { path: '/trade-history', name: 'Trade History' },
    { path: '/broker-integration', name: 'Broker Integration' },
    { path: '/settings', name: 'Settings' },
    { path: '/widgets', name: 'Widgets' },
    { path: '/strategy-detail', name: 'Strategy Detail' },
    { path: '/broker/callback', name: 'Broker Callback' }
  ];

  console.log('🔍 Testing Route Accessibility...\n');

  for (const route of routes) {
    results.totalTests++;
    try {
      console.log(`📍 Testing ${route.name} (${route.path})...`);
      
      await page.goto(`${baseUrl}${route.path}`, { 
        waitUntil: 'networkidle0',
        timeout: 10000 
      });
      
      // Wait for React to load
      await page.waitForSelector('body', { timeout: 5000 });
      
      // Check if page loaded successfully (not 404 or blank)
      const title = await page.title();
      const bodyText = await page.evaluate(() => document.body.innerText);
      
      if (bodyText.includes('404') || bodyText.includes('Not Found') || bodyText.trim().length < 10) {
        throw new Error(`Page appears to be 404 or empty. Body text: ${bodyText.substring(0, 100)}...`);
      }
      
      // Take screenshot
      const screenshotPath = `screenshots/route-${route.path.replace(/\//g, '_')}.png`;
      await page.screenshot({ 
        path: screenshotPath, 
        fullPage: true 
      });
      
      results.routes.push({
        ...route,
        status: 'success',
        title: title,
        screenshot: screenshotPath,
        bodyLength: bodyText.length
      });
      
      results.passedTests++;
      console.log(`✅ ${route.name} - OK (Title: "${title}")`);
      
    } catch (error) {
      results.failedTests++;
      results.routes.push({
        ...route,
        status: 'failed',
        error: error.message
      });
      console.log(`❌ ${route.name} - FAILED: ${error.message}`);
    }
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  console.log('\n🧪 Testing Broker Configuration API...\n');
  
  // Test BrokerConfig API functionality
  results.totalTests++;
  try {
    await page.goto(`${baseUrl}/broker-integration`, { waitUntil: 'networkidle0' });
    
    // Test if BrokerConfig functions are available
    const apiTest = await page.evaluate(async () => {
      try {
        // Import the entities module
        const module = await import('/src/api/entities.js');
        const { BrokerConfig } = module;
        
        // Test if methods exist
        const results = {
          hasCreate: typeof BrokerConfig.create === 'function',
          hasList: typeof BrokerConfig.list === 'function',
          hasUpdate: typeof BrokerConfig.update === 'function'
        };
        
        // Test list function
        const configs = await BrokerConfig.list();
        results.listWorks = Array.isArray(configs);
        results.configCount = configs.length;
        
        return results;
      } catch (error) {
        return { error: error.message, stack: error.stack };
      }
    });
    
    if (apiTest.error) {
      throw new Error(`BrokerConfig API Error: ${apiTest.error}`);
    }
    
    if (!apiTest.hasList) {
      throw new Error('BrokerConfig.list function does not exist');
    }
    
    if (!apiTest.listWorks) {
      throw new Error('BrokerConfig.list() did not return an array');
    }
    
    console.log(`✅ BrokerConfig API - OK (Methods: create=${apiTest.hasCreate}, list=${apiTest.hasList}, update=${apiTest.hasUpdate})`);
    console.log(`📋 Current configs in storage: ${apiTest.configCount}`);
    results.passedTests++;
    
  } catch (error) {
    results.failedTests++;
    console.log(`❌ BrokerConfig API - FAILED: ${error.message}`);
    results.errors.push({
      test: 'BrokerConfig API',
      message: error.message,
      timestamp: new Date().toISOString()
    });
  }

  console.log('\n🔐 Testing Authentication Status Detection...\n');
  
  // Test authentication status
  results.totalTests++;
  try {
    await page.goto(`${baseUrl}/broker-integration`, { waitUntil: 'networkidle0' });
    
    // Wait for components to load
    await page.waitForSelector('[data-testid="connection-status"], .trading-card, .text-slate-600', { timeout: 5000 });
    
    // Check for connection status indicators
    const statusInfo = await page.evaluate(() => {
      // Look for status indicators
      const badges = Array.from(document.querySelectorAll('.badge, [class*="badge"], [class*="Badge"]'))
        .map(el => el.textContent.trim());
      
      const statusTexts = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const text = el.textContent.toLowerCase();
          return text.includes('connected') || text.includes('disconnected') || text.includes('status');
        })
        .map(el => el.textContent.trim())
        .slice(0, 10); // Limit to first 10 matches
      
      return {
        badges,
        statusTexts,
        bodyText: document.body.innerText.substring(0, 1000)
      };
    });
    
    console.log(`📊 Status Detection: Found ${statusInfo.badges.length} badges, ${statusInfo.statusTexts.length} status texts`);
    
    if (statusInfo.badges.length > 0) {
      console.log(`🏷️ Status badges: ${statusInfo.badges.join(', ')}`);
    }
    
    results.passedTests++;
    console.log(`✅ Authentication Status UI - OK`);
    
  } catch (error) {
    results.failedTests++;
    console.log(`❌ Authentication Status UI - FAILED: ${error.message}`);
  }

  await browser.close();

  // Generate comprehensive report
  console.log('\n📊 COMPREHENSIVE TEST RESULTS\n');
  console.log('='.repeat(50));
  console.log(`Total Tests: ${results.totalTests}`);
  console.log(`Passed: ${results.passedTests}`);
  console.log(`Failed: ${results.failedTests}`);
  console.log(`Success Rate: ${((results.passedTests / results.totalTests) * 100).toFixed(1)}%`);
  
  if (results.consoleErrors.length > 0) {
    console.log(`\n⚠️ Console Errors Found: ${results.consoleErrors.length}`);
    results.consoleErrors.slice(0, 5).forEach((error, i) => {
      console.log(`${i + 1}. ${error.text} (${error.url})`);
    });
    if (results.consoleErrors.length > 5) {
      console.log(`... and ${results.consoleErrors.length - 5} more`);
    }
  }
  
  if (results.errors.length > 0) {
    console.log(`\n❌ JavaScript Errors Found: ${results.errors.length}`);
    results.errors.slice(0, 3).forEach((error, i) => {
      console.log(`${i + 1}. ${error.message}`);
    });
  }
  
  console.log('\n📍 Route Test Summary:');
  results.routes.forEach(route => {
    const status = route.status === 'success' ? '✅' : '❌';
    console.log(`${status} ${route.name} (${route.path})`);
    if (route.error) {
      console.log(`   Error: ${route.error}`);
    }
  });

  // Save detailed report
  const reportData = {
    timestamp: new Date().toISOString(),
    summary: {
      totalTests: results.totalTests,
      passedTests: results.passedTests,
      failedTests: results.failedTests,
      successRate: ((results.passedTests / results.totalTests) * 100).toFixed(1)
    },
    routes: results.routes,
    consoleErrors: results.consoleErrors,
    javascriptErrors: results.errors
  };
  
  fs.writeFileSync('test-report.json', JSON.stringify(reportData, null, 2));
  console.log('\n📄 Detailed report saved to test-report.json');
  
  // Create screenshots directory if it doesn't exist
  if (!fs.existsSync('screenshots')) {
    fs.mkdirSync('screenshots');
  }
  
  console.log('📸 Screenshots saved to screenshots/ directory');
  console.log('\n🎯 CRITICAL ISSUES TO ADDRESS:');
  
  if (results.failedTests > 0) {
    console.log(`- ${results.failedTests} route(s) failed to load`);
  }
  
  if (results.consoleErrors.length > 0) {
    console.log(`- ${results.consoleErrors.length} console error(s) found`);
  }
  
  if (results.errors.length > 0) {
    console.log(`- ${results.errors.length} JavaScript error(s) found`);
  }
  
  if (results.failedTests === 0 && results.consoleErrors.length === 0 && results.errors.length === 0) {
    console.log('🎉 ALL TESTS PASSED! Frontend is working correctly.');
  }
  
  return results;
}

// Run the tests
runComprehensiveTests().catch(console.error); 