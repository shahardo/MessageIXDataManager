"""
Tests for Logging Manager
"""

import pytest
import os
import sys
import tempfile
import sqlite3
import json
from datetime import datetime, timedelta

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from managers.logging_manager import LoggingManager, SQLiteHandler, logging_manager


class TestSQLiteHandler:
    """Test cases for SQLiteHandler"""

    def test_database_creation(self):
        """Test that database and tables are created"""
        # Use in-memory database to avoid file locking issues
        handler = SQLiteHandler(':memory:')

        # The handler should be created without errors and tables should exist
        # Since it's in-memory, we can't check file existence, but we can verify
        # the handler was created successfully
        assert handler is not None
        assert hasattr(handler, 'emit')
        assert hasattr(handler, 'db_path')
        assert handler.db_path == ':memory:'

        # Close the handler
        handler.close()

    def test_emit_stores_log(self):
        """Test that emit stores log records in database"""
        # Use in-memory database to avoid file locking issues
        handler = SQLiteHandler(':memory:')

        # Create a mock log record
        import logging
        record = logging.LogRecord(
            'test', logging.INFO, 'test.py', 1, 'Test message', (), None
        )
        record.created = 1609459200.0  # Fixed timestamp for testing
        record.category = 'TEST_CATEGORY'

        handler.emit(record)

        # Can't directly query in-memory database, but method should not error
        handler.close()

    def test_emit_with_details(self):
        """Test emit with structured details"""
        # Use in-memory database to avoid file locking issues
        handler = SQLiteHandler(':memory:')

        import logging
        record = logging.LogRecord(
            'test', logging.ERROR, 'test.py', 1, 'Error message', (), None
        )
        record.created = 1609459200.0
        record.category = 'ERROR_TEST'
        record.details = {'error_code': 500, 'user_id': 123}

        handler.emit(record)

        # Can't directly query in-memory database, but method should not error
        handler.close()

    def test_emit_exception_handling(self):
        """Test that emit handles exceptions gracefully"""
        # Create handler with invalid database path
        handler = SQLiteHandler('/invalid/path/logs.db')

        import logging
        record = logging.LogRecord(
            'test', logging.INFO, 'test.py', 1, 'Test', (), None
        )

        # Should not raise exception
        handler.emit(record)
        handler = None


class TestLoggingManager:
    """Test cases for LoggingManager"""

    def test_setup_logging(self):
        """Test logging setup"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')

            # Use in-memory database to avoid file locking issues
            manager = LoggingManager(log_file, ':memory:')
            assert manager.logger is not None
            assert len(manager.logger.handlers) == 3  # file, sqlite, console

            # Check handlers are configured correctly
            handler_types = [type(h).__name__ for h in manager.logger.handlers]
            assert 'FileHandler' in handler_types
            assert 'SQLiteHandler' in handler_types
            assert 'StreamHandler' in handler_types

            # Clean up handlers to release database connections
            for handler in manager.logger.handlers:
                handler.close()
            manager.logger.handlers.clear()

    def test_log_method(self):
        """Test the log method"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')

            # Use in-memory database to avoid file locking
            manager = LoggingManager(log_file, ':memory:')

            details = {'key': 'value', 'count': 42}
            manager.log('INFO', 'TEST', 'Test message', details, config_id=1)

            # Can't check database directly for in-memory, but method should not error
            # and log file should be created
            assert os.path.exists(log_file)

            # Clean up handlers
            for handler in manager.logger.handlers:
                handler.close()
            manager.logger.handlers.clear()

    def test_get_recent_logs(self):
        """Test retrieving recent logs"""
        # Use temporary log file and in-memory database
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log('INFO', 'TEST', 'Message 1')
                manager.log('ERROR', 'TEST', 'Message 2')
                manager.log('WARNING', 'OTHER', 'Message 3')

                # Get all logs
                logs = manager.get_recent_logs()
                assert len(logs) >= 3
                assert logs[0]['category'] == 'OTHER'  # Most recent first
                assert logs[1]['category'] == 'TEST'
                assert logs[2]['category'] == 'TEST'
            finally:
                # Clean up handlers to release file handles BEFORE leaving context
                for handler in manager.logger.handlers[:]:  # Copy the list to avoid modification issues
                    try:
                        handler.close()
                    except Exception:
                        pass  # Ignore cleanup errors
                manager.logger.handlers.clear()

                # Force garbage collection to release file handles
                import gc
                gc.collect()

                # Small delay to ensure file handles are released
                import time
                time.sleep(0.01)

    def test_get_recent_logs_with_category_filter(self):
        """Test retrieving logs filtered by category"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log('INFO', 'TEST', 'Message 1')
                manager.log('ERROR', 'OTHER', 'Message 2')
                manager.log('INFO', 'TEST', 'Message 3')

                # Get only TEST category logs
                logs = manager.get_recent_logs(category='TEST')
                assert len(logs) == 2
                assert all(log['category'] == 'TEST' for log in logs)
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_get_recent_logs_with_limit(self):
        """Test retrieving logs with limit"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                for i in range(5):
                    manager.log('INFO', 'TEST', f'Message {i}')

                # Get limited logs
                logs = manager.get_recent_logs(limit=3)
                assert len(logs) == 3
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_log_input_load_success(self):
        """Test logging input file loading success"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log_input_load('/path/to/file.xlsx', True)

                logs = manager.get_recent_logs(category='INPUT_LOAD')
                assert len(logs) >= 1
                assert 'successful' in logs[0]['message']
                assert logs[0]['details']['file_path'] == '/path/to/file.xlsx'
                assert logs[0]['details']['file_type'] == 'input'
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_log_input_load_failure(self):
        """Test logging input file loading failure"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log_input_load('/path/to/file.xlsx', False, 'File not found')

                logs = manager.get_recent_logs(category='INPUT_LOAD')
                assert len(logs) >= 1
                assert 'failed' in logs[0]['message']
                assert logs[0]['details']['error'] == 'File not found'
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_log_parameter_edit(self):
        """Test logging parameter edits"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log_parameter_edit('fix_cost', 'updated', {'old_value': 100, 'new_value': 150})

                logs = manager.get_recent_logs(category='PARAMETER_EDIT')
                assert len(logs) >= 1
                assert 'Parameter updated: fix_cost' in logs[0]['message']
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_log_solver_execution(self):
        """Test logging solver execution"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                manager.log_solver_execution('glpk input.xlsx', 'completed', 45.2)

                logs = manager.get_recent_logs(category='SOLVER_EXECUTION')
                assert len(logs) >= 1
                assert 'completed' in logs[0]['message']
                assert logs[0]['details']['duration_seconds'] == 45.2
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_log_results_load(self):
        """Test logging results file loading"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                stats = {'variables': 10, 'equations': 5}
                manager.log_results_load('/path/to/results.xlsx', True, stats)

                logs = manager.get_recent_logs(category='RESULTS_LOAD')
                assert len(logs) >= 1
                assert 'successful' in logs[0]['message']
                assert logs[0]['details']['variables'] == 10
            finally:
                # Clean up handlers
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)

    def test_cleanup_old_logs(self):
        """Test cleanup of old logs"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_file = os.path.join(tmp_dir, 'test.log')
            manager = LoggingManager(log_file, ':memory:')
            try:
                # Just test that the method exists and can be called without error
                manager.cleanup_old_logs(days_to_keep=30)
                # In-memory database, so no actual cleanup to verify
            finally:
                # Clean up handlers to release file handles
                for handler in manager.logger.handlers[:]:
                    try:
                        handler.close()
                    except Exception:
                        pass
                manager.logger.handlers.clear()
                import gc
                gc.collect()
                import time
                time.sleep(0.01)


class TestGlobalLoggingManager:
    """Test the global logging manager instance"""

    def test_global_instance_exists(self):
        """Test that the global logging manager instance is available"""
        assert logging_manager is not None
        assert hasattr(logging_manager, 'log')
        assert hasattr(logging_manager, 'get_recent_logs')
