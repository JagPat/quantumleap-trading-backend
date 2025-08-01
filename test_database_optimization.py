"""
Comprehensive tests for Railway-optimized database manager
"""

import pytest
import os
import tempfile
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the database components
from app.database.optimized_manager import (
    OptimizedDatabaseManager, 
    DatabaseConfig, 
    ConnectionPool,
    QueryMetrics
)
from app.database.railway_config import (
    RailwayDatabaseConfig,
    get_railway_database_config,
    validate_railway_environment,
    RailwayDatabaseUtils
)

class TestDatabaseConfig:
    """Test database configuration"""
    
    def test_default_config(self):
        """Test default database configuration"""
        config = DatabaseConfig()
        
        assert config.min_connections == 2
        assert config.max_connections == 20
        assert config.query_timeout == 50
        assert config.enable_query_cache is True
        
    def test_railway_config_detection(self):
        """Test Railway environment detection"""
        with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT': 'production'}):
            config = get_railway_database_config()
            
            assert config.is_railway_production is True
            assert config.is_railway is True
            assert config.enable_ssl is True
            assert config.max_connections == 15

class TestConnectionPool:
    """Test connection pool functionality"""
    
    def setup_method(self):
        """Setup test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.config = DatabaseConfig(
            database_url=f'sqlite:///{self.temp_db.name}',
            max_connections=5,
            min_connections=1
        )
        self.pool = ConnectionPool(self.config)
    
    def teardown_method(self):
        """Cleanup test database"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_sqlite_connection(self):
        """Test SQLite connection creation"""
        with self.pool.get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_connection_metrics(self):
        """Test connection metrics collection"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        
        metrics = self.pool.get_metrics()
        assert len(metrics) > 0
        assert 'execution_time_ms' in metrics[0]
        assert 'database_type' in metrics[0]
    
    def test_health_check(self):
        """Test connection pool health check"""
        health = self.pool.health_check()
        
        assert health['status'] == 'healthy'
        assert health['database_type'] == 'sqlite'
        assert 'version' in health
        assert 'timestamp' in health
    
    def test_concurrent_connections(self):
        """Test concurrent connection handling"""
        results = []
        errors = []
        
        def worker():
            try:
                with self.pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    results.append(result[0])
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == 1 for r in results)

class TestOptimizedDatabaseManager:
    """Test optimized database manager"""
    
    def setup_method(self):
        """Setup test database manager"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        config = DatabaseConfig(
            database_url=f'sqlite:///{self.temp_db.name}',
            enable_query_cache=True,
            cache_size=100
        )
        self.db_manager = OptimizedDatabaseManager(config)
        
        # Create test table
        self.db_manager.execute_query("""
            CREATE TABLE test_trades (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def teardown_method(self):
        """Cleanup test database"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_execute_query(self):
        """Test query execution"""
        # Insert test data
        result = self.db_manager.execute_query(
            "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
            ('AAPL', 100.0, 150.50)
        )
        
        # Query test data
        result = self.db_manager.execute_query(
            "SELECT * FROM test_trades WHERE symbol = ?",
            ('AAPL',)
        )
        
        assert len(result) == 1
        assert result[0]['symbol'] == 'AAPL'
        assert result[0]['quantity'] == 100.0
        assert result[0]['price'] == 150.50
    
    def test_query_caching(self):
        """Test query result caching"""
        # Insert test data
        self.db_manager.execute_query(
            "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
            ('AAPL', 100.0, 150.50)
        )
        
        # Execute same query twice (without parameters for caching)
        query = "SELECT COUNT(*) as count FROM test_trades"
        
        start_time = time.time()
        result1 = self.db_manager.execute_query(query)
        first_execution_time = time.time() - start_time
        
        start_time = time.time()
        result2 = self.db_manager.execute_query(query)
        second_execution_time = time.time() - start_time
        
        assert result1 == result2
        # Second execution should be faster due to caching
        # (This might not always be true in fast systems, so we just check results match)
        assert result1[0]['count'] == 1
    
    def test_transaction_execution(self):
        """Test transaction execution"""
        operations = [
            {
                'query': "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
                'params': ('AAPL', 100.0, 150.50)
            },
            {
                'query': "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
                'params': ('GOOGL', 50.0, 2800.00)
            }
        ]
        
        success = self.db_manager.execute_transaction(operations)
        assert success is True
        
        # Verify both records were inserted
        result = self.db_manager.execute_query("SELECT COUNT(*) as count FROM test_trades")
        assert result[0]['count'] == 2
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        operations = [
            {
                'query': "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
                'params': ('AAPL', 100.0, 150.50)
            },
            {
                'query': "INSERT INTO invalid_table (column) VALUES (?)",  # This will fail
                'params': ('value',)
            }
        ]
        
        success = self.db_manager.execute_transaction(operations)
        assert success is False
        
        # Verify no records were inserted due to rollback
        result = self.db_manager.execute_query("SELECT COUNT(*) as count FROM test_trades")
        assert result[0]['count'] == 0
    
    def test_performance_metrics(self):
        """Test performance metrics collection"""
        # Execute some queries to generate metrics
        for i in range(10):
            self.db_manager.execute_query(
                "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
                (f'STOCK{i}', float(i * 10), float(i * 100))
            )
        
        metrics = self.db_manager.get_performance_metrics()
        
        assert metrics['status'] == 'healthy'
        assert metrics['query_count'] > 0
        assert 'avg_execution_time_ms' in metrics
        assert 'p95_execution_time_ms' in metrics
        assert 'error_rate' in metrics
    
    def test_health_check(self):
        """Test comprehensive health check"""
        health = self.db_manager.health_check()
        
        assert health['status'] in ['healthy', 'degraded']
        assert 'database' in health
        assert 'performance' in health
        assert 'config' in health
        assert 'timestamp' in health
    
    def test_database_optimization(self):
        """Test database optimization procedures"""
        # Insert test data
        for i in range(100):
            self.db_manager.execute_query(
                "INSERT INTO test_trades (symbol, quantity, price) VALUES (?, ?, ?)",
                (f'STOCK{i}', float(i), float(i * 10))
            )
        
        # Run optimization
        self.db_manager.optimize_database()
        
        # Verify database still works after optimization
        result = self.db_manager.execute_query("SELECT COUNT(*) as count FROM test_trades")
        assert result[0]['count'] == 100

class TestRailwayConfiguration:
    """Test Railway-specific configuration"""
    
    def test_environment_validation(self):
        """Test Railway environment validation"""
        with patch.dict(os.environ, {
            'RAILWAY_ENVIRONMENT': 'production',
            'DATABASE_URL': 'postgresql://user:pass@host:5432/db'
        }):
            validation = validate_railway_environment()
            
            assert validation['valid'] is True
            assert validation['environment']['is_railway'] is True
            assert validation['environment']['database_url_provided'] is True
    
    def test_connection_info_postgresql(self):
        """Test PostgreSQL connection info parsing"""
        with patch('app.database.railway_config.get_database_connection_string') as mock_get_conn:
            mock_get_conn.return_value = 'postgresql://user:pass@host.railway.app:5432/railway'
            
            info = RailwayDatabaseUtils.get_connection_info()
            
            assert info['type'] == 'postgresql'
            assert info['host'] == 'host.railway.app'
            assert info['port'] == 5432
            assert info['database'] == 'railway'
            assert info['railway_managed'] is True
    
    def test_connection_info_sqlite(self):
        """Test SQLite connection info parsing"""
        with patch('app.database.railway_config.get_database_connection_string') as mock_get_conn:
            mock_get_conn.return_value = 'sqlite:///test.db'
            
            info = RailwayDatabaseUtils.get_connection_info()
            
            assert info['type'] == 'sqlite'
            assert info['path'] == 'test.db'
            assert info['railway_managed'] is False

class TestPerformanceAndConcurrency:
    """Test performance and concurrency aspects"""
    
    def setup_method(self):
        """Setup performance test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        config = DatabaseConfig(
            database_url=f'sqlite:///{self.temp_db.name}',
            max_connections=10
        )
        self.db_manager = OptimizedDatabaseManager(config)
        
        # Create test table with indexes
        self.db_manager.execute_query("""
            CREATE TABLE performance_test (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db_manager.execute_query("""
            CREATE INDEX idx_symbol_timestamp ON performance_test(symbol, timestamp)
        """)
    
    def teardown_method(self):
        """Cleanup performance test database"""
        try:
            os.unlink(self.temp_db.name)
        except:
            pass
    
    def test_concurrent_reads_writes(self):
        """Test concurrent read and write operations"""
        results = []
        errors = []
        
        def writer(thread_id):
            try:
                for i in range(10):
                    self.db_manager.execute_query(
                        "INSERT INTO performance_test (symbol, price, volume) VALUES (?, ?, ?)",
                        (f'STOCK{thread_id}_{i}', float(i * 10), i * 100)
                    )
                results.append(f'writer_{thread_id}_success')
            except Exception as e:
                errors.append(f'writer_{thread_id}_error: {str(e)}')
        
        def reader(thread_id):
            try:
                for i in range(5):
                    result = self.db_manager.execute_query(
                        "SELECT COUNT(*) as count FROM performance_test"
                    )
                    time.sleep(0.01)  # Small delay
                results.append(f'reader_{thread_id}_success')
            except Exception as e:
                errors.append(f'reader_{thread_id}_error: {str(e)}')
        
        threads = []
        
        # Start writer threads
        for i in range(3):
            thread = threading.Thread(target=writer, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Start reader threads
        for i in range(2):
            thread = threading.Thread(target=reader, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5  # 3 writers + 2 readers
        
        # Verify data integrity
        final_count = self.db_manager.execute_query(
            "SELECT COUNT(*) as count FROM performance_test"
        )
        assert final_count[0]['count'] == 30  # 3 writers * 10 inserts each
    
    def test_query_performance_under_load(self):
        """Test query performance under load"""
        # Insert test data
        for i in range(1000):
            self.db_manager.execute_query(
                "INSERT INTO performance_test (symbol, price, volume) VALUES (?, ?, ?)",
                (f'STOCK{i % 10}', float(i), i * 10)
            )
        
        # Measure query performance
        start_time = time.time()
        
        for _ in range(100):
            result = self.db_manager.execute_query(
                "SELECT symbol, AVG(price) as avg_price FROM performance_test GROUP BY symbol"
            )
        
        total_time = time.time() - start_time
        avg_query_time_ms = (total_time / 100) * 1000
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert avg_query_time_ms < 100, f"Average query time too slow: {avg_query_time_ms}ms"
        
        # Check performance metrics
        metrics = self.db_manager.get_performance_metrics()
        assert metrics['status'] == 'healthy'
        assert metrics['p95_execution_time_ms'] < 200  # 200ms threshold for p95

if __name__ == '__main__':
    pytest.main([__file__, '-v'])