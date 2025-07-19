// Debug script to check broker configuration state
// Run this in browser console on http://localhost:5173

console.log("🔍 Debugging Broker Configuration State");
console.log("=====================================");

// Check localStorage
const brokerConfigs = localStorage.getItem('brokerConfigs');
console.log("📄 Raw brokerConfigs from localStorage:", brokerConfigs);

if (brokerConfigs) {
  try {
    const configs = JSON.parse(brokerConfigs);
    console.log("📋 Parsed brokerConfigs:", configs);
    
    if (Array.isArray(configs) && configs.length > 0) {
      configs.forEach((config, index) => {
        console.log(`\n🔧 Config ${index}:`);
        console.log("  - ID:", config.id);
        console.log("  - Is Connected:", config.is_connected);
        console.log("  - Access Token:", config.access_token ? `${config.access_token.substring(0, 10)}...` : "MISSING");
        console.log("  - API Key:", config.api_key ? `${config.api_key.substring(0, 8)}...` : "MISSING");
        console.log("  - User Data:", config.user_data);
        console.log("  - Connection Status:", config.connection_status);
      });
      
      // Check for active config
      const activeConfig = configs.find(config => config.is_connected && config.access_token);
      if (activeConfig) {
        console.log("\n✅ Active config found:");
        console.log("  - User ID:", activeConfig.user_data?.user_id);
        console.log("  - API Key:", activeConfig.api_key?.substring(0, 8) + "...");
        console.log("  - Access Token:", activeConfig.access_token?.substring(0, 10) + "...");
        
        // Test auth headers
        const authHeaders = {
          'Authorization': `token ${activeConfig.api_key}:${activeConfig.access_token}`,
          'X-User-ID': activeConfig.user_data?.user_id || 'unknown'
        };
        console.log("\n🔐 Auth headers that would be sent:");
        console.log("  - Authorization:", authHeaders.Authorization?.substring(0, 30) + "...");
        console.log("  - X-User-ID:", authHeaders['X-User-ID']);
        
      } else {
        console.log("\n❌ No active config found!");
        console.log("Looking for config with both is_connected=true AND access_token");
      }
    } else {
      console.log("❌ No broker configs found or invalid format");
    }
  } catch (error) {
    console.error("❌ Error parsing brokerConfigs:", error);
  }
} else {
  console.log("❌ No brokerConfigs found in localStorage");
}

// Check if user needs to complete authentication
console.log("\n🔍 Authentication Status Check:");
console.log("If you see 'No active config found', you need to:");
console.log("1. Go to Broker Integration page");
console.log("2. Click 'Save & Authenticate' again"); 
console.log("3. Complete the OAuth flow");
console.log("4. Ensure the config gets saved with access_token"); 