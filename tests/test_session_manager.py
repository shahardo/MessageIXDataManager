"""
Tests for SessionManager - application session and settings management
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch, Mock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from managers.session_manager import SessionManager


class TestSessionManager:
    """Test cases for SessionManager"""

    @pytest.fixture(autouse=True)
    def _mock_qsettings(self):
        """Mock QSettings for each test so no real registry access occurs."""
        mock_settings_instance = Mock()
        mock_settings_instance._stored_values = {}
        mock_settings_instance._call_history = []

        # value(key, default) returns stored value or default
        def mock_value(key, default=None):
            return mock_settings_instance._stored_values.get(key, default)

        def mock_setValue(key, value):
            mock_settings_instance._stored_values[key] = value
            mock_settings_instance._call_history.append((key, value))

        mock_settings_instance.value = mock_value
        mock_settings_instance.setValue = mock_setValue
        mock_settings_instance.clear = Mock()

        self.mock_settings = mock_settings_instance

        with patch('managers.session_manager.QSettings', return_value=mock_settings_instance) as self.mock_qsettings_cls:
            yield

    def test_initialization(self):
        """Test SessionManager initialization"""
        manager = SessionManager()

        self.mock_qsettings_cls.assert_called_once_with("MessageIXDataManager", "MessageIXDataManager")
        assert manager.max_recent_scenarios == 5

    def test_initialization_custom_params(self):
        """Test SessionManager initialization with custom parameters"""
        manager = SessionManager("CustomApp", "CustomOrg")

        self.mock_qsettings_cls.assert_called_with("CustomOrg", "CustomApp")

    @patch('os.path.exists')
    def test_get_last_opened_files_empty(self, mock_exists):
        """Test getting last opened files when none exist"""
        mock_exists.return_value = True

        manager = SessionManager()
        input_files = manager.get_last_opened_files("input")
        results_files = manager.get_last_opened_files("results")

        assert input_files == []
        assert results_files == []

    @patch('os.path.exists')
    def test_get_last_opened_files_with_data(self, mock_exists):
        """Test getting last opened files with existing data"""
        mock_exists.return_value = True

        self.mock_settings._stored_values = {
            "recent_input_files": ["/path/to/file1.xlsx", "/path/to/file2.xlsx"],
            "recent_results_files": ["/path/to/results1.xlsx"]
        }

        manager = SessionManager()
        input_files = manager.get_last_opened_files("input")
        results_files = manager.get_last_opened_files("results")

        assert input_files == ["/path/to/file1.xlsx", "/path/to/file2.xlsx"]
        assert results_files == ["/path/to/results1.xlsx"]

    @patch('os.path.exists')
    def test_get_last_opened_files_filters_missing_files(self, mock_exists):
        """Test that missing files are filtered out"""
        mock_exists.side_effect = lambda path: path == "/path/to/existing.xlsx"

        self.mock_settings._stored_values = {
            "recent_input_files": ["/path/to/existing.xlsx", "/path/to/missing.xlsx"]
        }

        manager = SessionManager()
        input_files = manager.get_last_opened_files("input")

        assert input_files == ["/path/to/existing.xlsx"]

    @patch('os.path.exists')
    def test_get_last_opened_files_handles_string_values(self, mock_exists):
        """Test handling of string values (backward compatibility)"""
        mock_exists.return_value = True

        # String instead of list — get_last_opened_files treats non-list as empty
        self.mock_settings._stored_values = {
            "recent_input_files": "/path/to/single_file.xlsx"
        }

        manager = SessionManager()
        input_files = manager.get_last_opened_files("input")

        # Implementation returns [] for non-list values
        assert input_files == []

    @patch('os.path.exists')
    def test_add_recent_file_new_file(self, mock_exists):
        """Test adding a new file to recent files"""
        mock_exists.return_value = True

        manager = SessionManager()
        manager.add_recent_file("/path/to/new_file.xlsx", "input")

        assert self.mock_settings._stored_values["recent_input_files"] == ["/path/to/new_file.xlsx"]

    @patch('os.path.exists')
    def test_add_recent_file_existing_file_moves_to_front(self, mock_exists):
        """Test adding existing file moves it to front"""
        mock_exists.return_value = True

        self.mock_settings._stored_values = {
            "recent_input_files": ["/path/to/old1.xlsx", "/path/to/existing.xlsx", "/path/to/old2.xlsx"]
        }

        manager = SessionManager()
        manager.add_recent_file("/path/to/existing.xlsx", "input")

        assert self.mock_settings._stored_values["recent_input_files"] == [
            "/path/to/existing.xlsx", "/path/to/old1.xlsx", "/path/to/old2.xlsx"
        ]

    @patch('os.path.exists')
    def test_add_recent_file_respects_max_limit(self, mock_exists):
        """Test that max_recent_scenarios limit is respected"""
        mock_exists.return_value = True

        existing_files = [f"/path/to/file{i}.xlsx" for i in range(5)]
        self.mock_settings._stored_values = {
            "recent_input_files": existing_files
        }

        manager = SessionManager()
        manager.add_recent_file("/path/to/new_file.xlsx", "input")

        stored_files = self.mock_settings._stored_values["recent_input_files"]
        assert len(stored_files) == 5
        assert stored_files[0] == "/path/to/new_file.xlsx"
        assert "/path/to/new_file.xlsx" in stored_files
        assert len(set(stored_files[1:]) & set(existing_files)) == 4

    @patch('os.path.exists')
    def test_remove_recent_file(self, mock_exists):
        """Test removing a file from recent files"""
        mock_exists.return_value = True

        self.mock_settings._stored_values = {
            "recent_input_files": ["/path/to/file1.xlsx", "/path/to/file2.xlsx"]
        }

        manager = SessionManager()
        manager.remove_recent_file("/path/to/file1.xlsx", "input")

        assert self.mock_settings._stored_values["recent_input_files"] == ["/path/to/file2.xlsx"]

    @patch('os.path.exists')
    def test_remove_recent_file_handles_string_values(self, mock_exists):
        """Test removing file when stored list has the file"""
        mock_exists.return_value = True

        self.mock_settings._stored_values = {
            "recent_input_files": ["/path/to/single_file.xlsx"]
        }

        manager = SessionManager()
        manager.remove_recent_file("/path/to/single_file.xlsx", "input")

        assert self.mock_settings._stored_values["recent_input_files"] == []

    def test_save_session_state(self):
        """Test saving session state"""
        manager = SessionManager()
        state = {
            'current_view': 'results',
            'selected_input_file': '/path/to/input.xlsx',
            'selected_results_file': '/path/to/results.xlsx'
        }

        manager.save_session_state(state)

        assert self.mock_settings._stored_values['current_view'] == 'results'
        assert self.mock_settings._stored_values['selected_input_file'] == '/path/to/input.xlsx'
        assert self.mock_settings._stored_values['selected_results_file'] == '/path/to/results.xlsx'

    def test_load_session_state(self):
        """Test loading session state"""
        self.mock_settings._stored_values = {
            "current_view": "results",
            "selected_scenario": "test_scenario",
            "last_selected_parameter": "fix_cost",
            "selected_input_file": "/path/to/input.xlsx",
            "selected_results_file": "/path/to/results.xlsx",
        }

        manager = SessionManager()
        state = manager.load_session_state()

        assert state['current_view'] == 'results'
        assert state['selected_scenario'] == 'test_scenario'
        assert state['last_selected_parameter'] == 'fix_cost'
        assert state['selected_input_file'] == '/path/to/input.xlsx'
        assert state['selected_results_file'] == '/path/to/results.xlsx'

    def test_load_session_state_defaults(self):
        """Test loading session state with defaults"""
        manager = SessionManager()
        state = manager.load_session_state()

        assert state['current_view'] == 'input'
        assert state['selected_scenario'] is None
        assert state['last_selected_parameter'] is None
        assert state['selected_input_file'] is None
        assert state['selected_results_file'] is None

    def test_save_ui_prefs(self):
        """Test saving UI preferences"""
        manager = SessionManager()
        prefs = {
            'window_geometry': b'geometry_data',
            'window_state': b'state_data',
            'splitter_sizes': [300, 500]
        }

        manager.save_ui_prefs(prefs)

        assert self.mock_settings._stored_values['ui_window_geometry'] == b'geometry_data'
        assert self.mock_settings._stored_values['ui_window_state'] == b'state_data'
        assert self.mock_settings._stored_values['ui_splitter_sizes'] == [300, 500]

    def test_load_ui_prefs(self):
        """Test loading UI preferences"""
        self.mock_settings._stored_values = {
            "ui_window_geometry": b'geometry_data',
            "ui_window_state": b'state_data',
            "ui_splitter_sizes": [300, 500]
        }

        manager = SessionManager()
        prefs = manager.load_ui_prefs()

        expected_prefs = {
            'window_geometry': b'geometry_data',
            'window_state': b'state_data',
            'splitter_sizes': [300, 500]
        }

        assert prefs == expected_prefs

    def test_load_ui_prefs_defaults(self):
        """Test loading UI preferences with defaults"""
        manager = SessionManager()
        prefs = manager.load_ui_prefs()

        expected_prefs = {
            'window_geometry': None,
            'window_state': None,
            'splitter_sizes': {}
        }

        assert prefs == expected_prefs

    def test_clear_session_data(self):
        """Test clearing all session data"""
        manager = SessionManager()
        manager.clear_session_data()

        self.mock_settings.clear.assert_called_once()

    @patch('os.path.exists')
    def test_integration_workflow(self, mock_exists):
        """Test a complete workflow of session management"""
        mock_exists.return_value = True

        manager = SessionManager()

        # Start with empty state
        assert manager.get_last_opened_files("input") == []

        # Add some files
        manager.add_recent_file("/path/to/input1.xlsx", "input")
        manager.add_recent_file("/path/to/input2.xlsx", "input")
        manager.add_recent_file("/path/to/results1.xlsx", "results")

        # Check they were added
        input_files = manager.get_last_opened_files("input")
        results_files = manager.get_last_opened_files("results")
        assert "/path/to/input1.xlsx" in input_files
        assert "/path/to/input2.xlsx" in input_files
        assert results_files == ["/path/to/results1.xlsx"]

        # Save session state
        session_state = {
            'current_view': 'results',
            'selected_results_file': '/path/to/results1.xlsx'
        }
        manager.save_session_state(session_state)

        # Load session state
        loaded_state = manager.load_session_state()
        assert loaded_state['current_view'] == 'results'
        assert loaded_state['selected_results_file'] == '/path/to/results1.xlsx'

        # Remove a file
        manager.remove_recent_file("/path/to/input1.xlsx", "input")
        input_files = manager.get_last_opened_files("input")
        assert "/path/to/input1.xlsx" not in input_files
        assert "/path/to/input2.xlsx" in input_files
