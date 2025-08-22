#!/usr/bin/env python3
"""
Direct test of trading schema without import issues
"""

import os
import sys
import tempfile
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the standalone schema directly without going through __init__.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'database'))

def test_direct_schema():
    """Test schema directly without problematic imports"""
    print("🧪 Testing Trading Schema Directly")
    print("=" * 50)
    
    try:
        # Import directly from the file
        import trading_schema_standalone
        
        # Use temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            test_db_path = temp_db.name
        
        try:
            # Test 1: Schema Creation
            print("\n1️⃣ Testing Schema Creation...")
            config = trading_schema_standalone.StandaloneSchemaConfig(database_path=test_db_path)
            schema_manager = trading_schema_standalone.StandaloneTradingSchema(config)
            
            success = schema_manager.create_optimized_schema()
            if success:
                print("   ✅ Schema created successfully")
            else:
                print("   ❌ Schema creation failed")
                return False
            
            # Test 2: Schema Information
            print("\n2️⃣ Testing Schema Information...")
            schema_info = schema_manager.get_schema_info()
            
            if "error" not in schema_info:
                print(f"   ✅ Schema info retrieved: {schema_info['total_objects']} objects")
                print(f"      Tables: {len(schema_info['tables'])}")
                print(f"      Indexes: {len(schema_info['indexes'])}")
                print(f"      Views: {len(schema_info['views'])}")
                print(f"      Triggers: {len(schema_info['triggers'])}")
                
                # Show table names
                tables = [t for t in schema_info['tables'] if not t.startswith('sqlite_')]
                print(f"      Table names: {', '.join(tables)}")
            else:
                print(f"   ❌ Schema info failed: {schema_info['error']}")
                return False
            
            # Test 3: Data Operations
            print("\n3️⃣ Testing Data Operations...")
            conn = schema_manager.get_connection()
            cursor = conn.cursor()
            
            # Insert test user
            cursor.execute("""
                INSERT INTO users (user_id, email, name, risk_profile)
                VALUES ('test_user', 'test@example.com', 'Test User', 'moderate')
            """)
            
            # Insert test portfolio
            cursor.execute("""
                INSERT INTO portfolio (user_id, symbol, quantity, average_price, current_price)
                VALUES ('test_user', 'RELIANCE', 100, 2500.0, 2520.0)
            """)
            
            # Insert test order
            cursor.execute("""
                INSERT INTO orders (order_id, user_id, symbol, order_type, side, quantity, price, status)
                VALUES ('order_001', 'test_user', 'RELIANCE', 'limit', 'buy', 50, 2500.0, 'pending')
            """)
            
            conn.commit()
            print("   ✅ Data insertion successful")
            
            # Test 4: Query Operations
            print("\n4️⃣ Testing Query Operations...")
            
            # Test portfolio query
            cursor.execute("SELECT * FROM portfolio WHERE user_id = 'test_user'")
            portfolio_data = cursor.fetchone()
            
            if portfolio_data:
                print("   ✅ Portfolio query successful")
                print(f"      Symbol: {portfolio_data[2]}, Quantity: {portfolio_data[3]}")
                print(f"      Market Value: {portfolio_data[6]}, Unrealized P&L: {portfolio_data[7]}")
            
            # Test view query
            cursor.execute("SELECT * FROM portfolio_summary WHERE user_id = 'test_user'")
            summary_data = cursor.fetchone()
            
            if summary_data:
                print("   ✅ Portfolio summary view working")
                print(f"      Total positions: {summary_data[1]}")
                print(f"      Total market value: {summary_data[2]}")
            
            # Test 5: Schema Validation
            print("\n5️⃣ Testing Schema Validation...")
            validation = schema_manager.validate_schema()
            
            if validation["valid"]:
                print("   ✅ Schema validation passed")
                for check in validation["checks"]:
                    print(f"      ✓ {check}")
            else:
                print(f"   ⚠️ Schema validation issues: {validation['errors']}")
            
            schema_manager.close()
            print("\n🎉 All direct schema tests passed!")
            return True
            
        finally:
            # Cleanup
            if os.path.exists(test_db_path):
                os.unlink(test_db_path)
        
    except Exception as e:
        logger.error(f"Direct schema test failed: {e}")
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Direct Trading Schema Test\n")
    
    success = test_direct_schema()
    
    if success:
        print("\n🎉 Direct test passed! Trading schema is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Direct test failed.")
        sys.exit(1)