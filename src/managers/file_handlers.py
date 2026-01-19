"""
File Operation Handlers - Manage file loading and processing logic

Extracted from MainWindow to provide focused file operation functionality.
"""

from typing import List, Callable, Any
import os
from .input_manager import InputManager
from .results_analyzer import ResultsAnalyzer
from .logging_manager import logging_manager
from utils.error_handler import ErrorHandler, SafeOperation


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
