"""
Results Analyzer - handles loading and parsing of MESSAGEix result Excel files
"""

import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from typing import Dict, List, Optional, Any, Callable

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager
from utils.parameter_utils import create_parameter_from_data


class ResultsAnalyzer(BaseDataManager):
    """
    Analyzes MESSAGEix result Excel files and prepares data for visualization.

    This class handles the complex process of reading MESSAGEix result data
    from Excel workbooks, parsing variables and equations, and providing access
    to the loaded data for analysis and visualization.

    Attributes:
        scenarios: List of loaded ScenarioData objects containing results
        loaded_file_paths: Corresponding file paths for loaded result files
        summary_stats: Dictionary containing summary statistics of loaded results
    """

    def __init__(self) -> None:
        """
        Initialize the ResultsAnalyzer.

        Sets up the analyzer with empty state and initializes summary statistics.
        """
        super().__init__()
        self.summary_stats: Dict[str, Any] = {}

    @property
    def results(self):
        """Backward compatibility property for results (same as scenarios)"""
        return self.scenarios

    def load_results_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ScenarioData:
        """
        Load and parse a MESSAGEix results Excel file.

        This method performs comprehensive validation and parsing of MESSAGEix
        result files, extracting variables and equations, and calculating
        summary statistics for analysis and visualization.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls format).
                      File must exist and be readable.
            progress_callback: Optional callback function for progress updates.
                             Receives (percentage: int, message: str) parameters.
                             Called at key milestones during loading process.

        Returns:
            ScenarioData object containing parsed variables and equations.

        Raises:
            FileNotFoundError: If the specified file_path does not exist.
            ValueError: If the file format is invalid or parsing fails.
            PermissionError: If file cannot be read due to permissions.

        Example:
            >>> analyzer = ResultsAnalyzer()
            >>> def progress(pct, msg): print(f"{pct}%: {msg}")
            >>> results = analyzer.load_results_file("results.xlsx", progress)
            >>> stats = analyzer.get_summary_stats()
            >>> print(f"Loaded {stats['total_variables']} variables")
        """
        scenario = self.load_file(file_path, progress_callback)

        # Calculate summary statistics for all loaded results
        combined_results = self.get_current_scenario()
        if combined_results:
            self._calculate_summary_stats(combined_results)

        return scenario

    def _parse_workbook(
        self,
        wb: Any,
        scenario: ScenarioData,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse workbook for results data - implements abstract method.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate
            progress_callback: Optional progress callback function
        """
        # Parse results (typically in var_* and equ_* sheets)
        self._parse_results(wb, scenario, progress_callback)

    def _parse_results(
        self,
        wb: Any,
        results: ScenarioData,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse results from workbook.

        Identifies and parses result sheets containing variables and equations.

        Args:
            wb: Openpyxl workbook object
            results: ScenarioData object to populate with results
            progress_callback: Optional progress callback function
        """
        # Look for result sheets (typically var_* for variables, equ_* for equations)
        result_sheets = [sheet_name for sheet_name in wb.sheetnames if sheet_name.startswith(('var_', 'equ_'))]

        # Also include sheets that look like result data (have headers and data rows)
        # Exclude sheets that are clearly input-related
        input_indicators = ['parameter', 'parameters', 'set', 'sets', 'data']
        potential_result_sheets = [sheet_name for sheet_name in wb.sheetnames
                                 if not any(indicator.lower() in sheet_name.lower() for indicator in input_indicators)
                                 and sheet_name not in result_sheets]

        # Check which potential sheets actually contain result-like data
        for sheet_name in potential_result_sheets:
            sheet = wb[sheet_name]
            if self._is_result_sheet(sheet):
                result_sheets.append(sheet_name)

        total_sheets = len(result_sheets)

        for i, sheet_name in enumerate(result_sheets):
            if progress_callback and total_sheets > 0:
                progress = 20 + int((i / total_sheets) * 60)  # Progress from 20% to 80%
                progress_callback(progress, f"Parsing result sheet: {sheet_name}")

            sheet = wb[sheet_name]
            self._parse_result_sheet(sheet, results, sheet_name)

    def _is_result_sheet(self, sheet: Any) -> bool:
        """
        Check if a sheet contains result-like data.

        Determines if a worksheet contains data that looks like MESSAGEix results
        by checking for headers and numeric data.

        Args:
            sheet: Openpyxl worksheet object to analyze

        Returns:
            True if the sheet appears to contain result data
        """
        try:
            # Get all rows
            rows = list(sheet.iter_rows(values_only=True))

            # Need at least headers + 1 data row
            if len(rows) < 2:
                return False

            # Check if first row looks like headers (strings)
            headers = rows[0]
            if not headers or not any(isinstance(h, str) and h.strip() for h in headers):
                return False

            # Check if we have at least one data row with some numeric values
            has_numeric_data = False
            for row in rows[1:]:
                if any(isinstance(cell, (int, float)) and not pd.isna(cell) for cell in row):
                    has_numeric_data = True
                    break

            return has_numeric_data

        except Exception:
            return False

    def _parse_result_sheet(self, sheet: Any, results: ScenarioData, sheet_name: str) -> None:
        """
        Parse individual result sheet.

        Extracts data from a single result worksheet and creates appropriate
        Parameter objects.

        Args:
            sheet: Openpyxl worksheet object to parse
            results: ScenarioData object to populate
            sheet_name: Name of the sheet being parsed
        """
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

        # Make headers unique, as duplicate column names can cause issues with pandas
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
            # Use parameter utilities to create the parameter
            metadata_overrides = {
                'result_type': 'variable' if sheet_name.startswith('var_') else 'equation'
            }
            parameter = create_parameter_from_data(sheet_name, data, headers, metadata_overrides)
            if parameter:
                results.add_parameter(parameter)

    def _calculate_summary_stats(self, results: ScenarioData) -> None:
        """
        Calculate summary statistics from results.

        Computes statistics about the loaded result data including counts
        of variables, equations, and data points.

        Args:
            results: ScenarioData object containing the results to analyze
        """
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
        """
        Get summary statistics of loaded results.

        Returns a dictionary containing statistics about all loaded result data,
        including counts of variables, equations, and data points.

        Returns:
            Dictionary with the following keys:
            - 'total_variables': Number of variable parameters loaded
            - 'total_equations': Number of equation parameters loaded
            - 'total_data_points': Total number of data points across all results
            - 'result_sheets': List of all result sheet names

        Example:
            >>> analyzer = ResultsAnalyzer()
            >>> # ... load some results ...
            >>> stats = analyzer.get_summary_stats()
            >>> print(f"Variables: {stats['total_variables']}")
            >>> print(f"Data points: {stats['total_data_points']}")
        """
        return self.summary_stats.copy()

    def get_result_data(self, result_name: str) -> Optional[Parameter]:
        """
        Get specific result data by name.

        Retrieves a Parameter object containing result data for the specified
        result name (typically a sheet name from the Excel file).

        Args:
            result_name: Name of the result parameter to retrieve

        Returns:
            Parameter object if found, None otherwise

        Example:
            >>> analyzer = ResultsAnalyzer()
            >>> # ... load results ...
            >>> variable_data = analyzer.get_result_data('var_cost')
            >>> if variable_data:
            ...     print(f"Shape: {variable_data.df.shape}")
        """
        return self.get_parameter(result_name)

    def get_all_result_names(self) -> List[str]:
        """
        Get list of all result names.

        Returns a list of all available result parameter names from loaded
        result files.

        Returns:
            List of result parameter names (strings)

        Example:
            >>> analyzer = ResultsAnalyzer()
            >>> # ... load results ...
            >>> names = analyzer.get_all_result_names()
            >>> print(f"Available results: {names}")
        """
        return self.get_parameter_names()

    def prepare_chart_data(self, result_name: str, chart_type: str = 'line') -> Optional[Dict[str, Any]]:
        """
        Prepare data for charting.

        Transforms result data into a format suitable for chart visualization.
        Supports various chart types with automatic data formatting.

        Args:
            result_name: Name of the result parameter to chart
            chart_type: Type of chart to prepare data for. Supported types:
                       'line', 'bar', 'stacked_bar', 'stacked_area', 'area'

        Returns:
            Dictionary containing chart data with the following structure:
            {
                'title': str,        # Chart title
                'x_label': str,      # X-axis label
                'y_label': str,      # Y-axis label
                'data': List[dict]   # Chart data series
            }
            Returns None if the result_name is not found or data is invalid.

        Example:
            >>> analyzer = ResultsAnalyzer()
            >>> # ... load results ...
            >>> chart_data = analyzer.prepare_chart_data('var_cost', 'line')
            >>> if chart_data:
            ...     print(f"Chart title: {chart_data['title']}")
            ...     print(f"Data series: {len(chart_data['data'])}")
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

        # Simple chart preparation
        if len(df.columns) >= 2:
            # For line charts, use index as x
            x_data = list(range(len(df)))

            if chart_type == 'line':
                # Assume last column is the value column
                value_col = df.columns[-1]
                chart_data['data'] = [{
                    'x': x_data,
                    'y': df[value_col].fillna(0).tolist(),
                    'type': 'line',
                    'name': result_name
                }]
            elif chart_type in ['bar', 'stacked_bar']:
                # For bar charts, create traces for each numeric column
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    for col in numeric_cols:
                        chart_data['data'].append({
                            'x': df.index.tolist() if hasattr(df, 'index') else x_data,
                            'y': df[col].fillna(0).tolist(),
                            'name': str(col)
                        })
                else:
                    # Fallback to last column
                    value_col = df.columns[-1]
                    chart_data['data'] = [{
                        'x': x_data,
                        'y': df[value_col].fillna(0).tolist(),
                        'name': result_name
                    }]

        return chart_data

    # Override get_current_scenario to maintain backward compatibility naming
    def get_current_results(self) -> Optional[ScenarioData]:
        """
        Get the combined results from all loaded files.

        Backward compatibility method - equivalent to get_current_scenario().
        """
        return self.get_current_scenario()

    # Override other methods for backward compatibility
    def get_results_by_file_path(self, file_path: str) -> Optional[ScenarioData]:
        """
        Get specific results by file path.

        Backward compatibility method - equivalent to get_scenario_by_file_path().

        Args:
            file_path: Path to the results file

        Returns:
            ScenarioData object if found, None otherwise
        """
        return self.get_scenario_by_file_path(file_path)

    def clear_results(self) -> None:
        """
        Clear all loaded results.

        Backward compatibility method - equivalent to clear_scenarios().
        """
        self.clear_scenarios()

    # Keep remove_file method for backward compatibility (inherited from BaseDataManager)
