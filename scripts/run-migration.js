#!/usr/bin/env node

/**
 * Database Migration Runner
 * Runs the strategy automation migration on Railway PostgreSQL
 */

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

async function runMigration() {
  console.log('🗄️  Strategy Automation Database Migration');
  console.log('==========================================\n');

  // Get DATABASE_URL from environment
  const databaseUrl = process.env.DATABASE_URL;

  if (!databaseUrl) {
    console.error('❌ ERROR: DATABASE_URL environment variable is not set');
    console.error('\nThis script must be run on Railway where DATABASE_URL is available.');
    console.error('Or set it manually: export DATABASE_URL="postgresql://..."');
    process.exit(1);
  }

  console.log('✅ DATABASE_URL found');
  console.log('📡 Connecting to database...\n');

  // Create database connection pool
  const pool = new Pool({
    connectionString: databaseUrl,
    ssl: {
      rejectUnauthorized: false
    }
  });

  try {
    // Test connection
    const testResult = await pool.query('SELECT NOW()');
    console.log('✅ Connected to database at:', testResult.rows[0].now);
    console.log('');

    // Read migration file
    const migrationPath = path.join(__dirname, '../database/migrations/add_strategy_automation.sql');
    const migrationSQL = fs.readFileSync(migrationPath, 'utf8');

    console.log('📄 Migration file loaded');
    console.log('🔄 Executing migration...\n');

    // Execute migration
    await pool.query(migrationSQL);

    console.log('✅ Migration completed successfully!\n');
    console.log('📋 Created tables:');
    console.log('  - strategy_automations');
    console.log('  - automated_orders');
    console.log('  - automation_performance\n');
    console.log('🔧 Modified tables:');
    console.log('  - broker_configs (added trading_mode, max_daily_loss, max_trades_per_day)\n');
    console.log('🎉 Strategy automation system is now ready to use!');

    // Verify tables exist
    const verifyQuery = `
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
        AND table_name IN ('strategy_automations', 'automated_orders', 'automation_performance')
      ORDER BY table_name
    `;

    const verifyResult = await pool.query(verifyQuery);
    
    if (verifyResult.rows.length === 3) {
      console.log('\n✅ Verification: All tables created successfully');
      verifyResult.rows.forEach(row => {
        console.log(`   ✓ ${row.table_name}`);
      });
    } else {
      console.log('\n⚠️  Warning: Not all tables were created');
      console.log('Expected: 3 tables, Found:', verifyResult.rows.length);
    }

  } catch (error) {
    console.error('\n❌ Migration failed!');
    console.error('Error:', error.message);
    console.error('\nDetails:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

// Run migration
runMigration().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});

