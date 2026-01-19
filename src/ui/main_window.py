"""
Main application window for MessageIX Data Manager

Refactored to use composition with focused UI components.
Provides the primary user interface for loading, analyzing, and visualizing
MESSAGEix input files and results.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5 import uic
import os
import pandas as pd
from typing import Optional, List, Dict, Any

from .dashboard import ResultsDashboard
from .results_file_dashboard import ResultsFileDashboard
from .input_file_dashboard import InputFileDashboard
from .navigator import ProjectNavigator
from .components import (
    DataDisplayWidget, ChartWidget, ParameterTreeWidget, FileNavigatorWidget
)
from .components.find_widget import FindWidget
from .components.data_display_widget import UndoManager
from .controllers.find_controller import FindController
from .controllers.edit_handler import EditHandler
from managers.file_handlers import InputFileHandler, ResultsFileHandler, AutoLoadHandler
from managers.input_manager import InputManager
from managers.solver_manager import SolverManager
from managers.results_analyzer import ResultsAnalyzer
from managers.data_export_manager import DataExportManager
from managers.logging_manager import logging_manager
from managers.commands import EditCellCommand, EditPivotCommand, PasteColumnCommand
from managers.parameter_manager import ParameterManager
from managers.session_manager import SessionManager
from core.data_models import ScenarioData
from utils.error_handler import ErrorHandler, SafeOperation
from utils.data_transformer import DataTransformer


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
        self.parameter_manager: ParameterManager = ParameterManager()
        self.session_manager: SessionManager = SessionManager()

        # Load technology descriptions from CSV
        self.tech_descriptions = self._load_tech_descriptions()

        # Initialize dashboard
        self.dashboard: ResultsDashboard = ResultsDashboard(self.results_analyzer)
        self.results_file_dashboard: ResultsFileDashboard = ResultsFileDashboard(self.results_analyzer)
        self.input_file_dashboard: InputFileDashboard = InputFileDashboard(self.input_manager)

        # Initialize undo manager
        self.undo_manager = UndoManager()

        if not hasattr(self, 'dataContainer'):
            # probably test environment without UI loaded
            return
        
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

        # Store currently displayed parameter for cell editing (independent of tree selection)
        self.current_displayed_parameter: Optional[str] = None

        # Initialize find widget and controller
        self.find_widget = FindWidget(self)
        self.find_widget.hide()
        self.find_controller = FindController(self.param_tree, self.param_table)
        self.current_search_mode = "parameter"  # "parameter" or "table"
        self.last_parameter_search = ""  # Remember search text for parameters
        self.last_table_search = ""      # Remember search text for tables

        # Initialize edit handler
        self.edit_handler = EditHandler(self._get_current_scenario, self.data_display)

        # Initialize file handlers
        self.input_file_handler = InputFileHandler(self.input_manager)
        self.results_file_handler = ResultsFileHandler(self.results_analyzer)
        self.auto_load_handler = AutoLoadHandler(self.input_manager, self.results_analyzer, self.session_manager)

        self._connect_find_widget_signals()

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

        # Add widgets to the layout
        layout = self.dataContainer.layout()
        layout.addWidget(self.dataSplitter)
        layout.addWidget(self.results_file_dashboard)
        layout.addWidget(self.input_file_dashboard)

        # Initially show data splitter and hide dashboards
        self.dataSplitter.show()
        self.results_file_dashboard.hide()
        self.input_file_dashboard.hide()

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

        # Set parameter manager for the tree widget
        self.param_tree.set_parameter_manager(self.parameter_manager)

    def _connect_component_signals(self):
        """Connect component signals to main window handlers"""
        # Parameter tree signals
        self.param_tree.parameter_selected.connect(self._on_parameter_selected)
        self.param_tree.options_changed.connect(self._on_options_changed)

        # Data display signals
        self.data_display.display_mode_changed.connect(self._on_display_mode_changed)
        self.data_display.cell_value_changed.connect(self._on_cell_value_changed)
        self.data_display.column_paste_requested.connect(self._on_column_paste_requested)
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
        self.actionFind.triggered.connect(self._show_find_widget)

        # Edit menu actions
        self.actionUndo.triggered.connect(self._undo)
        self.actionRedo.triggered.connect(self._redo)
        self.actionCut.triggered.connect(self._cut)
        self.actionCopy.triggered.connect(self._copy)
        self.actionPaste.triggered.connect(self._paste)

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
            # If no parameter is selected, auto-select dashboard
            elif not self.param_tree.selectedItems():
                self._auto_select_parameter_if_exists("Dashboard", False)
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
            self.current_displayed_parameter = None
            self._clear_data_display()
            return

        # Special handling for dashboard selection
        if parameter_name == "Dashboard" and is_results:
            # Remember this parameter for future file switches
            self.last_selected_results_parameter = parameter_name
            self.current_displayed_parameter = None

            # Show the results file dashboard
            self._show_results_file_dashboard()
            return

        elif parameter_name == "Dashboard" and not is_results:
            # Remember this parameter for future file switches
            self.last_selected_input_parameter = parameter_name
            self.current_displayed_parameter = None

            # Show the input file dashboard
            self._show_input_file_dashboard()
            return

        # Remember this parameter for future file switches and current display
        if is_results:
            self.last_selected_results_parameter = parameter_name
        else:
            self.last_selected_input_parameter = parameter_name

        # Store the currently displayed parameter (independent of tree selection)
        self.current_displayed_parameter = parameter_name

        # Switch back to normal data display if dashboard was showing
        self._restore_normal_display()

        try:
            # Get the parameter object and display it
            scenario = self._get_current_scenario(is_results)
            if scenario:
                parameter = scenario.get_parameter(parameter_name)
                if parameter:
                    # Display data using the data display component
                    self.data_display.display_parameter_data(parameter, is_results)

                    # Update chart with transformed data for display
                    scenario = self._get_current_scenario(is_results)
                    filters = self.data_display._get_current_filters() if hasattr(self.data_display, '_get_current_filters') else {}
                    chart_df = DataTransformer.prepare_chart_data(
                        parameter, is_results=is_results,
                        scenario_options=scenario.options if scenario else None,
                        filters=filters, hide_empty=False
                    )

                    if chart_df is not None:
                        self.chart_widget.update_chart(chart_df, parameter.name, is_results)
        except Exception as e:
            print(f"ERROR in parameter selection: {e}")
            import traceback
            traceback.print_exc()
            # Try to show a basic error message in the console
            self._append_to_console(f"Error displaying parameter {parameter_name}: {str(e)}")

    def _on_display_mode_changed(self):
        """Handle display mode change (raw/advanced)"""
        try:
            # Refresh current parameter display
            self._refresh_current_display()
        except Exception as e:
            print(f"ERROR in _on_display_mode_changed: {e}")
            import traceback
            traceback.print_exc()

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
        # Get the currently displayed parameter name
        param_name = self._get_current_displayed_parameter()
        if not param_name:
            return

        # Use the edit handler to process the change
        success = self.edit_handler.handle_cell_value_change(mode, row_or_year, col_or_tech, new_value, self.undo_manager)

        if success:
            # Update UI elements
            self._update_undo_redo_ui()
            self.statusbar.showMessage(f"Modified {param_name} - unsaved changes")

            # Update chart immediately with the new data
            scenario = self._get_current_scenario(self.current_view == "results")
            filters = self.data_display._get_current_filters() if hasattr(self.data_display, '_get_current_filters') else {}
            parameter = scenario.get_parameter(param_name) if scenario else None
            if parameter:
                chart_df = DataTransformer.prepare_chart_data(
                    parameter, is_results=self.current_view == "results",
                    scenario_options=scenario.options if scenario else None,
                    filters=filters, hide_empty=False
                )
                if chart_df is not None:
                    self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")

            # Refresh the display to show the updated pivoted data (for advanced mode)
            if mode == "advanced":
                self._refresh_current_display()

            # Log the change
            self._append_to_console(f"Updated {param_name}: {col_or_tech} = {new_value}")

    def _on_column_paste_requested(self, column_name: str, paste_format: str, row_changes: dict):
        """Handle column paste requests from table"""
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

        # Create the paste command
        from managers.commands import PasteColumnCommand
        command = PasteColumnCommand(scenario, param_name, column_name, row_changes)

        # Execute the command
        success = self.undo_manager.execute(command)

        if success:
            # Update UI elements
            self._update_undo_redo_ui()

            # Update status bar
            self.statusbar.showMessage(f"Modified {param_name} - unsaved changes")

            # Mark parameter as modified
            scenario.mark_modified(param_name)

            # Update chart immediately with the new data
            scenario = self._get_current_scenario(self.current_view == "results")
            filters = self.data_display._get_current_filters() if hasattr(self.data_display, '_get_current_filters') else {}
            chart_df = DataTransformer.prepare_chart_data(
                parameter, is_results=self.current_view == "results",
                scenario_options=scenario.options if scenario else None,
                filters=filters, hide_empty=False
            )
            self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")

            # Refresh the display to show the updated data
            self._refresh_current_display()

            # Log the change
            self._append_to_console(f"Pasted {len(row_changes)} values into column '{column_name}' ({param_name})")
        else:
            self._append_to_console("Paste operation failed")

    def _on_chart_update_needed(self):
        """Update chart when data changes without refreshing the table"""
        try:
            # Get the currently selected parameter
            selected_items = self.param_tree.selectedItems()
            if not selected_items:
                print("DEBUG: No selected items in parameter tree")
                return

            param_name = selected_items[0].text(0)
            print(f"DEBUG: Chart update needed for parameter: {param_name}")
            if not param_name or param_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
                print(f"DEBUG: Skipping chart update for category/header: {param_name}")
                return

            # Get the parameter object
            scenario = self._get_current_scenario(self.current_view == "results")
            if not scenario:
                print("DEBUG: No current scenario found")
                return

            parameter = scenario.get_parameter(param_name)
            if not parameter:
                print(f"DEBUG: Parameter {param_name} not found in scenario")
                return

            print(f"DEBUG: Updating chart for parameter {param_name} with {len(parameter.df)} rows")

            # Update chart with current data (which includes our changes)
            scenario = self._get_current_scenario(self.current_view == "results")
            filters = self.data_display._get_current_filters() if hasattr(self.data_display, '_get_current_filters') else {}
            chart_df = DataTransformer.prepare_chart_data(
                parameter, is_results=self.current_view == "results",
                scenario_options=scenario.options if scenario else None,
                filters=filters, hide_empty=False
            )
            if chart_df is not None:
                print(f"DEBUG: Chart data has {len(chart_df)} rows, {len(chart_df.columns)} columns")
                self.chart_widget.update_chart(chart_df, parameter.name, self.current_view == "results")
            else:
                print("DEBUG: Chart data is None")

        except Exception as e:
            print(f"ERROR in _on_chart_update_needed: {e}")
            import traceback
            traceback.print_exc()

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
        else:
            # No results scenario available - clear tree and switch back to input view
            self.param_tree.clear()
            self._switch_to_input_view()

    def _clear_data_display(self):
        """Clear the data display and chart"""
        if self.current_view == "results" and self.selected_results_file:
            # Show dashboard for results files when no parameter is selected
            self._show_results_file_dashboard()
        elif self.current_view == "input" and self.input_manager.get_current_scenario():
            # Show input file dashboard for input files when no parameter is selected
            self._show_input_file_dashboard()
        else:
            self.data_display.display_parameter_data(None, False)  # This will show placeholder
            self.chart_widget.show_placeholder()

    def _refresh_current_display(self):
        """Refresh the current parameter/result display"""
        # This would be called when display mode or chart type changes
        # Use the stored current parameter instead of tree selection (which may be cleared)
        if self.current_displayed_parameter:
            print(f"DEBUG: Refreshing display for parameter: {self.current_displayed_parameter}")
            self._on_parameter_selected(self.current_displayed_parameter, self.current_view == "results")
        else:
            print("DEBUG: No current displayed parameter to refresh")

    def _auto_select_parameter_if_exists(self, parameter_name: str, is_results: bool):
        """Auto-select a parameter in the tree if it exists in the current scenario"""
        if parameter_name == "Dashboard":
            # Special handling for Dashboard - it's at root level
            root = self.param_tree.invisibleRootItem()
            if root:
                for i in range(root.childCount()):
                    child = root.child(i)
                    if child and child.text(0) == "Dashboard":
                        self.param_tree.setCurrentItem(child)
                        self.param_tree.scrollToItem(child)
                        return True
            return False

        scenario = self._get_current_scenario(is_results)
        if not scenario or not scenario.get_parameter(parameter_name):
            return  # Parameter doesn't exist in this scenario

        # Find and select the parameter in the tree
        def find_and_select_item(parent_item):
            """Recursively search for the parameter item"""
            if not parent_item:
                return False
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

    def _get_current_displayed_parameter(self) -> Optional[str]:
        """Get the currently displayed parameter name"""
        # First try to get from tree selection
        selected_items = self.param_tree.selectedItems()
        if selected_items:
            candidate_name = selected_items[0].text(0)
            if candidate_name and not candidate_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
                return candidate_name

        # If tree selection failed, use the stored currently displayed parameter
        if self.current_displayed_parameter:
            return self.current_displayed_parameter

        return None

    def _open_input_file(self):
        """Handle opening input Excel file(s)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Input Excel File(s)", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_paths:
            # Use the file handler to load files
            result = self.input_file_handler.load_files(
                file_paths, self.update_progress, self._append_to_console
            )

            loaded_files = result['loaded_files']
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
                all_validation_issues = result['validation_issues']
                if all_validation_issues:
                    self._append_to_console(f"⚠ Loaded {len(loaded_files)} file(s) with {len(all_validation_issues)} total validation issues")
                else:
                    self._append_to_console(f"✓ Successfully loaded {len(loaded_files)} file(s) with {result['total_parameters']} parameters, {result['total_sets']} sets")

                self.statusbar.showMessage(f"Loaded {len(loaded_files)} input file(s)")

    def _open_results_file(self):
        """Handle opening results Excel file(s)"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Results Excel File(s)", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_paths:
            # Use the file handler to load files
            result = self.results_file_handler.load_files(
                file_paths, self.update_progress, self._append_to_console
            )

            loaded_files = result['loaded_files']
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
                self._append_to_console(f"Loaded {len(loaded_files)} result file(s) with {result['total_variables']} variables, {result['total_equations']} equations")

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
            # Hide dashboards and show data splitter
            self.results_file_dashboard.hide()
            self.input_file_dashboard.hide()
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

    def _show_input_file_dashboard(self):
        """Show the input file dashboard in the main content area"""
        try:
            # Get the current input scenario
            scenario = self._get_current_scenario(False)  # False for input

            # Hide data splitter and show dashboard
            self.dataSplitter.hide()
            self.input_file_dashboard.update_dashboard(scenario)
            self.input_file_dashboard.show()

        except Exception as e:
            self._append_to_console(f"Error showing input file dashboard: {str(e)}")
            QMessageBox.critical(self, "Dashboard Error",
                               f"Failed to show input file dashboard: {str(e)}")

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
        self.session_manager.add_recent_file(file_path, file_type)

    def _save_current_session_state(self):
        """Save the current session state including selected files and view mode"""
        state = {
            'current_view': self.current_view,
            'selected_input_file': self.selected_input_file,
            'selected_results_file': self.selected_results_file,
            'last_selected_input_parameter': self.last_selected_input_parameter,
            'last_selected_results_parameter': self.last_selected_results_parameter,
        }
        self.session_manager.save_session_state(state)

    def _remove_last_opened_file(self, file_path, file_type):
        """Remove a file from the last opened files settings"""
        self.session_manager.remove_recent_file(file_path, file_type)

    def _get_last_opened_files(self):
        """Get the last opened file paths from settings"""
        input_files = self.session_manager.get_last_opened_files("input")
        results_files = self.session_manager.get_last_opened_files("results")
        return input_files, results_files

    def _get_last_session_state(self):
        """Get the last session state from settings"""
        state = self.session_manager.load_session_state()
        return state['current_view'], state['selected_input_file'], state['selected_results_file']

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
        # Use the auto load handler
        loaded_input_files, loaded_results_files = self.auto_load_handler.auto_load_files(
            self._append_to_console, self.update_progress
        )

        if loaded_input_files:
            # Update UI with all loaded input files
            self.file_navigator.update_input_files(loaded_input_files)
            for file_path in loaded_input_files:
                self.file_navigator.add_recent_file(file_path, "input")
            # Update parameter tree
            self._switch_to_input_view()

            # Auto-select Dashboard for input files
            self._auto_select_parameter_if_exists("Dashboard", False)

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
        input_scenario = self.input_manager.get_current_scenario()
        if input_scenario:
            if self.data_export_manager.has_modified_data(input_scenario):
                has_unsaved_changes = True

        # Check results scenarios
        results_scenario = self.results_analyzer.get_current_results()
        if results_scenario:
            if self.data_export_manager.has_modified_data(results_scenario):
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
                current_scenario = self._get_current_scenario(self.current_view == "results")
                if current_scenario and self.data_export_manager.has_modified_data(current_scenario):
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
            # If Discard, continue with closing

        # Save current session state
        self._save_current_session_state()
        super().closeEvent(event)

    def _connect_find_widget_signals(self):
        """Connect find widget signals"""
        self.find_widget.find_next_requested.connect(self._find_next)
        self.find_widget.find_previous_requested.connect(self._find_previous)
        self.find_widget.find_text_changed.connect(self._find_text_changed)
        self.find_widget.closed.connect(self._hide_find_widget)

    def _show_find_widget(self):
        """Show the find widget based on current context"""
        # Determine search context based on current focus
        focus_widget = QApplication.focusWidget()

        # Check if the current focus is on the parameter tree
        if focus_widget and (focus_widget is self.param_tree or self.param_tree.isAncestorOf(focus_widget)):
            search_mode = "parameter"
        # Check if the current focus is on the data table or related widgets
        elif focus_widget and (focus_widget is self.param_table or self.param_table.isAncestorOf(focus_widget) or
                               focus_widget is self.tableContainer or self.tableContainer.isAncestorOf(focus_widget)):
            search_mode = "table"
        else:
            # Default to parameter search if focus is unclear
            search_mode = "parameter"

        # Store the search mode for consistent behavior during the search session
        self.current_search_mode = search_mode

        # Calculate position based on search mode - ensure within main window bounds
        main_rect = self.rect()
        widget_width = 400  # Approximate width of find widget
        widget_height = 40  # Approximate height of find widget

        if search_mode == "parameter":
            # Position in top-left area above parameter tree
            widget_pos = QPoint(20, 30)  # Fixed position near top-left
        else:
            # Position above the data table area
            table_container_rect = self.tableContainer.geometry()
            # Position at the top-right of the table container
            widget_pos = QPoint(
                table_container_rect.right() - widget_width,
                table_container_rect.top() - widget_height - 5  # 5px above the table
            )

        # Ensure position is within bounds
        widget_pos.setX(max(10, min(widget_pos.x(), main_rect.width() - widget_width - 10)))
        widget_pos.setY(max(10, min(widget_pos.y(), main_rect.height() - widget_height - 10)))

        self.find_widget.show_at_position(widget_pos, search_mode)

        # Restore last search text for this mode
        if search_mode == "parameter":
            self.find_widget.set_search_text(self.last_parameter_search)
        elif search_mode == "table":
            self.find_widget.set_search_text(self.last_table_search)

        # Ensure the widget gets proper focus
        QApplication.setActiveWindow(self.find_widget)
        self.find_widget.search_input.setFocus()
        self.find_widget.search_input.selectAll()

        # Initialize search if there's existing data
        if search_mode == "parameter":
            self._initialize_parameter_search()
        else:
            self._initialize_table_search()

    def _hide_find_widget(self):
        """Hide the find widget"""
        self.find_widget.hide()

    def _find_next(self, search_text: str):
        """Find next match"""
        if self.find_widget.isVisible():
            # Use stored search mode for consistent behavior
            if self.current_search_mode == "parameter":
                self._find_next_parameter(search_text)
            else:
                self._find_next_table_cell(search_text)

    def _find_previous(self, search_text: str):
        """Find previous match"""
        if self.find_widget.isVisible():
            # Use stored search mode for consistent behavior
            if self.current_search_mode == "parameter":
                self._find_previous_parameter(search_text)
            else:
                self._find_previous_table_cell(search_text)

    def _find_text_changed(self, search_text: str):
        """Handle search text changes - find first match"""
        # Save the search text for this mode
        if self.current_search_mode == "parameter":
            self.last_parameter_search = search_text
        else:
            self.last_table_search = search_text

        if self.find_widget.isVisible() and search_text.strip():
            # Use stored search mode for consistent behavior
            if self.current_search_mode == "parameter":
                self._find_first_parameter(search_text)
            else:
                self._find_first_table_cell(search_text)

    def _initialize_parameter_search(self):
        """Initialize parameter search - collect all parameter names"""
        scenario = self._get_current_scenario(self.current_view == "results")
        self.find_controller.initialize_parameter_search(scenario)

    def _initialize_table_search(self):
        """Initialize table search - scan all table cells"""
        self.find_controller.initialize_table_search()

    def _find_first_parameter(self, search_text: str):
        """Find first parameter match"""
        current_match, total_matches = self.find_controller.find_first_parameter(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _find_next_parameter(self, search_text: str):
        """Find next parameter match"""
        current_match, total_matches = self.find_controller.find_next_parameter(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _find_previous_parameter(self, search_text: str):
        """Find previous parameter match"""
        current_match, total_matches = self.find_controller.find_previous_parameter(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _select_parameter_match(self, match_index: int):
        """Select the parameter match in the tree"""
        if 0 <= match_index < len(self.parameter_matches):
            param_name, tree_item = self.parameter_matches[match_index]
            self.param_tree.setCurrentItem(tree_item)
            self.param_tree.scrollToItem(tree_item)
            # Expand parent categories to show the item
            parent = tree_item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

    def _find_first_table_cell(self, search_text: str):
        """Find first table cell match"""
        current_match, total_matches = self.find_controller.find_first_table_cell(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _find_next_table_cell(self, search_text: str):
        """Find next table cell match"""
        current_match, total_matches = self.find_controller.find_next_table_cell(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _find_previous_table_cell(self, search_text: str):
        """Find previous table cell match"""
        current_match, total_matches = self.find_controller.find_previous_table_cell(search_text)
        self.find_widget.update_match_count(current_match, total_matches)

    def _select_table_match(self, match_index: int):
        """Select the table cell match"""
        if 0 <= match_index < len(self.table_matches):
            row, col, cell_text = self.table_matches[match_index]
            self.param_table.setCurrentCell(row, col)
            self.param_table.scrollToItem(self.param_table.item(row, col))

    # Edit menu action handlers

    def _undo(self):
        """Handle undo action"""
        # Perform undo operation
        success = self.undo_manager.undo()

        if success:
            # Update UI
            self._update_undo_redo_ui()
            self._refresh_current_display()
            undo_desc = self.undo_manager.get_undo_description()
            self._append_to_console(f"Undid: {undo_desc}")
        else:
            self._append_to_console("Undo: No operations to undo.")

    def _redo(self):
        """Handle redo action"""
        # Perform redo operation
        success = self.undo_manager.redo()

        if success:
            # Update UI
            self._update_undo_redo_ui()
            self._refresh_current_display()
            redo_desc = self.undo_manager.get_redo_description()
            self._append_to_console(f"Redid: {redo_desc}")
        else:
            self._append_to_console("Redo: No operations to redo.")

    def _cut(self):
        """Handle cut action - cut currently selected column data"""
        # For now, try to cut from the currently selected column in the table
        if hasattr(self.data_display, 'param_table'):
            current_column = self.data_display.param_table.currentColumn()
            if current_column >= 0:
                self.data_display.cut_column_data(current_column)
            else:
                QMessageBox.information(self, "Cut", "Please select a column header first by right-clicking on it.")

    def _copy(self):
        """Handle copy action - copy currently selected column data"""
        # For now, try to copy from the currently selected column in the table
        if hasattr(self.data_display, 'param_table'):
            current_column = self.data_display.param_table.currentColumn()
            if current_column >= 0:
                self.data_display.copy_column_data(current_column)
            else:
                QMessageBox.information(self, "Copy", "Please select a column header first by right-clicking on it.")

    def _paste(self):
        """Handle paste action - paste to currently selected column"""
        # For now, try to paste to the currently selected column in the table
        if hasattr(self.data_display, 'param_table'):
            current_column = self.data_display.param_table.currentColumn()
            if current_column >= 0:
                self.data_display.paste_column_data(current_column)
            else:
                QMessageBox.information(self, "Paste", "Please select a column header first by right-clicking on it.")



    def _update_undo_redo_ui(self):
        """Update the UI to reflect current undo/redo state"""
        try:
            # Update menu item enabled state
            if hasattr(self, 'actionUndo'):
                self.actionUndo.setEnabled(self.undo_manager.can_undo())
            if hasattr(self, 'actionRedo'):
                self.actionRedo.setEnabled(self.undo_manager.can_redo())

            # Update status bar with current operation descriptions
            undo_desc = self.undo_manager.get_undo_description()
            redo_desc = self.undo_manager.get_redo_description()

            if undo_desc:
                self.statusbar.showMessage(f"Ready - Undo: {undo_desc}")
            elif redo_desc:
                self.statusbar.showMessage(f"Ready - Redo: {redo_desc}")
            else:
                self.statusbar.showMessage("Ready")

        except Exception as e:
            print(f"Error updating undo/redo UI: {e}")
