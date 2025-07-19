// Portfolio Connection Diagnostic and Fix Tool
// Run this in browser console on http://localhost:5173

async function testPortfolioConnection() {
  console.log("🔧 Testing Portfolio Connection...");
  console.log("=====================================\n");

  // Step 1: Check Broker Configuration
  console.log("1️⃣ Checking Broker Configuration...");
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  console.log("📋 Found broker configs:", brokerConfigs.length);

  if (brokerConfigs.length === 0) {
    console.error("❌ No broker configs found!");
    console.log("🔧 Solution: Go to Broker Integration and complete authentication");
    return;
  }

  const activeConfig = brokerConfigs.find(config => config.is_connected && config.access_token);
  console.log("✅ Active config found:", !!activeConfig);

  if (!activeConfig) {
    console.error("❌ No active broker config with access_token!");
    console.log("🔧 Solution: Complete authentication or run fix-auth-state.js");
    
    // Show config details for debugging
    brokerConfigs.forEach((config, index) => {
      console.log(`Config ${index}:`, {
        is_connected: config.is_connected,
        has_access_token: !!config.access_token,
        user_id: config.user_data?.user_id
      });
    });
    return;
  }

  console.log("✅ Active broker config details:");
  console.log("  - User ID:", activeConfig.user_data?.user_id);
  console.log("  - API Key:", activeConfig.api_key?.substring(0, 8) + "...");
  console.log("  - Access Token:", activeConfig.access_token?.substring(0, 20) + "...");

  // Step 2: Test Authentication Headers
  console.log("\n2️⃣ Testing Authentication Headers...");
  const authHeaders = {
    'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
    'X-User-ID': activeConfig.user_data?.user_id || 'unknown',
    'Content-Type': 'application/json'
  };

  console.log("📡 Auth headers to be sent:");
  console.log("  - Authorization:", authHeaders.Authorization.substring(0, 30) + "...");
  console.log("  - X-User-ID:", authHeaders['X-User-ID']);

  // Step 3: Test Backend Health
  console.log("\n3️⃣ Testing Backend Health...");
  try {
    const healthResponse = await fetch('https://web-production-de0bc.up.railway.app/health');
    const healthData = await healthResponse.json();
    console.log("✅ Backend health:", healthData);
  } catch (error) {
    console.error("❌ Backend health check failed:", error);
    return;
  }

  // Step 4: Test Portfolio Endpoints
  console.log("\n4️⃣ Testing Portfolio Endpoints...");
  
  const userId = activeConfig.user_data?.user_id;
  
  // Test holdings endpoint
  console.log("Testing holdings endpoint...");
  try {
    const holdingsResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("📡 Holdings response status:", holdingsResponse.status);
    
    if (holdingsResponse.ok) {
      const holdingsData = await holdingsResponse.json();
      console.log("✅ Holdings data received:", holdingsData);
    } else {
      const errorData = await holdingsResponse.json().catch(() => ({ detail: holdingsResponse.statusText }));
      console.error("❌ Holdings request failed:", errorData);
      
      // Show detailed error analysis
      if (holdingsResponse.status === 401) {
        console.log("🔍 401 Unauthorized Analysis:");
        console.log("  - Check if access_token is valid");
        console.log("  - Verify header format: 'Authorization: token api_key:access_token'");
        console.log("  - Ensure user_id matches authenticated user");
      }
    }
  } catch (error) {
    console.error("❌ Holdings request error:", error);
  }

  // Test positions endpoint
  console.log("\nTesting positions endpoint...");
  try {
    const positionsResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/positions?user_id=${userId}`, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("📡 Positions response status:", positionsResponse.status);
    
    if (positionsResponse.ok) {
      const positionsData = await positionsResponse.json();
      console.log("✅ Positions data received:", positionsData);
    } else {
      const errorData = await positionsResponse.json().catch(() => ({ detail: positionsResponse.statusText }));
      console.error("❌ Positions request failed:", errorData);
    }
  } catch (error) {
    console.error("❌ Positions request error:", error);
  }

  // Step 5: Test Combined Portfolio Data Endpoint
  console.log("\n5️⃣ Testing Combined Portfolio Data Endpoint...");
  try {
    const portfolioResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/data`, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("📡 Portfolio data response status:", portfolioResponse.status);
    
    if (portfolioResponse.ok) {
      const portfolioData = await portfolioResponse.json();
      console.log("✅ Portfolio data received:", portfolioData);
      
      if (portfolioData.status === 'success') {
        console.log("\n🎉 SUCCESS! Portfolio connection is working!");
        console.log("📊 Data summary:");
        console.log("  - Holdings count:", portfolioData.data.holdings?.length || 0);
        console.log("  - Positions count:", portfolioData.data.positions?.net?.length || 0);
        console.log("  - Total value:", portfolioData.data.summary?.total_value || 0);
      }
    } else {
      const errorData = await portfolioResponse.json().catch(() => ({ detail: portfolioResponse.statusText }));
      console.error("❌ Portfolio data request failed:", errorData);
    }
  } catch (error) {
    console.error("❌ Portfolio data request error:", error);
  }

  console.log("\n📋 Diagnostic Complete!");
  console.log("=====================================");
}

// Step 6: Quick Fix Function
async function quickFixPortfolioConnection() {
  console.log("🔧 Quick Fix: Updating RailwayAPI headers...");
  
  // Test the current frontend API function
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  const activeConfig = brokerConfigs.find(config => config.is_connected && config.access_token);
  
  if (!activeConfig) {
    console.error("❌ No active config found for quick fix");
    return;
  }

  // Test the actual frontend API call
  try {
    console.log("🧪 Testing frontend API function...");
    
    // Simulate the frontend's getPortfolioData call
    const userId = activeConfig.user_data?.user_id;
    
    // This should work if everything is configured correctly
    const testResult = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`, {
      method: 'GET',
      headers: {
        'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
        'X-User-ID': activeConfig.user_data?.user_id || 'unknown',
        'Content-Type': 'application/json'
      }
    });
    
    if (testResult.ok) {
      console.log("✅ Quick fix successful! Frontend should work now.");
      console.log("🎯 Try clicking 'Fetch Live Data' in the app");
    } else {
      const errorData = await testResult.json().catch(() => ({ detail: testResult.statusText }));
      console.error("❌ Quick fix failed:", errorData);
    }
    
  } catch (error) {
    console.error("❌ Quick fix error:", error);
  }
}

// Run the diagnostic
console.log("Starting Portfolio Connection Diagnostic...");
testPortfolioConnection().then(() => {
  console.log("\n🔧 Want to try a quick fix? Run: quickFixPortfolioConnection()");
});

// Make functions available in console
window.testPortfolioConnection = testPortfolioConnection;
window.quickFixPortfolioConnection = quickFixPortfolioConnection; 