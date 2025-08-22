#!/usr/bin/env python3
"""
Create database tables for AI provider failover system
"""
import sqlite3
from app.database.service import get_db_connection

def create_failover_tables():
    """Create tables needed for AI provider failover system"""
    print("🗄️ Creating AI Provider Failover Database Tables")
    print("=" * 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create ai_provider_operations table
        print("📊 Creating ai_provider_operations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_provider_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                response_time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_operations_user ON ai_provider_operations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_operations_provider ON ai_provider_operations(provider_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_operations_created ON ai_provider_operations(created_at)")
        print("✅ ai_provider_operations table created")
        
        # Create ai_trading_signals table (if not exists)
        print("📊 Creating ai_trading_signals table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_trading_signals (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                reasoning TEXT,
                target_price REAL,
                stop_loss REAL,
                take_profit REAL,
                position_size REAL,
                market_data TEXT,
                provider_used TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_user ON ai_trading_signals(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON ai_trading_signals(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON ai_trading_signals(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trading_signals_expires ON ai_trading_signals(expires_at)")
        print("✅ ai_trading_signals table created")
        
        # Create ai_execution_feedback table
        print("📊 Creating ai_execution_feedback table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_execution_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                recommendation_id TEXT,
                order_id TEXT,
                symbol TEXT NOT NULL,
                execution_price REAL,
                predicted_price REAL,
                slippage REAL,
                success_score REAL,
                feedback_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_feedback_user ON ai_execution_feedback(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_feedback_symbol ON ai_execution_feedback(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_execution_feedback_created ON ai_execution_feedback(created_at)")
        print("✅ ai_execution_feedback table created")
        
        # Create ai_recommendation_outcomes table
        print("📊 Creating ai_recommendation_outcomes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendation_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                recommendation_id TEXT NOT NULL,
                outcome_data TEXT,
                success_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_user ON ai_recommendation_outcomes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_rec ON ai_recommendation_outcomes(recommendation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_created ON ai_recommendation_outcomes(created_at)")
        print("✅ ai_recommendation_outcomes table created")
        
        # Create ai_provider_health_log table for historical tracking
        print("📊 Creating ai_provider_health_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_provider_health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time_ms REAL,
                error_message TEXT,
                success_rate REAL,
                consecutive_failures INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes separately
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_health_provider ON ai_provider_health_log(provider_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provider_health_created ON ai_provider_health_log(created_at)")
        print("✅ ai_provider_health_log table created")
        
        # Insert some sample data for testing
        print("📊 Inserting sample data...")
        
        # Sample provider operations
        sample_operations = [
            ('test_user', 'openai', 'portfolio_analysis', True, None, 1200.5),
            ('test_user', 'claude', 'portfolio_analysis', True, None, 800.3),
            ('test_user', 'openai', 'signal_generation', False, 'API rate limit exceeded', 2000.0),
            ('test_user', 'gemini', 'portfolio_analysis', True, None, 1500.2),
        ]
        
        cursor.executemany("""
            INSERT INTO ai_provider_operations 
            (user_id, provider_name, operation_type, success, error_message, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_operations)
        
        # Sample health log entries
        sample_health_logs = [
            ('openai', 'healthy', 1200.5, None, 0.85, 0),
            ('claude', 'healthy', 800.3, None, 0.92, 0),
            ('gemini', 'degraded', 1500.2, 'Occasional timeouts', 0.75, 1),
            ('grok', 'failed', 0.0, 'API key invalid', 0.0, 3),
        ]
        
        cursor.executemany("""
            INSERT INTO ai_provider_health_log 
            (provider_name, status, response_time_ms, error_message, success_rate, consecutive_failures)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_health_logs)
        
        conn.commit()
        print("✅ Sample data inserted")
        
        # Verify tables were created
        print("\n📋 Verifying table creation...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'ai_%'
            ORDER BY name
        """)
        
        tables = cursor.fetchall()
        print(f"✅ Created {len(tables)} AI-related tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   - {table[0]}: {count} records")
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("🎉 AI Provider Failover Database Setup Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating failover tables: {e}")
        return False

if __name__ == "__main__":
    create_failover_tables()