"""
Main application window for MessageIX Data Manager
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QStatusBar, QMenuBar, QMenu, QAction, QFileDialog, QMessageBox, QTreeWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
import os
import pandas as pd

from .navigator import ProjectNavigator
from .dashboard import ResultsDashboard
from managers.input_manager import InputManager
from managers.solver_manager import SolverManager
from managers.results_analyzer import ResultsAnalyzer
from managers.logging_manager import logging_manager


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MessageIX Data Manager - message_ix Data Manager")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize managers
        self.input_manager = InputManager()
        self.solver_manager = SolverManager()
        self.results_analyzer = ResultsAnalyzer()

        # Initialize dashboard
        self.dashboard = ResultsDashboard(self.results_analyzer)

        # Connect solver manager to console
        self.solver_manager.set_output_callback(self._append_to_console)
        self.solver_manager.set_status_callback(self._update_status_from_solver)

        # Initialize components
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()

    def _setup_ui(self):
        """Set up the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Project navigator
        self.navigator = ProjectNavigator()
        splitter.addWidget(self.navigator)

        # Right panel: Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # Content splitter (vertical)
        content_splitter = QSplitter(Qt.Vertical)

        # Top: Parameter views
        self.param_tree = QTreeWidget()
        self.param_tree.setHeaderLabel("Parameters")
        self.param_tree.itemSelectionChanged.connect(self._on_parameter_selected)
        content_splitter.addWidget(self.param_tree)

        self.param_table = QTableWidget()
        self.param_table.setAlternatingRowColors(True)
        content_splitter.addWidget(self.param_table)

        # Bottom: Console/Dashboard area
        self.console = QTextEdit()
        self.console.setMaximumHeight(200)
        self.console.setPlainText("Welcome to MessageIX Data Manager\n")
        content_splitter.addWidget(self.console)

        content_layout.addWidget(content_splitter)
        splitter.addWidget(content_widget)

        # Set splitter proportions
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

    def _setup_menu(self):
        """Set up the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Input File", self)
        open_action.triggered.connect(self._open_input_file)
        file_menu.addAction(open_action)

        open_results_action = QAction("Open Results File", self)
        open_results_action.triggered.connect(self._open_results_file)
        file_menu.addAction(open_results_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Run menu
        run_menu = menubar.addMenu("Run")

        solve_action = QAction("Run Solver", self)
        solve_action.triggered.connect(self._run_solver)
        solve_action.setShortcut("F5")
        run_menu.addAction(solve_action)

        stop_action = QAction("Stop Solver", self)
        stop_action.triggered.connect(self._stop_solver)
        stop_action.setShortcut("Ctrl+C")
        run_menu.addAction(stop_action)

        # View menu
        view_menu = menubar.addMenu("View")

        dashboard_action = QAction("Dashboard", self)
        dashboard_action.triggered.connect(self._show_dashboard)
        view_menu.addAction(dashboard_action)

    def _setup_status_bar(self):
        """Set up the status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _open_input_file(self):
        """Handle opening input Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Input Excel File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            try:
                self.console.append(f"Loading input file: {file_path}")

                # Load file with Input Manager
                scenario = self.input_manager.load_excel_file(file_path)

                # Log successful load
                logging_manager.log_input_load(file_path, True)

                # Update UI
                self.navigator.update_input_files([file_path])
                self.navigator.add_recent_file(file_path, "input")

                # Validate the loaded data
                validation = self.input_manager.validate_scenario()

                # Update parameter tree
                self._update_parameter_tree()

                # Report validation results
                if validation['valid']:
                    self.console.append(f"✓ Successfully loaded {len(scenario.parameters)} parameters, {len(scenario.sets)} sets")
                    self.console.append(f"  Total data points: {validation['summary']['total_data_points']}")
                else:
                    self.console.append(f"⚠ Loaded {len(scenario.parameters)} parameters with validation issues:")
                    for issue in validation['issues'][:5]:  # Show first 5 issues
                        self.console.append(f"  - {issue}")
                    if len(validation['issues']) > 5:
                        self.console.append(f"  ... and {len(validation['issues']) - 5} more issues")

                self.status_bar.showMessage(f"Loaded {os.path.basename(file_path)} ({'Valid' if validation['valid'] else 'Issues found'})")

            except Exception as e:
                error_msg = f"Error loading file: {str(e)}"
                self.console.append(error_msg)
                QMessageBox.critical(self, "Load Error", error_msg)

                # Log failed load
                logging_manager.log_input_load(file_path, False, error_msg)

    def _update_parameter_tree(self):
        """Update the parameter tree with loaded parameters"""
        self.param_tree.clear()

        scenario = self.input_manager.get_current_scenario()
        if not scenario:
            return

        # Group parameters by category with enhanced logic
        categories = {}

        for param_name in scenario.get_parameter_names():
            parameter = scenario.get_parameter(param_name)
            if not parameter:
                continue

            # Enhanced categorization based on parameter name and metadata
            category = self._categorize_parameter(param_name, parameter)

            if category not in categories:
                categories[category] = []
            categories[category].append((param_name, parameter))

        # Sort categories
        sorted_categories = sorted(categories.keys())

        # Create tree items
        for category in sorted_categories:
            params = categories[category]
            category_item = QTreeWidgetItem(self.param_tree)
            category_item.setText(0, f"{category} ({len(params)} parameters)")

            # Sort parameters within category
            params.sort(key=lambda x: x[0])

            for param_name, parameter in params:
                param_item = QTreeWidgetItem(category_item)
                param_item.setText(0, param_name)

                # Add metadata to tooltip
                dims_info = f"Dimensions: {', '.join(parameter.metadata.get('dims', []))}" if parameter.metadata.get('dims') else "No dimensions"
                shape_info = f"Shape: {parameter.metadata.get('shape', ('?', '?'))}"
                tooltip = f"Parameter: {param_name}\n{dims_info}\n{shape_info}"
                param_item.setToolTip(0, tooltip)

            category_item.setExpanded(True)

        # Add sets information if available
        if scenario.sets:
            sets_item = QTreeWidgetItem(self.param_tree)
            sets_item.setText(0, f"Sets ({len(scenario.sets)} sets)")

            for set_name, set_values in sorted(scenario.sets.items()):
                set_item = QTreeWidgetItem(sets_item)
                set_item.setText(0, f"{set_name} ({len(set_values)} elements)")
                set_item.setToolTip(0, f"Set: {set_name}\nElements: {len(set_values)}")

            sets_item.setExpanded(False)

    def _categorize_parameter(self, param_name: str, parameter) -> str:
        """Categorize a parameter based on its name and properties"""
        name_lower = param_name.lower()

        # Economic parameters
        if any(keyword in name_lower for keyword in ['cost', 'price', 'revenue', 'profit', 'subsidy']):
            return "Economic"

        # Capacity and investment
        elif any(keyword in name_lower for keyword in ['capacity', 'cap', 'investment', 'inv']):
            return "Capacity & Investment"

        # Demand and consumption
        elif any(keyword in name_lower for keyword in ['demand', 'load', 'consumption']):
            return "Demand & Consumption"

        # Technical parameters
        elif any(keyword in name_lower for keyword in ['efficiency', 'eff', 'factor', 'ratio']):
            return "Technical"

        # Environmental
        elif any(keyword in name_lower for keyword in ['emission', 'emiss', 'carbon', 'co2']):
            return "Environmental"

        # Temporal
        elif any(keyword in name_lower for keyword in ['duration', 'lifetime', 'year']):
            return "Temporal"

        # Operational
        elif any(keyword in name_lower for keyword in ['operation', 'oper', 'maintenance']):
            return "Operational"

        # Bounds and constraints
        elif any(keyword in name_lower for keyword in ['bound', 'limit', 'max', 'min']):
            return "Bounds & Constraints"

        # Default category
        else:
            return "Other"

    def _on_parameter_selected(self):
        """Handle parameter selection in tree view"""
        selected_items = self.param_tree.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]

        # Check if it's a parameter item (not a category)
        if selected_item.parent() is None:
            # It's a category, don't display data
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            return

        # Get parameter name
        param_name = selected_item.text(0)

        # Get parameter data
        parameter = self.input_manager.get_parameter(param_name)
        if parameter:
            self._display_parameter_data(parameter)

    def _display_parameter_data(self, parameter):
        """Display parameter data in the table view"""
        df = parameter.df

        if df.empty:
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            self.status_bar.showMessage(f"Parameter: {parameter.name} (empty)")
            return

        # Set table dimensions
        self.param_table.setRowCount(len(df))
        self.param_table.setColumnCount(len(df.columns))

        # Set headers with better formatting
        headers = []
        for col in df.columns:
            if col == parameter.metadata.get('value_column', 'value'):
                headers.append(f"{col} ({parameter.metadata.get('units', 'N/A')})")
            else:
                headers.append(str(col))
        self.param_table.setHorizontalHeaderLabels(headers)

        # Fill table data with better formatting
        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                value = df.iloc[row_idx, col_idx]
                item = QTableWidgetItem()

                # Handle different data types with proper formatting
                if pd.isna(value):
                    item.setText("")
                    item.setToolTip("No data")
                elif isinstance(value, float):
                    # Format floats with reasonable precision
                    if abs(value) < 0.01 or abs(value) > 1000000:
                        item.setText(f"{value:.6g}")
                    else:
                        item.setText(f"{value:.4f}")
                    item.setToolTip(f"Float: {value}")
                elif isinstance(value, int):
                    item.setText(str(value))
                    item.setToolTip(f"Integer: {value}")
                else:
                    str_value = str(value).strip()
                    item.setText(str_value)
                    item.setToolTip(f"Text: {str_value}")

                # Right-align numeric columns
                col_name = df.columns[col_idx]
                if col_name == parameter.metadata.get('value_column', 'value'):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.param_table.setItem(row_idx, col_idx, item)

        # Resize columns to content with reasonable limits
        self.param_table.resizeColumnsToContents()

        # Limit maximum column width for readability
        for col_idx in range(self.param_table.columnCount()):
            width = self.param_table.columnWidth(col_idx)
            if width > 200:  # Max width of 200 pixels
                self.param_table.setColumnWidth(col_idx, 200)

        # Update status with more detailed information
        dims_info = f", dims: {len(parameter.metadata.get('dims', []))}" if parameter.metadata.get('dims') else ""
        self.status_bar.showMessage(f"Parameter: {parameter.name} ({len(df)} rows{dims_info})")

        # Update console with parameter info
        self.console.append(f"Displayed parameter: {parameter.name}")
        self.console.append(f"  Shape: {df.shape}")
        if parameter.metadata.get('dims'):
            self.console.append(f"  Dimensions: {', '.join(parameter.metadata['dims'])}")
        if parameter.metadata.get('units') != 'N/A':
            self.console.append(f"  Units: {parameter.metadata['units']}")

    def _append_to_console(self, message: str):
        """Append message to console from solver manager"""
        self.console.append(message)

    def _update_status_from_solver(self, status: str):
        """Update status bar from solver manager"""
        self.status_bar.showMessage(status)

    def _open_results_file(self):
        """Handle opening results Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Results Excel File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            try:
                self.console.append(f"Loading results file: {file_path}")

                # Load file with Results Analyzer
                results = self.results_analyzer.load_results_file(file_path)

                # Update UI
                self.navigator.update_result_files([file_path])
                self.navigator.add_recent_file(file_path, "results")

                # Show summary
                stats = self.results_analyzer.get_summary_stats()
                self.console.append(f"Loaded {stats['total_variables']} variables, "
                                  f"{stats['total_equations']} equations")
                self.console.append(f"Total data points: {stats['total_data_points']}")

                # Log successful results load
                logging_manager.log_results_load(file_path, True, stats)

                # Update dashboard with new results
                self.dashboard.update_results(True)

                self.status_bar.showMessage(f"Results loaded: {os.path.basename(file_path)}")

            except Exception as e:
                error_msg = f"Error loading results file: {str(e)}"
                self.console.append(error_msg)
                QMessageBox.critical(self, "Load Error", error_msg)

                # Log failed results load
                logging_manager.log_results_load(file_path, False, {'error': error_msg})

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

        input_path = self.input_manager.loaded_file_path
        if not input_path:
            QMessageBox.warning(self, "No Input File",
                              "Please load an input Excel file first.")
            return

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
            self.dashboard.update_results(bool(self.results_analyzer.current_results))
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()
        except Exception as e:
            self.console.append(f"Error showing dashboard: {str(e)}")
            QMessageBox.critical(self, "Dashboard Error",
                               f"Failed to open dashboard: {str(e)}")
