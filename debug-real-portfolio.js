// Debug Real Portfolio Import Issue
// Run this in browser console to find why your 36 holdings aren't showing

async function debugRealPortfolioImport() {
  console.log("🔍 DEBUGGING REAL PORTFOLIO IMPORT ISSUE");
  console.log("=========================================");
  console.log("Expected: 36 holdings with ₹5.16 crores value");
  console.log("Actual: ₹0.00 and empty table\n");

  // Step 1: Get authentication details
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  const activeConfig = brokerConfigs.find(config => config.is_connected && config.access_token);
  
  if (!activeConfig) {
    console.error("❌ CRITICAL: No active broker config found");
    return;
  }

  console.log("✅ Authentication Details:");
  console.log("  - User ID:", activeConfig.user_data?.user_id);
  console.log("  - API Key:", activeConfig.api_key?.substring(0, 8) + "...");
  console.log("  - Has Access Token:", !!activeConfig.access_token);
  console.log("  - Token Length:", activeConfig.access_token?.length);

  const userId = activeConfig.user_data?.user_id;
  const authHeaders = {
    'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
    'X-User-ID': userId,
    'Content-Type': 'application/json'
  };

  // Step 2: Test Raw Backend Response
  console.log("\n📡 TESTING RAW BACKEND RESPONSES...");
  
  try {
    // Test holdings endpoint directly
    console.log("🔍 Testing Holdings Endpoint...");
    const holdingsUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`;
    console.log("  URL:", holdingsUrl);
    
    const holdingsResponse = await fetch(holdingsUrl, {
      method: 'GET',
      headers: authHeaders
    });

    console.log("  Response Status:", holdingsResponse.status);
    console.log("  Response Headers:", Object.fromEntries(holdingsResponse.headers.entries()));

    if (holdingsResponse.ok) {
      const holdingsData = await holdingsResponse.json();
      console.log("✅ RAW HOLDINGS RESPONSE:");
      console.log(JSON.stringify(holdingsData, null, 2));
      
      // Analyze the response
      if (holdingsData.status === 'success') {
        const holdings = holdingsData.data || [];
        console.log("\n📊 HOLDINGS ANALYSIS:");
        console.log("  - Status:", holdingsData.status);
        console.log("  - Holdings Count:", holdings.length);
        console.log("  - Expected Count: 36");
        
        if (holdings.length === 0) {
          console.error("❌ PROBLEM: Backend returned empty holdings array!");
          console.log("🔍 Possible causes:");
          console.log("  1. Backend can't authenticate with Zerodha");
          console.log("  2. Backend getting empty response from Zerodha API");
          console.log("  3. Backend database lookup failing");
          console.log("  4. User credentials not stored properly in backend");
        } else if (holdings.length < 36) {
          console.log("⚠️ PARTIAL DATA: Got", holdings.length, "out of 36 expected holdings");
          console.log("📋 Sample holding:", holdings[0]);
        } else {
          console.log("🎉 SUCCESS: Got all", holdings.length, "holdings!");
          console.log("📋 Sample holding:", holdings[0]);
          
          // Check for enhanced fields
          if (holdings[0]) {
            const sample = holdings[0];
            console.log("🎯 Enhanced Fields Check:");
            console.log("  - pnl_percentage:", sample.pnl_percentage || 'MISSING');
            console.log("  - current_value:", sample.current_value || 'MISSING');
            console.log("  - invested_amount:", sample.invested_amount || 'MISSING');
            console.log("  - fetch_timestamp:", sample.fetch_timestamp || 'MISSING');
          }
        }
      } else {
        console.error("❌ Backend returned error status:", holdingsData.status);
        console.log("Error details:", holdingsData);
      }
    } else {
      const errorText = await holdingsResponse.text();
      console.error("❌ HOLDINGS REQUEST FAILED:");
      console.log("  Status:", holdingsResponse.status);
      console.log("  Error:", errorText);
      
      if (holdingsResponse.status === 401) {
        console.log("🔍 401 UNAUTHORIZED ANALYSIS:");
        console.log("  - Check if backend recognizes user_id:", userId);
        console.log("  - Check if access_token is valid");
        console.log("  - Check if backend has user credentials stored");
      }
    }
  } catch (error) {
    console.error("💥 HOLDINGS REQUEST ERROR:", error);
  }

  // Step 3: Test Positions Endpoint
  console.log("\n📈 TESTING POSITIONS ENDPOINT...");
  try {
    const positionsUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/positions?user_id=${userId}`;
    const positionsResponse = await fetch(positionsUrl, {
      method: 'GET',
      headers: authHeaders
    });

    if (positionsResponse.ok) {
      const positionsData = await positionsResponse.json();
      console.log("✅ RAW POSITIONS RESPONSE:");
      console.log(JSON.stringify(positionsData, null, 2));
    } else {
      const errorText = await positionsResponse.text();
      console.error("❌ POSITIONS REQUEST FAILED:", positionsResponse.status, errorText);
    }
  } catch (error) {
    console.error("💥 POSITIONS REQUEST ERROR:", error);
  }

  // Step 4: Test Enhanced Portfolio Endpoint
  console.log("\n🚀 TESTING ENHANCED PORTFOLIO ENDPOINT...");
  try {
    const portfolioUrl = `https://web-production-de0bc.up.railway.app/api/portfolio/data`;
    const portfolioResponse = await fetch(portfolioUrl, {
      method: 'GET',
      headers: authHeaders
    });

    if (portfolioResponse.ok) {
      const portfolioData = await portfolioResponse.json();
      console.log("🎉 ENHANCED PORTFOLIO RESPONSE:");
      console.log(JSON.stringify(portfolioData, null, 2));
      
      if (portfolioData.status === 'success') {
        const summary = portfolioData.data?.summary;
        console.log("\n📊 SUMMARY CHECK:");
        console.log("  - Total Value:", summary?.total_value || 0);
        console.log("  - Expected: ~51,600,000 (₹5.16 crores)");
        console.log("  - Holdings Count:", portfolioData.data?.holdings?.length || 0);
        console.log("  - Expected: 36");
      }
    } else {
      const errorText = await portfolioResponse.text();
      console.error("❌ PORTFOLIO REQUEST FAILED:", portfolioResponse.status, errorText);
    }
  } catch (error) {
    console.error("💥 PORTFOLIO REQUEST ERROR:", error);
  }

  // Step 5: Check Backend Credentials Storage
  console.log("\n🔍 CHECKING BACKEND CREDENTIAL STORAGE...");
  try {
    // Try to check if backend has stored credentials for this user
    const statusUrl = `https://web-production-de0bc.up.railway.app/api/auth/broker/status`;
    const statusResponse = await fetch(statusUrl, {
      method: 'GET',
      headers: authHeaders
    });

    if (statusResponse.ok) {
      const statusData = await statusResponse.json();
      console.log("📋 BACKEND STATUS CHECK:");
      console.log(JSON.stringify(statusData, null, 2));
    } else {
      console.log("⚠️ Backend status check failed:", statusResponse.status);
    }
  } catch (error) {
    console.log("⚠️ Backend status check error:", error);
  }

  console.log("\n🎯 NEXT STEPS:");
  console.log("Based on the output above:");
  console.log("1. If holdings array is empty → Backend authentication issue");
  console.log("2. If 401 errors → User credentials not stored in backend");
  console.log("3. If connection errors → Backend deployment issue");
  console.log("4. If data looks good → Frontend display issue");
  
  console.log("\n📞 SOLUTIONS:");
  console.log("- Empty data → Re-authenticate to store credentials in backend");
  console.log("- 401 errors → Check backend database for user credentials");
  console.log("- Frontend issue → Check component data flow");
}

// Auto-run the diagnostic
console.log("🚀 Starting Real Portfolio Import Diagnostic...");
debugRealPortfolioImport(); 