"""
Command classes for undo/redo operations in MessageIX Data Manager.

These commands encapsulate operations that can be undone and redone.
"""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


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


class EditCellCommand(Command):
    """Command to edit a single cell in a parameter."""

    def __init__(self, scenario, parameter_name: str, row: int, column_name: str, old_value: Any, new_value: Any):
        super().__init__(f"Edit cell in {parameter_name}")
        self.scenario = scenario
        self.parameter_name = parameter_name
        self.row = row
        self.column_name = column_name
        self.old_value = old_value
        self.new_value = new_value

    def do(self) -> bool:
        """Apply the cell edit."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            parameter.df.loc[self.row, self.column_name] = self.new_value
            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo the cell edit."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            parameter.df.loc[self.row, self.column_name] = self.old_value
            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False


class EditPivotCommand(Command):
    """Command to edit data in pivot/advanced view mode."""

    def __init__(self, scenario, parameter_name: str, year: int, technology: str, old_value: Any, new_value: Any,
                 year_col: str, tech_col: str, value_col: str):
        super().__init__(f"Edit {technology} in {year} ({parameter_name})")
        self.scenario = scenario
        self.parameter_name = parameter_name
        self.year = year
        self.technology = technology
        self.old_value = old_value
        self.new_value = new_value
        self.year_col = year_col
        self.tech_col = tech_col
        self.value_col = value_col

    def do(self) -> bool:
        """Apply the pivot edit."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            # Find the row that matches year and technology
            mask = (parameter.df[self.year_col] == self.year) & (parameter.df[self.tech_col] == self.technology)
            parameter.df.loc[mask, self.value_col] = self.new_value
            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo the pivot edit."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            # Find the row that matches year and technology
            mask = (parameter.df[self.year_col] == self.year) & (parameter.df[self.tech_col] == self.technology)
            parameter.df.loc[mask, self.value_col] = self.old_value
            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False


class PasteColumnCommand(Command):
    """Command to paste data into an entire column."""

    def __init__(self, scenario, parameter_name: str, column_name: str, row_changes: dict):
        """
        Initialize paste column command.

        Args:
            scenario: The scenario containing the parameter
            parameter_name: Name of the parameter being modified
            column_name: Name of the column being pasted into
            row_changes: Dict mapping row indices to (old_display_value, new_display_value) tuples
                         where display values are the formatted strings shown in the table
        """
        super().__init__(f"Paste into column {column_name} ({parameter_name})")
        self.scenario = scenario
        self.parameter_name = parameter_name
        self.column_name = column_name
        self.row_changes = row_changes  # {row_index: (old_display_value, new_display_value)}

    def do(self) -> bool:
        """Apply the column paste."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            # Apply all the new values (convert display strings to appropriate numeric types)
            for row_index, (old_display_value, new_display_value) in self.row_changes.items():
                # Convert display string to numeric value using same logic as load operation
                if not new_display_value or new_display_value == "":
                    numeric_value = 0.0
                else:
                    try:
                        # Try to parse as float first
                        numeric_value = float(new_display_value)
                    except ValueError:
                        # If it fails, keep as string
                        numeric_value = new_display_value
                parameter.df.loc[row_index, self.column_name] = numeric_value

            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False

    def undo(self) -> bool:
        """Undo the column paste."""
        try:
            parameter = self.scenario.get_parameter(self.parameter_name)
            if not parameter:
                return False

            # Restore all the old values (convert display strings to appropriate numeric types)
            for row_index, (old_display_value, new_display_value) in self.row_changes.items():
                # Convert display string to numeric value using same logic as load operation
                if not old_display_value or old_display_value == "":
                    numeric_value = 0.0
                else:
                    try:
                        # Try to parse as float first
                        numeric_value = float(old_display_value)
                    except ValueError:
                        # If it fails, keep as string
                        numeric_value = old_display_value
                parameter.df.loc[row_index, self.column_name] = numeric_value

            self.scenario.mark_modified(self.parameter_name)
            return True
        except Exception:
            return False

class AddParameterCommand(Command):
    """Command to add a parameter to the scenario."""

    def __init__(self, scenario, parameter_name: str, parameter_data: pd.DataFrame, metadata: dict):
        super().__init__(f"Add parameter '{parameter_name}'")
        self.scenario = scenario
        self.parameter_name = parameter_name
        self.parameter_data = parameter_data.copy()
        self.metadata = metadata.copy()

    def do(self) -> bool:
        """Add the parameter to the scenario."""
        try:
            from src.core.data_models import Parameter

            # Create the parameter object
            parameter = Parameter(self.parameter_name, self.parameter_data, self.metadata)

            # Add it to the scenario
            self.scenario.add_parameter(parameter)
            self.scenario.mark_modified(self.parameter_name)

            return True
        except Exception as e:
            print(f"Error adding parameter: {e}")
            return False

    def undo(self) -> bool:
        """Remove the added parameter."""
        try:
            # Remove the parameter from the scenario
            self.scenario.remove_parameter(self.parameter_name)
            return True
        except Exception as e:
            print(f"Error undoing add parameter: {e}")
            return False

class RemoveParameterCommand(Command):
    """Command to remove a parameter from the scenario."""

    def __init__(self, scenario, parameter_name: str):
        super().__init__(f"Remove parameter '{parameter_name}'")
        self.scenario = scenario
        self.parameter_name = parameter_name
        self.backup_parameter = None  # Will store the removed parameter

    def do(self) -> bool:
        """Remove the parameter from the scenario."""
        try:
            # Remove the parameter and store it for potential undo
            self.backup_parameter = self.scenario.remove_parameter(self.parameter_name)

            if self.backup_parameter is None:
                return False  # Parameter didn't exist

            return True
        except Exception as e:
            print(f"Error removing parameter: {e}")
            return False

    def undo(self) -> bool:
        """Restore the removed parameter."""
        try:
            if self.backup_parameter is None:
                return False

            # Add the parameter back to the scenario
            self.scenario.add_parameter(self.backup_parameter)
            self.scenario.mark_modified(self.parameter_name)

            return True
        except Exception as e:
            print(f"Error undoing remove parameter: {e}")
            return False
