// Test the CORS fix
const { RailwayAPI } = require('./quantum-leap-frontend/src/api/railwayAPI.js');

async function testCORSFix() {
  console.log('🧪 Testing CORS fix...');
  
  const api = new RailwayAPI();
  
  try {
    console.log('📡 Testing health endpoint...');
    const healthResult = await api.request('/health');
    console.log('✅ Health check result:', healthResult.status);
    
    console.log('📡 Testing AI preferences endpoint...');
    const prefsResult = await api.request('/api/ai/preferences');
    console.log('✅ AI preferences result:', prefsResult.status);
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

testCORSFix();