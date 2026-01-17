"""
Session management for MessageIX Data Manager

Handles persistence of application state including:
- Last opened files
- UI state (selected files, view mode, parameters)
- User preferences
"""

import os
from typing import List, Optional, Dict, Any
from PyQt5.QtCore import QSettings


class SessionManager:
    """
    Manages application session state and persistence.

    Provides centralized handling of:
    - Recently opened files
    - Current UI state
    - User preferences
    """

    def __init__(self, app_name: str = "MessageIXDataManager", org_name: str = "MessageIXDataManager"):
        """
        Initialize the session manager.

        Args:
            app_name: Application name for settings
            org_name: Organization name for settings
        """
        self.settings = QSettings(org_name, app_name)
        self.max_recent_files = 5

    def get_last_opened_files(self, file_type: str) -> List[str]:
        """
        Get the list of last opened files for a specific type.

        Args:
            file_type: Either "input" or "results"

        Returns:
            List of file paths that exist on disk
        """
        key = f"last_{file_type}_files"
        files = self.settings.value(key, [])

        # Ensure it's a list
        if isinstance(files, str):
            files = [files]

        # Filter out files that no longer exist
        existing_files = [f for f in files if f and os.path.exists(f)]

        # Update settings if we filtered out missing files
        if len(existing_files) != len(files):
            self.settings.setValue(key, existing_files)

        return existing_files

    def add_recent_file(self, file_path: str, file_type: str) -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to the file
            file_type: Either "input" or "results"
        """
        key = f"last_{file_type}_files"
        files = self.settings.value(key, [])

        # Ensure it's a list
        if isinstance(files, str):
            files = [files]

        # Remove if already exists (to move to front)
        if file_path in files:
            files.remove(file_path)

        # Add to front of list
        files.insert(0, file_path)

        # Keep only the most recent files
        files = files[:self.max_recent_files]

        self.settings.setValue(key, files)

    def remove_recent_file(self, file_path: str, file_type: str) -> None:
        """
        Remove a file from the recent files list.

        Args:
            file_path: Path to the file
            file_type: Either "input" or "results"
        """
        key = f"last_{file_type}_files"
        files = self.settings.value(key, [])

        # Ensure it's a list
        if isinstance(files, str):
            files = [files]

        if file_path in files:
            files.remove(file_path)
            self.settings.setValue(key, files)

    def save_session_state(self, state: Dict[str, Any]) -> None:
        """
        Save the current session state.

        Args:
            state: Dictionary containing session state
        """
        for key, value in state.items():
            self.settings.setValue(key, value)

    def load_session_state(self) -> Dict[str, Any]:
        """
        Load the saved session state.

        Returns:
            Dictionary containing session state
        """
        return {
            'current_view': self.settings.value("current_view", "input"),
            'selected_input_file': self.settings.value("selected_input_file", None),
            'selected_results_file': self.settings.value("selected_results_file", None),
            'last_selected_input_parameter': self.settings.value("last_selected_input_parameter", None),
            'last_selected_results_parameter': self.settings.value("last_selected_results_parameter", None),
        }

    def save_ui_prefs(self, prefs: Dict[str, Any]) -> None:
        """
        Save UI preferences.

        Args:
            prefs: Dictionary containing UI preferences
        """
        for key, value in prefs.items():
            self.settings.setValue(f"ui_{key}", value)

    def load_ui_prefs(self) -> Dict[str, Any]:
        """
        Load UI preferences.

        Returns:
            Dictionary containing UI preferences
        """
        return {
            'window_geometry': self.settings.value("ui_window_geometry"),
            'window_state': self.settings.value("ui_window_state"),
            'splitter_sizes': self.settings.value("ui_splitter_sizes", {}),
        }

    def clear_session_data(self) -> None:
        """Clear all session data."""
        self.settings.clear()
