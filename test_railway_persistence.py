#!/usr/bin/env python3
"""
Test Railway Persistence Issues
Test script to verify filesystem permissions and database persistence on Railway
"""

import os
import sqlite3
import tempfile
from pathlib import Path

def test_filesystem_permissions():
    """Test various directory permissions on Railway"""
    print("=== Testing Filesystem Permissions ===")
    
    test_dirs = [
        "/tmp",
        "/app",
        ".",
        "./data",
        "/var/tmp"
    ]
    
    for test_dir in test_dirs:
        try:
            # Test if directory exists
            exists = os.path.exists(test_dir)
            print(f"Directory {test_dir}: {'EXISTS' if exists else 'NOT EXISTS'}")
            
            if exists:
                # Test if writable
                test_file = os.path.join(test_dir, "test_write.txt")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    print(f"  ✓ WRITABLE")
                except Exception as e:
                    print(f"  ✗ NOT WRITABLE: {e}")
                
                # Test if readable
                try:
                    os.listdir(test_dir)
                    print(f"  ✓ READABLE")
                except Exception as e:
                    print(f"  ✗ NOT READABLE: {e}")
        except Exception as e:
            print(f"Directory {test_dir}: ERROR - {e}")
    
    print()

def test_database_creation():
    """Test database creation in various locations"""
    print("=== Testing Database Creation ===")
    
    test_locations = [
        "trading_app.db",
        "./trading_app.db", 
        "/tmp/trading_app.db",
        "./data/trading_app.db"
    ]
    
    for db_path in test_locations:
        try:
            print(f"Testing database at: {db_path}")
            
            # Create database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    test_data TEXT
                )
            """)
            
            # Insert test data
            cursor.execute("INSERT INTO test_table (test_data) VALUES (?)", ("test",))
            conn.commit()
            
            # Read test data
            cursor.execute("SELECT * FROM test_table")
            result = cursor.fetchone()
            
            print(f"  ✓ Database created and data inserted: {result}")
            
            # Clean up
            conn.close()
            os.remove(db_path)
            print(f"  ✓ Database cleaned up")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    print()

def test_environment_variables():
    """Test environment variables for Railway"""
    print("=== Testing Environment Variables ===")
    
    railway_vars = [
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID", 
        "RAILWAY_SERVICE_ID",
        "PORT",
        "DATABASE_URL"
    ]
    
    for var in railway_vars:
        value = os.environ.get(var)
        print(f"{var}: {value if value else 'NOT SET'}")
    
    print()

def test_current_working_directory():
    """Test current working directory and its contents"""
    print("=== Testing Current Working Directory ===")
    
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    try:
        contents = os.listdir(cwd)
        print(f"Directory contents ({len(contents)} items):")
        for item in contents[:10]:  # Show first 10 items
            item_path = os.path.join(cwd, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"  📄 {item} ({size} bytes)")
            else:
                print(f"  📁 {item}/")
        if len(contents) > 10:
            print(f"  ... and {len(contents) - 10} more items")
    except Exception as e:
        print(f"Error listing directory: {e}")
    
    print()

if __name__ == "__main__":
    print("🚂 Railway Persistence Test")
    print("=" * 50)
    
    test_environment_variables()
    test_current_working_directory()
    test_filesystem_permissions()
    test_database_creation()
    
    print("✅ Test completed!") 