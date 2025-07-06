import sqlite3
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)

DATABASE_PATH = "trading_app.db"

# Encryption key for storing sensitive data
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def store_user_credentials(user_id: str, api_key: str, api_secret: str, access_token: str, user_name: str = None, email: str = None) -> bool:
    """Store or update user credentials in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Encrypt sensitive data
        encrypted_api_key = encrypt_data(api_key)
        encrypted_api_secret = encrypt_data(api_secret)
        encrypted_access_token = encrypt_data(access_token)
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Update existing user
            cursor.execute("""
                UPDATE users 
                SET api_key = ?, api_secret = ?, access_token = ?, user_name = ?, email = ?, updated_at = ?
                WHERE user_id = ?
            """, (encrypted_api_key, encrypted_api_secret, encrypted_access_token, user_name, email, datetime.now(), user_id))
        else:
            # Insert new user
            cursor.execute("""
                INSERT INTO users (user_id, api_key, api_secret, access_token, user_name, email, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, encrypted_api_key, encrypted_api_secret, encrypted_access_token, user_name, email, datetime.now(), datetime.now()))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully stored credentials for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing user credentials: {str(e)}")
        return False

def get_user_credentials(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user credentials from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "user_id": user["user_id"],
                "api_key": decrypt_data(user["api_key"]),
                "api_secret": decrypt_data(user["api_secret"]),
                "access_token": decrypt_data(user["access_token"]) if user["access_token"] else None,
                "user_name": user["user_name"],
                "email": user["email"]
            }
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving user credentials: {str(e)}")
        return None

def update_access_token(user_id: str, access_token: str) -> bool:
    """Update access token for a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        encrypted_access_token = encrypt_data(access_token)
        cursor.execute("""
            UPDATE users 
            SET access_token = ?, updated_at = ?
            WHERE user_id = ?
        """, (encrypted_access_token, datetime.now(), user_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Successfully updated access token for user: {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating access token: {str(e)}")
        return False

def user_exists(user_id: str) -> bool:
    """Check if user exists in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return user is not None
        
    except Exception as e:
        logger.error(f"Error checking user existence: {str(e)}")
        return False 