"""
Syntax Error Fixer
Automatically detects and fixes common syntax errors in router files
"""
import ast
import os
import re
import shutil
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of syntax validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    line_number: Optional[int] = None

@dataclass
class FixResult:
    """Result of syntax fix operation"""
    success: bool
    fixes_applied: List[str]
    backup_path: Optional[str]
    errors: List[str]
    original_content: str
    fixed_content: str

class SyntaxErrorFixer:
    """Automatically detects and fixes common syntax errors in Python files"""
    
    def __init__(self):
        self.common_fixes = {
            # Stray decorator symbols
            r'^@\s*$': '',  # Remove standalone @ symbols
            r'^@\s*\n': '\n',  # Remove @ symbols on their own line
            
            # Missing colons
            r'(def\s+\w+\([^)]*\))\s*$': r'\1:',  # Add colon to function definitions
            r'(class\s+\w+(?:\([^)]*\))?)\s*$': r'\1:',  # Add colon to class definitions
            r'(if\s+[^:]+)\s*$': r'\1:',  # Add colon to if statements
            r'(for\s+[^:]+)\s*$': r'\1:',  # Add colon to for loops
            r'(while\s+[^:]+)\s*$': r'\1:',  # Add colon to while loops
            r'(try)\s*$': r'\1:',  # Add colon to try blocks
            r'(except[^:]*)\s*$': r'\1:',  # Add colon to except blocks
            r'(finally)\s*$': r'\1:',  # Add colon to finally blocks
            
            # Indentation fixes
            r'^(\s*)([^\s#].*[^:])$': lambda m: self._fix_indentation(m),
            
            # Import fixes
            r'from\s+(\w+)\s+import\s+(\w+)\s+import\s+(\w+)': r'from \1 import \2, \3',  # Duplicate import
            
            # Bracket matching
            r'\(\s*\)': '()',  # Clean up empty parentheses
            r'\[\s*\]': '[]',  # Clean up empty brackets
            r'\{\s*\}': '{}',  # Clean up empty braces
        }
    
    def validate_router_syntax(self, file_path: str) -> ValidationResult:
        """
        Validate syntax of a router file using AST parsing
        
        Args:
            file_path: Path to the Python file to validate
            
        Returns:
            ValidationResult with validation outcome
        """
        errors = []
        warnings = []
        line_number = None
        
        try:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                return ValidationResult(False, errors, warnings)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse with AST
            try:
                ast.parse(content)
                logger.debug(f"Syntax validation passed for {file_path}")
                return ValidationResult(True, errors, warnings)
                
            except SyntaxError as e:
                line_number = e.lineno
                errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
                logger.error(f"Syntax error in {file_path} at line {e.lineno}: {e.msg}")
                
            except Exception as e:
                errors.append(f"Parsing error: {str(e)}")
                logger.error(f"Parsing error in {file_path}: {str(e)}")
            
            # Additional checks for common issues
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Check for stray decorator symbols
                if re.match(r'^\s*@\s*$', line):
                    warnings.append(f"Line {i}: Stray decorator symbol '@'")
                
                # Check for missing colons in function/class definitions
                if re.match(r'^\s*(def|class|if|for|while|try|except|finally)\s+.*[^:]$', line.strip()):
                    if not line.strip().endswith(':'):
                        warnings.append(f"Line {i}: Missing colon at end of statement")
                
                # Check for indentation issues
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    if i > 1 and lines[i-2].strip().endswith(':'):
                        warnings.append(f"Line {i}: Possible indentation issue after colon")
            
            return ValidationResult(False, errors, warnings, line_number)
            
        except Exception as e:
            errors.append(f"File validation failed: {str(e)}")
            logger.error(f"File validation failed for {file_path}: {str(e)}")
            return ValidationResult(False, errors, warnings)
    
    def fix_common_syntax_errors(self, file_path: str) -> FixResult:
        """
        Automatically fix common syntax errors in a Python file
        
        Args:
            file_path: Path to the Python file to fix
            
        Returns:
            FixResult with fix operation outcome
        """
        fixes_applied = []
        errors = []
        backup_path = None
        
        try:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                return FixResult(False, fixes_applied, backup_path, errors, "", "")
            
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create backup
            backup_path = self.backup_original_file(file_path)
            if not backup_path:
                errors.append("Failed to create backup file")
                return FixResult(False, fixes_applied, backup_path, errors, original_content, original_content)
            
            fixed_content = original_content
            
            # Apply common fixes
            for pattern, replacement in self.common_fixes.items():
                if callable(replacement):
                    # Handle lambda functions
                    continue
                
                matches = re.findall(pattern, fixed_content, re.MULTILINE)
                if matches:
                    fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.MULTILINE)
                    fixes_applied.append(f"Applied fix for pattern: {pattern}")
                    logger.info(f"Applied fix for pattern '{pattern}' in {file_path}")
            
            # Specific fix for stray @ symbols (common issue)
            lines = fixed_content.split('\n')
            fixed_lines = []
            for i, line in enumerate(lines):
                # Remove standalone @ symbols
                if re.match(r'^\s*@\s*$', line):
                    fixes_applied.append(f"Removed stray '@' symbol at line {i+1}")
                    logger.info(f"Removed stray '@' symbol at line {i+1} in {file_path}")
                    continue
                
                # Fix @ symbols followed by newline
                if re.match(r'^\s*@\s*\n?$', line) and i < len(lines) - 1:
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    if next_line.strip().startswith(('def ', 'class ', 'async def ')):
                        # This is likely a decorator, keep it but fix formatting
                        fixed_lines.append(line.replace('@', '@' + next_line.strip().split()[0]))
                        fixes_applied.append(f"Fixed decorator formatting at line {i+1}")
                        continue
                    else:
                        # Standalone @, remove it
                        fixes_applied.append(f"Removed stray '@' symbol at line {i+1}")
                        continue
                
                fixed_lines.append(line)
            
            fixed_content = '\n'.join(fixed_lines)
            
            # Validate the fixed content
            try:
                ast.parse(fixed_content)
                
                # Write the fixed content back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                logger.info(f"Successfully fixed syntax errors in {file_path}")
                return FixResult(True, fixes_applied, backup_path, errors, original_content, fixed_content)
                
            except SyntaxError as e:
                errors.append(f"Fixed content still has syntax errors: {e.msg} at line {e.lineno}")
                logger.error(f"Fixed content still has syntax errors in {file_path}: {e.msg}")
                
                # Restore original content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                
                return FixResult(False, fixes_applied, backup_path, errors, original_content, fixed_content)
            
        except Exception as e:
            errors.append(f"Fix operation failed: {str(e)}")
            logger.error(f"Fix operation failed for {file_path}: {str(e)}")
            return FixResult(False, fixes_applied, backup_path, errors, "", "")
    
    def backup_original_file(self, file_path: str) -> Optional[str]:
        """
        Create a backup of the original file before making changes
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file or None if backup failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{file_path}.backup_{timestamp}"
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {str(e)}")
            return None
    
    def _fix_indentation(self, match):
        """Helper function to fix indentation issues"""
        indent = match.group(1)
        content = match.group(2)
        
        # Basic indentation fix - ensure proper spacing
        if not indent and content.strip():
            return content
        
        return match.group(0)  # Return original if no fix needed
    
    def validate_and_fix_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a file and fix it if needed
        
        Args:
            file_path: Path to the file to validate and fix
            
        Returns:
            Dictionary with validation and fix results
        """
        result = {
            "file_path": file_path,
            "validation": None,
            "fix": None,
            "success": False
        }
        
        try:
            # First validate
            validation_result = self.validate_router_syntax(file_path)
            result["validation"] = validation_result
            
            if validation_result.valid:
                result["success"] = True
                logger.info(f"File {file_path} passed syntax validation")
                return result
            
            # If validation failed, try to fix
            logger.info(f"Attempting to fix syntax errors in {file_path}")
            fix_result = self.fix_common_syntax_errors(file_path)
            result["fix"] = fix_result
            
            if fix_result.success:
                # Validate again after fixing
                post_fix_validation = self.validate_router_syntax(file_path)
                result["validation"] = post_fix_validation
                result["success"] = post_fix_validation.valid
                
                if post_fix_validation.valid:
                    logger.info(f"Successfully fixed and validated {file_path}")
                else:
                    logger.warning(f"File {file_path} still has issues after fixing")
            else:
                logger.error(f"Failed to fix syntax errors in {file_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Validate and fix operation failed for {file_path}: {str(e)}")
            result["error"] = str(e)
            return result
    
    def scan_and_fix_directory(self, directory: str, pattern: str = "*.py") -> Dict[str, Any]:
        """
        Scan a directory for Python files and fix syntax errors
        
        Args:
            directory: Directory to scan
            pattern: File pattern to match (default: *.py)
            
        Returns:
            Dictionary with scan and fix results
        """
        import glob
        
        results = {
            "directory": directory,
            "files_scanned": 0,
            "files_fixed": 0,
            "files_failed": 0,
            "file_results": []
        }
        
        try:
            # Find all Python files
            search_pattern = os.path.join(directory, "**", pattern)
            files = glob.glob(search_pattern, recursive=True)
            
            results["files_scanned"] = len(files)
            
            for file_path in files:
                file_result = self.validate_and_fix_file(file_path)
                results["file_results"].append(file_result)
                
                if file_result["success"]:
                    results["files_fixed"] += 1
                else:
                    results["files_failed"] += 1
            
            logger.info(f"Directory scan complete: {results['files_scanned']} scanned, "
                       f"{results['files_fixed']} fixed, {results['files_failed']} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Directory scan failed for {directory}: {str(e)}")
            results["error"] = str(e)
            return results