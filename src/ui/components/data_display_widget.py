"""
Data Display Widget - Handles data table display, raw/advanced views, and formatting

Extracted from MainWindow to provide focused data display functionality.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QComboBox, QGroupBox, QCheckBox, QHeaderView,
    QMenu, QAction, QApplication, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QKeySequence
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Union, Any, TYPE_CHECKING
import datetime
import copy

if TYPE_CHECKING:
    pass  # No additional imports needed since we assume UI widgets exist

from core.data_models import Parameter
from ..ui_styler import UIStyler
from managers.commands import Command


class UndoManager:
    """Manages undo/redo operations for data modifications using command objects"""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.undo_stack: List['Command'] = []
        self.redo_stack: List['Command'] = []

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return len(self.redo_stack) > 0

    def execute(self, command: 'Command') -> bool:
        """
        Execute a command and add it to the undo stack if successful

        Args:
            command: Command object to execute

        Returns:
            True if command executed successfully
        """
        try:
            success = command.do()
            if success:
                # Add to undo stack
                self.undo_stack.append(command)

                # Clear redo stack when new operation is performed
                self.redo_stack.clear()

                # Limit stack size
                if len(self.undo_stack) > self.max_history:
                    self.undo_stack.pop(0)

            return success
        except Exception as e:
            print(f"Error executing command: {e}")
            return False

    def undo(self) -> bool:
        """
        Undo the last operation

        Returns:
            True if undo was performed successfully
        """
        if not self.can_undo():
            return False

        # Get the last command
        command = self.undo_stack.pop()

        try:
            # Undo the command
            success = command.undo()
            if success:
                # Add to redo stack
                self.redo_stack.append(command)
            else:
                # Put command back on undo stack if undo failed
                self.undo_stack.append(command)
            return success
        except Exception as e:
            print(f"Error undoing command: {e}")
            # Put command back on undo stack
            self.undo_stack.append(command)
            return False

    def redo(self) -> bool:
        """
        Redo the last undone operation

        Returns:
            True if redo was performed successfully
        """
        if not self.can_redo():
            return False

        # Get the last undone command
        command = self.redo_stack.pop()

        try:
            # Redo the command
            success = command.do()
            if success:
                # Add back to undo stack
                self.undo_stack.append(command)
            else:
                # Put command back on redo stack if redo failed
                self.redo_stack.append(command)
            return success
        except Exception as e:
            print(f"Error redoing command: {e}")
            # Put command back on redo stack
            self.redo_stack.append(command)
            return False

    def clear_history(self):
        """Clear all undo/redo history"""
        self.undo_stack.clear()
        self.redo_stack.clear()

    def get_undo_description(self) -> str:
        """Get description of the operation that can be undone"""
        if self.can_undo():
            return self.undo_stack[-1].description
        return ""

    def get_redo_description(self) -> str:
        """Get description of the operation that can be redone"""
        if self.can_redo():
            return self.redo_stack[-1].description
        return ""


class ColumnHeaderView(QHeaderView):
    """Custom header view that supports right-click context menu for column operations"""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.data_display_widget = None  # Will be set by parent

    def mousePressEvent(self, event):
        """Handle mouse press to select the entire column"""
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            # Get the column index
            column = self.logicalIndexAt(event.pos())
            if column >= 0:
                # Select the entire column
                table = self.parent()
                if table and hasattr(table, 'selectColumn'):
                    table.selectColumn(column)
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        """Show context menu for column header"""
        # Get the column index from the position
        column = self.logicalIndexAt(pos)
        if column < 0:
            return

        # Create the context menu
        menu = QMenu(self)

        # Cut action
        cut_action = QAction("&Cut", self)
        cut_action.setStatusTip("Cut column data to clipboard")
        cut_action.triggered.connect(lambda: self._cut_column(column))
        menu.addAction(cut_action)

        # Copy action
        copy_action = QAction("C&opy", self)
        copy_action.setStatusTip("Copy column data to clipboard")
        copy_action.triggered.connect(lambda: self._copy_column(column))
        menu.addAction(copy_action)

        # Paste action
        paste_action = QAction("&Paste", self)
        paste_action.setStatusTip("Paste data from clipboard to column")
        paste_action.triggered.connect(lambda: self._paste_column(column))
        menu.addAction(paste_action)

        menu.addSeparator()

        # Insert column action
        insert_action = QAction("&Insert Column", self)
        insert_action.setStatusTip("Insert a new column")
        insert_action.triggered.connect(lambda: self._insert_column(column))
        menu.addAction(insert_action)

        # Delete column action
        delete_action = QAction("&Delete Column", self)
        delete_action.setStatusTip("Delete this column")
        delete_action.triggered.connect(lambda: self._delete_column(column))
        menu.addAction(delete_action)

        menu.addSeparator()

        # Delimiter submenu
        delimiter_menu = menu.addMenu("&Delimiter")
        delimiter_menu.setStatusTip("Set delimiter for clipboard operations")

        # Tab delimiter
        tab_action = QAction("&Tab", self)
        tab_action.setCheckable(True)
        tab_action.setChecked(True)  # Default
        tab_action.triggered.connect(lambda: self._set_delimiter('\t'))
        delimiter_menu.addAction(tab_action)

        # Comma delimiter
        comma_action = QAction("&Comma", self)
        comma_action.setCheckable(True)
        comma_action.triggered.connect(lambda: self._set_delimiter(','))
        delimiter_menu.addAction(comma_action)

        # Semicolon delimiter
        semicolon_action = QAction("&Semicolon", self)
        semicolon_action.setCheckable(True)
        semicolon_action.triggered.connect(lambda: self._set_delimiter(';'))
        delimiter_menu.addAction(semicolon_action)

        # Space delimiter
        space_action = QAction("&Space", self)
        space_action.setCheckable(True)
        space_action.triggered.connect(lambda: self._set_delimiter(' '))
        delimiter_menu.addAction(space_action)

        # Show the menu at the cursor position
        menu.exec_(self.mapToGlobal(pos))

    def _cut_column(self, column):
        """Cut column data to clipboard"""
        self._copy_column(column)
        self._clear_column(column)

    def _clear_column(self, column):
        """Clear all data in the specified column"""
        print(f"DEBUG: _clear_column called with column={column}")
        # Get the table widget
        table = self.parent()
        if not table or not hasattr(table, 'rowCount') or not hasattr(table, 'columnCount'):
            print("DEBUG: Could not find table widget")
            return

        # Clear all items in the column
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item:
                item.setText("")
        print(f"DEBUG: Cleared column {column}")

    def _copy_column(self, column):
        """Copy column data to clipboard"""
        print(f"DEBUG: _copy_column called with column={column}")
        if self.data_display_widget and hasattr(self.data_display_widget, 'copy_column_data'):
            print(f"DEBUG: Calling copy_column_data on DataDisplayWidget")
            self.data_display_widget.copy_column_data(column)
        else:
            print("DEBUG: No DataDisplayWidget reference or no copy_column_data method")

    def _paste_column(self, column):
        """Paste data from clipboard to column"""
        print(f"DEBUG: _paste_column called with column={column}")
        if self.data_display_widget and hasattr(self.data_display_widget, 'paste_column_data'):
            print(f"DEBUG: Calling paste_column_data on DataDisplayWidget")
            self.data_display_widget.paste_column_data(column)
        else:
            print("DEBUG: No DataDisplayWidget reference or no paste_column_data method")

    def _insert_column(self, column):
        """Insert a new column"""
        print(f"DEBUG: _insert_column called with column={column}")
        if self.data_display_widget and hasattr(self.data_display_widget, 'insert_column'):
            print(f"DEBUG: Calling insert_column on DataDisplayWidget")
            self.data_display_widget.insert_column(column)
        else:
            print("DEBUG: No DataDisplayWidget reference or no insert_column method")

    def _delete_column(self, column):
        """Delete a column"""
        print(f"DEBUG: _delete_column called with column={column}")
        if self.data_display_widget and hasattr(self.data_display_widget, 'delete_column'):
            print(f"DEBUG: Calling delete_column on DataDisplayWidget")
            self.data_display_widget.delete_column(column)
        else:
            print("DEBUG: No DataDisplayWidget reference or no delete_column method")

    def _set_delimiter(self, delimiter):
        """Set the delimiter for clipboard operations"""
        print(f"DEBUG: _set_delimiter called with delimiter='{delimiter}'")
        if self.data_display_widget and hasattr(self.data_display_widget, 'set_clipboard_delimiter'):
            print(f"DEBUG: Calling set_clipboard_delimiter on DataDisplayWidget")
            self.data_display_widget.set_clipboard_delimiter(delimiter)
        else:
            print("DEBUG: No DataDisplayWidget reference or no set_clipboard_delimiter method")


class DataDisplayWidget(QWidget):
    """Handles data table display, raw/advanced views, and formatting"""

    # Mapping from dimension names to display names for better readability
    DIMENSION_DISPLAY_NAMES = {
        'tec': 'technology',
        'node_loc': 'location',
        'node_dest': 'destination',
        'node_origin': 'origin',
        'node_rel': 'relation node',
        'node_share': 'share node',
        'year_vtg': 'vintage year',
        'year_act': 'active year',
        'year_rel': 'relation year',
        'type_tec': 'technology type',
        'type_emiss': 'emission type',
        'type_addon': 'addon type',
        'type_year': 'year type',
        'type_emission': 'emission type',
        'type_rel': 'relation type',
        'commodity': 'commodity',
        'level': 'level',
        'mode': 'mode',
        'time': 'time',
        'time_origin': 'origin time',
        'time_dest': 'destination time',
        'emission': 'emission',
        'land_scenario': 'land scenario',
        'land_type': 'land type',
        'rating': 'rating',
        'grade': 'grade',
        'shares': 'shares',
        'relation': 'relation',
        'value': 'value'
    }

    # Define PyQt signals
    display_mode_changed = pyqtSignal()
    cell_value_changed = pyqtSignal(str, object, object, object)  # mode, row_or_year, col_or_tech, new_value
    column_paste_requested = pyqtSignal(str, str, dict)  # column_name, paste_data_format, row_changes_dict
    chart_update_needed = pyqtSignal()  # Signal to update chart without refreshing table

    def __init__(self, parent=None, tech_descriptions=None):
        super().__init__(parent)
        self.table_display_mode = "raw"  # "raw" or "advanced"
        self.hide_empty_columns = False  # Whether to hide empty columns in advanced view
        self.property_selectors = {}
        self.hide_empty_checkbox = None
        self.tech_descriptions = tech_descriptions or {}

        # Clipboard operations
        self.clipboard_delimiter = '\t'  # Default delimiter for clipboard operations

        # Undo/Redo system
        self.undo_manager = UndoManager()

        # Debouncing timer for filter changes
        self._filter_change_timer = QTimer()
        self._filter_change_timer.setSingleShot(True)
        self._filter_change_timer.timeout.connect(self._emit_display_mode_changed)

        # Widgets will be assigned externally from .ui file
        self.param_title: QLabel
        self.view_toggle_button: QPushButton
        self.param_table: QTableWidget
        self.selector_container: QWidget

    def initialize_with_ui_widgets(self):
        """Initialize component with UI widgets assigned externally from .ui file"""
        # Connect signals for existing widgets
        self.view_toggle_button.clicked.connect(self._toggle_display_mode)
        self.param_table.cellChanged.connect(self._on_cell_changed)

        # Set custom header view for right-click context menu
        custom_header = ColumnHeaderView(Qt.Horizontal, self.param_table)
        custom_header.data_display_widget = self  # Store reference to this widget
        self.param_table.setHorizontalHeader(custom_header)

        # Initialize state
        self.table_display_mode = "raw"
        self.hide_empty_columns = False
        self.property_selectors = {}
        self.hide_empty_checkbox = None

    def display_parameter_data(self, parameter: Optional[Parameter], is_results: bool = False):
        """Display parameter/result data in the table view"""
        self.display_data_table(parameter, "Result" if is_results else "Parameter", is_results)

    def display_data_table(self, data: Optional[Parameter], title_prefix: str, is_results: bool = False):
        """
        Unified method for displaying parameter/result data in table and chart views.

        Args:
            data: Parameter object to display (can be None for clearing)
            title_prefix: "Parameter" or "Result" for titles
            is_results: Whether this is results data (affects some logic)
        """
        if data is None:
            # Clear the display when no data is selected
            self.param_title.setText("Select a parameter to view data")
            self._clear_table_display()
            return

        df = data.df

        # Update title
        self.param_title.setText(f"{title_prefix}: {data.name}")
        UIStyler.setup_parameter_title_label(self.param_title, is_small=False)

        if df.empty:
            self._clear_table_display()
            return

        # Handle view mode (raw vs advanced)
        display_df = df  # Default fallback
        try:
            if is_results:
                # For results data, always show transformed data (years as indices, year column hidden)
                try:
                    display_df = self.transform_to_display_format(
                        df,
                        is_results=True,
                        current_filters=self._get_current_filters(),
                        hide_empty=self.hide_empty_columns,
                        for_chart=True
                    )
                except Exception as e:
                    print(f"Transformation failed for results: {e}")
                    display_df = df
                self._setup_property_selectors(df)
            else:
                # For input data, use raw/advanced modes
                if self.table_display_mode == "advanced":
                    try:
                        display_df = self.transform_to_display_format(
                            df,
                            is_results=False,
                            current_filters=self._get_current_filters(),
                            hide_empty=self.hide_empty_columns,
                            for_chart=True
                        )
                    except Exception as e:
                        print(f"Transformation failed for advanced: {e}")
                        display_df = df
                    self._setup_property_selectors(df)
                else:
                    display_df = df
        except Exception as e:
            print(f"Error in display_data_table view mode handling: {e}")
            display_df = df

        # Show property selectors when data is transformed
        show_selectors = is_results or (not is_results and self.table_display_mode == "advanced")
        self.selector_container.setVisible(show_selectors)

        try:
            # Set up table dimensions and headers
            self._configure_table(display_df, is_results)

            # Format and populate table data
            self._populate_table(display_df, data)

            # Enable controls and update status
            self._finalize_display(display_df, data, title_prefix, is_results)
        except Exception as e:
            print(f"Error in table display setup: {e}")
            # Try to show a basic table with the original data as fallback
            try:
                self._configure_table(df, is_results)
                self._populate_table(df, data)
                self._finalize_display(df, data, title_prefix, is_results)
            except Exception as fallback_e:
                print(f"Fallback table display also failed: {fallback_e}")
                self._clear_table_display()

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

    def _finalize_display(self, display_df: pd.DataFrame, data: Optional[Parameter], title_prefix: str, is_results: bool):
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
        # Toggle the display mode
        if self.table_display_mode == "raw":
            self.table_display_mode = "advanced"
            self.view_toggle_button.setChecked(True)
            self.view_toggle_button.setText("Advanced Display")
            self.selector_container.setVisible(True)
        else:
            self.table_display_mode = "raw"
            self.view_toggle_button.setChecked(False)
            self.view_toggle_button.setText("Raw Display")
            self.selector_container.setVisible(False)

        # Emit signal to refresh display (will be connected by parent)
        self.display_mode_changed.emit()

    def _configure_table(self, df: pd.DataFrame, is_results: bool):
        """Configure table dimensions and headers"""
        self.param_table.setRowCount(len(df))

        # Set column count and vertical headers based on display mode or results type
        if self.table_display_mode == "advanced" or is_results:
            self.param_table.setColumnCount(len(df.columns))
            # Set vertical header labels to show years (for advanced view or results)
            year_labels = [str(year) for year in df.index]
            self.param_table.setVerticalHeaderLabels(year_labels)
        else:
            self.param_table.setColumnCount(len(df.columns))
            # Set vertical headers to show row numbers starting from 1 (for raw data)
            row_labels = [str(i + 1) for i in range(len(df))]
            self.param_table.setVerticalHeaderLabels(row_labels)

        # Set headers with tooltips
        for i, col in enumerate(df.columns):
            # Use display name if available, otherwise use the original column name
            display_name = self.DIMENSION_DISPLAY_NAMES.get(str(col), str(col))
            header_item = QTableWidgetItem(display_name)
            desc = self.tech_descriptions.get(str(col), {}).get('description', '')
            if desc and type(desc) is str: # since desc could be np.nan when reading empty CSV cells
                header_item.setToolTip(desc)
            self.param_table.setHorizontalHeaderItem(i, header_item)

    def _populate_table(self, df: pd.DataFrame, parameter: Parameter):
        """Fill table data with proper formatting"""
        # Disconnect cellChanged signal during population to prevent infinite loops
        self.param_table.cellChanged.disconnect(self._on_cell_changed)

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

        # Reconnect cellChanged signal after population
        self.param_table.cellChanged.connect(self._on_cell_changed)

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

        # Get column info to identify which columns should have selectors
        column_info = self._identify_columns(df)
        filter_columns = column_info.get('filter_cols', [])

        # Get selector layout and clear it completely
        selector_layout = self.selector_container.layout()
        if selector_layout is None:
            # Create layout if it doesn't exist
            selector_layout = QHBoxLayout(self.selector_container)
            selector_layout.setContentsMargins(2, 2, 2, 2)
            selector_layout.setSpacing(2)
        else:
            # Clear existing layout contents
            while selector_layout.count():
                item = selector_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()

        # Add checkbox for hiding empty columns
        self.hide_empty_checkbox = QCheckBox("Hide Empty Columns")
        UIStyler.setup_checkbox(self.hide_empty_checkbox)
        # Block signals while setting initial state to prevent unwanted emissions
        self.hide_empty_checkbox.blockSignals(True)
        self.hide_empty_checkbox.setChecked(self.hide_empty_columns)
        self.hide_empty_checkbox.blockSignals(False)
        self.hide_empty_checkbox.stateChanged.connect(self._on_hide_empty_changed)
        selector_layout.addWidget(self.hide_empty_checkbox)

        for col in filter_columns:
            # Skip the value column - we don't want to filter by values
            if col == column_info.get('value_col'):
                continue

            # Create label
            label = QLabel(f"{col}:")
            UIStyler.setup_filter_label(label)
            selector_layout.addWidget(label)

            # Create combo box
            combo = QComboBox()
            UIStyler.setup_combo_box(combo)

            # Add "All" option and unique values
            unique_values = sorted(df[col].dropna().unique().tolist())
            combo.addItem("All")
            for value in unique_values:
                combo.addItem(str(value))

            # Set default to "All"
            combo.setCurrentText("All")

            # Restore previous selection if available
            if col in current_selections and current_selections[col] in [combo.itemText(i) for i in range(combo.count())]:
                # Block signals while setting initial state to prevent unwanted emissions
                combo.blockSignals(True)
                combo.setCurrentText(current_selections[col])
                combo.blockSignals(False)

            # Connect signal
            combo.currentTextChanged.connect(self._on_selector_changed)

            selector_layout.addWidget(combo)
            self.property_selectors[col] = combo

        # Add stretch at the end
        selector_layout.addStretch()

    def _on_selector_changed(self):
        """Handle selector value changes - refresh the table display with debouncing"""
        try:
            # Get the sender (the combo box that changed)
            sender = self.sender()
            if sender and sender.currentText() == "All":
                # Selecting "All" should clear filters immediately without delay
                # Stop any pending timer
                if self._filter_change_timer.isActive():
                    self._filter_change_timer.stop()
                # Emit immediately
                self.display_mode_changed.emit()
            else:
                # Other filter changes are debounced
                self._filter_change_timer.start(100)
        except Exception as e:
            print(f"ERROR in _on_selector_changed: {e}")
            import traceback
            traceback.print_exc()

    def _emit_display_mode_changed(self):
        """Actually emit the display mode changed signal after debouncing"""
        try:
            self.display_mode_changed.emit()
        except Exception as e:
            print(f"ERROR in _emit_display_mode_changed: {e}")
            import traceback
            traceback.print_exc()

    def _on_hide_empty_changed(self):
        """Handle hide empty columns checkbox state change"""
        self.hide_empty_columns = self.hide_empty_checkbox.isChecked()
        # Emit signal to refresh display (will be connected by parent)
        self.display_mode_changed.emit()

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value changes in editable table"""

        # Get the new value from the cell
        item = self.param_table.item(row, col)
        if not item:
            return

        new_value_str = item.text().strip()

        # Parse the value (handle empty strings as 0 or NaN)
        try:
            if new_value_str == "":
                new_value = 0.0
            else:
                new_value = float(new_value_str)
        except ValueError:
            # Invalid input, revert to original value by refreshing display
            self.display_mode_changed.emit()
            return

        if self.table_display_mode == "advanced":
            # Handle advanced mode editing (pivot table)
            self._sync_pivot_change_to_raw_data(row, col, new_value)
        else:
            # Handle raw mode editing (direct table editing)
            # Get column name from horizontal header
            horizontal_header = self.param_table.horizontalHeaderItem(col)
            if horizontal_header:
                column_name = horizontal_header.text()
                self.cell_value_changed.emit("raw", row, column_name, new_value)

        self.chart_update_needed.emit()

    def _sync_pivot_change_to_raw_data(self, row: int, col: int, new_value: float):
        """Sync a change made in pivot mode back to the raw data"""
        # This method needs access to the current parameter data
        # We'll need to implement this with help from the parent MainWindow
        # For now, we'll emit a signal that includes the change information

        # Get column and row information from the current display
        year = None
        technology = None

        # Get year from vertical header (row)
        vertical_header = self.param_table.verticalHeaderItem(row)
        if vertical_header:
            try:
                year = int(vertical_header.text())
            except ValueError:
                pass

        # Get technology from horizontal header (column)
        horizontal_header = self.param_table.horizontalHeaderItem(col)
        if horizontal_header:
            technology = horizontal_header.text()

        # Emit signal with change information
        # This will be connected to MainWindow which has access to the scenario data
        if hasattr(self, 'cell_value_changed'):
            self.cell_value_changed.emit("advanced", year, technology, new_value)

    def transform_to_display_format(self, df: pd.DataFrame, is_results: bool = False,
                                   current_filters: Optional[Dict[str, str]] = None, hide_empty: Optional[bool] = None,
                                   for_chart: bool = False) -> pd.DataFrame:
        """
        Transform data to display format for both table and chart views.

        Args:
            df: Input DataFrame
            is_results: Whether this is results data
            current_filters: Filter selections to apply
            hide_empty: Whether to hide empty columns
            for_chart: Whether this is for chart display (affects some logic)

        Returns:
            Transformed DataFrame ready for display
        """
        try:
            if df.empty:
                return df

            if hide_empty is None:
                hide_empty = self.hide_empty_columns if not for_chart else False  # Charts typically don't hide empty columns

            # Identify column types
            column_info = self._identify_columns(df)

            # Apply filters
            filtered_df = self._apply_filters(df, current_filters, column_info)

            # Transform data structure
            transformed_df = self._transform_data_structure(filtered_df, column_info, is_results)

            # Clean and finalize output
            final_df = self._clean_output(transformed_df, hide_empty, is_results)

            return final_df
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    def _transform_to_advanced_view(self, df: pd.DataFrame, current_filters: dict = None,
                                   is_results: bool = False, hide_empty: bool = None) -> pd.DataFrame:
        """Transform data to advanced 2D view format - now uses common method"""
        return self.transform_to_display_format(df, is_results, current_filters, hide_empty, for_chart=False)

    def _identify_columns(self, df: pd.DataFrame) -> Dict[str, Union[List[str], Optional[str]]]:
        """Identify different types of columns in the DataFrame"""
        year_cols = []
        pivot_cols = []  # Columns that become pivot table headers
        filter_cols = []  # Columns used for filtering
        ignored_cols = []  # Columns to ignore completely
        value_col = None

        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['value', 'val']:
                value_col = col
            elif col_lower in ['year_vtg', 'year_act', 'year', 'period', 'year_vintage', 'year_active']:
                year_cols.append(col)
            elif col_lower in ['time', 'unit', 'units']:
                # Ignore these columns completely
                ignored_cols.append(col)
            elif col_lower in ['commodity', 'technology', 'type', 'tec']:
                # These become pivot table column headers
                pivot_cols.append(col)
            elif col_lower in ['region', 'node', 'node_loc', 'node_rel', 'node_dest', 'node_origin',
                              'mode', 'level', 'grade', 'fuel', 'sector', 'category', 'subcategory']:
                # These are used for filtering
                filter_cols.append(col)

        return {
            'year_cols': year_cols,
            'pivot_cols': pivot_cols,
            'filter_cols': filter_cols,
            'ignored_cols': ignored_cols,
            'value_col': value_col
        }

    def _apply_filters(self, df: pd.DataFrame, filters: Optional[Dict[str, str]], column_info: dict) -> pd.DataFrame:
        """Apply current filter selections to DataFrame"""
        try:
            filtered_df = df.copy()
            if filters:
                for filter_col, filter_value in filters.items():
                    if filter_value and filter_value != "All" and filter_col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[filter_col] == filter_value]
            return filtered_df
        except Exception as e:
            print(f"ERROR in _apply_filters: {e}")
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    def _transform_data_structure(self, df: pd.DataFrame, column_info: dict, is_results: bool) -> pd.DataFrame:
        """Transform DataFrame structure based on data type"""
        # Pivoting logic for input data
        if not is_results and self._should_pivot(df, column_info):
            return self._perform_pivot(df, column_info)
        else:
            return self._prepare_2d_format(df, column_info)

    def _clean_output(self, df: pd.DataFrame, hide_empty: bool, is_results: bool) -> pd.DataFrame:
        """Clean and filter final output DataFrame"""
        if hide_empty:
            df = self._hide_empty_columns(df, is_results)

        # Additional cleaning logic
        return df

    def _should_pivot(self, df: pd.DataFrame, column_info: dict) -> bool:
        """Determine if DataFrame should be pivoted based on column structure"""
        # Pivoting logic - simplified for now
        year_cols = column_info.get('year_cols', [])
        pivot_cols = column_info.get('pivot_cols', [])
        value_col = column_info.get('value_col')

        # Pivot if we have year columns, pivot columns, and a value column
        return bool(year_cols and pivot_cols and value_col)

    def _perform_pivot(self, df: pd.DataFrame, column_info: dict) -> pd.DataFrame:
        """Perform pivot operation on DataFrame"""
        try:
            year_cols = column_info.get('year_cols', [])
            pivot_cols = column_info.get('pivot_cols', [])
            value_col = column_info.get('value_col')

            print(f"DEBUG: _perform_pivot called with year_cols={year_cols}, pivot_cols={pivot_cols}, value_col={value_col}")

            if not (year_cols and pivot_cols and value_col):
                print("DEBUG: Missing required columns for pivot, returning original df")
                return df

            # Try different combinations of year and pivot columns
            for index_col in year_cols:
                for columns_col in pivot_cols:
                    try:
                        pivoted = df.pivot_table(
                            values=value_col,
                            index=index_col,
                            columns=columns_col,
                            aggfunc=lambda x: x.iloc[0] if len(x) > 0 else np.nan
                        )
                        return pivoted
                    except Exception as e:
                        print(f"DEBUG: Pivot attempt failed for index='{index_col}', columns='{columns_col}': {e}")
                        continue

            # Fallback to original data if all pivot attempts fail
            return df
        except Exception as e:
            print(f"ERROR in _perform_pivot: {e}")
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    def _prepare_2d_format(self, df: pd.DataFrame, column_info: dict) -> pd.DataFrame:
        """Prepare DataFrame in 2D format without pivoting"""
        # For results data in advanced view, set year as index and remove year column
        year_cols = column_info.get('year_cols', [])
        if year_cols:
            # Use the first year column found
            year_col = year_cols[0]
            if year_col in df.columns:
                # Set year as index and remove from columns
                df = df.set_index(year_col)
                df.index.name = year_col
        return df

    def _hide_empty_columns(self, df: pd.DataFrame, is_results: bool) -> pd.DataFrame:
        """Hide columns that are entirely empty or zero"""
        if df.empty:
            return df

        # Identify columns to keep
        columns_to_keep = []
        for col in df.columns:
            col_data = df[col]
            if col_data.dtype in ['int64', 'float64']:
                # Keep numeric columns that have at least one non-zero, non-NaN value
                if not (col_data.dropna() == 0).all():
                    columns_to_keep.append(col)
            else:
                # Keep non-numeric columns that have at least one non-empty value
                if not col_data.isna().all():
                    columns_to_keep.append(col)

        return df[columns_to_keep] if columns_to_keep else df

    # Column operations methods (called by the custom header view)

    def copy_column_data(self, column: int):
        """Copy column data to clipboard as a single column (one value per line)"""
        print(f"DEBUG: copy_column_data called with column={column}")
        try:
            if column < 0 or column >= self.param_table.columnCount():
                print(f"DEBUG: Invalid column {column}, table has {self.param_table.columnCount()} columns")
                return

            # Get column name
            header_item = self.param_table.horizontalHeaderItem(column)
            if not header_item:
                print(f"DEBUG: No header item for column {column}")
                return
            column_name = header_item.text()
            print(f"DEBUG: Column name is '{column_name}'")

            # Collect data from the column as a single column (one value per line)
            data_lines = []
            print(f"DEBUG: Starting data collection, table has {self.param_table.rowCount()} rows")

            for row in range(self.param_table.rowCount()):
                item = self.param_table.item(row, column)
                if item:
                    cell_text = item.text()
                    data_lines.append(cell_text)
                    print(f"DEBUG: Row {row}: '{cell_text}'")
                else:
                    data_lines.append("")
                    print(f"DEBUG: Row {row}: (empty)")

            # Join with newlines to create a single column format
            clipboard_text = '\n'.join(data_lines)
            print(f"DEBUG: Clipboard text (single column format): {repr(clipboard_text)}")
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            print(f"DEBUG: Set clipboard text successfully")

        except Exception as e:
            print(f"DEBUG: Error copying column data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Copy Error", f"Failed to copy column data: {str(e)}")

    def paste_column_data(self, column: int):
        """Paste data from clipboard to column"""
        print(f"DEBUG: paste_column_data called with column={column}")
        try:
            if column < 0 or column >= self.param_table.columnCount():
                print(f"DEBUG: Invalid column {column}")
                return

            # Get column name
            header_item = self.param_table.horizontalHeaderItem(column)
            if not header_item:
                print(f"DEBUG: No header item for column {column}")
                return
            column_name = header_item.text()
            print(f"DEBUG: Column name is '{column_name}'")

            # Get clipboard text
            clipboard = QApplication.clipboard()
            clipboard_text = clipboard.text().strip()
            if not clipboard_text:
                print("DEBUG: Clipboard is empty")
                return

            print(f"DEBUG: Clipboard text: {repr(clipboard_text)}")

            # Try to detect format: single column (one value per line) vs delimited format
            lines = clipboard_text.split('\n')
            print(f"DEBUG: Split into {len(lines)} lines")

            # Check if this looks like single-column data (no tabs/commas in most lines)
            is_single_column = True
            for line in lines:
                if self.clipboard_delimiter in line and line.strip():
                    is_single_column = False
                    break

            print(f"DEBUG: Detected format: {'single column' if is_single_column else 'delimited'}")

            # Prepare data for paste operation
            paste_data = []
            if is_single_column:
                # Single column format: just paste the values directly
                data_lines = [line.strip() for line in lines if line.strip()]
                print(f"DEBUG: Single column data has {len(data_lines)} values")

                if not data_lines:
                    QMessageBox.warning(self, "Paste Error", "No data found in clipboard.")
                    return

                paste_data = data_lines
            else:
                # Delimited format: expect header + data
                data_lines = clipboard_text.split(self.clipboard_delimiter)
                print(f"DEBUG: Delimited data split into {len(data_lines)} parts")

                if len(data_lines) < 2:  # Need at least header + one data row
                    QMessageBox.warning(self, "Paste Error", "Clipboard data must contain at least a header and one data row.")
                    return

                # Skip header (first line) and paste data
                paste_data = [data.strip() for data in data_lines[1:] if data.strip()]

            # Collect current values for undo (only for rows that will be changed)
            row_changes = {}
            for row in range(min(len(paste_data), self.param_table.rowCount())):
                item = self.param_table.item(row, column)
                if item:
                    current_text = item.text()
                    # Store the original display-formatted value for consistent undo formatting
                    # This preserves the same formatting that was shown before the paste
                    old_value = current_text if current_text else ""

                    row_changes[row] = (old_value, paste_data[row])

            # Emit signal to MainWindow to handle the paste operation with undo support
            paste_format = "single_column" if is_single_column else "delimited"
            self.column_paste_requested.emit(column_name, paste_format, row_changes)
            print("DEBUG: Paste operation requested successfully")

        except Exception as e:
            print(f"DEBUG: Error requesting paste column data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Paste Error", f"Failed to paste column data: {str(e)}")

    def insert_column(self, column: int):
        """Insert a new column at the specified position"""
        try:
            # Prompt for column name
            column_name, ok = QInputDialog.getText(
                self, "Insert Column", "Enter column name:",
                text=f"NewColumn{column}"
            )

            if not ok or not column_name.strip():
                return

            column_name = column_name.strip()

            # Get the current parameter data
            # This needs to be implemented - for now just show a placeholder
            QMessageBox.information(
                self, "Insert Column",
                f"Insert column '{column_name}' at position {column} would be implemented here.\n"
                "This requires integration with the scenario data management."
            )

        except Exception as e:
            print(f"Error inserting column: {e}")
            QMessageBox.warning(self, "Insert Error", f"Failed to insert column: {str(e)}")

    def delete_column(self, column: int):
        """Delete the specified column"""
        try:
            if column < 0 or column >= self.param_table.columnCount():
                return

            # Get column name
            header_item = self.param_table.horizontalHeaderItem(column)
            if not header_item:
                return
            column_name = header_item.text()

            # Confirm deletion
            reply = QMessageBox.question(
                self, "Delete Column",
                f"Are you sure you want to delete column '{column_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Get the current parameter data
            # This needs to be implemented - for now just show a placeholder
            QMessageBox.information(
                self, "Delete Column",
                f"Delete column '{column_name}' would be implemented here.\n"
                "This requires integration with the scenario data management."
            )

        except Exception as e:
            print(f"Error deleting column: {e}")
            QMessageBox.warning(self, "Delete Error", f"Failed to delete column: {str(e)}")

    def cut_column_data(self, column: int):
        """Cut column data to clipboard (copy then clear)"""
        # Copy the data first
        self.copy_column_data(column)

        # Then clear the column
        self._clear_column_data(column)

    def _clear_column_data(self, column: int):
        """Clear all data in the specified column"""
        if column < 0 or column >= self.param_table.columnCount():
            return

        # Clear all items in the column
        for row in range(self.param_table.rowCount()):
            item = self.param_table.item(row, column)
            if item:
                item.setText("")

    def set_clipboard_delimiter(self, delimiter: str):
        """Set the delimiter for clipboard operations"""
        self.clipboard_delimiter = delimiter
