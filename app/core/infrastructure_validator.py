"""
Infrastructure Validator
Ensures required directories and files exist before component loading
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of infrastructure validation"""
    success: bool
    message: str
    created_items: List[str]
    errors: List[str]

class InfrastructureValidator:
    """Validates and creates required infrastructure for backend startup"""
    
    def __init__(self):
        self.required_directories = [
            "logs",
            "app/logs",
            "data",
            "temp"
        ]
        
        self.required_files = [
            "logs/trading_engine.log",
            "logs/ai_engine.log", 
            "logs/portfolio.log",
            "logs/broker.log",
            "logs/application.log"
        ]
    
    def validate_logging_infrastructure(self) -> ValidationResult:
        """Check if logging infrastructure exists and is accessible"""
        created_items = []
        errors = []
        
        try:
            # Check and create directories
            for directory in self.required_directories:
                if not os.path.exists(directory):
                    try:
                        os.makedirs(directory, exist_ok=True)
                        created_items.append(f"Created directory: {directory}")
                        logger.info(f"Created missing directory: {directory}")
                    except Exception as e:
                        error_msg = f"Failed to create directory {directory}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    logger.debug(f"Directory exists: {directory}")
            
            # Check and create log files
            for file_path in self.required_files:
                if not os.path.exists(file_path):
                    try:
                        # Ensure parent directory exists
                        parent_dir = os.path.dirname(file_path)
                        if parent_dir and not os.path.exists(parent_dir):
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        # Create empty log file
                        Path(file_path).touch()
                        created_items.append(f"Created log file: {file_path}")
                        logger.info(f"Created missing log file: {file_path}")
                    except Exception as e:
                        error_msg = f"Failed to create log file {file_path}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    logger.debug(f"Log file exists: {file_path}")
            
            success = len(errors) == 0
            message = "Logging infrastructure validated successfully" if success else f"Validation failed with {len(errors)} errors"
            
            return ValidationResult(
                success=success,
                message=message,
                created_items=created_items,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Infrastructure validation failed: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                message=error_msg,
                created_items=created_items,
                errors=[error_msg]
            )
    
    def create_missing_directories(self) -> ValidationResult:
        """Create any missing directories required by the application"""
        created_items = []
        errors = []
        
        try:
            for directory in self.required_directories:
                if not os.path.exists(directory):
                    try:
                        os.makedirs(directory, exist_ok=True)
                        created_items.append(directory)
                        logger.info(f"Created directory: {directory}")
                    except Exception as e:
                        error_msg = f"Failed to create directory {directory}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            success = len(errors) == 0
            message = f"Created {len(created_items)} directories" if success else f"Failed to create {len(errors)} directories"
            
            return ValidationResult(
                success=success,
                message=message,
                created_items=created_items,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Directory creation failed: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                message=error_msg,
                created_items=created_items,
                errors=[error_msg]
            )
    
    def validate_file_permissions(self) -> ValidationResult:
        """Check write access to required directories and files"""
        errors = []
        checked_items = []
        
        try:
            # Check directory write permissions
            for directory in self.required_directories:
                if os.path.exists(directory):
                    if os.access(directory, os.W_OK):
                        checked_items.append(f"Directory writable: {directory}")
                        logger.debug(f"Directory {directory} is writable")
                    else:
                        error_msg = f"Directory not writable: {directory}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    # Try to create directory to test permissions
                    try:
                        os.makedirs(directory, exist_ok=True)
                        checked_items.append(f"Created and verified: {directory}")
                    except Exception as e:
                        error_msg = f"Cannot create directory {directory}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            # Check log file write permissions
            for file_path in self.required_files:
                try:
                    # Try to open file for writing
                    with open(file_path, 'a') as f:
                        pass
                    checked_items.append(f"File writable: {file_path}")
                    logger.debug(f"File {file_path} is writable")
                except Exception as e:
                    error_msg = f"File not writable {file_path}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            success = len(errors) == 0
            message = "All file permissions validated" if success else f"Permission validation failed with {len(errors)} errors"
            
            return ValidationResult(
                success=success,
                message=message,
                created_items=checked_items,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Permission validation failed: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(
                success=False,
                message=error_msg,
                created_items=checked_items,
                errors=[error_msg]
            )
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Run all validation checks and return comprehensive results"""
        results = {}
        
        logger.info("Starting comprehensive infrastructure validation...")
        
        # Run all validation checks
        results['logging'] = self.validate_logging_infrastructure()
        results['directories'] = self.create_missing_directories()
        results['permissions'] = self.validate_file_permissions()
        
        # Log summary
        total_errors = sum(len(result.errors) for result in results.values())
        total_created = sum(len(result.created_items) for result in results.values())
        
        if total_errors == 0:
            logger.info(f"✅ Infrastructure validation completed successfully. Created {total_created} items.")
        else:
            logger.warning(f"⚠️ Infrastructure validation completed with {total_errors} errors. Created {total_created} items.")
        
        return results