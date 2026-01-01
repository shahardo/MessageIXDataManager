"""
Main application window for MessageIX Data Manager
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QStatusBar, QMenuBar, QMenu, QAction, QFileDialog, QMessageBox, QTreeWidgetItem, QLabel, QProgressBar,
    QPushButton, QComboBox, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QFont
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

        # View state
        self.current_view = "input"  # "input" or "results"
        self.table_display_mode = "raw"  # "raw" or "advanced"

        # Connect solver manager to console
        self.solver_manager.set_output_callback(self._append_to_console)
        self.solver_manager.set_status_callback(self._update_status_from_solver)

        # Initialize components
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()

        # Auto-load last opened files
        self._auto_load_last_files()

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
        self.navigator.file_selected.connect(self._on_file_selected)
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

        # Parameter table with title and controls
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Title and toggle button in horizontal layout
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        self.param_title = QLabel("Select a parameter to view data")
        self.param_title.setStyleSheet("font-size: 12px; color: #333; padding: 5px; background-color: #f0f0f0;")
        title_layout.addWidget(self.param_title)
        title_layout.addStretch()

        # Toggle button for raw/advanced view
        self.view_toggle_button = QPushButton("Raw Display")
        self.view_toggle_button.setCheckable(True)
        self.view_toggle_button.setChecked(False)  # Start with raw mode
        self.view_toggle_button.clicked.connect(self._toggle_display_mode)
        self.view_toggle_button.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                padding: 3px 8px;
                background-color: #e0e0e0;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
        """)
        title_layout.addWidget(self.view_toggle_button)

        table_layout.addLayout(title_layout)

        # Selector container for advanced mode (initially hidden)
        self.selector_container = QGroupBox("Data Filters")
        self.selector_container.setVisible(False)
        self.selector_container.setStyleSheet("""
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
                padding-top: 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        selector_layout = QHBoxLayout(self.selector_container)
        selector_layout.setContentsMargins(10, 10, 10, 10)

        # Property selectors (will be populated dynamically)
        self.property_selectors = {}
        selector_layout.addStretch()

        table_layout.addWidget(self.selector_container)

        self.param_table = QTableWidget()
        self.param_table.setAlternatingRowColors(True)
        # Reduce row height for more compact display
        self.param_table.verticalHeader().setDefaultSectionSize(22)
        # Style the header to make it more distinct
        header = self.param_table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 4px;
                border: 1px solid #ccc;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        table_layout.addWidget(self.param_table)

        content_splitter.addWidget(table_container)

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
        """Set up the status bar with progress bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Add progress bar to status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setMinimumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

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

    def _save_last_opened_files(self, file_path, file_type):
        """Save the last opened file path to settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        if file_type == "input":
            settings.setValue("last_input_file", file_path)
        elif file_type == "results":
            settings.setValue("last_results_file", file_path)

    def _get_last_opened_files(self):
        """Get the last opened file paths from settings"""
        settings = QSettings("MessageIXDataManager", "MainWindow")
        input_file = settings.value("last_input_file", "")
        results_file = settings.value("last_results_file", "")
        return input_file, results_file

    def _auto_load_last_files(self):
        """Automatically load the last opened files on startup"""
        input_file, results_file = self._get_last_opened_files()

        # Load input file if it exists and is readable
        if input_file and os.path.exists(input_file):
            try:
                self.console.append(f"Auto-loading last input file: {input_file}")

                # Show progress bar for auto-loading
                self.show_progress_bar(100)

                # Define progress callback
                def progress_callback(value, message):
                    self.update_progress(value, message)

                scenario = self.input_manager.load_excel_file(input_file, progress_callback)

                # Hide progress bar
                self.hide_progress_bar()

                # Update UI
                self.navigator.update_input_files([input_file])
                self.navigator.add_recent_file(input_file, "input")

                # Update parameter tree
                self._update_parameter_tree()

                self.console.append(f"✓ Auto-loaded input file with {len(scenario.parameters)} parameters")

            except Exception as e:
                # Hide progress bar on error
                self.hide_progress_bar()
                self.console.append(f"Failed to auto-load input file: {str(e)}")

        # Load results file if it exists and is readable
        if results_file and os.path.exists(results_file):
            try:
                self.console.append(f"Auto-loading last results file: {results_file}")

                # Show progress bar for auto-loading results
                self.show_progress_bar(100)

                # Define progress callback
                def progress_callback(value, message):
                    self.update_progress(value, message)

                results = self.results_analyzer.load_results_file(results_file, progress_callback)

                # Hide progress bar
                self.hide_progress_bar()

                # Update UI
                self.navigator.update_result_files([results_file])
                self.navigator.add_recent_file(results_file, "results")

                # Update dashboard
                self.dashboard.update_results(True)

                stats = self.results_analyzer.get_summary_stats()
                self.console.append(f"✓ Auto-loaded results file with {stats['total_variables']} variables")

            except Exception as e:
                # Hide progress bar on error
                self.hide_progress_bar()
                self.console.append(f"Failed to auto-load results file: {str(e)}")

    def _open_input_file(self):
        """Handle opening input Excel file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Input Excel File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            try:
                self.console.append(f"Loading input file: {file_path}")

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

                # Save this file as the last opened input file
                self._save_last_opened_files(file_path, "input")

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
                # Hide progress bar on error
                self.hide_progress_bar()

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

    def _update_results_tree(self):
        """Update the parameter tree with loaded results"""
        self.param_tree.clear()

        results = self.results_analyzer.get_current_results()
        if not results:
            return

        # Group results by type
        categories = {}

        for result_name in results.get_parameter_names():
            result = results.get_parameter(result_name)
            if not result:
                continue

            # Categorize by result type
            result_type = result.metadata.get('result_type', 'result')
            if result_type == 'variable':
                category = "Variables"
            elif result_type == 'equation':
                category = "Equations"
            else:
                category = "Results"

            if category not in categories:
                categories[category] = []
            categories[category].append((result_name, result))

        # Sort categories
        sorted_categories = sorted(categories.keys())

        # Create tree items
        for category in sorted_categories:
            results_list = categories[category]
            category_item = QTreeWidgetItem(self.param_tree)
            category_item.setText(0, f"{category} ({len(results_list)} results)")

            # Sort results within category
            results_list.sort(key=lambda x: x[0])

            for result_name, result in results_list:
                result_item = QTreeWidgetItem(category_item)
                result_item.setText(0, result_name)

                # Add metadata to tooltip
                dims_info = f"Dimensions: {', '.join(result.metadata.get('dims', []))}" if result.metadata.get('dims') else "No dimensions"
                shape_info = f"Shape: {result.metadata.get('shape', ('?', '?'))}"
                units_info = f"Units: {result.metadata.get('units', 'N/A')}"
                tooltip = f"Result: {result_name}\n{dims_info}\n{shape_info}\n{units_info}"
                result_item.setToolTip(0, tooltip)

            category_item.setExpanded(True)

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
        """Handle parameter/result selection in tree view"""
        selected_items = self.param_tree.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]

        # Check if it's a parameter/result item (not a category)
        if selected_item.parent() is None:
            # It's a category, don't display data
            if self.current_view == "input":
                self.param_title.setText("Select a parameter to view data")
            else:
                self.param_title.setText("Select a result to view data")
            self.param_title.setStyleSheet("font-size: 12px; color: #333; padding: 5px; background-color: #f0f0f0;")
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            return

        # Get parameter/result name
        item_name = selected_item.text(0)

        # Get data based on current view
        if self.current_view == "input":
            data = self.input_manager.get_parameter(item_name)
            if data:
                self._display_parameter_data(data)
                # Reset table view to top when switching parameters
                self.param_table.scrollToTop()
        else:  # results view
            data = self.results_analyzer.get_result_data(item_name)
            if data:
                self._display_result_data(data)
                # Reset table view to top when switching parameters
                self.param_table.scrollToTop()

    def _display_parameter_data(self, parameter):
        """Display parameter data in the table view"""
        df = parameter.df

        # Update the table title
        self.param_title.setText(f"Parameter: {parameter.name}")
        self.param_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; padding: 5px; background-color: #f0f0f0;")

        if df.empty:
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            self.status_bar.showMessage(f"Parameter: {parameter.name} (empty)")
            return

        # Handle display mode
        if self.table_display_mode == "advanced":
            # Get current filter selections
            current_filters = {}
            for col, selector in self.property_selectors.items():
                selected_value = selector.currentText()
                if selected_value != "All":
                    current_filters[col] = selected_value

            # Transform data for advanced view
            display_df = self._transform_to_advanced_view(df, current_filters)

            # Set up selectors if not already done
            if not self.property_selectors:
                self._setup_property_selectors(df)
        else:
            # Raw mode - use original data
            display_df = df

        # Set table dimensions
        self.param_table.setRowCount(len(display_df))

        # In advanced mode, set vertical headers to show years
        if self.table_display_mode == "advanced":
            self.param_table.setColumnCount(len(display_df.columns))
            # Set vertical header labels to show years
            year_labels = [str(year) for year in display_df.index]
            self.param_table.setVerticalHeaderLabels(year_labels)
        else:
            self.param_table.setColumnCount(len(display_df.columns))
            # Reset vertical headers to default
            self.param_table.setVerticalHeaderLabels([])

        # Determine formatting for numerical columns based on max values
        column_formats = {}
        for col_idx, col_name in enumerate(display_df.columns):
            col_dtype = display_df.dtypes[col_name]
            # Handle case where duplicate column names return a Series
            if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                # Multiple columns with same name, check if any are numeric
                is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
            else:
                # Single column
                is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

            if is_numeric:
                # Find max absolute value in the column (excluding NaN)
                numeric_values = display_df[col_name].dropna()
                if not numeric_values.empty:
                    max_abs_value = abs(numeric_values).max()
                    # Handle case where max_abs_value is a Series (duplicate columns)
                    if hasattr(max_abs_value, 'max'):
                        max_abs_value = max_abs_value.max()
                    if max_abs_value < 10:
                        column_formats[col_idx] = ".2f"  # #.##
                    elif max_abs_value < 100:
                        column_formats[col_idx] = ".1f"  # #.#
                    else:
                        column_formats[col_idx] = ",.0f"  # #,##0

        # Set headers with better formatting
        headers = []
        for col in display_df.columns:
            if self.table_display_mode == "raw" and col == parameter.metadata.get('value_column', 'value'):
                headers.append(f"{col} ({parameter.metadata.get('units', 'N/A')})")
            else:
                headers.append(str(col))
        self.param_table.setHorizontalHeaderLabels(headers)

        # Fill table data with better formatting
        for row_idx in range(len(display_df)):
            for col_idx in range(len(display_df.columns)):
                value = display_df.iloc[row_idx, col_idx]
                item = QTableWidgetItem()

                # Handle different data types with proper formatting
                if pd.isna(value):
                    item.setText("")
                    item.setToolTip("No data")
                elif isinstance(value, float):
                    # Use column-specific formatting for numerical columns
                    if col_idx in column_formats:
                        format_str = column_formats[col_idx]
                        item.setText(f"{value:{format_str}}")
                    else:
                        # Fallback formatting for columns without specific format
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
                col_name = display_df.columns[col_idx]
                col_dtype = display_df.dtypes[col_name]
                # Handle case where duplicate column names return a Series
                if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                    # Multiple columns with same name, check if any are numeric
                    is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
                else:
                    # Single column
                    is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

                if is_numeric or (self.table_display_mode == "raw" and col_name == parameter.metadata.get('value_column', 'value')):
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
        display_mode_info = f" ({self.table_display_mode} view)"
        self.status_bar.showMessage(f"Parameter: {parameter.name} ({len(display_df)} rows{dims_info}){display_mode_info}")

        # Update console with parameter info
        self.console.append(f"Displayed parameter: {parameter.name} ({self.table_display_mode} view)")
        self.console.append(f"  Shape: {display_df.shape}")
        if parameter.metadata.get('dims'):
            self.console.append(f"  Dimensions: {', '.join(parameter.metadata['dims'])}")
        if self.table_display_mode == "raw" and parameter.metadata.get('units') != 'N/A':
            self.console.append(f"  Units: {parameter.metadata['units']}")

    def _display_result_data(self, result):
        """Display result data in the table view"""
        df = result.df

        # Update the table title
        self.param_title.setText(f"Result: {result.name}")
        self.param_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; padding: 5px; background-color: #f0f0f0;")

        if df.empty:
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            self.status_bar.showMessage(f"Result: {result.name} (empty)")
            return

        # Handle display mode
        if self.table_display_mode == "advanced":
            # Get current filter selections
            current_filters = {}
            for col, selector in self.property_selectors.items():
                selected_value = selector.currentText()
                if selected_value != "All":
                    current_filters[col] = selected_value

            # Transform data for advanced view
            display_df = self._transform_to_advanced_view(df, current_filters)

            # Set up selectors if not already done
            if not self.property_selectors:
                self._setup_property_selectors(df)
        else:
            # Raw mode - use original data
            display_df = df

        # Set table dimensions
        self.param_table.setRowCount(len(display_df))

        # In advanced mode, set vertical headers to show years
        if self.table_display_mode == "advanced":
            self.param_table.setColumnCount(len(display_df.columns))
            # Set vertical header labels to show years
            year_labels = [str(year) for year in display_df.index]
            self.param_table.setVerticalHeaderLabels(year_labels)
        else:
            self.param_table.setColumnCount(len(display_df.columns))
            # Reset vertical headers to default
            self.param_table.setVerticalHeaderLabels([])

        # Determine formatting for numerical columns based on max values
        column_formats = {}
        for col_idx, col_name in enumerate(display_df.columns):
            col_dtype = display_df.dtypes[col_name]
            # Handle case where duplicate column names return a Series
            if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                # Multiple columns with same name, check if any are numeric
                is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
            else:
                # Single column
                is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

            if is_numeric:
                # Find max absolute value in the column (excluding NaN)
                numeric_values = display_df[col_name].dropna()
                if not numeric_values.empty:
                    max_abs_value = abs(numeric_values).max()
                    # Handle case where max_abs_value is a Series (duplicate columns)
                    if hasattr(max_abs_value, 'max'):
                        max_abs_value = max_abs_value.max()
                    if max_abs_value < 10:
                        column_formats[col_idx] = ".2f"  # #.##
                    elif max_abs_value < 100:
                        column_formats[col_idx] = ".1f"  # #.#
                    else:
                        column_formats[col_idx] = ",.0f"  # #,##0

        # Set headers with better formatting
        headers = []
        for col in display_df.columns:
            if self.table_display_mode == "raw" and col == result.metadata.get('value_column', 'value'):
                headers.append(f"{col} ({result.metadata.get('units', 'N/A')})")
            else:
                headers.append(str(col))
        self.param_table.setHorizontalHeaderLabels(headers)

        # Fill table data with better formatting
        for row_idx in range(len(display_df)):
            for col_idx in range(len(display_df.columns)):
                value = display_df.iloc[row_idx, col_idx]
                item = QTableWidgetItem()

                # Handle different data types with proper formatting
                if pd.isna(value):
                    item.setText("")
                    item.setToolTip("No data")
                elif isinstance(value, float):
                    # Use column-specific formatting for numerical columns
                    if col_idx in column_formats:
                        format_str = column_formats[col_idx]
                        item.setText(f"{value:{format_str}}")
                    else:
                        # Fallback formatting for columns without specific format
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
                col_name = display_df.columns[col_idx]
                col_dtype = display_df.dtypes[col_name]
                # Handle case where duplicate column names return a Series
                if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                    # Multiple columns with same name, check if any are numeric
                    is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
                else:
                    # Single column
                    is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

                if is_numeric or (self.table_display_mode == "raw" and col_name == result.metadata.get('value_column', 'value')):
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
        dims_info = f", dims: {len(result.metadata.get('dims', []))}" if result.metadata.get('dims') else ""
        display_mode_info = f" ({self.table_display_mode} view)"
        self.status_bar.showMessage(f"Result: {result.name} ({len(display_df)} rows{dims_info}){display_mode_info}")

        # Update console with result info
        self.console.append(f"Displayed result: {result.name} ({self.table_display_mode} view)")
        self.console.append(f"  Shape: {display_df.shape}")
        if result.metadata.get('dims'):
            self.console.append(f"  Dimensions: {', '.join(result.metadata['dims'])}")
        if self.table_display_mode == "raw" and result.metadata.get('units') != 'N/A':
            self.console.append(f"  Units: {result.metadata['units']}")

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

                # Show progress bar
                self.show_progress_bar(100)

                # Define progress callback
                def progress_callback(value, message):
                    self.update_progress(value, message)

                # Load file with Results Analyzer
                results = self.results_analyzer.load_results_file(file_path, progress_callback)

                # Hide progress bar
                self.hide_progress_bar()

                # Save this file as the last opened results file
                self._save_last_opened_files(file_path, "results")

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
                # Hide progress bar on error
                self.hide_progress_bar()

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

    def _toggle_display_mode(self):
        """Toggle between raw and advanced display modes"""
        if self.view_toggle_button.isChecked():
            self.table_display_mode = "advanced"
            self.view_toggle_button.setText("Advanced Display")
            self.selector_container.setVisible(True)
        else:
            self.table_display_mode = "raw"
            self.view_toggle_button.setText("Raw Display")
            self.selector_container.setVisible(False)

        # Refresh the current parameter display if one is selected
        if self.current_view == "input":
            selected_items = self.param_tree.selectedItems()
            if selected_items and selected_items[0].parent() is not None:
                item_name = selected_items[0].text(0)
                data = self.input_manager.get_parameter(item_name)
                if data:
                    self._display_parameter_data(data)
        else:  # results view
            selected_items = self.param_tree.selectedItems()
            if selected_items and selected_items[0].parent() is not None:
                item_name = selected_items[0].text(0)
                data = self.results_analyzer.get_result_data(item_name)
                if data:
                    self._display_result_data(data)

    def _transform_to_advanced_view(self, df: pd.DataFrame, current_filters: dict = None) -> pd.DataFrame:
        """
        Transform parameter data into 2D advanced view format.

        Args:
            df: Original parameter DataFrame
            current_filters: Dictionary of current filter selections

        Returns:
            Transformed DataFrame with years as rows and properties as columns
        """
        if df.empty:
            return df

        # Default filters if none provided
        if current_filters is None:
            current_filters = {}

        # Identify year columns and property columns
        year_columns = []
        property_columns = []
        filter_columns = []
        value_column = None

        # Categorize columns
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['value', 'val']:
                value_column = col
            elif col_lower in ['year_vtg', 'year_act', 'year_rel', 'year']:
                year_columns.append(col)
            elif col_lower in ['node_loc', 'node_rel', 'node_dest', 'node_origin', 'region',
                             'mode', 'level', 'grade']:
                # These become filter selectors (popup menus)
                filter_columns.append(col)
            elif col_lower in ['commodity', 'technology', 'type']:
                # These become columns in advanced view
                property_columns.append(col)
            # Ignore units columns and other non-relevant columns

        # If no value column found, assume last column is value
        if value_column is None and len(df.columns) > 0:
            value_column = df.columns[-1]

        # Apply filters
        filtered_df = df.copy()
        for filter_col, filter_value in current_filters.items():
            if filter_value and filter_value != "All" and filter_col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[filter_col] == filter_value]

        # Create pivot table
        if not year_columns:
            # If no year columns, use index as rows
            pivot_df = filtered_df.copy()
        else:
            # Determine index columns (years)
            index_cols = year_columns.copy()

            # If both year_vtg and year_act exist, create combined year column
            if 'year_vtg' in year_columns and 'year_act' in year_columns:
                # Create a combined year identifier
                filtered_df['year_combined'] = filtered_df.apply(
                    lambda row: f"{row['year_vtg']}_{row['year_act']}", axis=1
                )
                index_cols = ['year_combined']

            # Determine columns for pivoting (exclude filter columns and year columns)
            pivot_cols = [col for col in property_columns if col in filtered_df.columns and col not in filter_columns and col not in year_columns]

            # If no property columns, use a default grouping
            if not pivot_cols:
                pivot_cols = ['index']
                filtered_df['index'] = range(len(filtered_df))

            # Create pivot table
            try:
                import numpy as np
                pivot_df = filtered_df.pivot_table(
                    values=value_column,
                    index=index_cols,
                    columns=pivot_cols,
                    aggfunc='first',  # Take first value if duplicates
                    fill_value=np.nan  # Use NaN for missing values to avoid downcasting warning
                )

                # Flatten MultiIndex columns if they exist
                if isinstance(pivot_df.columns, pd.MultiIndex):
                    # Create clean column names by joining the levels, excluding units
                    new_columns = []
                    for col_tuple in pivot_df.columns:
                        # Filter out None/NaN values, empty strings, and units-like values
                        clean_parts = []
                        for part in col_tuple:
                            if pd.notna(part) and str(part).strip():
                                part_str = str(part).strip()
                                # Skip units-like values (common units)
                                if part_str.lower() not in ['gwa', 'gw', 'mw', 'kw', 'tj', 'pj', 'mt', 'kt', 'usd', 'eur', 'usd_2005', 'usd_2010']:
                                    clean_parts.append(part_str)
                        if clean_parts:
                            new_columns.append('_'.join(clean_parts))
                        else:
                            # If all parts were filtered out, use the first non-empty part
                            for part in col_tuple:
                                if pd.notna(part) and str(part).strip():
                                    new_columns.append(str(part).strip())
                                    break
                            else:
                                new_columns.append(str(col_tuple))
                    pivot_df.columns = new_columns

            except Exception as e:
                # Fallback: just return filtered data if pivot fails
                print(f"Pivot failed: {e}")
                pivot_df = filtered_df

            # Keep years as DataFrame index for advanced view

        return pivot_df

    def _setup_property_selectors(self, df: pd.DataFrame):
        """Set up property selectors for advanced view based on DataFrame columns"""
        # Clear existing selectors
        for selector in self.property_selectors.values():
            selector.setParent(None)
        self.property_selectors.clear()

        # Identify filter columns
        filter_columns = []
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['node_loc', 'node_rel', 'node_dest', 'node_origin', 'region',
                           'mode', 'level', 'grade']:
                filter_columns.append(col)

        # Create selectors for filter columns
        selector_layout = self.selector_container.layout()
        if selector_layout:
            # Remove the stretch item if it exists
            while selector_layout.count() > 0:
                item = selector_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        for col in filter_columns:
            # Create label
            label = QLabel(f"{col}:")
            label.setStyleSheet("font-size: 11px; font-weight: bold;")
            selector_layout.addWidget(label)

            # Create combo box
            combo = QComboBox()
            combo.setStyleSheet("font-size: 11px; padding: 2px;")

            # Add "All" option and unique values
            unique_values = sorted(df[col].dropna().unique().tolist())
            combo.addItem("All")
            for value in unique_values:
                combo.addItem(str(value))

            # Set default to "All"
            combo.setCurrentText("All")

            # Connect signal
            combo.currentTextChanged.connect(self._on_selector_changed)

            selector_layout.addWidget(combo)
            self.property_selectors[col] = combo

        # Add stretch at the end
        selector_layout.addStretch()

    def _on_selector_changed(self):
        """Handle selector value changes - refresh the table display"""
        # Refresh the current parameter display
        if self.current_view == "input":
            selected_items = self.param_tree.selectedItems()
            if selected_items and selected_items[0].parent() is not None:
                item_name = selected_items[0].text(0)
                data = self.input_manager.get_parameter(item_name)
                if data:
                    self._display_parameter_data(data)
        else:  # results view
            selected_items = self.param_tree.selectedItems()
            if selected_items and selected_items[0].parent() is not None:
                item_name = selected_items[0].text(0)
                data = self.results_analyzer.get_result_data(item_name)
                if data:
                    self._display_result_data(data)

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

    def _on_file_selected(self, file_path: str, file_type: str):
        """Handle file selection in navigator"""
        if file_type == "input":
            self._switch_to_input_view()
        elif file_type == "results":
            self._switch_to_results_view()

    def _switch_to_input_view(self):
        """Switch to input parameters view"""
        if self.current_view != "input":
            self.current_view = "input"
            self._update_parameter_tree()
            self.param_tree.setHeaderLabel("Parameters")
            self.param_title.setText("Select a parameter to view data")
            self.param_title.setStyleSheet("font-size: 12px; color: #333; padding: 5px; background-color: #f0f0f0;")
            # Clear the table and reset selectors
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            # Reset display mode and hide selectors
            self.table_display_mode = "raw"
            self.view_toggle_button.setChecked(False)
            self.view_toggle_button.setText("Raw Display")
            self.selector_container.setVisible(False)
            # Clear existing selectors
            for selector in self.property_selectors.values():
                selector.setParent(None)
            self.property_selectors.clear()

    def _switch_to_results_view(self):
        """Switch to results view"""
        if self.current_view != "results":
            self.current_view = "results"
            self._update_results_tree()
            self.param_tree.setHeaderLabel("Results")
            self.param_title.setText("Select a result to view data")
            self.param_title.setStyleSheet("font-size: 12px; color: #333; padding: 5px; background-color: #f0f0f0;")
            # Clear the table and reset selectors
            self.param_table.setRowCount(0)
            self.param_table.setColumnCount(0)
            # Reset display mode and hide selectors
            self.table_display_mode = "raw"
            self.view_toggle_button.setChecked(False)
            self.view_toggle_button.setText("Raw Display")
            self.selector_container.setVisible(False)
            # Clear existing selectors
            for selector in self.property_selectors.values():
                selector.setParent(None)
            self.property_selectors.clear()
