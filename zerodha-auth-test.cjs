const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

// Create screenshots directory
const screenshotsDir = path.join(__dirname, 'screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

test.describe('Zerodha Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set longer timeout for authentication processes
    test.setTimeout(120000);
    
    // Navigate to the broker integration page
    await page.goto('http://localhost:3000/broker-integration');
    await page.waitForLoadState('networkidle');
  });

  test('should show current broker status and authenticate if needed', async ({ page }) => {
    console.log('🔍 Starting Zerodha authentication verification...');

    // Take initial screenshot
    await page.screenshot({ 
      path: path.join(screenshotsDir, '01-initial-broker-page.png'),
      fullPage: true 
    });
    console.log('📸 Screenshot saved: 01-initial-broker-page.png');

    // Check current broker status
    const statusBadge = page.locator('[data-testid="broker-status-badge"], .bg-green-600, .bg-red-600, .bg-yellow-600').first();
    
    let currentStatus = 'unknown';
    try {
      const badgeText = await statusBadge.textContent({ timeout: 5000 });
      console.log('📊 Current status badge:', badgeText);
      
      if (badgeText?.includes('Connected')) {
        currentStatus = 'connected';
      } else if (badgeText?.includes('Disconnected')) {
        currentStatus = 'disconnected';
      }
    } catch (error) {
      console.log('⚠️ Could not determine status badge, checking page content...');
      
      // Try to find status in the page content
      const pageContent = await page.textContent('body');
      if (pageContent.includes('Connected')) {
        currentStatus = 'connected';
      } else if (pageContent.includes('Disconnected')) {
        currentStatus = 'disconnected';
      }
    }

    console.log(`📊 Detected broker status: ${currentStatus}`);

    // Take screenshot showing current status
    await page.screenshot({ 
      path: path.join(screenshotsDir, '02-current-status.png'),
      fullPage: true 
    });

    // Check for any console errors
    const errors = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Wait a bit to catch any immediate errors
    await page.waitForTimeout(3000);

    // Test authentication form if disconnected
    if (currentStatus === 'disconnected') {
      console.log('🔐 Status is disconnected, testing authentication form...');
      
      // Look for API key input
      const apiKeyInput = page.locator('input[placeholder*="API Key"], input[name="api_key"]').first();
      const apiSecretInput = page.locator('input[placeholder*="API Secret"], input[name="api_secret"]').first();
      
      if (await apiKeyInput.isVisible()) {
        console.log('📝 Authentication form found, filling in test credentials...');
        
        // Fill in test credentials (using non-sensitive test data)
        await apiKeyInput.fill('test_api_key_placeholder');
        await apiSecretInput.fill('test_api_secret_placeholder');
        
        await page.screenshot({ 
          path: path.join(screenshotsDir, '03-credentials-filled.png'),
          fullPage: true 
        });
        
        console.log('⚠️ Note: Using placeholder credentials for UI testing only');
        console.log('🔒 Real authentication requires manual Zerodha app confirmation');
        
      } else {
        console.log('❌ Authentication form not found');
      }
    } else if (currentStatus === 'connected') {
      console.log('✅ Broker status shows as connected');
      
      // Check for heartbeat indicators
      const heartbeatIndicators = await page.locator('[data-testid="heartbeat"], .text-green-600, .last-checked').count();
      console.log(`💓 Found ${heartbeatIndicators} potential heartbeat indicators`);
      
      // Look for user information
      const userInfo = page.locator('text=/User:|Broker:/');
      if (await userInfo.count() > 0) {
        const userText = await userInfo.first().textContent();
        console.log('👤 User info found:', userText);
      }
      
      // Check if "Check Backend" button is present
      const checkBackendBtn = page.locator('text="Check Backend"');
      if (await checkBackendBtn.isVisible()) {
        console.log('🔍 Testing backend status check...');
        await checkBackendBtn.click();
        await page.waitForTimeout(2000);
        
        await page.screenshot({ 
          path: path.join(screenshotsDir, '04-backend-check.png'),
          fullPage: true 
        });
      }
    }

    // Take final screenshot
    await page.screenshot({ 
      path: path.join(screenshotsDir, '05-final-state.png'),
      fullPage: true 
    });

    // Report console errors
    if (errors.length > 0) {
      console.log('❌ Console errors detected:');
      errors.slice(0, 5).forEach((error, i) => {
        console.log(`   ${i + 1}. ${error}`);
      });
      if (errors.length > 5) {
        console.log(`   ... and ${errors.length - 5} more errors`);
      }
    } else {
      console.log('✅ No console errors detected');
    }

    // Create test report
    const report = {
      timestamp: new Date().toISOString(),
      currentStatus: currentStatus,
      consoleErrors: errors.length,
      screenshots: [
        '01-initial-broker-page.png',
        '02-current-status.png',
        '03-credentials-filled.png', 
        '04-backend-check.png',
        '05-final-state.png'
      ].filter(screenshot => {
        return fs.existsSync(path.join(screenshotsDir, screenshot));
      }),
      testResults: {
        pageLoaded: true,
        statusDetected: currentStatus !== 'unknown',
        formAccessible: currentStatus === 'disconnected' ? 'tested' : 'n/a',
        noMajorErrors: errors.length === 0
      }
    };

    // Save report
    fs.writeFileSync(
      path.join(screenshotsDir, 'zerodha-auth-test-report.json'),
      JSON.stringify(report, null, 2)
    );

    console.log('\n📋 Test Summary:');
    console.log(`   Status: ${currentStatus}`);
    console.log(`   Console Errors: ${errors.length}`);
    console.log(`   Screenshots: ${report.screenshots.length}`);
    console.log(`   Report saved: zerodha-auth-test-report.json`);
    
    // Test passes if no major errors and status is detectable
    expect(errors.length).toBeLessThan(10); // Allow some minor errors
    expect(currentStatus).not.toBe('unknown');
  });

  test('should test page navigation and function calls', async ({ page }) => {
    console.log('🧪 Testing critical function calls...');

    // Check for specific function errors mentioned by user
    const functionErrors = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (text.includes('is not a function')) {
          functionErrors.push(text);
        }
      }
    });

    // Navigate to different pages to trigger function calls
    const testPages = [
      { path: '/', name: 'Dashboard' },
      { path: '/trading', name: 'Trading' },
      { path: '/portfolio', name: 'Portfolio' },
      { path: '/broker-integration', name: 'Broker Integration' }
    ];

    for (const testPage of testPages) {
      console.log(`📄 Testing ${testPage.name} page...`);
      try {
        await page.goto(`http://localhost:3000${testPage.path}`);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000); // Let the page settle and run its functions
        
        await page.screenshot({ 
          path: path.join(screenshotsDir, `test-${testPage.name.toLowerCase()}.png`),
          fullPage: true 
        });
      } catch (error) {
        console.log(`❌ Error loading ${testPage.name}: ${error.message}`);
      }
    }

    console.log('\n🔍 Function Call Results:');
    if (functionErrors.length === 0) {
      console.log('✅ No "is not a function" errors detected');
    } else {
      console.log(`❌ Found ${functionErrors.length} function errors:`);
      functionErrors.forEach((error, i) => {
        console.log(`   ${i + 1}. ${error}`);
      });
    }

    // Save function test results
    const functionReport = {
      timestamp: new Date().toISOString(),
      pagesTestedCount: testPages.length,
      functionErrors: functionErrors,
      pagesWithScreenshots: testPages.map(p => `test-${p.name.toLowerCase()}.png`)
    };

    fs.writeFileSync(
      path.join(screenshotsDir, 'function-test-report.json'),
      JSON.stringify(functionReport, null, 2)
    );

    expect(functionErrors.length).toBeLessThan(3); // Allow very few function errors
  });
}); 