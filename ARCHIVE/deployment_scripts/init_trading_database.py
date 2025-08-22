#!/usr/bin/env python3
"""
Initialize Trading Database with Optimized Schema
Creates and initializes the trading database with all optimized tables, indexes, and constraints
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize trading database"""
    print("🚀 Initializing Trading Database with Optimized Schema")
    print("=" * 60)
    
    try:
        # Import the trading schema manager
        from app.database.trading_schema import initialize_trading_schema, get_trading_schema_manager
        
        # Set database path
        database_path = os.getenv("DATABASE_PATH", "trading_optimized.db")
        print(f"📁 Database path: {database_path}")
        
        # Initialize schema
        print("\n🔧 Creating optimized trading schema...")
        success = initialize_trading_schema(database_path)
        
        if success:
            print("✅ Trading schema initialized successfully!")
            
            # Get schema manager for additional operations
            schema_manager = get_trading_schema_manager()
            
            # Get schema information
            print("\n📊 Schema Information:")
            schema_info = schema_manager.get_schema_info()
            
            if "error" not in schema_info:
                print(f"   📋 Schema Version: {schema_info['schema_version']}")
                print(f"   🗃️ Tables: {len(schema_info['tables'])}")
                print(f"   📇 Indexes: {len(schema_info['indexes'])}")
                print(f"   👁️ Views: {len(schema_info['views'])}")
                print(f"   ⚡ Triggers: {len(schema_info['triggers'])}")
                print(f"   📦 Total Objects: {schema_info['total_objects']}")
                
                print(f"\n📋 Tables Created:")
                for table in schema_info['tables']:
                    if not table.startswith('sqlite_'):
                        print(f"   - {table}")
                
                print(f"\n👁️ Views Created:")
                for view in schema_info['views']:
                    print(f"   - {view}")
            
            # Validate schema
            print("\n🔍 Validating Schema...")
            validation = schema_manager.validate_schema()
            
            if validation["valid"]:
                print("✅ Schema validation passed!")
                for check in validation["checks"]:
                    print(f"   ✓ {check}")
            else:
                print("⚠️ Schema validation issues found:")
                for error in validation["errors"]:
                    print(f"   ❌ {error}")
                for warning in validation.get("warnings", []):
                    print(f"   ⚠️ {warning}")
            
            # Insert sample data for testing
            print("\n📝 Inserting Sample Data...")
            insert_sample_data(schema_manager)
            
            print("\n🎉 Database initialization completed successfully!")
            print(f"📍 Database location: {os.path.abspath(database_path)}")
            
        else:
            print("❌ Failed to initialize trading schema")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

def insert_sample_data(schema_manager):
    """Insert sample data for testing"""
    try:
        conn = schema_manager.get_connection()
        cursor = conn.cursor()
        
        # Insert sample user
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, email, name, risk_profile, max_position_size, max_daily_loss)
            VALUES ('user_001', 'test@example.com', 'Test User', 'moderate', 100000.00, 5000.00)
        """)
        
        # Insert sample strategies
        cursor.execute("""
            INSERT OR IGNORE INTO strategies (strategy_id, user_id, name, strategy_type, status, max_position_size, max_daily_loss)
            VALUES ('strategy_001', 'user_001', 'Momentum Strategy', 'momentum', 'active', 50000.00, 2000.00)
        """)
        
        # Insert sample market data
        sample_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK']
        for symbol in sample_symbols:
            cursor.execute("""
                INSERT OR IGNORE INTO market_data (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (symbol, datetime.now(), 2500.0, 2550.0, 2480.0, 2520.0, 100000))
        
        # Insert sample portfolio positions
        cursor.execute("""
            INSERT OR IGNORE INTO portfolio (user_id, symbol, quantity, average_price, current_price)
            VALUES ('user_001', 'RELIANCE', 100, 2500.0, 2520.0)
        """)
        
        cursor.execute("""
            INSERT OR IGNORE INTO portfolio (user_id, symbol, quantity, average_price, current_price)
            VALUES ('user_001', 'TCS', 50, 3200.0, 3250.0)
        """)
        
        conn.commit()
        print("   ✅ Sample data inserted successfully")
        
        # Verify data insertion
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        portfolio_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM market_data")
        market_data_count = cursor.fetchone()[0]
        
        print(f"   📊 Data Summary:")
        print(f"      Users: {user_count}")
        print(f"      Portfolio positions: {portfolio_count}")
        print(f"      Market data records: {market_data_count}")
        
    except Exception as e:
        logger.error(f"Failed to insert sample data: {e}")
        print(f"   ⚠️ Sample data insertion failed: {e}")

if __name__ == "__main__":
    main()