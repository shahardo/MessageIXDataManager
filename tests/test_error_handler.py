"""
Tests for the comprehensive error handling framework.
"""

import pytest
import os
import logging
import tempfile
from unittest.mock import Mock, patch, MagicMock
from src.utils.error_handler import ErrorHandler, SafeOperation, with_error_handling


class TestErrorHandler:
    """Test the ErrorHandler class functionality"""

    def test_handle_file_loading_error_file_not_found(self):
        """Test handling of FileNotFoundError"""
        handler = ErrorHandler()
        error = FileNotFoundError("No such file or directory: 'nonexistent.xlsx'")
        logger = Mock()

        result = handler.handle_file_loading_error(error, "nonexistent.xlsx", logger)

        assert "File not found: nonexistent.xlsx" in result
        logger.error.assert_called_once()

    def test_handle_file_loading_error_permission_denied(self):
        """Test handling of PermissionError"""
        handler = ErrorHandler()
        error = PermissionError("Permission denied")
        logger = Mock()

        result = handler.handle_file_loading_error(error, "protected.xlsx", logger)

        assert "Permission denied accessing: protected.xlsx" in result
        logger.error.assert_called_once()

    def test_handle_file_loading_error_invalid_format(self):
        """Test handling of invalid file format errors"""
        handler = ErrorHandler()
        error = ValueError("Invalid file format detected")
        logger = Mock()

        result = handler.handle_file_loading_error(error, "invalid.xlsx", logger)

        assert "Invalid Excel format in: invalid.xlsx" in result
        logger.error.assert_called_once()

    def test_handle_file_loading_error_corrupt_file(self):
        """Test handling of corrupt file errors"""
        handler = ErrorHandler()
        error = Exception("File is corrupt")
        logger = Mock()

        result = handler.handle_file_loading_error(error, "corrupt.xlsx", logger)

        assert "Corrupted Excel file: corrupt.xlsx" in result
        logger.error.assert_called_once()

    def test_handle_data_processing_error_memory(self):
        """Test handling of memory-related errors"""
        handler = ErrorHandler()
        error = MemoryError("Out of memory")
        logger = Mock()

        result = handler.handle_data_processing_error(error, "parameter processing", logger)

        assert "Insufficient memory for parameter processing" in result
        logger.error.assert_called_once()

    def test_handle_data_processing_error_column_issue(self):
        """Test handling of column-related errors"""
        handler = ErrorHandler()
        error = ValueError("Column 'invalid' not found")
        logger = Mock()

        result = handler.handle_data_processing_error(error, "data transformation", logger)

        assert "Data format issue in data transformation" in result
        logger.error.assert_called_once()

    def test_handle_solver_error_not_found(self):
        """Test handling of solver not found errors"""
        handler = ErrorHandler()
        error = FileNotFoundError("cplex not found")
        logger = Mock()

        result = handler.handle_solver_error(error, "cplex", logger)

        assert "Solver 'cplex' not found in system PATH" in result
        logger.error.assert_called_once()

    def test_handle_solver_error_timeout(self):
        """Test handling of solver timeout errors"""
        handler = ErrorHandler()
        error = Exception("Solver timed out after 3600 seconds")
        logger = Mock()

        result = handler.handle_solver_error(error, "gurobi", logger)

        assert "Solver 'gurobi' timed out during execution" in result
        logger.error.assert_called_once()

    def test_handle_ui_error_generic(self):
        """Test handling of generic UI errors"""
        handler = ErrorHandler()
        error = RuntimeError("Widget not initialized")
        logger = Mock()

        result = handler.handle_ui_error(error, "chart display", logger)

        assert "Interface error in chart display: Widget not initialized" in result
        logger.error.assert_called_once()

    def test_handle_validation_error_no_issues(self):
        """Test handling validation with no issues"""
        handler = ErrorHandler()
        logger = Mock()

        result = handler.handle_validation_error([], logger)

        assert result == ""
        logger.warning.assert_not_called()

    def test_handle_validation_error_with_issues(self):
        """Test handling validation with issues"""
        handler = ErrorHandler()
        issues = ["Missing required column", "Invalid data type"]
        logger = Mock()

        result = handler.handle_validation_error(issues, logger)

        assert "Data validation issues found: 2 issues" in result
        assert logger.warning.call_count == 3  # One for summary + two for issues


class TestSafeOperation:
    """Test the SafeOperation context manager"""

    def test_successful_operation(self):
        """Test successful operation with no errors"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("test operation", handler, logger, on_error) as safe_op:
            # Simulate successful work
            pass

        assert not safe_op.error_occurred
        on_error.assert_not_called()

    def test_file_loading_error_handling(self):
        """Test error handling for file loading operations"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("file loading: test.xlsx", handler, logger, on_error) as safe_op:
            raise FileNotFoundError("File not found")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        args = on_error.call_args[0][0]
        assert "File not found: test.xlsx" in args

    def test_data_processing_error_handling(self):
        """Test error handling for data processing operations"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("parameter processing", handler, logger, on_error) as safe_op:
            raise MemoryError("Out of memory")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        args = on_error.call_args[0][0]
        assert "Insufficient memory for parameter processing" in args

    def test_solver_error_handling(self):
        """Test error handling for solver operations"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("solver execution", handler, logger, on_error) as safe_op:
            raise Exception("Solver license expired")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        args = on_error.call_args[0][0]
        assert "license" in args.lower()

    def test_ui_error_handling(self):
        """Test error handling for UI operations"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("chart display", handler, logger, on_error) as safe_op:
            raise RuntimeError("Chart rendering failed")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        args = on_error.call_args[0][0]
        assert "Interface error in chart display" in args

    def test_generic_error_handling(self):
        """Test generic error handling for unrecognized operations"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("unknown operation", handler, logger, on_error) as safe_op:
            raise ValueError("Something went wrong")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        args = on_error.call_args[0][0]
        assert "Operation 'unknown operation' failed: Something went wrong" in args


class TestErrorHandlingDecorator:
    """Test the error handling decorator"""

    def test_decorator_success(self):
        """Test decorator with successful function"""
        handler = ErrorHandler()
        logger = Mock()

        @with_error_handling("test function", handler, logger)
        def test_func():
            return "success"

        result, success = test_func()

        assert result == "success"
        assert success is True

    def test_decorator_with_error(self):
        """Test decorator with function that raises error"""
        handler = ErrorHandler()
        logger = Mock()

        @with_error_handling("test function", handler, logger)
        def test_func():
            raise ValueError("Test error")

        result, success = test_func()

        assert result is None  # Error suppressed, returns None
        assert success is False


class TestErrorHandlerIntegration:
    """Integration tests for error handling in real scenarios"""

    def test_file_loading_integration(self):
        """Test complete file loading error scenario"""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from managers.input_manager import InputManager

        # Create a temporary invalid file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp.write(b"not an excel file")
            invalid_file = tmp.name

        try:
            manager = InputManager()

            # This should handle the error gracefully
            with pytest.raises(ValueError):
                manager.load_file(invalid_file)

        finally:
            os.unlink(invalid_file)

    def test_nonexistent_file_integration(self):
        """Test loading non-existent file"""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from managers.input_manager import InputManager

        manager = InputManager()

        # This should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            manager.load_file("nonexistent_file.xlsx")

    def test_safe_operation_with_logger(self):
        """Test SafeOperation with actual logger"""
        handler = ErrorHandler()
        logger = Mock()
        on_error = Mock()

        with SafeOperation("test with logger", handler, logger, on_error) as safe_op:
            raise FileNotFoundError("Test file not found")

        assert safe_op.error_occurred
        on_error.assert_called_once()
        logger.error.assert_called_once()


class TestErrorHandlerWithoutLogger:
    """Test ErrorHandler functionality without logger"""

    def test_error_handler_without_logger(self):
        """Test that ErrorHandler works without logger parameter"""
        handler = ErrorHandler()

        # Should not raise any exceptions
        result = handler.handle_file_loading_error(FileNotFoundError("test"), "test.xlsx")

        assert "File not found: test.xlsx" in result

    def test_safe_operation_without_logger(self):
        """Test SafeOperation without logger"""
        handler = ErrorHandler()
        on_error = Mock()

        with SafeOperation("test operation", handler, on_error=on_error) as safe_op:
            raise ValueError("test error")

        assert safe_op.error_occurred
        on_error.assert_called_once()
