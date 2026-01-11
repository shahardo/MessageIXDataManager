"""
Main application window for MessageIX Data Manager

Refactored to use composition with focused UI components.
Provides the primary user interface for loading, analyzing, and visualizing
MESSAGEix input files and results.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5 import uic
import os
import pandas as pd
from typing import Optional, List

from .dashboard import ResultsDashboard
from .results_file_dashboard import ResultsFileDashboard
from .navigator import ProjectNavigator
from .components import (
    DataDisplayWidget, ChartWidget, ParameterTreeWidget, FileNavigatorWidget
)
from managers.input_manager import InputManager
from managers.solver_manager import SolverManager
from managers.results_analyzer import ResultsAnalyzer
from managers.data_export_manager import DataExportManager
from managers.logging_manager import logging_manager
from core.data_models import ScenarioData
from utils.error_handler import ErrorHandler, SafeOperation


class MainWindow(QMainWindow):
    """
    Main application window for MESSAGEix Data Manager.

    Provides the primary user interface for loading, analyzing, and visualizing
    MESSAGEix input files and results. Uses composition with focused UI components
    for better maintainability and testability.

    Attributes:
        input_manager: Manager for loading and parsing input Excel files
        solver_manager: Manager for running MESSAGEix solvers
        results_analyzer: Manager for loading and analyzing result files
        dashboard: Dashboard widget for results visualization
        current_view: Current view mode ("input" or "results")
        selected_input_file: Currently selected input file path
        selected_results_file: Currently selected results file path
    """

    def __init__(self) -> None:
        """
        Initialize the main application window.

        Sets up UI components, managers, signal connections, and loads
        previously opened files automatically.
        """
        super().__init__()

        # Load UI from .ui file
        try:
            uic.loadUi('src/ui/main_window.ui', self)
        except Exception:
            # UI loading failed (possibly mocked in tests), continue without UI components
            print("DEBUG: UI loading failed")  # Debug print
            pass

        # Initialize managers
        self.input_manager: InputManager = InputManager()
        self.solver_manager: SolverManager = SolverManager()
        self.results_analyzer: ResultsAnalyzer = ResultsAnalyzer()
        self.data_export_manager: DataExportManager = DataExportManager()

        # Load technology descriptions from CSV
        self.tech_descriptions = self._load_tech_descriptions()

        # Initialize dashboard
        self.dashboard: ResultsDashboard = ResultsDashboard(self.results_analyzer)
        self.results_file_dashboard: ResultsFileDashboard = ResultsFileDashboard(self.results_analyzer)

        # Add dashboard widget to the data container layout
        self._setup_data_area_widgets()

        # Initialize UI components
        self._setup_ui_components()

        # Connect signals
        self._connect_signals()

        # View state - initialize BEFORE auto-loading files
        self.current_view: str = "input"  # "input" or "results"
        self.selected_input_file: Optional[str] = None
        self.selected_results_file: Optional[str] = None

        # Remember last selected parameters for each file type
        self.last_selected_input_parameter: Optional[str] = None
        self.last_selected_results_parameter: Optional[str] = None

        # Auto-load last opened files
        self._auto_load_last_files()

    def _load_tech_descriptions(self):
        """Load technology descriptions from CSV file"""
        try:
            df = pd.read_csv('helpers/message_relations.csv')
            descriptions = {}
            for _, row in df.iterrows():
                descriptions[row['technology']] = {
                    'group': row['group'],
                    'parameters': row['parameters'],
                    'technology-entry': row['technology-entry'],
                    'description': row['description']
                }
            return descriptions
        except Exception as e:
            print(f"Failed to load technology descriptions: {e}")
            return {}

    def _setup_data_area_widgets(self):
        """Set up the data area widgets in the dataContainer layout"""
        # Ensure dataContainer has a layout
        if self.dataContainer.layout() is None:
            from PyQt5.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(self.dataContainer)
            self.dataContainer.setLayout(layout)

        # Add both widgets to the layout
        layout = self.dataContainer.layout()
        layout.addWidget(self.dataSplitter)
        layout.addWidget(self.results_file_dashboard)

        # Initially show data splitter and hide dashboard
        self.dataSplitter.show()
        self.results_file_dashboard.hide()

    def _setup_ui_components(self):
        """Set up the UI components using composition"""
        # Create component instances, passing existing widgets from .ui file
        self.file_navigator = FileNavigatorWidget()
        self.param_tree = ParameterTreeWidget()
        self.data_display = DataDisplayWidget()
        self.chart_widget = ChartWidget()

        # Initialize components with existing UI widgets
        self._initialize_components_with_ui_widgets()

        # Connect component signals
        self._connect_component_signals()

        # Set splitter sizes (only if they exist)
        self.splitter.setSizes([300, 900])
        self.splitter.setStretchFactor(0, 0)  # left panel fixed
        self.splitter.setStretchFactor(1, 1)  # content area stretches

        self.leftSplitter.setSizes([150, 450])
        self.leftSplitter.setStretchFactor(0, 1)  # navigator resizes
        self.leftSplitter.setStretchFactor(1, 1)  # parameter tree resizes

        self.contentSplitter.setSizes([720, 80])  # Give more space to data, less to console
        self.contentSplitter.setStretchFactor(0, 1)  # data container stretches
        self.contentSplitter.setStretchFactor(1, 0)  # console fixed

        self.dataSplitter.setSizes([600, 400])
        self.dataSplitter.setStretchFactor(0, 0)  # table container fixed
        self.dataSplitter.setStretchFactor(1, 1)  # graph container stretches

    def _initialize_components_with_ui_widgets(self):
        """Initialize components to reuse existing UI widgets instead of creating new ones"""
        # Replace navigator widget
        placeholder_navigator = self.leftSplitter.widget(0)
        if placeholder_navigator:
            placeholder_navigator.setParent(None)
        self.leftSplitter.insertWidget(0, self.file_navigator)

        # Replace parameter tree widget
        placeholder_tree = self.leftSplitter.widget(1)
        if placeholder_tree:
            placeholder_tree.setParent(None)
        self.leftSplitter.insertWidget(1, self.param_tree)

        # For data display and chart, reuse existing widgets from .ui file
        # Instead of replacing entire containers, connect to existing widgets

        # Connect data display to existing widgets
        self.data_display.param_title = self.param_title
        self.data_display.view_toggle_button = self.view_toggle_button
        self.data_display.param_table = self.param_table
        self.data_display.selector_container = self.selector_container
        self.data_display.tech_descriptions = self.tech_descriptions

        # Connect chart widget to existing widgets
        self.chart_widget.simple_bar_btn = self.simple_bar_btn
        self.chart_widget.stacked_bar_btn = self.stacked_bar_btn
        self.chart_widget.line_chart_btn = self.line_chart_btn
        self.chart_widget.stacked_area_btn = self.stacked_area_btn
        self.chart_widget.param_chart = self.param_chart

        # Initialize component internal state
        self.data_display.initialize_with_ui_widgets()
        self.chart_widget.initialize_with_ui_widgets()

    def _connect_component_signals(self):
        """Connect component signals to main window handlers"""
        # Parameter tree signals
        self.param_tree.parameter_selected.connect(self._on_parameter_selected)
        self.param_tree.options_changed.connect(self._on_options_changed)

        # Data display signals
        self.data_display.display_mode_changed.connect(self._on_display_mode_changed)
        self.data_display.cell_value_changed.connect(self._on_cell_value_changed)
        self.data_display.chart_update_needed.connect(self._on_chart_update_needed)

        # Chart widget signals
        self.chart_widget.chart_type_changed.connect(self._on_chart_type_changed)

    def _connect_signals(self):
        """Connect all component signals"""
        # File navigator signals
        self.file_navigator.file_selected.connect(self._on_file_selected)
        self.file_navigator.load_files_requested.connect(self._on_load_files_requested)
        self.file_navigator.file_removed.connect(self._on_file_removed)

        # Menu actions
        self.actionOpen_Input_File.triggered.connect(self._open_input_file)
        self.actionOpen_Results_File.triggered.connect(self._open_results_file)
        self.actionExit.triggered.connect(self.close)
        self.actionRun_Solver.triggered.connect(self._run_solver)
        self.actionStop_Solver.triggered.connect(self._stop_solver)
        self.actionDashboard.triggered.connect(self._show_dashboard)

        # Connect save actions from UI
        self.actionSave.triggered.connect(self._save_file)
        self.actionSave_As.triggered.connect(self._save_file_as)

        # Solver manager signals
        self.solver_manager.set_output_callback(self._append_to_console)
        self.solver_manager.set_status_callback(self._update_status_from_solver)



    def _on_file_selected(self, file_path: str, file_type: str):
        """Handle file selection in navigator"""
        if file_type == "input":
            self.selected_input_file = file_path
            self._switch_to_input_view()
            self._clear_data_display()
            # Auto-select the last selected parameter if it exists in this file
            if self.last_selected_input_parameter:
                self._auto_select_parameter_if_exists(self.last_selected_input_parameter, False)
        elif file_type == "results":
            self.selected_results_file = file_path
            self._switch_to_results_view()
            self._clear_data_display()
            # Auto-select the last selected parameter if it exists in this file
            if self.last_selected_results_parameter:
                self._auto_select_parameter_if_exists(self.last_selected_results_parameter, True)

        # Save current session state
        self._save_current_session_state()

    def _on_parameter_selected(self, parameter_name: str, is_results: bool):
        """Handle parameter/result selection in tree"""
        if parameter_name is None:
            # Category selected, clear display
            self._clear_data_display()
            return

        # Special handling for dashboard selection
        if parameter_name == "Dashboard" and is_results:
            # Remember this parameter for future file switches
            self.last_selected_results_parameter = parameter_name

            # Show the results file dashboard
            self._show_results_file_dashboard()
            return

        # Remember this parameter for future file switches
        if is_results:
            self.last_selected_results_parameter = parameter_name
        else:
            self.last_selected_input_parameter = parameter_name

        # Switch back to normal data display if dashboard was showing
        self._restore_normal_display()

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

    def _on_options_changed(self):
        """Handle scenario options change"""
        # Refresh current chart to reflect new year range
        self._refresh_current_display()

    def _on_cell_value_changed(self, mode: str, row_or_year, col_or_tech, new_value):
        """Handle cell value changes from table editing"""
        # Get the current scenario and parameter
        scenario = self._get_current_scenario(self.current_view == "results")
        if not scenario:
            return

        # Get the currently selected parameter
        selected_items = self.param_tree.selectedItems()
        if not selected_items:
            return

        param_name = selected_items[0].text(0)
        if not param_name or param_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
            return

        parameter = scenario.get_parameter(param_name)
        if not parameter:
            return

        df = parameter.df.copy()

        if mode == "raw":
            # Direct editing of raw data table
            row_idx = row_or_year
            column_name = col_or_tech

            # Update the value at the specific row and column
            if 0 <= row_idx < len(df) and column_name in df.columns:
                df.loc[row_idx, column_name] = new_value
                log_message = f"Updated {param_name}: row {row_idx + 1}, column '{column_name}' = {new_value}"
            else:
                self._append_to_console(f"Warning: Invalid raw edit - row {row_idx}, column '{column_name}'")
                return

        elif mode == "advanced":
            # Pivot/advanced mode editing - sync to raw data
            year = row_or_year
            technology = col_or_tech

            # Identify column types
            column_info = self.data_display._identify_columns(df)

            # Find the year column and technology column
            year_col = None
            tech_col = None

            for col in column_info['year_cols']:
                if col in df.columns:
                    year_col = col
                    break

            for col in column_info['pivot_cols']:
                if col in df.columns:
                    tech_col = col
                    break

            value_col = column_info.get('value_col')

            if not (year_col and tech_col and value_col):
                self._append_to_console("Warning: Cannot sync pivot changes - missing required columns")
                return

            # Find rows that match the year and technology (robust comparison)
            try:
                year_values = pd.to_numeric(df[year_col], errors='coerce')
            except:
                year_values = df[year_col]  # Fallback if conversion fails
            tech_values = df[tech_col].astype(str).str.strip()
            mask = (year_values == year) & (tech_values == str(technology).strip())
            matching_rows = df[mask]

            if matching_rows.empty:
                self._append_to_console(f"Warning: No matching data found for year={year}, technology='{technology}' (checked {len(df)} rows)")
                return

            # Update the value in the raw data
            df.loc[mask, value_col] = new_value
            log_message = f"Updated {param_name}: {technology} in {year} = {new_value} (matched {len(matching_rows)} rows)"

            # Update the parameter with the modified DataFrame
            parameter.df = df

            # Mark the parameter as modified
            scenario.mark_modified(param_name)

            # Update status bar
            self.statusbar.showMessage(f"Modified {param_name} - unsaved changes")

            # Update chart immediately with the new data
            chart_df = self._get_chart_data(parameter, self.current_view == "results")
            self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")

            # Refresh the display to show the updated pivoted data
            self._refresh_current_display()

            # Log the change
            self._append_to_console(log_message)

        else:
            self._append_to_console(f"Warning: Unknown editing mode: {mode}")
            return

        # Update the parameter with the modified DataFrame
        parameter.df = df

        # Mark the parameter as modified
        scenario.mark_modified(param_name)

        # Update status bar
        self.statusbar.showMessage(f"Modified {param_name} - unsaved changes")

        # Update chart immediately with the new data
        chart_df = self._get_chart_data(parameter, self.current_view == "results")
        self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")

        # Log the change
        self._append_to_console(log_message)

    def _on_chart_update_needed(self):
        """Update chart when data changes without refreshing the table"""
        # Get the currently selected parameter
        selected_items = self.param_tree.selectedItems()
        if not selected_items:
            return

        param_name = selected_items[0].text(0)
        if not param_name or param_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
            return

        # Get the parameter object
        scenario = self._get_current_scenario(self.current_view == "results")
        if scenario:
            parameter = scenario.get_parameter(param_name)
            if parameter:
                # Update chart with current data (which includes our changes)
                chart_df = self._get_chart_data(parameter, self.current_view == "results")
                self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")

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
        if self.current_view == "results" and self.selected_results_file:
            # Show dashboard for results files when no parameter is selected
            self._show_results_file_dashboard()
        else:
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

    def _auto_select_parameter_if_exists(self, parameter_name: str, is_results: bool):
        """Auto-select a parameter in the tree if it exists in the current scenario"""
        scenario = self._get_current_scenario(is_results)
        if not scenario or not scenario.get_parameter(parameter_name):
            return  # Parameter doesn't exist in this scenario

        # Find and select the parameter in the tree
        def find_and_select_item(parent_item):
            """Recursively search for the parameter item"""
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == parameter_name:
                    # Found the parameter item - select it
                    self.param_tree.setCurrentItem(child)
                    self.param_tree.scrollToItem(child)
                    return True
                # Recursively search in children
                if find_and_select_item(child):
                    return True
            return False

        # Search through all top-level items
        root = self.param_tree.invisibleRootItem()
        if find_and_select_item(root):
            # The selection will trigger the parameter_selected signal automatically
            # which will call _on_parameter_selected and display the data
            pass

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
        """Get transformed data for chart display using the same logic as table view"""
        df = parameter.df

        # Use the same transformation logic as the data display widget
        # For charts, we always want advanced view transformation (pivoted data)
        # Charts always hide empty columns for cleaner visualization
        transformed_df = self.data_display.transform_to_display_format(
            df,
            is_results=is_results,
            current_filters=None,  # No filters for chart data
            hide_empty=True,       # Charts always hide empty columns
            for_chart=True         # Indicate this is for chart display
        )

        # Apply year clipping based on scenario options
        scenario = self._get_current_scenario(is_results)
        if scenario and transformed_df is not None and not transformed_df.empty:
            min_year = scenario.options.get('MinYear', 2020)
            max_year = scenario.options.get('MaxYear', 2050)

            # Check for year column (could be 'year' or 'year_act')
            year_col = None
            for y in ['year', 'year_act']:
                if y in transformed_df.columns:
                    year_col = y
                    break

            if year_col:
                # Filter by year column - ensure numeric comparison
                try:
                    year_values = pd.to_numeric(transformed_df[year_col], errors='coerce')
                    transformed_df = transformed_df[
                        (year_values >= min_year) & (year_values <= max_year)
                    ]
                except (TypeError, ValueError):
                    # If conversion fails, skip filtering
                    pass
            elif isinstance(transformed_df.index, pd.MultiIndex):
                # Check for year in MultiIndex (could be 'year' or 'year_act')
                year_level = None
                for y in ['year', 'year_act']:
                    if y in transformed_df.index.names:
                        year_level = y
                        break

                if year_level:
                    # Filter by year in MultiIndex - ensure numeric comparison
                    try:
                        year_values = pd.to_numeric(transformed_df.index.get_level_values(year_level), errors='coerce')
                        mask = (year_values >= min_year) & (year_values <= max_year)
                        transformed_df = transformed_df[mask]
                    except (TypeError, ValueError):
                        # If conversion fails, skip filtering
                        pass
            elif hasattr(transformed_df.index, 'name') and transformed_df.index.name in ['year', 'year_act']:
                # Filter by year index - ensure numeric comparison
                try:
                    year_values = pd.to_numeric(transformed_df.index, errors='coerce')
                    transformed_df = transformed_df[
                        (year_values >= min_year) & (year_values <= max_year)
                    ]
                except (TypeError, ValueError):
                    # If conversion fails, skip filtering
                    pass

        return transformed_df

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
            all_validation_issues = []
            error_handler = ErrorHandler()

            for file_path in file_paths:
                def on_error(error_msg):
                    self.hide_progress_bar()
                    self._append_to_console(error_msg)
                    QMessageBox.critical(self, "Load Error", error_msg)
                    logging_manager.log_input_load(file_path, False, error_msg)

                with SafeOperation(f"input file loading: {os.path.basename(file_path)}",
                                 error_handler, logging_manager.logger, on_error) as safe_op:
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
                    if not validation['valid']:
                        all_validation_issues.extend(validation['issues'])

                    # Report validation results for this file
                    if validation['valid']:
                        self._append_to_console(f"✓ Successfully loaded {len(scenario.parameters)} parameters, {len(scenario.sets)} sets")
                    else:
                        self._append_to_console(f"⚠ Loaded {len(scenario.parameters)} parameters with validation issues:")

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
                    self._append_to_console(f"⚠ Loaded {len(loaded_files)} file(s) with {len(all_validation_issues)} total validation issues")
                else:
                    self._append_to_console(f"✓ Successfully loaded {len(loaded_files)} file(s) with {total_parameters} parameters, {total_sets} sets")

                self.statusbar.showMessage(f"Loaded {len(loaded_files)} input file(s)")

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
            error_handler = ErrorHandler()

            for file_path in file_paths:
                def on_error(error_msg):
                    self.hide_progress_bar()
                    self.console.append(error_msg)
                    QMessageBox.critical(self, "Load Error", error_msg)
                    logging_manager.log_results_load(file_path, False, {'error': error_msg})

                with SafeOperation(f"results file loading: {os.path.basename(file_path)}",
                                 error_handler, logging_manager.logger, on_error) as safe_op:
                    self._append_to_console(f"Loading results file: {file_path}")

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
                self._append_to_console(f"Loaded {len(loaded_files)} result file(s) with {total_variables} variables, {total_equations} equations")

                # Update dashboard with new results
                self.dashboard.update_results(True)

                self.statusbar.showMessage(f"Results loaded: {len(loaded_files)} file(s)")

    def _run_solver(self):
        """Handle running the solver"""
        if self.solver_manager.is_solver_running():
            self._append_to_console("Solver is already running")
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

        self._append_to_console(f"Starting solver with input: {input_path}")
        self._append_to_console(f"Using solver: {solver_name}")

        success = self.solver_manager.run_solver(input_path, solver_name)
        if not success:
            QMessageBox.critical(self, "Solver Error",
                               "Failed to start solver. Check console for details.")

    def _stop_solver(self):
        """Handle stopping the solver"""
        if self.solver_manager.is_solver_running():
            success = self.solver_manager.stop_solver()
            if success:
                self._append_to_console("Solver stop requested")
            else:
                QMessageBox.warning(self, "Stop Failed",
                                  "Failed to stop solver gracefully.")
        else:
            self._append_to_console("No solver is currently running")

    def _restore_normal_display(self):
        """Restore the normal data display (table and chart)"""
        try:
            # Hide dashboard and show data splitter
            self.results_file_dashboard.hide()
            self.dataSplitter.show()

        except Exception as e:
            self._append_to_console(f"Error restoring normal display: {str(e)}")

    def _show_results_file_dashboard(self):
        """Show the results file dashboard in the main content area"""
        try:
            # Get the current results scenario
            scenario = self._get_current_scenario(True)  # True for results

            # Hide data splitter and show dashboard
            self.dataSplitter.hide()
            self.results_file_dashboard.update_dashboard(scenario)
            self.results_file_dashboard.show()

        except Exception as e:
            self._append_to_console(f"Error showing results file dashboard: {str(e)}")
            QMessageBox.critical(self, "Dashboard Error",
                               f"Failed to show results file dashboard: {str(e)}")

    def _show_dashboard(self):
        """Show results dashboard"""
        try:
            self.dashboard.update_results(bool(self.results_analyzer.get_current_results()))
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()
        except Exception as e:
            self._append_to_console(f"Error showing dashboard: {str(e)}")
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
            self.statusbar.showMessage(f"Removed {file_type} file: {os.path.basename(file_path)}")
        else:
            self.statusbar.showMessage(f"Failed to remove {file_type} file: {os.path.basename(file_path)}")

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
            self.statusbar.showMessage(message)

    def hide_progress_bar(self):
        """Hide the progress bar"""
        self.progress_bar.setVisible(False)
        self.statusbar.showMessage("Ready")

    # Console methods
    def _append_to_console(self, message: str):
        """Append message to console"""
        self.console.append(message)

    def _update_status_from_solver(self, status: str):
        """Update status bar from solver manager"""
        self.statusbar.showMessage(status)

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

    def _save_current_session_state(self):
        """Save the current session state including selected files and view mode"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        settings.setValue("current_view", self.current_view)
        settings.setValue("selected_input_file", self.selected_input_file)
        settings.setValue("selected_results_file", self.selected_results_file)

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

    def _get_last_session_state(self):
        """Get the last session state from settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        current_view = settings.value("current_view", "input")
        selected_input_file = settings.value("selected_input_file", None)
        selected_results_file = settings.value("selected_results_file", None)
        return current_view, selected_input_file, selected_results_file

    def _restore_session_state(self, loaded_input_files, loaded_results_files):
        """Restore the session state after auto-loading files"""
        current_view, selected_input_file, selected_results_file = self._get_last_session_state()

        # Restore view mode
        self.current_view = current_view

        # Restore selected files if they were loaded
        if selected_input_file and selected_input_file in loaded_input_files:
            self.selected_input_file = selected_input_file
            if current_view == "input":
                self._switch_to_input_view()
        elif selected_results_file and selected_results_file in loaded_results_files:
            self.selected_results_file = selected_results_file
            if current_view == "results":
                self._switch_to_results_view()
        else:
            # If no specific file was selected or it wasn't loaded, switch to appropriate view
            if loaded_input_files and not loaded_results_files:
                self._switch_to_input_view()
            elif loaded_results_files and not loaded_input_files:
                self._switch_to_results_view()
            elif loaded_input_files and loaded_results_files:
                # Both loaded, switch to the saved view
                if current_view == "results":
                    self._switch_to_results_view()
                else:
                    self._switch_to_input_view()

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
                    self._append_to_console(f"Failed to auto-load input file {input_file}: {str(e)}")

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
                    self._append_to_console(f"✓ Auto-loaded results file with {stats['total_variables']} variables")

                except Exception as e:
                    # Hide progress bar on error
                    self.hide_progress_bar()
                    self._append_to_console(f"Failed to auto-load results file {results_file}: {str(e)}")

        if loaded_results_files:
            # Update UI with all loaded results files
            self.file_navigator.update_result_files(self.results_analyzer.get_loaded_file_paths())
            for file_path in loaded_results_files:
                self.file_navigator.add_recent_file(file_path, "results")
            # Update dashboard
            self.dashboard.update_results(True)

        # Restore session state (view mode and selected files)
        self._restore_session_state(loaded_input_files, loaded_results_files)

    def _save_file(self):
        """Save the current scenario to its original file"""
        scenario = self._get_current_scenario(self.current_view == "results")
        if not scenario:
            QMessageBox.warning(self, "No Data", "No scenario data is currently loaded.")
            return

        # Check if there are any modified parameters
        if not self.data_export_manager.has_modified_data(scenario):
            self.statusbar.showMessage("No changes to save")
            return

        # Determine the file path
        if self.current_view == "input" and self.selected_input_file:
            file_path = self.selected_input_file
        elif self.current_view == "results" and self.selected_results_file:
            file_path = self.selected_results_file
        else:
            # No specific file selected, use save as
            self._save_file_as()
            return

        # Confirm save
        modified_count = self.data_export_manager.get_modified_parameters_count(scenario)
        reply = QMessageBox.question(
            self, "Confirm Save",
            f"Save {modified_count} modified parameter(s) to {os.path.basename(file_path)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        # Save the file
        self._perform_save(scenario, file_path, False)

    def _save_file_as(self):
        """Save the current scenario to a new file"""
        scenario = self._get_current_scenario(self.current_view == "results")
        if not scenario:
            QMessageBox.warning(self, "No Data", "No scenario data is currently loaded.")
            return

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "",
            "Excel Files (*.xlsx);;All Files (*)"
        )

        if not file_path:
            return

        # Save the file
        self._perform_save(scenario, file_path, True)

    def _perform_save(self, scenario: ScenarioData, file_path: str, is_save_as: bool):
        """Perform the actual save operation"""
        try:
            self.statusbar.showMessage("Saving...")

            # Show progress bar
            self.show_progress_bar(100)

            # Perform save
            success = self.data_export_manager.save_scenario(scenario, file_path, modified_only=True)

            # Hide progress bar
            self.hide_progress_bar()

            if success:
                # Clear modified flags after successful save
                self.data_export_manager.clear_modified_flags(scenario)

                # Update status
                if is_save_as:
                    self.statusbar.showMessage(f"Saved as: {os.path.basename(file_path)}")
                    self._append_to_console(f"✓ Saved scenario as: {file_path}")
                else:
                    self.statusbar.showMessage(f"Saved: {os.path.basename(file_path)}")
                    self._append_to_console(f"✓ Saved changes to: {file_path}")

                # Update window title if this was the first save
                if is_save_as:
                    self.setWindowTitle(f"MessageIX Data Manager - {os.path.basename(file_path)}")

            else:
                QMessageBox.critical(self, "Save Failed", f"Failed to save file: {file_path}")
                self.statusbar.showMessage("Save failed")

        except Exception as e:
            # Hide progress bar on error
            self.hide_progress_bar()
            QMessageBox.critical(self, "Save Error", f"Error saving file: {str(e)}")
            self.statusbar.showMessage("Save failed")

    def closeEvent(self, event):
        """Handle application close event - check for unsaved changes"""
        # Check for unsaved changes before closing
        has_unsaved_changes = False

        # Check input scenarios
        if self.input_manager.get_current_scenario():
            if self.data_export_manager.has_modified_data(self.input_manager.get_current_scenario()):
                has_unsaved_changes = True

        # Check results scenarios
        if self.results_analyzer.get_current_results():
            if self.data_export_manager.has_modified_data(self.results_analyzer.get_current_results()):
                has_unsaved_changes = True

        if has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                # Try to save changes
                self._save_file()
                # If save was cancelled or failed, don't close
                if self.data_export_manager.has_modified_data(self._get_current_scenario(self.current_view == "results")):
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
            # If Discard, continue with closing

        # Save current session state
        self._save_current_session_state()
        super().closeEvent(event)
