"""
Input Manager - handles loading and parsing of message_ix Excel input files
"""

import os
import pandas as pd
import numpy as np
import logging
from openpyxl import load_workbook
from typing import Optional, List, Callable

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager
from utils.parameter_utils import create_parameter_from_data
from utils.error_handler import ErrorHandler, SafeOperation


class InputManager(BaseDataManager):
    """Manages loading and parsing of message_ix input Excel files"""

    def load_excel_file(self, file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScenarioData:
        """
        Load and parse a message_ix Excel input file

        Args:
            file_path: Path to the Excel file
            progress_callback: Optional callback function for progress updates (value, message)

        Returns:
            ScenarioData object containing parsed data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        return self.load_file(file_path, progress_callback)

    def _parse_workbook(self, wb, scenario: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse workbook for input data - implements abstract method"""
        if progress_callback:
            progress_callback(10, "Parsing sets...")

        # Parse sets
        self._parse_sets(wb, scenario, progress_callback)

        if progress_callback:
            progress_callback(40, "Sets parsed, parsing parameters...")

        # Parse parameters
        self._parse_parameters(wb, scenario, progress_callback)

    def _parse_sets(self, wb, scenario: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse sets from the workbook"""
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

    def _parse_sets_sheet(self, sheet, scenario: ScenarioData):
        """Parse a combined sets sheet"""
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

    def _parse_individual_set_sheet(self, sheet, set_name: str, scenario: ScenarioData):
        """Parse an individual set sheet"""
        set_values = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is not None:
                val_str = str(row[0]).strip()
                if val_str and val_str not in set_values:
                    set_values.append(val_str)
        if set_values:
            scenario.sets[set_name] = pd.Series(set_values)

    def _parse_parameters(self, wb, scenario: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse parameters from the workbook"""
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

    def _parse_parameters_sheet(self, sheet, scenario: ScenarioData):
        """Parse a combined parameters sheet"""
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

    def _parse_individual_parameter_sheet(self, sheet, param_name: str, scenario: ScenarioData):
        """Parse an individual parameter sheet"""
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
