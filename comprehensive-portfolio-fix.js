// Comprehensive Portfolio Connection Fix
// This script will diagnose and fix the frontend-backend portfolio connection issue
// Run this in browser console on http://localhost:5173

async function comprehensivePortfolioFix() {
  console.log("🔧 COMPREHENSIVE PORTFOLIO CONNECTION FIX");
  console.log("===========================================\n");

  // Step 1: Analyze Current State
  console.log("1️⃣ ANALYZING CURRENT STATE...");
  
  // Check broker configs
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  console.log("📋 Broker configs found:", brokerConfigs.length);
  
  if (brokerConfigs.length === 0) {
    console.error("❌ CRITICAL: No broker configs found!");
    console.log("🔧 SOLUTION: Run fix-auth-state.js first to complete authentication");
    return;
  }

  // Find active config
  const activeConfig = brokerConfigs.find(config => config.is_connected && config.access_token);
  
  if (!activeConfig) {
    console.error("❌ CRITICAL: No active broker config with access_token!");
    
    // Try to find any config with credentials
    const configWithCreds = brokerConfigs.find(config => config.api_key && config.api_secret);
    
    if (configWithCreds) {
      console.log("🔧 Found config with credentials but missing access_token");
      console.log("🔧 SOLUTION: Re-authenticate to get access_token");
      
      // Show how to fix
      console.log("\nTo fix this, run the following in console:");
      console.log("1. Go to Broker Integration page");
      console.log("2. Click 'Save & Authenticate' button");
      console.log("3. Complete OAuth flow");
      console.log("4. Or run fix-auth-state.js script");
    }
    return;
  }

  console.log("✅ Active config found:");
  console.log("  - User ID:", activeConfig.user_data?.user_id);
  console.log("  - API Key:", activeConfig.api_key?.substring(0, 8) + "...");
  console.log("  - Has Access Token:", !!activeConfig.access_token);
  console.log("  - Connection Status:", activeConfig.connection_status);

  // Step 2: Test Backend Connectivity
  console.log("\n2️⃣ TESTING BACKEND CONNECTIVITY...");
  
  try {
    const healthResponse = await fetch('https://web-production-de0bc.up.railway.app/health');
    const healthData = await healthResponse.json();
    console.log("✅ Backend health:", healthData);
  } catch (error) {
    console.error("❌ Backend connectivity failed:", error);
    console.log("🔧 SOLUTION: Check your internet connection and try again");
    return;
  }

  // Step 3: Test Authentication Headers
  console.log("\n3️⃣ TESTING AUTHENTICATION HEADERS...");
  
  const userId = activeConfig.user_data?.user_id;
  if (!userId || userId === 'unknown') {
    console.error("❌ Invalid user_id:", userId);
    console.log("🔧 SOLUTION: Re-authenticate to get proper user_id");
    return;
  }

  const authHeaders = {
    'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
    'X-User-ID': userId,
    'Content-Type': 'application/json'
  };

  console.log("📡 Authentication headers prepared:");
  console.log("  - Authorization format: token api_key:access_token");
  console.log("  - X-User-ID:", authHeaders['X-User-ID']);

  // Step 4: Test Individual Endpoints
  console.log("\n4️⃣ TESTING INDIVIDUAL ENDPOINTS...");
  
  // Test holdings endpoint
  console.log("📊 Testing holdings endpoint...");
  try {
    const holdingsUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`;
    console.log("  URL:", holdingsUrl);
    
    const holdingsResponse = await fetch(holdingsUrl, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("  Status:", holdingsResponse.status);
    
    if (holdingsResponse.ok) {
      const holdingsData = await holdingsResponse.json();
      console.log("✅ Holdings endpoint working!");
      console.log("  Data preview:", {
        status: holdingsData.status,
        count: holdingsData.data?.length || 0
      });
    } else {
      const errorData = await holdingsResponse.json().catch(() => ({ detail: holdingsResponse.statusText }));
      console.error("❌ Holdings endpoint failed:", errorData);
      
      if (holdingsResponse.status === 401) {
        console.log("🔍 401 Error Analysis:");
        console.log("  - Backend expects: Authorization: token api_key:access_token");
        console.log("  - Backend expects: X-User-ID header");
        console.log("  - User credentials might not be stored in backend database");
        console.log("  - Access token might be expired or invalid");
      }
    }
  } catch (error) {
    console.error("❌ Holdings endpoint error:", error);
  }

  // Test positions endpoint
  console.log("\n📈 Testing positions endpoint...");
  try {
    const positionsUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/positions?user_id=${userId}`;
    const positionsResponse = await fetch(positionsUrl, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("  Status:", positionsResponse.status);
    
    if (positionsResponse.ok) {
      const positionsData = await positionsResponse.json();
      console.log("✅ Positions endpoint working!");
      console.log("  Data preview:", {
        status: positionsData.status,
        net_positions: positionsData.data?.net?.length || 0,
        day_positions: positionsData.data?.day?.length || 0
      });
    } else {
      const errorData = await positionsResponse.json().catch(() => ({ detail: positionsResponse.statusText }));
      console.error("❌ Positions endpoint failed:", errorData);
    }
  } catch (error) {
    console.error("❌ Positions endpoint error:", error);
  }

  // Step 5: Test Combined Portfolio Data Endpoint (Phase 1 Enhanced)
  console.log("\n5️⃣ TESTING ENHANCED PORTFOLIO DATA ENDPOINT...");
  try {
    const portfolioUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/data`;
    const portfolioResponse = await fetch(portfolioUrl, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("  Status:", portfolioResponse.status);
    
    if (portfolioResponse.ok) {
      const portfolioData = await portfolioResponse.json();
      console.log("🎉 ENHANCED PORTFOLIO DATA WORKING!");
      console.log("  Status:", portfolioData.status);
      
      if (portfolioData.status === 'success' && portfolioData.data) {
        console.log("📊 Portfolio Summary:");
        console.log("  - Total Value:", portfolioData.data.summary?.total_value || 0);
        console.log("  - Total P&L:", portfolioData.data.summary?.total_pnl || 0);
        console.log("  - P&L %:", portfolioData.data.summary?.total_pnl_percentage || 0);
        console.log("  - Holdings Count:", portfolioData.data.holdings?.length || 0);
        console.log("  - Net Positions:", portfolioData.data.positions?.net?.length || 0);
        
        // Check for Phase 1 enhanced fields
        if (portfolioData.data.holdings?.length > 0) {
          const sampleHolding = portfolioData.data.holdings[0];
          console.log("📈 Phase 1 Enhanced Fields Check:");
          console.log("  - pnl_percentage:", 'pnl_percentage' in sampleHolding ? "✅" : "❌");
          console.log("  - current_value:", 'current_value' in sampleHolding ? "✅" : "❌");
          console.log("  - invested_amount:", 'invested_amount' in sampleHolding ? "✅" : "❌");
          console.log("  - fetch_timestamp:", 'fetch_timestamp' in sampleHolding ? "✅" : "❌");
        }
      }
    } else {
      const errorData = await portfolioResponse.json().catch(() => ({ detail: portfolioResponse.statusText }));
      console.error("❌ Portfolio data endpoint failed:", errorData);
    }
  } catch (error) {
    console.error("❌ Portfolio data endpoint error:", error);
  }

  // Step 6: Test Frontend RailwayAPI Function
  console.log("\n6️⃣ TESTING FRONTEND RAILWAYAPI FUNCTION...");
  
  try {
    // Simulate the frontend's getAuthHeaders function
    const configs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
    const activeConfig = configs.find(config => config.is_connected && config.access_token);
    
    if (activeConfig && activeConfig.api_key && activeConfig.access_token) {
      const frontendHeaders = {
        'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
        'X-User-ID': activeConfig.user_data?.user_id || 'unknown'
      };
      
      console.log("✅ Frontend would generate these headers:");
      console.log("  - Authorization:", frontendHeaders.Authorization.substring(0, 30) + "...");
      console.log("  - X-User-ID:", frontendHeaders['X-User-ID']);
      
      // Test if frontend would detect authentication
      if (!frontendHeaders.Authorization || !frontendHeaders['X-User-ID']) {
        console.error("❌ Frontend would fail authentication check");
      } else {
        console.log("✅ Frontend authentication headers look good");
      }
    } else {
      console.error("❌ Frontend would not find active broker configuration");
    }
  } catch (error) {
    console.error("❌ Frontend simulation error:", error);
  }

  // Step 7: Provide Solutions
  console.log("\n7️⃣ SOLUTIONS AND NEXT STEPS...");
  
  console.log("🎯 If all tests passed:");
  console.log("  - Your Portfolio connection should work!");
  console.log("  - Try clicking 'Fetch Live Data' in the app");
  console.log("  - You should see Phase 1 enhanced features");
  
  console.log("\n🔧 If tests failed:");
  console.log("  - Check console output above for specific errors");
  console.log("  - Most likely cause: Authentication not completed");
  console.log("  - Solution: Run fix-auth-state.js to complete auth");
  
  console.log("\n📋 Phase 1 Features to Test:");
  console.log("  - 5-stage progress tracking during data fetch");
  console.log("  - Enhanced data fields: pnl_percentage, current_value, etc.");
  console.log("  - Toast notifications for success/error states");
  console.log("  - Retry logic with exponential backoff");
  console.log("  - Data freshness timestamps");

  console.log("\n✅ COMPREHENSIVE DIAGNOSTIC COMPLETE!");
}

// Make the function available globally
window.comprehensivePortfolioFix = comprehensivePortfolioFix;

// Auto-run the diagnostic
console.log("🚀 Starting Comprehensive Portfolio Connection Fix...");
comprehensivePortfolioFix(); 