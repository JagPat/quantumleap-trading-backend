#!/usr/bin/env python3
"""
Test Database Error Handler
Tests for comprehensive error handling system functionality
"""
import os
import sqlite3
import tempfile
import shutil
import time
from datetime import datetime, timedelta
import sys

# Add the app directory to the path
sys.path.append('app/database')
from error_handler import (
    DatabaseErrorHandler, DatabaseError, RetryPolicy, CircuitBreakerConfig,
    ErrorCategory, ErrorSeverity, RecoveryAction, CircuitState,
    DatabaseOperationError, CircuitBreakerOpenError
)

def test_error_handler():
    """Test error handler basic functionality"""
    print("🧪 Testing Database Error Handler...")
    
    # Create temporary test environment
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_errors.db")
    
    try:
        # Initialize error handler
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        print("✅ Error handler initialized successfully")
        
        # Test 1: Error categorization
        connection_error = sqlite3.OperationalError("database connection failed")
        error = error_handler.handle_error(connection_error)
        
        assert error.category == ErrorCategory.CONNECTION_ERROR
        assert error.severity == ErrorSeverity.HIGH
        assert error.recovery_action == RecoveryAction.RECONNECT
        print("✅ Error categorization works")
        
        # Test 2: Constraint error handling
        constraint_error = sqlite3.IntegrityError("UNIQUE constraint failed")
        error = error_handler.handle_error(constraint_error)
        
        assert error.category == ErrorCategory.CONSTRAINT_ERROR
        assert error.recovery_action == RecoveryAction.IGNORE
        print("✅ Constraint error handling works")
        
        # Test 3: Timeout error handling
        timeout_error = sqlite3.OperationalError("database timeout")
        error = error_handler.handle_error(timeout_error)
        
        assert error.category == ErrorCategory.TIMEOUT_ERROR
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.recovery_action == RecoveryAction.RETRY
        print("✅ Timeout error handling works")
        
        # Test 4: Error statistics
        stats = error_handler.get_error_statistics()
        assert "total_errors_24h" in stats
        assert "errors_by_category_24h" in stats
        assert "circuit_breaker_states" in stats
        print("✅ Error statistics work")
        
        # Test 5: Recent errors retrieval
        recent_errors = error_handler.get_recent_errors(hours=1)
        assert len(recent_errors) >= 3  # We created 3 errors
        print("✅ Recent errors retrieval works")
        
        print("🎉 All basic tests passed!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_retry_mechanism():
    """Test retry mechanism"""
    print("\n🧪 Testing Retry Mechanism...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_retry.db")
    
    try:
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        # Test successful retry
        attempt_count = 0
        
        def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise sqlite3.OperationalError("temporary failure")
            return "success"
        
        # Execute with retry
        retry_decorator = error_handler.with_retry("test_operation")
        retried_operation = retry_decorator(flaky_operation)
        result = retried_operation()
        
        assert result == "success"
        assert attempt_count == 3
        print("✅ Retry mechanism works for recoverable errors")
        
        # Test retry exhaustion
        def always_failing_operation():
            raise sqlite3.OperationalError("permanent failure")
        
        try:
            retry_decorator = error_handler.with_retry("failing_operation")
            retried_failing_operation = retry_decorator(always_failing_operation)
            retried_failing_operation()
            assert False, "Should have raised exception"
        except sqlite3.OperationalError:
            print("✅ Retry exhaustion works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Retry mechanism test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n🧪 Testing Circuit Breaker...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_circuit_breaker.db")
    
    try:
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        # Get circuit breaker
        breaker = error_handler.circuit_breakers["connection"]
        assert breaker.state == CircuitState.CLOSED
        print("✅ Circuit breaker starts in CLOSED state")
        
        # Cause failures to open circuit breaker
        def failing_operation():
            raise sqlite3.OperationalError("connection failed")
        
        # Trigger failures
        for i in range(5):
            try:
                breaker.call(failing_operation)
            except:
                pass
        
        assert breaker.state == CircuitState.OPEN
        print("✅ Circuit breaker opens after failures")
        
        # Test that circuit breaker blocks calls
        try:
            breaker.call(failing_operation)
            assert False, "Should have raised CircuitBreakerOpenError"
        except CircuitBreakerOpenError:
            print("✅ Circuit breaker blocks calls when OPEN")
        
        # Test reset
        success = error_handler.reset_circuit_breaker("connection")
        assert success
        assert breaker.state == CircuitState.CLOSED
        print("✅ Circuit breaker reset works")
        
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_comprehensive_error_handling():
    """Test comprehensive error handling with execute_with_error_handling"""
    print("\n🧪 Testing Comprehensive Error Handling...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_comprehensive.db")
    
    try:
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        # Test successful operation
        def successful_operation(value):
            return value * 2
        
        result = error_handler.execute_with_error_handling(
            successful_operation,
            5,
            operation_name="test_success"
        )
        
        assert result == 10
        print("✅ Successful operation works")
        
        # Test operation with retries
        attempt_count = 0
        
        def retry_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise sqlite3.OperationalError("temporary error")
            return "recovered"
        
        result = error_handler.execute_with_error_handling(
            retry_operation,
            operation_name="test_retry",
            use_circuit_breaker=False  # Disable for this test
        )
        
        assert result == "recovered"
        print("✅ Operation with retries works")
        
        # Test permanent failure
        def permanent_failure():
            raise sqlite3.IntegrityError("constraint violation")
        
        try:
            error_handler.execute_with_error_handling(
                permanent_failure,
                operation_name="test_permanent_failure",
                use_circuit_breaker=False
            )
            assert False, "Should have raised DatabaseOperationError"
        except DatabaseOperationError:
            print("✅ Permanent failure handling works")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_error_resolution():
    """Test error resolution functionality"""
    print("\n🧪 Testing Error Resolution...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_resolution.db")
    
    try:
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        # Create an error
        test_error = sqlite3.OperationalError("test error for resolution")
        error = error_handler.handle_error(test_error)
        
        assert not error.resolved
        print("✅ Error created as unresolved")
        
        # Mark error as resolved
        success = error_handler.mark_error_resolved(error.error_id)
        assert success
        print("✅ Error marked as resolved")
        
        # Verify resolution in recent errors
        recent_errors = error_handler.get_recent_errors(hours=1)
        resolved_error = next((e for e in recent_errors if e["error_id"] == error.error_id), None)
        assert resolved_error is not None
        assert resolved_error["resolved"]
        print("✅ Error resolution verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resolution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

def test_error_cleanup():
    """Test error cleanup functionality"""
    print("\n🧪 Testing Error Cleanup...")
    
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_cleanup.db")
    
    try:
        error_handler = DatabaseErrorHandler(database_path=db_path)
        
        # Create some old errors
        old_error = sqlite3.OperationalError("old error")
        error = error_handler.handle_error(old_error)
        
        # Mark as resolved
        error_handler.mark_error_resolved(error.error_id)
        
        # Manually update timestamp to make it old
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            old_timestamp = (datetime.now() - timedelta(days=35)).isoformat()
            cursor.execute("""
                UPDATE error_log SET timestamp = ? WHERE error_id = ?
            """, (old_timestamp, error.error_id))
            conn.commit()
        
        # Count errors before cleanup
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM error_log")
            count_before = cursor.fetchone()[0]
        
        # Perform cleanup
        error_handler.cleanup_old_errors(days=30)
        
        # Count errors after cleanup
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM error_log")
            count_after = cursor.fetchone()[0]
        
        assert count_after < count_before
        print("✅ Error cleanup works")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleanup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("🚀 Starting Database Error Handler Tests\n")
    
    success1 = test_error_handler()
    success2 = test_retry_mechanism()
    success3 = test_circuit_breaker()
    success4 = test_comprehensive_error_handling()
    success5 = test_error_resolution()
    success6 = test_error_cleanup()
    
    if all([success1, success2, success3, success4, success5, success6]):
        print("\n🎉 All tests completed successfully!")
        print("✅ Database Error Handler is working correctly")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)