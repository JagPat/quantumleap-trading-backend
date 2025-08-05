#!/usr/bin/env python3
"""
Database Initialization Script
This script initializes the database with test data for production testing
"""

import sqlite3
import hashlib
import os
from datetime import datetime

def get_database_path():
    """Find the correct database file"""
    possible_paths = [
        "trading_app.db",
        "quantumleap.db", 
        "production_trading.db",
        "app.db",
        "database.db"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Default to trading_app.db if none found
    return "trading_app.db"

def create_test_user(db_path):
    """Create test user in the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📁 Using database: {db_path}")
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            print("❌ Users table not found")
            return False
        
        # Check if test user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", ('test@quantumleap.com',))
        if cursor.fetchone():
            print("✅ Test user already exists")
            return True
        
        # Create test user
        cursor.execute("""
            INSERT INTO users (user_id, api_key, api_secret, user_name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'test-user-001',
            'test_api_key_001',
            'test_api_secret_001',
            'Test User',
            'test@quantumleap.com',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        print("✅ Test user created in users table")
        
        # Create auth_users table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                user_id TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create auth record
        password_hash = hashlib.sha256('test123'.encode()).hexdigest()
        cursor.execute("""
            INSERT OR REPLACE INTO auth_users (email, password_hash, user_id, is_active)
            VALUES (?, ?, ?, ?)
        """, ('test@quantumleap.com', password_hash, 'test-user-001', True))
        
        print("✅ Auth record created")
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_test_user(db_path):
    """Verify the test user was created correctly"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check main user record
        cursor.execute("SELECT user_id, email FROM users WHERE email = ?", ('test@quantumleap.com',))
        user = cursor.fetchone()
        
        if user:
            print(f"✅ User verified: {user[1]} (ID: {user[0]})")
        else:
            print("❌ User not found in users table")
            return False
        
        # Check auth record
        cursor.execute("SELECT email, is_active FROM auth_users WHERE email = ?", ('test@quantumleap.com',))
        auth = cursor.fetchone()
        
        if auth:
            print(f"✅ Auth verified: {auth[0]} (Active: {auth[1]})")
        else:
            print("❌ Auth record not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    print("🚀 Initializing Database with Test Data")
    print("=" * 50)
    
    # Find database
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}, creating new one...")
    
    # Create test user
    if create_test_user(db_path):
        if verify_test_user(db_path):
            print("\n🎉 Database initialization successful!")
            print("\n📋 Test Credentials:")
            print("   Email: test@quantumleap.com")
            print("   Password: test123")
            print("\n🧪 Ready for testing!")
        else:
            print("\n❌ Verification failed")
    else:
        print("\n❌ Database initialization failed")

if __name__ == "__main__":
    main()