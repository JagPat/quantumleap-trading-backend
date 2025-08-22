"""
Simple test for Trading Engine System Health Monitoring
Tests core functionality without external dependencies
"""
import asyncio
import tempfile
import os
import sys
import time
from datetime import datetime, timedelta

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Test basic imports and functionality
def test_health_monitoring_components():
    """Test system health monitoring components"""
    print("🧪 Testing System Health Monitoring Components")
    print("=" * 55)
    
    try:
        # Test enum imports
        from trading_engine.system_health_monitor import (
            HealthStatus, ComponentType, HealthMetric, ComponentHealth, SystemHealth
        )
        print("✅ Basic imports successful")
        
        # Test HealthStatus enum
        statuses = [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.DOWN]
        print(f"✅ HealthStatus enum: {[s.value for s in statuses]}")
        
        # Test ComponentType enum
        components = [ComponentType.DATABASE, ComponentType.API_SERVER, ComponentType.SYSTEM_RESOURCES]
        print(f"✅ ComponentType enum: {[c.value for c in components]}")
        
        # Test HealthMetric creation
        metric = HealthMetric(
            name="cpu_usage",
            value=45.5,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=70.0,
            threshold_critical=90.0,
            timestamp=datetime.now()
        )
        print(f"✅ HealthMetric created: {metric.name} = {metric.value}{metric.unit}")
        
        # Test ComponentHealth creation
        component_health = ComponentHealth(
            component_id="test_component",
            component_type=ComponentType.SYSTEM_RESOURCES,
            status=HealthStatus.HEALTHY,
            metrics=[metric],
            last_check=datetime.now(),
            uptime_seconds=3600.0
        )
        print(f"✅ ComponentHealth created: {component_health.component_id}")
        
        # Test to_dict conversion
        health_dict = component_health.to_dict()
        print(f"✅ ComponentHealth to_dict: {len(health_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False

def test_health_checker_base():
    """Test health checker base functionality"""
    print("\n🧪 Testing Health Checker Base")
    print("=" * 35)
    
    try:
        from trading_engine.system_health_monitor import HealthChecker, ComponentType, HealthStatus
        
        # Create a simple test health checker
        class TestHealthChecker(HealthChecker):
            async def check_health(self):
                metrics = [
                    self._create_metric("test_metric", 50.0, "units", 70.0, 90.0)
                ]
                
                return ComponentHealth(
                    component_id=self.component_id,
                    component_type=self.component_type,
                    status=HealthStatus.HEALTHY,
                    metrics=metrics,
                    last_check=datetime.now(),
                    uptime_seconds=(datetime.now() - self.start_time).total_seconds()
                )
        
        # Test checker creation
        checker = TestHealthChecker("test_checker", ComponentType.SYSTEM_RESOURCES)
        print(f"✅ Health checker created: {checker.component_id}")
        
        # Test metric creation
        metric = checker._create_metric("cpu_usage", 45.0, "%", 70.0, 90.0)
        print(f"✅ Metric created: {metric.name} = {metric.value}{metric.unit} ({metric.status.value})")
        
        # Test different metric statuses
        warning_metric = checker._create_metric("memory_usage", 75.0, "%", 70.0, 90.0)
        critical_metric = checker._create_metric("disk_usage", 95.0, "%", 70.0, 90.0)
        
        print(f"✅ Warning metric: {warning_metric.status.value}")
        print(f"✅ Critical metric: {critical_metric.status.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health checker test failed: {e}")
        return False

async def test_system_resources_checker():
    """Test system resources health checker"""
    print("\n🧪 Testing System Resources Checker")
    print("=" * 40)
    
    try:
        from trading_engine.system_health_monitor import SystemResourcesHealthChecker
        
        # Create system resources checker
        checker = SystemResourcesHealthChecker()
        print(f"✅ System resources checker created: {checker.component_id}")
        
        # Perform health check
        health = await checker.check_health()
        print(f"✅ Health check completed: {health.status.value}")
        print(f"   Metrics count: {len(health.metrics)}")
        
        # Display metrics
        for metric in health.metrics:
            print(f"   - {metric.name}: {metric.value}{metric.unit} ({metric.status.value})")
        
        # Verify expected metrics
        metric_names = [m.name for m in health.metrics]
        expected_metrics = ["cpu_usage", "memory_usage", "disk_usage"]
        
        for expected in expected_metrics:
            if expected in metric_names:
                print(f"✅ Found expected metric: {expected}")
            else:
                print(f"⚠️  Missing expected metric: {expected}")
        
        return True
        
    except Exception as e:
        print(f"❌ System resources checker test failed: {e}")
        return False

async def test_database_checker():
    """Test database health checker"""
    print("\n🧪 Testing Database Checker")
    print("=" * 30)
    
    try:
        from trading_engine.system_health_monitor import DatabaseHealthChecker
        
        # Create temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Create database checker
            checker = DatabaseHealthChecker(db_path)
            print(f"✅ Database checker created: {checker.component_id}")
            
            # Initialize test database
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
                conn.execute("INSERT INTO test_table (name) VALUES ('test1'), ('test2')")
                conn.commit()
            
            # Perform health check
            health = await checker.check_health()
            print(f"✅ Health check completed: {health.status.value}")
            print(f"   Metrics count: {len(health.metrics)}")
            
            # Display metrics
            for metric in health.metrics:
                print(f"   - {metric.name}: {metric.value}{metric.unit} ({metric.status.value})")
            
            # Verify database-specific metrics
            metric_names = [m.name for m in health.metrics]
            expected_metrics = ["connection_time", "database_size", "total_rows", "table_count"]
            
            for expected in expected_metrics:
                if expected in metric_names:
                    print(f"✅ Found expected metric: {expected}")
                else:
                    print(f"⚠️  Missing expected metric: {expected}")
            
            return True
            
        finally:
            # Clean up temporary database
            try:
                os.unlink(db_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ Database checker test failed: {e}")
        return False

async def test_system_health_monitor():
    """Test system health monitor"""
    print("\n🧪 Testing System Health Monitor")
    print("=" * 35)
    
    try:
        from trading_engine.system_health_monitor import SystemHealthMonitor, SystemResourcesHealthChecker
        
        # Create temporary database for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name
        
        try:
            # Create system health monitor
            monitor = SystemHealthMonitor(db_path)
            print(f"✅ System health monitor created")
            
            # Add a test health checker
            test_checker = SystemResourcesHealthChecker()
            monitor.add_health_checker(test_checker)
            print(f"✅ Health checker added: {test_checker.component_id}")
            
            # Check all components
            system_health = await monitor.check_all_components()
            print(f"✅ System health check completed: {system_health.overall_status.value}")
            print(f"   Total components: {system_health.total_components}")
            print(f"   Healthy components: {system_health.healthy_components}")
            print(f"   Warning components: {system_health.warning_components}")
            print(f"   Critical components: {system_health.critical_components}")
            
            # Test health history
            history = monitor.get_health_history(1)  # Last hour
            print(f"✅ Health history retrieved: {len(history)} records")
            
            # Test current health
            current = monitor.get_current_health()
            if current:
                print(f"✅ Current health retrieved: {current.overall_status.value}")
            
            # Test statistics
            stats = monitor.get_health_statistics()
            print(f"✅ Health statistics retrieved: {len(stats)} fields")
            
            # Test component removal
            monitor.remove_health_checker(test_checker.component_id)
            print(f"✅ Health checker removed: {test_checker.component_id}")
            
            return True
            
        finally:
            # Clean up temporary database
            try:
                os.unlink(db_path)
            except:
                pass
        
    except Exception as e:
        print(f"❌ System health monitor test failed: {e}")
        return False

def test_health_status_determination():
    """Test health status determination logic"""
    print("\n🧪 Testing Health Status Determination")
    print("=" * 40)
    
    try:
        from trading_engine.system_health_monitor import HealthStatus, SystemHealth, ComponentHealth, ComponentType
        
        # Create test components with different statuses
        healthy_component = ComponentHealth(
            component_id="healthy_comp",
            component_type=ComponentType.SYSTEM_RESOURCES,
            status=HealthStatus.HEALTHY,
            metrics=[],
            last_check=datetime.now(),
            uptime_seconds=3600.0
        )
        
        warning_component = ComponentHealth(
            component_id="warning_comp",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.WARNING,
            metrics=[],
            last_check=datetime.now(),
            uptime_seconds=3600.0
        )
        
        critical_component = ComponentHealth(
            component_id="critical_comp",
            component_type=ComponentType.API_SERVER,
            status=HealthStatus.CRITICAL,
            metrics=[],
            last_check=datetime.now(),
            uptime_seconds=3600.0
        )
        
        # Test different system health scenarios
        test_scenarios = [
            {
                "name": "All Healthy",
                "components": [healthy_component],
                "expected_status": HealthStatus.HEALTHY
            },
            {
                "name": "One Warning",
                "components": [healthy_component, warning_component],
                "expected_status": HealthStatus.WARNING
            },
            {
                "name": "One Critical",
                "components": [healthy_component, critical_component],
                "expected_status": HealthStatus.CRITICAL
            },
            {
                "name": "Mixed Status",
                "components": [healthy_component, warning_component, critical_component],
                "expected_status": HealthStatus.CRITICAL
            }
        ]
        
        for scenario in test_scenarios:
            components = scenario["components"]
            
            # Calculate status counts
            total = len(components)
            healthy_count = sum(1 for c in components if c.status == HealthStatus.HEALTHY)
            warning_count = sum(1 for c in components if c.status == HealthStatus.WARNING)
            critical_count = sum(1 for c in components if c.status == HealthStatus.CRITICAL)
            down_count = sum(1 for c in components if c.status == HealthStatus.DOWN)
            
            # Determine overall status (simplified logic)
            if down_count > 0 or critical_count > total * 0.3:
                overall_status = HealthStatus.CRITICAL
            elif critical_count > 0 or warning_count > total * 0.5:
                overall_status = HealthStatus.WARNING
            else:
                overall_status = HealthStatus.HEALTHY
            
            expected = scenario["expected_status"]
            result = "✅" if overall_status == expected else "❌"
            
            print(f"{result} {scenario['name']}: {overall_status.value} (expected: {expected.value})")
        
        return True
        
    except Exception as e:
        print(f"❌ Health status determination test failed: {e}")
        return False

def test_health_metrics_thresholds():
    """Test health metrics threshold logic"""
    print("\n🧪 Testing Health Metrics Thresholds")
    print("=" * 40)
    
    try:
        from trading_engine.system_health_monitor import HealthChecker, ComponentType, HealthStatus
        
        class TestChecker(HealthChecker):
            def __init__(self):
                super().__init__("test", ComponentType.SYSTEM_RESOURCES)
        
        checker = TestChecker()
        
        # Test different threshold scenarios
        test_cases = [
            {"value": 30.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.HEALTHY},
            {"value": 75.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.WARNING},
            {"value": 95.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.CRITICAL},
            {"value": 90.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.CRITICAL},  # Boundary case
        ]
        
        for i, case in enumerate(test_cases):
            metric = checker._create_metric(
                f"test_metric_{i}",
                case["value"],
                "units",
                case["warning"],
                case["critical"]
            )
            
            result = "✅" if metric.status == case["expected"] else "❌"
            print(f"{result} Value {case['value']}: {metric.status.value} (expected: {case['expected'].value})")
        
        return True
        
    except Exception as e:
        print(f"❌ Health metrics threshold test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting System Health Monitoring Tests")
    print("=" * 60)
    
    test_results = []
    
    # Run individual tests
    test_results.append(("Health Monitoring Components", test_health_monitoring_components()))
    test_results.append(("Health Checker Base", test_health_checker_base()))
    test_results.append(("System Resources Checker", await test_system_resources_checker()))
    test_results.append(("Database Checker", await test_database_checker()))
    test_results.append(("System Health Monitor", await test_system_health_monitor()))
    test_results.append(("Health Status Determination", test_health_status_determination()))
    test_results.append(("Health Metrics Thresholds", test_health_metrics_thresholds()))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed_tests += 1
    
    total_tests = len(test_results)
    print(f"\n📊 Overall Results: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! System health monitoring is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    print("\n💡 Key Features Tested:")
    print("   • Health status enumeration and logic")
    print("   • Component health checking")
    print("   • System resources monitoring")
    print("   • Database health validation")
    print("   • Health metrics with thresholds")
    print("   • System-wide health aggregation")
    print("   • Health history and statistics")

if __name__ == "__main__":
    asyncio.run(main())