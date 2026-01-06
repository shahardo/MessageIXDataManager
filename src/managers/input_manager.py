"""
Input Manager - handles loading and parsing of MESSAGEix Excel input files
"""

import os
import pandas as pd
import numpy as np
import logging
from openpyxl import load_workbook
from typing import Optional, List, Callable, Dict, Any

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager
from utils.parameter_utils import create_parameter_from_data
from utils.error_handler import ErrorHandler, SafeOperation


class InputManager(BaseDataManager):
    """
    InputManager class for loading and parsing MESSAGEix input Excel files.

    This class handles the complex process of reading MESSAGEix scenario data
    from Excel workbooks, parsing sets and parameters, and providing access
    to the loaded data for analysis and visualization.

    Attributes:
        scenarios: List of loaded ScenarioData objects
        loaded_file_paths: Corresponding file paths for loaded scenarios
    """

    def load_excel_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ScenarioData:
        """
        Load and parse a MESSAGEix Excel input file.

        This method performs comprehensive validation and parsing of MESSAGEix
        input files, extracting sets, parameters, and metadata.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls format).
                      File must exist and be readable.
            progress_callback: Optional callback function for progress updates.
                             Receives (percentage: int, message: str) parameters.
                             Called at key milestones during loading process.

        Returns:
            ScenarioData object containing parsed sets and parameters.

        Raises:
            FileNotFoundError: If the specified file_path does not exist.
            ValueError: If the file format is invalid or parsing fails.
            PermissionError: If file cannot be read due to permissions.

        Example:
            >>> manager = InputManager()
            >>> def progress(pct, msg): print(f"{pct}%: {msg}")
            >>> scenario = manager.load_excel_file("data.xlsx", progress)
            >>> print(f"Loaded {len(scenario.parameters)} parameters")
        """
        return self.load_file(file_path, progress_callback)

    def _parse_workbook(
        self,
        wb: Any,
        scenario: ScenarioData,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse workbook for input data - implements abstract method.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate
            progress_callback: Optional progress callback function
        """
        if progress_callback:
            progress_callback(10, "Parsing sets...")

        # Parse sets
        self._parse_sets(wb, scenario, progress_callback)

        if progress_callback:
            progress_callback(40, "Sets parsed, parsing parameters...")

        # Parse parameters
        self._parse_parameters(wb, scenario, progress_callback)

    def _parse_sets(
        self,
        wb: Any,
        scenario: ScenarioData,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse sets from the workbook.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate with sets
            progress_callback: Optional progress callback function
        """
        error_handler = ErrorHandler()
        logger = logging.getLogger(__name__)

        with SafeOperation("set parsing", error_handler, logger) as safe_op:
            # Look for common set sheet names in message_ix format
            set_sheet_names = ['sets', 'set', 'Sets', 'Set']

            for sheet_name in set_sheet_names:
                if sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    self._parse_sets_sheet(sheet, scenario)
                    break

            # Also check for individual set sheets (common in message_ix)
            potential_set_sheets = ['node', 'technology', 'commodity', 'level', 'year', 'mode', 'time']
            total_sheets = len([s for s in potential_set_sheets if s in wb.sheetnames])

            for i, set_name in enumerate(potential_set_sheets):
                if set_name in wb.sheetnames:
                    if progress_callback and total_sheets > 0:
                        progress = 10 + int((i / total_sheets) * 20)  # Progress from 10% to 30%
                        progress_callback(progress, f"Parsing set: {set_name}")

                    sheet = wb[set_name]
                    self._parse_individual_set_sheet(sheet, set_name, scenario)

    def _parse_sets_sheet(self, sheet: Any, scenario: ScenarioData) -> None:
        """
        Parse a combined sets sheet.

        Args:
            sheet: Openpyxl worksheet object
            scenario: ScenarioData object to populate
        """
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is not None and len(row) > 1:
                set_name = str(row[0]).strip()
                # Collect all non-empty values from remaining columns
                set_values = []
                for val in row[1:]:
                    if val is not None:
                        val_str = str(val).strip()
                        if val_str:
                            set_values.append(val_str)
                if set_values:
                    scenario.sets[set_name] = pd.Series(set_values)

    def _parse_individual_set_sheet(self, sheet: Any, set_name: str, scenario: ScenarioData) -> None:
        """
        Parse an individual set sheet.

        Args:
            sheet: Openpyxl worksheet object
            set_name: Name of the set to parse
            scenario: ScenarioData object to populate
        """
        set_values = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is not None:
                val_str = str(row[0]).strip()
                if val_str and val_str not in set_values:
                    set_values.append(val_str)
        if set_values:
            scenario.sets[set_name] = pd.Series(set_values)

    def _parse_parameters(
        self,
        wb: Any,
        scenario: ScenarioData,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse parameters from the workbook.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate with parameters
            progress_callback: Optional progress callback function
        """
        # Look for parameter sheets
        param_sheet_names = ['parameters', 'parameter', 'Parameters', 'Parameter', 'data']

        for sheet_name in param_sheet_names:
            if sheet_name in wb.sheetnames:
                if progress_callback:
                    progress_callback(40, f"Parsing combined parameters sheet: {sheet_name}")
                sheet = wb[sheet_name]
                self._parse_parameters_sheet(sheet, scenario)
                break

        # Also check for individual parameter sheets
        all_sheets = set(wb.sheetnames)
        exclude_sheets = set(param_sheet_names + ['sets', 'set', 'Sets', 'Set'] + list(scenario.sets.keys()))
        potential_param_sheets = all_sheets - exclude_sheets

        param_sheets = [sheet_name for sheet_name in potential_param_sheets if sheet_name not in scenario.sets]
        total_param_sheets = len(param_sheets)

        for i, sheet_name in enumerate(param_sheets):
            if progress_callback and total_param_sheets > 0:
                progress = 50 + int((i / total_param_sheets) * 50)  # Progress from 50% to 100%
                progress_callback(progress, f"Parsing parameter: {sheet_name}")

            sheet = wb[sheet_name]
            self._parse_individual_parameter_sheet(sheet, sheet_name, scenario)

    def _parse_parameters_sheet(self, sheet: Any, scenario: ScenarioData) -> None:
        """
        Parse a combined parameters sheet.

        Args:
            sheet: Openpyxl worksheet object containing combined parameter data
            scenario: ScenarioData object to populate
        """
        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value).strip())
            else:
                break

        if len(headers) < 2:
            return  # Not enough columns

        # Parse parameter data
        current_param = None
        param_data = []

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue

            param_name = str(row[0]).strip()

            if param_name != current_param:
                # Save previous parameter if exists
                if current_param and param_data:
                    parameter = create_parameter_from_data(current_param, param_data, headers[1:])
                    if parameter:
                        scenario.add_parameter(parameter)

                # Start new parameter
                current_param = param_name
                param_data = []

            # Add row data (skip parameter name column for data)
            if len(row) > 1:
                param_data.append(row[1:])

        # Save last parameter
        if current_param and param_data:
            parameter = create_parameter_from_data(current_param, param_data, headers[1:])
            if parameter:
                scenario.add_parameter(parameter)

    def _parse_individual_parameter_sheet(self, sheet: Any, param_name: str, scenario: ScenarioData) -> None:
        """
        Parse an individual parameter sheet.

        Args:
            sheet: Openpyxl worksheet object
            param_name: Name of the parameter to parse
            scenario: ScenarioData object to populate
        """
        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value).strip())
            else:
                break

        if not headers:
            return

        # Collect all data rows
        param_data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row and any(cell is not None for cell in row):
                param_data.append(row)

        if param_data:
            parameter = create_parameter_from_data(param_name, param_data, headers)
            if parameter:
                scenario.add_parameter(parameter)

    # Keep backward compatibility - get_current_scenario is now inherited
    # All other inherited methods from BaseDataManager are available
