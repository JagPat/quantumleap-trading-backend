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
      },
      {
        version: '005',
        name: 'add_multi_agent_ai_preferences',
        up: this.addMultiAgentAIPreferences.bind(this),
        down: this.rollbackMultiAgentAIPreferences.bind(this)
      },
      {
        version: '006',
        name: 'add_research_and_learning_tables',
        up: this.addResearchAndLearningTables.bind(this),
        down: this.rollbackResearchAndLearningTables.bind(this)
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

  /**
   * Migration 005: Add Multi-Agent AI Preferences
   * Adds provider selection per task type and trading mode management
   */
  async addMultiAgentAIPreferences(client) {
    console.log('Adding multi-agent AI preference columns...');

    // Add provider selection columns
    await client.query(`
      ALTER TABLE ai_preferences
      ADD COLUMN IF NOT EXISTS strategy_provider VARCHAR(50) DEFAULT 'openai',
      ADD COLUMN IF NOT EXISTS goal_provider VARCHAR(50) DEFAULT 'openai',
      ADD COLUMN IF NOT EXISTS portfolio_provider VARCHAR(50) DEFAULT 'openai',
      ADD COLUMN IF NOT EXISTS claude_api_key TEXT,
      ADD COLUMN IF NOT EXISTS mistral_api_key TEXT
    `);

    // Add trading mode and consent columns
    await client.query(`
      ALTER TABLE ai_preferences
      ADD COLUMN IF NOT EXISTS trading_mode VARCHAR(20) DEFAULT 'manual',
      ADD COLUMN IF NOT EXISTS auto_trading_consent BOOLEAN DEFAULT false,
      ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP,
      ADD COLUMN IF NOT EXISTS consent_ip VARCHAR(100),
      ADD COLUMN IF NOT EXISTS consent_disclaimers JSONB
    `);

    // Add constraint for trading mode
    await client.query(`
      ALTER TABLE ai_preferences
      ADD CONSTRAINT IF NOT EXISTS check_trading_mode 
      CHECK (trading_mode IN ('manual', 'auto'))
    `);

    // Add constraint for provider values
    await client.query(`
      ALTER TABLE ai_preferences
      ADD CONSTRAINT IF NOT EXISTS check_providers
      CHECK (
        strategy_provider IN ('openai', 'claude', 'mistral', 'auto') AND
        goal_provider IN ('openai', 'claude', 'mistral', 'auto') AND
        portfolio_provider IN ('openai', 'claude', 'mistral', 'auto')
      )
    `);

    // Create AI usage metrics table
    await client.query(`
      CREATE TABLE IF NOT EXISTS ai_usage_metrics (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        metric_type VARCHAR(50) NOT NULL,
        metric_value TEXT,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Create indexes for efficient querying
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_ai_metrics_user_type 
      ON ai_usage_metrics(user_id, metric_type)
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_ai_metrics_created 
      ON ai_usage_metrics(created_at)
    `);

    console.log('✅ AI usage metrics table created');
    console.log('✅ Multi-agent AI preference columns added successfully');
  }

  /**
   * Rollback Migration 005
   */
  async rollbackMultiAgentAIPreferences(client) {
    // Drop metrics table
    await client.query(`DROP TABLE IF EXISTS ai_usage_metrics`);

    await client.query(`
      ALTER TABLE ai_preferences
      DROP CONSTRAINT IF EXISTS check_trading_mode,
      DROP CONSTRAINT IF EXISTS check_providers
    `);

    await client.query(`
      ALTER TABLE ai_preferences
      DROP COLUMN IF EXISTS strategy_provider,
      DROP COLUMN IF EXISTS goal_provider,
      DROP COLUMN IF EXISTS portfolio_provider,
      DROP COLUMN IF EXISTS claude_api_key,
      DROP COLUMN IF EXISTS mistral_api_key,
      DROP COLUMN IF EXISTS trading_mode,
      DROP COLUMN IF EXISTS auto_trading_consent,
      DROP COLUMN IF EXISTS consent_timestamp,
      DROP COLUMN IF EXISTS consent_ip,
      DROP COLUMN IF EXISTS consent_disclaimers
    `);
  }

  /**
   * Migration 006: Add Research and Learning Tables
   */
  async addResearchAndLearningTables(client) {
    console.log('Creating research and learning tables...');

    // 1. Research Data Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS research_data (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        data_type VARCHAR(50) NOT NULL,
        source VARCHAR(100) NOT NULL,
        content TEXT,
        metadata JSONB,
        relevance_score FLOAT,
        fetched_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_research_symbol_type 
      ON research_data(symbol, data_type)
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_research_fetched 
      ON research_data(fetched_at DESC)
    `);

    // 2. Market Regimes Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS market_regimes (
        id SERIAL PRIMARY KEY,
        regime_type VARCHAR(50) NOT NULL,
        confidence FLOAT NOT NULL,
        indicators JSONB,
        llm_reasoning TEXT,
        detected_at TIMESTAMP DEFAULT NOW(),
        valid_until TIMESTAMP
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_regimes_valid 
      ON market_regimes(valid_until DESC)
    `);

    // 3. AI Decisions Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS ai_decisions (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        decision_type VARCHAR(50) NOT NULL,
        decision_data JSONB NOT NULL,
        market_regime VARCHAR(50),
        regime_confidence FLOAT,
        created_at TIMESTAMP DEFAULT NOW()
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_decisions_user 
      ON ai_decisions(user_id, created_at DESC)
    `);

    // 4. AI Decision Attributions Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS ai_decision_attributions (
        id SERIAL PRIMARY KEY,
        decision_id INT REFERENCES ai_decisions(id) ON DELETE CASCADE,
        data_source VARCHAR(50) NOT NULL,
        source_detail VARCHAR(200),
        attribution_weight FLOAT,
        content_summary TEXT
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_attributions_decision 
      ON ai_decision_attributions(decision_id)
    `);

    // 5. Trade Outcomes Table
    await client.query(`
      CREATE TABLE IF NOT EXISTS trade_outcomes (
        id SERIAL PRIMARY KEY,
        trade_id INT,
        decision_id INT REFERENCES ai_decisions(id) ON DELETE SET NULL,
        symbol VARCHAR(20) NOT NULL,
        entry_price DECIMAL(10,2),
        exit_price DECIMAL(10,2),
        quantity INT,
        pnl DECIMAL(12,2),
        pnl_percent FLOAT,
        holding_period_hours INT,
        exit_reason VARCHAR(100),
        user_override BOOLEAN DEFAULT FALSE,
        override_reason TEXT,
        executed_at TIMESTAMP,
        closed_at TIMESTAMP
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_outcomes_decision 
      ON trade_outcomes(decision_id)
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_outcomes_symbol_date 
      ON trade_outcomes(symbol, closed_at DESC)
    `);

    // 6. Learning Insights Table (cache for generated insights)
    await client.query(`
      CREATE TABLE IF NOT EXISTS learning_insights (
        id SERIAL PRIMARY KEY,
        insight_type VARCHAR(50) NOT NULL,
        insight_text TEXT NOT NULL,
        confidence FLOAT,
        sample_size INT,
        metadata JSONB,
        generated_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP
      )
    `);

    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_insights_expires 
      ON learning_insights(expires_at DESC)
    `);

    console.log('✅ Research and learning tables created successfully');
  }

  /**
   * Rollback Migration 006
   */
  async rollbackResearchAndLearningTables(client) {
    console.log('Dropping research and learning tables...');

    await client.query(`DROP TABLE IF EXISTS learning_insights CASCADE`);
    await client.query(`DROP TABLE IF EXISTS trade_outcomes CASCADE`);
    await client.query(`DROP TABLE IF EXISTS ai_decision_attributions CASCADE`);
    await client.query(`DROP TABLE IF EXISTS ai_decisions CASCADE`);
    await client.query(`DROP TABLE IF EXISTS market_regimes CASCADE`);
    await client.query(`DROP TABLE IF EXISTS research_data CASCADE`);

    console.log('✅ Research and learning tables dropped');
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
