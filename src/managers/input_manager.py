"""
Input Manager - handles loading and parsing of message_ix Excel input files
"""

import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from typing import Optional, List, Callable

from core.data_models import ScenarioData, Parameter


class InputManager:
    """Manages loading and parsing of message_ix input Excel files"""

    def __init__(self):
        self.scenarios: List[ScenarioData] = []
        self.loaded_file_paths: List[str] = []

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
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")

        print(f"Loading input file: {file_path}")

        # Create new scenario data
        scenario = ScenarioData()

        try:
            # Initialize progress
            if progress_callback:
                progress_callback(0, "Loading workbook...")

            # Load workbook
            wb = load_workbook(file_path, data_only=True)

            if progress_callback:
                progress_callback(10, "Workbook loaded, parsing sets...")

            # Parse sets
            self._parse_sets(wb, scenario, progress_callback)

            if progress_callback:
                progress_callback(40, "Sets parsed, parsing parameters...")

            # Parse parameters
            self._parse_parameters(wb, scenario, progress_callback)

            # Store reference
            self.scenarios.append(scenario)
            self.loaded_file_paths.append(file_path)

            if progress_callback:
                progress_callback(100, "Loading complete")

            print(f"Successfully loaded {len(scenario.parameters)} parameters and {len(scenario.sets)} sets")

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise ValueError(f"Error parsing Excel file: {str(e)}")

        return scenario

    def _parse_sets(self, wb, scenario: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse sets from the workbook"""
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
                    self._create_parameter(scenario, current_param, param_data, headers[1:])

                # Start new parameter
                current_param = param_name
                param_data = []

            # Add row data (skip parameter name column for data)
            if len(row) > 1:
                param_data.append(row[1:])

        # Save last parameter
        if current_param and param_data:
            self._create_parameter(scenario, current_param, param_data, headers[1:])

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
            self._create_parameter(scenario, param_name, param_data, headers)

    def _create_parameter(self, scenario: ScenarioData, param_name: str,
                         param_data: List, headers: List[str]):
        """Create a Parameter object from parsed data"""
        try:
            # Check for valid input data - handle pandas Series ambiguity
            if param_data is None or headers is None or len(param_data) == 0 or len(headers) == 0:
                return

            # Convert to DataFrame
            df = pd.DataFrame(param_data, columns=headers)
            # Ensure None values are converted to NaN to preserve empty cells
            df = df.replace({None: np.nan})

            # Convert any integer columns that contain NaN to float to preserve NaN values
            for col in df.columns:
                col_data = df[col]
                if hasattr(col_data, 'dtype') and col_data.dtype in ['int64', 'int32', 'int16', 'int8'] and col_data.isna().any():
                    df[col] = col_data.astype('float64')

            # Convert columns that are all zeros to NaN (treat as empty)
            for col in df.columns:
                col_data = df[col]
                if hasattr(col_data, 'dtype') and col_data.dtype in ['int64', 'int32', 'int16', 'int8', 'float64', 'float32']:
                    # Check if all non-NaN values are 0
                    non_nan_values = col_data.dropna()
                    if len(non_nan_values) > 0 and (non_nan_values == 0).all():
                        df[col] = col_data.replace(0, np.nan)

            # Remove any completely empty rows
            df = df.dropna(how='all')

            if df.empty:
                return

            # Determine dimensions and value column
            # Assume last column is the value, others are dimensions
            if len(headers) > 1:
                dims = headers[:-1]
                value_col = headers[-1]
            else:
                dims = []
                value_col = headers[0] if headers else 'value'

            # Basic metadata
            metadata = {
                'units': 'N/A',
                'desc': f'Parameter {param_name}',
                'dims': dims,
                'value_column': value_col,
                'shape': df.shape
            }

            # Create parameter object
            parameter = Parameter(param_name, df, metadata)
            # Update shape to reflect the reset_index() operation
            parameter.metadata['shape'] = parameter.df.shape
            scenario.add_parameter(parameter)

        except Exception as e:
            print(f"Warning: Could not create parameter {param_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_current_scenario(self) -> Optional[ScenarioData]:
        """Get the combined scenario from all loaded files"""
        if not self.scenarios:
            return None

        if len(self.scenarios) == 1:
            return self.scenarios[0]

        # Combine multiple scenarios
        combined = ScenarioData()
        for scenario in self.scenarios:
            # Merge sets (avoid duplicates)
            for set_name, set_data in scenario.sets.items():
                if set_name not in combined.sets:
                    combined.sets[set_name] = set_data.copy()
                else:
                    # Merge set elements - concatenate Series and drop duplicates
                    combined.sets[set_name] = pd.concat([combined.sets[set_name], set_data]).drop_duplicates().reset_index(drop=True)

            # Merge parameters
            for param_name, param in scenario.parameters.items():
                if param_name not in combined.parameters:
                    combined.parameters[param_name] = param
                else:
                    # Merge parameter data (append rows)
                    existing_data = combined.parameters[param_name].df
                    new_data = param.df
                    combined.parameters[param_name].df = pd.concat([existing_data, new_data], ignore_index=True)

        return combined

    def get_loaded_file_paths(self) -> List[str]:
        """Get list of all loaded file paths"""
        return self.loaded_file_paths.copy()

    def get_scenario_by_file_path(self, file_path: str) -> Optional[ScenarioData]:
        """Get a specific scenario by file path"""
        if file_path in self.loaded_file_paths:
            index = self.loaded_file_paths.index(file_path)
            return self.scenarios[index]
        return None

    def clear_scenarios(self):
        """Clear all loaded scenarios"""
        self.scenarios.clear()
        self.loaded_file_paths.clear()

    def get_parameter_names(self) -> List[str]:
        """Get list of parameter names from current scenario"""
        scenario = self.get_current_scenario()
        if scenario:
            return scenario.get_parameter_names()
        return []

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get a parameter by name"""
        scenario = self.get_current_scenario()
        if scenario:
            return scenario.get_parameter(name)
        return None

    def validate_scenario(self) -> dict:
        """
        Validate the loaded scenario for common issues

        Returns:
            dict: Validation results with 'valid' boolean and 'issues' list
        """
        scenario = self.get_current_scenario()
        if not scenario:
            return {'valid': False, 'issues': ['No scenario loaded']}

        issues = []

        # Check for empty scenario
        if not scenario.parameters and not scenario.sets:
            issues.append('Scenario contains no parameters or sets')

        # Check parameters
        for param_name, parameter in scenario.parameters.items():
            param_issues = self._validate_parameter(parameter)
            issues.extend([f"Parameter '{param_name}': {issue}" for issue in param_issues])

        # Check sets
        for set_name, set_values in scenario.sets.items():
            if set_values.empty:
                issues.append(f"Set '{set_name}' is empty")
            elif set_values.duplicated().any():
                issues.append(f"Set '{set_name}' contains duplicate values")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'summary': {
                'parameters': len(scenario.parameters),
                'sets': len(scenario.sets),
                'total_data_points': sum(len(p.df) for p in scenario.parameters.values())
            }
        }

    def _validate_parameter(self, parameter: Parameter) -> list:
        """Validate a single parameter for common issues"""
        issues = []

        # Check for empty dataframe
        if parameter.df.empty:
            issues.append('Parameter dataframe is empty')
            return issues

        # Check for missing values in critical columns
        value_col = parameter.metadata.get('value_column', parameter.df.columns[-1] if len(parameter.df.columns) > 0 else None)
        if value_col and value_col in parameter.df.columns:
            na_count = parameter.df[value_col].isna().sum()
            if na_count > 0:
                issues.append(f"{na_count} missing values in value column '{value_col}'")

        # Check dimension consistency
        dims = parameter.metadata.get('dims', [])
        if dims and len(dims) > 0:  # Explicit check to avoid pandas Series ambiguity
            missing_dims = [dim for dim in dims if dim not in parameter.df.columns]
            if missing_dims:
                issues.append(f"Missing dimension columns: {missing_dims}")

        # Check for duplicate dimension combinations
        if dims and len(dims) > 0 and all(dim in parameter.df.columns for dim in dims):
            dim_cols = parameter.df[dims]
            duplicates = dim_cols.duplicated().sum()
            if duplicates > 0:
                issues.append(f"{duplicates} duplicate dimension combinations found")

        return issues
