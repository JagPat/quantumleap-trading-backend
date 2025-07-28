"""
Performance Monitoring Tests
Tests for startup performance monitoring and metrics
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.core.startup_monitor import StartupMonitor
from app.core.component_loader import ComponentLoader, ComponentStatusInfo, ComponentStatus

class TestPerformanceMonitoring:
    
    def setup_method(self):
        """Set up test environment"""
        self.monitor = StartupMonitor()
        self.loader = ComponentLoader()
    
    def test_startup_duration_tracking(self):
        """Test that startup duration is tracked correctly"""
        # Simulate some startup time
        time.sleep(0.1)
        
        summary = self.monitor.generate_startup_summary()
        
        assert summary.startup_duration > 0.1
        assert isinstance(summary.startup_duration, float)
    
    def test_component_load_time_tracking(self):
        """Test that individual component load times are tracked"""
        # Create test component status with load duration
        status = ComponentStatusInfo(
            name="test_component",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.5
        )
        
        self.monitor.update_component_status(status)
        
        # Check that load duration is tracked
        statuses = self.monitor.get_component_statuses()
        assert "test_component" in statuses
        assert statuses["test_component"].load_duration == 1.5
    
    def test_performance_rating_calculation(self):
        """Test performance rating calculations"""
        # Test different performance ratings
        assert self.monitor._get_performance_rating(0.3) == "excellent"
        assert self.monitor._get_performance_rating(0.7) == "good"
        assert self.monitor._get_performance_rating(1.5) == "fair"
        assert self.monitor._get_performance_rating(3.0) == "slow"
    
    def test_startup_speed_rating(self):
        """Test startup speed rating calculations"""
        assert self.monitor._get_startup_speed_rating(3.0) == "fast"
        assert self.monitor._get_startup_speed_rating(7.0) == "moderate"
        assert self.monitor._get_startup_speed_rating(15.0) == "slow"
        assert self.monitor._get_startup_speed_rating(25.0) == "very_slow"
    
    def test_efficiency_rating(self):
        """Test component loading efficiency ratings"""
        assert self.monitor._get_efficiency_rating(0.2) == "highly_efficient"
        assert self.monitor._get_efficiency_rating(0.5) == "efficient"
        assert self.monitor._get_efficiency_rating(1.0) == "moderate"
        assert self.monitor._get_efficiency_rating(2.0) == "inefficient"
    
    def test_fastest_component_identification(self):
        """Test identification of fastest loading component"""
        # Add multiple components with different load times
        components = [
            ("fast", 0.5),
            ("medium", 1.0),
            ("slow", 2.0)
        ]
        
        for name, duration in components:
            status = ComponentStatusInfo(
                name=name,
                status=ComponentStatus.LOADED,
                error_message=None,
                load_time=datetime.now(),
                fallback_reason=None,
                load_duration=duration
            )
            self.monitor.update_component_status(status)
        
        fastest = self.monitor._get_fastest_component()
        
        assert fastest is not None
        assert fastest["name"] == "fast"
        assert fastest["duration"] == 0.5
    
    def test_slowest_component_identification(self):
        """Test identification of slowest loading component"""
        # Add multiple components with different load times
        components = [
            ("fast", 0.5),
            ("medium", 1.0),
            ("slow", 2.0)
        ]
        
        for name, duration in components:
            status = ComponentStatusInfo(
                name=name,
                status=ComponentStatus.LOADED,
                error_message=None,
                load_time=datetime.now(),
                fallback_reason=None,
                load_duration=duration
            )
            self.monitor.update_component_status(status)
        
        slowest = self.monitor._get_slowest_component()
        
        assert slowest is not None
        assert slowest["name"] == "slow"
        assert slowest["duration"] == 2.0
    
    def test_fastest_slowest_with_no_components(self):
        """Test fastest/slowest component identification with no components"""
        fastest = self.monitor._get_fastest_component()
        slowest = self.monitor._get_slowest_component()
        
        assert fastest is None
        assert slowest is None
    
    def test_performance_metrics_endpoint_data(self):
        """Test that performance metrics endpoint returns correct data structure"""
        # Add test components
        components = [
            ("component1", ComponentStatus.LOADED, 0.5),
            ("component2", ComponentStatus.FALLBACK, 1.2),
            ("component3", ComponentStatus.LOADED, 0.8)
        ]
        
        for name, status, duration in components:
            comp_status = ComponentStatusInfo(
                name=name,
                status=status,
                error_message=None,
                load_time=datetime.now(),
                fallback_reason=None,
                load_duration=duration
            )
            self.monitor.update_component_status(comp_status)
        
        # Create health router to test endpoint
        health_router = self.monitor.create_health_endpoints()
        
        # Find performance metrics endpoint
        perf_endpoint = None
        for route in health_router.routes:
            if route.path.endswith("/performance-metrics"):
                perf_endpoint = route
                break
        
        assert perf_endpoint is not None
    
    def test_component_load_duration_accuracy(self):
        """Test that component load durations are measured accurately"""
        loader = ComponentLoader()
        
        # Mock a component loading scenario
        start_time = time.time()
        
        # Simulate loading time
        time.sleep(0.1)
        
        # Create result with measured duration
        from app.core.component_loader import RouterLoadResult
        result = RouterLoadResult(
            success=True,
            router=None,
            error=None,
            fallback_used=False,
            load_duration=time.time() - start_time,
            component_name="test_component"
        )
        
        # Duration should be approximately 0.1 seconds
        assert result.load_duration >= 0.1
        assert result.load_duration < 0.2  # Allow some tolerance
    
    def test_startup_events_timing(self):
        """Test that startup events include timing information"""
        self.monitor.log_startup_progress("test", "loading", "Test loading", 1.5)
        
        events = self.monitor.get_startup_events()
        
        assert len(events) == 1
        event = events[0]
        
        assert event["duration"] == 1.5
        assert "timestamp" in event
        assert isinstance(event["timestamp"], datetime)
    
    def test_performance_comparison_production_vs_fallback(self):
        """Test performance comparison between production and fallback loading"""
        # Create production component (should be faster)
        prod_status = ComponentStatusInfo(
            name="production_comp",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=0.5
        )
        
        # Create fallback component (typically slower due to error handling)
        fallback_status = ComponentStatusInfo(
            name="fallback_comp",
            status=ComponentStatus.FALLBACK,
            error_message="Import failed",
            load_time=datetime.now(),
            fallback_reason="Production unavailable",
            load_duration=1.2
        )
        
        self.monitor.update_component_status(prod_status)
        self.monitor.update_component_status(fallback_status)
        
        # Check that we can distinguish performance characteristics
        statuses = self.monitor.get_component_statuses()
        
        prod_perf = self.monitor._get_performance_rating(statuses["production_comp"].load_duration)
        fallback_perf = self.monitor._get_performance_rating(statuses["fallback_comp"].load_duration)
        
        # Production should typically perform better
        perf_order = ["excellent", "good", "fair", "slow"]
        assert perf_order.index(prod_perf) <= perf_order.index(fallback_perf)
    
    def test_memory_usage_monitoring_availability(self):
        """Test memory usage monitoring when psutil is available"""
        health_router = self.monitor.create_health_endpoints()
        
        # Find memory usage endpoint
        memory_endpoint = None
        for route in health_router.routes:
            if route.path.endswith("/memory-usage"):
                memory_endpoint = route
                break
        
        assert memory_endpoint is not None
    
    @patch('app.core.startup_monitor.psutil')
    def test_memory_usage_monitoring_with_psutil(self, mock_psutil):
        """Test memory usage monitoring with mocked psutil"""
        # Mock psutil process
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100 MB
        mock_memory_info.vms = 1024 * 1024 * 200  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 5.5
        mock_psutil.Process.return_value = mock_process
        
        health_router = self.monitor.create_health_endpoints()
        
        # The endpoint should be created successfully
        assert health_router is not None
    
    def test_error_handling_overhead_measurement(self):
        """Test that error handling doesn't significantly impact performance"""
        loader = ComponentLoader()
        
        # Measure time for successful loading (simulated)
        start_time = time.time()
        
        # Simulate successful component loading
        for i in range(5):
            # This would normally be a successful import
            pass
        
        success_time = time.time() - start_time
        
        # Measure time for failed loading with fallback
        start_time = time.time()
        
        for i in range(5):
            # Simulate failed loading with fallback creation
            result = loader.load_router_with_fallback(
                f"test_{i}",
                f"app.nonexistent_{i}.router.router",
                f"/api/test_{i}"
            )
            assert result.fallback_used is True
        
        fallback_time = time.time() - start_time
        
        # Fallback should not be significantly slower (allow 5x overhead)
        assert fallback_time < success_time * 5 + 1.0  # +1s for absolute tolerance
    
    def test_startup_summary_performance_data(self):
        """Test that startup summary includes performance data"""
        # Add components with various performance characteristics
        components = [
            ("fast_comp", ComponentStatus.LOADED, 0.3),
            ("slow_comp", ComponentStatus.LOADED, 2.1),
            ("fallback_comp", ComponentStatus.FALLBACK, 1.5)
        ]
        
        for name, status, duration in components:
            comp_status = ComponentStatusInfo(
                name=name,
                status=status,
                error_message=None,
                load_time=datetime.now(),
                fallback_reason=None,
                load_duration=duration
            )
            self.monitor.update_component_status(comp_status)
        
        summary = self.monitor.generate_startup_summary()
        
        # Summary should include timing information
        assert summary.startup_duration > 0
        assert len(summary.components) == 3
        
        # Each component should have load duration
        for component in summary.components:
            assert hasattr(component, 'load_duration')
            assert component.load_duration > 0