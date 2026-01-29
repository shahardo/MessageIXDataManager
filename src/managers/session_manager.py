"""
Session management for MessageIX Data Manager

Handles persistence of application state including:
- Last opened scenarios
- UI state (selected scenarios, view mode, parameters)
- User preferences
"""

import os
from typing import List, Optional, Dict, Any, Tuple
from PyQt5.QtCore import QSettings
from datetime import datetime
from core.data_models import Scenario


class SessionManager:
    """
    Manages application session state and persistence.

    Provides centralized handling of:
    - Recently opened scenarios
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
        self.max_recent_scenarios = 5

    def get_scenarios(self) -> List[Scenario]:
        """
        Get the list of recently opened scenarios.

        Returns:
            List of Scenario objects that exist on disk
        """
        scenarios_data = self.settings.value("recent_scenarios", [])

        # Ensure it's a list
        if not isinstance(scenarios_data, list):
            scenarios_data = []

        # Filter out scenarios that no longer exist or are invalid
        valid_scenarios = []
        for scenario_data in scenarios_data:
            try:
                scenario = self._deserialize_scenario(scenario_data)
                # Check if at least ONE file exists (input, data, or results)
                if scenario and (
                    (scenario.input_file and os.path.exists(scenario.input_file)) or
                    (scenario.message_scenario_file and os.path.exists(scenario.message_scenario_file)) or
                    (scenario.results_file and os.path.exists(scenario.results_file))
                ):
                    valid_scenarios.append(scenario)
            except Exception:
                continue

        # Update settings if we filtered out invalid scenarios
        if len(valid_scenarios) != len(scenarios_data):
            self._save_scenarios(valid_scenarios)

        return valid_scenarios

    def get_scenario(self, scenario_name: str) -> Optional[Scenario]:
        """
        Get a scenario by name.

        Args:
            scenario_name: Name of the scenario to retrieve

        Returns:
            Scenario object or None if not found
        """
        scenarios = self.get_scenarios()
        for scenario in scenarios:
            if scenario.name == scenario_name:
                return scenario
        return None

    def add_scenario(self, scenario: Scenario) -> None:
        """
        Add a scenario to the recent scenarios list.

        Args:
            scenario: Scenario object to add
        """
        scenarios = self.get_scenarios()

        # Remove if already exists (to move to front)
        for existing_scenario in scenarios:
            if existing_scenario.name == scenario.name:
                scenarios.remove(existing_scenario)
                break

        # Add to front of list
        scenarios.insert(0, scenario)

        # Keep only the most recent scenarios
        scenarios = scenarios[:self.max_recent_scenarios]

        self._save_scenarios(scenarios)

    def remove_scenario(self, scenario_name: str) -> None:
        """
        Remove a scenario from the recent scenarios list.

        Args:
            scenario_name: Name of the scenario to remove
        """
        scenarios = self.get_scenarios()

        # Find and remove the scenario
        for scenario in scenarios:
            if scenario.name == scenario_name:
                scenarios.remove(scenario)
                self._save_scenarios(scenarios)
                return

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
            'selected_scenario': self.settings.value("selected_scenario", None),
            'last_selected_parameter': self.settings.value("last_selected_parameter", None),
            'selected_input_file': self.settings.value("selected_input_file", None),
            'selected_results_file': self.settings.value("selected_results_file", None),
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

    def add_recent_file(self, file_path: str, file_type: str) -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to the file to add
            file_type: Type of file ("input" or "results")
        """
        recent_files = self.get_last_opened_files(file_type)
        
        # Remove if already exists (to move to front)
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # Add to front of list
        recent_files.insert(0, file_path)
        
        # Keep only the most recent files
        recent_files = recent_files[:self.max_recent_scenarios]
        
        self.settings.setValue(f"recent_{file_type}_files", recent_files)

    def remove_recent_file(self, file_path: str, file_type: str) -> None:
        """
        Remove a file from the recent files list.

        Args:
            file_path: Path of the file to remove
            file_type: Type of file ("input" or "results")
        """
        recent_files = self.get_last_opened_files(file_type)
        
        # Find and remove the file
        if file_path in recent_files:
            recent_files.remove(file_path)
            self.settings.setValue(f"recent_{file_type}_files", recent_files)

    def get_last_opened_files(self, file_type: str) -> List[str]:
        """
        Get the list of recently opened files.

        Args:
            file_type: Type of files to get ("input" or "results")

        Returns:
            List of file paths that exist on disk
        """
        files_data = self.settings.value(f"recent_{file_type}_files", [])
        
        # Ensure it's a list
        if not isinstance(files_data, list):
            files_data = []
        
        # Filter out files that no longer exist or are invalid
        valid_files = []
        for file_path in files_data:
            try:
                if file_path and isinstance(file_path, str) and os.path.exists(file_path):
                    valid_files.append(file_path)
            except Exception:
                continue
        
        # Update settings if we filtered out invalid files
        if len(valid_files) != len(files_data):
            self.settings.setValue(f"recent_{file_type}_files", valid_files)
        
        return valid_files

    def _save_scenarios(self, scenarios: List[Scenario]) -> None:
        """Serialize and save scenarios to settings."""
        scenarios_data = [self._serialize_scenario(scenario) for scenario in scenarios]
        self.settings.setValue("recent_scenarios", scenarios_data)

    def _serialize_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Serialize a Scenario object to a dictionary."""
        return {
            'name': scenario.name,
            'input_file': scenario.input_file,
            'message_scenario_file': scenario.message_scenario_file,
            'results_file': scenario.results_file,
            'status': scenario.status,
            'created_at': scenario.created_at.isoformat() if scenario.created_at else None,
            'modified_at': scenario.modified_at.isoformat() if scenario.modified_at else None
        }

    def _deserialize_scenario(self, scenario_data: Dict[str, Any]) -> Optional[Scenario]:
        """Deserialize a dictionary to a Scenario object."""
        try:
            name = scenario_data.get('name')
            if not name:
                return None
            
            input_file = scenario_data.get('input_file')
            
            scenario = Scenario(name, input_file)
            scenario.message_scenario_file = scenario_data.get('message_scenario_file')
            scenario.results_file = scenario_data.get('results_file')
            scenario.status = scenario_data.get('status', 'loaded')

            created_at_str = scenario_data.get('created_at')
            if created_at_str:
                scenario.created_at = datetime.fromisoformat(created_at_str)

            modified_at_str = scenario_data.get('modified_at')
            if modified_at_str:
                scenario.modified_at = datetime.fromisoformat(modified_at_str)

            return scenario
        except Exception:
            return None