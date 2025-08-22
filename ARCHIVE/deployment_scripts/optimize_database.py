#!/usr/bin/env python3
"""
Database Optimization Script
Adds performance indexes and optimizes database structure
"""
import sqlite3
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_database_indexes():
    """Add performance indexes to the database"""
    print("🔧 Starting database optimization...")
    
    try:
        conn = sqlite3.connect('trading_app.db')
        cursor = conn.cursor()
        
        # Performance indexes for frequent queries
        indexes = [
            ("idx_users_user_id", "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)"),
            ("idx_portfolio_snapshots_user_timestamp", "CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_timestamp ON portfolio_snapshots(user_id, timestamp DESC)"),
            ("idx_ai_chat_messages_thread_id", "CREATE INDEX IF NOT EXISTS idx_ai_chat_messages_thread_id ON ai_chat_messages(thread_id, created_at DESC)"),
            ("idx_ai_trading_signals_user_symbol", "CREATE INDEX IF NOT EXISTS idx_ai_trading_signals_user_symbol ON ai_trading_signals(user_id, symbol, created_at DESC)"),
            ("idx_ai_analysis_results_user_type", "CREATE INDEX IF NOT EXISTS idx_ai_analysis_results_user_type ON ai_analysis_results(user_id, analysis_type, created_at DESC)"),
            ("idx_ai_usage_tracking_user_provider", "CREATE INDEX IF NOT EXISTS idx_ai_usage_tracking_user_provider ON ai_usage_tracking(user_id, provider, created_at DESC)"),
            ("idx_ai_chat_sessions_user_active", "CREATE INDEX IF NOT EXISTS idx_ai_chat_sessions_user_active ON ai_chat_sessions(user_id, is_active, updated_at DESC)"),
            ("idx_ai_strategies_user_active", "CREATE INDEX IF NOT EXISTS idx_ai_strategies_user_active ON ai_strategies(user_id, is_active, updated_at DESC)"),
            ("idx_ai_trading_signals_active_expires", "CREATE INDEX IF NOT EXISTS idx_ai_trading_signals_active_expires ON ai_trading_signals(is_active, expires_at)"),
        ]
        
        print(f"📊 Adding {len(indexes)} performance indexes...")
        
        for index_name, index_sql in indexes:
            start_time = time.time()
            cursor.execute(index_sql)
            execution_time = (time.time() - start_time) * 1000
            print(f"  ✅ {index_name}: {execution_time:.2f}ms")
        
        # Optimize database
        print("🔧 Running VACUUM to optimize database...")
        cursor.execute("VACUUM")
        
        print("📈 Running ANALYZE to update statistics...")
        cursor.execute("ANALYZE")
        
        conn.commit()
        
        # Check database size after optimization
        cursor.execute('PRAGMA page_count')
        page_count = cursor.fetchone()[0]
        cursor.execute('PRAGMA page_size')
        page_size = cursor.fetchone()[0]
        db_size = page_count * page_size
        
        print(f"✅ Database optimization completed!")
        print(f"📊 Final database size: {db_size / 1024:.2f} KB")
        print(f"📊 Pages: {page_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        return False

def verify_indexes():
    """Verify that all indexes were created successfully"""
    print("🔍 Verifying database indexes...")
    
    try:
        conn = sqlite3.connect('trading_app.db')
        cursor = conn.cursor()
        
        # Get all indexes
        cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
        indexes = cursor.fetchall()
        
        print(f"📋 Found {len(indexes)} performance indexes:")
        for index_name, table_name in indexes:
            print(f"  ✅ {index_name} on {table_name}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Index verification failed: {e}")
        return False

def database_health_check():
    """Perform comprehensive database health check"""
    print("🏥 Running database health check...")
    
    try:
        conn = sqlite3.connect('trading_app.db')
        cursor = conn.cursor()
        
        # Check database integrity
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()[0]
        
        if integrity_result == "ok":
            print("  ✅ Database integrity: OK")
        else:
            print(f"  ❌ Database integrity: {integrity_result}")
            return False
        
        # Check foreign key constraints
        cursor.execute("PRAGMA foreign_key_check")
        fk_violations = cursor.fetchall()
        
        if not fk_violations:
            print("  ✅ Foreign key constraints: OK")
        else:
            print(f"  ❌ Foreign key violations: {len(fk_violations)}")
            for violation in fk_violations:
                print(f"    - {violation}")
        
        # Check table statistics
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        print(f"  📊 Tables: {len(tables)}")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    - {table_name}: {count} records")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def main():
    """Main optimization routine"""
    print("🚀 QuantumLeap Backend Database Optimization")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Health check
    if not database_health_check():
        print("❌ Database health check failed. Aborting optimization.")
        return False
    
    print()
    
    # Step 2: Add indexes
    if not add_database_indexes():
        print("❌ Database optimization failed.")
        return False
    
    print()
    
    # Step 3: Verify indexes
    if not verify_indexes():
        print("❌ Index verification failed.")
        return False
    
    print()
    
    # Step 4: Final health check
    if not database_health_check():
        print("❌ Post-optimization health check failed.")
        return False
    
    print()
    print("🎉 Database optimization completed successfully!")
    print("🚀 Backend performance should be improved")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)