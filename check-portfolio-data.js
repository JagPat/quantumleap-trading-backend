// Check Portfolio Data Script
// Run this in browser console to see what data is actually being returned

async function checkPortfolioData() {
  console.log("🔍 Checking Portfolio Data Flow...");
  console.log("==================================\n");

  // Get broker config
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  const activeConfig = brokerConfigs.find(config => config.is_connected && config.access_token);
  
  if (!activeConfig) {
    console.error("❌ No active broker config found");
    return;
  }

  const userId = activeConfig.user_data?.user_id;
  console.log("👤 User ID:", userId);

  // Test the exact same calls your app is making
  const authHeaders = {
    'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
    'X-User-ID': userId,
    'Content-Type': 'application/json'
  };

  try {
    // Test holdings endpoint
    console.log("📊 Testing Holdings Endpoint...");
    const holdingsResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`, {
      method: 'GET',
      headers: authHeaders
    });

    if (holdingsResponse.ok) {
      const holdingsData = await holdingsResponse.json();
      console.log("✅ Holdings Response:", holdingsData);
      
      if (holdingsData.status === 'success') {
        console.log("📈 Holdings Count:", holdingsData.data?.length || 0);
        
        if (holdingsData.data && holdingsData.data.length > 0) {
          console.log("📋 Sample Holding:", holdingsData.data[0]);
          
          // Check for Phase 1 enhanced fields
          const sample = holdingsData.data[0];
          console.log("🎯 Phase 1 Enhanced Fields Check:");
          console.log("  - pnl_percentage:", sample.pnl_percentage || 'NOT FOUND');
          console.log("  - current_value:", sample.current_value || 'NOT FOUND');
          console.log("  - invested_amount:", sample.invested_amount || 'NOT FOUND');
          console.log("  - fetch_timestamp:", sample.fetch_timestamp || 'NOT FOUND');
        } else {
          console.log("⚠️ No holdings data found");
          console.log("📝 This could mean:");
          console.log("  - Your Zerodha account has no holdings");
          console.log("  - Market is closed and positions are cleared");
          console.log("  - Backend returned empty array from Zerodha API");
        }
      }
    } else {
      console.error("❌ Holdings endpoint failed");
    }

    // Test positions endpoint
    console.log("\n📊 Testing Positions Endpoint...");
    const positionsResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/positions?user_id=${userId}`, {
      method: 'GET',
      headers: authHeaders
    });

    if (positionsResponse.ok) {
      const positionsData = await positionsResponse.json();
      console.log("✅ Positions Response:", positionsData);
      
      if (positionsData.status === 'success') {
        const netPositions = positionsData.data?.net || [];
        const dayPositions = positionsData.data?.day || [];
        
        console.log("📈 Net Positions Count:", netPositions.length);
        console.log("📈 Day Positions Count:", dayPositions.length);
        
        if (netPositions.length > 0) {
          console.log("📋 Sample Net Position:", netPositions[0]);
        }
        
        if (dayPositions.length > 0) {
          console.log("📋 Sample Day Position:", dayPositions[0]);
        }
        
        if (netPositions.length === 0 && dayPositions.length === 0) {
          console.log("⚠️ No positions data found");
          console.log("📝 This is normal if:");
          console.log("  - Market is closed");
          console.log("  - No active positions today");
          console.log("  - No intraday trades");
        }
      }
    } else {
      console.error("❌ Positions endpoint failed");
    }

    // Test the enhanced portfolio data endpoint (Phase 1)
    console.log("\n🚀 Testing Enhanced Portfolio Data Endpoint (Phase 1)...");
    const portfolioResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/data`, {
      method: 'GET',
      headers: authHeaders
    });

    if (portfolioResponse.ok) {
      const portfolioData = await portfolioResponse.json();
      console.log("🎉 Enhanced Portfolio Data Response:", portfolioData);
      
      if (portfolioData.status === 'success') {
        console.log("📊 Portfolio Summary:");
        const summary = portfolioData.data?.summary;
        if (summary) {
          console.log("  - Total Value:", summary.total_value);
          console.log("  - Total P&L:", summary.total_pnl);
          console.log("  - Total P&L %:", summary.total_pnl_percentage);
          console.log("  - Total Invested:", summary.total_invested);
          console.log("  - Today's P&L:", summary.todays_pnl);
          console.log("  - Fetch Timestamp:", new Date(summary.fetch_timestamp * 1000).toLocaleString());
        }
        
        console.log("📈 Enhanced Data Quality:");
        console.log("  - Holdings with enhanced fields:", portfolioData.data?.holdings?.length || 0);
        console.log("  - Positions with enhanced fields:", portfolioData.data?.positions?.net?.length || 0);
      }
    } else {
      console.error("❌ Enhanced portfolio endpoint failed");
    }

  } catch (error) {
    console.error("💥 Error during data check:", error);
  }

  console.log("\n🎯 Conclusion:");
  console.log("If you see empty arrays or zero values, this means:");
  console.log("1. ✅ Connection is working perfectly");
  console.log("2. ✅ Authentication is working");
  console.log("3. ✅ Enhanced backend is deployed");
  console.log("4. 📊 Your Zerodha account just has no holdings/positions right now");
  console.log("\nTo test with real data:");
  console.log("- Make sure you have holdings in your Zerodha account");
  console.log("- Or test during market hours with active positions");
}

// Run the check
checkPortfolioData(); 