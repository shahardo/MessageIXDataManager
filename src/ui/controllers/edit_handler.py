"""
Edit Handler - Manages cell value editing logic for parameters and results

Extracted from MainWindow to provide focused editing functionality.
"""

from typing import Optional, Tuple, Any
import pandas as pd
from core.data_models import ScenarioData, Parameter
from managers.commands import EditCellCommand, EditPivotCommand


class EditHandler:
    """
    Handler for managing cell value editing operations across different data formats.

    Handles raw data editing, advanced/pivot mode editing, and sync operations
    between different data representations.
    """

    def __init__(self, get_current_scenario_callback, data_display):
        """
        Initialize the edit handler.

        Args:
            get_current_scenario_callback: Function to get current scenario (is_results: bool) -> ScenarioData
            data_display: DataDisplayWidget instance for accessing display state
        """
        self.get_current_scenario = get_current_scenario_callback
        self.data_display = data_display

    def handle_cell_value_change(self, mode: str, row_or_year, col_or_tech, new_value, undo_manager) -> bool:
        """
        Handle cell value changes from table editing.

        Args:
            mode: "raw" or "advanced" editing mode
            row_or_year: Row index for raw mode, year value for advanced mode
            col_or_tech: Column name for raw mode, technology name for advanced mode
            new_value: New value to set
            undo_manager: Undo manager for recording operations

        Returns:
            True if edit was handled successfully
        """
        # Get the current scenario and parameter
        scenario = self.get_current_scenario(self.data_display.table_display_mode == "advanced" and hasattr(self.data_display, '_get_current_filters'))
        if not scenario:
            return False

        # Get the currently displayed parameter
        param_name = self._get_current_displayed_parameter()
        if not param_name:
            return False

        parameter = scenario.get_parameter(param_name)
        if not parameter:
            return False

        # Store the original data before making changes
        original_df = parameter.df.copy()
        df = parameter.df.copy()

        # Parse the value (handle empty strings as 0 or NaN)
        try:
            if new_value == "":
                parsed_value = 0.0
            else:
                parsed_value = float(new_value)
        except ValueError:
            # Invalid input, revert to original value by refreshing display
            return False

        old_value = None  # Will be set based on mode
        command = None

        if mode == "raw":
            success = self._handle_raw_edit(df, row_or_year, col_or_tech, parsed_value)
            if success:
                old_value = success[0]
                command = EditCellCommand(scenario, param_name, row_or_year, col_or_tech, old_value, parsed_value)
        elif mode == "advanced":
            success = self._handle_advanced_edit(df, row_or_year, col_or_tech, parsed_value)
            if success:
                old_value, year_col, tech_col, value_col = success
                command = EditPivotCommand(scenario, param_name, row_or_year, col_or_tech, old_value, parsed_value,
                                         year_col, tech_col, value_col)
            else:
                return False
        else:
            return False

        if success and command:
            # Update the parameter with the modified DataFrame
            parameter.df = df

            # Mark the parameter as modified
            scenario.mark_modified(param_name)

            # Record the operation for undo/redo
            undo_manager.execute(command)

            return True

        return False

    def _handle_raw_edit(self, df: pd.DataFrame, row_idx: int, column_name: str, new_value: float) -> Optional[Tuple[Any, str]]:
        """
        Handle direct editing of raw data table.

        Args:
            df: DataFrame to modify
            row_idx: Row index to modify
            column_name: Column name to modify
            new_value: New value to set

        Returns:
            Tuple of (old_value, log_message) if successful, None otherwise
        """
        # Get the old value
        if 0 <= row_idx < len(df) and column_name in df.columns:
            old_value = df.loc[row_idx, column_name]
            df.loc[row_idx, column_name] = new_value
            return (old_value, f"Updated {column_name}: row {row_idx + 1} = {new_value}")
        return None

    def _handle_advanced_edit(self, df: pd.DataFrame, year: int, technology: str, new_value: float) -> Optional[Tuple[Any, str, str, str]]:
        """
        Handle editing in advanced/pivot mode.

        Args:
            df: DataFrame to modify
            year: Year value to match
            technology: Technology name to match
            new_value: New value to set

        Returns:
            Tuple of (old_value, year_col, tech_col, value_col, log_message) if successful, None otherwise
        """
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
            return None

        # Find rows that match the year and technology (robust comparison)
        try:
            year_values = pd.to_numeric(df[year_col], errors='coerce')
        except:
            year_values = df[year_col]  # Fallback if conversion fails

        tech_values = df[tech_col].astype(str).str.strip()
        mask = (year_values == year) & (tech_values == str(technology).strip())
        matching_rows = df[mask]

        if matching_rows.empty:
            return None

        # Get old value and update
        old_value = matching_rows[value_col].iloc[0] if not matching_rows.empty else None
        df.loc[mask, value_col] = new_value

        return (old_value, year_col, tech_col, value_col)

    def sync_advanced_to_raw_data(self, row: int, col: int, new_value: float, scenario: ScenarioData, param_name: str) -> bool:
        """
        Sync a change made in pivot mode back to the raw data.

        Args:
            row: Row in the pivot table
            col: Column in the pivot table
            new_value: New value to set
            scenario: Current scenario
            param_name: Parameter name being edited

        Returns:
            True if sync was successful
        """
        # This method needs access to the current parameter data
        parameter = scenario.get_parameter(param_name)
        if not parameter:
            return False

        df = parameter.df

        # Get column and row information from the current display
        year = None
        technology = None

        # Get year from vertical header (row)
        vertical_header = self.data_display.param_table.verticalHeaderItem(row)
        if vertical_header:
            try:
                year = int(vertical_header.text())
            except ValueError:
                pass

        # Get technology from horizontal header (column)
        horizontal_header = self.data_display.param_table.horizontalHeaderItem(col)
        if horizontal_header:
            technology = horizontal_header.text()

        if year is None or technology is None:
            return False

        # Sync the change using the advanced edit handler
        result = self._handle_advanced_edit(df, year, technology, new_value)
        if result:
            # Update the parameter data
            parameter.df = df
            scenario.mark_modified(param_name)
            return True

        return False

    def _get_current_displayed_parameter(self) -> Optional[str]:
        """
        Get the currently displayed parameter name.

        Returns:
            Parameter name or None if not found
        """
        # This would need to be implemented based on how the main window tracks current parameter
        # For now, return None - this should be passed in from the main window
        return None
