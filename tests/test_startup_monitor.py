"""
Unit tests for Startup Monitor
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import time

from app.core.startup_monitor import StartupMonitor, StartupSummary
from app.core.component_loader import ComponentStatusInfo, ComponentStatus

class TestStartupMonitor:
    
    def setup_method(self):
        """Set up test environment"""
        self.monitor = StartupMonitor()
    
    def test_startup_monitor_initialization(self):
        """Test StartupMonitor initialization"""
        monitor = StartupMonitor()
        
        assert isinstance(monitor.startup_events, list)
        assert isinstance(monitor.component_statuses, dict)
        assert isinstance(monitor.infrastructure_results, dict)
        assert len(monitor.startup_events) == 0
        assert monitor.startup_start_time > 0
    
    def test_log_startup_progress_basic(self):
        """Test basic startup progress logging"""
        self.monitor.log_startup_progress("test_component", "loading", "Starting up")
        
        assert len(self.monitor.startup_events) == 1
        event = self.monitor.startup_events[0]
        
        assert event["component"] == "test_component"
        assert event["status"] == "loading"
        assert event["details"] == "Starting up"
        assert "timestamp" in event
        assert "message" in event
    
    def test_log_startup_progress_with_duration(self):
        """Test startup progress logging with duration"""
        self.monitor.log_startup_progress("test_component", "success", "Loaded", 1.5)
        
        event = self.monitor.startup_events[0]
        assert event["duration"] == 1.5
        assert "1.5s" in event["message"]
    
    def test_log_startup_progress_different_statuses(self):
        """Test logging with different status types"""
        statuses = ["loading", "success", "fallback", "failed", "created", "validated"]
        
        for status in statuses:
            self.monitor.log_startup_progress(f"comp_{status}", status, f"Test {status}")
        
        assert len(self.monitor.startup_events) == len(statuses)
        
        for i, status in enumerate(statuses):
            event = self.monitor.startup_events[i]
            assert event["status"] == status
            assert event["component"] == f"comp_{status}"
    
    def test_update_component_status(self):
        """Test component status updating"""
        status_info = ComponentStatusInfo(
            name="test_component",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        self.monitor.update_component_status(status_info)
        
        assert "test_component" in self.monitor.component_statuses
        assert self.monitor.component_statuses["test_component"] == status_info
        assert len(self.monitor.startup_events) == 1  # Should log the status update
    
    def test_set_infrastructure_results(self):
        """Test setting infrastructure results"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "Infrastructure validated"
        
        results = {"logging": mock_result}
        self.monitor.set_infrastructure_results(results)
        
        assert self.monitor.infrastructure_results == results
        assert len(self.monitor.startup_events) == 1  # Should log infrastructure status
    
    def test_generate_startup_summary(self):
        """Test startup summary generation"""
        # Add some component statuses
        loaded_status = ComponentStatusInfo(
            name="loaded_comp",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        fallback_status = ComponentStatusInfo(
            name="fallback_comp",
            status=ComponentStatus.FALLBACK,
            error_message="Import failed",
            load_time=datetime.now(),
            fallback_reason="Production unavailable",
            load_duration=2.0
        )
        
        failed_status = ComponentStatusInfo(
            name="failed_comp",
            status=ComponentStatus.FAILED,
            error_message="Critical error",
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=0.5
        )
        
        self.monitor.update_component_status(loaded_status)
        self.monitor.update_component_status(fallback_status)
        self.monitor.update_component_status(failed_status)
        
        # Add infrastructure results
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message = "All good"
        self.monitor.set_infrastructure_results({"test": mock_result})
        
        summary = self.monitor.generate_startup_summary()
        
        assert isinstance(summary, StartupSummary)
        assert summary.total_components == 3
        assert summary.loaded_successfully == 1
        assert summary.fallback_active == 1
        assert summary.failed_completely == 1
        assert summary.startup_duration > 0
        assert len(summary.components) == 3
        assert summary.infrastructure_status == {"test": mock_result}
    
    def test_startup_summary_to_dict(self):
        """Test StartupSummary to_dict conversion"""
        component = ComponentStatusInfo(
            name="test",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        summary = StartupSummary(
            total_components=1,
            loaded_successfully=1,
            fallback_active=0,
            failed_completely=0,
            startup_duration=5.0,
            startup_time=datetime.now(),
            components=[component],
            infrastructure_status={}
        )
        
        result = summary.to_dict()
        
        assert isinstance(result, dict)
        assert result["total_components"] == 1
        assert result["loaded_successfully"] == 1
        assert result["startup_duration"] == 5.0
        assert len(result["components"]) == 1
        assert result["components"][0]["name"] == "test"
        assert result["components"][0]["status"] == "loaded"
    
    def test_create_health_endpoints(self):
        """Test health endpoints creation"""
        from fastapi import APIRouter
        
        router = self.monitor.create_health_endpoints()
        
        assert isinstance(router, APIRouter)
        assert router.prefix == "/health"
        # Detailed endpoint testing would require FastAPI test client
    
    def test_get_startup_events(self):
        """Test getting startup events"""
        self.monitor.log_startup_progress("test", "loading", "Test")
        
        events = self.monitor.get_startup_events()
        
        assert len(events) == 1
        assert events[0]["component"] == "test"
        assert events[0]["status"] == "loading"
        
        # Should return a copy, not the original
        events.append({"test": "data"})
        assert len(self.monitor.startup_events) == 1
    
    def test_get_component_statuses(self):
        """Test getting component statuses"""
        status = ComponentStatusInfo(
            name="test",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        self.monitor.update_component_status(status)
        
        statuses = self.monitor.get_component_statuses()
        
        assert len(statuses) == 1
        assert "test" in statuses
        assert statuses["test"] == status
        
        # Should return a copy
        statuses["new"] = status
        assert "new" not in self.monitor.component_statuses
    
    def test_is_startup_healthy_empty(self):
        """Test startup health check with no components"""
        assert self.monitor.is_startup_healthy() is False
    
    def test_is_startup_healthy_all_loaded(self):
        """Test startup health check with all components loaded"""
        for i in range(3):
            status = ComponentStatusInfo(
                name=f"comp_{i}",
                status=ComponentStatus.LOADED,
                error_message=None,
                load_time=datetime.now(),
                fallback_reason=None,
                load_duration=1.0
            )
            self.monitor.update_component_status(status)
        
        assert self.monitor.is_startup_healthy() is True
    
    def test_is_startup_healthy_mixed(self):
        """Test startup health check with mixed component statuses"""
        # Add 2 loaded, 1 fallback - should be healthy (66% > 50%)
        loaded_status = ComponentStatusInfo(
            name="loaded1",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        loaded_status2 = ComponentStatusInfo(
            name="loaded2",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        fallback_status = ComponentStatusInfo(
            name="fallback1",
            status=ComponentStatus.FALLBACK,
            error_message="Error",
            load_time=datetime.now(),
            fallback_reason="Failed",
            load_duration=1.0
        )
        
        self.monitor.update_component_status(loaded_status)
        self.monitor.update_component_status(loaded_status2)
        self.monitor.update_component_status(fallback_status)
        
        assert self.monitor.is_startup_healthy() is True
    
    def test_is_startup_healthy_mostly_failed(self):
        """Test startup health check with mostly failed components"""
        # Add 1 loaded, 2 failed - should be unhealthy (33% < 50%)
        loaded_status = ComponentStatusInfo(
            name="loaded1",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        failed_status1 = ComponentStatusInfo(
            name="failed1",
            status=ComponentStatus.FAILED,
            error_message="Error",
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        failed_status2 = ComponentStatusInfo(
            name="failed2",
            status=ComponentStatus.FAILED,
            error_message="Error",
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        self.monitor.update_component_status(loaded_status)
        self.monitor.update_component_status(failed_status1)
        self.monitor.update_component_status(failed_status2)
        
        assert self.monitor.is_startup_healthy() is False
    
    def test_get_fallback_components_info(self):
        """Test getting fallback components info for frontend transparency"""
        fallback_status = ComponentStatusInfo(
            name="portfolio",
            status=ComponentStatus.FALLBACK,
            error_message="Import failed",
            load_time=datetime.now(),
            fallback_reason="Production service unavailable",
            load_duration=2.0
        )
        
        loaded_status = ComponentStatusInfo(
            name="auth",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=datetime.now(),
            fallback_reason=None,
            load_duration=1.0
        )
        
        self.monitor.update_component_status(fallback_status)
        self.monitor.update_component_status(loaded_status)
        
        fallback_info = self.monitor.get_fallback_components_info()
        
        assert len(fallback_info) == 1
        assert "portfolio" in fallback_info
        assert "auth" not in fallback_info
        
        portfolio_info = fallback_info["portfolio"]
        assert portfolio_info["real_data"] is False
        assert portfolio_info["fallback_active"] is True
        assert "⚠️" in portfolio_info["warning"]
        assert "Portfolio service is in fallback mode" in portfolio_info["warning"]