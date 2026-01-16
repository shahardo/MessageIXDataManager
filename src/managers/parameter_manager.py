"""
Parameter Manager for MessageIX Data Manager.

Handles adding and removing parameters from input files with undo/redo support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import os


class Command(ABC):
    """Base class for commands that support do/undo operations."""

    def __init__(self, description: str):
        self.description = description

    @abstractmethod
    def do(self) -> bool:
        """Execute the command. Returns True if successful."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command. Returns True if successful."""
        pass


class AddParameterCommand(Command):
    """Command to add a parameter to an input file."""

    def __init__(self, file_path: str, parameter_name: str, parameter_data: pd.DataFrame,
                 parameter_type: str, index_columns: List[str]):
        super().__init__(f"Add parameter '{parameter_name}' to {os.path.basename(file_path)}")
        self.file_path = file_path
        self.parameter_name = parameter_name
        self.parameter_data = parameter_data.copy()
        self.parameter_type = parameter_type
        self.index_columns = index_columns.copy()
        self.backup_data = None  # Will store existing data if parameter already exists

    def do(self) -> bool:
        """Add the parameter to the file."""
        try:
            # Load existing file
            if os.path.exists(self.file_path):
                # For now, assume Excel format - can extend later
                existing_data = pd.read_excel(self.file_path, sheet_name=None)
            else:
                existing_data = {}

            # Check if parameter already exists
            if self.parameter_name in existing_data:
                self.backup_data = existing_data[self.parameter_name].copy()
            else:
                self.backup_data = None

            # Add/update the parameter sheet
            existing_data[self.parameter_name] = self.parameter_data

            # Save back to file
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in existing_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True
        except Exception as e:
            print(f"Error adding parameter: {e}")
            return False

    def undo(self) -> bool:
        """Remove the added parameter or restore previous version."""
        try:
            # Load current file
            existing_data = pd.read_excel(self.file_path, sheet_name=None)

            if self.backup_data is not None:
                # Restore previous version
                existing_data[self.parameter_name] = self.backup_data
            else:
                # Remove the parameter entirely
                if self.parameter_name in existing_data:
                    del existing_data[self.parameter_name]

            # Save back to file
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in existing_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True
        except Exception as e:
            print(f"Error undoing add parameter: {e}")
            return False


class RemoveParameterCommand(Command):
    """Command to remove a parameter from an input file."""

    def __init__(self, file_path: str, parameter_name: str):
        super().__init__(f"Remove parameter '{parameter_name}' from {os.path.basename(file_path)}")
        self.file_path = file_path
        self.parameter_name = parameter_name
        self.backup_data = None  # Will store the data being removed

    def do(self) -> bool:
        """Remove the parameter from the file."""
        try:
            # Load existing file
            existing_data = pd.read_excel(self.file_path, sheet_name=None)

            # Check if parameter exists
            if self.parameter_name not in existing_data:
                return False  # Nothing to remove

            # Backup the data
            self.backup_data = existing_data[self.parameter_name].copy()

            # Remove the parameter
            del existing_data[self.parameter_name]

            # Save back to file
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in existing_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True
        except Exception as e:
            print(f"Error removing parameter: {e}")
            return False

    def undo(self) -> bool:
        """Restore the removed parameter."""
        try:
            # Load current file
            existing_data = pd.read_excel(self.file_path, sheet_name=None)

            # Restore the parameter if backup exists
            if self.backup_data is not None:
                existing_data[self.parameter_name] = self.backup_data

            # Save back to file
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in existing_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

            return True
        except Exception as e:
            print(f"Error undoing remove parameter: {e}")
            return False


class ParameterManager:
    """Manages parameter operations on input files."""

    def __init__(self):
        self.valid_parameters = self._load_valid_parameters()

    def _load_valid_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Load the list of valid MessageIX parameters."""
        # This would ideally be loaded from a configuration file or database
        # For now, using the parameters from devplan
        return {
            'input': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'mode', 'node_origin', 'commodity', 'level', 'time', 'time_origin'],
                'type': 'Numeric'
            },
            'output': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'mode', 'node_dest', 'commodity', 'level', 'time', 'time_dest'],
                'type': 'Numeric'
            },
            'capacity_factor': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'time'],
                'type': 'Numeric'
            },
            'technical_lifetime': {
                'index_dims': ['node_loc', 'technology', 'year_vtg'],
                'type': 'Numeric'
            },
            'duration_period': {
                'index_dims': ['year'],
                'type': 'Numeric'
            },
            'duration_time': {
                'index_dims': ['time'],
                'type': 'Numeric'
            },
            'construction_time': {
                'index_dims': ['node_loc', 'technology', 'year_vtg'],
                'type': 'Numeric'
            },
            'inv_cost': {
                'index_dims': ['node_loc', 'technology', 'year_vtg'],
                'type': 'Currency'
            },
            'fix_cost': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act'],
                'type': 'Currency'
            },
            'var_cost': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'mode', 'time'],
                'type': 'Currency'
            },
            'interest_rate': {
                'index_dims': ['year'],
                'type': 'Percentage'
            },
            'tax_emission': {
                'index_dims': ['node_loc', 'emission', 'type_emission', 'year'],
                'type': 'Currency'
            },
            'tax_var_cost': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'mode', 'time'],
                'type': 'Currency'
            },
            'demand': {
                'index_dims': ['node', 'commodity', 'level', 'year', 'time'],
                'type': 'Energy'
            },
            'resource_volume': {
                'index_dims': ['node', 'commodity', 'grade'],
                'type': 'Energy'
            },
            'resource_cost': {
                'index_dims': ['node', 'commodity', 'grade', 'year'],
                'type': 'Currency'
            },
            'bound_total_capacity_up': {
                'index_dims': ['node_loc', 'technology', 'year_act'],
                'type': 'Capacity'
            },
            'bound_activity_up': {
                'index_dims': ['node_loc', 'technology', 'year_act', 'mode', 'time'],
                'type': 'Activity'
            },
            'bound_new_capacity_up': {
                'index_dims': ['node_loc', 'technology', 'year_vtg'],
                'type': 'Capacity'
            },
            'emission_factor': {
                'index_dims': ['node_loc', 'technology', 'year_vtg', 'year_act', 'mode', 'emission'],
                'type': 'Mass/Energy'
            },
            'bound_emission': {
                'index_dims': ['node_loc', 'emission', 'type_emission', 'year'],
                'type': 'Mass'
            },
            'emission_scaling': {
                'index_dims': ['type_emission', 'emission'],
                'type': 'Numeric'
            }
        }

    def get_valid_parameters(self) -> List[str]:
        """Get list of valid parameter names."""
        return list(self.valid_parameters.keys())

    def get_parameter_info(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a parameter."""
        return self.valid_parameters.get(parameter_name)

    def validate_parameter_data(self, parameter_name: str, data: pd.DataFrame) -> List[str]:
        """Validate parameter data against MessageIX requirements."""
        errors = []

        if parameter_name not in self.valid_parameters:
            errors.append(f"Parameter '{parameter_name}' is not a valid MessageIX parameter")
            return errors

        param_info = self.valid_parameters[parameter_name]
        required_dims = param_info['index_dims']

        # Check if all required index columns are present
        missing_cols = [col for col in required_dims if col not in data.columns]
        if missing_cols:
            errors.append(f"Missing required index columns: {missing_cols}")

        # Check for duplicate index combinations
        if len(data) != len(data.drop_duplicates(subset=required_dims)):
            errors.append("Duplicate index combinations found")

        return errors

    def create_add_parameter_command(self, file_path: str, parameter_name: str,
                                   parameter_data: pd.DataFrame) -> Optional[AddParameterCommand]:
        """Create an AddParameterCommand after validation."""
        # Validate parameter
        errors = self.validate_parameter_data(parameter_name, parameter_data)
        if errors:
            raise ValueError(f"Parameter validation failed: {'; '.join(errors)}")

        param_info = self.get_parameter_info(parameter_name)
        if not param_info:
            raise ValueError(f"Unknown parameter: {parameter_name}")

        return AddParameterCommand(file_path, parameter_name, parameter_data,
                                 param_info['type'], param_info['index_dims'])

    def create_remove_parameter_command(self, file_path: str, parameter_name: str) -> RemoveParameterCommand:
        """Create a RemoveParameterCommand."""
        return RemoveParameterCommand(file_path, parameter_name)

    def get_parameters_in_file(self, file_path: str) -> List[str]:
        """Get list of parameters currently in the file."""
        try:
            if not os.path.exists(file_path):
                return []

            data = pd.read_excel(file_path, sheet_name=None)
            return list(data.keys())
        except Exception:
            return []
