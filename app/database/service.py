"""
Database service - handles all database operations
"""
import sqlite3
import logging
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
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
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
    
    conn.commit()
    conn.close()


def store_portfolio_snapshot(user_id: str, timestamp: str, holdings: str, positions: str) -> bool:
    """
    Stores a snapshot of the user's portfolio.
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO portfolio_snapshots (user_id, timestamp, holdings, positions) VALUES (?, ?, ?, ?)",
            (user_id, timestamp, holdings, positions)
        )
        conn.commit()
        logger.info(f"Successfully stored portfolio snapshot for user {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error storing portfolio snapshot for user {user_id}: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_latest_portfolio_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent portfolio snapshot for a given user.
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, holdings, positions FROM portfolio_snapshots WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            return {"timestamp": result[0], "holdings": result[1], "positions": result[2]}
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving latest portfolio snapshot for user {user_id}: {e}")
        return None
    finally:
        if conn:
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
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        
        # Encrypt sensitive data
        encrypted_api_secret = encrypt_data(api_secret)
        encrypted_access_token = encrypt_data(access_token)
        
        # Insert or update user credentials
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
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, api_key, api_secret, access_token, user_name, email, last_successful_connection, token_expiry, last_error
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "user_id": result[0],
                "api_key": result[1],
                "api_secret": decrypt_data(result[2]),
                "access_token": decrypt_data(result[3]),
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
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        rows_affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"Successfully deleted credentials for user: {user_id}")
            return True
        else:
            logger.warning(f"No credentials found to delete for user: {user_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error deleting user credentials: {str(e)}")
        return False


def get_user_credentials_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user credentials from database by email
    
    Args:
        email: User email address
        
    Returns:
        Dict with user credentials or None if not found
    """
    try:
        conn = sqlite3.connect(settings.database_path)
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, api_key, api_secret, access_token, user_name, email
            FROM users WHERE email = ?
        ''', (email,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "user_id": result[0],
                "api_key": result[1],
                "api_secret": decrypt_data(result[2]),
                "access_token": decrypt_data(result[3]),
                "user_name": result[4],
                "email": result[5]
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving user credentials by email: {str(e)}")
        return None


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
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
        
    except Exception as e:
        logger.error(f"Error checking if user exists: {str(e)}")
def check_database_health() -> dict:
    """
    Comprehensive database health check
    """
    health_status = {
        "database_path": settings.database_path,
        "connection": False,
        "tables": [],
        "portfolio_snapshots_exists": False,
        "users_exists": False,
        "portfolio_snapshots_columns": [],
        "users_columns": [],
        "portfolio_snapshots_count": 0,
        "users_count": 0,
        "errors": []
    }
    
    try:
        conn = sqlite3.connect(settings.database_path)
        logger.info(f"DB: Database connection established")
        cursor = conn.cursor()
        logger.info(f"DB: Cursor created")
        
        # Check if portfolio_snapshots table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type="table" AND name="portfolio_snapshots"")
        table_exists = cursor.fetchone()
        logger.info(f"DB: portfolio_snapshots table exists: {table_exists is not None}")
        
        if not table_exists:
            logger.error(f"DB: portfolio_snapshots table does not exist!")
            logger.info(f"DB: Available tables:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type="table"")
            tables = cursor.fetchall()
            for table in tables:
                logger.info(f"DB: - {table[0]}")
            conn.close()
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(portfolio_snapshots)")
        columns = cursor.fetchall()
        logger.info(f"DB: portfolio_snapshots table columns: {[col[1] for col in columns]}")
        
        # Check if we can write to the database
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        count = cursor.fetchone()[0]
        logger.info(f"DB: Current portfolio_snapshots count: {count}")
        health_status["connection"] = True
        cursor = conn.cursor()
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
        tables = cursor.fetchall()
        health_status["tables"] = [table[0] for table in tables]
        
        # Check portfolio_snapshots table
        if "portfolio_snapshots" in health_status["tables"]:
            health_status["portfolio_snapshots_exists"] = True
            
            # Get column info
            cursor.execute("PRAGMA table_info(portfolio_snapshots)")
            columns = cursor.fetchall()
            health_status["portfolio_snapshots_columns"] = [col[1] for col in columns]
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
            count = cursor.fetchone()[0]
            health_status["portfolio_snapshots_count"] = count
        
        # Check users table
        if "users" in health_status["tables"]:
            health_status["users_exists"] = True
            
            # Get column info
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            health_status["users_columns"] = [col[1] for col in columns]
            
            # Get row count
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            health_status["users_count"] = count
        
        conn.close()
        
    except Exception as e:
        health_status["errors"].append(f"Database health check failed: {str(e)}")
        logger.error(f"Database health check error: {e}")
    
    return health_status
