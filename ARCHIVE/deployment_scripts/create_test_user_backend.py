#!/usr/bin/env python3

"""
Create Test User for Backend Testing
This script creates a test user in the backend database for testing purposes.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

# Database configuration
DATABASE_PATH = "quantumleap.db"  # Adjust path as needed
TEST_USER_EMAIL = "test@quantumleap.com"
TEST_USER_PASSWORD = "test123"

def hash_password(password):
    """Hash password using SHA256 (adjust based on your backend's hashing method)"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_test_user():
    """Create test user in the database"""
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
        
        # Hash the password
        password_hash = hash_password(TEST_USER_PASSWORD)
        
        # Create user
        cursor.execute("""
            INSERT INTO users (email, password_hash, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            TEST_USER_EMAIL,
            password_hash,
            True,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Test user created successfully!")
        print(f"   Email: {TEST_USER_EMAIL}")
        print(f"   Password: {TEST_USER_PASSWORD}")
        print(f"   User ID: {user_id}")
        
        return user_id
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return None
    finally:
        if conn:
            conn.close()

def verify_user_creation():
    """Verify the user was created correctly"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, is_active, created_at 
            FROM users 
            WHERE email = ?
        """, (TEST_USER_EMAIL,))
        
        user = cursor.fetchone()
        
        if user:
            print(f"\n🔍 User verification:")
            print(f"   ID: {user[0]}")
            print(f"   Email: {user[1]}")
            print(f"   Active: {user[2]}")
            print(f"   Created: {user[3]}")
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

def main():
    print("🚀 Creating Test User for Backend Testing")
    print("=" * 50)
    
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found at: {DATABASE_PATH}")
        print("💡 Please adjust DATABASE_PATH in the script")
        return
    
    print(f"📁 Database: {DATABASE_PATH}")
    print(f"👤 Creating user: {TEST_USER_EMAIL}")
    
    # Create test user
    user_id = create_test_user()
    
    if user_id:
        # Verify creation
        if verify_user_creation():
            print(f"\n🎉 Test user setup complete!")
            print(f"\n🧪 Next steps:")
            print(f"   1. Run: cd quantum-leap-frontend")
            print(f"   2. Run: node check-backend-users.js")
            print(f"   3. Run: node test-railway-backend.js")
            print(f"   4. Expect 70%+ pass rate!")
        else:
            print(f"\n❌ User creation verification failed")
    else:
        print(f"\n❌ Failed to create test user")

if __name__ == "__main__":
    main()