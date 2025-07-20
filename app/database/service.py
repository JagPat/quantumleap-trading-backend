"""
Database service - handles all database operations
"""
import sqlite3
import logging
import json
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize cipher suite for encryption
cipher_suite = Fernet(settings.get_encryption_key())

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
    
    conn.commit()
    conn.close()

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