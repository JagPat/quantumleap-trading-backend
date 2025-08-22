#!/usr/bin/env python3
"""
Test Suite for Gradual Rollout System
Tests beta user management, monitoring, and rollback procedures
"""

import os
import sys
import json
import sqlite3
import time
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GradualRolloutTester:
    """Test suite for gradual rollout system"""
    
    def __init__(self):
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db_path = self.temp_db.name
        self.temp_db.close()
        
        self.test_results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": []
        }
    
    def run_test(self, test_name, test_func):
        """Run a single test and record results"""
        print(f"🧪 Testing {test_name}...")
        
        try:
            result = test_func()
            if result:
                print(f"  ✅ {test_name} - PASSED")
                self.test_results["tests_passed"] += 1
                self.test_results["test_details"].append({
                    "test": test_name,
                    "status": "PASSED",
                    "message": "Test completed successfully"
                })
            else:
                print(f"  ❌ {test_name} - FAILED")
                self.test_results["tests_failed"] += 1
                self.test_results["test_details"].append({
                    "test": test_name,
                    "status": "FAILED",
                    "message": "Test returned False"
                })
        except Exception as e:
            print(f"  ❌ {test_name} - ERROR: {e}")
            self.test_results["tests_failed"] += 1
            self.test_results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "message": str(e)
            })
    
    def test_beta_user_manager_initialization(self):
        """Test BetaUserManager initialization"""
        from gradual_rollout_system import BetaUserManager
        
        beta_manager = BetaUserManager(self.test_db_path)
        
        # Check if tables were created
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["beta_users", "rollout_phases", "rollout_events"]
        for table in required_tables:
            if table not in tables:
                conn.close()
                raise Exception(f"Missing required table: {table}")
        
        # Check if phases were initialized
        cursor.execute("SELECT COUNT(*) FROM rollout_phases")
        phase_count = cursor.fetchone()[0]
        
        conn.close()
        
        if phase_count < 4:
            raise Exception(f"Expected 4 phases, found {phase_count}")
        
        return True
    
    def test_beta_user_enrollment(self):
        """Test beta user enrollment process"""
        from gradual_rollout_system import BetaUserManager
        
        beta_manager = BetaUserManager(self.test_db_path)
        
        # Test successful enrollment
        success = beta_manager.enroll_beta_user("test_user_1", "test1@example.com", "phase_1")
        if not success:
            raise Exception("Failed to enroll valid user")
        
        # Test duplicate enrollment
        success = beta_manager.enroll_beta_user("test_user_1", "test1@example.com", "phase_1")
        if success:
            raise Exception("Duplicate enrollment should fail")
        
        # Test phase capacity
        # Enroll users up to phase_1 limit (5 users)
        for i in range(2, 6):
            success = beta_manager.enroll_beta_user(f"test_user_{i}", f"test{i}@example.com", "phase_1")
            if not success:
                raise Exception(f"Failed to enroll user {i}")
        
        # Try to enroll one more (should fail due to capacity)
        success = beta_manager.enroll_beta_user("test_user_6", "test6@example.com", "phase_1")
        if success:
            raise Exception("Enrollment should fail when phase is at capacity")
        
        return True
    
    def test_rollout_phase_management(self):
        """Test rollout phase management"""
        from gradual_rollout_system import BetaUserManager
        
        beta_manager = BetaUserManager(self.test_db_path)
        
        # Get beta users
        users = beta_manager.get_beta_users("phase_1")
        if len(users) != 5:  # From previous test
            raise Exception(f"Expected 5 users in phase_1, found {len(users)}")
        
        # Test user activity update
        beta_manager.update_user_activity("test_user_1", {
            "last_login": datetime.now().isoformat(),
            "actions_performed": 10,
            "session_duration": 300
        })
        
        # Verify activity was updated
        users = beta_manager.get_beta_users("phase_1")
        user_1 = next((u for u in users if u["user_id"] == "test_user_1"), None)
        
        if not user_1 or not user_1["performance_metrics"]:
            raise Exception("User activity update failed")
        
        return True
    
    def test_enhanced_monitoring(self):
        """Test enhanced monitoring system"""
        from gradual_rollout_system import BetaUserManager, EnhancedMonitoring
        
        beta_manager = BetaUserManager(self.test_db_path)
        monitoring = EnhancedMonitoring(beta_manager)
        
        # Test monitoring initialization
        monitoring.start_enhanced_monitoring()
        
        # Let it run briefly
        time.sleep(2)
        
        # Test metric collection
        system_metrics = monitoring._collect_system_metrics()
        if not isinstance(system_metrics, dict):
            raise Exception("System metrics collection failed")
        
        user_metrics = monitoring._collect_user_metrics()
        if not isinstance(user_metrics, dict):
            raise Exception("User metrics collection failed")
        
        app_metrics = monitoring._collect_application_metrics()
        if not isinstance(app_metrics, dict):
            raise Exception("Application metrics collection failed")
        
        # Stop monitoring
        monitoring.stop_enhanced_monitoring()
        
        return True
    
    def test_rollback_manager(self):
        """Test rollback manager functionality"""
        from gradual_rollout_system import BetaUserManager, RollbackManager
        
        beta_manager = BetaUserManager(self.test_db_path)
        rollback_manager = RollbackManager(beta_manager)
        
        # Test rollback plan creation
        rollback_plan = rollback_manager.create_rollback_plan()
        
        if not isinstance(rollback_plan, dict):
            raise Exception("Rollback plan creation failed")
        
        required_keys = ["rollback_procedures", "emergency_contacts", "rollback_triggers"]
        for key in required_keys:
            if key not in rollback_plan:
                raise Exception(f"Missing key in rollback plan: {key}")
        
        # Test emergency rollback execution
        success = rollback_manager.execute_emergency_rollback("high_error_rate", "critical")
        if not success:
            raise Exception("Emergency rollback execution failed")
        
        # Verify phases were paused
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT status FROM rollout_phases WHERE status = 'paused'")
        paused_phases = cursor.fetchall()
        
        conn.close()
        
        if len(paused_phases) == 0:
            raise Exception("Emergency rollback did not pause phases")
        
        return True
    
    def test_performance_monitoring(self):
        """Test performance monitoring system"""
        from performance_monitoring_optimization import PerformanceMonitor
        
        performance_monitor = PerformanceMonitor(self.test_db_path)
        
        # Test monitoring initialization
        performance_monitor.start_monitoring()
        
        # Let it collect some data
        time.sleep(3)
        
        # Test metrics collection
        metrics = performance_monitor._collect_performance_metrics()
        if not isinstance(metrics, dict):
            raise Exception("Performance metrics collection failed")
        
        # Test report generation
        report = performance_monitor.get_performance_report(hours=1)
        if not isinstance(report, dict):
            raise Exception("Performance report generation failed")
        
        required_keys = ["performance_summary", "optimization_actions", "total_metrics_collected"]
        for key in required_keys:
            if key not in report:
                raise Exception(f"Missing key in performance report: {key}")
        
        # Stop monitoring
        performance_monitor.stop_monitoring()
        
        return True
    
    def test_gradual_rollout_orchestrator(self):
        """Test gradual rollout orchestrator"""
        from gradual_rollout_system import GradualRolloutOrchestrator
        
        # Create new orchestrator with test database
        orchestrator = GradualRolloutOrchestrator()
        orchestrator.beta_manager.db_path = self.test_db_path
        orchestrator.beta_manager._init_beta_tables()
        
        # Test rollout status
        status = orchestrator.get_rollout_status()
        if not isinstance(status, dict):
            raise Exception("Rollout status retrieval failed")
        
        required_keys = ["rollout_active", "current_phase", "phases", "user_counts"]
        for key in required_keys:
            if key not in status:
                raise Exception(f"Missing key in rollout status: {key}")
        
        # Test batch enrollment
        test_users = [
            {"user_id": "batch_user_1", "email": "batch1@example.com"},
            {"user_id": "batch_user_2", "email": "batch2@example.com"}
        ]
        
        results = orchestrator.enroll_beta_users_batch(test_users)
        if not isinstance(results, dict):
            raise Exception("Batch enrollment failed")
        
        if "successful" not in results or "failed" not in results:
            raise Exception("Batch enrollment results incomplete")
        
        return True
    
    def test_dashboard_creation(self):
        """Test dashboard creation"""
        from gradual_rollout_system import GradualRolloutOrchestrator
        from performance_monitoring_optimization import create_performance_dashboard, PerformanceMonitor
        
        # Test rollout dashboard
        orchestrator = GradualRolloutOrchestrator()
        orchestrator.beta_manager.db_path = self.test_db_path
        orchestrator.beta_manager._init_beta_tables()
        
        orchestrator.create_rollout_dashboard()
        
        if not Path("rollout_dashboard.html").exists():
            raise Exception("Rollout dashboard creation failed")
        
        # Test performance dashboard
        performance_monitor = PerformanceMonitor(self.test_db_path)
        create_performance_dashboard(performance_monitor)
        
        if not Path("performance_dashboard.html").exists():
            raise Exception("Performance dashboard creation failed")
        
        return True
    
    def test_database_operations(self):
        """Test database operations under concurrent access"""
        from gradual_rollout_system import BetaUserManager
        
        beta_manager = BetaUserManager(self.test_db_path)
        
        def concurrent_enrollment(user_id):
            """Concurrent enrollment function"""
            try:
                return beta_manager.enroll_beta_user(f"concurrent_user_{user_id}", f"concurrent{user_id}@example.com", "phase_2")
            except Exception:
                return False
        
        # Test concurrent enrollments
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_enrollment, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        users = beta_manager.get_beta_users("phase_2")
        if len(users) == 0:
            raise Exception("No users enrolled in concurrent test")
        
        return True
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            if os.path.exists(self.test_db_path):
                os.unlink(self.test_db_path)
            
            # Clean up generated files
            test_files = [
                "rollout_dashboard.html",
                "performance_dashboard.html",
                "rollback_plan.json"
            ]
            
            for file_path in test_files:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
    
    def run_all_tests(self):
        """Run all gradual rollout tests"""
        print("🚀 Starting Gradual Rollout System Tests...\n")
        
        tests = [
            ("Beta User Manager Initialization", self.test_beta_user_manager_initialization),
            ("Beta User Enrollment", self.test_beta_user_enrollment),
            ("Rollout Phase Management", self.test_rollout_phase_management),
            ("Enhanced Monitoring", self.test_enhanced_monitoring),
            ("Rollback Manager", self.test_rollback_manager),
            ("Performance Monitoring", self.test_performance_monitoring),
            ("Gradual Rollout Orchestrator", self.test_gradual_rollout_orchestrator),
            ("Dashboard Creation", self.test_dashboard_creation),
            ("Database Operations", self.test_database_operations)
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            print()
        
        # Print summary
        total_tests = self.test_results["tests_passed"] + self.test_results["tests_failed"]
        success_rate = (self.test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print("=" * 60)
        print("📊 GRADUAL ROLLOUT SYSTEM TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['tests_passed']}")
        print(f"Failed: {self.test_results['tests_failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        if self.test_results["tests_failed"] == 0:
            print("🎉 All tests passed! Gradual rollout system is ready.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the issues above.")
            return False

def main():
    """Main test function"""
    tester = GradualRolloutTester()
    
    try:
        # Run all tests
        success = tester.run_all_tests()
        
        # Create test report
        with open("gradual_rollout_test_report.json", "w") as f:
            json.dump(tester.test_results, f, indent=2)
        
        print("📄 Test report saved to gradual_rollout_test_report.json")
        
        return success
        
    finally:
        # Always cleanup
        tester.cleanup()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)