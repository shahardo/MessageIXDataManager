"""
File Operation Handlers - Manage file loading and processing logic

Extracted from MainWindow to provide focused file operation functionality.
"""

from typing import List, Callable, Any, Dict, Optional
import os
import pickle
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox
from .input_manager import InputManager
from .results_analyzer import ResultsAnalyzer
from .logging_manager import logging_manager
from utils.error_handler import ErrorHandler, SafeOperation
from core.data_models import Scenario


class InputFileHandler:
    """
    Handler for input Excel file operations.

    Manages loading, validation, and processing of MESSAGEix input files.
    """

    def __init__(self, input_manager: InputManager):
        self.input_manager = input_manager

    def load_files(self, file_paths: List[str], progress_callback: Callable[[int, str], None],
                   console_callback: Callable[[str], None]) -> dict:
        """
        Load multiple input Excel files.

        Args:
            file_paths: List of file paths to load
            progress_callback: Callback for progress updates (value, message)
            console_callback: Callback for console messages

        Returns:
            Dictionary with loading statistics
        """
        loaded_files = []
        total_parameters = 0
        total_sets = 0
        all_validation_issues = []
        error_handler = ErrorHandler()

        for file_path in file_paths:
            def on_error(error_msg):
                progress_callback(0, "")  # Clear progress
                console_callback(error_msg)

            with SafeOperation(f"input file loading: {os.path.basename(file_path)}",
                             error_handler, logging_manager.logger, on_error) as safe_op:
                console_callback(f"Loading input file: {file_path}")

                # Show progress bar
                progress_callback(0, f"Loading {os.path.basename(file_path)}...")

                # Load file with Input Manager
                scenario = self.input_manager.load_excel_file(file_path, progress_callback)

                # Log successful load
                logging_manager.log_input_load(file_path, True)

                # Validate the loaded data
                validation = self.input_manager.validate_scenario()

                # Accumulate statistics
                loaded_files.append(file_path)
                total_parameters += len(scenario.parameters)
                total_sets += len(scenario.sets)
                if not validation['valid']:
                    all_validation_issues.extend(validation['issues'])

                # Report validation results for this file
                if validation['valid']:
                    console_callback(f"✓ Successfully loaded {len(scenario.parameters)} parameters, {len(scenario.sets)} sets")
                else:
                    console_callback(f"⚠ Loaded {len(scenario.parameters)} parameters with validation issues:")

        return {
            'loaded_files': loaded_files,
            'total_parameters': total_parameters,
            'total_sets': total_sets,
            'validation_issues': all_validation_issues
        }


class ResultsFileHandler:
    """
    Handler for results file operations.

    Manages loading and processing of MESSAGEix results files.
    """

    def __init__(self, results_analyzer: ResultsAnalyzer):
        self.results_analyzer = results_analyzer

    def load_files(self, file_paths: List[str], progress_callback: Callable[[int, str], None],
                   console_callback: Callable[[str], None]) -> dict:
        """
        Load multiple results files.

        Args:
            file_paths: List of file paths to load
            progress_callback: Callback for progress updates (value, message)
            console_callback: Callback for console messages

        Returns:
            Dictionary with loading statistics
        """
        loaded_files = []
        total_variables = 0
        total_equations = 0
        error_handler = ErrorHandler()

        for file_path in file_paths:
            def on_error(error_msg):
                progress_callback(0, "")  # Clear progress
                console_callback(error_msg)

            with SafeOperation(f"results file loading: {os.path.basename(file_path)}",
                             error_handler, logging_manager.logger, on_error) as safe_op:
                console_callback(f"Loading results file: {file_path}")

                # Show progress bar
                progress_callback(0, f"Loading {os.path.basename(file_path)}...")

                # Load file with Results Analyzer
                results = self.results_analyzer.load_results_file(file_path, progress_callback)

                # Log successful results load
                logging_manager.log_results_load(file_path, True, self.results_analyzer.get_summary_stats())

                loaded_files.append(file_path)

                # Accumulate statistics
                stats = self.results_analyzer.get_summary_stats()
                total_variables += stats['total_variables']
                total_equations += stats['total_equations']

        return {
            'loaded_files': loaded_files,
            'total_variables': total_variables,
            'total_equations': total_equations
        }


class AutoLoadHandler:
    """
    Handler for automatic file loading on application startup.

    Manages loading of last opened files and session restoration.
    """

    def __init__(self, input_manager: InputManager, results_analyzer: ResultsAnalyzer,
                 session_manager):
        self.input_manager = input_manager
        self.results_analyzer = results_analyzer
        self.session_manager = session_manager

    def auto_load_files(self, console_callback: Callable[[str], None],
                       progress_callback: Callable[[int, str], None]) -> tuple:
        """
        Automatically load the last opened files on startup.

        Args:
            console_callback: Callback for console messages
            progress_callback: Callback for progress updates

        Returns:
            Tuple of (loaded_input_files, loaded_results_files)
        """
        input_files, results_files = self.session_manager.get_last_opened_files("input"), \
                                   self.session_manager.get_last_opened_files("results")

        # Load all input files
        loaded_input_files = []
        for input_file in input_files:
            if input_file and os.path.exists(input_file):
                try:
                    console_callback(f"Auto-loading input file: {input_file}")

                    # Show progress bar for auto-loading
                    progress_callback(0, f"Loading {os.path.basename(input_file)}...")

                    scenario = self.input_manager.load_excel_file(input_file, progress_callback)

                    loaded_input_files.append(input_file)

                    console_callback(f"✓ Auto-loaded input file with {len(scenario.parameters)} parameters")

                except Exception as e:
                    progress_callback(0, "")  # Clear progress
                    console_callback(f"Failed to auto-load input file {input_file}: {str(e)}")

        # Load all results files
        loaded_results_files = []
        for results_file in results_files:
            if results_file and os.path.exists(results_file):
                try:
                    console_callback(f"Auto-loading results file: {results_file}")

                    # Show progress bar for auto-loading results
                    progress_callback(0, f"Loading {os.path.basename(results_file)}...")

                    results = self.results_analyzer.load_results_file(results_file, progress_callback)

                    loaded_results_files.append(results_file)

                    stats = self.results_analyzer.get_summary_stats()
                    console_callback(f"✓ Auto-loaded results file with {stats['total_variables']} variables")

                except Exception as e:
                    progress_callback(0, "")  # Clear progress
                    console_callback(f"Failed to auto-load results file {results_file}: {str(e)}")

        return loaded_input_files, loaded_results_files


class ScenarioFileHandler:
    """
    Handler for scenario file operations.

    Manages loading, saving, and processing of MESSAGEix scenario files.
    """

    def __init__(self, input_manager: InputManager, results_analyzer: ResultsAnalyzer):
        self.input_manager = input_manager
        self.results_analyzer = results_analyzer

    def save_scenario(self, scenario: Scenario, console_callback: Callable[[str], None]) -> bool:
        """
        Save a scenario to a pickle file.

        Args:
            scenario: Scenario object to save
            console_callback: Callback for console messages

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Update scenario metadata
            scenario.modified_at = datetime.now()

            # Create directory if it doesn't exist
            scenario_dir = os.path.dirname(scenario.message_scenario_file)
            if scenario_dir and not os.path.exists(scenario_dir):
                os.makedirs(scenario_dir, exist_ok=True)

            # Save scenario to pickle file
            with open(scenario.message_scenario_file, 'wb') as f:
                pickle.dump(scenario, f)

            # Log successful save
            logging_manager.log_scenario_save(scenario.message_scenario_file, True)

            console_callback(f"✓ Successfully saved scenario '{scenario.name}'")
            scenario.mark_saved()
            return True

        except Exception as e:
            console_callback(f"✗ Failed to save scenario '{scenario.name}': {str(e)}")
            logging_manager.log_scenario_save(scenario.message_scenario_file, False, str(e))
            return False

    def load_scenario(self, scenario_file_path: str, progress_callback: Callable[[int, str], None],
                     console_callback: Callable[[str], None]) -> Optional[Scenario]:
        """
        Load a scenario from a pickle file.

        Args:
            scenario_file_path: Path to the scenario pickle file
            progress_callback: Callback for progress updates
            console_callback: Callback for console messages

        Returns:
            Loaded Scenario object, or None if loading failed
        """
        try:
            console_callback(f"Loading scenario from file: {scenario_file_path}")

            # Show progress bar
            progress_callback(0, f"Loading scenario from {os.path.basename(scenario_file_path)}...")

            # Load scenario from pickle file
            with open(scenario_file_path, 'rb') as f:
                scenario = pickle.load(f)

            # Validate loaded scenario
            if not isinstance(scenario, Scenario):
                raise ValueError("Loaded object is not a valid Scenario")

            # Log successful load
            logging_manager.log_scenario_load(scenario_file_path, True)

            console_callback(f"✓ Successfully loaded scenario '{scenario.name}'")
            scenario.mark_saved()
            return scenario

        except Exception as e:
            console_callback(f"✗ Failed to load scenario from {scenario_file_path}: {str(e)}")
            logging_manager.log_scenario_load(scenario_file_path, False, str(e))
            return None

    def validate_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """
        Validate a scenario's integrity.

        Args:
            scenario: Scenario object to validate

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check if input file exists
        if not os.path.exists(scenario.input_file):
            issues.append(f"Input file '{scenario.input_file}' does not exist")

        # Check if scenario file exists
        if not os.path.exists(scenario.message_scenario_file):
            issues.append(f"Scenario file '{scenario.message_scenario_file}' does not exist")

        # Check if results file exists (if specified)
        if scenario.results_file and not os.path.exists(scenario.results_file):
            issues.append(f"Results file '{scenario.results_file}' does not exist")

        # Check scenario data integrity
        if not scenario.data.parameters:
            issues.append("Scenario has no parameters")
        if not scenario.data.sets:
            issues.append("Scenario has no sets")

        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def backup_scenario(self, scenario: Scenario, console_callback: Callable[[str], None]) -> bool:
        """
        Create a backup of a scenario.

        Args:
            scenario: Scenario object to backup
            console_callback: Callback for console messages

        Returns:
            True if backup was successful, False otherwise
        """
        try:
            backup_file = f"{scenario.message_scenario_file}.backup"
            with open(backup_file, 'wb') as f:
                pickle.dump(scenario, f)

            console_callback(f"✓ Created backup of scenario '{scenario.name}' at {backup_file}")
            return True

        except Exception as e:
            console_callback(f"✗ Failed to create backup of scenario '{scenario.name}': {str(e)}")
            return False

    def import_scenario(self, input_file_path: str, scenario_name: str,
                       console_callback: Callable[[str], None],
                       progress_callback: Callable[[int, str], None]) -> Optional[Scenario]:
        """
        Import a new scenario from an input file.

        Args:
            input_file_path: Path to the input Excel file
            scenario_name: Name for the new scenario
            console_callback: Callback for console messages
            progress_callback: Callback for progress updates

        Returns:
            New Scenario object, or None if import failed
        """
        try:
            console_callback(f"Importing scenario '{scenario_name}' from {input_file_path}")

            # Load the input file
            scenario = self.input_manager.load_excel_file(input_file_path, progress_callback)

            # Create new Scenario object
            new_scenario = Scenario(scenario_name, input_file_path)
            new_scenario.data = scenario

            # Save the new scenario
            if self.save_scenario(new_scenario, console_callback):
                console_callback(f"✓ Successfully imported scenario '{scenario_name}'")
                return new_scenario
            else:
                console_callback(f"✗ Failed to save imported scenario '{scenario_name}'")
                return None

        except Exception as e:
            console_callback(f"✗ Failed to import scenario '{scenario_name}': {str(e)}")
            return None

    def export_scenario(self, scenario: Scenario, export_path: str,
                       console_callback: Callable[[str], None]) -> bool:
        """
        Export a scenario to a new location.

        Args:
            scenario: Scenario object to export
            export_path: Path to export the scenario to
            console_callback: Callback for console messages

        Returns:
            True if export was successful, False otherwise
        """
        try:
            # Create a copy of the scenario with new file paths
            exported_scenario = Scenario(scenario.name, export_path)
            exported_scenario.data = scenario.data
            exported_scenario.results_file = scenario.results_file

            # Save the exported scenario
            if self.save_scenario(exported_scenario, console_callback):
                console_callback(f"✓ Successfully exported scenario '{scenario.name}' to {export_path}")
                return True
            else:
                console_callback(f"✗ Failed to export scenario '{scenario.name}'")
                return False

        except Exception as e:
            console_callback(f"✗ Failed to export scenario '{scenario.name}': {str(e)}")
            return False