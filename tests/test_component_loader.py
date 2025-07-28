"""
Unit tests for Component Loader
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import APIRouter
import time

from app.core.component_loader import (
    ComponentLoader, ComponentStatus, RouterLoadResult, ComponentStatusInfo
)

class TestComponentLoader:
    
    def setup_method(self):
        """Set up test environment"""
        self.loader = ComponentLoader()
    
    def test_component_loader_initialization(self):
        """Test ComponentLoader initialization"""
        loader = ComponentLoader()
        
        assert isinstance(loader.component_statuses, dict)
        assert isinstance(loader.loaded_routers, dict)
        assert isinstance(loader.fallback_routers, dict)
        assert len(loader.component_statuses) == 0
    
    @patch('app.core.component_loader.__import__')
    def test_load_router_with_fallback_success(self, mock_import):
        """Test successful router loading"""
        # Mock successful import
        mock_router = APIRouter()
        mock_module = MagicMock()
        mock_module.router = mock_router
        mock_import.return_value = mock_module
        
        result = self.loader.load_router_with_fallback(
            "test_component",
            "app.test.router",
            "/api/test"
        )
        
        assert result.success is True
        assert result.router == mock_router
        assert result.error is None
        assert result.fallback_used is False
        assert result.component_name == "test_component"
        assert result.load_duration > 0
        
        # Check component status tracking
        status = self.loader.get_component_status("test_component")
        assert status is not None
        assert status.status == ComponentStatus.LOADED
        assert status.error_message is None
    
    @patch('app.core.component_loader.__import__')
    def test_load_router_with_fallback_import_error(self, mock_import):
        """Test router loading with import error"""
        # Mock import failure
        mock_import.side_effect = ImportError("Module not found")
        
        result = self.loader.load_router_with_fallback(
            "test_component",
            "app.nonexistent.router",
            "/api/test"
        )
        
        assert result.success is False
        assert result.router is not None  # Should have fallback router
        assert isinstance(result.error, ImportError)
        assert result.fallback_used is True
        assert result.component_name == "test_component"
        
        # Check component status tracking
        status = self.loader.get_component_status("test_component")
        assert status is not None
        assert status.status == ComponentStatus.FALLBACK
        assert "Module not found" in status.error_message
    
    @patch('app.core.component_loader.__import__')
    def test_load_router_with_fallback_wrong_type(self, mock_import):
        """Test router loading when imported object is not APIRouter"""
        # Mock import returning wrong type
        mock_module = MagicMock()
        mock_module.router = "not_a_router"
        mock_import.return_value = mock_module
        
        result = self.loader.load_router_with_fallback(
            "test_component",
            "app.test.router",
            "/api/test"
        )
        
        assert result.success is False
        assert result.fallback_used is True
        assert isinstance(result.error, TypeError)
        
        # Check component status
        status = self.loader.get_component_status("test_component")
        assert status.status == ComponentStatus.FALLBACK
    
    def test_create_fallback_router_basic(self):
        """Test basic fallback router creation"""
        router = self.loader.create_fallback_router(
            "test_component",
            "/api/test",
            "Test error message"
        )
        
        assert router is not None
        assert isinstance(router, APIRouter)
        assert router.prefix == "/api/test"
    
    def test_create_fallback_router_portfolio(self):
        """Test portfolio-specific fallback router"""
        router = self.loader.create_fallback_router(
            "portfolio",
            "/api/portfolio",
            "Portfolio service failed"
        )
        
        assert router is not None
        assert isinstance(router, APIRouter)
        # Portfolio fallback should have specific endpoints
        # This is tested through integration tests
    
    def test_create_fallback_router_trading(self):
        """Test trading-specific fallback router"""
        router = self.loader.create_fallback_router(
            "trading",
            "/api/trading",
            "Trading service failed"
        )
        
        assert router is not None
        assert isinstance(router, APIRouter)
    
    def test_track_component_status(self):
        """Test component status tracking"""
        self.loader.track_component_status(
            "test_component",
            ComponentStatus.LOADED,
            None,
            1.5
        )
        
        status = self.loader.get_component_status("test_component")
        assert status is not None
        assert status.name == "test_component"
        assert status.status == ComponentStatus.LOADED
        assert status.error_message is None
        assert status.load_duration == 1.5
        assert status.fallback_reason is None
    
    def test_track_component_status_with_error(self):
        """Test component status tracking with error"""
        self.loader.track_component_status(
            "test_component",
            ComponentStatus.FALLBACK,
            "Import failed",
            2.0,
            "Production router unavailable"
        )
        
        status = self.loader.get_component_status("test_component")
        assert status is not None
        assert status.status == ComponentStatus.FALLBACK
        assert status.error_message == "Import failed"
        assert status.fallback_reason == "Production router unavailable"
    
    def test_get_all_component_statuses(self):
        """Test getting all component statuses"""
        # Add multiple components
        self.loader.track_component_status("comp1", ComponentStatus.LOADED)
        self.loader.track_component_status("comp2", ComponentStatus.FALLBACK, "Error")
        self.loader.track_component_status("comp3", ComponentStatus.FAILED, "Critical error")
        
        all_statuses = self.loader.get_all_component_statuses()
        
        assert len(all_statuses) == 3
        assert "comp1" in all_statuses
        assert "comp2" in all_statuses
        assert "comp3" in all_statuses
        assert all_statuses["comp1"].status == ComponentStatus.LOADED
        assert all_statuses["comp2"].status == ComponentStatus.FALLBACK
        assert all_statuses["comp3"].status == ComponentStatus.FAILED
    
    def test_get_loaded_components(self):
        """Test getting loaded components list"""
        self.loader.track_component_status("comp1", ComponentStatus.LOADED)
        self.loader.track_component_status("comp2", ComponentStatus.FALLBACK, "Error")
        self.loader.track_component_status("comp3", ComponentStatus.LOADED)
        
        loaded = self.loader.get_loaded_components()
        
        assert len(loaded) == 2
        assert "comp1" in loaded
        assert "comp3" in loaded
        assert "comp2" not in loaded
    
    def test_get_fallback_components(self):
        """Test getting fallback components list"""
        self.loader.track_component_status("comp1", ComponentStatus.LOADED)
        self.loader.track_component_status("comp2", ComponentStatus.FALLBACK, "Error")
        self.loader.track_component_status("comp3", ComponentStatus.FALLBACK, "Error2")
        
        fallback = self.loader.get_fallback_components()
        
        assert len(fallback) == 2
        assert "comp2" in fallback
        assert "comp3" in fallback
        assert "comp1" not in fallback
    
    def test_get_failed_components(self):
        """Test getting failed components list"""
        self.loader.track_component_status("comp1", ComponentStatus.LOADED)
        self.loader.track_component_status("comp2", ComponentStatus.FALLBACK, "Error")
        self.loader.track_component_status("comp3", ComponentStatus.FAILED, "Critical")
        
        failed = self.loader.get_failed_components()
        
        assert len(failed) == 1
        assert "comp3" in failed
        assert "comp1" not in failed
        assert "comp2" not in failed
    
    def test_is_component_healthy(self):
        """Test component health checking"""
        self.loader.track_component_status("healthy", ComponentStatus.LOADED)
        self.loader.track_component_status("fallback", ComponentStatus.FALLBACK, "Error")
        self.loader.track_component_status("failed", ComponentStatus.FAILED, "Critical")
        
        assert self.loader.is_component_healthy("healthy") is True
        assert self.loader.is_component_healthy("fallback") is False
        assert self.loader.is_component_healthy("failed") is False
        assert self.loader.is_component_healthy("nonexistent") is False
    
    def test_router_load_result_dataclass(self):
        """Test RouterLoadResult dataclass"""
        result = RouterLoadResult(
            success=True,
            router=APIRouter(),
            error=None,
            fallback_used=False,
            load_duration=1.5,
            component_name="test"
        )
        
        assert result.success is True
        assert isinstance(result.router, APIRouter)
        assert result.error is None
        assert result.fallback_used is False
        assert result.load_duration == 1.5
        assert result.component_name == "test"
    
    def test_component_status_info_dataclass(self):
        """Test ComponentStatusInfo dataclass"""
        from datetime import datetime
        
        now = datetime.now()
        status = ComponentStatusInfo(
            name="test",
            status=ComponentStatus.LOADED,
            error_message=None,
            load_time=now,
            fallback_reason=None,
            load_duration=1.0
        )
        
        assert status.name == "test"
        assert status.status == ComponentStatus.LOADED
        assert status.error_message is None
        assert status.load_time == now
        assert status.fallback_reason is None
        assert status.load_duration == 1.0