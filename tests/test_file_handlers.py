"""
Tests for File Handler classes
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import os

from managers.file_handlers import InputFileHandler, ResultsFileHandler, AutoLoadHandler
from managers.input_manager import InputManager
from managers.results_analyzer import ResultsAnalyzer
from managers.session_manager import SessionManager
from core.data_models import ScenarioData, Parameter


class TestInputFileHandler:
    """Test cases for InputFileHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_input_manager = Mock(spec=InputManager)
        self.mock_scenario = Mock(spec=ScenarioData)
        self.mock_scenario.parameters = [Mock(spec=Parameter), Mock(spec=Parameter)]
        self.mock_scenario.sets = [Mock(), Mock(), Mock()]

        # Mock the load_excel_file method
        self.mock_input_manager.load_excel_file.return_value = self.mock_scenario
        self.mock_input_manager.validate_scenario.return_value = {'valid': True, 'issues': []}

        self.handler = InputFileHandler(self.mock_input_manager)

    def test_initialization(self):
        """Test handler initialization"""
        assert self.handler.input_manager == self.mock_input_manager

    @patch('managers.file_handlers.SafeOperation')
    @patch('managers.logging_manager.logging_manager.log_input_load')
    def test_load_files_success(self, mock_log, mock_safe_op):
        """Test successful loading of multiple input files"""
        mock_safe_op.return_value.__enter__ = Mock(return_value=None)
        mock_safe_op.return_value.__exit__ = Mock(return_value=None)

        file_paths = ['file1.xlsx', 'file2.xlsx']

        result = self.handler.load_files(
            file_paths,
            lambda v, m: None,  # progress_callback
            lambda m: None      # console_callback
        )

        assert result['loaded_files'] == file_paths
        assert result['total_parameters'] == 4  # 2 files * 2 parameters each
        assert result['total_sets'] == 6       # 2 files * 3 sets each
        assert result['validation_issues'] == []

        # Verify load_excel_file was called for each file
        assert self.mock_input_manager.load_excel_file.call_count == 2
        # Check that the calls were made with the correct file paths and callable progress callbacks
        call_args_list = self.mock_input_manager.load_excel_file.call_args_list
        assert len(call_args_list) == 2
        assert call_args_list[0][0][0] == 'file1.xlsx'  # First arg is file path
        assert callable(call_args_list[0][0][1])  # Second arg is progress callback
        assert call_args_list[1][0][0] == 'file2.xlsx'  # First arg is file path
        assert callable(call_args_list[1][0][1])  # Second arg is progress callback

    @patch('managers.file_handlers.SafeOperation')
    def test_load_files_with_validation_issues(self, mock_safe_op):
        """Test loading files with validation issues"""
        mock_safe_op.return_value.__enter__ = Mock(return_value=None)
        mock_safe_op.return_value.__exit__ = Mock(return_value=None)

        # Mock validation with issues
        self.mock_input_manager.validate_scenario.return_value = {
            'valid': False,
            'issues': ['Issue 1', 'Issue 2']
        }

        file_paths = ['file1.xlsx']

        result = self.handler.load_files(
            file_paths,
            lambda v, m: None,
            lambda m: None
        )

        assert result['validation_issues'] == ['Issue 1', 'Issue 2']

    def test_load_files_with_error(self):
        """Test loading files when an error occurs"""
        # Mock the input manager to raise an exception during loading
        self.mock_input_manager.load_excel_file.side_effect = Exception("Load failed")

        console_messages = []
        progress_values = []

        def console_callback(msg):
            console_messages.append(msg)

        def progress_callback(value, msg):
            progress_values.append((value, msg))

        file_paths = ['file1.xlsx']

        result = self.handler.load_files(
            file_paths,
            progress_callback,
            console_callback
        )

        # Should handle error gracefully
        assert isinstance(result, dict)
        assert result['loaded_files'] == []  # No files loaded due to error
        # Should have called the error callback
        assert len(console_messages) > 0
        assert any("Failed to load file file1.xlsx" in msg or "Load failed" in msg for msg in console_messages)
        # Progress should be cleared on error
        assert any(value == 0 for value, msg in progress_values)


class TestResultsFileHandler:
    """Test cases for ResultsFileHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_results_analyzer = Mock(spec=ResultsAnalyzer)
        self.mock_results_analyzer.load_results_file.return_value = Mock()
        self.mock_results_analyzer.get_summary_stats.return_value = {
            'total_variables': 5,
            'total_equations': 3
        }

        self.handler = ResultsFileHandler(self.mock_results_analyzer)

    def test_initialization(self):
        """Test handler initialization"""
        assert self.handler.results_analyzer == self.mock_results_analyzer

    @patch('managers.file_handlers.SafeOperation')
    @patch('managers.logging_manager.logging_manager.log_results_load')
    def test_load_files_success(self, mock_log, mock_safe_op):
        """Test successful loading of multiple results files"""
        mock_safe_op.return_value.__enter__ = Mock(return_value=None)
        mock_safe_op.return_value.__exit__ = Mock(return_value=None)

        file_paths = ['results1.xlsx', 'results2.xlsx']

        result = self.handler.load_files(
            file_paths,
            lambda v, m: None,
            lambda m: None
        )

        assert result['loaded_files'] == file_paths
        assert result['total_variables'] == 10  # 2 files * 5 variables each
        assert result['total_equations'] == 6   # 2 files * 3 equations each

        # Verify load_results_file was called for each file
        assert self.mock_results_analyzer.load_results_file.call_count == 2

    def test_load_files_with_error(self):
        """Test loading results files when an error occurs"""
        # Mock the results analyzer to raise an exception during loading
        self.mock_results_analyzer.load_results_file.side_effect = Exception("Load failed")

        console_messages = []

        def console_callback(msg):
            console_messages.append(msg)

        file_paths = ['results1.xlsx']

        result = self.handler.load_files(
            file_paths,
            lambda v, m: None,
            console_callback
        )

        # Should handle error gracefully
        assert isinstance(result, dict)
        assert result['loaded_files'] == []  # No files loaded due to error
        # Should have called the error callback
        assert len(console_messages) > 0
        assert any("Failed to load file results1.xlsx" in msg or "Load failed" in msg for msg in console_messages)


class TestAutoLoadHandler:
    """Test cases for AutoLoadHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_input_manager = Mock(spec=InputManager)
        self.mock_results_analyzer = Mock(spec=ResultsAnalyzer)
        self.mock_session_manager = Mock(spec=SessionManager)

        # Mock session manager methods
        self.mock_session_manager.get_last_opened_files.side_effect = lambda file_type: {
            "input": ["input1.xlsx", "input2.xlsx"],
            "results": ["results1.xlsx"]
        }[file_type]

        # Mock scenario for successful loading
        self.mock_scenario = Mock(spec=ScenarioData)
        self.mock_scenario.parameters = [Mock(spec=Parameter)]
        self.mock_input_manager.load_excel_file.return_value = self.mock_scenario

        # Mock results for successful loading
        self.mock_results = Mock()
        self.mock_results_analyzer.load_results_file.return_value = self.mock_results
        self.mock_results_analyzer.get_summary_stats.return_value = {'total_variables': 10}

        self.handler = AutoLoadHandler(
            self.mock_input_manager,
            self.mock_results_analyzer,
            self.mock_session_manager
        )

    def test_initialization(self):
        """Test handler initialization"""
        assert self.handler.input_manager == self.mock_input_manager
        assert self.handler.results_analyzer == self.mock_results_analyzer
        assert self.handler.session_manager == self.mock_session_manager

    @patch('os.path.exists')
    def test_auto_load_files_success(self, mock_exists):
        """Test successful auto-loading of all files"""
        mock_exists.return_value = True

        console_messages = []

        def console_callback(msg):
            console_messages.append(msg)

        result = self.handler.auto_load_files(console_callback, lambda v, m: None)

        loaded_input, loaded_results = result

        assert loaded_input == ["input1.xlsx", "input2.xlsx"]
        assert loaded_results == ["results1.xlsx"]

        # Verify input files were loaded
        assert self.mock_input_manager.load_excel_file.call_count == 2

        # Verify results files were loaded
        assert self.mock_results_analyzer.load_results_file.call_count == 1

        # Check console messages
        assert any("Auto-loading input file: input1.xlsx" in msg for msg in console_messages)
        assert any("Auto-loading input file: input2.xlsx" in msg for msg in console_messages)
        assert any("Auto-loading results file: results1.xlsx" in msg for msg in console_messages)

    @patch('os.path.exists')
    def test_auto_load_files_missing_files(self, mock_exists):
        """Test auto-loading when some files don't exist"""
        def exists_side_effect(path):
            return path in ["input1.xlsx"]  # Only first input file exists

        mock_exists.side_effect = exists_side_effect

        console_messages = []

        def console_callback(msg):
            console_messages.append(msg)

        result = self.handler.auto_load_files(console_callback, lambda v, m: None)

        loaded_input, loaded_results = result

        assert loaded_input == ["input1.xlsx"]  # Only existing file loaded
        assert loaded_results == []  # No results files exist

        # Should only load the existing input file
        assert self.mock_input_manager.load_excel_file.call_count == 1
        assert self.mock_results_analyzer.load_results_file.call_count == 0

    @patch('os.path.exists')
    def test_auto_load_files_load_error(self, mock_exists):
        """Test auto-loading when loading fails"""
        mock_exists.return_value = True
        self.mock_input_manager.load_excel_file.side_effect = Exception("Load failed")
        self.mock_results_analyzer.load_results_file.side_effect = Exception("Results load failed")

        console_messages = []

        def console_callback(msg):
            console_messages.append(msg)

        result = self.handler.auto_load_files(console_callback, lambda v, m: None)

        loaded_input, loaded_results = result

        assert loaded_input == []  # No files loaded due to error
        assert loaded_results == []

        # Check that errors were logged
        assert any("Failed to auto-load input file input1.xlsx: Load failed" in msg for msg in console_messages)
        assert any("Failed to auto-load results file results1.xlsx: Results load failed" in msg for msg in console_messages)

    def test_auto_load_files_empty_lists(self):
        """Test auto-loading when no files are configured"""
        self.mock_session_manager.get_last_opened_files.side_effect = lambda file_type: []

        result = self.handler.auto_load_files(lambda m: None, lambda v, m: None)

        loaded_input, loaded_results = result

        assert loaded_input == []
        assert loaded_results == []

        # No loading should occur
        assert self.mock_input_manager.load_excel_file.call_count == 0
        assert self.mock_results_analyzer.load_results_file.call_count == 0
