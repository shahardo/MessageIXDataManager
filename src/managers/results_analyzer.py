"""
Results Analyzer - handles loading and parsing of message_ix result Excel files
"""

import os
import pandas as pd
from openpyxl import load_workbook
from typing import Dict, List, Optional, Any, Callable

from core.data_models import ScenarioData, Parameter


class ResultsAnalyzer:
    """Analyzes message_ix result Excel files and prepares data for visualization"""

    def __init__(self):
        self.current_results: Optional[ScenarioData] = None
        self.loaded_file_path: Optional[str] = None
        self.summary_stats: Dict[str, Any] = {}

    def load_results_file(self, file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScenarioData:
        """
        Load and parse a message_ix results Excel file

        Args:
            file_path: Path to the results Excel file
            progress_callback: Optional callback function for progress updates (value, message)

        Returns:
            ScenarioData object containing parsed results

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Results file not found: {file_path}")

        print(f"Loading results file: {file_path}")

        # Create new results data
        results = ScenarioData()

        try:
            # Initialize progress
            if progress_callback:
                progress_callback(0, "Loading results workbook...")

            # Load workbook
            wb = load_workbook(file_path, data_only=True)

            if progress_callback:
                progress_callback(20, "Workbook loaded, parsing results...")

            # Parse results (typically in var_* and equ_* sheets)
            self._parse_results(wb, results, progress_callback)

            if progress_callback:
                progress_callback(80, "Calculating summary statistics...")

            # Calculate summary statistics
            self._calculate_summary_stats(results)

            # Store reference
            self.current_results = results
            self.loaded_file_path = file_path

            if progress_callback:
                progress_callback(100, "Results loading complete")

            print(f"Successfully loaded results with {len(results.parameters)} variables/equations")

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise ValueError(f"Error parsing results file: {str(e)}")

        return results

    def _parse_results(self, wb, results: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse results from workbook"""
        # Look for result sheets (typically var_* for variables, equ_* for equations)
        result_sheets = [sheet_name for sheet_name in wb.sheetnames if sheet_name.startswith(('var_', 'equ_'))]
        total_sheets = len(result_sheets)

        for i, sheet_name in enumerate(result_sheets):
            if progress_callback and total_sheets > 0:
                progress = 20 + int((i / total_sheets) * 60)  # Progress from 20% to 80%
                progress_callback(progress, f"Parsing result sheet: {sheet_name}")

            sheet = wb[sheet_name]
            self._parse_result_sheet(sheet, results, sheet_name)

    def _parse_result_sheet(self, sheet, results: ScenarioData, sheet_name: str):
        """Parse individual result sheet"""
        # Get headers
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value))

        if not headers or len(headers) == 0:
            return

        # Parse data
        data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row and any(cell is not None for cell in row):
                data.append(row)

        if data and len(data) > 0:
            df = pd.DataFrame(data, columns=headers)

            # Create parameter object for this result
            metadata = {
                'units': 'N/A',
                'desc': f'Result {sheet_name}',
                'dims': headers[:-1] if len(headers) > 1 else [],
                'result_type': 'variable' if sheet_name.startswith('var_') else 'equation'
            }

            parameter = Parameter(sheet_name, df, metadata)
            results.add_parameter(parameter)

    def _calculate_summary_stats(self, results: ScenarioData):
        """Calculate summary statistics from results"""
        self.summary_stats = {
            'total_variables': 0,
            'total_equations': 0,
            'total_data_points': 0,
            'result_sheets': []
        }

        for param in results.parameters.values():
            self.summary_stats['total_data_points'] += len(param.df)

            if param.metadata.get('result_type') == 'variable':
                self.summary_stats['total_variables'] += 1
            else:
                self.summary_stats['total_equations'] += 1

            self.summary_stats['result_sheets'].append(param.name)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of loaded results"""
        return self.summary_stats.copy()

    def get_result_data(self, result_name: str) -> Optional[Parameter]:
        """Get specific result data by name"""
        if self.current_results:
            return self.current_results.get_parameter(result_name)
        return None

    def get_all_result_names(self) -> List[str]:
        """Get list of all result names"""
        if self.current_results:
            return self.current_results.get_parameter_names()
        return []

    def prepare_chart_data(self, result_name: str, chart_type: str = 'line') -> Optional[Dict[str, Any]]:
        """
        Prepare data for charting

        Args:
            result_name: Name of the result to chart
            chart_type: Type of chart ('line', 'bar', 'area')

        Returns:
            Dictionary with chart data or None if not available
        """
        parameter = self.get_result_data(result_name)
        if not parameter:
            return None

        df = parameter.df

        # Basic data preparation (would be more sophisticated in real implementation)
        chart_data = {
            'title': f'{result_name} Results',
            'x_label': 'Index',
            'y_label': 'Value',
            'data': []
        }

        # Simple line chart preparation
        if len(df.columns) >= 2:
            # Assume last column is the value column
            value_col = df.columns[-1]
            x_data = list(range(len(df)))

            if chart_type == 'line':
                chart_data['data'] = [{
                    'x': x_data,
                    'y': df[value_col].fillna(0).tolist(),
                    'type': 'line',
                    'name': result_name
                }]

        return chart_data

    def get_current_results(self) -> Optional[ScenarioData]:
        """Get the currently loaded results"""
        return self.current_results
