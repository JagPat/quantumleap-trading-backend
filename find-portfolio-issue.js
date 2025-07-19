// Find Portfolio Issue - Focused Diagnostic
// Run this to find why your 36 holdings (₹5.16 crores) aren't showing

async function findPortfolioIssue() {
  console.log("🎯 FOCUSED PORTFOLIO ISSUE DIAGNOSTIC");
  console.log("====================================");
  console.log("TARGET: Find why 36 holdings (₹5.16 crores) not importing\n");

  // Get auth config
  const configs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  const active = configs.find(c => c.is_connected && c.access_token);
  
  if (!active) {
    console.error("❌ No active config - authentication issue");
    return;
  }

  const userId = active.user_data?.user_id;
  console.log("🔑 Auth Status:");
  console.log("  User ID:", userId);
  console.log("  API Key:", active.api_key?.substring(0, 8) + "...");
  console.log("  Access Token:", active.access_token?.substring(0, 20) + "...");

  // Test the exact call your frontend makes
  const headers = {
    'Authorization': `token ${active.api_key}:${active.access_token}`,
    'X-User-ID': userId,
    'Content-Type': 'application/json'
  };

  console.log("\n🧪 TESTING EXACT FRONTEND CALL...");
  
  try {
    // This is the EXACT call your frontend makes
    const response = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/holdings?user_id=${userId}`, {
      method: 'GET',
      headers: headers
    });

    console.log("📡 Response Status:", response.status);

    if (!response.ok) {
      const error = await response.text();
      console.error("❌ FAILED REQUEST:");
      console.log("Status:", response.status);
      console.log("Error:", error);
      
      if (response.status === 401) {
        console.log("\n🔍 401 ANALYSIS - Backend doesn't recognize authentication:");
        console.log("LIKELY CAUSE: Backend database doesn't have user credentials stored");
        console.log("SOLUTION: Re-authenticate to store credentials in backend database");
        
        console.log("\n🔧 TO FIX:");
        console.log("1. Go to Broker Integration page");
        console.log("2. Click 'Save & Authenticate' again"); 
        console.log("3. Complete OAuth flow");
        console.log("4. This will store credentials in backend database");
      }
      return;
    }

    const data = await response.json();
    console.log("✅ SUCCESS - Got Response:");
    console.log("Status:", data.status);
    console.log("Data Type:", typeof data.data);
    console.log("Data Length:", Array.isArray(data.data) ? data.data.length : 'Not Array');

    if (data.status === 'success') {
      if (Array.isArray(data.data)) {
        console.log("\n📊 HOLDINGS DATA ANALYSIS:");
        console.log("Holdings Count:", data.data.length);
        console.log("Expected: 36");
        
        if (data.data.length === 0) {
          console.error("❌ EMPTY HOLDINGS ARRAY");
          console.log("🔍 Backend connected to Zerodha but got empty response");
          console.log("POSSIBLE CAUSES:");
          console.log("1. Backend using wrong API credentials");
          console.log("2. Backend database lookup failing");
          console.log("3. Zerodha API returning empty (unlikely)");
          console.log("4. Backend not calling Zerodha API correctly");
          
          console.log("\n🔧 TO DEBUG:");
          console.log("Check backend logs for Zerodha API calls");
          console.log("Verify backend stored correct API key/secret");
        } else if (data.data.length < 36) {
          console.log("⚠️ PARTIAL DATA - Got", data.data.length, "of 36 holdings");
          console.log("First holding:", data.data[0]);
        } else {
          console.log("🎉 CORRECT DATA - Got all", data.data.length, "holdings!");
          console.log("✅ The data is being returned correctly");
          console.log("🔍 Issue might be in frontend display logic");
          
          // Check data format
          const sample = data.data[0];
          console.log("\n📋 Sample holding data:");
          console.log(JSON.stringify(sample, null, 2));
        }
      } else {
        console.error("❌ DATA NOT ARRAY:", typeof data.data);
        console.log("Received data:", data.data);
      }
    } else {
      console.error("❌ Backend returned error status:", data.status);
      console.log("Full response:", data);
    }

  } catch (error) {
    console.error("💥 REQUEST FAILED:", error);
    console.log("🔍 This indicates a network or backend issue");
  }

  // Also test the combined endpoint
  console.log("\n🚀 TESTING COMBINED PORTFOLIO ENDPOINT...");
  try {
    const portfolioResponse = await fetch(`https://web-production-de0bc.up.railway.app/api/portfolio/data`, {
      method: 'GET',
      headers: headers
    });

    if (portfolioResponse.ok) {
      const portfolioData = await portfolioResponse.json();
      console.log("📊 Combined Portfolio Data:");
      console.log("Status:", portfolioData.status);
      
      if (portfolioData.status === 'success') {
        console.log("Holdings Count:", portfolioData.data?.holdings?.length || 0);
        console.log("Total Value:", portfolioData.data?.summary?.total_value || 0);
        console.log("Expected Value: ~51,600,000");
      }
    } else {
      console.log("❌ Combined endpoint failed:", portfolioResponse.status);
    }
  } catch (error) {
    console.log("❌ Combined endpoint error:", error);
  }

  console.log("\n🎯 SUMMARY & NEXT STEPS:");
  console.log("Based on the results above:");
  console.log("• If 401 error → Re-authenticate to store backend credentials");
  console.log("• If empty array → Backend database/API issue");
  console.log("• If correct data → Frontend display issue");
  console.log("• If network error → Backend deployment issue");
}

// Make available and run
window.findPortfolioIssue = findPortfolioIssue;
findPortfolioIssue(); 