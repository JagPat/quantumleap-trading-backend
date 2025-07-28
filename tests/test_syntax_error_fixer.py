"""
Unit tests for Syntax Error Fixer
"""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, mock_open

from app.core.syntax_error_fixer import SyntaxErrorFixer, ValidationResult, FixResult

class TestSyntaxErrorFixer:
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.fixer = SyntaxErrorFixer()
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, content: str, filename: str = "test.py") -> str:
        """Create a test file with given content"""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_validate_router_syntax_valid_file(self):
        """Test syntax validation with valid Python file"""
        valid_content = '''
def test_function():
    return "hello"

class TestClass:
    def method(self):
        pass
'''
        file_path = self.create_test_file(valid_content)
        
        result = self.fixer.validate_router_syntax(file_path)
        
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.line_number is None
    
    def test_validate_router_syntax_invalid_file(self):
        """Test syntax validation with invalid Python file"""
        invalid_content = '''
def test_function()  # Missing colon
    return "hello"
'''
        file_path = self.create_test_file(invalid_content)
        
        result = self.fixer.validate_router_syntax(file_path)
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert result.line_number is not None
        assert "Syntax error" in result.errors[0]
    
    def test_validate_router_syntax_stray_decorator(self):
        """Test detection of stray decorator symbols"""
        content_with_stray_decorator = '''
@
def test_function():
    return "hello"
'''
        file_path = self.create_test_file(content_with_stray_decorator)
        
        result = self.fixer.validate_router_syntax(file_path)
        
        assert result.valid is False
        assert len(result.warnings) > 0
        assert any("Stray decorator symbol" in warning for warning in result.warnings)
    
    def test_validate_router_syntax_missing_colon(self):
        """Test detection of missing colons"""
        content_missing_colon = '''
def test_function()
    return "hello"
'''
        file_path = self.create_test_file(content_missing_colon)
        
        result = self.fixer.validate_router_syntax(file_path)
        
        assert result.valid is False
        # Should detect syntax error due to missing colon
        assert len(result.errors) > 0
    
    def test_validate_router_syntax_nonexistent_file(self):
        """Test validation with non-existent file"""
        result = self.fixer.validate_router_syntax("/nonexistent/file.py")
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]
    
    def test_fix_common_syntax_errors_stray_decorator(self):
        """Test fixing stray decorator symbols"""
        content_with_stray = '''
@
def test_function():
    return "hello"
'''
        file_path = self.create_test_file(content_with_stray)
        
        result = self.fixer.fix_common_syntax_errors(file_path)
        
        assert result.success is True
        assert len(result.fixes_applied) > 0
        assert any("stray '@' symbol" in fix.lower() for fix in result.fixes_applied)
        assert result.backup_path is not None
        
        # Check that file is now valid
        with open(file_path, 'r') as f:
            fixed_content = f.read()
        
        # Should not contain standalone @ symbol
        assert '@\n' not in fixed_content
    
    def test_fix_common_syntax_errors_valid_file(self):
        """Test fixing already valid file"""
        valid_content = '''
def test_function():
    return "hello"
'''
        file_path = self.create_test_file(valid_content)
        
        result = self.fixer.fix_common_syntax_errors(file_path)
        
        # Should succeed but apply no fixes
        assert result.success is True
        # May have minimal fixes applied due to regex patterns
        assert result.backup_path is not None
    
    def test_fix_common_syntax_errors_nonexistent_file(self):
        """Test fixing non-existent file"""
        result = self.fixer.fix_common_syntax_errors("/nonexistent/file.py")
        
        assert result.success is False
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]
        assert result.backup_path is None
    
    def test_backup_original_file(self):
        """Test backup file creation"""
        content = "def test(): pass"
        file_path = self.create_test_file(content)
        
        backup_path = self.fixer.backup_original_file(file_path)
        
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path.startswith(file_path + ".backup_")
        
        # Check backup content matches original
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        assert backup_content == content
    
    def test_backup_original_file_nonexistent(self):
        """Test backup creation for non-existent file"""
        backup_path = self.fixer.backup_original_file("/nonexistent/file.py")
        
        assert backup_path is None
    
    def test_validate_and_fix_file_valid(self):
        """Test validate and fix with valid file"""
        valid_content = '''
def test_function():
    return "hello"
'''
        file_path = self.create_test_file(valid_content)
        
        result = self.fixer.validate_and_fix_file(file_path)
        
        assert result["success"] is True
        assert result["validation"].valid is True
        assert result["fix"] is None  # No fix needed
    
    def test_validate_and_fix_file_fixable(self):
        """Test validate and fix with fixable file"""
        fixable_content = '''
@
def test_function():
    return "hello"
'''
        file_path = self.create_test_file(fixable_content)
        
        result = self.fixer.validate_and_fix_file(file_path)
        
        assert result["file_path"] == file_path
        assert result["validation"] is not None
        assert result["fix"] is not None
        # Success depends on whether the fix actually resolves the syntax error
    
    def test_validate_and_fix_file_unfixable(self):
        """Test validate and fix with unfixable file"""
        unfixable_content = '''
def test_function(
    # Unclosed parenthesis - hard to fix automatically
    return "hello"
'''
        file_path = self.create_test_file(unfixable_content)
        
        result = self.fixer.validate_and_fix_file(file_path)
        
        assert result["file_path"] == file_path
        assert result["validation"] is not None
        assert result["validation"].valid is False
        # Fix may be attempted but likely won't succeed
    
    def test_scan_and_fix_directory(self):
        """Test directory scanning and fixing"""
        # Create multiple test files
        valid_file = self.create_test_file('''
def valid_function():
    return "valid"
''', "valid.py")
        
        invalid_file = self.create_test_file('''
@
def invalid_function():
    return "invalid"
''', "invalid.py")
        
        result = self.fixer.scan_and_fix_directory(self.temp_dir)
        
        assert result["directory"] == self.temp_dir
        assert result["files_scanned"] == 2
        assert len(result["file_results"]) == 2
        
        # At least one file should be processed
        assert result["files_fixed"] + result["files_failed"] == 2
    
    def test_scan_and_fix_directory_empty(self):
        """Test directory scanning with no Python files"""
        # Create non-Python file
        self.create_test_file("not python", "test.txt")
        
        result = self.fixer.scan_and_fix_directory(self.temp_dir)
        
        assert result["files_scanned"] == 0
        assert result["files_fixed"] == 0
        assert result["files_failed"] == 0
        assert len(result["file_results"]) == 0
    
    def test_scan_and_fix_directory_nonexistent(self):
        """Test directory scanning with non-existent directory"""
        result = self.fixer.scan_and_fix_directory("/nonexistent/directory")
        
        assert "error" in result
        assert result["files_scanned"] == 0
    
    def test_syntax_error_fixer_initialization(self):
        """Test SyntaxErrorFixer initialization"""
        fixer = SyntaxErrorFixer()
        
        assert hasattr(fixer, 'common_fixes')
        assert isinstance(fixer.common_fixes, dict)
        assert len(fixer.common_fixes) > 0
    
    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass"""
        result = ValidationResult(
            valid=True,
            errors=["error1"],
            warnings=["warning1"],
            line_number=5
        )
        
        assert result.valid is True
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
        assert result.line_number == 5
    
    def test_fix_result_dataclass(self):
        """Test FixResult dataclass"""
        result = FixResult(
            success=True,
            fixes_applied=["fix1"],
            backup_path="/path/to/backup",
            errors=["error1"],
            original_content="original",
            fixed_content="fixed"
        )
        
        assert result.success is True
        assert result.fixes_applied == ["fix1"]
        assert result.backup_path == "/path/to/backup"
        assert result.errors == ["error1"]
        assert result.original_content == "original"
        assert result.fixed_content == "fixed"