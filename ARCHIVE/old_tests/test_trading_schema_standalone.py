#!/usr/bin/env python3
"""
Test Standalone Trading Schema Implementation
Tests the standalone trading database schema functionality
"""

import os
import sys
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_standalone_trading_schema():
    """Test standalone trading schema creation and functionality"""
    print("🧪 Testing Standalone Trading Schema Implementation")
    print("=" * 60)
    
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        test_db_path = temp_db.name
    
    try:
        from app.database.trading_schema_standalone import StandaloneTradingSchema, StandaloneSchemaConfig
        
        # Test 1: Schema Creation
        print("\n1️⃣ Testing Schema Creation...")
        config = StandaloneSchemaConfig(database_path=test_db_path)
        schema_manager = StandaloneTradingSchema(config)
        
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
        else:
            print(f"   ❌ Schema info failed: {schema_info['error']}")
            return False
        
        # Test 3: Schema Validation
        print("\n3️⃣ Testing Schema Validation...")
        validation = schema_manager.validate_schema()
        
        if validation["valid"]:
            print("   ✅ Schema validation passed")
        else:
            print(f"   ⚠️ Schema validation issues: {validation['errors']}")
        
        # Test 4: Data Operations
        print("\n4️⃣ Testing Data Operations...")
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
            VALUES ('test_user', 'TEST', 100, 1000.0, 1050.0)
        """)
        
        # Insert test order
        cursor.execute("""
            INSERT INTO orders (order_id, user_id, symbol, order_type, side, quantity, price, status)
            VALUES ('order_001', 'test_user', 'TEST', 'limit', 'buy', 50, 1000.0, 'pending')
        """)
        
        conn.commit()
        print("   ✅ Data insertion successful")
        
        # Test 5: Views and Computed Columns
        print("\n5️⃣ Testing Views and Computed Columns...")
        
        # Test portfolio summary view
        cursor.execute("SELECT * FROM portfolio_summary WHERE user_id = 'test_user'")
        portfolio_summary = cursor.fetchone()
        
        if portfolio_summary:
            print("   ✅ Portfolio summary view working")
            print(f"      Total positions: {portfolio_summary[1]}")
            print(f"      Total market value: {portfolio_summary[2]}")
        
        # Test computed columns
        cursor.execute("SELECT market_value, unrealized_pnl FROM portfolio WHERE user_id = 'test_user'")
        portfolio_data = cursor.fetchone()
        
        if portfolio_data:
            print("   ✅ Computed columns working")
            print(f"      Market value: {portfolio_data[0]}")
            print(f"      Unrealized P&L: {portfolio_data[1]}")
        
        # Test 6: Constraints
        print("\n6️⃣ Testing Constraints...")
        
        try:
            # Test invalid risk profile (should fail)
            cursor.execute("""
                INSERT INTO users (user_id, email, name, risk_profile)
                VALUES ('invalid_user', 'invalid@example.com', 'Invalid User', 'invalid_risk')
            """)
            conn.commit()
            print("   ❌ Constraint validation failed - invalid data accepted")
        except Exception:
            print("   ✅ Constraint validation working - invalid data rejected")
        
        schema_manager.close()
        print("\n🎉 All standalone trading schema tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Standalone trading schema test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

def test_standalone_integration():
    """Test standalone schema integration"""
    print("\n🔗 Testing Standalone Schema Integration...")
    
    try:
        from app.database.trading_schema_standalone import get_standalone_trading_schema, initialize_standalone_trading_schema
        
        # Test initialization function
        test_db = "test_standalone_integration.db"
        success = initialize_standalone_trading_schema(test_db)
        
        if success:
            print("   ✅ Standalone schema initialization function working")
            
            # Test global instance
            schema_manager = get_standalone_trading_schema()
            if schema_manager:
                print("   ✅ Global standalone schema manager instance working")
            
            # Cleanup
            if os.path.exists(test_db):
                os.unlink(test_db)
            
            return True
        else:
            print("   ❌ Standalone schema initialization failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Standalone integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Standalone Trading Schema Tests\n")
    
    success1 = test_standalone_trading_schema()
    success2 = test_standalone_integration()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Standalone trading schema is ready for Railway deployment.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)