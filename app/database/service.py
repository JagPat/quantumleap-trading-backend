"""
Database service - handles all database operations
"""
import sqlite3
import logging
import json
from typing import Optional, Dict, Any
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
    # Create ai_user_preferences table for storing AI API keys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            openai_api_key TEXT,
            claude_api_key TEXT,
            gemini_api_key TEXT,
            preferred_provider TEXT DEFAULT 'auto',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    preferred_provider: str = "auto"
) -> bool:
    """
    Store AI preferences for a user
    Args:
        user_id: User identifier
        openai_api_key: OpenAI API key (encrypted)
        claude_api_key: Claude API key (encrypted)
        gemini_api_key: Gemini API key (encrypted)
        preferred_provider: Preferred AI provider
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
        
        cursor.execute('''
            INSERT OR REPLACE INTO ai_user_preferences 
            (user_id, openai_api_key, claude_api_key, gemini_api_key, preferred_provider, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, encrypted_openai, encrypted_claude, encrypted_gemini, preferred_provider))
        
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
            SELECT openai_api_key, claude_api_key, gemini_api_key, preferred_provider, created_at, updated_at
            FROM ai_user_preferences WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Decrypt API keys if they exist
            openai_key = decrypt_data(result[0]) if result[0] else None
            claude_key = decrypt_data(result[1]) if result[1] else None
            gemini_key = decrypt_data(result[2]) if result[2] else None
            
            return {
                "openai_api_key": openai_key,
                "claude_api_key": claude_key,
                "gemini_api_key": gemini_key,
                "preferred_provider": result[3],
                "created_at": result[4],
                "updated_at": result[5]
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
