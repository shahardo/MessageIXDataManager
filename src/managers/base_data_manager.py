"""
Base Data Manager - Abstract base class for data managers
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from openpyxl import load_workbook

from core.data_models import ScenarioData, Parameter
from utils.error_handler import ErrorHandler, SafeOperation


class BaseDataManager(ABC):
    """Base class for data managers handling Excel file loading and scenario management"""

    def __init__(self):
        self.scenarios: List[ScenarioData] = []
        self.loaded_file_paths: List[str] = []

    def load_file(self, file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScenarioData:
        """
        Common file loading logic with error handling and progress reporting

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
            raise FileNotFoundError(f"File not found: {file_path}")

        logger = logging.getLogger(__name__)
        error_handler = ErrorHandler()

        print(f"Loading file: {file_path}")

        # Create new scenario data
        scenario = ScenarioData()

        # Use SafeOperation for comprehensive error handling
        with SafeOperation(f"file loading: {os.path.basename(file_path)}", error_handler, logger) as safe_op:
            # Initialize progress
            if progress_callback:
                progress_callback(0, "Loading workbook...")

            # Load workbook
            wb = load_workbook(file_path, data_only=True)

            if progress_callback:
                progress_callback(20, "Workbook loaded, parsing data...")

            # Delegate to subclass for specific parsing
            self._parse_workbook(wb, scenario, progress_callback)

            # Store reference
            self.scenarios.append(scenario)
            self.loaded_file_paths.append(file_path)

            if progress_callback:
                progress_callback(100, "Loading complete")

            print(f"Successfully loaded {len(scenario.parameters)} parameters and {len(scenario.sets)} sets")

        # If error occurred in SafeOperation, re-raise with user-friendly message
        if safe_op.error_occurred:
            raise ValueError(safe_op._handle_error(RuntimeError("File loading failed")))

        return scenario

    @abstractmethod
    def _parse_workbook(self, wb, scenario: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Subclass-specific parsing logic"""
        pass

    def get_current_scenario(self) -> Optional[ScenarioData]:
        """
        Get combined scenario from all loaded files

        Returns:
            Combined ScenarioData or None if no scenarios loaded
        """
        if not self.scenarios:
            return None

        if len(self.scenarios) == 1:
            return self.scenarios[0]

        # Combine multiple scenarios
        combined = ScenarioData()
        for scenario in self.scenarios:
            self._merge_scenario(combined, scenario)
        return combined

    def _merge_scenario(self, combined: ScenarioData, scenario: ScenarioData):
        """Merge scenario data - can be overridden by subclasses"""
        import pandas as pd

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
                # Create a copy of the parameter with copied DataFrame
                param_copy = type(param)(param.name, param.df.copy(), param.metadata.copy())
                combined.parameters[param_name] = param_copy
            else:
                # Merge parameter data (append rows)
                existing_data = combined.parameters[param_name].df
                new_data = param.df
                combined.parameters[param_name].df = pd.concat([existing_data, new_data], ignore_index=True)

    def get_loaded_file_paths(self) -> List[str]:
        """Get list of all loaded file paths"""
        return self.loaded_file_paths.copy()

    def get_number_of_scenarios(self) -> int:
        """Get the number of loaded scenarios"""
        return len(self.scenarios)

    def get_scenario_by_index(self, index: int) -> Optional[ScenarioData]:
        """Get a scenario by index"""
        if 0 <= index < len(self.scenarios):
            return self.scenarios[index]
        return None

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

    def get_parameter(self, name: str) -> Optional['Parameter']:
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

    def _validate_parameter(self, parameter) -> list:
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

    def remove_file(self, file_path: str) -> bool:
        """
        Remove a loaded file and its associated scenario data

        Args:
            file_path: Path to the file to remove

        Returns:
            True if file was found and removed, False otherwise
        """
        if file_path in self.loaded_file_paths:
            # Find the index of the file
            index = self.loaded_file_paths.index(file_path)

            # Remove from both lists
            self.loaded_file_paths.pop(index)
            self.scenarios.pop(index)

            print(f"Removed file: {file_path}")
            return True

        return False
