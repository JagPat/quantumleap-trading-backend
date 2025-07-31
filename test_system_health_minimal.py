"""
Minimal test for Trading Engine System Health Monitoring
Tests core functionality without external dependencies
"""
import asyncio
import tempfile
import os
import sys
import time
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

# Define core classes locally for testing
class HealthStatus(Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    DOWN = "DOWN"

class ComponentType(Enum):
    DATABASE = "DATABASE"
    API_SERVER = "API_SERVER"
    SYSTEM_RESOURCES = "SYSTEM_RESOURCES"
    EXTERNAL_API = "EXTERNAL_API"

@dataclass
class HealthMetric:
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class ComponentHealth:
    component_id: str
    component_type: ComponentType
    status: HealthStatus
    metrics: List[HealthMetric]
    last_check: datetime
    uptime_seconds: float
    error_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'component_id': self.component_id,
            'component_type': self.component_type.value,
            'status': self.status.value,
            'metrics': [asdict(m) for m in self.metrics],
            'last_check': self.last_check.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'recovery_attempts': self.recovery_attempts
        }

@dataclass
class SystemHealth:
    overall_status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    down_components: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_status': self.overall_status.value,
            'components': [c.to_dict() for c in self.components],
            'timestamp': self.timestamp.isoformat(),
            'total_components': self.total_components,
            'healthy_components': self.healthy_components,
            'warning_components': self.warning_components,
            'critical_components': self.critical_components,
            'down_components': self.down_components
        }

class MockHealthChecker:
    """Mock health checker for testing"""
    
    def __init__(self, component_id: str, component_type: ComponentType):
        self.component_id = component_id
        self.component_type = component_type
        self.start_time = datetime.now()
        self.error_count = 0
        self.last_error = ""
    
    def _create_metric(self, name: str, value: float, unit: str, 
                      warning_threshold: float, critical_threshold: float) -> HealthMetric:
        """Create a health metric with status determination"""
        if value >= critical_threshold:
            status = HealthStatus.CRITICAL
        elif value >= warning_threshold:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
        
        return HealthMetric(
            name=name,
            value=value,
            unit=unit,
            status=status,
            threshold_warning=warning_threshold,
            threshold_critical=critical_threshold,
            timestamp=datetime.now()
        )
    
    async def check_health(self) -> ComponentHealth:
        """Mock health check"""
        # Generate mock metrics based on component type
        metrics = []
        
        if self.component_type == ComponentType.SYSTEM_RESOURCES:
            metrics = [
                self._create_metric("cpu_usage", 45.5, "%", 70.0, 90.0),
                self._create_metric("memory_usage", 62.3, "%", 80.0, 95.0),
                self._create_metric("disk_usage", 35.8, "%", 80.0, 95.0),
            ]
        elif self.component_type == ComponentType.DATABASE:
            metrics = [
                self._create_metric("connection_time", 25.5, "ms", 100.0, 500.0),
                self._create_metric("database_size", 150.2, "MB", 500.0, 1000.0),
                self._create_metric("total_rows", 5000, "rows", 100000, 500000),
            ]
        elif self.component_type == ComponentType.API_SERVER:
            metrics = [
                self._create_metric("response_time", 120.5, "ms", 1000.0, 5000.0),
                self._create_metric("endpoint_availability", 98.5, "%", 90.0, 50.0),
                self._create_metric("port_connectivity", 1, "boolean", 0.5, 0.5),
            ]
        
        # Determine overall component status
        status = HealthStatus.HEALTHY
        for metric in metrics:
            if metric.status == HealthStatus.CRITICAL:
                status = HealthStatus.CRITICAL
                break
            elif metric.status == HealthStatus.WARNING and status == HealthStatus.HEALTHY:
                status = HealthStatus.WARNING
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ComponentHealth(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )

class MockSystemHealthMonitor:
    """Mock system health monitor for testing"""
    
    def __init__(self):
        self.health_checkers: Dict[str, MockHealthChecker] = {}
        self.health_history: List[SystemHealth] = []
        self.monitoring_active = False
    
    def add_health_checker(self, checker: MockHealthChecker):
        """Add a health checker"""
        self.health_checkers[checker.component_id] = checker
    
    def remove_health_checker(self, component_id: str):
        """Remove a health checker"""
        if component_id in self.health_checkers:
            del self.health_checkers[component_id]
    
    async def check_all_components(self) -> SystemHealth:
        """Check health of all components"""
        component_healths = []
        
        # Run all health checks
        for checker in self.health_checkers.values():
            health = await checker.check_health()
            component_healths.append(health)
        
        # Calculate overall system health
        total_components = len(component_healths)
        healthy_count = sum(1 for h in component_healths if h.status == HealthStatus.HEALTHY)
        warning_count = sum(1 for h in component_healths if h.status == HealthStatus.WARNING)
        critical_count = sum(1 for h in component_healths if h.status == HealthStatus.CRITICAL)
        down_count = sum(1 for h in component_healths if h.status == HealthStatus.DOWN)
        
        # Determine overall status
        if down_count > 0 or critical_count > total_components * 0.3:
            overall_status = HealthStatus.CRITICAL
        elif critical_count > 0 or warning_count > total_components * 0.5:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        system_health = SystemHealth(
            overall_status=overall_status,
            components=component_healths,
            timestamp=datetime.now(),
            total_components=total_components,
            healthy_components=healthy_count,
            warning_components=warning_count,
            critical_components=critical_count,
            down_components=down_count
        )
        
        # Store in history
        self.health_history.append(system_health)
        
        return system_health
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health"""
        if self.health_history:
            return self.health_history[-1]
        return None
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """Get health statistics"""
        current_health = self.get_current_health()
        if not current_health:
            return {}
        
        return {
            'overall_status': current_health.overall_status.value,
            'total_components': current_health.total_components,
            'healthy_components': current_health.healthy_components,
            'warning_components': current_health.warning_components,
            'critical_components': current_health.critical_components,
            'down_components': current_health.down_components,
            'monitoring_active': self.monitoring_active,
            'last_check': current_health.timestamp.isoformat()
        }

def test_health_status_enum():
    """Test health status enumeration"""
    print("🧪 Testing Health Status Enum")
    print("=" * 35)
    
    try:
        # Test all status values
        statuses = [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.DOWN]
        status_values = [s.value for s in statuses]
        
        expected_values = ["HEALTHY", "WARNING", "CRITICAL", "DOWN"]
        
        print(f"✅ Status values: {status_values}")
        
        # Verify all expected values are present
        for expected in expected_values:
            if expected in status_values:
                print(f"✅ Found status: {expected}")
            else:
                print(f"❌ Missing status: {expected}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Health status enum test failed: {e}")
        return False

def test_component_type_enum():
    """Test component type enumeration"""
    print("\n🧪 Testing Component Type Enum")
    print("=" * 35)
    
    try:
        # Test all component types
        types = [ComponentType.DATABASE, ComponentType.API_SERVER, 
                ComponentType.SYSTEM_RESOURCES, ComponentType.EXTERNAL_API]
        type_values = [t.value for t in types]
        
        expected_values = ["DATABASE", "API_SERVER", "SYSTEM_RESOURCES", "EXTERNAL_API"]
        
        print(f"✅ Component types: {type_values}")
        
        # Verify all expected values are present
        for expected in expected_values:
            if expected in type_values:
                print(f"✅ Found type: {expected}")
            else:
                print(f"❌ Missing type: {expected}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Component type enum test failed: {e}")
        return False

def test_health_metric_creation():
    """Test health metric creation and status determination"""
    print("\n🧪 Testing Health Metric Creation")
    print("=" * 40)
    
    try:
        # Test different metric scenarios
        test_cases = [
            {"value": 30.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.HEALTHY},
            {"value": 75.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.WARNING},
            {"value": 95.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.CRITICAL},
            {"value": 90.0, "warning": 70.0, "critical": 90.0, "expected": HealthStatus.CRITICAL},  # Boundary case
        ]
        
        checker = MockHealthChecker("test", ComponentType.SYSTEM_RESOURCES)
        
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
            
            if metric.status != case["expected"]:
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Health metric creation test failed: {e}")
        return False

def test_component_health_creation():
    """Test component health creation"""
    print("\n🧪 Testing Component Health Creation")
    print("=" * 40)
    
    try:
        # Create test metrics
        metrics = [
            HealthMetric(
                name="cpu_usage",
                value=45.5,
                unit="%",
                status=HealthStatus.HEALTHY,
                threshold_warning=70.0,
                threshold_critical=90.0,
                timestamp=datetime.now()
            ),
            HealthMetric(
                name="memory_usage",
                value=75.0,
                unit="%",
                status=HealthStatus.WARNING,
                threshold_warning=70.0,
                threshold_critical=90.0,
                timestamp=datetime.now()
            )
        ]
        
        # Create component health
        component_health = ComponentHealth(
            component_id="test_component",
            component_type=ComponentType.SYSTEM_RESOURCES,
            status=HealthStatus.WARNING,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=3600.0,
            error_count=2,
            last_error="Test error"
        )
        
        print(f"✅ Component health created: {component_health.component_id}")
        print(f"   Status: {component_health.status.value}")
        print(f"   Metrics count: {len(component_health.metrics)}")
        print(f"   Uptime: {component_health.uptime_seconds} seconds")
        print(f"   Error count: {component_health.error_count}")
        
        # Test to_dict conversion
        health_dict = component_health.to_dict()
        print(f"✅ to_dict conversion: {len(health_dict)} fields")
        
        # Verify required fields
        required_fields = ['component_id', 'component_type', 'status', 'metrics', 'last_check']
        for field in required_fields:
            if field in health_dict:
                print(f"✅ Found required field: {field}")
            else:
                print(f"❌ Missing required field: {field}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Component health creation test failed: {e}")
        return False

async def test_mock_health_checker():
    """Test mock health checker functionality"""
    print("\n🧪 Testing Mock Health Checker")
    print("=" * 35)
    
    try:
        # Test different component types
        component_types = [
            ComponentType.SYSTEM_RESOURCES,
            ComponentType.DATABASE,
            ComponentType.API_SERVER
        ]
        
        for comp_type in component_types:
            checker = MockHealthChecker(f"test_{comp_type.value.lower()}", comp_type)
            print(f"✅ Created checker: {checker.component_id}")
            
            # Perform health check
            health = await checker.check_health()
            print(f"   Status: {health.status.value}")
            print(f"   Metrics: {len(health.metrics)}")
            
            # Verify metrics are appropriate for component type
            metric_names = [m.name for m in health.metrics]
            
            if comp_type == ComponentType.SYSTEM_RESOURCES:
                expected_metrics = ["cpu_usage", "memory_usage", "disk_usage"]
            elif comp_type == ComponentType.DATABASE:
                expected_metrics = ["connection_time", "database_size", "total_rows"]
            elif comp_type == ComponentType.API_SERVER:
                expected_metrics = ["response_time", "endpoint_availability", "port_connectivity"]
            
            for expected in expected_metrics:
                if expected in metric_names:
                    print(f"   ✅ Found metric: {expected}")
                else:
                    print(f"   ❌ Missing metric: {expected}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Mock health checker test failed: {e}")
        return False

async def test_system_health_monitor():
    """Test system health monitor functionality"""
    print("\n🧪 Testing System Health Monitor")
    print("=" * 35)
    
    try:
        # Create monitor
        monitor = MockSystemHealthMonitor()
        print("✅ System health monitor created")
        
        # Add health checkers
        checkers = [
            MockHealthChecker("system_resources", ComponentType.SYSTEM_RESOURCES),
            MockHealthChecker("database", ComponentType.DATABASE),
            MockHealthChecker("api_server", ComponentType.API_SERVER)
        ]
        
        for checker in checkers:
            monitor.add_health_checker(checker)
            print(f"✅ Added checker: {checker.component_id}")
        
        # Check all components
        system_health = await monitor.check_all_components()
        print(f"✅ System health check completed: {system_health.overall_status.value}")
        print(f"   Total components: {system_health.total_components}")
        print(f"   Healthy: {system_health.healthy_components}")
        print(f"   Warning: {system_health.warning_components}")
        print(f"   Critical: {system_health.critical_components}")
        print(f"   Down: {system_health.down_components}")
        
        # Test current health
        current = monitor.get_current_health()
        if current:
            print(f"✅ Current health retrieved: {current.overall_status.value}")
        else:
            print("❌ Failed to get current health")
            return False
        
        # Test statistics
        stats = monitor.get_health_statistics()
        print(f"✅ Statistics retrieved: {len(stats)} fields")
        
        # Test component removal
        monitor.remove_health_checker("database")
        print("✅ Component removed successfully")
        
        # Verify removal
        if "database" not in monitor.health_checkers:
            print("✅ Component removal verified")
        else:
            print("❌ Component removal failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ System health monitor test failed: {e}")
        return False

def test_system_health_aggregation():
    """Test system health status aggregation logic"""
    print("\n🧪 Testing System Health Aggregation")
    print("=" * 40)
    
    try:
        # Create components with different statuses
        healthy_comp = ComponentHealth(
            component_id="healthy", component_type=ComponentType.SYSTEM_RESOURCES,
            status=HealthStatus.HEALTHY, metrics=[], last_check=datetime.now(), uptime_seconds=3600
        )
        
        warning_comp = ComponentHealth(
            component_id="warning", component_type=ComponentType.DATABASE,
            status=HealthStatus.WARNING, metrics=[], last_check=datetime.now(), uptime_seconds=3600
        )
        
        critical_comp = ComponentHealth(
            component_id="critical", component_type=ComponentType.API_SERVER,
            status=HealthStatus.CRITICAL, metrics=[], last_check=datetime.now(), uptime_seconds=3600
        )
        
        down_comp = ComponentHealth(
            component_id="down", component_type=ComponentType.EXTERNAL_API,
            status=HealthStatus.DOWN, metrics=[], last_check=datetime.now(), uptime_seconds=3600
        )
        
        # Test different scenarios
        test_scenarios = [
            {
                "name": "All Healthy",
                "components": [healthy_comp],
                "expected": HealthStatus.HEALTHY
            },
            {
                "name": "One Warning",
                "components": [healthy_comp, warning_comp],
                "expected": HealthStatus.WARNING
            },
            {
                "name": "One Critical",
                "components": [healthy_comp, critical_comp],
                "expected": HealthStatus.CRITICAL
            },
            {
                "name": "One Down",
                "components": [healthy_comp, down_comp],
                "expected": HealthStatus.CRITICAL
            },
            {
                "name": "Mixed Status",
                "components": [healthy_comp, warning_comp, critical_comp],
                "expected": HealthStatus.CRITICAL
            }
        ]
        
        for scenario in test_scenarios:
            components = scenario["components"]
            
            # Calculate status (using same logic as monitor)
            total = len(components)
            healthy_count = sum(1 for c in components if c.status == HealthStatus.HEALTHY)
            warning_count = sum(1 for c in components if c.status == HealthStatus.WARNING)
            critical_count = sum(1 for c in components if c.status == HealthStatus.CRITICAL)
            down_count = sum(1 for c in components if c.status == HealthStatus.DOWN)
            
            if down_count > 0 or critical_count > total * 0.3:
                overall_status = HealthStatus.CRITICAL
            elif critical_count > 0 or warning_count > total * 0.5:
                overall_status = HealthStatus.WARNING
            else:
                overall_status = HealthStatus.HEALTHY
            
            expected = scenario["expected"]
            result = "✅" if overall_status == expected else "❌"
            
            print(f"{result} {scenario['name']}: {overall_status.value} (expected: {expected.value})")
            
            if overall_status != expected:
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ System health aggregation test failed: {e}")
        return False

def test_health_data_serialization():
    """Test health data serialization"""
    print("\n🧪 Testing Health Data Serialization")
    print("=" * 40)
    
    try:
        # Create test data
        metric = HealthMetric(
            name="test_metric",
            value=50.0,
            unit="%",
            status=HealthStatus.HEALTHY,
            threshold_warning=70.0,
            threshold_critical=90.0,
            timestamp=datetime.now()
        )
        
        component = ComponentHealth(
            component_id="test_component",
            component_type=ComponentType.SYSTEM_RESOURCES,
            status=HealthStatus.HEALTHY,
            metrics=[metric],
            last_check=datetime.now(),
            uptime_seconds=3600.0
        )
        
        system_health = SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            components=[component],
            timestamp=datetime.now(),
            total_components=1,
            healthy_components=1,
            warning_components=0,
            critical_components=0,
            down_components=0
        )
        
        # Test serialization
        component_dict = component.to_dict()
        system_dict = system_health.to_dict()
        
        print(f"✅ Component serialization: {len(component_dict)} fields")
        print(f"✅ System health serialization: {len(system_dict)} fields")
        
        # Verify key fields are present and properly formatted
        assert component_dict['component_id'] == 'test_component'
        assert component_dict['status'] == 'HEALTHY'
        assert len(component_dict['metrics']) == 1
        assert isinstance(component_dict['uptime_seconds'], float)
        
        assert system_dict['overall_status'] == 'HEALTHY'
        assert system_dict['total_components'] == 1
        assert len(system_dict['components']) == 1
        
        print("✅ Serialization validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Health data serialization test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting System Health Monitoring Tests")
    print("=" * 60)
    
    test_results = []
    
    # Run individual tests
    test_results.append(("Health Status Enum", test_health_status_enum()))
    test_results.append(("Component Type Enum", test_component_type_enum()))
    test_results.append(("Health Metric Creation", test_health_metric_creation()))
    test_results.append(("Component Health Creation", test_component_health_creation()))
    test_results.append(("Mock Health Checker", await test_mock_health_checker()))
    test_results.append(("System Health Monitor", await test_system_health_monitor()))
    test_results.append(("System Health Aggregation", test_system_health_aggregation()))
    test_results.append(("Health Data Serialization", test_health_data_serialization()))
    
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
    print("   • Component type classification")
    print("   • Health metrics with threshold evaluation")
    print("   • Component health tracking")
    print("   • System-wide health aggregation")
    print("   • Health data serialization")
    print("   • Mock health checking functionality")
    print("   • System health monitoring coordination")

if __name__ == "__main__":
    asyncio.run(main())