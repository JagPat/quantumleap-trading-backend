#!/usr/bin/env python3
"""
Simple AI Database Test
"""
import sqlite3
import os

def test_database():
    """Test the AI database directly"""
    print("🧪 Testing AI Database")
    print("=" * 50)
    
    try:
        # Connect to database
        db_path = os.getenv('DATABASE_PATH', 'quantumleap.db')
        print(f"Database path: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_user_preferences';")
        table_exists = cursor.fetchone()
        print(f"ai_user_preferences table exists: {bool(table_exists)}")
        
        if table_exists:
            # Check records
            cursor.execute("SELECT COUNT(*) FROM ai_user_preferences;")
            count = cursor.fetchone()[0]
            print(f"Total records: {count}")
            
            # Check specific user
            cursor.execute("""
                SELECT user_id, preferred_ai_provider, 
                       openai_api_key IS NOT NULL as has_openai,
                       claude_api_key IS NOT NULL as has_claude,
                       gemini_api_key IS NOT NULL as has_gemini,
                       created_at, updated_at
                FROM ai_user_preferences 
                WHERE user_id = 'EBW183';
            """)
            result = cursor.fetchone()
            
            if result:
                print(f"\\nUser EBW183 record:")
                print(f"  User ID: {result[0]}")
                print(f"  Provider: {result[1]}")
                print(f"  Has OpenAI: {result[2]}")
                print(f"  Has Claude: {result[3]}")
                print(f"  Has Gemini: {result[4]}")
                print(f"  Created: {result[5]}")
                print(f"  Updated: {result[6]}")
                
                # Check actual key lengths (encrypted)
                cursor.execute("""
                    SELECT LENGTH(openai_api_key) as openai_len,
                           LENGTH(claude_api_key) as claude_len,
                           LENGTH(gemini_api_key) as gemini_len
                    FROM ai_user_preferences 
                    WHERE user_id = 'EBW183';
                """)
                lengths = cursor.fetchone()
                if lengths:
                    print(f"  OpenAI key length: {lengths[0] or 0}")
                    print(f"  Claude key length: {lengths[1] or 0}")
                    print(f"  Gemini key length: {lengths[2] or 0}")
            else:
                print("\\n❌ No record found for user EBW183")
                
            # Show all users
            cursor.execute("SELECT user_id, preferred_ai_provider FROM ai_user_preferences;")
            all_users = cursor.fetchall()
            print(f"\\nAll users in database:")
            for user in all_users:
                print(f"  - {user[0]} (provider: {user[1]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database()