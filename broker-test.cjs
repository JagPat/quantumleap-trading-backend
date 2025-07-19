const puppeteer = require('puppeteer');

async function testBrokerIntegration() {
  console.log('🔍 Testing Broker Integration Functionality...\n');
  
  const browser = await puppeteer.launch({ 
    headless: false, // Show browser for debugging
    defaultViewport: { width: 1920, height: 1080 },
    devtools: true
  });
  
  const page = await browser.newPage();
  
  // Capture console logs
  const logs = [];
  page.on('console', (msg) => {
    logs.push({
      type: msg.type(),
      text: msg.text(),
      timestamp: new Date().toISOString()
    });
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });

  // Capture errors
  const errors = [];
  page.on('pageerror', (error) => {
    errors.push({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    });
    console.error(`[PAGE ERROR] ${error.message}`);
  });

  try {
    console.log('📍 Navigating to Broker Integration page...');
    await page.goto('http://localhost:3000/broker-integration', { 
      waitUntil: 'networkidle0',
      timeout: 15000 
    });
    
    console.log('⏳ Waiting for page to load...');
    await page.waitForSelector('body', { timeout: 10000 });
    
    // Test 1: Check if BrokerConfig API functions are available
    console.log('\n🧪 Test 1: BrokerConfig API Availability');
    const apiTest = await page.evaluate(async () => {
      try {
        const module = await import('/src/api/entities.js');
        const { BrokerConfig } = module;
        
        return {
          hasCreate: typeof BrokerConfig.create === 'function',
          hasList: typeof BrokerConfig.list === 'function',
          hasUpdate: typeof BrokerConfig.update === 'function',
          createType: typeof BrokerConfig.create,
          listType: typeof BrokerConfig.list,
          updateType: typeof BrokerConfig.update
        };
      } catch (error) {
        return { error: error.message, stack: error.stack };
      }
    });
    
    if (apiTest.error) {
      console.error(`❌ API Test Failed: ${apiTest.error}`);
    } else {
      console.log(`✅ BrokerConfig.create: ${apiTest.hasCreate ? 'Available' : 'Missing'} (${apiTest.createType})`);
      console.log(`✅ BrokerConfig.list: ${apiTest.hasList ? 'Available' : 'Missing'} (${apiTest.listType})`);
      console.log(`✅ BrokerConfig.update: ${apiTest.hasUpdate ? 'Available' : 'Missing'} (${apiTest.updateType})`);
    }
    
    // Test 2: Try calling BrokerConfig.list()
    console.log('\n🧪 Test 2: BrokerConfig.list() Function Call');
    const listTest = await page.evaluate(async () => {
      try {
        const module = await import('/src/api/entities.js');
        const { BrokerConfig } = module;
        
        const configs = await BrokerConfig.list();
        return {
          success: true,
          isArray: Array.isArray(configs),
          count: configs.length,
          configs: configs
        };
      } catch (error) {
        return { 
          success: false, 
          error: error.message, 
          stack: error.stack 
        };
      }
    });
    
    if (!listTest.success) {
      console.error(`❌ BrokerConfig.list() Failed: ${listTest.error}`);
    } else {
      console.log(`✅ BrokerConfig.list() Success: Found ${listTest.count} configs`);
      console.log(`✅ Return type: ${listTest.isArray ? 'Array' : 'Not Array'}`);
      if (listTest.count > 0) {
        console.log('📋 Configs:', JSON.stringify(listTest.configs, null, 2));
      }
    }
    
    // Test 3: Check UI elements
    console.log('\n🧪 Test 3: UI Elements and Status Display');
    const uiTest = await page.evaluate(() => {
      const statusBadges = Array.from(document.querySelectorAll('[class*="badge"], [class*="Badge"]'))
        .map(el => el.textContent.trim())
        .filter(text => text.length > 0);
      
      const statusTexts = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const text = el.textContent.toLowerCase();
          return (text.includes('connected') || text.includes('disconnected') || text.includes('status')) && 
                 el.children.length === 0 && text.length < 200;
        })
        .map(el => el.textContent.trim())
        .slice(0, 10);
      
      const refreshButton = document.querySelector('button[class*="refresh"], button:has([data-name="refresh"])');
      const checkBackendButton = document.querySelector('button:contains("Check Backend"), button[class*="backend"]');
      
      return {
        statusBadges,
        statusTexts,
        hasRefreshButton: !!refreshButton,
        hasCheckBackendButton: !!checkBackendButton,
        pageTitle: document.title,
        hasErrorMessage: document.body.innerText.includes('is not a function')
      };
    });
    
    console.log(`✅ Page Title: ${uiTest.pageTitle}`);
    console.log(`✅ Status Badges Found: ${uiTest.statusBadges.length} (${uiTest.statusBadges.join(', ')})`);
    console.log(`✅ Status Texts Found: ${uiTest.statusTexts.length}`);
    if (uiTest.statusTexts.length > 0) {
      uiTest.statusTexts.forEach((text, i) => {
        console.log(`   ${i + 1}. "${text}"`);
      });
    }
    console.log(`✅ Refresh Button: ${uiTest.hasRefreshButton ? 'Present' : 'Missing'}`);
    console.log(`✅ Check Backend Button: ${uiTest.hasCheckBackendButton ? 'Present' : 'Missing'}`);
    console.log(`✅ Function Error: ${uiTest.hasErrorMessage ? '❌ Found' : '✅ None'}`);
    
    // Test 4: Take screenshot
    console.log('\n📸 Taking screenshot...');
    await page.screenshot({ 
      path: 'broker-integration-test.png', 
      fullPage: true 
    });
    console.log('✅ Screenshot saved: broker-integration-test.png');
    
    // Test 5: Test refresh functionality
    console.log('\n🧪 Test 4: Testing Refresh Button');
    try {
      const refreshButton = await page.$('button:has-text("Refresh"), button[title*="refresh"], button[class*="refresh"]');
      if (refreshButton) {
        console.log('🔄 Clicking refresh button...');
        await refreshButton.click();
        await page.waitForTimeout(2000);
        console.log('✅ Refresh button clicked successfully');
      } else {
        console.log('⚠️ Refresh button not found or not clickable');
      }
    } catch (error) {
      console.log(`⚠️ Refresh test failed: ${error.message}`);
    }
    
    // Summary
    console.log('\n📊 Test Summary:');
    console.log(`- API Functions Available: ${apiTest.hasList && apiTest.hasCreate && apiTest.hasUpdate ? '✅' : '❌'}`);
    console.log(`- BrokerConfig.list() Works: ${listTest.success ? '✅' : '❌'}`);
    console.log(`- UI Elements Present: ${uiTest.statusBadges.length > 0 ? '✅' : '❌'}`);
    console.log(`- No Function Errors: ${!uiTest.hasErrorMessage ? '✅' : '❌'}`);
    console.log(`- Console Errors: ${errors.length === 0 ? '✅' : `❌ (${errors.length})`}`);
    
    if (errors.length > 0) {
      console.log('\n❌ Errors Found:');
      errors.forEach((error, i) => {
        console.log(`${i + 1}. ${error.message}`);
      });
    }
    
    const errorLogs = logs.filter(log => log.type === 'error');
    if (errorLogs.length > 0) {
      console.log('\n⚠️ Console Errors:');
      errorLogs.forEach((log, i) => {
        console.log(`${i + 1}. ${log.text}`);
      });
    }
    
  } catch (error) {
    console.error(`❌ Test Failed: ${error.message}`);
  } finally {
    console.log('\n🔚 Closing browser...');
    await browser.close();
  }
}

// Run the test
console.log('🚀 Starting Broker Integration Test...\n');
testBrokerIntegration().catch(console.error); 