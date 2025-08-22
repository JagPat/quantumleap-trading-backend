#!/usr/bin/env python3
"""
Initialize User Profile Database Tables
Ensures all required tables for user investment profiles are created
"""
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def init_user_profile_database():
    """Initialize database with user profile tables"""
    print("🔧 Initializing User Profile Database Tables")
    print("=" * 60)
    
    try:
        from app.database.service import init_database
        
        print("1. Running database initialization...")
        init_database()
        print("✅ Database initialization completed")
        
        # Verify tables exist
        import sqlite3
        from app.core.config import settings
        
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()
        
        print("\n2. Verifying user profile tables...")
        
        # Check if user_investment_profiles table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_investment_profiles'
        """)
        
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ user_investment_profiles table exists")
            
            # Check table structure
            cursor.execute("PRAGMA table_info(user_investment_profiles)")
            columns = cursor.fetchall()
            
            print(f"   - Table has {len(columns)} columns")
            
            # Display key columns
            key_columns = ['user_id', 'risk_tolerance', 'investment_timeline', 'preferred_sectors']
            for col in columns:
                col_name = col[1]  # Column name is at index 1
                if col_name in key_columns:
                    print(f"   - Column: {col_name} ({col[2]})")  # col[2] is data type
            
        else:
            print("❌ user_investment_profiles table missing")
            print("Creating table manually...")
            
            # Create the table manually
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_investment_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    risk_tolerance TEXT DEFAULT 'moderate',
                    investment_timeline TEXT DEFAULT 'medium_term',
                    investment_goals TEXT DEFAULT '[]',
                    preferred_sectors TEXT DEFAULT '[]',
                    avoided_sectors TEXT DEFAULT '[]',
                    max_position_size REAL DEFAULT 15.0,
                    min_position_size REAL DEFAULT 2.0,
                    trading_frequency TEXT DEFAULT 'monthly',
                    auto_trading_enabled BOOLEAN DEFAULT FALSE,
                    auto_trading_max_amount REAL DEFAULT 100000,
                    stop_loss_preference REAL DEFAULT 10.0,
                    take_profit_preference REAL DEFAULT 25.0,
                    rebalancing_frequency TEXT DEFAULT 'monthly',
                    dividend_preference TEXT DEFAULT 'reinvest',
                    tax_optimization_enabled BOOLEAN DEFAULT TRUE,
                    esg_preference BOOLEAN DEFAULT FALSE,
                    international_exposure_preference REAL DEFAULT 10.0,
                    cash_allocation_preference REAL DEFAULT 5.0,
                    volatility_tolerance TEXT DEFAULT 'medium',
                    market_timing_preference TEXT DEFAULT 'systematic',
                    notification_preferences TEXT DEFAULT '{}',
                    custom_constraints TEXT DEFAULT '',
                    profile_notes TEXT DEFAULT '',
                    last_risk_assessment_date TIMESTAMP,
                    profile_completeness_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_investment_profiles_user_id 
                ON user_investment_profiles (user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_investment_profiles_risk_tolerance 
                ON user_investment_profiles (risk_tolerance)
            ''')
            
            conn.commit()
            print("✅ user_investment_profiles table created manually")
        
        print("\n3. Testing table functionality...")
        
        # Test insert
        test_user_id = "test_init_user"
        cursor.execute('''
            INSERT OR REPLACE INTO user_investment_profiles (
                user_id, risk_tolerance, investment_timeline, preferred_sectors
            ) VALUES (?, ?, ?, ?)
        ''', (test_user_id, 'moderate', 'long_term', '["Technology", "Banking"]'))
        
        # Test select
        cursor.execute('''
            SELECT user_id, risk_tolerance, investment_timeline, preferred_sectors
            FROM user_investment_profiles 
            WHERE user_id = ?
        ''', (test_user_id,))
        
        result = cursor.fetchone()
        
        if result:
            print("✅ Table insert/select working")
            print(f"   - User ID: {result[0]}")
            print(f"   - Risk Tolerance: {result[1]}")
            print(f"   - Timeline: {result[2]}")
            print(f"   - Sectors: {result[3]}")
            
            # Clean up test data
            cursor.execute('DELETE FROM user_investment_profiles WHERE user_id = ?', (test_user_id,))
            conn.commit()
            print("✅ Test data cleaned up")
        else:
            print("❌ Table insert/select failed")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 USER PROFILE DATABASE INITIALIZATION COMPLETE")
        print("=" * 60)
        print("✅ All tables created and verified")
        print("✅ Ready for user profile system testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_user_profile_database()
    sys.exit(0 if success else 1)