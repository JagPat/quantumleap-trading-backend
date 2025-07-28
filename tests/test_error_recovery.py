"""
Error Recovery Testing Suite
Comprehensive tests for error simulation and recovery mechanisms
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock, mock_open
import asyncio

from app.core.infrastructure_validator import InfrastructureValidator
from app.core.component_loader import ComponentLoader, ComponentStatus
from app.core.startup_monitor import StartupMonitor
from app.core.syntax_error_fixer import SyntaxErrorFixer

class TestErrorRecovery:
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test directory structure
        os.makedirs("app/test_module", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_router_file(self, content: str, path: str = "app/test_module/router.py"):
        """Create a test router file with given content"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path
    
    def test_startup_with_missing_log_directories(self):
        """Test startup behavior when log directories are missing"""
        # Remove logs directory
        if os.path.exists("logs"):
            shutil.rmtree("logs")
        
        validator = InfrastructureValidator()
        
        # Override required directories to use temp directory
        validator.required_directories = [
            os.path.join(self.temp_dir, "logs"),
            os.path.join(self.temp_dir, "data")
        ]
        validator.required_files = [
            os.path.join(self.temp_dir, "logs", "test.log")
        ]
        
        # Validate - should create missing directories
        result = validator.validate_logging_infrastructure()
        
        assert result.success is True
        assert len(result.created_items) > 0
        assert os.path.exists(os.path.join(self.temp_dir, "logs"))
        assert os.path.exists(os.path.join(self.temp_dir, "logs", "test.log"))
    
    def test_startup_with_syntax_errors_in_router_files(self):
        """Test startup behavior with syntax errors in router files"""
        # Create router file with syntax error
        router_content = '''
from fastapi import APIRouter

router = APIRouter()

@
@router.get("/test")
def test_endpoint():
    return {"test": "value"}
'''
        router_path = self.create_test_router_file(router_content)
        
        # Test syntax error fixer
        fixer = SyntaxErrorFixer()
        validation_result = fixer.validate_router_syntax(router_path)
        
        assert validation_result.valid is False
        assert len(validation_result.errors) > 0 or len(validation_result.warnings) > 0
        
        # Test fix
        fix_result = fixer.fix_common_syntax_errors(router_path)
        
        # Should attempt to fix (success depends on specific error)
        assert fix_result.backup_path is not None
        assert len(fix_result.fixes_applied) > 0
    
    def test_startup_with_import_failures(self):
        """Test startup behavior when router imports fail"""
        component_loader = ComponentLoader()
        
        # Try to load non-existent router
        result = component_loader.load_router_with_fallback(
            "nonexistent",
            "app.nonexistent.router.router",
            "/api/nonexistent"
        )
        
        assert result.success is False
        assert result.fallback_used is True
        assert result.router is not None  # Should have fallback router
        assert isinstance(result.error, (ImportError, ModuleNotFoundError, AttributeError))
        
        # Check component status tracking
        status = component_loader.get_component_status("nonexistent")
        assert status is not None
        assert status.status == ComponentStatus.FALLBACK
    
    def test_startup_with_invalid_router_object(self):
        """Test startup behavior when imported object is not a router"""
        # Create file with invalid router object
        invalid_router_content = '''
# This is not a valid router
router = "not_a_router"
'''
        router_path = self.create_test_router_file(invalid_router_content)
        
        component_loader = ComponentLoader()
        
        # Try to load invalid router
        result = component_loader.load_router_with_fallback(
            "invalid",
            "app.test_module.router.router",
            "/api/invalid"
        )
        
        assert result.success is False
        assert result.fallback_used is True
        assert isinstance(result.error, TypeError)
    
    def test_fallback_system_activation(self):
        """Test that fallback systems activate correctly under various error conditions"""
        component_loader = ComponentLoader()
        startup_monitor = StartupMonitor()
        
        # Test multiple component failures
        components_to_test = [
            ("portfolio", "app.nonexistent.portfolio.router", "/api/portfolio"),
            ("broker", "app.nonexistent.broker.router", "/api/broker"),
            ("trading", "app.nonexistent.trading.router", "/api/trading")
        ]
        
        fallback_count = 0
        
        for name, path, prefix in components_to_test:
            result = component_loader.load_router_with_fallback(name, path, prefix)
            
            if result.fallback_used:
                fallback_count += 1
            
            # Update startup monitor
            if hasattr(component_loader, 'get_component_status'):
                status = component_loader.get_component_status(name)
                if status:
                    startup_monitor.update_component_status(status)
        
        # Check that fallbacks were activated
        assert fallback_count > 0
        
        # Check startup monitor summary
        summary = startup_monitor.generate_startup_summary()
        assert summary.fallback_active > 0
        assert summary.total_components > 0
    
    def test_component_isolation(self):
        """Test that individual component failures don't affect others"""
        component_loader = ComponentLoader()
        
        # Create one valid router
        valid_router_content = '''
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
def test_endpoint():
    return {"status": "ok"}
'''
        self.create_test_router_file(valid_router_content, "app/valid_module/router.py")
        
        # Test loading valid router
        valid_result = component_loader.load_router_with_fallback(
            "valid",
            "app.valid_module.router.router",
            "/api/valid"
        )
        
        # Test loading invalid router
        invalid_result = component_loader.load_router_with_fallback(
            "invalid",
            "app.nonexistent.router.router",
            "/api/invalid"
        )
        
        # Valid router should succeed
        assert valid_result.success is True
        assert valid_result.fallback_used is False
        
        # Invalid router should fail but have fallback
        assert invalid_result.success is False
        assert invalid_result.fallback_used is True
        
        # Check that both components are tracked independently
        valid_status = component_loader.get_component_status("valid")
        invalid_status = component_loader.get_component_status("invalid")
        
        assert valid_status.status == ComponentStatus.LOADED
        assert invalid_status.status == ComponentStatus.FALLBACK
    
    def test_infrastructure_recovery_from_permission_errors(self):
        """Test infrastructure recovery from permission errors"""
        validator = InfrastructureValidator()
        
        # Create a directory with restricted permissions (if possible)
        restricted_dir = os.path.join(self.temp_dir, "restricted")
        os.makedirs(restricted_dir, exist_ok=True)
        
        validator.required_directories = [restricted_dir]
        validator.required_files = [os.path.join(restricted_dir, "test.log")]
        
        # Test validation - should handle permission issues gracefully
        result = validator.validate_file_permissions()
        
        # Should not crash, even if permissions are restricted
        assert isinstance(result.success, bool)
        assert isinstance(result.errors, list)
    
    @patch('app.core.component_loader.__import__')
    def test_recovery_from_various_import_errors(self, mock_import):
        """Test recovery from various types of import errors"""
        component_loader = ComponentLoader()
        
        # Test different import error types
        error_types = [
            ImportError("Module not found"),
            ModuleNotFoundError("No module named 'test'"),
            AttributeError("Module has no attribute 'router'"),
            SyntaxError("Invalid syntax"),
            Exception("Generic error")
        ]
        
        for i, error in enumerate(error_types):
            mock_import.side_effect = error
            
            result = component_loader.load_router_with_fallback(
                f"test_{i}",
                f"app.test_{i}.router.router",
                f"/api/test_{i}"
            )
            
            # Should handle all error types gracefully
            assert result.success is False
            assert result.fallback_used is True
            assert result.router is not None  # Should have fallback
            assert result.error == error
    
    def test_startup_monitor_error_tracking(self):
        """Test that startup monitor correctly tracks errors"""
        startup_monitor = StartupMonitor()
        component_loader = ComponentLoader()
        
        # Simulate component loading with errors
        startup_monitor.log_startup_progress("test_component", "loading", "Starting test")
        
        # Simulate failure
        result = component_loader.load_router_with_fallback(
            "test_component",
            "app.nonexistent.router.router",
            "/api/test"
        )
        
        # Update monitor with result
        if hasattr(component_loader, 'get_component_status'):
            status = component_loader.get_component_status("test_component")
            if status:
                startup_monitor.update_component_status(status)
        
        startup_monitor.log_startup_progress("test_component", "fallback", "Using fallback")
        
        # Check that errors are tracked
        events = startup_monitor.get_startup_events()
        assert len(events) >= 2
        
        # Check summary
        summary = startup_monitor.generate_startup_summary()
        assert summary.fallback_active > 0
    
    def test_health_endpoint_error_handling(self):
        """Test health endpoints handle errors gracefully"""
        startup_monitor = StartupMonitor()
        
        # Create health router
        health_router = startup_monitor.create_health_endpoints()
        
        # Test that endpoints exist and are callable
        assert health_router is not None
        assert hasattr(health_router, 'routes')
        assert len(health_router.routes) > 0
    
    def test_fallback_router_functionality(self):
        """Test that fallback routers provide basic functionality"""
        component_loader = ComponentLoader()
        
        # Create fallback router
        fallback_router = component_loader.create_fallback_router(
            "test_component",
            "/api/test",
            "Test error message"
        )
        
        assert fallback_router is not None
        assert fallback_router.prefix == "/api/test"
        assert len(fallback_router.routes) > 0
        
        # Check that status endpoint exists
        status_routes = [route for route in fallback_router.routes if route.path.endswith("/status")]
        assert len(status_routes) > 0
    
    def test_comprehensive_error_recovery_flow(self):
        """Test complete error recovery flow from start to finish"""
        # Initialize all components
        validator = InfrastructureValidator()
        component_loader = ComponentLoader()
        startup_monitor = StartupMonitor()
        
        # Set up test environment
        validator.required_directories = [os.path.join(self.temp_dir, "logs")]
        validator.required_files = [os.path.join(self.temp_dir, "logs", "test.log")]
        
        # Step 1: Infrastructure validation (should create missing items)
        infra_results = validator.validate_all()
        startup_monitor.set_infrastructure_results(infra_results)
        
        # Step 2: Component loading with errors
        components = [
            ("working", "app.working.router.router", "/api/working"),
            ("broken", "app.broken.router.router", "/api/broken"),
            ("missing", "app.missing.router.router", "/api/missing")
        ]
        
        # Create one working router
        working_content = '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/test")
def test():
    return {"status": "ok"}
'''
        self.create_test_router_file(working_content, "app/working/router.py")
        
        loaded_routers = []
        for name, path, prefix in components:
            startup_monitor.log_startup_progress(name, "loading", f"Loading {name}")
            
            result = component_loader.load_router_with_fallback(name, path, prefix)
            
            if result.router:
                loaded_routers.append(result.router)
            
            # Update monitor
            status = component_loader.get_component_status(name)
            if status:
                startup_monitor.update_component_status(status)
            
            if result.success:
                startup_monitor.log_startup_progress(name, "success", f"{name} loaded")
            else:
                startup_monitor.log_startup_progress(name, "fallback", f"{name} in fallback")
        
        # Step 3: Generate summary
        summary = startup_monitor.generate_startup_summary()
        
        # Verify recovery worked
        assert summary.total_components == 3
        assert summary.loaded_successfully >= 1  # At least the working one
        assert summary.fallback_active >= 2  # The broken ones
        assert len(loaded_routers) == 3  # All should have routers (including fallbacks)
        
        # Verify infrastructure was created
        assert os.path.exists(os.path.join(self.temp_dir, "logs"))
        assert os.path.exists(os.path.join(self.temp_dir, "logs", "test.log"))
    
    def test_error_recovery_performance(self):
        """Test that error recovery doesn't significantly impact performance"""
        import time
        
        component_loader = ComponentLoader()
        
        # Measure time for multiple component loading attempts
        start_time = time.time()
        
        for i in range(10):
            result = component_loader.load_router_with_fallback(
                f"test_{i}",
                f"app.nonexistent_{i}.router.router",
                f"/api/test_{i}"
            )
            
            # Should fail but create fallback quickly
            assert result.fallback_used is True
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert total_time < 5.0  # 5 seconds for 10 failed loads should be reasonable
        
        # Check that all components are tracked
        all_statuses = component_loader.get_all_component_statuses()
        assert len(all_statuses) == 10