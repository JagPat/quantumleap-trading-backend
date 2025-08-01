"""
Database service - handles all database operations
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize cipher suite for encryption
cipher_suite = Fernet(settings.encryption_key)

def get_db_connection():
    """Get a database connection"""
    return sqlite3.connect(settings.database_path)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    # Create users table for storing broker credentials
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            api_key TEXT NOT NULL,
            api_secret TEXT NOT NULL,
            access_token TEXT,
            user_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_successful_connection TIMESTAMP,
            token_expiry TIMESTAMP,
            last_error TEXT
        )
    ''')
    # Create portfolio_snapshots table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            holdings TEXT NOT NULL,
            positions TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    # Create enhanced ai_user_preferences table for storing AI API keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            openai_api_key TEXT,
            claude_api_key TEXT,
            gemini_api_key TEXT,
            grok_api_key TEXT,
            preferred_provider TEXT DEFAULT 'auto',
            provider_priorities TEXT,
            cost_limits TEXT,
            risk_tolerance TEXT DEFAULT 'medium',
            trading_style TEXT DEFAULT 'balanced',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_chat_sessions table for conversation management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            session_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_chat_messages table for message history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            thread_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            provider_used TEXT,
            tokens_used INTEGER,
            cost_cents INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES ai_chat_sessions (id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_strategies table for generated trading strategies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            parameters TEXT NOT NULL,
            rules TEXT NOT NULL,
            risk_management TEXT,
            backtesting_results TEXT,
            performance_metrics TEXT,
            is_active BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_trading_signals table for signal management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            reasoning TEXT,
            target_price REAL,
            stop_loss REAL,
            take_profit REAL,
            position_size REAL,
            market_data TEXT,
            provider_used TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_usage_tracking table for cost monitoring
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_usage_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            tokens_used INTEGER,
            cost_cents INTEGER,
            response_time_ms INTEGER,
            success BOOLEAN,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create ai_analysis_results table for analysis storage
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            symbols TEXT,
            input_data TEXT,
            analysis_result TEXT NOT NULL,
            provider_used TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create enhanced_recommendations table for specific stock recommendations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enhanced_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            analysis_id TEXT NOT NULL,
            stock_symbol TEXT NOT NULL,
            current_allocation DECIMAL(5,2),
            target_allocation DECIMAL(5,2),
            action_type TEXT NOT NULL CHECK (action_type IN ('BUY', 'SELL', 'HOLD', 'REDUCE', 'INCREASE')),
            quantity_change INTEGER,
            value_change DECIMAL(15,2),
            current_price DECIMAL(10,2),
            reasoning TEXT NOT NULL,
            confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
            priority_level TEXT NOT NULL CHECK (priority_level IN ('HIGH', 'MEDIUM', 'LOW')),
            timeframe TEXT NOT NULL CHECK (timeframe IN ('IMMEDIATE', 'SHORT_TERM', 'LONG_TERM')),
            expected_impact TEXT,
            risk_warning TEXT,
            optimal_timing TEXT,
            auto_trading_eligible BOOLEAN DEFAULT FALSE,
            market_context TEXT,
            sector TEXT,
            implementation_status TEXT DEFAULT 'PENDING' CHECK (implementation_status IN ('PENDING', 'IMPLEMENTED', 'CANCELLED', 'EXPIRED')),
            implementation_date TIMESTAMP,
            implementation_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create recommendation_performance table for tracking outcomes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendation_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            stock_symbol TEXT NOT NULL,
            implementation_date TIMESTAMP NOT NULL,
            implementation_method TEXT NOT NULL CHECK (implementation_method IN ('MANUAL', 'AUTO_TRADING', 'PARTIAL')),
            implementation_price DECIMAL(10,2),
            predicted_price DECIMAL(10,2),
            actual_outcome_1d DECIMAL(10,2),
            actual_outcome_7d DECIMAL(10,2),
            actual_outcome_30d DECIMAL(10,2),
            predicted_outcome DECIMAL(10,2),
            accuracy_score_1d DECIMAL(3,2),
            accuracy_score_7d DECIMAL(3,2),
            accuracy_score_30d DECIMAL(3,2),
            user_feedback_rating INTEGER CHECK (user_feedback_rating >= 1 AND user_feedback_rating <= 5),
            user_feedback_text TEXT,
            market_conditions_during TEXT,
            portfolio_impact DECIMAL(10,2),
            recommendation_success BOOLEAN,
            lessons_learned TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recommendation_id) REFERENCES enhanced_recommendations (id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_enhanced_recommendations_user_id 
        ON enhanced_recommendations (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_enhanced_recommendations_symbol 
        ON enhanced_recommendations (stock_symbol)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_enhanced_recommendations_status 
        ON enhanced_recommendations (implementation_status)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_enhanced_recommendations_priority 
        ON enhanced_recommendations (priority_level, timeframe)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recommendation_performance_user_id 
        ON recommendation_performance (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recommendation_performance_symbol 
        ON recommendation_performance (stock_symbol)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recommendation_performance_date 
        ON recommendation_performance (implementation_date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recommendation_performance_success 
        ON recommendation_performance (recommendation_success)
    ''')
    
    # Create user_investment_profiles table for personalized recommendations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_investment_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            risk_tolerance TEXT NOT NULL CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive')),
            investment_timeline TEXT NOT NULL CHECK (investment_timeline IN ('short_term', 'medium_term', 'long_term')),
            investment_goals TEXT,
            preferred_sectors TEXT,
            avoided_sectors TEXT,
            max_position_size DECIMAL(5,2) DEFAULT 15.0 CHECK (max_position_size > 0 AND max_position_size <= 100),
            min_position_size DECIMAL(5,2) DEFAULT 2.0 CHECK (min_position_size > 0 AND min_position_size <= 100),
            trading_frequency TEXT DEFAULT 'monthly' CHECK (trading_frequency IN ('daily', 'weekly', 'monthly', 'quarterly')),
            auto_trading_enabled BOOLEAN DEFAULT FALSE,
            auto_trading_max_amount DECIMAL(15,2) DEFAULT 100000,
            stop_loss_preference DECIMAL(5,2) DEFAULT 10.0 CHECK (stop_loss_preference >= 0 AND stop_loss_preference <= 50),
            take_profit_preference DECIMAL(5,2) DEFAULT 25.0 CHECK (take_profit_preference >= 0 AND take_profit_preference <= 200),
            rebalancing_frequency TEXT DEFAULT 'monthly' CHECK (rebalancing_frequency IN ('weekly', 'monthly', 'quarterly', 'annually')),
            dividend_preference TEXT DEFAULT 'reinvest' CHECK (dividend_preference IN ('reinvest', 'cash', 'mixed')),
            tax_optimization_enabled BOOLEAN DEFAULT TRUE,
            esg_preference BOOLEAN DEFAULT FALSE,
            international_exposure_preference DECIMAL(5,2) DEFAULT 10.0 CHECK (international_exposure_preference >= 0 AND international_exposure_preference <= 50),
            cash_allocation_preference DECIMAL(5,2) DEFAULT 5.0 CHECK (cash_allocation_preference >= 0 AND cash_allocation_preference <= 30),
            volatility_tolerance TEXT DEFAULT 'medium' CHECK (volatility_tolerance IN ('low', 'medium', 'high')),
            market_timing_preference TEXT DEFAULT 'systematic' CHECK (market_timing_preference IN ('systematic', 'opportunistic', 'passive')),
            notification_preferences TEXT,
            custom_constraints TEXT,
            profile_notes TEXT,
            last_risk_assessment_date TIMESTAMP,
            profile_completeness_score INTEGER DEFAULT 0 CHECK (profile_completeness_score >= 0 AND profile_completeness_score <= 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create investment_goals table for detailed goal tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investment_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            goal_name TEXT NOT NULL,
            goal_type TEXT NOT NULL CHECK (goal_type IN ('retirement', 'house', 'education', 'emergency', 'wealth_building', 'other')),
            target_amount DECIMAL(15,2) NOT NULL,
            current_amount DECIMAL(15,2) DEFAULT 0,
            target_date DATE,
            priority_level INTEGER CHECK (priority_level >= 1 AND priority_level <= 5),
            risk_tolerance_override TEXT CHECK (risk_tolerance_override IN ('conservative', 'moderate', 'aggressive')),
            monthly_contribution DECIMAL(10,2) DEFAULT 0,
            goal_status TEXT DEFAULT 'active' CHECK (goal_status IN ('active', 'paused', 'completed', 'cancelled')),
            progress_percentage DECIMAL(5,2) DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create risk_assessment_history table for tracking risk profile changes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_assessment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
            risk_tolerance TEXT NOT NULL CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive')),
            assessment_method TEXT CHECK (assessment_method IN ('questionnaire', 'behavioral', 'portfolio_analysis', 'manual')),
            questionnaire_responses TEXT,
            key_factors TEXT,
            recommended_allocation TEXT,
            assessor_notes TEXT,
            is_current BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Create indexes for user investment profiles
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_investment_profiles_user_id 
        ON user_investment_profiles (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_investment_profiles_risk_tolerance 
        ON user_investment_profiles (risk_tolerance)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_investment_goals_user_id 
        ON investment_goals (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_investment_goals_status 
        ON investment_goals (goal_status)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_risk_assessment_history_user_id 
        ON risk_assessment_history (user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_risk_assessment_history_current 
        ON risk_assessment_history (user_id, is_current)
    ''')
    
    # Create market_context table for daily market data and trends
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL UNIQUE,
            nifty_value DECIMAL(10,2),
            nifty_change DECIMAL(10,2),
            nifty_change_percent DECIMAL(5,2),
            nifty_trend TEXT CHECK (nifty_trend IN ('bullish', 'bearish', 'neutral', 'volatile')),
            sensex_value DECIMAL(10,2),
            sensex_change DECIMAL(10,2),
            sensex_change_percent DECIMAL(5,2),
            market_sentiment TEXT CHECK (market_sentiment IN ('very_bullish', 'bullish', 'neutral', 'bearish', 'very_bearish')),
            volatility_index DECIMAL(5,2),
            market_volume BIGINT,
            advances_count INTEGER,
            declines_count INTEGER,
            unchanged_count INTEGER,
            sector_performance TEXT,
            top_gainers TEXT,
            top_losers TEXT,
            key_events TEXT,
            economic_indicators TEXT,
            global_market_impact TEXT,
            currency_rates TEXT,
            commodity_prices TEXT,
            bond_yields TEXT,
            market_breadth_ratio DECIMAL(5,2),
            fear_greed_index INTEGER CHECK (fear_greed_index >= 0 AND fear_greed_index <= 100),
            analyst_sentiment TEXT,
            news_sentiment_score DECIMAL(3,2),
            trading_session TEXT CHECK (trading_session IN ('pre_market', 'regular', 'post_market', 'closed')),
            market_status TEXT CHECK (market_status IN ('open', 'closed', 'holiday')),
            data_source TEXT,
            data_quality_score INTEGER CHECK (data_quality_score >= 0 AND data_quality_score <= 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sector_performance table for detailed sector analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sector_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            sector_name TEXT NOT NULL,
            sector_index_value DECIMAL(10,2),
            sector_change DECIMAL(10,2),
            sector_change_percent DECIMAL(5,2),
            sector_trend TEXT CHECK (sector_trend IN ('strong_bullish', 'bullish', 'neutral', 'bearish', 'strong_bearish')),
            market_cap BIGINT,
            volume BIGINT,
            pe_ratio DECIMAL(8,2),
            pb_ratio DECIMAL(8,2),
            dividend_yield DECIMAL(5,2),
            top_performers TEXT,
            worst_performers TEXT,
            sector_news TEXT,
            analyst_rating TEXT CHECK (analyst_rating IN ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell')),
            risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high', 'very_high')),
            growth_potential TEXT CHECK (growth_potential IN ('high', 'medium', 'low')),
            correlation_with_nifty DECIMAL(3,2),
            volatility_30d DECIMAL(5,2),
            momentum_score INTEGER CHECK (momentum_score >= 0 AND momentum_score <= 100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (date) REFERENCES market_context (date)
        )
    ''')
    
    # Create stock_market_data table for individual stock context
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            symbol TEXT NOT NULL,
            open_price DECIMAL(10,2),
            high_price DECIMAL(10,2),
            low_price DECIMAL(10,2),
            close_price DECIMAL(10,2),
            volume BIGINT,
            price_change DECIMAL(10,2),
            price_change_percent DECIMAL(5,2),
            market_cap BIGINT,
            pe_ratio DECIMAL(8,2),
            pb_ratio DECIMAL(8,2),
            dividend_yield DECIMAL(5,2),
            beta DECIMAL(5,2),
            volatility_30d DECIMAL(5,2),
            rsi DECIMAL(5,2),
            moving_avg_50d DECIMAL(10,2),
            moving_avg_200d DECIMAL(10,2),
            support_level DECIMAL(10,2),
            resistance_level DECIMAL(10,2),
            analyst_target_price DECIMAL(10,2),
            analyst_rating TEXT CHECK (analyst_rating IN ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell')),
            news_sentiment_score DECIMAL(3,2),
            social_sentiment_score DECIMAL(3,2),
            institutional_holding_percent DECIMAL(5,2),
            promoter_holding_percent DECIMAL(5,2),
            recent_news TEXT,
            earnings_date DATE,
            dividend_date DATE,
            stock_events TEXT,
            sector TEXT,
            industry TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create market_events table for significant market events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date DATE NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('earnings', 'policy', 'economic', 'geopolitical', 'corporate', 'technical')),
            event_title TEXT NOT NULL,
            event_description TEXT,
            impact_level TEXT CHECK (impact_level IN ('high', 'medium', 'low')),
            affected_sectors TEXT,
            affected_stocks TEXT,
            market_reaction TEXT,
            price_impact_estimate DECIMAL(5,2),
            duration_estimate TEXT CHECK (duration_estimate IN ('immediate', 'short_term', 'medium_term', 'long_term')),
            confidence_score INTEGER CHECK (confidence_score >= 0 AND confidence_score <= 100),
            data_source TEXT,
            analyst_notes TEXT,
            follow_up_required BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for market context tables
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_market_context_date 
        ON market_context (date DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_market_context_sentiment 
        ON market_context (market_sentiment, nifty_trend)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sector_performance_date_sector 
        ON sector_performance (date, sector_name)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sector_performance_trend 
        ON sector_performance (sector_trend, analyst_rating)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stock_market_data_date_symbol 
        ON stock_market_data (date, symbol)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stock_market_data_symbol 
        ON stock_market_data (symbol, date DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stock_market_data_performance 
        ON stock_market_data (price_change_percent, volume)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_market_events_date 
        ON market_events (event_date DESC)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_market_events_impact 
        ON market_events (impact_level, event_type)
    ''')
    
    conn.commit()
    conn.close()
    
    # Initialize trading engine tables
    try:
        from app.trading_engine.database_schema import create_trading_engine_tables
        create_trading_engine_tables()
        logger.info("Trading engine database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize trading engine tables: {e}")

def store_portfolio_snapshot(user_id: str, timestamp: str, holdings: str, positions: str) -> bool:
    """
    Stores a snapshot of the user's portfolio.
    """
    logger.info(f"DB: Starting portfolio snapshot storage for user {user_id}")
    logger.info(f"DB: Database path: {settings.database_path}")
    logger.info(f"DB: Timestamp: {timestamp}")
    logger.info(f"DB: Holdings length: {len(holdings)}")
    logger.info(f"DB: Positions length: {len(positions)}")
    try:
        conn = sqlite3.connect(settings.database_path)
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_snapshots'")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor.execute(
            "INSERT INTO portfolio_snapshots (user_id, timestamp, holdings, positions) VALUES (?, ?, ?, ?)",
            (user_id, timestamp, holdings, positions)
        )
        logger.info(f"DB: INSERT query executed successfully")
        conn.commit()
        logger.info(f"DB: Transaction committed successfully")
        logger.info(f"Successfully stored portfolio snapshot for user {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error storing portfolio snapshot for user {user_id}: {e}")
        logger.error(f"DB: SQLite error type: {type(e).__name__}")
        logger.error(f"DB: SQLite error details: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing portfolio snapshot for user {user_id}: {e}")
        logger.error(f"DB: Error type: {type(e).__name__}")
        logger.error(f"DB: Error details: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()
            logger.info(f"DB: Database connection closed")

def get_latest_portfolio_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent portfolio snapshot for a given user.
    Returns raw JSON strings for holdings and positions to avoid double parsing.
    """
    conn = None
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, holdings, positions FROM portfolio_snapshots WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            # Return raw JSON strings - let the calling service handle parsing
            return {
                "timestamp": result[0], 
                "holdings": result[1],  # Raw JSON string
                "positions": result[2]  # Raw JSON string
            }
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving latest portfolio snapshot for user {user_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()
            conn.close()

def store_user_credentials(
    user_id: str, 
    api_key: str, 
    api_secret: str, 
    access_token: str,
    user_name: Optional[str] = None,
    email: Optional[str] = None,
    last_successful_connection: Optional[str] = None,
    token_expiry: Optional[str] = None,
    last_error: Optional[str] = None
) -> bool:
    """
    Store user credentials securely in database
    Args:
        user_id: User identifier from broker
        api_key: Broker API key
        api_secret: Broker API secret  
        access_token: Broker access token
        user_name: User's name
        email: User's email
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        encrypted_api_secret = encrypt_data(api_secret)
        encrypted_access_token = encrypt_data(access_token)
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, api_key, api_secret, access_token, user_name, email, updated_at, last_successful_connection, token_expiry, last_error)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
        ''', (user_id, api_key, encrypted_api_secret, encrypted_access_token, user_name, email, last_successful_connection, token_expiry, last_error))
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored credentials for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing user credentials: {str(e)}")
        return False

def get_user_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user credentials from database
    Args:
        user_id: User identifier
    Returns:
        Dict with user credentials or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, api_key, api_secret, access_token, user_name, email, last_successful_connection, token_expiry, last_error
            FROM users WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        if result:
            decrypted_api_secret = decrypt_data(result[2])
            decrypted_access_token = decrypt_data(result[3])
            return {
                "user_id": result[0],
                "api_key": result[1],
                "api_secret": decrypted_api_secret,
                "access_token": decrypted_access_token,
                "user_name": result[4],
                "email": result[5],
                "last_successful_connection": result[6],
                "token_expiry": result[7],
                "last_error": result[8]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving user credentials: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def delete_user_credentials(user_id: str) -> bool:
    """
    Delete user credentials from database
    Args:
        user_id: User identifier
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Successfully deleted credentials for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting user credentials: {str(e)}")
        return False

def get_user_credentials_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user credentials by email
    Args:
        email: User's email address
    Returns:
        Dict with user credentials or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, api_key, api_secret, access_token, user_name, email, last_successful_connection, token_expiry, last_error
            FROM users WHERE email = ?
        ''', (email,))
        result = cursor.fetchone()
        if result:
            decrypted_api_secret = decrypt_data(result[2])
            decrypted_access_token = decrypt_data(result[3])
            return {
                "user_id": result[0],
                "api_key": result[1],
                "api_secret": decrypted_api_secret,
                "access_token": decrypted_access_token,
                "user_name": result[4],
                "email": result[5],
                "last_successful_connection": result[6],
                "token_expiry": result[7],
                "last_error": result[8]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving user credentials by email: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def user_exists(user_id: str) -> bool:
    """
    Check if user exists in database
    Args:
        user_id: User identifier
    Returns:
        bool: True if user exists, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        logger.error(f"Error checking if user exists: {str(e)}")
        return False

def check_database_health() -> dict:
    """
    Check database health and return status information
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        table_counts = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_counts[table] = count
        import os
        db_size = os.path.getsize(settings.database_path) if os.path.exists(settings.database_path) else 0
        conn.close()
        return {
            "status": "healthy",
            "database_path": settings.database_path,
            "tables": tables,
            "table_counts": table_counts,
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
            "database_path": settings.database_path
        }

def store_ai_preferences(
    user_id: str,
    openai_api_key: Optional[str] = None,
    claude_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    grok_api_key: Optional[str] = None,
    preferred_provider: str = "auto",
    provider_priorities: Optional[str] = None,
    cost_limits: Optional[str] = None,
    risk_tolerance: str = "medium",
    trading_style: str = "balanced"
) -> bool:
    """
    Store AI preferences for a user
    Args:
        user_id: User identifier
        openai_api_key: OpenAI API key (encrypted)
        claude_api_key: Claude API key (encrypted)
        gemini_api_key: Gemini API key (encrypted)
        grok_api_key: Grok API key (encrypted)
        preferred_provider: Preferred AI provider
        provider_priorities: JSON string of provider priorities by task type
        cost_limits: JSON string of cost limits per provider
        risk_tolerance: User's risk tolerance level
        trading_style: User's trading style preference
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Encrypt API keys if provided
        encrypted_openai = encrypt_data(openai_api_key) if openai_api_key else None
        encrypted_claude = encrypt_data(claude_api_key) if claude_api_key else None
        encrypted_gemini = encrypt_data(gemini_api_key) if gemini_api_key else None
        encrypted_grok = encrypt_data(grok_api_key) if grok_api_key else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO ai_user_preferences 
            (user_id, openai_api_key, claude_api_key, gemini_api_key, grok_api_key, 
             preferred_provider, provider_priorities, cost_limits, risk_tolerance, 
             trading_style, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, encrypted_openai, encrypted_claude, encrypted_gemini, encrypted_grok,
              preferred_provider, provider_priorities, cost_limits, risk_tolerance, trading_style))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored AI preferences for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing AI preferences for user {user_id}: {str(e)}")
        return False

def get_ai_preferences(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve AI preferences for a user
    Args:
        user_id: User identifier
    Returns:
        Dict with AI preferences or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT openai_api_key, claude_api_key, gemini_api_key, grok_api_key, 
                   preferred_provider, provider_priorities, cost_limits, 
                   risk_tolerance, trading_style, created_at, updated_at
            FROM ai_user_preferences WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Decrypt API keys if they exist
            openai_key = decrypt_data(result[0]) if result[0] else None
            claude_key = decrypt_data(result[1]) if result[1] else None
            gemini_key = decrypt_data(result[2]) if result[2] else None
            grok_key = decrypt_data(result[3]) if result[3] else None
            
            return {
                "openai_api_key": openai_key,
                "claude_api_key": claude_key,
                "gemini_api_key": gemini_key,
                "grok_api_key": grok_key,
                "preferred_provider": result[4],
                "provider_priorities": result[5],
                "cost_limits": result[6],
                "risk_tolerance": result[7],
                "trading_style": result[8],
                "created_at": result[9],
                "updated_at": result[10]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving AI preferences for user {user_id}: {str(e)}")
        return None

def delete_ai_preferences(user_id: str) -> bool:
    """
    Delete AI preferences for a user
    Args:
        user_id: User identifier
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ai_user_preferences WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Successfully deleted AI preferences for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting AI preferences for user {user_id}: {str(e)}")
        return False

def get_ai_client_for_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get AI client configuration for AutoBot usage
    Args:
        user_id: User identifier
    Returns:
        Dict with AI client config or None if no preferences found
    """
    preferences = get_ai_preferences(user_id)
    if not preferences:
        logger.warning(f"No AI preferences found for user {user_id}")
        return None
    
    # Check which provider has a valid key
    providers = []
    if preferences.get("openai_api_key"):
        providers.append("openai")
    if preferences.get("claude_api_key"):
        providers.append("claude")
    if preferences.get("gemini_api_key"):
        providers.append("gemini")
    
    if not providers:
        logger.warning(f"No valid AI keys found for user {user_id}")
        return None
    
    # Determine preferred provider
    preferred = preferences.get("preferred_provider", "auto")
    if preferred == "auto":
        # Use first available provider
        selected_provider = providers[0]
    elif preferred in providers:
        selected_provider = preferred
    else:
        # Fallback to first available
        selected_provider = providers[0]
    
    return {
        "user_id": user_id,
        "selected_provider": selected_provider,
        "api_key": preferences.get(f"{selected_provider}_api_key"),
        "available_providers": providers,
        "preferred_provider": preferred
    }
# ========================================
# Chat Session Management Functions
# ========================================

def create_chat_session(user_id: str, thread_id: str, session_name: Optional[str] = None) -> Optional[int]:
    """
    Create a new chat session
    Args:
        user_id: User identifier
        thread_id: Thread identifier for the conversation
        session_name: Optional name for the session
    Returns:
        Session ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_chat_sessions (user_id, thread_id, session_name)
            VALUES (?, ?, ?)
        ''', (user_id, thread_id, session_name))
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Created chat session {session_id} for user {user_id}")
        return session_id
    except Exception as e:
        logger.error(f"Error creating chat session for user {user_id}: {str(e)}")
        return None

def store_chat_message(
    session_id: int,
    thread_id: str,
    user_id: str,
    message_type: str,
    content: str,
    metadata: Optional[str] = None,
    provider_used: Optional[str] = None,
    tokens_used: Optional[int] = None,
    cost_cents: Optional[int] = None
) -> bool:
    """
    Store a chat message
    Args:
        session_id: Chat session ID
        thread_id: Thread identifier
        user_id: User identifier
        message_type: 'user' or 'assistant'
        content: Message content
        metadata: Optional JSON metadata
        provider_used: AI provider used for response
        tokens_used: Number of tokens used
        cost_cents: Cost in cents
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_chat_messages 
            (session_id, thread_id, user_id, message_type, content, metadata, 
             provider_used, tokens_used, cost_cents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, thread_id, user_id, message_type, content, metadata,
              provider_used, tokens_used, cost_cents))
        conn.commit()
        conn.close()
        logger.info(f"Stored {message_type} message for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing chat message: {str(e)}")
        return False

def get_chat_sessions(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get chat sessions for a user
    Args:
        user_id: User identifier
        limit: Maximum number of sessions to return
    Returns:
        List of chat sessions
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, thread_id, session_name, created_at, updated_at, is_active
            FROM ai_chat_sessions 
            WHERE user_id = ? AND is_active = TRUE
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (user_id, limit))
        results = cursor.fetchall()
        conn.close()
        
        sessions = []
        for result in results:
            sessions.append({
                "id": result[0],
                "thread_id": result[1],
                "session_name": result[2],
                "created_at": result[3],
                "updated_at": result[4],
                "is_active": bool(result[5])
            })
        return sessions
    except Exception as e:
        logger.error(f"Error retrieving chat sessions for user {user_id}: {str(e)}")
        return []

def get_chat_messages(session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get chat messages for a session
    Args:
        session_id: Chat session ID
        limit: Maximum number of messages to return
    Returns:
        List of chat messages
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, message_type, content, metadata, provider_used, 
                   tokens_used, cost_cents, created_at
            FROM ai_chat_messages 
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        ''', (session_id, limit))
        results = cursor.fetchall()
        conn.close()
        
        messages = []
        for result in results:
            messages.append({
                "id": result[0],
                "message_type": result[1],
                "content": result[2],
                "metadata": result[3],
                "provider_used": result[4],
                "tokens_used": result[5],
                "cost_cents": result[6],
                "created_at": result[7]
            })
        return messages
    except Exception as e:
        logger.error(f"Error retrieving chat messages for session {session_id}: {str(e)}")
        return []

# ========================================
# Strategy Management Functions
# ========================================

def store_ai_strategy(
    user_id: str,
    strategy_name: str,
    strategy_type: str,
    parameters: str,
    rules: str,
    risk_management: Optional[str] = None,
    backtesting_results: Optional[str] = None,
    performance_metrics: Optional[str] = None
) -> Optional[int]:
    """
    Store an AI-generated trading strategy
    Args:
        user_id: User identifier
        strategy_name: Name of the strategy
        strategy_type: Type of strategy (momentum, mean_reversion, etc.)
        parameters: JSON string of strategy parameters
        rules: JSON string of trading rules
        risk_management: JSON string of risk management rules
        backtesting_results: JSON string of backtest results
        performance_metrics: JSON string of performance metrics
    Returns:
        Strategy ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_strategies 
            (user_id, strategy_name, strategy_type, parameters, rules, 
             risk_management, backtesting_results, performance_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, strategy_name, strategy_type, parameters, rules,
              risk_management, backtesting_results, performance_metrics))
        strategy_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Stored strategy {strategy_id} for user {user_id}")
        return strategy_id
    except Exception as e:
        logger.error(f"Error storing strategy for user {user_id}: {str(e)}")
        return None

def get_user_strategies(user_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
    """
    Get strategies for a user
    Args:
        user_id: User identifier
        active_only: Whether to return only active strategies
    Returns:
        List of strategies
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, strategy_name, strategy_type, parameters, rules,
                   risk_management, backtesting_results, performance_metrics,
                   is_active, created_at, updated_at
            FROM ai_strategies 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if active_only:
            query += ' AND is_active = TRUE'
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        strategies = []
        for result in results:
            strategies.append({
                "id": result[0],
                "strategy_name": result[1],
                "strategy_type": result[2],
                "parameters": result[3],
                "rules": result[4],
                "risk_management": result[5],
                "backtesting_results": result[6],
                "performance_metrics": result[7],
                "is_active": bool(result[8]),
                "created_at": result[9],
                "updated_at": result[10]
            })
        return strategies
    except Exception as e:
        logger.error(f"Error retrieving strategies for user {user_id}: {str(e)}")
        return []

# ========================================
# Trading Signals Functions
# ========================================

def store_trading_signal(
    user_id: str,
    symbol: str,
    signal_type: str,
    confidence_score: float,
    reasoning: str,
    target_price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    position_size: Optional[float] = None,
    market_data: Optional[str] = None,
    provider_used: Optional[str] = None,
    expires_at: Optional[str] = None
) -> Optional[int]:
    """
    Store a trading signal
    Args:
        user_id: User identifier
        symbol: Trading symbol
        signal_type: 'buy', 'sell', or 'hold'
        confidence_score: Confidence score (0.0 to 1.0)
        reasoning: Explanation for the signal
        target_price: Target price for the trade
        stop_loss: Stop loss price
        take_profit: Take profit price
        position_size: Recommended position size
        market_data: JSON string of market data used
        provider_used: AI provider that generated the signal
        expires_at: When the signal expires
    Returns:
        Signal ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_trading_signals 
            (user_id, symbol, signal_type, confidence_score, reasoning,
             target_price, stop_loss, take_profit, position_size, 
             market_data, provider_used, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, symbol, signal_type, confidence_score, reasoning,
              target_price, stop_loss, take_profit, position_size,
              market_data, provider_used, expires_at))
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Stored trading signal {signal_id} for user {user_id}")
        return signal_id
    except Exception as e:
        logger.error(f"Error storing trading signal for user {user_id}: {str(e)}")
        return None

def get_active_signals(user_id: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get active trading signals for a user
    Args:
        user_id: User identifier
        symbol: Optional symbol filter
    Returns:
        List of active trading signals
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, symbol, signal_type, confidence_score, reasoning,
                   target_price, stop_loss, take_profit, position_size,
                   market_data, provider_used, expires_at, created_at
            FROM ai_trading_signals 
            WHERE user_id = ? AND is_active = TRUE
        '''
        params = [user_id]
        
        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol)
        
        query += ' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)'
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        signals = []
        for result in results:
            signals.append({
                "id": result[0],
                "symbol": result[1],
                "signal_type": result[2],
                "confidence_score": result[3],
                "reasoning": result[4],
                "target_price": result[5],
                "stop_loss": result[6],
                "take_profit": result[7],
                "position_size": result[8],
                "market_data": result[9],
                "provider_used": result[10],
                "expires_at": result[11],
                "created_at": result[12]
            })
        return signals
    except Exception as e:
        logger.error(f"Error retrieving trading signals for user {user_id}: {str(e)}")
        return []

# ========================================
# Usage Tracking Functions
# ========================================

def track_ai_usage(
    user_id: str,
    provider: str,
    operation_type: str,
    tokens_used: Optional[int] = None,
    cost_cents: Optional[int] = None,
    response_time_ms: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> bool:
    """
    Track AI usage for cost monitoring and analytics
    Args:
        user_id: User identifier
        provider: AI provider used
        operation_type: Type of operation (chat, analysis, strategy, etc.)
        tokens_used: Number of tokens used
        cost_cents: Cost in cents
        response_time_ms: Response time in milliseconds
        success: Whether the operation was successful
        error_message: Error message if operation failed
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_usage_tracking 
            (user_id, provider, operation_type, tokens_used, cost_cents,
             response_time_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, provider, operation_type, tokens_used, cost_cents,
              response_time_ms, success, error_message))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error tracking AI usage for user {user_id}: {str(e)}")
        return False

def get_usage_statistics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Get usage statistics for a user
    Args:
        user_id: User identifier
        days: Number of days to look back
    Returns:
        Dictionary with usage statistics
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Get usage by provider
        cursor.execute('''
            SELECT provider, COUNT(*) as requests, SUM(tokens_used) as total_tokens,
                   SUM(cost_cents) as total_cost_cents, AVG(response_time_ms) as avg_response_time
            FROM ai_usage_tracking 
            WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
            GROUP BY provider
        '''.format(days), (user_id,))
        provider_stats = cursor.fetchall()
        
        # Get usage by operation type
        cursor.execute('''
            SELECT operation_type, COUNT(*) as requests, SUM(cost_cents) as total_cost_cents
            FROM ai_usage_tracking 
            WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
            GROUP BY operation_type
        '''.format(days), (user_id,))
        operation_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "provider_statistics": [
                {
                    "provider": stat[0],
                    "requests": stat[1],
                    "total_tokens": stat[2] or 0,
                    "total_cost_cents": stat[3] or 0,
                    "avg_response_time_ms": stat[4] or 0
                }
                for stat in provider_stats
            ],
            "operation_statistics": [
                {
                    "operation_type": stat[0],
                    "requests": stat[1],
                    "total_cost_cents": stat[2] or 0
                }
                for stat in operation_stats
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving usage statistics for user {user_id}: {str(e)}")
        return {"user_id": user_id, "period_days": days, "provider_statistics": [], "operation_statistics": []}

# ========================================
# Analysis Results Functions
# ========================================

def store_analysis_result(
    user_id: str,
    analysis_type: str,
    symbols: Optional[str] = None,
    input_data: Optional[str] = None,
    analysis_result: str = "",
    provider_used: Optional[str] = None,
    confidence_score: Optional[float] = None
) -> Optional[int]:
    """
    Store an analysis result
    Args:
        user_id: User identifier
        analysis_type: Type of analysis (technical, fundamental, sentiment, etc.)
        symbols: JSON string of symbols analyzed
        input_data: JSON string of input data
        analysis_result: JSON string of analysis results
        provider_used: AI provider used
        confidence_score: Confidence score for the analysis
    Returns:
        Analysis ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO ai_analysis_results 
            (user_id, analysis_type, symbols, input_data, analysis_result,
             provider_used, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, analysis_type, symbols, input_data, analysis_result,
              provider_used, confidence_score))
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Stored analysis result {analysis_id} for user {user_id}")
        return analysis_id
    except Exception as e:
        logger.error(f"Error storing analysis result for user {user_id}: {str(e)}")
        return None

def get_recent_analyses(user_id: str, analysis_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent analysis results for a user
    Args:
        user_id: User identifier
        analysis_type: Optional filter by analysis type
        limit: Maximum number of results to return
    Returns:
        List of analysis results
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, analysis_type, symbols, input_data, analysis_result,
                   provider_used, confidence_score, created_at
            FROM ai_analysis_results 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if analysis_type:
            query += ' AND analysis_type = ?'
            params.append(analysis_type)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        analyses = []
        for result in results:
            analyses.append({
                "id": result[0],
                "analysis_type": result[1],
                "symbols": result[2],
                "input_data": result[3],
                "analysis_result": result[4],
                "provider_used": result[5],
                "confidence_score": result[6],
                "created_at": result[7]
            })
        return analyses
    except Exception as e:
        logger.error(f"Error retrieving analysis results for user {user_id}: {str(e)}")
        return []
# ========================================
# Enhanced Recommendations Management Functions
# ========================================

def store_enhanced_recommendations(
    user_id: str,
    analysis_id: str,
    recommendations: List[Dict[str, Any]]
) -> bool:
    """
    Store enhanced AI recommendations in the database
    Args:
        user_id: User identifier
        analysis_id: Analysis session identifier
        recommendations: List of recommendation dictionaries
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        for rec in recommendations:
            # Calculate expiry date based on timeframe
            expires_at = None
            timeframe = rec.get('timeframe', 'SHORT_TERM')
            if timeframe == 'IMMEDIATE':
                expires_at = 'datetime("now", "+7 days")'
            elif timeframe == 'SHORT_TERM':
                expires_at = 'datetime("now", "+30 days")'
            elif timeframe == 'LONG_TERM':
                expires_at = 'datetime("now", "+90 days")'
            
            cursor.execute('''
                INSERT INTO enhanced_recommendations (
                    user_id, analysis_id, stock_symbol, current_allocation, target_allocation,
                    action_type, quantity_change, value_change, current_price, reasoning,
                    confidence_score, priority_level, timeframe, expected_impact, risk_warning,
                    optimal_timing, auto_trading_eligible, market_context, sector, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ''' + expires_at + ''')
            ''', (
                user_id,
                analysis_id,
                rec.get('symbol', ''),
                rec.get('current_allocation', 0.0),
                rec.get('target_allocation', 0.0),
                rec.get('action', 'HOLD'),
                rec.get('quantity_change', 0),
                rec.get('value_change', 0.0),
                rec.get('current_price', 0.0),
                rec.get('reasoning', ''),
                rec.get('confidence', 75),
                rec.get('priority', 'MEDIUM'),
                rec.get('timeframe', 'SHORT_TERM'),
                rec.get('expected_impact', ''),
                rec.get('risk_warning', ''),
                rec.get('optimal_timing', ''),
                rec.get('auto_trading_eligible', False),
                rec.get('market_context', ''),
                rec.get('sector', '')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored {len(recommendations)} enhanced recommendations for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing enhanced recommendations for user {user_id}: {str(e)}")
        return False

def get_enhanced_recommendations(
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieve enhanced recommendations for a user
    Args:
        user_id: User identifier
        status: Filter by implementation status
        priority: Filter by priority level
        symbol: Filter by stock symbol
        limit: Maximum number of recommendations to return
    Returns:
        List of recommendation dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Build query with filters
        query = '''
            SELECT id, analysis_id, stock_symbol, current_allocation, target_allocation,
                   action_type, quantity_change, value_change, current_price, reasoning,
                   confidence_score, priority_level, timeframe, expected_impact, risk_warning,
                   optimal_timing, auto_trading_eligible, market_context, sector,
                   implementation_status, implementation_date, implementation_method,
                   created_at, updated_at, expires_at
            FROM enhanced_recommendations 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if status:
            query += ' AND implementation_status = ?'
            params.append(status)
        
        if priority:
            query += ' AND priority_level = ?'
            params.append(priority)
        
        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        recommendations = []
        for result in results:
            recommendations.append({
                "id": result[0],
                "analysis_id": result[1],
                "symbol": result[2],
                "current_allocation": result[3],
                "target_allocation": result[4],
                "action": result[5],
                "quantity_change": result[6],
                "value_change": result[7],
                "current_price": result[8],
                "reasoning": result[9],
                "confidence": result[10],
                "priority": result[11],
                "timeframe": result[12],
                "expected_impact": result[13],
                "risk_warning": result[14],
                "optimal_timing": result[15],
                "auto_trading_eligible": bool(result[16]),
                "market_context": result[17],
                "sector": result[18],
                "implementation_status": result[19],
                "implementation_date": result[20],
                "implementation_method": result[21],
                "created_at": result[22],
                "updated_at": result[23],
                "expires_at": result[24]
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error retrieving enhanced recommendations for user {user_id}: {str(e)}")
        return []

def update_recommendation_status(
    recommendation_id: int,
    user_id: str,
    status: str,
    implementation_method: Optional[str] = None,
    implementation_price: Optional[float] = None
) -> bool:
    """
    Update the implementation status of a recommendation
    Args:
        recommendation_id: Recommendation ID
        user_id: User identifier
        status: New implementation status
        implementation_method: How the recommendation was implemented
        implementation_price: Price at which it was implemented
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Update recommendation status
        cursor.execute('''
            UPDATE enhanced_recommendations 
            SET implementation_status = ?, 
                implementation_date = CURRENT_TIMESTAMP,
                implementation_method = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (status, implementation_method, recommendation_id, user_id))
        
        # If implemented, create performance tracking record
        if status == 'IMPLEMENTED' and implementation_price:
            cursor.execute('''
                INSERT INTO recommendation_performance (
                    recommendation_id, user_id, stock_symbol, implementation_date,
                    implementation_method, implementation_price, predicted_price
                ) 
                SELECT ?, ?, stock_symbol, CURRENT_TIMESTAMP, ?, ?, current_price
                FROM enhanced_recommendations 
                WHERE id = ? AND user_id = ?
            ''', (
                recommendation_id, user_id, implementation_method or 'MANUAL', 
                implementation_price, recommendation_id, user_id
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Updated recommendation {recommendation_id} status to {status} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating recommendation status: {str(e)}")
        return False

def get_recommendation_performance(
    user_id: str,
    days: int = 30,
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get performance metrics for implemented recommendations
    Args:
        user_id: User identifier
        days: Number of days to look back
        symbol: Optional symbol filter
    Returns:
        Dictionary with performance metrics
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Build query with filters
        query = '''
            SELECT rp.*, er.action_type, er.confidence_score, er.priority_level
            FROM recommendation_performance rp
            JOIN enhanced_recommendations er ON rp.recommendation_id = er.id
            WHERE rp.user_id = ? 
            AND rp.implementation_date >= datetime('now', '-{} days')
        '''.format(days)
        
        params = [user_id]
        
        if symbol:
            query += ' AND rp.stock_symbol = ?'
            params.append(symbol)
        
        query += ' ORDER BY rp.implementation_date DESC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                "total_count": 0,
                "implemented_count": 0,
                "successful_count": 0,
                "accuracy_rate": 0.0,
                "average_return": 0.0,
                "detailed_results": []
            }
        
        # Calculate performance metrics
        total_count = len(results)
        successful_count = sum(1 for r in results if r[15])  # recommendation_success column
        accuracy_rate = (successful_count / total_count * 100) if total_count > 0 else 0
        
        # Calculate average return (simplified)
        returns = [r[11] for r in results if r[11] is not None]  # portfolio_impact column
        average_return = sum(returns) / len(returns) if returns else 0
        
        detailed_results = []
        for result in results:
            detailed_results.append({
                "recommendation_id": result[1],
                "symbol": result[2],
                "implementation_date": result[3],
                "implementation_method": result[4],
                "implementation_price": result[5],
                "predicted_price": result[6],
                "actual_outcome_30d": result[9],
                "accuracy_score_30d": result[12],
                "user_feedback_rating": result[13],
                "recommendation_success": bool(result[15]),
                "portfolio_impact": result[11]
            })
        
        return {
            "total_count": total_count,
            "implemented_count": total_count,  # All results are implemented
            "successful_count": successful_count,
            "accuracy_rate": accuracy_rate,
            "average_return": average_return,
            "best_performer": max(detailed_results, key=lambda x: x.get('portfolio_impact', 0)) if detailed_results else None,
            "worst_performer": min(detailed_results, key=lambda x: x.get('portfolio_impact', 0)) if detailed_results else None,
            "detailed_results": detailed_results
        }
        
    except Exception as e:
        logger.error(f"Error retrieving recommendation performance for user {user_id}: {str(e)}")
        return {
            "total_count": 0,
            "implemented_count": 0,
            "successful_count": 0,
            "accuracy_rate": 0.0,
            "average_return": 0.0,
            "detailed_results": []
        }

def get_recommendations_by_ids(
    recommendation_ids: List[int],
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Get specific recommendations by their IDs
    Args:
        recommendation_ids: List of recommendation IDs
        user_id: User identifier for security
    Returns:
        List of recommendation dictionaries
    """
    try:
        if not recommendation_ids:
            return []
        
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Create placeholders for the IN clause
        placeholders = ','.join('?' * len(recommendation_ids))
        query = f'''
            SELECT id, analysis_id, stock_symbol, current_allocation, target_allocation,
                   action_type, quantity_change, value_change, current_price, reasoning,
                   confidence_score, priority_level, timeframe, expected_impact, risk_warning,
                   optimal_timing, auto_trading_eligible, market_context, sector,
                   implementation_status, created_at
            FROM enhanced_recommendations 
            WHERE id IN ({placeholders}) AND user_id = ?
        '''
        
        params = recommendation_ids + [user_id]
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        recommendations = []
        for result in results:
            recommendations.append({
                "id": result[0],
                "analysis_id": result[1],
                "symbol": result[2],
                "current_allocation": result[3],
                "target_allocation": result[4],
                "action": result[5],
                "quantity_change": result[6],
                "value_change": result[7],
                "current_price": result[8],
                "reasoning": result[9],
                "confidence": result[10],
                "priority": result[11],
                "timeframe": result[12],
                "expected_impact": result[13],
                "risk_warning": result[14],
                "optimal_timing": result[15],
                "auto_trading_eligible": bool(result[16]),
                "market_context": result[17],
                "sector": result[18],
                "implementation_status": result[19],
                "created_at": result[20]
            })
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error retrieving recommendations by IDs: {str(e)}")
        return []

def cleanup_expired_recommendations() -> int:
    """
    Clean up expired recommendations
    Returns:
        Number of recommendations cleaned up
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Update expired recommendations
        cursor.execute('''
            UPDATE enhanced_recommendations 
            SET implementation_status = 'EXPIRED',
                updated_at = CURRENT_TIMESTAMP
            WHERE expires_at < CURRENT_TIMESTAMP 
            AND implementation_status = 'PENDING'
        ''')
        
        expired_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired recommendations")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"Error cleaning up expired recommendations: {str(e)}")
        return 0

# ========================================
# User Investment Profile Management Functions
# ========================================

def store_user_investment_profile(
    user_id: str,
    profile_data: Dict[str, Any]
) -> bool:
    """
    Store or update user investment profile
    Args:
        user_id: User identifier
        profile_data: Dictionary containing profile information
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Calculate profile completeness score
        completeness_score = calculate_profile_completeness(profile_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_investment_profiles (
                user_id, risk_tolerance, investment_timeline, investment_goals,
                preferred_sectors, avoided_sectors, max_position_size, min_position_size,
                trading_frequency, auto_trading_enabled, auto_trading_max_amount,
                stop_loss_preference, take_profit_preference, rebalancing_frequency,
                dividend_preference, tax_optimization_enabled, esg_preference,
                international_exposure_preference, cash_allocation_preference,
                volatility_tolerance, market_timing_preference, notification_preferences,
                custom_constraints, profile_notes, profile_completeness_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id,
            profile_data.get('risk_tolerance', 'moderate'),
            profile_data.get('investment_timeline', 'medium_term'),
            json.dumps(profile_data.get('investment_goals', [])),
            json.dumps(profile_data.get('preferred_sectors', [])),
            json.dumps(profile_data.get('avoided_sectors', [])),
            profile_data.get('max_position_size', 15.0),
            profile_data.get('min_position_size', 2.0),
            profile_data.get('trading_frequency', 'monthly'),
            profile_data.get('auto_trading_enabled', False),
            profile_data.get('auto_trading_max_amount', 100000),
            profile_data.get('stop_loss_preference', 10.0),
            profile_data.get('take_profit_preference', 25.0),
            profile_data.get('rebalancing_frequency', 'monthly'),
            profile_data.get('dividend_preference', 'reinvest'),
            profile_data.get('tax_optimization_enabled', True),
            profile_data.get('esg_preference', False),
            profile_data.get('international_exposure_preference', 10.0),
            profile_data.get('cash_allocation_preference', 5.0),
            profile_data.get('volatility_tolerance', 'medium'),
            profile_data.get('market_timing_preference', 'systematic'),
            json.dumps(profile_data.get('notification_preferences', {})),
            profile_data.get('custom_constraints', ''),
            profile_data.get('profile_notes', ''),
            completeness_score
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored investment profile for user: {user_id} (completeness: {completeness_score}%)")
        return True
        
    except Exception as e:
        logger.error(f"Error storing investment profile for user {user_id}: {str(e)}")
        return False

def save_user_investment_profile(user_id: str, profile_data: Dict[str, Any]) -> bool:
    """Wrapper function for storing user investment profile"""
    return store_user_investment_profile(user_id, profile_data)

def get_user_investment_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user investment profile
    Args:
        user_id: User identifier
    Returns:
        Dictionary with profile data or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT risk_tolerance, investment_timeline, investment_goals, preferred_sectors,
                   avoided_sectors, max_position_size, min_position_size, trading_frequency,
                   auto_trading_enabled, auto_trading_max_amount, stop_loss_preference,
                   take_profit_preference, rebalancing_frequency, dividend_preference,
                   tax_optimization_enabled, esg_preference, international_exposure_preference,
                   cash_allocation_preference, volatility_tolerance, market_timing_preference,
                   notification_preferences, custom_constraints, profile_notes,
                   last_risk_assessment_date, profile_completeness_score, created_at, updated_at
            FROM user_investment_profiles 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "user_id": user_id,
                "risk_tolerance": result[0],
                "investment_timeline": result[1],
                "investment_goals": json.loads(result[2]) if result[2] else [],
                "preferred_sectors": json.loads(result[3]) if result[3] else [],
                "avoided_sectors": json.loads(result[4]) if result[4] else [],
                "max_position_size": result[5],
                "min_position_size": result[6],
                "trading_frequency": result[7],
                "auto_trading_enabled": bool(result[8]),
                "auto_trading_max_amount": result[9],
                "stop_loss_preference": result[10],
                "take_profit_preference": result[11],
                "rebalancing_frequency": result[12],
                "dividend_preference": result[13],
                "tax_optimization_enabled": bool(result[14]),
                "esg_preference": bool(result[15]),
                "international_exposure_preference": result[16],
                "cash_allocation_preference": result[17],
                "volatility_tolerance": result[18],
                "market_timing_preference": result[19],
                "notification_preferences": json.loads(result[20]) if result[20] else {},
                "custom_constraints": result[21],
                "profile_notes": result[22],
                "last_risk_assessment_date": result[23],
                "profile_completeness_score": result[24],
                "created_at": result[25],
                "updated_at": result[26]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving investment profile for user {user_id}: {str(e)}")
        return None

def store_investment_goal(
    user_id: str,
    goal_data: Dict[str, Any]
) -> Optional[int]:
    """
    Store a new investment goal
    Args:
        user_id: User identifier
        goal_data: Dictionary containing goal information
    Returns:
        Goal ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO investment_goals (
                user_id, goal_name, goal_type, target_amount, current_amount,
                target_date, priority_level, risk_tolerance_override,
                monthly_contribution, goal_status, progress_percentage, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            goal_data.get('goal_name', ''),
            goal_data.get('goal_type', 'other'),
            goal_data.get('target_amount', 0),
            goal_data.get('current_amount', 0),
            goal_data.get('target_date'),
            goal_data.get('priority_level', 3),
            goal_data.get('risk_tolerance_override'),
            goal_data.get('monthly_contribution', 0),
            goal_data.get('goal_status', 'active'),
            goal_data.get('progress_percentage', 0),
            goal_data.get('notes', '')
        ))
        
        goal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully stored investment goal {goal_id} for user: {user_id}")
        return goal_id
        
    except Exception as e:
        logger.error(f"Error storing investment goal for user {user_id}: {str(e)}")
        return None

def get_user_investment_goals(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve user investment goals
    Args:
        user_id: User identifier
        status: Optional status filter
    Returns:
        List of goal dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, goal_name, goal_type, target_amount, current_amount,
                   target_date, priority_level, risk_tolerance_override,
                   monthly_contribution, goal_status, progress_percentage,
                   notes, created_at, updated_at
            FROM investment_goals 
            WHERE user_id = ?
        '''
        params = [user_id]
        
        if status:
            query += ' AND goal_status = ?'
            params.append(status)
        
        query += ' ORDER BY priority_level ASC, target_date ASC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        goals = []
        for result in results:
            goals.append({
                "id": result[0],
                "goal_name": result[1],
                "goal_type": result[2],
                "target_amount": result[3],
                "current_amount": result[4],
                "target_date": result[5],
                "priority_level": result[6],
                "risk_tolerance_override": result[7],
                "monthly_contribution": result[8],
                "goal_status": result[9],
                "progress_percentage": result[10],
                "notes": result[11],
                "created_at": result[12],
                "updated_at": result[13]
            })
        
        return goals
        
    except Exception as e:
        logger.error(f"Error retrieving investment goals for user {user_id}: {str(e)}")
        return []

def store_risk_assessment(
    user_id: str,
    assessment_data: Dict[str, Any]
) -> bool:
    """
    Store a new risk assessment
    Args:
        user_id: User identifier
        assessment_data: Dictionary containing assessment information
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Mark previous assessments as not current
        cursor.execute('''
            UPDATE risk_assessment_history 
            SET is_current = FALSE 
            WHERE user_id = ? AND is_current = TRUE
        ''', (user_id,))
        
        # Insert new assessment
        cursor.execute('''
            INSERT INTO risk_assessment_history (
                user_id, risk_score, risk_tolerance, assessment_method,
                questionnaire_responses, key_factors, recommended_allocation,
                assessor_notes, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE)
        ''', (
            user_id,
            assessment_data.get('risk_score', 50),
            assessment_data.get('risk_tolerance', 'moderate'),
            assessment_data.get('assessment_method', 'questionnaire'),
            json.dumps(assessment_data.get('questionnaire_responses', {})),
            json.dumps(assessment_data.get('key_factors', [])),
            json.dumps(assessment_data.get('recommended_allocation', {})),
            assessment_data.get('assessor_notes', '')
        ))
        
        # Update the user profile with the new risk assessment date
        cursor.execute('''
            UPDATE user_investment_profiles 
            SET last_risk_assessment_date = CURRENT_TIMESTAMP,
                risk_tolerance = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (assessment_data.get('risk_tolerance', 'moderate'), user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully stored risk assessment for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing risk assessment for user {user_id}: {str(e)}")
        return False

def get_current_risk_assessment(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current risk assessment for a user
    Args:
        user_id: User identifier
    Returns:
        Dictionary with assessment data or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, assessment_date, risk_score, risk_tolerance, assessment_method,
                   questionnaire_responses, key_factors, recommended_allocation,
                   assessor_notes, created_at
            FROM risk_assessment_history 
            WHERE user_id = ? AND is_current = TRUE
            ORDER BY assessment_date DESC
            LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "assessment_date": result[1],
                "risk_score": result[2],
                "risk_tolerance": result[3],
                "assessment_method": result[4],
                "questionnaire_responses": json.loads(result[5]) if result[5] else {},
                "key_factors": json.loads(result[6]) if result[6] else [],
                "recommended_allocation": json.loads(result[7]) if result[7] else {},
                "assessor_notes": result[8],
                "created_at": result[9]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving current risk assessment for user {user_id}: {str(e)}")
        return None

def calculate_profile_completeness(profile_data: Dict[str, Any]) -> int:
    """
    Calculate profile completeness score based on filled fields
    Args:
        profile_data: Profile data dictionary
    Returns:
        Completeness score (0-100)
    """
    required_fields = [
        'risk_tolerance', 'investment_timeline', 'max_position_size',
        'trading_frequency', 'stop_loss_preference', 'take_profit_preference'
    ]
    
    optional_fields = [
        'investment_goals', 'preferred_sectors', 'avoided_sectors',
        'auto_trading_enabled', 'rebalancing_frequency', 'dividend_preference',
        'volatility_tolerance', 'market_timing_preference'
    ]
    
    score = 0
    
    # Required fields (60% of score)
    required_filled = sum(1 for field in required_fields if profile_data.get(field))
    score += (required_filled / len(required_fields)) * 60
    
    # Optional fields (40% of score)
    optional_filled = sum(1 for field in optional_fields if profile_data.get(field))
    score += (optional_filled / len(optional_fields)) * 40
    
    return min(100, int(score))

def update_goal_progress(goal_id: int, user_id: str, current_amount: float) -> bool:
    """
    Update the progress of an investment goal
    Args:
        goal_id: Goal identifier
        user_id: User identifier for security
        current_amount: Current amount achieved
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Get target amount to calculate progress
        cursor.execute('''
            SELECT target_amount FROM investment_goals 
            WHERE id = ? AND user_id = ?
        ''', (goal_id, user_id))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        target_amount = result[0]
        progress_percentage = min(100, (current_amount / target_amount * 100)) if target_amount > 0 else 0
        
        # Update goal status based on progress
        goal_status = 'completed' if progress_percentage >= 100 else 'active'
        
        cursor.execute('''
            UPDATE investment_goals 
            SET current_amount = ?, 
                progress_percentage = ?,
                goal_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (current_amount, progress_percentage, goal_status, goal_id, user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated goal {goal_id} progress to {progress_percentage:.1f}% for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating goal progress: {str(e)}")
        return False

def get_profile_based_recommendations_context(user_id: str) -> Dict[str, Any]:
    """
    Get user profile context for AI recommendations
    Args:
        user_id: User identifier
    Returns:
        Dictionary with profile context for AI prompts
    """
    try:
        profile = get_user_investment_profile(user_id)
        goals = get_user_investment_goals(user_id, status='active')
        risk_assessment = get_current_risk_assessment(user_id)
        
        if not profile:
            return {
                "risk_tolerance": "moderate",
                "investment_timeline": "medium_term",
                "max_position_size": 15.0,
                "profile_available": False
            }
        
        context = {
            "profile_available": True,
            "risk_tolerance": profile["risk_tolerance"],
            "investment_timeline": profile["investment_timeline"],
            "preferred_sectors": profile["preferred_sectors"],
            "avoided_sectors": profile["avoided_sectors"],
            "max_position_size": profile["max_position_size"],
            "min_position_size": profile["min_position_size"],
            "trading_frequency": profile["trading_frequency"],
            "auto_trading_enabled": profile["auto_trading_enabled"],
            "stop_loss_preference": profile["stop_loss_preference"],
            "take_profit_preference": profile["take_profit_preference"],
            "volatility_tolerance": profile["volatility_tolerance"],
            "market_timing_preference": profile["market_timing_preference"],
            "profile_completeness": profile["profile_completeness_score"],
            "active_goals_count": len(goals),
            "primary_goal": goals[0] if goals else None,
            "risk_score": risk_assessment["risk_score"] if risk_assessment else 50
        }
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting profile context for user {user_id}: {str(e)}")
        return {
            "risk_tolerance": "moderate",
            "investment_timeline": "medium_term",
            "max_position_size": 15.0,
            "profile_available": False
        }

# ========================================
# Market Context Management Functions
# ========================================

def store_market_context(
    date: str,
    market_data: Dict[str, Any]
) -> bool:
    """
    Store daily market context data
    Args:
        date: Date in YYYY-MM-DD format
        market_data: Dictionary containing market information
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO market_context (
                date, nifty_value, nifty_change, nifty_change_percent, nifty_trend,
                sensex_value, sensex_change, sensex_change_percent, market_sentiment,
                volatility_index, market_volume, advances_count, declines_count, unchanged_count,
                sector_performance, top_gainers, top_losers, key_events, economic_indicators,
                global_market_impact, currency_rates, commodity_prices, bond_yields,
                market_breadth_ratio, fear_greed_index, analyst_sentiment, news_sentiment_score,
                trading_session, market_status, data_source, data_quality_score, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            date,
            market_data.get('nifty_value'),
            market_data.get('nifty_change'),
            market_data.get('nifty_change_percent'),
            market_data.get('nifty_trend', 'neutral'),
            market_data.get('sensex_value'),
            market_data.get('sensex_change'),
            market_data.get('sensex_change_percent'),
            market_data.get('market_sentiment', 'neutral'),
            market_data.get('volatility_index'),
            market_data.get('market_volume'),
            market_data.get('advances_count'),
            market_data.get('declines_count'),
            market_data.get('unchanged_count'),
            json.dumps(market_data.get('sector_performance', {})),
            json.dumps(market_data.get('top_gainers', [])),
            json.dumps(market_data.get('top_losers', [])),
            json.dumps(market_data.get('key_events', [])),
            json.dumps(market_data.get('economic_indicators', {})),
            json.dumps(market_data.get('global_market_impact', {})),
            json.dumps(market_data.get('currency_rates', {})),
            json.dumps(market_data.get('commodity_prices', {})),
            json.dumps(market_data.get('bond_yields', {})),
            market_data.get('market_breadth_ratio'),
            market_data.get('fear_greed_index'),
            market_data.get('analyst_sentiment'),
            market_data.get('news_sentiment_score'),
            market_data.get('trading_session', 'regular'),
            market_data.get('market_status', 'open'),
            market_data.get('data_source', 'manual'),
            market_data.get('data_quality_score', 80)
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored market context for date: {date}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing market context for date {date}: {str(e)}")
        return False

def get_market_context(
    date: Optional[str] = None,
    days_back: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Retrieve market context data
    Args:
        date: Specific date in YYYY-MM-DD format (if None, gets latest)
        days_back: Number of days to look back if no specific date
    Returns:
        Dictionary with market context or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT * FROM market_context WHERE date = ?
            ''', (date,))
        else:
            cursor.execute('''
                SELECT * FROM market_context 
                ORDER BY date DESC 
                LIMIT ?
            ''', (days_back,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "date": result[1],
                "nifty_value": result[2],
                "nifty_change": result[3],
                "nifty_change_percent": result[4],
                "nifty_trend": result[5],
                "sensex_value": result[6],
                "sensex_change": result[7],
                "sensex_change_percent": result[8],
                "market_sentiment": result[9],
                "volatility_index": result[10],
                "market_volume": result[11],
                "advances_count": result[12],
                "declines_count": result[13],
                "unchanged_count": result[14],
                "sector_performance": json.loads(result[15]) if result[15] else {},
                "top_gainers": json.loads(result[16]) if result[16] else [],
                "top_losers": json.loads(result[17]) if result[17] else [],
                "key_events": json.loads(result[18]) if result[18] else [],
                "economic_indicators": json.loads(result[19]) if result[19] else {},
                "global_market_impact": json.loads(result[20]) if result[20] else {},
                "currency_rates": json.loads(result[21]) if result[21] else {},
                "commodity_prices": json.loads(result[22]) if result[22] else {},
                "bond_yields": json.loads(result[23]) if result[23] else {},
                "market_breadth_ratio": result[24],
                "fear_greed_index": result[25],
                "analyst_sentiment": result[26],
                "news_sentiment_score": result[27],
                "trading_session": result[28],
                "market_status": result[29],
                "data_source": result[30],
                "data_quality_score": result[31],
                "created_at": result[32],
                "updated_at": result[33]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving market context: {str(e)}")
        return None

def store_sector_performance(
    date: str,
    sector_data: List[Dict[str, Any]]
) -> bool:
    """
    Store sector performance data for a specific date
    Args:
        date: Date in YYYY-MM-DD format
        sector_data: List of sector performance dictionaries
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Delete existing data for the date to avoid duplicates
        cursor.execute('DELETE FROM sector_performance WHERE date = ?', (date,))
        
        for sector in sector_data:
            cursor.execute('''
                INSERT INTO sector_performance (
                    date, sector_name, sector_index_value, sector_change, sector_change_percent,
                    sector_trend, market_cap, volume, pe_ratio, pb_ratio, dividend_yield,
                    top_performers, worst_performers, sector_news, analyst_rating, risk_level,
                    growth_potential, correlation_with_nifty, volatility_30d, momentum_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                sector.get('sector_name', ''),
                sector.get('sector_index_value'),
                sector.get('sector_change'),
                sector.get('sector_change_percent'),
                sector.get('sector_trend', 'neutral'),
                sector.get('market_cap'),
                sector.get('volume'),
                sector.get('pe_ratio'),
                sector.get('pb_ratio'),
                sector.get('dividend_yield'),
                json.dumps(sector.get('top_performers', [])),
                json.dumps(sector.get('worst_performers', [])),
                json.dumps(sector.get('sector_news', [])),
                sector.get('analyst_rating', 'hold'),
                sector.get('risk_level', 'medium'),
                sector.get('growth_potential', 'medium'),
                sector.get('correlation_with_nifty'),
                sector.get('volatility_30d'),
                sector.get('momentum_score', 50)
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored sector performance for {len(sector_data)} sectors on {date}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing sector performance for date {date}: {str(e)}")
        return False

def get_sector_performance(
    date: Optional[str] = None,
    sector_name: Optional[str] = None,
    days_back: int = 1
) -> List[Dict[str, Any]]:
    """
    Retrieve sector performance data
    Args:
        date: Specific date in YYYY-MM-DD format
        sector_name: Specific sector name filter
        days_back: Number of days to look back
    Returns:
        List of sector performance dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT date, sector_name, sector_index_value, sector_change, sector_change_percent,
                   sector_trend, market_cap, volume, pe_ratio, pb_ratio, dividend_yield,
                   top_performers, worst_performers, sector_news, analyst_rating, risk_level,
                   growth_potential, correlation_with_nifty, volatility_30d, momentum_score
            FROM sector_performance
        '''
        params = []
        
        conditions = []
        if date:
            conditions.append('date = ?')
            params.append(date)
        else:
            conditions.append('date >= date("now", "-{} days")'.format(days_back))
        
        if sector_name:
            conditions.append('sector_name = ?')
            params.append(sector_name)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += ' ORDER BY date DESC, sector_change_percent DESC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        sectors = []
        for result in results:
            sectors.append({
                "date": result[0],
                "sector_name": result[1],
                "sector_index_value": result[2],
                "sector_change": result[3],
                "sector_change_percent": result[4],
                "sector_trend": result[5],
                "market_cap": result[6],
                "volume": result[7],
                "pe_ratio": result[8],
                "pb_ratio": result[9],
                "dividend_yield": result[10],
                "top_performers": json.loads(result[11]) if result[11] else [],
                "worst_performers": json.loads(result[12]) if result[12] else [],
                "sector_news": json.loads(result[13]) if result[13] else [],
                "analyst_rating": result[14],
                "risk_level": result[15],
                "growth_potential": result[16],
                "correlation_with_nifty": result[17],
                "volatility_30d": result[18],
                "momentum_score": result[19]
            })
        
        return sectors
        
    except Exception as e:
        logger.error(f"Error retrieving sector performance: {str(e)}")
        return []

def store_stock_market_data(
    date: str,
    stock_data: List[Dict[str, Any]]
) -> bool:
    """
    Store stock market data for multiple stocks
    Args:
        date: Date in YYYY-MM-DD format
        stock_data: List of stock data dictionaries
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        for stock in stock_data:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_market_data (
                    date, symbol, open_price, high_price, low_price, close_price, volume,
                    price_change, price_change_percent, market_cap, pe_ratio, pb_ratio,
                    dividend_yield, beta, volatility_30d, rsi, moving_avg_50d, moving_avg_200d,
                    support_level, resistance_level, analyst_target_price, analyst_rating,
                    news_sentiment_score, social_sentiment_score, institutional_holding_percent,
                    promoter_holding_percent, recent_news, earnings_date, dividend_date,
                    stock_events, sector, industry
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                stock.get('symbol', ''),
                stock.get('open_price'),
                stock.get('high_price'),
                stock.get('low_price'),
                stock.get('close_price'),
                stock.get('volume'),
                stock.get('price_change'),
                stock.get('price_change_percent'),
                stock.get('market_cap'),
                stock.get('pe_ratio'),
                stock.get('pb_ratio'),
                stock.get('dividend_yield'),
                stock.get('beta'),
                stock.get('volatility_30d'),
                stock.get('rsi'),
                stock.get('moving_avg_50d'),
                stock.get('moving_avg_200d'),
                stock.get('support_level'),
                stock.get('resistance_level'),
                stock.get('analyst_target_price'),
                stock.get('analyst_rating', 'hold'),
                stock.get('news_sentiment_score'),
                stock.get('social_sentiment_score'),
                stock.get('institutional_holding_percent'),
                stock.get('promoter_holding_percent'),
                json.dumps(stock.get('recent_news', [])),
                stock.get('earnings_date'),
                stock.get('dividend_date'),
                json.dumps(stock.get('stock_events', [])),
                stock.get('sector', ''),
                stock.get('industry', '')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored market data for {len(stock_data)} stocks on {date}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing stock market data for date {date}: {str(e)}")
        return False

def get_stock_market_data(
    symbol: str,
    date: Optional[str] = None,
    days_back: int = 30
) -> List[Dict[str, Any]]:
    """
    Retrieve stock market data for a specific symbol
    Args:
        symbol: Stock symbol
        date: Specific date (if None, gets recent data)
        days_back: Number of days to look back
    Returns:
        List of stock data dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT * FROM stock_market_data 
                WHERE symbol = ? AND date = ?
            ''', (symbol, date))
        else:
            cursor.execute('''
                SELECT * FROM stock_market_data 
                WHERE symbol = ? AND date >= date("now", "-{} days")
                ORDER BY date DESC
            '''.format(days_back), (symbol,))
        
        results = cursor.fetchall()
        conn.close()
        
        stock_data = []
        for result in results:
            stock_data.append({
                "date": result[1],
                "symbol": result[2],
                "open_price": result[3],
                "high_price": result[4],
                "low_price": result[5],
                "close_price": result[6],
                "volume": result[7],
                "price_change": result[8],
                "price_change_percent": result[9],
                "market_cap": result[10],
                "pe_ratio": result[11],
                "pb_ratio": result[12],
                "dividend_yield": result[13],
                "beta": result[14],
                "volatility_30d": result[15],
                "rsi": result[16],
                "moving_avg_50d": result[17],
                "moving_avg_200d": result[18],
                "support_level": result[19],
                "resistance_level": result[20],
                "analyst_target_price": result[21],
                "analyst_rating": result[22],
                "news_sentiment_score": result[23],
                "social_sentiment_score": result[24],
                "institutional_holding_percent": result[25],
                "promoter_holding_percent": result[26],
                "recent_news": json.loads(result[27]) if result[27] else [],
                "earnings_date": result[28],
                "dividend_date": result[29],
                "stock_events": json.loads(result[30]) if result[30] else [],
                "sector": result[31],
                "industry": result[32],
                "created_at": result[33]
            })
        
        return stock_data
        
    except Exception as e:
        logger.error(f"Error retrieving stock market data for {symbol}: {str(e)}")
        return []

def store_market_event(
    event_data: Dict[str, Any]
) -> Optional[int]:
    """
    Store a market event
    Args:
        event_data: Dictionary containing event information
    Returns:
        Event ID if successful, None otherwise
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO market_events (
                event_date, event_type, event_title, event_description, impact_level,
                affected_sectors, affected_stocks, market_reaction, price_impact_estimate,
                duration_estimate, confidence_score, data_source, analyst_notes, follow_up_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_data.get('event_date'),
            event_data.get('event_type', 'economic'),
            event_data.get('event_title', ''),
            event_data.get('event_description', ''),
            event_data.get('impact_level', 'medium'),
            json.dumps(event_data.get('affected_sectors', [])),
            json.dumps(event_data.get('affected_stocks', [])),
            event_data.get('market_reaction', ''),
            event_data.get('price_impact_estimate'),
            event_data.get('duration_estimate', 'short_term'),
            event_data.get('confidence_score', 70),
            event_data.get('data_source', 'manual'),
            event_data.get('analyst_notes', ''),
            event_data.get('follow_up_required', False)
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully stored market event {event_id}: {event_data.get('event_title')}")
        return event_id
        
    except Exception as e:
        logger.error(f"Error storing market event: {str(e)}")
        return None

def get_market_events(
    days_back: int = 7,
    impact_level: Optional[str] = None,
    event_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve recent market events
    Args:
        days_back: Number of days to look back
        impact_level: Filter by impact level
        event_type: Filter by event type
    Returns:
        List of market event dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, event_date, event_type, event_title, event_description, impact_level,
                   affected_sectors, affected_stocks, market_reaction, price_impact_estimate,
                   duration_estimate, confidence_score, data_source, analyst_notes,
                   follow_up_required, created_at, updated_at
            FROM market_events 
            WHERE event_date >= date("now", "-{} days")
        '''.format(days_back)
        
        params = []
        if impact_level:
            query += ' AND impact_level = ?'
            params.append(impact_level)
        
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY event_date DESC, impact_level DESC'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        events = []
        for result in results:
            events.append({
                "id": result[0],
                "event_date": result[1],
                "event_type": result[2],
                "event_title": result[3],
                "event_description": result[4],
                "impact_level": result[5],
                "affected_sectors": json.loads(result[6]) if result[6] else [],
                "affected_stocks": json.loads(result[7]) if result[7] else [],
                "market_reaction": result[8],
                "price_impact_estimate": result[9],
                "duration_estimate": result[10],
                "confidence_score": result[11],
                "data_source": result[12],
                "analyst_notes": result[13],
                "follow_up_required": bool(result[14]),
                "created_at": result[15],
                "updated_at": result[16]
            })
        
        return events
        
    except Exception as e:
        logger.error(f"Error retrieving market events: {str(e)}")
        return []

def get_market_context_for_ai_prompt(days_back: int = 3) -> Dict[str, Any]:
    """
    Get market context formatted for AI prompts
    Args:
        days_back: Number of days of context to include
    Returns:
        Dictionary with market context for AI analysis
    """
    try:
        # Get recent market data
        market_context = get_market_context(days_back=days_back)
        sector_performance = get_sector_performance(days_back=days_back)
        recent_events = get_market_events(days_back=days_back, impact_level='high')
        
        if not market_context:
            return {
                "market_available": False,
                "message": "Market context data not available"
            }
        
        # Format for AI prompt
        context = {
            "market_available": True,
            "current_date": market_context["date"],
            "nifty_trend": market_context["nifty_trend"],
            "nifty_change_percent": market_context["nifty_change_percent"],
            "market_sentiment": market_context["market_sentiment"],
            "volatility_index": market_context["volatility_index"],
            "fear_greed_index": market_context["fear_greed_index"],
            "market_breadth": {
                "advances": market_context["advances_count"],
                "declines": market_context["declines_count"],
                "ratio": market_context["market_breadth_ratio"]
            },
            "top_performing_sectors": [
                s for s in sector_performance 
                if s["sector_change_percent"] and s["sector_change_percent"] > 1
            ][:5],
            "worst_performing_sectors": [
                s for s in sector_performance 
                if s["sector_change_percent"] and s["sector_change_percent"] < -1
            ][:5],
            "recent_high_impact_events": recent_events[:3],
            "trading_session": market_context["trading_session"],
            "data_quality": market_context["data_quality_score"]
        }
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting market context for AI prompt: {str(e)}")
        return {
            "market_available": False,
            "message": f"Error retrieving market context: {str(e)}"
        }

# ========================================
# Enhanced Database Integration Functions
# ========================================

def get_comprehensive_user_context(user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive user context for enhanced AI analysis
    Args:
        user_id: User identifier
    Returns:
        Dictionary with complete user context
    """
    try:
        # Get user profile
        profile = get_user_investment_profile(user_id)
        
        # Get active goals
        goals = get_user_investment_goals(user_id, status='active')
        
        # Get current risk assessment
        risk_assessment = get_current_risk_assessment(user_id)
        
        # Get recent recommendations
        recent_recommendations = get_enhanced_recommendations(user_id, limit=10)
        
        # Get recommendation performance
        performance = get_recommendation_performance(user_id, days=30)
        
        # Get market context for AI
        market_context = get_market_context_for_ai_prompt(days_back=3)
        
        return {
            "user_id": user_id,
            "profile": profile,
            "active_goals": goals,
            "risk_assessment": risk_assessment,
            "recent_recommendations": recent_recommendations,
            "performance_metrics": performance,
            "market_context": market_context,
            "context_completeness": calculate_context_completeness(profile, goals, risk_assessment),
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive user context for {user_id}: {str(e)}")
        return {
            "user_id": user_id,
            "profile": None,
            "active_goals": [],
            "risk_assessment": None,
            "recent_recommendations": [],
            "performance_metrics": {"total_count": 0},
            "market_context": {"market_available": False},
            "context_completeness": 0,
            "error": str(e)
        }

def calculate_context_completeness(
    profile: Optional[Dict[str, Any]], 
    goals: List[Dict[str, Any]], 
    risk_assessment: Optional[Dict[str, Any]]
) -> int:
    """
    Calculate completeness of user context for AI analysis
    Args:
        profile: User investment profile
        goals: User investment goals
        risk_assessment: Current risk assessment
    Returns:
        Completeness score (0-100)
    """
    score = 0
    
    # Profile completeness (50% of total)
    if profile:
        score += (profile.get('profile_completeness_score', 0) * 0.5)
    
    # Goals completeness (25% of total)
    if goals:
        goal_score = min(100, len(goals) * 25)  # Up to 4 goals for full score
        score += (goal_score * 0.25)
    
    # Risk assessment completeness (25% of total)
    if risk_assessment:
        score += 25
    
    return min(100, int(score))

def store_enhanced_analysis_session(
    user_id: str,
    analysis_data: Dict[str, Any],
    recommendations: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Store a complete enhanced analysis session
    Args:
        user_id: User identifier
        analysis_data: Complete analysis result
        recommendations: List of recommendations
    Returns:
        Analysis session ID if successful, None otherwise
    """
    try:
        analysis_id = f"enhanced_{user_id}_{int(datetime.now().timestamp())}"
        
        # Store the analysis result
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_analysis_results (
                user_id, analysis_type, symbols, input_data, analysis_result,
                provider_used, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            "enhanced_portfolio",
            None,  # Portfolio-wide analysis
            json.dumps({
                "total_holdings": len(analysis_data.get("portfolio_data", {}).get("holdings", [])),
                "total_value": analysis_data.get("portfolio_data", {}).get("total_value", 0)
            }),
            json.dumps(analysis_data),
            analysis_data.get("provider_used", "unknown"),
            analysis_data.get("confidence_score", 0.7)
        ))
        
        conn.commit()
        conn.close()
        
        # Store individual recommendations
        if recommendations:
            success = store_enhanced_recommendations(user_id, analysis_id, recommendations)
            if not success:
                logger.warning(f"Failed to store recommendations for analysis {analysis_id}")
        
        logger.info(f"Stored enhanced analysis session {analysis_id} with {len(recommendations)} recommendations")
        return analysis_id
        
    except Exception as e:
        logger.error(f"Error storing enhanced analysis session: {str(e)}")
        return None

def get_portfolio_analysis_history(
    user_id: str,
    days_back: int = 30,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get portfolio analysis history for a user
    Args:
        user_id: User identifier
        days_back: Number of days to look back
        limit: Maximum number of analyses to return
    Returns:
        List of analysis history dictionaries
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, analysis_type, input_data, analysis_result, provider_used,
                   confidence_score, created_at
            FROM ai_analysis_results 
            WHERE user_id = ? 
            AND analysis_type IN ('enhanced_portfolio', 'portfolio')
            AND created_at >= datetime('now', '-{} days')
            ORDER BY created_at DESC
            LIMIT ?
        '''.format(days_back), (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        history = []
        for result in results:
            try:
                analysis_result = json.loads(result[3])
                input_data = json.loads(result[2]) if result[2] else {}
                
                history.append({
                    "id": result[0],
                    "analysis_type": result[1],
                    "input_data": input_data,
                    "analysis_result": analysis_result,
                    "provider_used": result[4],
                    "confidence_score": result[5],
                    "created_at": result[6],
                    "recommendations_count": len(analysis_result.get("stock_recommendations", [])),
                    "portfolio_score": analysis_result.get("portfolio_health", {}).get("overall_score", 0)
                })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse analysis result for ID {result[0]}")
                continue
        
        return history
        
    except Exception as e:
        logger.error(f"Error retrieving portfolio analysis history for {user_id}: {str(e)}")
        return []

def get_recommendation_analytics(user_id: str, days_back: int = 90) -> Dict[str, Any]:
    """
    Get comprehensive recommendation analytics
    Args:
        user_id: User identifier
        days_back: Number of days to analyze
    Returns:
        Dictionary with recommendation analytics
    """
    try:
        # Get recommendations
        recommendations = get_enhanced_recommendations(user_id, limit=100)
        
        # Get performance data
        performance = get_recommendation_performance(user_id, days=days_back)
        
        # Calculate analytics
        total_recommendations = len(recommendations)
        implemented_count = len([r for r in recommendations if r["implementation_status"] == "IMPLEMENTED"])
        pending_count = len([r for r in recommendations if r["implementation_status"] == "PENDING"])
        expired_count = len([r for r in recommendations if r["implementation_status"] == "EXPIRED"])
        
        # Action type distribution
        action_distribution = {}
        for rec in recommendations:
            action = rec["action"]
            action_distribution[action] = action_distribution.get(action, 0) + 1
        
        # Priority distribution
        priority_distribution = {}
        for rec in recommendations:
            priority = rec["priority"]
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        # Sector distribution
        sector_distribution = {}
        for rec in recommendations:
            sector = rec.get("sector", "Unknown")
            sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
        
        # Average confidence by action
        confidence_by_action = {}
        for action in action_distribution.keys():
            action_recs = [r for r in recommendations if r["action"] == action]
            avg_confidence = sum(r["confidence"] for r in action_recs) / len(action_recs)
            confidence_by_action[action] = round(avg_confidence, 1)
        
        return {
            "total_recommendations": total_recommendations,
            "implementation_stats": {
                "implemented": implemented_count,
                "pending": pending_count,
                "expired": expired_count,
                "implementation_rate": (implemented_count / total_recommendations * 100) if total_recommendations > 0 else 0
            },
            "action_distribution": action_distribution,
            "priority_distribution": priority_distribution,
            "sector_distribution": sector_distribution,
            "confidence_by_action": confidence_by_action,
            "performance_metrics": performance,
            "analysis_period_days": days_back,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendation analytics for {user_id}: {str(e)}")
        return {
            "total_recommendations": 0,
            "implementation_stats": {"implemented": 0, "pending": 0, "expired": 0, "implementation_rate": 0},
            "action_distribution": {},
            "priority_distribution": {},
            "sector_distribution": {},
            "confidence_by_action": {},
            "performance_metrics": {"total_count": 0},
            "error": str(e)
        }

def cleanup_old_data(days_to_keep: int = 365) -> Dict[str, int]:
    """
    Clean up old data from enhanced analysis tables
    Args:
        days_to_keep: Number of days of data to retain
    Returns:
        Dictionary with cleanup statistics
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        cleanup_stats = {}
        
        # Clean up old analysis results
        cursor.execute('''
            DELETE FROM ai_analysis_results 
            WHERE created_at < datetime('now', '-{} days')
        '''.format(days_to_keep))
        cleanup_stats["analysis_results"] = cursor.rowcount
        
        # Clean up old recommendations (keep implemented ones longer)
        cursor.execute('''
            DELETE FROM enhanced_recommendations 
            WHERE created_at < datetime('now', '-{} days')
            AND implementation_status NOT IN ('IMPLEMENTED')
        '''.format(days_to_keep))
        cleanup_stats["recommendations"] = cursor.rowcount
        
        # Clean up old performance data
        cursor.execute('''
            DELETE FROM recommendation_performance 
            WHERE created_at < datetime('now', '-{} days')
        '''.format(days_to_keep * 2))  # Keep performance data longer
        cleanup_stats["performance_records"] = cursor.rowcount
        
        # Clean up old market context (keep 1 year)
        cursor.execute('''
            DELETE FROM market_context 
            WHERE date < date('now', '-{} days')
        '''.format(min(days_to_keep, 365)))
        cleanup_stats["market_context"] = cursor.rowcount
        
        # Clean up old stock market data
        cursor.execute('''
            DELETE FROM stock_market_data 
            WHERE date < date('now', '-{} days')
        '''.format(min(days_to_keep, 180)))  # Keep 6 months of stock data
        cleanup_stats["stock_data"] = cursor.rowcount
        
        # Clean up old sector performance
        cursor.execute('''
            DELETE FROM sector_performance 
            WHERE date < date('now', '-{} days')
        '''.format(min(days_to_keep, 180)))
        cleanup_stats["sector_performance"] = cursor.rowcount
        
        # Clean up old market events
        cursor.execute('''
            DELETE FROM market_events 
            WHERE event_date < date('now', '-{} days')
            AND follow_up_required = FALSE
        '''.format(days_to_keep))
        cleanup_stats["market_events"] = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        total_cleaned = sum(cleanup_stats.values())
        logger.info(f"Cleaned up {total_cleaned} old records from enhanced analysis tables")
        
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Error during data cleanup: {str(e)}")
        return {"error": str(e)}

def get_database_health_enhanced() -> Dict[str, Any]:
    """
    Get enhanced database health information including new tables
    Returns:
        Dictionary with enhanced database health metrics
    """
    try:
        base_health = check_database_health()
        
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        # Check enhanced tables
        enhanced_tables = [
            "enhanced_recommendations",
            "recommendation_performance", 
            "user_investment_profiles",
            "investment_goals",
            "risk_assessment_history",
            "market_context",
            "sector_performance",
            "stock_market_data",
            "market_events"
        ]
        
        enhanced_stats = {}
        for table in enhanced_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                enhanced_stats[table] = count
            except sqlite3.Error:
                enhanced_stats[table] = "table_not_found"
        
        # Get recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM enhanced_recommendations 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        recent_recommendations = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM ai_analysis_results 
            WHERE created_at >= datetime('now', '-7 days')
            AND analysis_type = 'enhanced_portfolio'
        ''')
        recent_analyses = cursor.fetchone()[0]
        
        conn.close()
        
        # Combine with base health
        enhanced_health = base_health.copy()
        enhanced_health.update({
            "enhanced_tables": enhanced_stats,
            "recent_activity": {
                "recommendations_7d": recent_recommendations,
                "analyses_7d": recent_analyses
            },
            "feature_status": "enhanced_ai_analysis_active"
        })
        
        return enhanced_health
        
    except Exception as e:
        logger.error(f"Error getting enhanced database health: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "feature_status": "enhanced_ai_analysis_error"
        }

# Export key functions for easy import
__all__ = [
    # Core database functions
    'init_database',
    'get_db_connection',
    
    # Enhanced recommendations
    'store_enhanced_recommendations',
    'get_enhanced_recommendations', 
    'update_recommendation_status',
    'get_recommendation_performance',
    'get_recommendations_by_ids',
    
    # User investment profiles
    'store_user_investment_profile',
    'get_user_investment_profile',
    'store_investment_goal',
    'get_user_investment_goals',
    'store_risk_assessment',
    'get_current_risk_assessment',
    'get_profile_based_recommendations_context',
    
    # Market context
    'store_market_context',
    'get_market_context',
    'store_sector_performance',
    'get_sector_performance',
    'store_stock_market_data',
    'get_stock_market_data',
    'store_market_event',
    'get_market_events',
    'get_market_context_for_ai_prompt',
    
    # Integration functions
    'get_comprehensive_user_context',
    'store_enhanced_analysis_session',
    'get_portfolio_analysis_history',
    'get_recommendation_analytics',
    'cleanup_old_data',
    'get_database_health_enhanced'
]