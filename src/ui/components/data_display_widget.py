"""
Data Display Widget - Handles data table display, raw/advanced views, and formatting

Extracted from MainWindow to provide focused data display functionality.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QComboBox, QGroupBox, QCheckBox, QFrame
)
from PyQt5.QtCore import Qt
import pandas as pd
from typing import Optional, Dict, List

from core.data_models import Parameter


class DataDisplayWidget(QWidget):
    """Handles data table display, raw/advanced views, and formatting"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table_display_mode = "raw"  # "raw" or "advanced"
        self.hide_empty_columns = False  # Whether to hide empty columns in advanced view
        self.property_selectors = {}
        self.hide_empty_checkbox = None

        self.setup_ui()

    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)

        # Title label
        self.param_title = QLabel("Select a parameter to view data")
        self.param_title.setStyleSheet("font-size: 12px; color: #333; padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.param_title)

        # View toggle button
        self.view_toggle_button = QPushButton("Raw Display")
        self.view_toggle_button.setCheckable(True)
        self.view_toggle_button.setChecked(False)
        self.view_toggle_button.setCursor(Qt.PointingHandCursor)
        self.view_toggle_button.setEnabled(False)
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
        self.view_toggle_button.clicked.connect(self._toggle_display_mode)
        layout.addWidget(self.view_toggle_button)

        # Selector container for filters
        self.selector_container = QFrame()
        self.selector_container.setFrameStyle(QFrame.StyledPanel)
        self.selector_container.setVisible(False)
        self.selector_container.setStyleSheet("""
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                margin-top: 0px;
                margin-left: 10px;
                padding-top: 5px;
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
        selector_layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.selector_container)

        # Data table
        self.param_table = QTableWidget()
        self.param_table.setAlternatingRowColors(True)
        self.param_table.verticalHeader().setDefaultSectionSize(22)
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
        layout.addWidget(self.param_table)

        self.setLayout(layout)

    def display_parameter_data(self, parameter: Parameter, is_results: bool = False):
        """Display parameter/result data in the table view"""
        self.display_data_table(parameter, "Result" if is_results else "Parameter", is_results)

    def display_data_table(self, data: Parameter, title_prefix: str, is_results: bool = False):
        """
        Unified method for displaying parameter/result data in table and chart views.

        Args:
            data: Parameter object to display
            title_prefix: "Parameter" or "Result" for titles
            is_results: Whether this is results data (affects some logic)
        """
        df = data.df

        # Update title
        self.param_title.setText(f"{title_prefix}: {data.name}")
        self.param_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; padding: 5px; background-color: #f0f0f0;")

        if df.empty:
            self._clear_table_display()
            return

        # Handle view mode (raw vs advanced)
        if self.table_display_mode == "advanced":
            current_filters = self._get_current_filters()
            display_df = self._transform_to_advanced_view(df, current_filters, is_results)
            self._setup_property_selectors(df)
        else:
            display_df = df

        # Set up table dimensions and headers
        self._configure_table(display_df, is_results)

        # Format and populate table data
        self._populate_table(display_df, data)

        # Enable controls and update status
        self._finalize_display(display_df, data, title_prefix, is_results)

    def _clear_table_display(self):
        """Clear the table display when no data is available"""
        self.param_table.setRowCount(0)
        self.param_table.setColumnCount(0)
        self.view_toggle_button.setEnabled(False)

    def _get_current_filters(self) -> Dict[str, str]:
        """Get current filter selections from property selectors"""
        current_filters = {}
        for col, selector in self.property_selectors.items():
            selected_value = selector.currentText()
            if selected_value != "All":
                current_filters[col] = selected_value
        return current_filters

    def _finalize_display(self, display_df: pd.DataFrame, data: Parameter, title_prefix: str, is_results: bool):
        """Finalize the display after populating table data"""
        # Enable the view toggle button since we have data
        self.view_toggle_button.setEnabled(True)

        # Resize columns to content with reasonable limits
        self.param_table.resizeColumnsToContents()
        for col_idx in range(self.param_table.columnCount()):
            width = self.param_table.columnWidth(col_idx)
            if width > 200:  # Max width of 200 pixels
                self.param_table.setColumnWidth(col_idx, 200)

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

        # Emit signal to refresh display (will be connected by parent)
        self.display_mode_changed.emit()

    def _configure_table(self, df: pd.DataFrame, is_results: bool):
        """Configure table dimensions and headers"""
        self.param_table.setRowCount(len(df))

        # Set column count and vertical headers based on display mode
        if self.table_display_mode == "advanced":
            self.param_table.setColumnCount(len(df.columns))
            # Set vertical header labels to show years
            year_labels = [str(year) for year in df.index]
            self.param_table.setVerticalHeaderLabels(year_labels)
        else:
            self.param_table.setColumnCount(len(df.columns))
            # Set vertical headers to show row numbers starting from 1
            row_labels = [str(i + 1) for i in range(len(df))]
            self.param_table.setVerticalHeaderLabels(row_labels)

        # Set headers with better formatting
        headers = []
        for col in df.columns:
            headers.append(str(col))
        self.param_table.setHorizontalHeaderLabels(headers)

    def _populate_table(self, df: pd.DataFrame, parameter: Parameter):
        """Fill table data with proper formatting"""
        # Determine formatting for numerical columns based on max values
        column_formats = {}
        for col_idx, col_name in enumerate(df.columns):
            col_dtype = df.dtypes[col_name]
            # Handle case where duplicate column names return a Series
            if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                # Multiple columns with same name, check if any are numeric
                is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
            else:
                # Single column
                is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

            if is_numeric:
                # Find max absolute value in the column (excluding NaN)
                numeric_values = df[col_name].dropna()
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

        # Fill table data
        for row_idx in range(len(df)):
            for col_idx in range(len(df.columns)):
                value = df.iloc[row_idx, col_idx]
                item = QTableWidgetItem()

                # Handle different data types with proper formatting
                if pd.isna(value) or (isinstance(value, (int, float)) and value == 0):
                    item.setText("")
                    item.setToolTip("No data" if pd.isna(value) else "Zero value")
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
                col_name = df.columns[col_idx]
                col_dtype = df.dtypes[col_name]
                # Handle case where duplicate column names return a Series
                if hasattr(col_dtype, '__iter__') and not isinstance(col_dtype, str):
                    # Multiple columns with same name, check if any are numeric
                    is_numeric = any(dtype in ['int64', 'float64', 'int32', 'float32'] for dtype in col_dtype)
                else:
                    # Single column
                    is_numeric = col_dtype in ['int64', 'float64', 'int32', 'float32']

                if is_numeric:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.param_table.setItem(row_idx, col_idx, item)

    def _setup_property_selectors(self, df: pd.DataFrame):
        """Set up property selectors for advanced view based on DataFrame columns"""
        # Save current selections before clearing
        current_selections = {}
        for col_name, selector in self.property_selectors.items():
            current_selections[col_name] = selector.currentText()

        # Clear existing selectors
        for selector in self.property_selectors.values():
            selector.setParent(None)
        self.property_selectors.clear()

        # Remove existing checkbox if it exists
        if self.hide_empty_checkbox:
            self.hide_empty_checkbox.setParent(None)
            self.hide_empty_checkbox = None

        # Identify filter columns
        filter_columns = []
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['node_loc', 'node_rel', 'node_dest', 'node_origin', 'region',
                           'mode', 'level', 'grade', 'node']:
                filter_columns.append(col)

        # Get selector layout
        selector_layout = self.selector_container.layout()

        # Add checkbox for hiding empty columns
        self.hide_empty_checkbox = QCheckBox("Hide Empty Columns")
        self.hide_empty_checkbox.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.hide_empty_checkbox.setChecked(self.hide_empty_columns)
        self.hide_empty_checkbox.stateChanged.connect(self._on_hide_empty_changed)
        selector_layout.addWidget(self.hide_empty_checkbox)

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

            # Restore previous selection if available
            if col in current_selections and current_selections[col] in [combo.itemText(i) for i in range(combo.count())]:
                combo.setCurrentText(current_selections[col])

            # Connect signal
            combo.currentTextChanged.connect(self._on_selector_changed)

            selector_layout.addWidget(combo)
            self.property_selectors[col] = combo

        # Add stretch at the end
        selector_layout.addStretch()

    def _on_selector_changed(self):
        """Handle selector value changes - refresh the table display"""
        # Emit signal to refresh display (will be connected by parent)
        self.display_mode_changed.emit()

    def _on_hide_empty_changed(self):
        """Handle hide empty columns checkbox state change"""
        self.hide_empty_columns = self.hide_empty_checkbox.isChecked()
        # Emit signal to refresh display (will be connected by parent)
        self.display_mode_changed.emit()

    def _transform_to_advanced_view(self, df: pd.DataFrame, current_filters: dict = None, is_results: bool = False) -> pd.DataFrame:
        """
        Transform parameter data into 2D advanced view format.

        This is a simplified version - the full implementation will be moved from MainWindow.
        """
        if df.empty:
            return df

        # Apply filters
        filtered_df = df.copy()
        for filter_col, filter_value in current_filters.items():
            if filter_value and filter_value != "All" and filter_col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[filter_col] == filter_value]

        # For now, return filtered data - full pivot logic will be moved later
        return filtered_df

    # Signals (will be implemented when PyQt signals are added)
    display_mode_changed = None  # Placeholder for signal
