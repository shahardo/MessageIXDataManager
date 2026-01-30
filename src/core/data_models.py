"""
Core data models for message_ix data
"""

import pandas as pd
from typing import Dict, List, Optional, Any, Set
import os
from datetime import datetime


class Parameter:
    """Represents a message_ix parameter with its data and metadata"""

    def __init__(self, name: str, df: pd.DataFrame, metadata: dict):
        self.name = name
        self.df = df  # columns: dim1, dim2, ..., value
        self.metadata = metadata  # {'units': str, 'desc': str, 'dims': list[str]}


class Scenario:
    """
    Represents a complete MESSAGEix scenario with all associated data and files.

    Attributes:
        name: User-defined scenario name
        input_file: Optional path to the input Excel file
        message_scenario_file: Optional path to the pickle file with scenario snapshot
        results_file: Optional path to results Excel file
        status: Current status (loaded, modified, etc.)
        data: ScenarioData object containing all scenario data
        created_at: Timestamp when scenario was created
        modified_at: Timestamp when scenario was last modified
    """

    def __init__(self, name: str, input_file: Optional[str] = None):
        """
        Initialize a new scenario.

        Args:
            name: User-defined scenario name
            input_file: Optional path to the input Excel file
        """
        self.name = name
        self.input_file = input_file
        self.message_scenario_file = self._generate_scenario_file_path() if input_file else None
        self.results_file: Optional[str] = None
        self.status = "loaded"
        self.data = ScenarioData()
        self.created_at = datetime.now()
        self.modified_at = datetime.now()

    def _generate_scenario_file_path(self) -> str:
        """Generate the path for the scenario pickle file."""
        base_name = os.path.splitext(self.input_file)[0]
        return f"{base_name}_scenario.pkl"

    def update_status(self, status: str):
        """Update the scenario status."""
        self.status = status
        self.modified_at = datetime.now()

    def mark_modified(self):
        """Mark the scenario as modified."""
        self.update_status("modified")

    def mark_saved(self):
        """Mark the scenario as saved."""
        self.update_status("loaded")

    def is_modified(self) -> bool:
        """Check if the scenario has been modified."""
        return self.status == "modified"

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the scenario."""
        return {
            "name": self.name,
            "input_file": self.input_file,
            "message_scenario_file": self.message_scenario_file,
            "results_file": self.results_file,
            "status": self.status,
            "parameter_count": len(self.data.parameters),
            "set_count": len(self.data.sets),
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }

    def __str__(self) -> str:
        return f"Scenario(name={self.name}, status={self.status})"


class ScenarioData:
    """Container for all data in a message_ix scenario"""

    def __init__(self):
        self.sets: Dict[str, pd.Series] = {}        # set_name → values
        self.parameters: Dict[str, Parameter] = {}  # par_name → Parameter
        self.mappings: Dict[str, pd.DataFrame] = {} # optional mappings
        self.modified: Set[str] = set()             # tracked changed parameters
        self.change_history: List[dict] = []        # undo/redo stack
        self.options: Dict[str, Any] = {            # scenario options
            'MinYear': 2020,
            'MaxYear': 2050,
            'YearsLimitEnabled': True
        }

    def get_parameter_names(self) -> List[str]:
        """Get list of all parameter names"""
        return list(self.parameters.keys())

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get a parameter by name"""
        return self.parameters.get(name)

    def add_parameter(self, parameter: Parameter, mark_modified: bool = True, add_to_history: bool = True):
        """Add a parameter to the scenario"""
        self.parameters[parameter.name] = parameter
        if mark_modified:
            self.modified.add(parameter.name)
        if add_to_history:
            self.change_history.append({
                'action': 'add',
                'parameter': parameter.name,
                'timestamp': pd.Timestamp.now()
            })

    def remove_parameter(self, name: str) -> Optional[Parameter]:
        """Remove a parameter from the scenario and return it"""
        if name in self.parameters:
            parameter = self.parameters.pop(name)
            self.modified.add(name)
            self.change_history.append({
                'action': 'remove',
                'parameter': name,
                'timestamp': pd.Timestamp.now()
            })
            return parameter
        return None

    def mark_modified(self, param_name: str):
        """Mark a parameter as modified"""
        self.modified.add(param_name)
        self.change_history.append({
            'action': 'modify',
            'parameter': param_name,
            'timestamp': pd.Timestamp.now()
        })

    def clear_modified(self):
        """Clear all modified flags"""
        self.modified.clear()
        self.change_history.clear()

    def has_modified_data(self) -> bool:
        """Check if there are any modified parameters"""
        return len(self.modified) > 0

    def get_modified_parameters(self) -> List[str]:
        """Get list of modified parameter names"""
        return list(self.modified)