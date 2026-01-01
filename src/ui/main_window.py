"""
Main application window for Message Viewer
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
    QStatusBar, QMenuBar, QMenu, QAction, QFileDialog, QMessageBox, QTreeWidgetItem
)
from PyQt5.QtCore import Qt

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
        self.setWindowTitle("Message Viewer - message_ix Data Manager")
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
        self.console.setPlainText("Welcome to Message Viewer\n")
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

                # Update parameter tree
                self._update_parameter_tree()

                self.console.append(f"Successfully loaded {len(scenario.parameters)} parameters")
                self.status_bar.showMessage(f"Loaded {os.path.basename(file_path)}")

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

        # Group parameters by category (simplified - would be more sophisticated)
        categories = {}

        for param_name in scenario.get_parameter_names():
            # Simple categorization based on parameter name
            if param_name.startswith(('cost', 'price', 'price')):
                category = "Costs"
            elif param_name.startswith(('demand', 'load')):
                category = "Demands"
            elif param_name.startswith(('capacity', 'cap')):
                category = "Capacities"
            elif param_name.startswith(('efficiency', 'eff')):
                category = "Efficiencies"
            else:
                category = "Other"

            if category not in categories:
                categories[category] = []
            categories[category].append(param_name)

        # Create tree items
        for category, params in categories.items():
            category_item = QTreeWidgetItem(self.param_tree)
            category_item.setText(0, f"{category} ({len(params)} parameters)")

            for param_name in params:
                param_item = QTreeWidgetItem(category_item)
                param_item.setText(0, param_name)
                param_item.setToolTip(0, f"Parameter: {param_name}")

            category_item.setExpanded(True)

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
            return

        # Set table dimensions
        self.param_table.setRowCount(len(df))
        self.param_table.setColumnCount(len(df.columns))

        # Set headers
        self.param_table.setHorizontalHeaderLabels(df.columns.tolist())

        # Fill table data
        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                value = df.iloc[row_idx, col_idx]
                # Handle different data types
                if pd.isna(value):
                    display_value = ""
                elif isinstance(value, (int, float)):
                    display_value = str(value)
                else:
                    display_value = str(value)

                self.param_table.setItem(row_idx, col_idx,
                                       QTableWidgetItem(display_value))

        # Resize columns to content
        self.param_table.resizeColumnsToContents()

        # Update status
        self.status_bar.showMessage(f"Parameter: {parameter.name} ({len(df)} rows)")

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
