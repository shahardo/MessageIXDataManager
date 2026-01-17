"""Parameter Manager for MessageIX Data Manager.

Provides parameter definitions, validation, and factory methods for creating new parameter DataFrames.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from core.message_ix_schema import MESSAGE_IX_PARAMETERS, PARAMETER_CATEGORIES

class ParameterManager:
    """Manages parameter definitions, validation, and factory methods for creating new parameter DataFrames."""

    def __init__(self):
        # Use the canonical MESSAGEix schema from message_ix_schema.py
        self.valid_parameters = MESSAGE_IX_PARAMETERS
        self.parameter_categories = PARAMETER_CATEGORIES

    def get_valid_parameters(self) -> List[str]:
        """Get list of valid parameter names."""
        return list(self.valid_parameters.keys())

    def get_parameter_info(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a parameter."""
        return self.valid_parameters.get(parameter_name)

    def get_parameter_categories(self) -> Dict[str, List[str]]:
        """Get categorized parameter list."""
        return self.parameter_categories

    def get_parameters_by_category(self, category: str) -> List[str]:
        """Get parameters in a specific category."""
        return self.parameter_categories.get(category, [])

    def create_empty_parameter_dataframe(self, parameter_name: str) -> pd.DataFrame:
        """Create an empty DataFrame with correct columns for the parameter."""
        if parameter_name not in self.valid_parameters:
            raise ValueError(f"Unknown parameter: {parameter_name}")

        param_info = self.valid_parameters[parameter_name]
        dims = param_info['dims']

        # Create empty DataFrame with index dimensions + value column
        columns = dims + ['value']
        return pd.DataFrame(columns=columns)

    def validate_parameter_data(self, parameter_name: str, data: pd.DataFrame) -> List[str]:
        """Validate parameter data against MessageIX requirements."""
        errors = []

        if parameter_name not in self.valid_parameters:
            errors.append(f"Parameter '{parameter_name}' is not a valid MessageIX parameter")
            return errors

        param_info = self.valid_parameters[parameter_name]
        required_dims = param_info['dims']

        # Check if all required index columns are present
        missing_cols = [col for col in required_dims if col not in data.columns]
        if missing_cols:
            errors.append(f"Missing required index columns: {missing_cols}")

        # Check for duplicate index combinations
        if len(data) != len(data.drop_duplicates(subset=required_dims)):
            errors.append("Duplicate index combinations found")

        return errors

    def get_missing_parameters(self, existing_parameters: List[str]) -> List[str]:
        """Get list of valid parameters that are not in the existing list."""
        existing_set = set(existing_parameters)
        all_valid = set(self.get_valid_parameters())
        return list(all_valid - existing_set)

    def get_parameter_description(self, parameter_name: str) -> str:
        """Get the description for a parameter."""
        param_info = self.get_parameter_info(parameter_name)
        return param_info['description'] if param_info else "Unknown parameter"

    def get_parameter_dimensions(self, parameter_name: str) -> List[str]:
        """Get the dimension names for a parameter."""
        param_info = self.get_parameter_info(parameter_name)
        return param_info['dims'] if param_info else []
