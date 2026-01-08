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
from utils.parsing_strategies import ExcelParser, ResultParsingStrategy


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
        Parse workbook for results data using Strategy pattern - implements abstract method.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate
            progress_callback: Optional progress callback function
        """
        # Use ExcelParser with result parsing strategy
        parser = ExcelParser()
        # Replace default strategies with result-specific strategy
        parser.strategies = [ResultParsingStrategy()]

        parser.parse_workbook(wb, scenario, progress_callback)

    def _is_result_sheet(self, worksheet) -> bool:
        """
        Determine if a worksheet contains MESSAGEix result data.

        Result sheets in MESSAGEix typically start with 'var_' for variables
        or 'equ_' for equations.

        Args:
            worksheet: Openpyxl worksheet object

        Returns:
            True if the worksheet contains result data, False otherwise
        """
        sheet_name = worksheet.title
        return sheet_name.startswith('var_') or sheet_name.startswith('equ_')



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

    def calculate_dashboard_metrics(self, scenario: ScenarioData) -> Dict[str, float]:
        """
        Calculate dashboard metrics for a given scenario.

        Computes the four key metrics displayed in the dashboard top row:
        - Total primary energy (2050)
        - Total electricity (2050)
        - % Clean electricity (2050)
        - Total emissions (2050)

        Args:
            scenario: ScenarioData object containing the scenario to analyze

        Returns:
            Dictionary with metric values:
            - 'primary_energy_2050': Total primary energy for 2050 (PJ)
            - 'electricity_2050': Total electricity generation for 2050 (TWh)
            - 'clean_electricity_pct': Percentage of clean electricity for 2050 (%)
            - 'emissions_2050': Total emissions for 2050 (ktCO2e or equivalent)
        """
        metrics = {
            'primary_energy_2050': 0.0,
            'electricity_2050': 0.0,
            'clean_electricity_pct': 0.0,
            'emissions_2050': 0.0
        }

        # 1. Primary energy 2050 - try multiple parameter names
        primary_energy_param = scenario.get_parameter('Primary energy supply (PJ)')

        if primary_energy_param and not primary_energy_param.df.empty:
            df = primary_energy_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                # Sum all numeric columns except year
                for col in df_2050.columns:
                    if col != year_col and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['primary_energy_2050'] += df_2050[col].sum()

        # 2. Electricity 2050 - try multiple parameter names
        electricity_param = scenario.get_parameter('Electricity generation (TWh)')

        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                # Sum all numeric columns except year
                for col in df_2050.columns:
                    if col != year_col and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['electricity_2050'] += df_2050[col].sum()

        # 3. Clean electricity percentage - need source breakdown
        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]

            if not df_2050.empty:
                total_electricity = 0.0
                clean_electricity = 0.0
                clean_technologies = ['nuclear', 'solar PV', 'solar CSP', 'wind', 'hydro', 'biomass', 'geothermal', 'renewable']

                for col in df_2050.columns:
                    if col in clean_technologies:
                        clean_electricity += df_2050[col].sum()
                    total_electricity += df_2050[col].sum()

                if total_electricity > 0:
                    metrics['clean_electricity_pct'] = (clean_electricity / total_electricity) * 100

        # 4. Emissions 2050 - try multiple parameter names
        emissions_param = scenario.get_parameter('Total GHG emissions (MtCeq)')

        if emissions_param and not emissions_param.df.empty:
            df = emissions_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                # Sum all numeric columns except year
                for col in df_2050.columns:
                    if col != year_col and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['emissions_2050'] += df_2050[col].sum()

        return metrics

    # Keep remove_file method for backward compatibility (inherited from BaseDataManager)
