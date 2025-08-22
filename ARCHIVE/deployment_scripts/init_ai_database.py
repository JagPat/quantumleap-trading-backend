#!/usr/bin/env python3
"""
Initialize AI Database Tables
"""
import sqlite3
import os

def init_ai_database():
    """Initialize the AI database tables"""
    print("🔧 Initializing AI Database Tables")
    print("=" * 50)
    
    try:
        # Connect to database
        db_path = os.getenv('DATABASE_PATH', 'quantumleap.db')
        print(f"Database path: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create ai_user_preferences table
        print("Creating ai_user_preferences table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                openai_api_key TEXT,
                claude_api_key TEXT,
                gemini_api_key TEXT,
                grok_api_key TEXT,
                preferred_ai_provider TEXT DEFAULT 'auto',
                provider_priorities TEXT,
                cost_limits TEXT,
                risk_tolerance TEXT DEFAULT 'medium',
                trading_style TEXT DEFAULT 'balanced',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create users table if it doesn't exist (for foreign key)
        print("Creating users table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert user EBW183 if it doesn't exist
        print("Ensuring user EBW183 exists...")
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id) VALUES ('EBW183')
        ''')
        
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"\\nTables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check ai_user_preferences table structure
        cursor.execute("PRAGMA table_info(ai_user_preferences);")
        columns = cursor.fetchall()
        print(f"\\nai_user_preferences table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        print("\\n✅ Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    init_ai_database()