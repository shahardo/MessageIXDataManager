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

    def __init__(self, main_window=None) -> None:
        """
        Initialize the ResultsAnalyzer.

        Sets up the analyzer with empty state and initializes summary statistics.

        Args:
            main_window: Reference to the main application window for accessing input scenarios
        """
        super().__init__()
        self.main_window = main_window
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
        file_path: str,
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

        parser.parse_workbook(wb, scenario, file_path, progress_callback)

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
        primary_energy_names = ['Primary energy supply (PJ)', 'var_primary_energy', 'primary_energy']
        primary_energy_param = None
        for name in primary_energy_names:
            primary_energy_param = scenario.get_parameter(name)
            if primary_energy_param:
                break

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
        electricity_names = ['Electricity generation (TWh)', 'var_electricity', 'var_electricity_generation', 'var_electricity_consumption']
        electricity_param = None
        for name in electricity_names:
            electricity_param = scenario.get_parameter(name)
            if electricity_param:
                break

        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]
            if not df_2050.empty:
                # Sum all numeric columns except year and region
                for col in df_2050.columns:
                    if col not in [year_col, 'region'] and pd.api.types.is_numeric_dtype(df_2050[col]):
                        metrics['electricity_2050'] += df_2050[col].sum()

        # 3. Clean electricity percentage - need source breakdown
        if electricity_param and not electricity_param.df.empty:
            df = electricity_param.df
            year_col = 'year' if 'year' in df.columns else 'year_act'
            df_2050 = df[df[year_col] == 2050]

            if not df_2050.empty:
                clean_technologies = ['nuclear', 'solar', 'solar PV', 'solar CSP', 'wind', 'hydro', 'biomass', 'geothermal', 'renewable']
                clean_electricity = 0.0
                total_electricity = 0.0

                # Check if we have technology column (long format)
                if 'technology' in df_2050.columns and 'value' in df_2050.columns:
                    # Group by technology and sum values
                    tech_sums = df_2050.groupby('technology')['value'].sum()
                    for tech, val in tech_sums.items():
                        total_electricity += val
                        if tech.lower() in [t.lower() for t in clean_technologies]:
                            clean_electricity += val
                else:
                    # Wide format: columns per technology
                    for col in df_2050.columns:
                        if col not in [year_col, 'region'] and pd.api.types.is_numeric_dtype(df_2050[col]):
                            val = df_2050[col].sum()
                            total_electricity += val
                            if col.lower() in [t.lower() for t in clean_technologies]:
                                clean_electricity += val

                if total_electricity > 0:
                    metrics['clean_electricity_pct'] = (clean_electricity / total_electricity) * 100

        # 4. Emissions 2050 - try multiple parameter names
        emissions_names = ['Total GHG emissions (MtCeq)', 'var_emissions', 'emissions']
        emissions_param = None
        for name in emissions_names:
            emissions_param = scenario.get_parameter(name)
            if emissions_param:
                break

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

    def calculate_crf(self, interest_rate: float, lifetime: float) -> float:
        """Calculates Capital Recovery Factor for annualized capital costs."""
        if interest_rate == 0:
            return 1 / lifetime

        # Handle infinite lifetime or very long lifetimes to prevent overflow
        lifetime = min(lifetime, 100)

        rate_factor = (1 + interest_rate) ** lifetime
        crf = (interest_rate * rate_factor) / (rate_factor - 1)
        return crf

    def calculate_electricity_cost_breakdown(self, scenario: ScenarioData, regions=None, electricity_commodity='electr') -> pd.DataFrame:
        """
        Analyzes a MESSAGEix scenario to break down electricity generation costs
        by technology and cost component (Capex, Opex, Fuels, Emissions).

        Returns DataFrame with unit costs ($/MWh) by technology and year.
        """
        print("DEBUG: Starting cost breakdown calculation")

        if regions is None:
            print(f"DEBUG: scenario.sets = {scenario.sets}")
            print(f"DEBUG: type(scenario.sets) = {type(scenario.sets)}")

            # Handle case where scenario.sets might be None or missing 'node'
            if scenario.sets and isinstance(scenario.sets, dict) and 'node' in scenario.sets:
                regions = list(scenario.sets['node'].values)
                print(f"DEBUG: Found regions in sets: {regions}")
            else:
                print("DEBUG: No regions in sets, trying parameter data")
                # Fallback: try to get regions from parameter data
                all_regions = set()
                for param_name, param in scenario.parameters.items():
                    print(f"DEBUG: Checking parameter {param_name}")
                    if hasattr(param.df, 'columns'):
                        print(f"DEBUG: Columns in {param_name}: {list(param.df.columns)}")
                        if 'node' in param.df.columns:
                            node_values = param.df['node'].unique()
                            all_regions.update(node_values)
                            print(f"DEBUG: Found node values: {node_values}")
                        elif 'region' in param.df.columns:
                            region_values = param.df['region'].unique()
                            all_regions.update(region_values)
                            print(f"DEBUG: Found region values: {region_values}")

                regions = list(all_regions) if all_regions else ['World']
                print(f"DEBUG: Final regions list: {regions}")

        # Get default interest rate for CRF calculation
        interest_rate = 0.05  # Default 5%
        try:
            interest_par = scenario.get_parameter('interest_rate')
            if interest_par and not interest_par.df.empty:
                interest_rate = interest_par.df['value'].mean()
        except:
            pass

        # Identify electricity generating technologies
        output_param = scenario.get_parameter('output')
        if output_param:
            elec_techs = output_param.df[output_param.df['commodity'] == electricity_commodity]['technology'].unique().tolist()
        else:
            # Fallback: use technologies from electricity generation data
            elec_gen_param = scenario.get_parameter('Electricity generation (TWh)')
            if elec_gen_param and not elec_gen_param.df.empty:
                # Get technology names from electricity generation data
                tech_cols = [col for col in elec_gen_param.df.columns if col not in ['year', 'year_act', 'node', 'region']]
                elec_techs = tech_cols
            else:
                # Final fallback: common electricity technologies
                elec_techs = ['coal', 'gas', 'nuclear', 'hydro', 'solar', 'wind']

        # Get activity (generation) data - try multiple parameter names
        act_param = None
        act_param_names = ['ACT', 'var_act', 'activity', 'Activity']
        for param_name in act_param_names:
            act_param = scenario.get_parameter(param_name)
            if act_param and not act_param.df.empty:
                break

        if not act_param or act_param.df.empty:
            # If no direct activity parameter, use electricity generation as proxy
            electricity_param_names = ['Electricity generation (TWh)', 'var_electricity', 'var_electricity_generation']
            for param_name in electricity_param_names:
                elec_param = scenario.get_parameter(param_name)
                if elec_param and not elec_param.df.empty:
                    # Use electricity generation data directly as activity proxy
                    # Convert from TWh to MWh and restructure for activity format
                    act_df = elec_param.df.copy()

                    # Convert electricity generation to activity-like format
                    print(f"DEBUG: Electricity gen DataFrame shape: {act_df.shape}")
                    print(f"DEBUG: Electricity gen DataFrame columns: {act_df.columns.tolist()}")
                    print(f"DEBUG: Electricity gen DataFrame sample:\n{act_df.head()}")

                    # This data is in wide format with technologies as columns
                    # Convert to long format for activity data
                    id_cols = ['year']  # Only year column exists
                    value_cols = [col for col in act_df.columns if col not in id_cols]

                    print(f"DEBUG: ID cols: {id_cols}, Value cols: {value_cols}")

                    # Melt wide format to long format
                    act_df = act_df.melt(id_vars=id_cols, value_vars=value_cols,
                                       var_name='technology', value_name='value')

                    print(f"DEBUG: After melt shape: {act_df.shape}")
                    print(f"DEBUG: After melt sample:\n{act_df.head()}")

                    # Convert units and add required columns
                    act_df['value'] = act_df['value'] * 1000000  # TWh to MWh
                    act_df['year_act'] = act_df['year']  # Copy year to year_act
                    act_df['node'] = 'World'  # Add node column
                    act_df['mode'] = 'M1'  # Default mode
                    act_df['time'] = 'year'  # Default time

                    print(f"DEBUG: Final activity DataFrame shape: {act_df.shape}")
                    print(f"DEBUG: Final activity DataFrame sample:\n{act_df.head()}")

                    # Create a parameter-like object
                    from core.data_models import Parameter
                    act_param = Parameter('ACT_synthetic', act_df, {'result_type': 'variable'})
                    break

            if not act_param:
                raise ValueError("Neither ACT nor electricity generation parameters found - cannot calculate generation costs")

        # Filter for electricity technologies and ensure node column exists
        act_df = act_param.df[act_param.df['technology'].isin(elec_techs)].copy()

        # Add node column if missing (for global/single-region data)
        if 'node' not in act_df.columns:
            act_df['node'] = 'World'

        # Total Generation per tech per year (sum over modes)
        gen_total = act_df.groupby(['node', 'year_act', 'technology'])['value'].sum().reset_index(name='total_gen_MWh')

        # Filter out technologies with zero generation BEFORE cost calculations
        gen_total = gen_total[gen_total['total_gen_MWh'] > 0.001].copy()

        print(f"DEBUG: Technologies with generation > 0: {gen_total['technology'].unique().tolist()}")
        print(f"DEBUG: Total technologies to process: {len(gen_total)}")

        # Filter the activity DataFrame to only include technologies with generation > 0
        active_techs = gen_total['technology'].unique()
        act_df = act_df[act_df['technology'].isin(active_techs)].copy()

        # --- Component Calculations ---

       # Try to find input files with cost parameters
        input_cost_scenario = self._load_input_costs()
        if input_cost_scenario:
            print("DEBUG: Found input files with cost parameters, using detailed costs")
            has_detailed_costs = True
            # Use input file scenario for cost calculations
            cost_scenario = input_cost_scenario
        else:
            print("DEBUG: No input files with costs found, checking current scenario")
            has_detailed_costs = False

        if has_detailed_costs:
            print("DEBUG: Using detailed cost parameters for calculation")
            # Variable Opex (VOM)
            vom_total = self._calculate_variable_opex(act_df, cost_scenario, elec_techs)

            # Check if VOM costs are all zero (no matching technologies)
            if vom_total['cost_vom_total'].sum() == 0:
                print("DEBUG: Detailed VOM costs are all zero - likely no matching technologies, falling back to simplified costs")
                has_detailed_costs = False
            else:
                print(f"DEBUG: Found non-zero VOM costs, total: ${vom_total['cost_vom_total'].sum():.2f}")

                # Fixed Opex (FOM)
                fom_total = self._calculate_fixed_opex(cost_scenario, elec_techs)

                # Fuel Costs
                fuel_total = self._calculate_fuel_costs(act_df, cost_scenario, elec_techs)

                # Emission Costs
                em_total = self._calculate_emission_costs(act_df, cost_scenario, elec_techs)

                # Annualized Investment Costs (CAPEX) - Most Complex
                capex_total = self._calculate_capex_costs(cost_scenario, elec_techs, interest_rate)

        if not has_detailed_costs:
            print("DEBUG: Using simplified price-based cost estimation")
            # Try to use available price data for simplified cost estimation
            cost_results = self._calculate_simplified_costs(act_df, scenario, elec_techs, interest_rate)

            vom_total = cost_results['vom']
            fom_total = cost_results['fom']
            fuel_total = cost_results['fuel']
            em_total = cost_results['em']
            capex_total = cost_results['capex']

        # --- Final Assembly ---
        final_df = gen_total.copy()

        # Initialize cost columns with zeros
        cost_cols = ['cost_capex_total', 'cost_fom_total', 'cost_vom_total', 'cost_fuel_total', 'cost_em_total']
        for col in cost_cols:
            final_df[col] = 0.0

        # Merge cost components that have data
        cost_dfs = [
            ('capex', capex_total),
            ('fom', fom_total),
            ('vom', vom_total),
            ('fuel', fuel_total),
            ('em', em_total)
        ]

        for cost_type, df in cost_dfs:
            if not df.empty and len(df) > 0:
                # Update the corresponding column with actual values
                col_name = f'cost_{cost_type}_total'
                merge_df = df[['node', 'year_act', 'technology', col_name]].copy()
                final_df = pd.merge(final_df, merge_df, on=['node', 'year_act', 'technology'], how='left', suffixes=('', '_new'))
                # Use the merged values where available, keep zeros otherwise
                final_df[col_name] = final_df[f'{col_name}_new'].fillna(final_df[col_name])
                final_df = final_df.drop(columns=[f'{col_name}_new'])

        # Calculate Unit Costs ($/MWh)
        for col in cost_cols:
            unit_col = col.replace('cost_', 'Unit_').replace('_total', '')
            final_df[unit_col] = final_df[col] / final_df['total_gen_MWh']

        # Calculate Total Unit Cost
        unit_cost_cols = [col for col in final_df.columns if col.startswith('Unit_')]
        final_df['Unit_Total_LCOE_Proxy'] = final_df[unit_cost_cols].sum(axis=1)

        return final_df

    def _load_input_costs(self) -> Optional[ScenarioData]:
        """Get the currently loaded input scenario if it has cost parameters."""
        print("DEBUG: Looking for input scenario in application...")

        if not self.main_window:
            print("DEBUG: No main window reference available")
            return None

        if not hasattr(self.main_window, 'input_manager'):
            print("DEBUG: Main window has no input_manager")
            return None

        # Try to get scenario by the selected input file path
        if hasattr(self.main_window, 'selected_input_file') and self.main_window.selected_input_file:
            scenario = self.main_window.input_manager.get_scenario_by_file_path(self.main_window.selected_input_file)
            if scenario and self._has_cost_parameters(scenario):
                print(f"DEBUG: Found input scenario with cost parameters: {self.main_window.selected_input_file}")
                return scenario

        # Fallback: try current scenario
        scenario = self.main_window.input_manager.get_current_scenario()
        if scenario and self._has_cost_parameters(scenario):
            print("DEBUG: Found current input scenario with cost parameters")
            return scenario

        print("DEBUG: No input scenario with cost parameters found - cost calculation cannot be performed")
        return None

    def _has_cost_parameters(self, scenario: ScenarioData) -> bool:
        """Check if a scenario has the required cost parameters."""
        required_cost_params = [
            'investment_cost',
            'fixed_cost',
            'variable_cost',
            'technical_lifetime'
        ]

        # Check if scenario has at least some of the key cost parameters
        cost_params_found = 0
        for param_name in required_cost_params:
            if scenario.get_parameter(param_name):
                cost_params_found += 1

        # Also check for historical capacity
        if scenario.get_parameter('historical_new_capacity'):
            cost_params_found += 1

        # Require at least 2 cost parameters to consider it a cost scenario
        return cost_params_found >= 2

    def _calculate_variable_opex(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
        """Calculate variable operating costs."""
        print("DEBUG: Calculating variable Opex...")

        # Return empty DataFrame for now - to be implemented
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_vom_total'])

    def _calculate_fixed_opex(self, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
        """Calculate fixed operating costs based on capacity."""
        print("DEBUG: Calculating fixed Opex...")

        # Return empty DataFrame for now - to be implemented
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fom_total'])

    def _calculate_fuel_costs(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
        """Calculate fuel costs."""
        # Return empty DataFrame for now - to be implemented
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_fuel_total'])

    def _calculate_emission_costs(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list) -> pd.DataFrame:
        """Calculate emission costs."""
        # Return empty DataFrame for now - to be implemented
        return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_em_total'])

    def _calculate_capex_costs(self, scenario: ScenarioData, elec_techs: list, interest_rate: float) -> pd.DataFrame:
        """Calculate annualized capital costs - the most complex component."""
        cap_new_param = scenario.get_parameter('CAP_NEW')
        inv_cost_param = scenario.get_parameter('investment_cost')
        lifetime_param = scenario.get_parameter('technical_lifetime')
        hist_cap_param = scenario.get_parameter('historical_new_capacity')

        if not cap_new_param or not inv_cost_param or not lifetime_param:
            return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])

        # Merge capacity investments with costs and lifetimes
        capex_df = pd.merge(cap_new_param.df, inv_cost_param.df,
                           on=['node', 'technology', 'year_vtg'],
                           how='inner', suffixes=('_cap', '_cost'))

        # Add lifetimes (try vintage-specific first, then technology-level)
        lifetime_df = lifetime_param.df.copy()
        capex_df = pd.merge(capex_df, lifetime_df,
                           on=['node', 'technology', 'year_vtg'], how='left')

        # Fill missing lifetimes
        if 'lifetime' not in capex_df.columns:
            capex_df['lifetime'] = 30
        else:
            capex_df['lifetime'] = capex_df['lifetime'].fillna(30)

        # Calculate CRF and annualized costs
        capex_df['crf'] = capex_df.apply(lambda row: self.calculate_crf(interest_rate, row['lifetime']), axis=1)
        capex_df['overnight_cost'] = capex_df['value_cap'] * capex_df['value_cost']
        capex_df['annualized_inv_cost_stream'] = capex_df['overnight_cost'] * capex_df['crf']

        # --- Handle Historical Capacity ---
        historical_capex = pd.DataFrame()
        if hist_cap_param and not hist_cap_param.df.empty:
            # Historical capacity has different structure - need to map to future years
            hist_df = hist_cap_param.df.copy()

            # Add costs and lifetimes for historical capacity
            hist_df = pd.merge(hist_df, inv_cost_param.df,
                              left_on=['node', 'technology', 'year_vtg'],
                              right_on=['node', 'technology', 'year_vtg'],
                              how='inner', suffixes=('_hist', '_cost'))

            # Add lifetimes for historical capacity
            hist_df = pd.merge(hist_df, lifetime_df,
                              on=['node', 'technology', 'year_vtg'], how='left')

            # Fill missing lifetimes
            if 'lifetime' not in hist_df.columns:
                hist_df['lifetime'] = 30
            else:
                hist_df['lifetime'] = hist_df['lifetime'].fillna(30)

            # Calculate CRF for historical capacity
            hist_df['crf'] = hist_df.apply(lambda row: self.calculate_crf(interest_rate, row['lifetime']), axis=1)
            hist_df['overnight_cost'] = hist_df['value_hist'] * hist_df['value_cost']
            hist_df['annualized_inv_cost_stream'] = hist_df['overnight_cost'] * hist_df['crf']

            # Expand historical capacity to all active years
            min_year = scenario.options.get('MinYear', 2020)
            max_year = scenario.options.get('MaxYear', 2050)
            if 'year' in scenario.sets:
                model_years = sorted(scenario.sets['year'].tolist())
            else:
                model_years = list(range(min_year, max_year + 1))

            expanded_hist_capex = []
            for _, row in hist_df.iterrows():
                vtg = row['year_vtg']
                life = row['lifetime']
                stream_cost = row['annualized_inv_cost_stream']

                # Find years where this historical vintage is still active
                active_years = [y for y in model_years if vtg <= y < vtg + life]

                for year_act in active_years:
                    expanded_hist_capex.append({
                        'node': row['node'],
                        'technology': row['technology'],
                        'year_act': year_act,
                        'cost_capex_total': stream_cost
                    })

            historical_capex = pd.DataFrame(expanded_hist_capex)

        # --- Combine Model Horizon and Historical Capacity ---
        # Expand model horizon capacity to all active years
        min_year = scenario.options.get('MinYear', 2020)
        max_year = scenario.options.get('MaxYear', 2050)
        if 'year' in scenario.sets:
            model_years = sorted(scenario.sets['year'].tolist())
        else:
            model_years = list(range(min_year, max_year + 1))

        expanded_capex = []
        for _, row in capex_df.iterrows():
            vtg = row['year_vtg']
            life = row['lifetime']
            stream_cost = row['annualized_inv_cost_stream']

            # Find years where this vintage is active
            active_years = [y for y in model_years if vtg <= y < vtg + life]

            for year_act in active_years:
                expanded_capex.append({
                    'node': row['node'],
                    'technology': row['technology'],
                    'year_act': year_act,
                    'cost_capex_total': stream_cost
                })

        capex_long_df = pd.DataFrame(expanded_capex)

        # Combine with historical capacity if available
        if not historical_capex.empty:
            capex_long_df = pd.concat([capex_long_df, historical_capex], ignore_index=True)

        # Sum costs for same technology in same operation year
        if not capex_long_df.empty:
            return capex_long_df.groupby(['node', 'year_act', 'technology'])['cost_capex_total'].sum().reset_index()
        else:
            return pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_capex_total'])

    def _calculate_simplified_costs(self, act_df: pd.DataFrame, scenario: ScenarioData, elec_techs: list, interest_rate: float) -> Dict[str, pd.DataFrame]:
        """Calculate simplified costs using available price data."""
        print("DEBUG: Starting simplified cost calculation")

        # Return empty DataFrames for each cost component when simplified calculation is not available
        empty_df = pd.DataFrame(columns=['node', 'year_act', 'technology', 'cost_total'])
        return {
            'vom': empty_df.copy(),
            'fom': empty_df.copy(),
            'fuel': empty_df.copy(),
            'em': empty_df.copy(),
            'capex': empty_df.copy()
        }

    # Keep remove_file method for backward compatibility (inherited from BaseDataManager)
