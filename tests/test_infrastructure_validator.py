"""
Unit tests for Infrastructure Validator
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, mock_open
from pathlib import Path

from app.core.infrastructure_validator import InfrastructureValidator, ValidationResult

class TestInfrastructureValidator:
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = InfrastructureValidator()
        
        # Override required directories to use temp directory
        self.validator.required_directories = [
            os.path.join(self.temp_dir, "logs"),
            os.path.join(self.temp_dir, "data"),
            os.path.join(self.temp_dir, "temp")
        ]
        
        self.validator.required_files = [
            os.path.join(self.temp_dir, "logs", "trading_engine.log"),
            os.path.join(self.temp_dir, "logs", "ai_engine.log"),
            os.path.join(self.temp_dir, "logs", "application.log")
        ]
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validate_logging_infrastructure_success(self):
        """Test successful logging infrastructure validation"""
        result = self.validator.validate_logging_infrastructure()
        
        assert result.success is True
        assert "successfully" in result.message.lower()
        assert len(result.created_items) > 0
        assert len(result.errors) == 0
        
        # Verify directories were created
        for directory in self.validator.required_directories:
            assert os.path.exists(directory)
        
        # Verify log files were created
        for file_path in self.validator.required_files:
            assert os.path.exists(file_path)
    
    def test_validate_logging_infrastructure_existing_files(self):
        """Test validation when files already exist"""
        # Pre-create some directories and files
        os.makedirs(os.path.join(self.temp_dir, "logs"), exist_ok=True)
        Path(os.path.join(self.temp_dir, "logs", "trading_engine.log")).touch()
        
        result = self.validator.validate_logging_infrastructure()
        
        assert result.success is True
        # Should create remaining items but not duplicate existing ones
        assert len(result.created_items) < len(self.validator.required_directories) + len(self.validator.required_files)
    
    def test_create_missing_directories_success(self):
        """Test successful directory creation"""
        result = self.validator.create_missing_directories()
        
        assert result.success is True
        assert len(result.created_items) == len(self.validator.required_directories)
        assert len(result.errors) == 0
        
        # Verify all directories were created
        for directory in self.validator.required_directories:
            assert os.path.exists(directory)
    
    def test_create_missing_directories_partial_existing(self):
        """Test directory creation when some already exist"""
        # Pre-create one directory
        existing_dir = self.validator.required_directories[0]
        os.makedirs(existing_dir, exist_ok=True)
        
        result = self.validator.create_missing_directories()
        
        assert result.success is True
        # Should create only the missing directories
        assert len(result.created_items) == len(self.validator.required_directories) - 1
    
    @patch('os.makedirs')
    def test_create_missing_directories_permission_error(self, mock_makedirs):
        """Test directory creation with permission errors"""
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        result = self.validator.create_missing_directories()
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "Permission denied" in result.errors[0]
    
    def test_validate_file_permissions_success(self):
        """Test successful file permission validation"""
        # First create the infrastructure
        self.validator.validate_logging_infrastructure()
        
        result = self.validator.validate_file_permissions()
        
        assert result.success is True
        assert len(result.errors) == 0
        assert len(result.created_items) > 0
    
    @patch('os.access')
    def test_validate_file_permissions_no_write_access(self, mock_access):
        """Test file permission validation with no write access"""
        # Create directories first
        self.validator.create_missing_directories()
        
        # Mock os.access to return False for write permission
        mock_access.return_value = False
        
        result = self.validator.validate_file_permissions()
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "not writable" in result.errors[0]
    
    def test_validate_all_comprehensive(self):
        """Test comprehensive validation"""
        results = self.validator.validate_all()
        
        assert 'logging' in results
        assert 'directories' in results
        assert 'permissions' in results
        
        # All validations should succeed
        for key, result in results.items():
            assert isinstance(result, ValidationResult)
            assert result.success is True
    
    @patch('os.makedirs')
    def test_validate_all_with_errors(self, mock_makedirs):
        """Test comprehensive validation with some errors"""
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        results = self.validator.validate_all()
        
        assert 'logging' in results
        assert 'directories' in results
        assert 'permissions' in results
        
        # Some validations should fail
        assert results['directories'].success is False
        assert len(results['directories'].errors) > 0
    
    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass functionality"""
        result = ValidationResult(
            success=True,
            message="Test message",
            created_items=["item1", "item2"],
            errors=[]
        )
        
        assert result.success is True
        assert result.message == "Test message"
        assert len(result.created_items) == 2
        assert len(result.errors) == 0
    
    def test_infrastructure_validator_initialization(self):
        """Test InfrastructureValidator initialization"""
        validator = InfrastructureValidator()
        
        assert len(validator.required_directories) > 0
        assert len(validator.required_files) > 0
        assert "logs" in validator.required_directories
        assert any("trading_engine.log" in f for f in validator.required_files)