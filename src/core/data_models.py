"""
Core data models for message_ix data
"""

import pandas as pd
from typing import Dict, List, Optional, Any


class Parameter:
    """Represents a message_ix parameter with its data and metadata"""

    def __init__(self, name: str, df: pd.DataFrame, metadata: dict):
        self.name = name
        self.df = df  # columns: dim1, dim2, ..., value
        self.metadata = metadata  # {'units': str, 'desc': str, 'dims': list[str]}


class ScenarioData:
    """Container for all data in a message_ix scenario"""

    def __init__(self):
        self.sets: Dict[str, pd.Series] = {}        # set_name → values
        self.parameters: Dict[str, Parameter] = {}  # par_name → Parameter
        self.mappings: Dict[str, pd.DataFrame] = {} # optional mappings
        self.modified: set[str] = set()             # tracked changed parameters
        self.change_history: List[dict] = []        # undo/redo stack
        self.options: Dict[str, int] = {            # scenario options
            'MinYear': 2020,
            'MaxYear': 2050
        }

    def get_parameter_names(self) -> List[str]:
        """Get list of all parameter names"""
        return list(self.parameters.keys())

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get a parameter by name"""
        return self.parameters.get(name)

    def add_parameter(self, parameter: Parameter):
        """Add a parameter to the scenario"""
        self.parameters[parameter.name] = parameter

    def mark_modified(self, param_name: str):
        """Mark a parameter as modified"""
        self.modified.add(param_name)
        self.change_history.append({
            'action': 'modify',
            'parameter': param_name,
            'timestamp': pd.Timestamp.now()
        })
