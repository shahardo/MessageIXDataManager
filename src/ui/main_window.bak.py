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
from managers.file_handlers import InputFileHandler, ResultsFileHandler, AutoLoadHandler, ScenarioFileHandler
from managers.input_manager import InputManager
from managers.solver_manager import SolverManager
from managers.results_analyzer import ResultsAnalyzer
from managers.data_export_manager import DataExportManager
from managers.logging_manager import logging_manager
from managers.commands import EditCellCommand, EditPivotCommand, PasteColumnCommand
from managers.parameter_manager import ParameterManager
from managers.session_manager import SessionManager
from core.data_models import Scenario
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
        selected_scenario: Currently selected Scenario object
    """

    def __init__(self) -> None:
        """
        Initialize the main application window.

        Sets up UI components, managers, signal connections, and loads
        previously opened scenarios automatically.
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
        self.results_analyzer: ResultsAnalyzer = ResultsAnalyzer(self)
        self.data_export_manager: DataExportManager = DataExportManager()
        self.parameter_manager: ParameterManager = ParameterManager()
        self.session_manager: SessionManager = SessionManager()
        self.scenario_file_handler: ScenarioFileHandler = ScenarioFileHandler(self.input_manager, self.results_analyzer)

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

        # View state - initialize BEFORE auto-loading scenarios
        self.current_view: str = "input"  # "input" or "results"
        self.selected_scenario: Optional[Scenario] = None

        # Remember last selected parameters for each view
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

        # Auto-load last opened scenarios
        self._auto_load_last_scenarios()

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
        self.file_navigator = ProjectNavigator()
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

        # Connect navigator signals
        self.file_navigator.scenario_selected.connect(self._on_scenario_selected)
        self.file_navigator.load_scenario_requested.connect(self._on_load_scenario_requested)
        self.file_navigator.scenario_removed.connect(self._on_scenario_removed)
        self.file_navigator.scenario_renamed.connect(self._on_scenario_renamed)

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
        self.actionSave.triggered.connect(self._save_scenario)
        self.actionSave_As.triggered.connect(self._save_scenario_as)

        # Solver manager signals
        self.solver_manager.set_output_callback(self._append_to_console)
        self.solver_manager.set_status_callback(self._update_status_from_solver)

    def _on_scenario_selected(self, scenario: Scenario):
        """Handle scenario selection in navigator"""
        self.selected_scenario = scenario
        self._switch_to_scenario_view(scenario)
        self._clear_data_display()
        # Auto-select the last selected parameter if it exists in this scenario
        if self.last_selected_input_parameter and scenario.input_file:
            self._auto_select_parameter_if_exists(self.last_selected_input_parameter, False)
        # If no parameter is selected, auto-select dashboard
        elif not self.param_tree.selected_items():
            self._auto_select_parameter_if_exists("Dashboard", False)

        # Save current session state
        self._save_current_session_state()

    def _on_load_scenario_requested(self):
        """Handle request to load scenario when 'no scenarios loaded' is clicked"""
        self._open_scenario()

    def _on_scenario_removed(self, scenario_name: str):
        """Handle scenario removal from navigator"""
        # Remove scenario from session manager
        self.session_manager.remove_scenario(scenario_name)

        # Update navigator
        scenarios = self.session_manager.get_scenarios()
        self.file_navigator.update_scenarios(scenarios)

        # Clear selection if this was the selected scenario
        if self.selected_scenario and self.selected_scenario.name == scenario_name:
            self.selected_scenario = None
            self._clear_data_display()

        self.statusbar.showMessage(f"Removed scenario: {scenario_name}")

    def _on_scenario_renamed(self, old_name: str, new_name: str):
        """Handle scenario rename from navigator"""
        # Find the scenario
        scenarios = self.session_manager.get_scenarios()
        for scenario in scenarios:
            if scenario.name == old_name:
                # Update scenario name
                scenario.name = new_name
                # Update session manager
                self.session_manager.remove_scenario(old_name)
                self.session_manager.add_scenario(scenario)
                # Update navigator
                self.file_navigator.update_scenarios(scenarios)
                # Update selected scenario reference
                if self.selected_scenario and self.selected_scenario.name == old_name:
                    self.selected_scenario.name = new_name
                self.statusbar.showMessage(f"Renamed scenario: {old_name} -> {new_name}")
                return

        self.statusbar.showMessage(f"Failed to rename scenario: {old_name}")

    def _switch_to_scenario_view(self, scenario: Scenario):
        """Switch to the appropriate view based on scenario type"""
        if scenario.input_file:
            self.current_view = "input"
            self.param_tree.set_view_mode(False)
            # Update parameter tree
            self.param_tree.update_parameters(scenario.data)
        elif scenario.results_file:
            self.current_view = "results"
            self.param_tree.set_view_mode(True)
            # Update results tree
            self.param_tree.update_results(scenario.data)
        else:
            # Handle scenario without files (shouldn't happen)
            self.current_view = "input"
            self.param_tree.set_view_mode(False)
            self.param_tree.clear()

    def _clear_data_display(self):
        """Clear the data display and chart"""
        if self.selected_scenario:
            if self.current_view == "results" and self.selected_scenario.results_file:
                # Show dashboard for results scenarios when no parameter is selected
                self._show_results_file_dashboard()
            elif self.current_view == "input" and self.selected_scenario.input_file:
                # Show input file dashboard for input scenarios when no parameter is selected
                self._show_input_file_dashboard()
            else:
                self.data_display.display_parameter_data(None, False)  # This will show placeholder
                self.chart_widget.show_placeholder()
        else:
            self.data_display.display_parameter_data(None, False)  # This will show placeholder
            self.chart_widget.show_placeholder()

    def _get_current_scenario(self, is_results: bool) -> Optional[Scenario]:
        """Get the current scenario based on selection and view mode"""
        if is_results:
            return self.selected_scenario if self.selected_scenario and self.selected_scenario.results_file else None
        else:
            return self.selected_scenario if self.selected_scenario and self.selected_scenario.input_file else None

    def _get_current_displayed_parameter(self) -> Optional[str]:
        """Get the currently displayed parameter name"""
        # First try to get from tree selection
        selected_items = self.param_tree.selected_items()
        if selected_items:
            candidate_name = selected_items[0].text(0)
            if candidate_name and not candidate_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")):
                return candidate_name

        # If tree selection failed, use the stored currently displayed parameter
        if self.current_displayed_parameter:
            return self.current_displayed_parameter

        return None

    def _open_scenario(self):
        """Handle opening a scenario file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Scenario File", "",
            "Scenario Files (*.pkl);;All Files (*)"
        )

        if file_path:
            # Use the scenario file handler to load scenario
            scenario = self.scenario_file_handler.load_scenario(
                file_path, self.update_progress, self._append_to_console
            )

            if scenario:
                # Add scenario to session manager
                self.session_manager.add_scenario(scenario)

                # Update navigator
                scenarios = self.session_manager.get_scenarios()
                self.file_navigator.update_scenarios(scenarios)

                # Select the loaded scenario
                self.file_navigator.update_scenarios([scenario])

                self.statusbar.showMessage(f"Loaded scenario: {scenario.name}")

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
                # Create scenarios for each loaded file
                for file_path in loaded_files:
                    # Create scenario name from file name
                    scenario_name = os.path.splitext(os.path.basename(file_path))[0]
                    # Import scenario
                    scenario = self.scenario_file_handler.import_scenario(
                        file_path, scenario_name, self._append_to_console, self.update_progress
                    )
                    if scenario:
                        # Add scenario to session manager
                        self.session_manager.add_scenario(scenario)

                # Update navigator
                scenarios = self.session_manager.get_scenarios()
                self.file_navigator.update_scenarios(scenarios)

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
                # Create scenarios for each loaded file
                for file_path in loaded_files:
                    # Create scenario name from file name
                    scenario_name = os.path.splitext(os.path.basename(file_path))[0]
                    # Import scenario
                    scenario = self.scenario_file_handler.import_scenario(
                        file_path, scenario_name, self._append_to_console, self.update_progress
                    )
                    if scenario:
                        # Add scenario to session manager
                        self.session_manager.add_scenario(scenario)

                # Update navigator
                scenarios = self.session_manager.get_scenarios()
                self.file_navigator.update_scenarios(scenarios)

                # Show summary
                self._append_to_console(f"Loaded {len(loaded_files)} result file(s) with {result['total_variables']} variables, {result['total_equations']} equations")

                # Update dashboard with new results
                self.dashboard.update_results(True)

                self.statusbar.showMessage(f"Results loaded: {len(loaded_files)} file(s)")

    def _save_scenario(self):
        """Save the current scenario to its original file"""
        scenario = self._get_current_scenario(self.current_view == "results")
        if not scenario:
            QMessageBox.warning(self, "No Data", "No scenario data is currently loaded.")
            return

        # Check if there are any modified parameters
        if not self.data_export_manager.has_modified_data(scenario.data):
            self.statusbar.showMessage("No changes to save")
            return

        # Determine the file path
        if self.current_view == "input" and scenario.input_file:
            file_path = scenario.input_file
        elif self.current_view == "results" and scenario.results_file:
            file_path = scenario.results_file
        else:
            # No specific file, use save as
            self._save_scenario_as()
            return

        # Confirm save
        modified_count = self.data_export_manager.get_modified_parameters_count(scenario.data)
        reply = QMessageBox.question(
            self, "Confirm Save",
            f"Save {modified_count} modified parameter(s) to {os.path.basename(file_path)}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        # Save the scenario
        success = self.scenario_file_handler.save_scenario(scenario, self._append_to_console)

        if success:
            # Clear modified flags after successful save
            self.data_export_manager.clear_modified_flags(scenario.data)

            # Update status
            self.statusbar.showMessage(f"Saved: {os.path.basename(file_path)}")
            self._append_to_console(f"✓ Saved changes to: {file_path}")

    def _save_scenario_as(self):
        """Save the current scenario to a new file"""
        scenario = self._get_current_scenario(self.current_view == "results")
        if not scenario:
            QMessageBox.warning(self, "No Data", "No scenario data is currently loaded.")
            return

        # Get save file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Scenario As", "",
            "Scenario Files (*.pkl);;All Files (*)"
        )

        if not file_path:
            return

        # Save the scenario
        success = self.scenario_file_handler.save_scenario(scenario, self._append_to_console)

        if success:
            # Update scenario file path
            scenario.message_scenario_file = file_path
            # Add scenario to session manager
            self.session_manager.add_scenario(scenario)
            # Update navigator
            scenarios = self.session_manager.get_scenarios()
            self.file_navigator.update_scenarios(scenarios)
            # Update status
            self.statusbar.showMessage(f"Saved as: {os.path.basename(file_path)}")
            self._append_to_console(f"✓ Saved scenario as: {file_path}")

    def _auto_load_last_scenarios(self):
        """Automatically load the last opened scenarios on startup"""
        # Get scenarios from session manager
        scenarios = self.session_manager.get_scenarios()

        if scenarios:
            # Update navigator
            self.file_navigator.update_scenarios(scenarios)

            # Select the first scenario
            if scenarios:
                self.file_navigator.update_scenarios([scenarios[0]])

        self.statusbar.showMessage(f"Loaded {len(scenarios)} scenario(s)")

    def closeEvent(self, event):
        """Handle application close event - check for unsaved changes"""
        # Check for unsaved changes before closing
        has_unsaved_changes = False

        # Check scenarios
        scenarios = self.session_manager.get_scenarios()
        for scenario in scenarios:
            if self.data_export_manager.has_modified_data(scenario.data):
                has_unsaved_changes = True
                break

        if has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save them before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )

            if reply == QMessageBox.Save:
                # Try to save changes
                self._save_scenario()
                # If save was cancelled or failed, don't close
                scenarios = self.session_manager.get_scenarios()
                for scenario in scenarios:
                    if self.data_export_manager.has_modified_data(scenario.data):
                        event.ignore()
                        return
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
            # If Discard, continue with closing

        # Save current session state
        self._save_current_session_state()
        super().closeEvent(event)

    def _on_parameter_selected(self, parameter_name: str):
        """Handle parameter selection in the parameter tree"""
        # Get the parameter information from the parameter manager
        parameter_info = self.parameter_manager.get_parameter_info(parameter_name)
        if parameter_info:
            self.current_displayed_parameter = parameter_name
            # Create empty DataFrame for the parameter
            empty_df = self.parameter_manager.create_empty_parameter_dataframe(parameter_name)
            self.data_display.display_parameter_data(empty_df, self.current_view == "results")
            self.chart_widget.update_chart(empty_df, parameter_name, self.current_view == "results")

    # Other methods remain the same...

    def _save_current_session_state(self):
        """Save the current session state including selected scenario and view mode"""
        state = {
            'current_view': self.current_view,
            'selected_scenario': self.selected_scenario.name if self.selected_scenario else None,
            'last_selected_input_parameter': self.last_selected_input_parameter,
            'last_selected_results_parameter': self.last_selected_results_parameter,
        }
        self.session_manager.save_session_state(state)