#!/usr/bin/env node

/**
 * Simple script to trigger database schema migration via HTTP request
 */

const https = require('https');

async function triggerSchemaMigration() {
  console.log('🔄 Triggering Database Schema Migration');
  console.log('======================================');
  console.log(`⏱️  Started at: ${new Date().toISOString()}`);
  console.log('');

  // First, let's check if there's a migration endpoint
  try {
    console.log('🔍 Checking for migration endpoint...');
    
    const response = await new Promise((resolve, reject) => {
      const req = https.get('https://web-production-de0bc.up.railway.app/api/migrate', (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            data: data
          });
        });
      });
      
      req.on('error', reject);
      req.setTimeout(30000, () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });
    });

    console.log(`📊 Migration endpoint status: ${response.status}`);
    console.log(`📊 Response: ${response.data}`);

  } catch (error) {
    console.log(`❌ Migration endpoint not available: ${error.message}`);
  }

  // Alternative: Try to trigger migration via a POST request
  try {
    console.log('');
    console.log('🔄 Attempting alternative migration trigger...');
    
    const postData = JSON.stringify({ action: 'migrate_schema' });
    
    const response = await new Promise((resolve, reject) => {
      const options = {
        hostname: 'web-production-de0bc.up.railway.app',
        port: 443,
        path: '/api/admin/migrate',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const req = https.request(options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            data: data
          });
        });
      });

      req.on('error', reject);
      req.setTimeout(30000, () => {
        req.destroy();
        reject(new Error('Request timeout'));
      });

      req.write(postData);
      req.end();
    });

    console.log(`📊 Alternative migration status: ${response.status}`);
    console.log(`📊 Response: ${response.data}`);

  } catch (error) {
    console.log(`❌ Alternative migration failed: ${error.message}`);
  }

  console.log('');
  console.log('💡 Manual Migration Required');
  console.log('============================');
  console.log('Since automatic migration endpoints are not available,');
  console.log('the database schema needs to be updated manually.');
  console.log('');
  console.log('The issue is that the broker_configs table has:');
  console.log('  - api_key (VARCHAR) - but code expects api_key_encrypted (TEXT)');
  console.log('');
  console.log('Solution: The table schema needs to be updated to match the model.');
  console.log('This typically requires Railway database console access or');
  console.log('a migration script run during deployment.');
}

// Run the migration trigger
if (require.main === module) {
  triggerSchemaMigration()
    .then(() => {
      console.log(`🏁 Migration trigger completed at: ${new Date().toISOString()}`);
    })
    .catch(error => {
      console.error('💥 Migration trigger failed:', error);
    });
}

module.exports = { triggerSchemaMigration };