"""
Input Manager - handles loading and parsing of message_ix Excel input files
"""

import os
import pandas as pd
from openpyxl import load_workbook
from typing import Optional, List

from core.data_models import ScenarioData, Parameter


class InputManager:
    """Manages loading and parsing of message_ix input Excel files"""

    def __init__(self):
        self.current_scenario: Optional[ScenarioData] = None
        self.loaded_file_path: Optional[str] = None

    def load_excel_file(self, file_path: str) -> ScenarioData:
        """
        Load and parse a message_ix Excel input file

        Args:
            file_path: Path to the Excel file

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
            # Load workbook
            wb = load_workbook(file_path, data_only=True)

            # Parse sets
            self._parse_sets(wb, scenario)

            # Parse parameters
            self._parse_parameters(wb, scenario)

            # Store reference
            self.current_scenario = scenario
            self.loaded_file_path = file_path

            print(f"Successfully loaded {len(scenario.parameters)} parameters and {len(scenario.sets)} sets")

        except Exception as e:
            raise ValueError(f"Error parsing Excel file: {str(e)}")

        return scenario

    def _parse_sets(self, wb, scenario: ScenarioData):
        """Parse sets from the workbook"""
        # Look for sets sheet
        if 'sets' in wb.sheetnames:
            sheet = wb['sets']
            # Simple parsing - assume first column is set name, second is values
            # This is a simplified version; real message_ix format is more complex
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row[0] and row[1]:
                    set_name = str(row[0]).strip()
                    set_values = str(row[1]).split(',')  # Assume comma-separated
                    scenario.sets[set_name] = pd.Series([v.strip() for v in set_values])

    def _parse_parameters(self, wb, scenario: ScenarioData):
        """Parse parameters from the workbook"""
        # Look for parameters sheet
        if 'parameters' in wb.sheetnames:
            sheet = wb['parameters']

            # Get headers
            headers = []
            for cell in sheet[1]:
                if cell.value:
                    headers.append(str(cell.value))

            # Parse parameter data
            current_param = None
            param_data = []

            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row[0]:  # New parameter
                    # Save previous parameter if exists
                    if current_param and param_data:
                        self._create_parameter(scenario, current_param, param_data, headers)

                    # Start new parameter
                    current_param = str(row[0]).strip()
                    param_data = [row]
                elif current_param:  # Continuation of current parameter
                    param_data.append(row)

            # Save last parameter
            if current_param and param_data:
                self._create_parameter(scenario, current_param, param_data, headers)

    def _create_parameter(self, scenario: ScenarioData, param_name: str,
                         param_data: List, headers: List[str]):
        """Create a Parameter object from parsed data"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(param_data, columns=headers)

            # Basic metadata (would be more sophisticated in real implementation)
            metadata = {
                'units': 'N/A',
                'desc': f'Parameter {param_name}',
                'dims': headers[:-1] if len(headers) > 1 else []  # All columns except last (value)
            }

            # Create parameter object
            parameter = Parameter(param_name, df, metadata)
            scenario.add_parameter(parameter)

        except Exception as e:
            print(f"Warning: Could not create parameter {param_name}: {str(e)}")

    def get_current_scenario(self) -> Optional[ScenarioData]:
        """Get the currently loaded scenario"""
        return self.current_scenario

    def get_parameter_names(self) -> List[str]:
        """Get list of parameter names from current scenario"""
        if self.current_scenario:
            return self.current_scenario.get_parameter_names()
        return []

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """Get a parameter by name"""
        if self.current_scenario:
            return self.current_scenario.get_parameter(name)
        return None
