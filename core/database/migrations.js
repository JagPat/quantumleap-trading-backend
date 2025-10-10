const db = require('./connection');

class DatabaseMigrations {
  constructor() {
    this.migrations = [
      {
        version: '001',
        name: 'create_initial_tables',
        up: this.createInitialTables.bind(this),
        down: this.dropInitialTables.bind(this)
      },
      {
        version: '002', 
        name: 'create_oauth_tables',
        up: this.createOAuthTables.bind(this),
        down: this.dropOAuthTables.bind(this)
      },
      {
        version: '003',
        name: 'create_portfolio_tables', 
        up: this.createPortfolioTables.bind(this),
        down: this.dropPortfolioTables.bind(this)
      },
      {
        version: '004',
        name: 'enhance_oauth_status_tracking',
        up: this.enhanceOAuthStatusTracking.bind(this),
        down: this.rollbackOAuthStatusTracking.bind(this)
      }
    ];
  }

  async runMigrations() {
    try {
      // Create migrations table if it doesn't exist
      await this.createMigrationsTable();

      // Get current migration version
      const currentVersion = await this.getCurrentVersion();
      console.log(`📊 Current database version: ${currentVersion || 'none'}`);

      // Run pending migrations
      for (const migration of this.migrations) {
        if (!currentVersion || migration.version > currentVersion) {
          console.log(`🔄 Running migration ${migration.version}: ${migration.name}`);
          
          await db.transaction(async (client) => {
            await migration.up(client);
            await client.query(
              'INSERT INTO migrations (version, name, applied_at) VALUES ($1, $2, NOW())',
              [migration.version, migration.name]
            );
          });
          
          console.log(`✅ Migration ${migration.version} completed`);
        }
      }

      console.log('✅ All database migrations completed successfully');
      return true;
    } catch (error) {
      console.error('❌ Migration failed:', error);
      throw error;
    }
  }

  async createMigrationsTable() {
    await db.query(`
      CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        version VARCHAR(10) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async getCurrentVersion() {
    try {
      const result = await db.query(
        'SELECT version FROM migrations ORDER BY version DESC LIMIT 1'
      );
      return result.rows[0]?.version || null;
    } catch (error) {
      return null;
    }
  }

  // Migration 001: Initial tables
  async createInitialTables(client) {
    // Users table
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(20),
        name VARCHAR(255),
        is_active BOOLEAN DEFAULT true,
        email_verified BOOLEAN DEFAULT false,
        phone_verified BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        metadata JSONB DEFAULT '{}'
      )
    `);

    // OTP table for authentication
    await client.query(`
      CREATE TABLE IF NOT EXISTS otps (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        otp_code VARCHAR(10) NOT NULL,
        otp_type VARCHAR(20) NOT NULL, -- 'email', 'sms', 'login'
        expires_at TIMESTAMP NOT NULL,
        is_used BOOLEAN DEFAULT false,
        attempts INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create indexes
    await client.query('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_otps_user_id ON otps(user_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_otps_expires_at ON otps(expires_at)');
  }

  async dropInitialTables(client) {
    await client.query('DROP TABLE IF EXISTS otps CASCADE');
    await client.query('DROP TABLE IF EXISTS users CASCADE');
  }

  // Migration 002: OAuth tables
  async createOAuthTables(client) {
    // Broker configurations
    await client.query(`
      CREATE TABLE IF NOT EXISTS broker_configs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        broker_name VARCHAR(50) NOT NULL,
        api_key VARCHAR(255) NOT NULL,
        api_secret_encrypted TEXT NOT NULL,
        oauth_state VARCHAR(255),
        is_connected BOOLEAN DEFAULT false,
        connection_status JSONB DEFAULT '{}',
        last_sync TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, broker_name)
      )
    `);

    // OAuth tokens
    await client.query(`
      CREATE TABLE IF NOT EXISTS oauth_tokens (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        config_id UUID REFERENCES broker_configs(id) ON DELETE CASCADE,
        access_token_encrypted TEXT NOT NULL,
        refresh_token_encrypted TEXT,
        expires_at TIMESTAMP NOT NULL,
        token_type VARCHAR(20) DEFAULT 'Bearer',
        scope JSONB DEFAULT '[]',
        broker_user_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(config_id)
      )
    `);

    // OAuth audit log
    await client.query(`
      CREATE TABLE IF NOT EXISTS oauth_audit_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        config_id UUID REFERENCES broker_configs(id) ON DELETE SET NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(50) NOT NULL,
        status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'pending'
        details JSONB DEFAULT '{}',
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Create indexes
    await client.query('CREATE INDEX IF NOT EXISTS idx_broker_configs_user_id ON broker_configs(user_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_broker_configs_broker_name ON broker_configs(broker_name)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_oauth_tokens_config_id ON oauth_tokens(config_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at ON oauth_tokens(expires_at)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_oauth_audit_log_user_id ON oauth_audit_log(user_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_oauth_audit_log_created_at ON oauth_audit_log(created_at)');
  }

  async dropOAuthTables(client) {
    await client.query('DROP TABLE IF EXISTS oauth_audit_log CASCADE');
    await client.query('DROP TABLE IF EXISTS oauth_tokens CASCADE');
    await client.query('DROP TABLE IF EXISTS broker_configs CASCADE');
  }

  // Migration 003: Portfolio tables
  async createPortfolioTables(client) {
    // Portfolios
    await client.query(`
      CREATE TABLE IF NOT EXISTS portfolios (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        config_id UUID REFERENCES broker_configs(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        total_value DECIMAL(15,2) DEFAULT 0,
        total_investment DECIMAL(15,2) DEFAULT 0,
        total_pnl DECIMAL(15,2) DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB DEFAULT '{}'
      )
    `);

    // Holdings
    await client.query(`
      CREATE TABLE IF NOT EXISTS holdings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
        symbol VARCHAR(50) NOT NULL,
        exchange VARCHAR(20) NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        average_price DECIMAL(10,4) NOT NULL DEFAULT 0,
        current_price DECIMAL(10,4) DEFAULT 0,
        market_value DECIMAL(15,2) DEFAULT 0,
        pnl DECIMAL(15,2) DEFAULT 0,
        pnl_percentage DECIMAL(8,4) DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, symbol, exchange)
      )
    `);

    // Trades
    await client.query(`
      CREATE TABLE IF NOT EXISTS trades (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
        order_id VARCHAR(100),
        symbol VARCHAR(50) NOT NULL,
        exchange VARCHAR(20) NOT NULL,
        trade_type VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
        quantity INTEGER NOT NULL,
        price DECIMAL(10,4) NOT NULL,
        total_amount DECIMAL(15,2) NOT NULL,
        fees DECIMAL(10,2) DEFAULT 0,
        trade_date TIMESTAMP NOT NULL,
        status VARCHAR(20) DEFAULT 'COMPLETED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata JSONB DEFAULT '{}'
      )
    `);

    // Create indexes
    await client.query('CREATE INDEX IF NOT EXISTS idx_portfolios_user_id ON portfolios(user_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_portfolios_config_id ON portfolios(config_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_holdings_portfolio_id ON holdings(portfolio_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON holdings(symbol)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_trades_portfolio_id ON trades(portfolio_id)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)');
    await client.query('CREATE INDEX IF NOT EXISTS idx_trades_trade_date ON trades(trade_date)');
  }

  async dropPortfolioTables(client) {
    await client.query('DROP TABLE IF EXISTS trades CASCADE');
    await client.query('DROP TABLE IF EXISTS holdings CASCADE');
    await client.query('DROP TABLE IF EXISTS portfolios CASCADE');
  }

  // Migration 004: Enhance OAuth status/session tracking
  async enhanceOAuthStatusTracking(client) {
    // Add non-user_id columns first
    await client.query(`
      ALTER TABLE oauth_tokens
      ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'connected',
      ADD COLUMN IF NOT EXISTS source VARCHAR(50),
      ADD COLUMN IF NOT EXISTS last_refreshed TIMESTAMP
    `);

    await client.query(`
      ALTER TABLE oauth_tokens
      ADD COLUMN IF NOT EXISTS needs_reauth BOOLEAN DEFAULT false
    `);

    // Handle user_id column with type checking and conversion
    const userIdColumnCheck = await client.query(`
      SELECT column_name, data_type, udt_name
      FROM information_schema.columns
      WHERE table_name = 'oauth_tokens' 
        AND column_name = 'user_id'
    `);
    
    if (userIdColumnCheck.rows.length === 0) {
      // Column doesn't exist, add it as UUID
      await client.query(`
        ALTER TABLE oauth_tokens
        ADD COLUMN user_id UUID
      `);
    } else if (userIdColumnCheck.rows[0].udt_name !== 'uuid') {
      // Column exists but wrong type (VARCHAR), need to convert
      console.log(`⚠️  user_id column exists as ${userIdColumnCheck.rows[0].data_type}, converting to UUID...`);
      
      // Drop existing foreign key constraint if it exists
      await client.query(`
        ALTER TABLE oauth_tokens
        DROP CONSTRAINT IF EXISTS oauth_tokens_user_id_fk
      `);
      
      // Drop the index if it exists
      await client.query(`
        DROP INDEX IF EXISTS idx_oauth_tokens_user_unique
      `);
      
      // Convert the column type using USING clause for safe conversion
      // This will set NULL for any values that can't be converted to UUID
      await client.query(`
        ALTER TABLE oauth_tokens
        ALTER COLUMN user_id TYPE UUID USING (
          CASE 
            WHEN user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            THEN user_id::UUID
            ELSE NULL
          END
        )
      `);
      
      console.log('✅ user_id column converted to UUID');
    }

    // Add foreign key constraint only if it doesn't exist
    const constraintExists = await client.query(`
      SELECT constraint_name 
      FROM information_schema.table_constraints 
      WHERE table_name = 'oauth_tokens' 
        AND constraint_name = 'oauth_tokens_user_id_fk'
    `);
    
    if (constraintExists.rows.length === 0) {
      await client.query(`
        ALTER TABLE oauth_tokens
        ADD CONSTRAINT oauth_tokens_user_id_fk
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      `);
      console.log('✅ Foreign key constraint oauth_tokens_user_id_fk added');
    }

    await client.query(`
      CREATE UNIQUE INDEX IF NOT EXISTS idx_oauth_tokens_user_unique
      ON oauth_tokens(user_id)
      WHERE user_id IS NOT NULL
    `);

    await client.query(`
      ALTER TABLE broker_configs
      ADD COLUMN IF NOT EXISTS session_status VARCHAR(20) DEFAULT 'disconnected',
      ADD COLUMN IF NOT EXISTS needs_reauth BOOLEAN DEFAULT false,
      ADD COLUMN IF NOT EXISTS last_token_refresh TIMESTAMP,
      ADD COLUMN IF NOT EXISTS last_status_check TIMESTAMP
    `);
  }

  async rollbackOAuthStatusTracking(client) {
    await client.query('DROP INDEX IF EXISTS idx_oauth_tokens_user_unique');

    await client.query(`
      ALTER TABLE oauth_tokens
      DROP CONSTRAINT IF EXISTS oauth_tokens_user_id_fk
    `);

    await client.query(`
      ALTER TABLE oauth_tokens
      DROP COLUMN IF EXISTS needs_reauth,
      DROP COLUMN IF EXISTS last_refreshed,
      DROP COLUMN IF EXISTS source,
      DROP COLUMN IF EXISTS status,
      DROP COLUMN IF EXISTS user_id
    `);

    await client.query(`
      ALTER TABLE broker_configs
      DROP COLUMN IF EXISTS session_status,
      DROP COLUMN IF EXISTS needs_reauth,
      DROP COLUMN IF EXISTS last_token_refresh,
      DROP COLUMN IF EXISTS last_status_check
    `);
  }

  // Rollback to specific version
  async rollbackTo(targetVersion) {
    try {
      const currentVersion = await this.getCurrentVersion();
      
      if (!currentVersion || targetVersion >= currentVersion) {
        console.log('No rollback needed');
        return;
      }

      // Find migrations to rollback (in reverse order)
      const migrationsToRollback = this.migrations
        .filter(m => m.version > targetVersion)
        .reverse();

      for (const migration of migrationsToRollback) {
        console.log(`🔄 Rolling back migration ${migration.version}: ${migration.name}`);
        
        await db.transaction(async (client) => {
          await migration.down(client);
          await client.query('DELETE FROM migrations WHERE version = $1', [migration.version]);
        });
        
        console.log(`✅ Rollback ${migration.version} completed`);
      }

      console.log(`✅ Rollback to version ${targetVersion} completed`);
    } catch (error) {
      console.error('❌ Rollback failed:', error);
      throw error;
    }
  }
}

module.exports = new DatabaseMigrations();
