#!/usr/bin/env node

/**
 * Auto-Migration Script
 * Automatically runs database migrations on server startup
 * Safe to run multiple times (uses IF NOT EXISTS)
 */

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

async function autoMigrate() {
  console.log('\n🔄 Auto-Migration: Checking database schema...');

  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    console.warn('⚠️  DATABASE_URL not set, skipping auto-migration');
    return;
  }

  const pool = new Pool({
    connectionString: databaseUrl,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
  });

  try {
    // Check if migration is needed
    const checkQuery = `
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'strategy_automations'
      ) as table_exists
    `;

    const checkResult = await pool.query(checkQuery);
    const tableExists = checkResult.rows[0].table_exists;

    if (tableExists) {
      console.log('✅ Strategy automation tables already exist - skipping migration');
      return;
    }

    console.log('📄 Strategy automation tables not found - running migration...');

    // Read and execute migration
    const migrationPath = path.join(__dirname, '../database/migrations/add_strategy_automation.sql');
    const migrationSQL = fs.readFileSync(migrationPath, 'utf8');

    await pool.query(migrationSQL);

    console.log('✅ Migration completed successfully!');
    console.log('   Created: strategy_automations, automated_orders, automation_performance');
    console.log('   Updated: broker_configs (added trading_mode columns)\n');

  } catch (error) {
    // If tables already exist, this is fine
    if (error.message && error.message.includes('already exists')) {
      console.log('✅ Tables already exist - migration skipped');
    } else {
      console.error('❌ Auto-migration error:', error.message);
      console.warn('⚠️  Server will continue, but strategy automation may not work');
      console.warn('   Please run migration manually or check DATABASE_URL');
    }
  } finally {
    await pool.end();
  }
}

// Run auto-migration
autoMigrate().catch(error => {
  console.error('Fatal migration error:', error);
  // Don't exit - allow server to start anyway
});

