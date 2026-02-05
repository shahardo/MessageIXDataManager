"""
Table formatting utilities for data display.
Handles cell styling, number formatting, and conditional formatting.

Extracted from data_display_widget.py as part of refactoring.
"""
from typing import Optional, Dict, Any, List, Union
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt
import pandas as pd
import numpy as np


class CellStyle:
    """
    Represents styling for a table cell.

    Can be applied to QTableWidgetItem instances to set visual appearance.
    """

    def __init__(
        self,
        background: Optional[QColor] = None,
        foreground: Optional[QColor] = None,
        font: Optional[QFont] = None,
        alignment: int = Qt.AlignLeft | Qt.AlignVCenter,
        editable: bool = True
    ):
        """
        Initialize a cell style.

        Args:
            background: Background color
            foreground: Text color
            font: Font for the cell
            alignment: Text alignment (Qt flags)
            editable: Whether cell should be editable
        """
        self.background = background
        self.foreground = foreground
        self.font = font
        self.alignment = alignment
        self.editable = editable

    def apply_to(self, item: QTableWidgetItem) -> None:
        """
        Apply this style to a table widget item.

        Args:
            item: The QTableWidgetItem to style
        """
        if self.background:
            item.setBackground(QBrush(self.background))
        if self.foreground:
            item.setForeground(QBrush(self.foreground))
        if self.font:
            item.setFont(self.font)
        item.setTextAlignment(self.alignment)

        # Set editability
        flags = item.flags()
        if self.editable:
            flags |= Qt.ItemIsEditable
        else:
            flags &= ~Qt.ItemIsEditable
        item.setFlags(flags)


class TableFormatter:
    """
    Formats table cells based on data type and value.

    Handles:
    - Number formatting (decimals, thousands separator)
    - Conditional formatting (highlight changes, errors)
    - Type-based alignment
    - Column-specific formatting rules

    Usage:
        formatter = TableFormatter()
        formatted_text = formatter.format_value(123.456)
        item = formatter.create_table_item(value, editable=True)
    """

    # Default colors
    CHANGED_BACKGROUND = QColor(255, 255, 200)   # Light yellow
    ERROR_BACKGROUND = QColor(255, 200, 200)     # Light red
    HEADER_BACKGROUND = QColor(240, 240, 240)    # Light gray
    READONLY_BACKGROUND = QColor(245, 245, 245)  # Very light gray

    # Number format thresholds
    LARGE_NUMBER_THRESHOLD = 10000
    MEDIUM_NUMBER_THRESHOLD = 10
    DECIMAL_PLACES_DEFAULT = 4

    def __init__(self, decimal_places: int = DECIMAL_PLACES_DEFAULT):
        """
        Initialize the formatter.

        Args:
            decimal_places: Default number of decimal places for floats
        """
        self.decimal_places = decimal_places
        self._column_formats: Dict[int, str] = {}

    def set_column_format(self, column_index: int, format_string: str) -> None:
        """
        Set a specific format string for a column.

        Args:
            column_index: Column index (0-based)
            format_string: Python format string (e.g., ".2f", ",.0f")
        """
        self._column_formats[column_index] = format_string

    def clear_column_formats(self) -> None:
        """Clear all column-specific formats."""
        self._column_formats.clear()

    def auto_detect_column_formats(self, df: pd.DataFrame) -> Dict[int, str]:
        """
        Auto-detect appropriate formats for each column based on data.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary mapping column index to format string
        """
        formats = {}

        for col_idx, col_name in enumerate(df.columns):
            col_data = df[col_name]

            # Check if column is numeric
            if pd.api.types.is_numeric_dtype(col_data):
                # Get non-null values
                values = col_data.dropna()
                if len(values) == 0:
                    continue

                max_val = values.abs().max()

                # Choose format based on magnitude
                if max_val >= self.LARGE_NUMBER_THRESHOLD:
                    formats[col_idx] = ",.0f"   # #,##0 - thousands separator, no decimals
                elif max_val >= self.MEDIUM_NUMBER_THRESHOLD:
                    formats[col_idx] = ".1f"    # #.# - one decimal
                elif max_val > 0:
                    formats[col_idx] = ".2f"    # #.## - two decimals
                else:
                    formats[col_idx] = f".{self.decimal_places}f"

        return formats

    def format_value(
        self,
        value: Any,
        column_index: Optional[int] = None,
        column_type: Optional[str] = None
    ) -> str:
        """
        Format a value for display.

        Args:
            value: The value to format
            column_index: Optional column index for column-specific formatting
            column_type: Optional type hint for the column

        Returns:
            Formatted string representation
        """
        # Handle null/empty values
        if pd.isna(value) or value is None:
            return ""

        # Handle boolean
        if isinstance(value, bool):
            return str(value)

        # Handle numeric values
        if isinstance(value, (int, float, np.integer, np.floating)):
            # Check for column-specific format
            if column_index is not None and column_index in self._column_formats:
                format_str = self._column_formats[column_index]
                try:
                    return f"{value:{format_str}}"
                except (ValueError, TypeError):
                    pass

            # Default formatting based on type
            if isinstance(value, (int, np.integer)):
                if abs(value) >= self.LARGE_NUMBER_THRESHOLD:
                    return f"{value:,.0f}"
                return str(value)

            # Float formatting
            if abs(value) >= self.LARGE_NUMBER_THRESHOLD:
                return f"{value:,.0f}"
            elif abs(value) >= self.MEDIUM_NUMBER_THRESHOLD:
                return f"{value:.1f}"
            elif abs(value) > 0:
                return f"{value:.{self.decimal_places}f}"
            else:
                return "0"

        # Default: convert to string
        return str(value)

    def get_cell_style(
        self,
        value: Any,
        is_changed: bool = False,
        is_error: bool = False,
        is_header: bool = False,
        is_readonly: bool = False
    ) -> CellStyle:
        """
        Get the appropriate style for a cell.

        Args:
            value: The cell value
            is_changed: Whether the cell has been modified
            is_error: Whether the cell contains an error
            is_header: Whether this is a header cell
            is_readonly: Whether the cell should be read-only

        Returns:
            CellStyle to apply
        """
        background = None
        alignment = Qt.AlignLeft | Qt.AlignVCenter
        editable = not is_readonly

        # Priority: error > changed > header > readonly
        if is_error:
            background = self.ERROR_BACKGROUND
        elif is_changed:
            background = self.CHANGED_BACKGROUND
        elif is_header:
            background = self.HEADER_BACKGROUND
            editable = False
        elif is_readonly:
            background = self.READONLY_BACKGROUND
            editable = False

        # Type-based alignment
        if isinstance(value, (int, float, np.integer, np.floating)):
            alignment = Qt.AlignRight | Qt.AlignVCenter

        return CellStyle(
            background=background,
            alignment=alignment,
            editable=editable
        )

    def create_table_item(
        self,
        value: Any,
        column_index: Optional[int] = None,
        editable: bool = True,
        is_changed: bool = False,
        is_error: bool = False
    ) -> QTableWidgetItem:
        """
        Create a formatted table item.

        Args:
            value: The value for the cell
            column_index: Optional column index for formatting
            editable: Whether the cell should be editable
            is_changed: Whether the cell has been modified
            is_error: Whether the cell contains an error

        Returns:
            Configured QTableWidgetItem
        """
        text = self.format_value(value, column_index)
        item = QTableWidgetItem(text)

        # Get and apply style
        style = self.get_cell_style(
            value,
            is_changed=is_changed,
            is_error=is_error,
            is_readonly=not editable
        )
        style.apply_to(item)

        return item

    def populate_table_row(
        self,
        table,
        row_index: int,
        row_data: List[Any],
        editable: bool = True
    ) -> None:
        """
        Populate a table row with formatted items.

        Args:
            table: QTableWidget to populate
            row_index: Row index to populate
            row_data: List of values for the row
            editable: Whether cells should be editable
        """
        for col_idx, value in enumerate(row_data):
            item = self.create_table_item(
                value,
                column_index=col_idx,
                editable=editable
            )
            table.setItem(row_index, col_idx, item)

    @staticmethod
    def strip_formatting(text: str) -> str:
        """
        Remove formatting from a text value (e.g., thousands separators).

        Args:
            text: Formatted text value

        Returns:
            Plain text value suitable for parsing
        """
        if not text:
            return ""

        # Remove thousands separators
        stripped = text.replace(",", "")

        return stripped.strip()

    @staticmethod
    def parse_numeric(text: str) -> Optional[Union[int, float]]:
        """
        Parse a possibly-formatted numeric string.

        Args:
            text: Text to parse

        Returns:
            Parsed number or None if parsing fails
        """
        stripped = TableFormatter.strip_formatting(text)
        if not stripped:
            return None

        try:
            # Try int first
            if '.' not in stripped:
                return int(stripped)
            return float(stripped)
        except (ValueError, TypeError):
            return None


# Dimension display name mapping for better readability
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


def get_display_name(dimension: str) -> str:
    """
    Get the display name for a dimension.

    Args:
        dimension: Internal dimension name

    Returns:
        Human-readable display name
    """
    return DIMENSION_DISPLAY_NAMES.get(dimension, dimension)
