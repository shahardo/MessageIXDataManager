"""
Parsing Strategies - Strategy pattern for parsing different Excel sheet types
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
import pandas as pd
import logging

from core.data_models import ScenarioData
from utils.parameter_factory import parameter_factory_registry
from utils.error_handler import ErrorHandler, SafeOperation


class ParsingStrategy(ABC):
    """Abstract base class for parsing strategies"""

    def __init__(self):
        self.error_handler = ErrorHandler()
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def parse_sheet(self, sheet: Any, scenario: ScenarioData, sheet_name: str,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Parse a specific sheet type"""
        pass

    @abstractmethod
    def can_parse_sheet(self, sheet: Any, sheet_name: str) -> bool:
        """Determine if this strategy can parse the given sheet"""
        pass


class SetParsingStrategy(ParsingStrategy):
    """Strategy for parsing set sheets"""

    def parse_sheet(self, sheet: Any, scenario: ScenarioData, sheet_name: str,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Parse a set sheet"""
        with SafeOperation(f"parsing set sheet: {sheet_name}", self.error_handler, self.logger):
            if sheet_name.lower() in ['sets', 'set']:
                self._parse_combined_sets_sheet(sheet, scenario)
            else:
                self._parse_individual_set_sheet(sheet, sheet_name, scenario)

    def can_parse_sheet(self, sheet: Any, sheet_name: str) -> bool:
        """Check if this is a set sheet"""
        # Common set sheet names
        set_sheet_names = ['sets', 'set', 'Sets', 'Set']
        if sheet_name in set_sheet_names:
            return True

        # Individual set sheets (common MESSAGEix sets)
        potential_set_sheets = ['node', 'technology', 'commodity', 'level', 'year', 'mode', 'time']
        if sheet_name in potential_set_sheets:
            return True

        return False

    def _parse_combined_sets_sheet(self, sheet: Any, scenario: ScenarioData) -> None:
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

    def _parse_individual_set_sheet(self, sheet: Any, set_name: str, scenario: ScenarioData) -> None:
        """Parse an individual set sheet"""
        set_values = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] is not None:
                val_str = str(row[0]).strip()
                if val_str and val_str not in set_values:
                    set_values.append(val_str)
        if set_values:
            scenario.sets[set_name] = pd.Series(set_values)


class ParameterParsingStrategy(ParsingStrategy):
    """Strategy for parsing parameter sheets"""

    def __init__(self, param_type: str = 'input'):
        super().__init__()
        self.param_type = param_type

    def parse_sheet(self, sheet: Any, scenario: ScenarioData, sheet_name: str,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Parse a parameter sheet"""
        with SafeOperation(f"parsing parameter sheet: {sheet_name}", self.error_handler, self.logger):
            if sheet_name.lower() in ['parameters', 'parameter', 'data']:
                self._parse_combined_parameters_sheet(sheet, scenario)
            else:
                self._parse_individual_parameter_sheet(sheet, sheet_name, scenario)

    def can_parse_sheet(self, sheet: Any, sheet_name: str) -> bool:
        """Check if this is a parameter sheet"""
        # Common parameter sheet names
        param_sheet_names = ['parameters', 'parameter', 'Parameters', 'Parameter', 'data']
        if sheet_name in param_sheet_names:
            return True

        # For individual parameter sheets, check if it contains parameter-like data
        return self._is_parameter_sheet(sheet)

    def _is_parameter_sheet(self, sheet: Any) -> bool:
        """Check if sheet contains parameter-like data"""
        try:
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) < 2:
                return False

            # Check for headers
            headers = rows[0]
            if not headers or not any(isinstance(h, str) and h.strip() for h in headers):
                return False

            # Check for data rows with mixed types (typical of parameters)
            data_rows = rows[1:]
            has_mixed_data = False
            for row in data_rows[:5]:  # Check first few rows
                if row and len(row) > 1:
                    has_strings = any(isinstance(cell, str) and cell.strip() for cell in row)
                    has_numbers = any(isinstance(cell, (int, float)) and not pd.isna(cell) for cell in row)
                    if has_strings and has_numbers:
                        has_mixed_data = True
                        break

            return has_mixed_data

        except Exception:
            return False

    def _parse_combined_parameters_sheet(self, sheet: Any, scenario: ScenarioData) -> None:
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
                    parameter = parameter_factory_registry.create_parameter(
                        self.param_type, current_param, param_data, headers[1:]
                    )
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
            parameter = parameter_factory_registry.create_parameter(
                self.param_type, current_param, param_data, headers[1:]
            )
            if parameter:
                scenario.add_parameter(parameter)

    def _parse_individual_parameter_sheet(self, sheet: Any, param_name: str, scenario: ScenarioData) -> None:
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
            parameter = parameter_factory_registry.create_parameter(
                self.param_type, param_name, param_data, headers
            )
            if parameter:
                scenario.add_parameter(parameter)


class ResultParsingStrategy(ParsingStrategy):
    """Strategy for parsing result sheets (variables and equations)"""

    def parse_sheet(self, sheet: Any, scenario: ScenarioData, sheet_name: str,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Parse a result sheet"""
        with SafeOperation(f"parsing result sheet: {sheet_name}", self.error_handler, self.logger):
            self._parse_result_sheet(sheet, scenario, sheet_name)

    def can_parse_sheet(self, sheet: Any, sheet_name: str) -> bool:
        """Check if this is a result sheet"""
        # Result sheets typically start with var_ or equ_
        if sheet_name.startswith(('var_', 'equ_')):
            return True

        # Check if it contains result-like data
        return self._is_result_sheet(sheet)

    def _is_result_sheet(self, sheet: Any) -> bool:
        """Check if sheet contains result-like data (not parameter-like)"""
        try:
            rows = list(sheet.iter_rows(values_only=True))
            if len(rows) < 2:
                return False

            # Check for headers
            headers = rows[0]
            if not headers or not any(isinstance(h, str) and h.strip() for h in headers):
                return False

            # Check for numeric data (typical of results)
            has_numeric_data = False
            has_mixed_data = False

            for row in rows[1:]:
                # Check for numeric values
                if any(isinstance(cell, (int, float)) and not pd.isna(cell) for cell in row):
                    has_numeric_data = True

                # Check for mixed data types (strings + numbers in same row)
                has_strings = any(isinstance(cell, str) and cell.strip() for cell in row)
                has_numbers = any(isinstance(cell, (int, float)) and not pd.isna(cell) for cell in row)
                if has_strings and has_numbers:
                    has_mixed_data = True
                    break

            # Result sheets typically have numeric data but not mixed types
            # (parameters have both strings and numbers in the same row)
            return has_numeric_data and not has_mixed_data

        except Exception:
            return False

    def _parse_result_sheet(self, sheet: Any, scenario: ScenarioData, sheet_name: str) -> None:
        """Parse individual result sheet"""
        # Get all headers (including None)
        all_headers = [cell.value for cell in sheet[1]]

        # Check if first column should be included as year column
        include_year_column = False
        if len(all_headers) > 0 and all_headers[0] is None:
            # Check if first column data looks like years
            year_values = []
            for row in sheet.iter_rows(min_row=2, max_row=min(10, sheet.max_row), values_only=True):
                if row and len(row) > 0 and row[0] is not None:
                    try:
                        year_val = float(row[0])
                        if 1900 <= year_val <= 2100:  # Reasonable year range
                            year_values.append(year_val)
                    except (ValueError, TypeError):
                        pass

            # Include as year column if we found year-like values
            if len(year_values) >= 3:  # At least a few years
                include_year_column = True

        # Filter out None headers and get their indices
        headers = []
        valid_indices = []
        for i, header in enumerate(all_headers):
            if header is not None:
                headers.append(str(header))
                valid_indices.append(i)
            elif i == 0 and include_year_column:
                # Include first column as year column
                headers.append("year")
                valid_indices.append(i)

        if not headers:
            return

        # Make headers unique
        unique_headers = []
        counts = {}
        for col in headers:
            if col in counts:
                counts[col] += 1
                unique_headers.append(f"{col}.{counts[col]-1}")
            else:
                counts[col] = 1
                unique_headers.append(col)
        headers = unique_headers

        # Parse data, keeping only columns with valid headers
        data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row and any(cell is not None for cell in row):
                # Filter row to only include valid columns
                filtered_row = [row[i] for i in valid_indices if i < len(row)]
                if filtered_row:  # Only add if we have some valid data
                    data.append(filtered_row)

        if data and len(data) > 0:
            # Determine result type
            result_type = 'variable' if sheet_name.startswith('var_') else 'equation'

            # Use parameter factory to create the parameter
            metadata_overrides = {'result_type': result_type}
            parameter = parameter_factory_registry.create_parameter(
                'result', sheet_name, data, headers, metadata_overrides
            )
            if parameter:
                scenario.add_parameter(parameter)


class ExcelParser:
    """Parser that uses different strategies based on sheet type"""

    def __init__(self):
        # Order matters: more specific strategies first
        self.strategies = [
            SetParsingStrategy(),
            ResultParsingStrategy(),  # Check results before parameters
            ParameterParsingStrategy('input')
        ]

    def parse_workbook(self, wb: Any, scenario: ScenarioData,
                      progress_callback: Optional[Callable[[int, str], None]] = None) -> None:
        """Parse entire workbook using appropriate strategies"""
        total_sheets = len(wb.sheetnames)

        for i, sheet_name in enumerate(wb.sheetnames):
            if progress_callback:
                progress = int((i / total_sheets) * 100)
                progress_callback(progress, f"Parsing sheet: {sheet_name}")

            sheet = wb[sheet_name]
            strategy = self._get_strategy_for_sheet(sheet, sheet_name)

            if strategy:
                strategy.parse_sheet(sheet, scenario, sheet_name, progress_callback)

    def _get_strategy_for_sheet(self, sheet: Any, sheet_name: str) -> Optional[ParsingStrategy]:
        """Get the appropriate strategy for a sheet"""
        for strategy in self.strategies:
            if strategy.can_parse_sheet(sheet, sheet_name):
                return strategy
        return None
