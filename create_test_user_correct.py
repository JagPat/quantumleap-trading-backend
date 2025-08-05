#!/usr/bin/env python3

"""
Create Test User with Correct Schema
This script creates a test user in the correct database with the proper schema
"""

import sqlite3
import hashlib
import uuid
from datetime import datetime

# Database configuration
DATABASE_PATH = "trading_app.db"
TEST_USER_EMAIL = "test@quantumleap.com"
TEST_USER_PASSWORD = "test123"

def generate_user_id():
    """Generate a unique user ID"""
    return str(uuid.uuid4())

def generate_api_credentials():
    """Generate mock API credentials"""
    api_key = f"test_api_key_{uuid.uuid4().hex[:16]}"
    api_secret = f"test_api_secret_{uuid.uuid4().hex[:32]}"
    return api_key, api_secret

def create_test_user():
    """Create test user in the trading_app.db database"""
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (TEST_USER_EMAIL,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"✅ Test user {TEST_USER_EMAIL} already exists (ID: {existing_user[0]})")
            return existing_user[0]
        
        # Generate user data
        user_id = generate_user_id()
        api_key, api_secret = generate_api_credentials()
        
        # Create user
        cursor.execute("""
            INSERT INTO users (user_id, api_key, api_secret, user_name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            api_key,
            api_secret,
            "Test User",
            TEST_USER_EMAIL,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        db_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Test user created successfully!")
        print(f"   Email: {TEST_USER_EMAIL}")
        print(f"   User ID: {user_id}")
        print(f"   Database ID: {db_id}")
        print(f"   API Key: {api_key}")
        
        return db_id
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_auth_user():
    """Create a separate auth user for the authentication system"""
    try:
        # Check if there's a separate auth database or table
        # For now, we'll assume the backend uses the same user table
        print(f"ℹ️  Auth user will use the same record as the main user")
        return True
        
    except Exception as e:
        print(f"❌ Error creating auth user: {e}")
        return False

def verify_user_creation():
    """Verify the user was created correctly"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, email, user_name, created_at 
            FROM users 
            WHERE email = ?
        """, (TEST_USER_EMAIL,))
        
        user = cursor.fetchone()
        
        if user:
            print(f"\\n🔍 User verification:")
            print(f"   Database ID: {user[0]}")
            print(f"   User ID: {user[1]}")
            print(f"   Email: {user[2]}")
            print(f"   Name: {user[3]}")
            print(f"   Created: {user[4]}")
            return True
        else:
            print(f"❌ User {TEST_USER_EMAIL} not found in database")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying user: {e}")
        return False
    finally:
        if conn:
            conn.close()

def create_backend_auth_record():
    """Create authentication record for the backend"""
    print(f"\\n🔐 Creating backend authentication record...")
    
    # The backend might need a separate authentication mechanism
    # For now, we'll create a simple auth record that maps email to user_id
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if there's an auth table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_users';")
        auth_table_exists = cursor.fetchone()
        
        if not auth_table_exists:
            # Create auth table if it doesn't exist
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
            print(f"   Created auth_users table")
        
        # Hash the password (simple SHA256 for testing)
        password_hash = hashlib.sha256(TEST_USER_PASSWORD.encode()).hexdigest()
        
        # Get the user_id from the main users table
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (TEST_USER_EMAIL,))
        user_record = cursor.fetchone()
        
        if not user_record:
            print(f"❌ Main user record not found")
            return False
        
        user_id = user_record[0]
        
        # Insert auth record
        cursor.execute("""
            INSERT OR REPLACE INTO auth_users (email, password_hash, user_id, is_active)
            VALUES (?, ?, ?, ?)
        """, (TEST_USER_EMAIL, password_hash, user_id, True))
        
        conn.commit()
        print(f"   ✅ Auth record created for {TEST_USER_EMAIL}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating auth record: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    print("🚀 Creating Test User with Correct Schema")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found at: {DATABASE_PATH}")
        print("💡 Available databases found:")
        import glob
        for db in glob.glob("*.db"):
            print(f"   - {db}")
        return
    
    print(f"📁 Database: {DATABASE_PATH}")
    print(f"👤 Creating user: {TEST_USER_EMAIL}")
    
    # Create main user record
    user_id = create_test_user()
    
    if user_id:
        # Verify creation
        if verify_user_creation():
            # Create auth record
            auth_success = create_backend_auth_record()
            
            if auth_success:
                print(f"\\n🎉 Complete test user setup successful!")
                print(f"\\n🧪 Next steps:")
                print(f"   1. Run: cd quantum-leap-frontend")
                print(f"   2. Run: node check-backend-users.js")
                print(f"   3. Run: node test-railway-backend.js")
                print(f"   4. Expect 70%+ pass rate!")
                
                print(f"\\n📋 Test Credentials:")
                print(f"   Email: {TEST_USER_EMAIL}")
                print(f"   Password: {TEST_USER_PASSWORD}")
            else:
                print(f"\\n⚠️  Main user created but auth setup failed")
                print(f"   You may need to configure backend authentication manually")
        else:
            print(f"\\n❌ User creation verification failed")
    else:
        print(f"\\n❌ Failed to create test user")

if __name__ == "__main__":
    import os
    main()