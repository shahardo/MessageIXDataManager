"""
Data Display Widget - Handles data table display, raw/advanced views, and formatting

Extracted from MainWindow to provide focused data display functionality.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QComboBox, QGroupBox, QCheckBox, QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Union, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # No additional imports needed since we assume UI widgets exist

from core.data_models import Parameter
from ..ui_styler import UIStyler


class DataDisplayWidget(QWidget):
    """Handles data table display, raw/advanced views, and formatting"""

    # Define PyQt signals
    display_mode_changed = pyqtSignal()
    cell_value_changed = pyqtSignal(str, object, object, object)  # mode, row_or_year, col_or_tech, new_value
    chart_update_needed = pyqtSignal()  # Signal to update chart without refreshing table

    def __init__(self, parent=None, tech_descriptions=None):
        super().__init__(parent)
        self.table_display_mode = "raw"  # "raw" or "advanced"
        self.hide_empty_columns = False  # Whether to hide empty columns in advanced view
        self.property_selectors = {}
        self.hide_empty_checkbox = None
        self.tech_descriptions = tech_descriptions or {}

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
            header_item = QTableWidgetItem(str(col))
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
        print(f"DEBUG: Cell changed at row={row}, col={col}")  # Debug print

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
            print(f"DEBUG: Invalid value, reverting display")  # Debug print
            # Invalid input, revert to original value by refreshing display
            self.display_mode_changed.emit()
            return

        print(f"DEBUG: Parsed value: {new_value}, syncing...")  # Debug print

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
            print(f"DEBUG: transform_to_display_format called - is_results={is_results}, for_chart={for_chart}")
            print(f"DEBUG: input df shape: {df.shape}, columns: {list(df.columns)}")
            print(f"DEBUG: current_filters: {current_filters}")

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
            elif col_lower in ['commodity', 'technology', 'type']:
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
            print(f"DEBUG: _perform_pivot called with df shape: {df.shape}")
            year_cols = column_info.get('year_cols', [])
            pivot_cols = column_info.get('pivot_cols', [])
            value_col = column_info.get('value_col')

            if not (year_cols and pivot_cols and value_col):
                return df

            # Try different combinations of year and pivot columns
            for index_col in year_cols:
                for columns_col in pivot_cols:
                    try:
                        pivoted = df.pivot_table(
                            values=value_col,
                            index=index_col,
                            columns=columns_col,
                            aggfunc=lambda x: x.iloc[0] if len(x) > 0 else 0
                        ).fillna(0)
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
