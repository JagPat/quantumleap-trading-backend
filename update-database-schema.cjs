#!/usr/bin/env node

/**
 * Database Schema Update Script
 * Updates the broker_configs table to match the expected schema
 */

const { Pool } = require('pg');

async function updateDatabaseSchema() {
  console.log('🔄 Updating Database Schema');
  console.log('===========================');
  console.log(`⏱️  Started at: ${new Date().toISOString()}`);
  console.log('');

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
  });

  try {
    const client = await pool.connect();
    
    console.log('✅ Connected to database');
    
    // Check if api_key_encrypted column exists
    const checkColumn = await client.query(`
      SELECT column_name 
      FROM information_schema.columns 
      WHERE table_name = 'broker_configs' 
      AND column_name = 'api_key_encrypted'
    `);

    if (checkColumn.rows.length === 0) {
      console.log('🔄 Adding api_key_encrypted column...');
      
      // Add the missing column
      await client.query(`
        ALTER TABLE broker_configs 
        ADD COLUMN IF NOT EXISTS api_key_encrypted TEXT
      `);
      
      // Copy data from api_key to api_key_encrypted if api_key exists
      const checkApiKey = await client.query(`
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'broker_configs' 
        AND column_name = 'api_key'
      `);
      
      if (checkApiKey.rows.length > 0) {
        console.log('🔄 Migrating api_key data to api_key_encrypted...');
        await client.query(`
          UPDATE broker_configs 
          SET api_key_encrypted = api_key 
          WHERE api_key_encrypted IS NULL
        `);
        
        console.log('🔄 Dropping old api_key column...');
        await client.query(`
          ALTER TABLE broker_configs 
          DROP COLUMN IF EXISTS api_key
        `);
      }
      
      console.log('✅ api_key_encrypted column added successfully');
    } else {
      console.log('✅ api_key_encrypted column already exists');
    }

    // Add missing columns if they don't exist
    const missingColumns = [
      { name: 'broker_user_id', type: 'VARCHAR(255)' },
      { name: 'broker_user_name', type: 'VARCHAR(255)' },
      { name: 'broker_user_type', type: 'VARCHAR(50)' }
    ];

    for (const column of missingColumns) {
      const checkCol = await client.query(`
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'broker_configs' 
        AND column_name = $1
      `, [column.name]);

      if (checkCol.rows.length === 0) {
        console.log(`🔄 Adding ${column.name} column...`);
        await client.query(`
          ALTER TABLE broker_configs 
          ADD COLUMN IF NOT EXISTS ${column.name} ${column.type}
        `);
        console.log(`✅ ${column.name} column added successfully`);
      } else {
        console.log(`✅ ${column.name} column already exists`);
      }
    }

    // Verify the final schema
    console.log('');
    console.log('🔍 Verifying final schema...');
    const finalSchema = await client.query(`
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns 
      WHERE table_name = 'broker_configs'
      ORDER BY ordinal_position
    `);

    console.log('📋 broker_configs table schema:');
    finalSchema.rows.forEach(row => {
      console.log(`   - ${row.column_name}: ${row.data_type} (${row.is_nullable === 'YES' ? 'nullable' : 'not null'})`);
    });

    client.release();
    console.log('');
    console.log('✅ Database schema update completed successfully');
    
    return { success: true };

  } catch (error) {
    console.error('❌ Database schema update failed:', error);
    return { success: false, error: error.message };
  } finally {
    await pool.end();
  }
}

// Run the update
if (require.main === module) {
  updateDatabaseSchema()
    .then(result => {
      console.log(`🏁 Schema update completed at: ${new Date().toISOString()}`);
      console.log(`📊 Status: ${result.success ? 'SUCCESS' : 'FAILED'}`);
      process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
      console.error('💥 Schema update failed:', error);
      process.exit(1);
    });
}

module.exports = { updateDatabaseSchema };