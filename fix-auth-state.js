// Fix Authentication State - Run this in browser console on http://localhost:5173
// This will complete the authentication using the request token we saw in the logs

async function fixAuthenticationState() {
  console.log("🔧 Fixing Authentication State...");
  
  // The request token from your logs
  const requestToken = "E6smeqbDSB7rE4ybpNJIzLsZRLe20fJO";
  
  // Get the broker config to find API credentials
  const brokerConfigs = JSON.parse(localStorage.getItem('brokerConfigs') || '[]');
  console.log("📋 Current broker configs:", brokerConfigs);
  
  let config = brokerConfigs.find(c => c.broker_name === 'zerodha');
  
  if (!config || !config.api_key || !config.api_secret) {
    console.error("❌ No valid broker config found! Please:");
    console.log("1. Go to Broker Integration page");
    console.log("2. Enter your API Key and Secret");
    console.log("3. Click 'Save & Authenticate'");
    return;
  }
  
  console.log("✅ Found broker config with credentials");
  console.log("🔐 API Key:", config.api_key.substring(0, 8) + "...");
  
  try {
    console.log("🚀 Calling backend to exchange token...");
    
    // Call backend to exchange the request token for access token
    const response = await fetch('https://web-production-de0bc.up.railway.app/api/auth/broker/generate-session', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        request_token: requestToken,
        api_key: config.api_key,
        api_secret: config.api_secret
      })
    });
    
    const result = await response.json();
    console.log("📡 Backend response:", result);
    
    if (result.status === 'success') {
      console.log("✅ Authentication successful!");
      
      // Update the broker config with the access token
      const updatedConfig = {
        ...config,
        is_connected: true,
        access_token: result.access_token,
        user_data: result.user_data,
        connection_status: 'connected',
        updated_at: new Date().toISOString()
      };
      
      // Save updated config
      const updatedConfigs = brokerConfigs.filter(c => c.broker_name !== 'zerodha');
      updatedConfigs.push(updatedConfig);
      localStorage.setItem('brokerConfigs', JSON.stringify(updatedConfigs));
      
      console.log("💾 Updated broker config saved!");
      console.log("🎉 You are now connected as:", result.user_data.user_name || result.user_data.user_id);
      
      // Reload the page to reflect the connection
      alert("Authentication completed! Reloading page...");
      window.location.reload();
      
    } else {
      console.error("❌ Authentication failed:", result.message);
      alert("Authentication failed: " + result.message);
    }
    
  } catch (error) {
    console.error("💥 Error during authentication:", error);
    alert("Authentication error: " + error.message);
  }
}

// Run the fix
fixAuthenticationState(); 