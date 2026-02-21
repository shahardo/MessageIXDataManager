"""
Results Analyzer - handles loading and parsing of MESSAGEix result Excel files.

Business logic (LCOE, dashboard metrics, cost breakdown) has been moved to:
  - analysis.electricity_analyzer.ElectricityAnalyzer
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Any, Callable

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager
from utils.parsing_strategies import ExcelParser, ResultParsingStrategy
from managers.results_postprocessor import add_postprocessed_results
from analysis.electricity_analyzer import ElectricityAnalyzer


class ResultsAnalyzer(BaseDataManager):
    """
    Analyzes MESSAGEix result Excel files and prepares data for visualization.

    This class handles loading and parsing result Excel workbooks. Business
    logic (cost breakdown, LCOE, dashboard metrics) is delegated to
    ElectricityAnalyzer in src/analysis/.
    """

    def __init__(self, main_window=None, auto_postprocess: bool = True) -> None:
        """
        Initialize the ResultsAnalyzer.

        Args:
            main_window: Reference to the main application window for accessing
                         input scenarios (used by _load_input_costs).
            auto_postprocess: If True, automatically run postprocessing after loading.
        """
        super().__init__()
        self.main_window = main_window
        self.summary_stats: Dict[str, Any] = {}
        self.auto_postprocess = auto_postprocess

    @property
    def results(self):
        """Backward compatibility alias for scenarios."""
        return self.scenarios

    # =========================================================================
    # File Loading
    # =========================================================================

    def load_results_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ScenarioData:
        """
        Load and parse a MESSAGEix results Excel file.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls format).
            progress_callback: Optional callback for progress updates
                               (percentage: int, message: str).

        Returns:
            ScenarioData object containing parsed variables and equations.

        Example:
            analyzer = ResultsAnalyzer()
            scenario = analyzer.load_results_file("results.xlsx")
        """
        scenario = self.load_file(file_path, progress_callback)

        combined_results = self.get_current_scenario()
        if combined_results:
            self._calculate_summary_stats(combined_results)

            if self.auto_postprocess:
                self.run_postprocessing(combined_results, progress_callback)

        return scenario

    def _parse_workbook(
        self,
        wb: Any,
        scenario: ScenarioData,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """Parse workbook using ResultParsingStrategy (implements abstract method)."""
        parser = ExcelParser()
        parser.strategies = [ResultParsingStrategy()]
        parser.parse_workbook(wb, scenario, file_path, progress_callback)

    def _is_result_sheet(self, worksheet) -> bool:
        """Determine if a worksheet contains MESSAGEix result data."""
        sheet_name = worksheet.title
        return sheet_name.startswith('var_') or sheet_name.startswith('equ_')

    def _calculate_summary_stats(self, results: ScenarioData) -> None:
        """Calculate summary statistics from results."""
        self.summary_stats = {
            'total_variables': 0,
            'total_equations': 0,
            'total_data_points': 0,
            'result_sheets': [],
            'postprocessed_count': 0
        }

        for param in results.parameters.values():
            self.summary_stats['total_data_points'] += len(param.df)

            if param.metadata.get('result_type') == 'variable':
                self.summary_stats['total_variables'] += 1
            elif param.metadata.get('result_type') == 'postprocessed':
                self.summary_stats['postprocessed_count'] += 1
            else:
                self.summary_stats['total_equations'] += 1

            self.summary_stats['result_sheets'].append(param.name)

    # =========================================================================
    # Postprocessing
    # =========================================================================

    def run_postprocessing(
        self,
        scenario: Optional[ScenarioData] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        nodeloc: Optional[str] = None,
        plot_years: Optional[List[int]] = None
    ) -> int:
        """
        Run postprocessing calculations on results and add derived parameters.

        Args:
            scenario: ScenarioData to process (defaults to current combined scenario).
            progress_callback: Optional progress callback function.
            nodeloc: Optional node location filter.
            plot_years: Optional list of years to include.

        Returns:
            Number of postprocessed parameters added.
        """
        if scenario is None:
            scenario = self.get_current_scenario()

        if scenario is None:
            print("Warning: No scenario data available for postprocessing")
            return 0

        if progress_callback:
            progress_callback(90, "Running postprocessing calculations...")

        try:
            count = add_postprocessed_results(scenario, nodeloc, plot_years)
            print(f"Postprocessing added {count} derived parameters")
            self.summary_stats['postprocessed_count'] = count

            if progress_callback:
                progress_callback(100, f"Postprocessing complete: {count} parameters added")

            return count

        except Exception as e:
            print(f"Warning: Postprocessing failed: {e}")
            if progress_callback:
                progress_callback(100, f"Postprocessing failed: {e}")
            return 0

    # =========================================================================
    # Data Access
    # =========================================================================

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of loaded results."""
        return self.summary_stats.copy()

    def get_result_data(self, result_name: str) -> Optional[Parameter]:
        """Get specific result data by name."""
        return self.get_parameter(result_name)

    def get_all_result_names(self) -> List[str]:
        """Get list of all result parameter names."""
        return self.get_parameter_names()

    def prepare_chart_data(self, result_name: str, chart_type: str = 'line') -> Optional[Dict[str, Any]]:
        """Prepare data for charting.

        Example:
            chart_data = analyzer.prepare_chart_data('var_ACT', chart_type='line')
        """
        parameter = self.get_result_data(result_name)
        if not parameter:
            return None

        df = parameter.df
        chart_data = {
            'title': f'{result_name} Results',
            'x_label': 'Index',
            'y_label': 'Value',
            'data': []
        }

        if len(df.columns) >= 2:
            x_data = list(range(len(df)))
            if chart_type == 'line':
                value_col = df.columns[-1]
                chart_data['data'] = [{
                    'x': x_data,
                    'y': df[value_col].fillna(0).tolist(),
                    'type': 'line',
                    'name': result_name
                }]
            elif chart_type in ['bar', 'stacked_bar']:
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    for col in numeric_cols:
                        chart_data['data'].append({
                            'x': df.index.tolist() if hasattr(df, 'index') else x_data,
                            'y': df[col].fillna(0).tolist(),
                            'name': str(col)
                        })
                else:
                    value_col = df.columns[-1]
                    chart_data['data'] = [{
                        'x': x_data,
                        'y': df[value_col].fillna(0).tolist(),
                        'name': result_name
                    }]

        return chart_data

    # =========================================================================
    # Backward Compatibility Aliases
    # =========================================================================

    def get_current_results(self) -> Optional[ScenarioData]:
        """Backward compatibility - equivalent to get_current_scenario()."""
        return self.get_current_scenario()

    def get_results_by_file_path(self, file_path: str) -> Optional[ScenarioData]:
        """Backward compatibility - equivalent to get_scenario_by_file_path()."""
        return self.get_scenario_by_file_path(file_path)

    def clear_results(self) -> None:
        """Backward compatibility - equivalent to clear_scenarios()."""
        self.clear_scenarios()

    # =========================================================================
    # Dashboard Metrics / Cost Breakdown (delegate to ElectricityAnalyzer)
    # =========================================================================

    def calculate_dashboard_metrics(self, scenario: ScenarioData) -> Dict[str, float]:
        """
        Calculate dashboard metrics (primary energy, electricity, clean %, emissions).

        Delegates to ElectricityAnalyzer.calculate_dashboard_metrics.
        """
        return ElectricityAnalyzer.calculate_dashboard_metrics(scenario)

    def calculate_crf(self, interest_rate: float, lifetime: float) -> float:
        """Calculate Capital Recovery Factor. Delegates to ElectricityAnalyzer."""
        return ElectricityAnalyzer.calculate_crf(interest_rate, lifetime)

    def calculate_electricity_cost_breakdown(
        self,
        scenario: ScenarioData,
        regions=None,
        electricity_commodity: str = 'electr'
    ) -> pd.DataFrame:
        """
        Break down electricity generation costs by technology and cost component.

        Delegates to ElectricityAnalyzer.calculate_electricity_cost_breakdown,
        passing the input cost scenario loaded from the active input file (if any).
        """
        input_cost_scenario = self._load_input_costs()
        return ElectricityAnalyzer.calculate_electricity_cost_breakdown(
            scenario,
            input_cost_scenario=input_cost_scenario,
            regions=regions,
            electricity_commodity=electricity_commodity
        )

    # =========================================================================
    # Input Cost Scenario Loading (needs main_window access)
    # =========================================================================

    def _load_input_costs(self) -> Optional[ScenarioData]:
        """Get the currently loaded input scenario if it has cost parameters."""
        if not self.main_window:
            return None

        if not hasattr(self.main_window, 'input_manager'):
            return None

        if hasattr(self.main_window, 'selected_input_file') and self.main_window.selected_input_file:
            scenario = self.main_window.input_manager.get_scenario_by_file_path(
                self.main_window.selected_input_file
            )
            if scenario and self._has_cost_parameters(scenario):
                return scenario

        scenario = self.main_window.input_manager.get_current_scenario()
        if scenario and self._has_cost_parameters(scenario):
            return scenario

        return None

    def _has_cost_parameters(self, scenario: ScenarioData) -> bool:
        """Check if a scenario has the required cost parameters."""
        required = ['investment_cost', 'fixed_cost', 'variable_cost', 'technical_lifetime']
        count = sum(1 for p in required if scenario.get_parameter(p))
        if scenario.get_parameter('historical_new_capacity'):
            count += 1
        return count >= 2
