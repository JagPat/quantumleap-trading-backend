#!/usr/bin/env python3

"""
Check Database Schema
This script examines the database structure to understand the user table schema
"""

import sqlite3
import os
import glob

def find_database_files():
    """Find all SQLite database files in the project"""
    db_patterns = [
        "*.db",
        "**/*.db",
        "app/*.db",
        "database/*.db"
    ]
    
    db_files = []
    for pattern in db_patterns:
        db_files.extend(glob.glob(pattern, recursive=True))
    
    return db_files

def examine_database(db_path):
    """Examine the structure of a database file"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\\n📁 Database: {db_path}")
        print("-" * 50)
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("   No tables found")
            return
        
        print(f"   Tables found: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            print(f"\\n   📋 Table: {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if columns:
                print("      Columns:")
                for col in columns:
                    col_id, name, data_type, not_null, default, pk = col
                    pk_indicator = " (PRIMARY KEY)" if pk else ""
                    null_indicator = " NOT NULL" if not_null else ""
                    default_indicator = f" DEFAULT {default}" if default else ""
                    print(f"        - {name}: {data_type}{pk_indicator}{null_indicator}{default_indicator}")
            
            # Check if this looks like a users table
            column_names = [col[1].lower() for col in columns]
            if any(keyword in column_names for keyword in ['email', 'username', 'user', 'login']):
                print(f"      👤 This looks like a users table!")
                
                # Show sample data (first 3 rows)
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                    sample_data = cursor.fetchall()
                    if sample_data:
                        print(f"      Sample data:")
                        for i, row in enumerate(sample_data):
                            print(f"        Row {i+1}: {row}")
                    else:
                        print(f"      No data in table")
                except Exception as e:
                    print(f"      Could not fetch sample data: {e}")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"   ❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error examining database: {e}")
        return False

def main():
    print("🔍 Checking Database Schema")
    print("=" * 40)
    
    # Find all database files
    db_files = find_database_files()
    
    if not db_files:
        print("❌ No database files found")
        print("💡 Database files to look for:")
        print("   - quantumleap.db")
        print("   - app.db")
        print("   - users.db")
        print("   - main.db")
        return
    
    print(f"📁 Found {len(db_files)} database file(s):")
    for db_file in db_files:
        print(f"   - {db_file}")
    
    # Examine each database
    for db_file in db_files:
        if os.path.exists(db_file):
            examine_database(db_file)
        else:
            print(f"\\n❌ Database file not found: {db_file}")
    
    print(f"\\n💡 Next Steps:")
    print(f"   1. Identify the correct users table structure")
    print(f"   2. Create test user with correct schema")
    print(f"   3. Update authentication to match database")

if __name__ == "__main__":
    main()