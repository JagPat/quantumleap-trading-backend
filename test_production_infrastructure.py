#!/usr/bin/env python3
"""
Production Infrastructure Testing Suite
Tests all deployed components and configurations
"""

import os
import sys
import json
import sqlite3
import subprocess
import time
import requests
from pathlib import Path
from datetime import datetime

class ProductionInfrastructureTest:
    """Test suite for production infrastructure"""
    
    def __init__(self):
        self.test_results = {
            "test_date": datetime.now().isoformat(),
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
    
    def test_configuration_files(self):
        """Test that all configuration files exist"""
        required_files = [
            "production_config.json",
            "production_main.py",
            "database_backup.py",
            "setup_backup_schedule.sh",
            "monitoring/monitoring_config.json",
            "monitoring/production_monitor.py"
        ]
        
        for file_path in required_files:
            if not Path(file_path).exists():
                raise Exception(f"Missing configuration file: {file_path}")
        
        return True
    
    def test_database_schema(self):
        """Test production database schema"""
        conn = sqlite3.connect("production_trading.db")
        cursor = conn.cursor()
        
        # Check required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            "orders", "positions", "strategies", "executions",
            "events", "performance_metrics", "system_health"
        ]
        
        for table in required_tables:
            if table not in tables:
                conn.close()
                raise Exception(f"Missing required table: {table}")
        
        # Test basic operations
        cursor.execute("INSERT INTO system_health (id, component, status, checked_at) VALUES (?, ?, ?, ?)",
                      ("test_1", "test_component", "healthy", datetime.now().isoformat()))
        conn.commit()
        
        cursor.execute("SELECT * FROM system_health WHERE id = ?", ("test_1",))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            raise Exception("Database insert/select test failed")
        
        # Cleanup test data
        cursor.execute("DELETE FROM system_health WHERE id = ?", ("test_1",))
        conn.commit()
        conn.close()
        
        return True
    
    def test_backup_system(self):
        """Test database backup functionality"""
        # Run backup
        result = subprocess.run([sys.executable, "database_backup.py"], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Backup script failed: {result.stderr}")
        
        # Check if backup was created
        backup_dir = Path("backups")
        backup_files = list(backup_dir.glob("trading_db_backup_*.db.gz"))
        
        if not backup_files:
            raise Exception("No backup files found")
        
        # Check if backup is recent (within last minute)
        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        backup_age = time.time() - latest_backup.stat().st_mtime
        
        if backup_age > 120:  # 2 minutes
            raise Exception(f"Latest backup is too old: {backup_age} seconds")
        
        return True
    
    def test_monitoring_configuration(self):
        """Test monitoring system configuration"""
        config_path = Path("monitoring/monitoring_config.json")
        
        with open(config_path) as f:
            config = json.load(f)
        
        # Check required configuration sections
        required_sections = ["health_checks", "performance_metrics", "alerts"]
        
        for section in required_sections:
            if section not in config:
                raise Exception(f"Missing monitoring configuration section: {section}")
        
        # Check health check configuration
        health_checks = config["health_checks"]
        required_checks = ["database", "trading_engine", "ai_engine"]
        
        for check in required_checks:
            if check not in health_checks:
                raise Exception(f"Missing health check configuration: {check}")
        
        return True
    
    def test_production_main_syntax(self):
        """Test production main file syntax"""
        result = subprocess.run([sys.executable, "-m", "py_compile", "production_main.py"],
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Production main syntax error: {result.stderr}")
        
        return True
    
    def test_file_permissions(self):
        """Test that executable files have correct permissions"""
        executable_files = [
            "database_backup.py",
            "setup_backup_schedule.sh",
            "monitoring/production_monitor.py"
        ]
        
        for file_path in executable_files:
            file_stat = Path(file_path).stat()
            # Check if file is executable (owner execute bit)
            if not (file_stat.st_mode & 0o100):
                raise Exception(f"File not executable: {file_path}")
        
        return True
    
    def test_directory_structure(self):
        """Test that required directories exist"""
        required_dirs = ["backups", "monitoring"]
        
        for dir_path in required_dirs:
            if not Path(dir_path).is_dir():
                raise Exception(f"Missing required directory: {dir_path}")
        
        return True
    
    def test_configuration_validity(self):
        """Test that configuration files are valid JSON"""
        json_files = [
            "production_config.json",
            "monitoring/monitoring_config.json"
        ]
        
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in {json_file}: {e}")
        
        return True
    
    def run_all_tests(self):
        """Run all infrastructure tests"""
        print("🚀 Starting Production Infrastructure Tests...\n")
        
        # Define all tests
        tests = [
            ("Configuration Files", self.test_configuration_files),
            ("Database Schema", self.test_database_schema),
            ("Backup System", self.test_backup_system),
            ("Monitoring Configuration", self.test_monitoring_configuration),
            ("Production Main Syntax", self.test_production_main_syntax),
            ("File Permissions", self.test_file_permissions),
            ("Directory Structure", self.test_directory_structure),
            ("Configuration Validity", self.test_configuration_validity)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            print()
        
        # Print summary
        total_tests = self.test_results["tests_passed"] + self.test_results["tests_failed"]
        success_rate = (self.test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print("=" * 60)
        print("📊 PRODUCTION INFRASTRUCTURE TEST RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.test_results['tests_passed']}")
        print(f"Failed: {self.test_results['tests_failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        if self.test_results["tests_failed"] == 0:
            print("🎉 All tests passed! Production infrastructure is ready.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the issues above.")
            return False
    
    def create_test_report(self):
        """Create detailed test report"""
        with open("PRODUCTION_INFRASTRUCTURE_TEST_REPORT.md", "w") as f:
            f.write("# Production Infrastructure Test Report\n\n")
            f.write(f"**Test Date:** {self.test_results['test_date']}\n")
            f.write(f"**Tests Passed:** {self.test_results['tests_passed']}\n")
            f.write(f"**Tests Failed:** {self.test_results['tests_failed']}\n\n")
            
            f.write("## Test Results\n\n")
            
            for test in self.test_results["test_details"]:
                status_emoji = "✅" if test["status"] == "PASSED" else "❌"
                f.write(f"### {status_emoji} {test['test']}\n")
                f.write(f"**Status:** {test['status']}\n")
                f.write(f"**Message:** {test['message']}\n\n")
            
            if self.test_results["tests_failed"] == 0:
                f.write("## Summary\n\n")
                f.write("🎉 **All tests passed!** The production infrastructure is ready for deployment.\n\n")
                f.write("### Next Steps\n")
                f.write("- Deploy to Railway production environment\n")
                f.write("- Configure monitoring alerts\n")
                f.write("- Set up automated backup schedule\n")
                f.write("- Configure SSL certificates\n")
                f.write("- Perform load testing\n")
            else:
                f.write("## Issues Found\n\n")
                f.write("⚠️ **Some tests failed.** Please address the following issues:\n\n")
                
                failed_tests = [t for t in self.test_results["test_details"] if t["status"] != "PASSED"]
                for test in failed_tests:
                    f.write(f"- **{test['test']}:** {test['message']}\n")
        
        print("📄 Test report saved to PRODUCTION_INFRASTRUCTURE_TEST_REPORT.md")

def main():
    """Main test function"""
    tester = ProductionInfrastructureTest()
    
    # Run all tests
    success = tester.run_all_tests()
    
    # Create test report
    tester.create_test_report()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)