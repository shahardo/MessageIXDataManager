"""
Main application window for MessageIX Data Manager

Refactored to use composition with focused UI components.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QTextEdit, QStatusBar, QMenuBar, QMenu, QAction,
    QFileDialog, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5 import uic
import os
from typing import Optional

from .dashboard import ResultsDashboard
from .navigator import ProjectNavigator
from .components import (
    DataDisplayWidget, ChartWidget, ParameterTreeWidget, FileNavigatorWidget
)
from managers.input_manager import InputManager
from managers.solver_manager import SolverManager
from managers.results_analyzer import ResultsAnalyzer
from managers.logging_manager import logging_manager
from core.data_models import ScenarioData


class MainWindow(QMainWindow):
    """Main application window using composition with focused UI components"""

    def __init__(self):
        super().__init__()

        # Load UI from .ui file
        uic.loadUi('src/ui/main_window.ui', self)

        # Initialize managers
        self.input_manager = InputManager()
        self.solver_manager = SolverManager()
        self.results_analyzer = ResultsAnalyzer()

        # Initialize dashboard
        self.dashboard = ResultsDashboard(self.results_analyzer)

        # Initialize UI components
        self._setup_ui_components()

        # Connect signals
        self._connect_signals()

        # Auto-load last opened files
        self._auto_load_last_files()

    def _setup_ui_components(self):
        """Set up the UI components using composition"""
        # Create component instances
        self.file_navigator = FileNavigatorWidget()
        self.param_tree = ParameterTreeWidget()
        self.data_display = DataDisplayWidget()
        self.chart_widget = ChartWidget()

        # Replace UI elements with components
        # Left panel: navigator and parameter tree
        placeholder_navigator = self.leftSplitter.widget(0)
        if placeholder_navigator:
            placeholder_navigator.setParent(None)
        self.leftSplitter.insertWidget(0, self.file_navigator)

        placeholder_tree = self.leftSplitter.widget(1)
        if placeholder_tree:
            placeholder_tree.setParent(None)
        self.leftSplitter.insertWidget(1, self.param_tree)

        # Right panel: data display and chart
        placeholder_data = self.contentSplitter.widget(0)
        if placeholder_data:
            placeholder_data.setParent(None)

        # Create a splitter for data display and chart
        data_chart_splitter = self.dataSplitter

        # Replace data display area
        placeholder_table = data_chart_splitter.widget(0)
        if placeholder_table:
            placeholder_table.setParent(None)
        data_chart_splitter.insertWidget(0, self.data_display)

        # Replace chart area
        placeholder_chart = data_chart_splitter.widget(1)
        if placeholder_chart:
            placeholder_chart.setParent(None)
        data_chart_splitter.insertWidget(1, self.chart_widget)

        # Set splitter sizes
        self.splitter.setSizes([300, 900])
        self.leftSplitter.setSizes([150, 450])
        self.dataSplitter.setSizes([600, 400])

        # Set stretch factors for proper resizing
        self.splitter.setStretchFactor(0, 0)  # left panel fixed
        self.splitter.setStretchFactor(1, 1)  # content area stretches

        self.leftSplitter.setStretchFactor(0, 0)  # navigator fixed
        self.leftSplitter.setStretchFactor(1, 1)  # parameter tree stretches

        self.contentSplitter.setStretchFactor(0, 1)  # data container stretches
        self.contentSplitter.setStretchFactor(1, 0)  # console fixed

        self.dataSplitter.setStretchFactor(0, 0)  # table container fixed
        self.dataSplitter.setStretchFactor(1, 1)  # graph container stretches

        # View state
        self.current_view = "input"  # "input" or "results"
        self.selected_input_file = None
        self.selected_results_file = None

    def _connect_signals(self):
        """Connect all component signals"""
        # File navigator signals
        self.file_navigator.file_selected.connect(self._on_file_selected)
        self.file_navigator.load_files_requested.connect(self._on_load_files_requested)
        self.file_navigator.file_removed.connect(self._on_file_removed)

        # Parameter tree signals
        self.param_tree.parameter_selected.connect(self._on_parameter_selected)

        # Data display signals
        self.data_display.display_mode_changed.connect(self._on_display_mode_changed)

        # Chart widget signals
        self.chart_widget.chart_type_changed.connect(self._on_chart_type_changed)

        # Menu actions
        self.actionOpen_Input_File.triggered.connect(self._open_input_file)
        self.actionOpen_Results_File.triggered.connect(self._open_results_file)
        self.actionExit.triggered.connect(self.close)
        self.actionRun_Solver.triggered.connect(self._run_solver)
        self.actionStop_Solver.triggered.connect(self._stop_solver)
        self.actionDashboard.triggered.connect(self._show_dashboard)

        # Solver manager signals
        self.solver_manager.set_output_callback(self._append_to_console)
        self.solver_manager.set_status_callback(self._update_status_from_solver)

    def _on_file_selected(self, file_path: str, file_type: str):
        """Handle file selection in navigator"""
        if file_type == "input":
            self.selected_input_file = file_path
            self._switch_to_input_view()
            self._clear_data_display()
        elif file_type == "results":
            self.selected_results_file = file_path
            self._switch_to_results_view()
            self._clear_data_display()

    def _on_parameter_selected(self, parameter_name: str, is_results: bool):
        """Handle parameter/result selection in tree"""
        if parameter_name is None:
            # Category selected, clear display
            self._clear_data_display()
            return

        # Get the parameter object and display it
        scenario = self._get_current_scenario(is_results)
        if scenario:
            parameter = scenario.get_parameter(parameter_name)
            if parameter:
                # Display data using the data display component
                self.data_display.display_parameter_data(parameter, is_results)

                # Update chart with transformed data for display
                chart_df = self._get_chart_data(parameter, is_results)
                self.chart_widget.update_chart(chart_df, parameter.name, is_results)

    def _on_display_mode_changed(self):
        """Handle display mode change (raw/advanced)"""
        # Refresh current parameter display
        self._refresh_current_display()

    def _on_chart_type_changed(self, chart_type: str):
        """Handle chart type change"""
        # Refresh current chart
        self._refresh_current_display()

    def _switch_to_input_view(self):
        """Switch to input parameters view"""
        self.current_view = "input"
        self.param_tree.set_view_mode(False)

        # Update parameter tree
        scenario = self._get_current_scenario(False)
        if scenario:
            self.param_tree.update_parameters(scenario)

    def _switch_to_results_view(self):
        """Switch to results view"""
        self.current_view = "results"
        self.param_tree.set_view_mode(True)

        # Update results tree
        scenario = self._get_current_scenario(True)
        if scenario:
            self.param_tree.update_results(scenario)

    def _clear_data_display(self):
        """Clear the data display and chart"""
        self.data_display.display_parameter_data(None, False)  # This will show placeholder
        self.chart_widget.show_placeholder()

    def _refresh_current_display(self):
        """Refresh the current parameter/result display"""
        # This would be called when display mode or chart type changes
        # For now, retrigger the current parameter selection
        selected_items = self.param_tree.selectedItems()
        if selected_items:
            item_name = selected_items[0].text(0)
            if item_name and not item_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
                self._on_parameter_selected(item_name, self.current_view == "results")

    def _get_current_scenario(self, is_results: bool) -> Optional[ScenarioData]:
        """Get the current scenario based on selection"""
        if is_results:
            if self.selected_results_file:
                return self.results_analyzer.get_results_by_file_path(self.selected_results_file)
            return self.results_analyzer.get_current_results()
        else:
            if self.selected_input_file:
                return self.input_manager.get_scenario_by_file_path(self.selected_input_file)
            return self.input_manager.get_current_scenario()

    def _get_chart_data(self, parameter, is_results: bool):
        """Get transformed data for chart display"""
        # This is a simplified version - the full transformation logic
        # would be moved to a utility function
        df = parameter.df
        # For now, return a simple pivot if possible
        try:
            # Try to create a simple pivot for chart
            pivot_cols = [col for col in df.columns if col in ['technology', 'commodity', 'region']]
            if pivot_cols and 'year' in df.columns and 'value' in df.columns:
                chart_df = df.pivot_table(
                    values='value',
                    index='year',
                    columns=pivot_cols[:2],  # Limit columns for readability
                    aggfunc='first'
                ).fillna(0)
                return chart_df
        except:
            pass

        # Fallback: return original data
        return df

    def _open_input_file(self):
        """Handle opening input Excel file(s)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Input Excel File(s)", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_paths:
            loaded_files = []
            total_parameters = 0
            total_sets = 0
            total_data_points = 0
            all_validation_issues = []

            for file_path in file_paths:
                try:
                    self._append_to_console(f"Loading input file: {file_path}")

                    # Show progress bar
                    self.show_progress_bar(100)

                    # Define progress callback
                    def progress_callback(value, message):
                        self.update_progress(value, message)

                    # Load file with Input Manager
                    scenario = self.input_manager.load_excel_file(file_path, progress_callback)

                    # Hide progress bar
                    self.hide_progress_bar()

                    # Log successful load
                    logging_manager.log_input_load(file_path, True)

                    # Validate the loaded data
                    validation = self.input_manager.validate_scenario()

                    # Accumulate statistics
                    loaded_files.append(file_path)
                    total_parameters += len(scenario.parameters)
                    total_sets += len(scenario.sets)
                    total_data_points += validation['summary']['total_data_points']
                    if not validation['valid']:
                        all_validation_issues.extend(validation['issues'])

                    # Report validation results for this file
                    if validation['valid']:
                        self._append_to_console(f"✓ Successfully loaded {len(scenario.parameters)} parameters, {len(scenario.sets)} sets")
                    else:
                        self.console.append(f"⚠ Loaded {len(scenario.parameters)} parameters with validation issues:")

                except Exception as e:
                    # Hide progress bar on error
                    self.hide_progress_bar()

                    error_msg = f"Error loading file {file_path}: {str(e)}"
                    self.console.append(error_msg)
                    QMessageBox.critical(self, "Load Error", error_msg)

                    # Log failed load
                    logging_manager.log_input_load(file_path, False, error_msg)

            if loaded_files:
                # Clear file selection to show combined view
                self.selected_input_file = None

                # Save all opened files for auto-load
                for file_path in loaded_files:
                    self._save_last_opened_files(file_path, "input")

                # Update UI with all loaded files
                self.file_navigator.update_input_files(self.input_manager.get_loaded_file_paths())
                for file_path in loaded_files:
                    self.file_navigator.add_recent_file(file_path, "input")

                # Update parameter tree (will show combined data)
                self._switch_to_input_view()

                # Report overall results
                if all_validation_issues:
                    self.console.append(f"⚠ Loaded {len(loaded_files)} file(s) with {len(all_validation_issues)} total validation issues")
                else:
                    self._append_to_console(f"✓ Successfully loaded {len(loaded_files)} file(s) with {total_parameters} parameters, {total_sets} sets")

                self.status_bar.showMessage(f"Loaded {len(loaded_files)} input file(s)")

    def _open_results_file(self):
        """Handle opening results Excel file(s)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Results Excel File(s)", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_paths:
            loaded_files = []
            total_variables = 0
            total_equations = 0
            total_data_points = 0

            for file_path in file_paths:
                try:
                    self.console.append(f"Loading results file: {file_path}")

                    # Show progress bar
                    self.show_progress_bar(100)

                    # Define progress callback
                    def progress_callback(value, message):
                        self.update_progress(value, message)

                    # Load file with Results Analyzer
                    results = self.results_analyzer.load_results_file(file_path, progress_callback)

                    # Hide progress bar
                    self.hide_progress_bar()

                    # Log successful results load
                    logging_manager.log_results_load(file_path, True, self.results_analyzer.get_summary_stats())

                    loaded_files.append(file_path)

                    # Accumulate statistics
                    stats = self.results_analyzer.get_summary_stats()
                    total_variables += stats['total_variables']
                    total_equations += stats['total_equations']
                    total_data_points += stats['total_data_points']

                except Exception as e:
                    # Hide progress bar on error
                    self.hide_progress_bar()

                    error_msg = f"Error loading results file {file_path}: {str(e)}"
                    self.console.append(error_msg)
                    QMessageBox.critical(self, "Load Error", error_msg)

                    # Log failed results load
                    logging_manager.log_results_load(file_path, False, {'error': error_msg})

            if loaded_files:
                # Clear file selection to show combined view
                self.selected_results_file = None

                # Save all opened files for auto-load
                for file_path in loaded_files:
                    self._save_last_opened_files(file_path, "results")

                # Update UI with all loaded files
                self.file_navigator.update_result_files(self.results_analyzer.get_loaded_file_paths())
                for file_path in loaded_files:
                    self.file_navigator.add_recent_file(file_path, "results")

                # Update results tree
                self._switch_to_results_view()

                # Show summary
                self.console.append(f"Loaded {len(loaded_files)} result file(s) with {total_variables} variables, {total_equations} equations")

                # Update dashboard with new results
                self.dashboard.update_results(True)

                self.status_bar.showMessage(f"Results loaded: {len(loaded_files)} file(s)")

    def _run_solver(self):
        """Handle running the solver"""
        if self.solver_manager.is_solver_running():
            self.console.append("Solver is already running")
            return

        # Check if we have an input file loaded
        if not self.input_manager.get_current_scenario():
            QMessageBox.warning(self, "No Input File",
                              "Please load an input Excel file first.")
            return

        input_paths = self.input_manager.get_loaded_file_paths()
        if not input_paths:
            QMessageBox.warning(self, "No Input File",
                              "Please load an input Excel file first.")
            return

        # Use the last loaded input file for solver
        input_path = input_paths[-1]

        # Get available solvers
        solvers = self.solver_manager.get_available_solvers()
        if not solvers:
            QMessageBox.warning(self, "No Solvers Available",
                              "No compatible solvers found in the environment.")
            return

        # Use first available solver (could add solver selection dialog later)
        solver_name = solvers[0]

        self.console.append(f"Starting solver with input: {input_path}")
        self.console.append(f"Using solver: {solver_name}")

        success = self.solver_manager.run_solver(input_path, solver_name)
        if not success:
            QMessageBox.critical(self, "Solver Error",
                               "Failed to start solver. Check console for details.")

    def _stop_solver(self):
        """Handle stopping the solver"""
        if self.solver_manager.is_solver_running():
            success = self.solver_manager.stop_solver()
            if success:
                self.console.append("Solver stop requested")
            else:
                QMessageBox.warning(self, "Stop Failed",
                                  "Failed to stop solver gracefully.")
        else:
            self.console.append("No solver is currently running")

    def _show_dashboard(self):
        """Show results dashboard"""
        try:
            self.dashboard.update_results(bool(self.results_analyzer.get_current_results()))
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()
        except Exception as e:
            self.console.append(f"Error showing dashboard: {str(e)}")
            QMessageBox.critical(self, "Dashboard Error",
                               f"Failed to open dashboard: {str(e)}")

    def _on_load_files_requested(self, file_type: str):
        """Handle request to load files when 'no files loaded' is clicked"""
        if file_type == "input":
            self._open_input_file()
        elif file_type == "results":
            self._open_results_file()

    def _on_file_removed(self, file_path: str, file_type: str):
        """Handle file removal from navigator"""
        removed = False
        if file_type == "input":
            removed = self.input_manager.remove_file(file_path)
            if removed:
                # Remove from settings so it won't auto-load on restart
                self._remove_last_opened_file(file_path, file_type)

                # Update navigator
                self.file_navigator.update_input_files(self.input_manager.get_loaded_file_paths())

                # Clear selection if this was the selected file
                if self.selected_input_file == file_path:
                    self.selected_input_file = None
                    self._clear_data_display()

        elif file_type == "results":
            removed = self.results_analyzer.remove_file(file_path)
            if removed:
                # Remove from settings so it won't auto-load on restart
                self._remove_last_opened_file(file_path, file_type)

                # Update navigator
                self.file_navigator.update_result_files(self.results_analyzer.get_loaded_file_paths())

                # Clear selection if this was the selected file
                if self.selected_results_file == file_path:
                    self.selected_results_file = None
                    self._clear_data_display()

        if removed:
            self.status_bar.showMessage(f"Removed {file_type} file: {os.path.basename(file_path)}")
        else:
            self.status_bar.showMessage(f"Failed to remove {file_type} file: {os.path.basename(file_path)}")

    # Progress bar methods
    def show_progress_bar(self, maximum=100):
        """Show and initialize the progress bar"""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

    def update_progress(self, value, message=None):
        """Update progress bar value and optionally status message"""
        self.progress_bar.setValue(value)
        if message:
            self.status_bar.showMessage(message)

    def hide_progress_bar(self):
        """Hide the progress bar"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Ready")

    # Console methods
    def _append_to_console(self, message: str):
        """Append message to console"""
        self.console.append(message)

    def _update_status_from_solver(self, status: str):
        """Update status bar from solver manager"""
        self.status_bar.showMessage(status)

    # Settings methods
    def _save_last_opened_files(self, file_path, file_type):
        """Save the last opened file path to settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        if file_type == "input":
            input_files = settings.value("last_input_files", [])
            if isinstance(input_files, str):
                input_files = [input_files]
            if file_path not in input_files:
                input_files.append(file_path)
                input_files = input_files[-5:]  # Keep only the last 5 files
            settings.setValue("last_input_files", input_files)
        elif file_type == "results":
            results_files = settings.value("last_results_files", [])
            if isinstance(results_files, str):
                results_files = [results_files]
            if file_path not in results_files:
                results_files.append(file_path)
                results_files = results_files[-5:]  # Keep only the last 5 files
            settings.setValue("last_results_files", results_files)

    def _remove_last_opened_file(self, file_path, file_type):
        """Remove a file from the last opened files settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        if file_type == "input":
            input_files = settings.value("last_input_files", [])
            if isinstance(input_files, str):
                input_files = [input_files]
            if file_path in input_files:
                input_files.remove(file_path)
            settings.setValue("last_input_files", input_files)
        elif file_type == "results":
            results_files = settings.value("last_results_files", [])
            if isinstance(results_files, str):
                results_files = [results_files]
            if file_path in results_files:
                results_files.remove(file_path)
            settings.setValue("last_results_files", results_files)

    def _get_last_opened_files(self):
        """Get the last opened file paths from settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        input_files = settings.value("last_input_files", [])
        results_files = settings.value("last_results_files", [])
        # Ensure they are lists
        if isinstance(input_files, str):
            input_files = [input_files]
        if isinstance(results_files, str):
            results_files = [results_files]
        return input_files, results_files

    def _auto_load_last_files(self):
        """Automatically load the last opened files on startup"""
        input_files, results_files = self._get_last_opened_files()

        # Load all input files
        loaded_input_files = []
        for input_file in input_files:
            if input_file and os.path.exists(input_file):
                try:
                    self._append_to_console(f"Auto-loading input file: {input_file}")

                    # Show progress bar for auto-loading
                    self.show_progress_bar(100)

                    # Define progress callback
                    def progress_callback(value, message):
                        self.update_progress(value, message)

                    scenario = self.input_manager.load_excel_file(input_file, progress_callback)

                    # Hide progress bar
                    self.hide_progress_bar()

                    loaded_input_files.append(input_file)

                    self._append_to_console(f"✓ Auto-loaded input file with {len(scenario.parameters)} parameters")

                except Exception as e:
                    # Hide progress bar on error
                    self.hide_progress_bar()
                    self.console.append(f"Failed to auto-load input file {input_file}: {str(e)}")

        if loaded_input_files:
            # Update UI with all loaded input files
            self.file_navigator.update_input_files(loaded_input_files)
            for file_path in loaded_input_files:
                self.file_navigator.add_recent_file(file_path, "input")
            # Update parameter tree
            self._switch_to_input_view()

        # Load all results files
        loaded_results_files = []
        for results_file in results_files:
            if results_file and os.path.exists(results_file):
                try:
                    self.console.append(f"Auto-loading results file: {results_file}")

                    # Show progress bar for auto-loading results
                    self.show_progress_bar(100)

                    # Define progress callback
                    def progress_callback(value, message):
                        self.update_progress(value, message)

                    results = self.results_analyzer.load_results_file(results_file, progress_callback)

                    # Hide progress bar
                    self.hide_progress_bar()

                    loaded_results_files.append(results_file)

                    stats = self.results_analyzer.get_summary_stats()
                    self.console.append(f"✓ Auto-loaded results file with {stats['total_variables']} variables")

                except Exception as e:
                    # Hide progress bar on error
                    self.hide_progress_bar()
                    self.console.append(f"Failed to auto-load results file {results_file}: {str(e)}")

        if loaded_results_files:
            # Update UI with all loaded results files
            self.file_navigator.update_result_files(self.results_analyzer.get_loaded_file_paths())
            for file_path in loaded_results_files:
                self.file_navigator.add_recent_file(file_path, "results")
            # Update dashboard
            self.dashboard.update_results(True)
