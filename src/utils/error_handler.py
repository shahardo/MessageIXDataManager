"""
Error Handling Framework for MessageIX Data Manager

Provides centralized error handling, user-friendly messages, and logging.
"""

import os
import logging
from typing import Optional, Callable, Any


class ErrorHandler:
    """
    ErrorHandler class for centralized error handling and user feedback.

    Provides comprehensive error handling utilities for file loading, data processing,
    solver execution, UI errors, and validation issues with user-friendly messages
    and proper logging.
    """

    @staticmethod
    def handle_file_loading_error(error: Exception, file_path: str, logger: Optional[logging.Logger] = None) -> str:
        """Handle file loading errors with appropriate user feedback"""
        error_msg = f"Failed to load file {os.path.basename(file_path)}: {str(error)}"

        if isinstance(error, FileNotFoundError):
            user_msg = f"File not found: {file_path}"
        elif isinstance(error, PermissionError):
            user_msg = f"Permission denied accessing: {file_path}"
        elif "invalid file format" in str(error).lower():
            user_msg = f"Invalid Excel format in: {os.path.basename(file_path)}"
        elif "corrupt" in str(error).lower():
            user_msg = f"Corrupted Excel file: {os.path.basename(file_path)}"
        elif "workbook" in str(error).lower():
            user_msg = f"Unable to read Excel workbook: {os.path.basename(file_path)}"
        else:
            user_msg = f"Error loading file: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return user_msg

    @staticmethod
    def handle_data_processing_error(error: Exception, context: str, logger: Optional[logging.Logger] = None) -> str:
        """Handle data processing errors"""
        error_msg = f"Data processing error in {context}: {str(error)}"

        if "memory" in str(error).lower():
            user_msg = f"Insufficient memory for {context}. Try processing smaller files."
        elif "column" in str(error).lower():
            user_msg = f"Data format issue in {context}: {str(error)}"
        elif "type" in str(error).lower():
            user_msg = f"Data type mismatch in {context}: {str(error)}"
        else:
            user_msg = f"Data processing failed in {context}: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return user_msg

    @staticmethod
    def handle_solver_error(error: Exception, solver_name: str, logger: Optional[logging.Logger] = None) -> str:
        """Handle solver execution errors"""
        error_msg = f"Solver '{solver_name}' execution error: {str(error)}"

        if "not found" in str(error).lower():
            user_msg = f"Solver '{solver_name}' not found in system PATH"
        elif "timeout" in str(error).lower() or "timed out" in str(error).lower():
            user_msg = f"Solver '{solver_name}' timed out during execution"
        elif "license" in str(error).lower():
            user_msg = f"Solver '{solver_name}' license issue: {str(error)}"
        else:
            user_msg = f"Solver execution failed: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return user_msg

    @staticmethod
    def handle_ui_error(error: Exception, context: str, logger: Optional[logging.Logger] = None) -> str:
        """Handle UI-related errors"""
        error_msg = f"UI error in {context}: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return f"Interface error in {context}: {str(error)}"

    @staticmethod
    def handle_validation_error(validation_issues: list, logger: Optional[logging.Logger] = None) -> str:
        """Handle data validation errors"""
        if not validation_issues:
            return ""

        error_msg = f"Validation found {len(validation_issues)} issue(s)"
        if logger:
            logger.warning(error_msg)
            for issue in validation_issues:
                logger.warning(f"  - {issue}")

        return f"Data validation issues found: {len(validation_issues)} issues"


class SafeOperation:
    """
    SafeOperation class for context manager with automatic error handling.

    Provides a context manager that automatically handles errors during operations,
    logging them appropriately and providing user-friendly error messages.
    """

    def __init__(self, operation_name: str, error_handler: Optional[ErrorHandler] = None,
                 logger: Optional[logging.Logger] = None, on_error: Optional[Callable[[str], None]] = None):
        self.operation_name = operation_name
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logger
        self.on_error = on_error
        self.error_occurred = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, _):
        if exc_type:
            self.error_occurred = True
            error_msg = self._handle_error(exc_val)
            if self.on_error:
                self.on_error(error_msg)
            # Return True to suppress the exception
            return True
        return False

    def _handle_error(self, error: Exception) -> str:
        """Handle the error based on operation type"""
        if "file" in self.operation_name.lower() and "load" in self.operation_name.lower():
            # Try to extract file path from operation name (format: "file loading: filename.xlsx")
            if ":" in self.operation_name:
                file_path = self.operation_name.split(":", 1)[1].strip()
            else:
                file_path = getattr(error, 'filename', '') or 'unknown file'
            return self.error_handler.handle_file_loading_error(error, file_path, self.logger)
        elif "process" in self.operation_name.lower() or "parse" in self.operation_name.lower():
            return self.error_handler.handle_data_processing_error(error, self.operation_name, self.logger)
        elif "solver" in self.operation_name.lower():
            solver_name = getattr(self, 'solver_name', 'unknown')
            return self.error_handler.handle_solver_error(error, solver_name, self.logger)
        elif "ui" in self.operation_name.lower() or "display" in self.operation_name.lower():
            return self.error_handler.handle_ui_error(error, self.operation_name, self.logger)
        else:
            # Generic error handling
            error_msg = f"Operation '{self.operation_name}' failed: {str(error)}"
            if self.logger:
                self.logger.error(error_msg, exc_info=True)
            return error_msg


def with_error_handling(operation_name: str, error_handler: Optional[ErrorHandler] = None,
                       logger: Optional[logging.Logger] = None):
    """
    Decorator for functions that need comprehensive error handling

    Args:
        operation_name: Name of the operation for error context
        error_handler: ErrorHandler instance to use
        logger: Logger instance to use

    Returns:
        Decorated function that handles errors gracefully
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = None
            with SafeOperation(operation_name, error_handler, logger) as safe_op:
                result = func(*args, **kwargs)
            return result, not safe_op.error_occurred
        return wrapper
    return decorator
