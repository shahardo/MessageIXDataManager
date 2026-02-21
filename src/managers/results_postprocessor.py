"""
Results Postprocessor - Facade/Orchestrator.

Delegates all domain-specific calculations to analyzers in src/analysis/:
  - ElectricityAnalyzer: generation, capacity, LCOE, costs
  - EmissionsAnalyzer: GHG emissions by type, sector, fuel
  - EnergyBalanceAnalyzer: primary/final energy, trade, feedstock
  - FuelAnalyzer: gas, coal, oil, biomass supply/use
  - SectorAnalyzer: buildings, industry, transport
  - PriceAnalyzer: energy prices

This file is kept as a thin facade to maintain backward compatibility with
code that imports ResultsPostprocessor, run_postprocessing, or
add_postprocessed_results.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, List, Optional, Any

from core.data_models import ScenarioData, Parameter
from analysis.base_analyzer import ScenarioDataWrapper
from analysis.electricity_analyzer import ElectricityAnalyzer
from analysis.emissions_analyzer import EmissionsAnalyzer
from analysis.energy_balance_analyzer import EnergyBalanceAnalyzer
from analysis.fuel_analyzer import FuelAnalyzer
from analysis.sector_analyzer import SectorAnalyzer
from analysis.price_analyzer import PriceAnalyzer


class ResultsPostprocessor:
    """
    Facade/orchestrator for MESSAGEix results postprocessing.

    Delegates all calculations to domain-specific analyzers in src/analysis/.
    All results are accumulated in a shared dictionary and converted to
    Parameter objects at the end of processing.
    """

    # Unit conversion factors (kept for backward compatibility)
    UNIT_GWA_TO_PJ = 8.76 * 3.6
    UNIT_GWA_TO_TWH = 8760 / 1000
    UNIT_GW_TO_MW = 1000

    def __init__(self, scenario: ScenarioData):
        """
        Initialize the postprocessor.

        Args:
            scenario: ScenarioData containing input parameters and result variables
        """
        self.scenario = scenario
        self.msg = ScenarioDataWrapper(scenario)
        self.results: Dict[str, pd.DataFrame] = {}

        # Default plot years - can be overridden
        self.plotyrs = list(range(2020, 2051, 5))

    def set_plot_years(self, years: List[int]) -> None:
        """Set the years to include in calculations."""
        self.plotyrs = years

    def process(self, nodeloc: Optional[str] = None) -> Dict[str, Parameter]:
        """
        Run all postprocessing calculations and return derived parameters.

        Args:
            nodeloc: Optional node location filter (e.g., 'World')

        Returns:
            Dict of parameter_name -> Parameter objects
        """
        if not self.msg.has_solution():
            print("Warning: Scenario has no solution - cannot run postprocessing")
            return {}

        # Determine first model year for historical data cutoff
        try:
            yr = int(self.msg.set('cat_year', {'type_year': 'firstmodelyear'})['year'].iloc[0])
        except Exception:
            yr = min(self.plotyrs)

        # Auto-detect node location if not provided
        if nodeloc is None:
            nodes = self.msg.set('node')
            if len(nodes) > 0:
                nodeloc = nodes.iloc[0]
            else:
                act = self.msg.var('ACT')
                if not act.empty and 'node_loc' in act.columns:
                    nodeloc = act['node_loc'].iloc[0]
                else:
                    nodeloc = 'World'

        # Shared state passed by reference to all analyzers
        shared_args = (self.msg, self.scenario, self.plotyrs, self.results)

        # Orchestrate domain analyzers
        ElectricityAnalyzer(*shared_args).calculate(nodeloc, yr)
        EmissionsAnalyzer(*shared_args).calculate(nodeloc, yr)
        EnergyBalanceAnalyzer(*shared_args).calculate(nodeloc, yr)
        FuelAnalyzer(*shared_args).calculate(nodeloc, yr)
        SectorAnalyzer(*shared_args).calculate(nodeloc, yr)
        PriceAnalyzer(*shared_args).calculate(nodeloc, yr)

        return self._create_parameters()

    # =========================================================================
    # Parameter Conversion
    # =========================================================================

    def _create_parameters(self) -> Dict[str, Parameter]:
        """Convert pivot table results to Parameter objects."""
        parameters = {}

        for name, df in self.results.items():
            if df.empty:
                continue

            long_df = self._pivot_to_long(df, name)

            if long_df.empty:
                continue

            dims = list(long_df.columns[:-1])  # All columns except 'value'

            metadata = {
                'units': self._extract_units(name),
                'desc': f'Postprocessed result: {name}',
                'dims': dims,
                'value_column': 'value',
                'parameter_type': 'result',
                'result_type': 'postprocessed',
                'source': 'postprocessor'
            }

            param = Parameter(name, long_df, metadata)
            parameters[name] = param

        return parameters

    def _pivot_to_long(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Convert pivot table (year index, categories columns) to long format.

        If the DataFrame is already in long format (has 'value' column), it is
        returned as-is after filtering out zero values.
        """
        if df.empty:
            return pd.DataFrame()

        col_list = list(df.columns)
        is_long_format = (
            'value' in col_list and
            isinstance(df.index, pd.RangeIndex) and
            ('year' in col_list or 'year_act' in col_list)
        )

        if is_long_format:
            try:
                long_df = df.query('value != 0').reset_index(drop=True)
            except Exception:
                value_col_idx = col_list.index('value')
                mask = df.iloc[:, value_col_idx].values != 0
                long_df = df[mask].reset_index(drop=True)
            return long_df

        # Reset index to make year a column
        df = df.reset_index()

        index_col = df.columns[0]
        value_cols = [col for col in df.columns if col != index_col]

        if not value_cols:
            return pd.DataFrame()

        long_df = df.melt(
            id_vars=[index_col],
            value_vars=value_cols,
            var_name='category',
            value_name='value'
        )

        if index_col != 'year':
            long_df = long_df.rename(columns={index_col: 'year'})

        long_df = long_df[long_df['value'] != 0]

        return long_df

    def _extract_units(self, name: str) -> str:
        """Extract units from parameter name (looks for text in parentheses)."""
        if '(' in name and ')' in name:
            start = name.rfind('(')
            end = name.rfind(')')
            return name[start + 1:end]
        return 'N/A'

    # =========================================================================
    # Backward-Compatible Delegation Methods
    # Tests and external code that accessed private methods directly on
    # ResultsPostprocessor can continue to work via these thin delegates.
    # =========================================================================

    def _make_base_analyzer(self):
        """Create a BaseAnalyzer instance for delegation."""
        from analysis.base_analyzer import BaseAnalyzer
        return BaseAnalyzer(self.msg, self.scenario, self.plotyrs, self.results)

    def _group(self, df, groupby, result, limit, lyr, keep_long=False):
        """Delegate to BaseAnalyzer._group."""
        return self._make_base_analyzer()._group(df, groupby, result, limit, lyr, keep_long)

    def _model_output(self, tecs, nodeloc, parname, coms=None):
        """Delegate to BaseAnalyzer._model_output."""
        return self._make_base_analyzer()._model_output(tecs, nodeloc, parname, coms)

    def _attach_history(self, tec):
        """Delegate to BaseAnalyzer._attach_history."""
        return self._make_base_analyzer()._attach_history(tec)

    def _calculate_energy_exports_by_fuel(self, nodeloc, yr):
        """Delegate to EnergyBalanceAnalyzer._calculate_energy_exports_by_fuel."""
        EnergyBalanceAnalyzer(self.msg, self.scenario, self.plotyrs, self.results)._calculate_energy_exports_by_fuel(nodeloc, yr)

    def _calculate_energy_imports_by_fuel(self, nodeloc, yr):
        """Delegate to EnergyBalanceAnalyzer._calculate_energy_imports_by_fuel."""
        EnergyBalanceAnalyzer(self.msg, self.scenario, self.plotyrs, self.results)._calculate_energy_imports_by_fuel(nodeloc, yr)

    def _calculate_feedstock_by_fuel(self, nodeloc, yr):
        """Delegate to EnergyBalanceAnalyzer._calculate_feedstock_by_fuel."""
        EnergyBalanceAnalyzer(self.msg, self.scenario, self.plotyrs, self.results)._calculate_feedstock_by_fuel(nodeloc, yr)

    def _calculate_electricity_price_by_source(self, nodeloc, yr):
        """Delegate to ElectricityAnalyzer._calculate_electricity_price_by_source."""
        ElectricityAnalyzer(self.msg, self.scenario, self.plotyrs, self.results)._calculate_electricity_price_by_source(nodeloc, yr)


# =============================================================================
# Module-level convenience functions
# =============================================================================

def run_postprocessing(scenario: ScenarioData,
                       nodeloc: Optional[str] = None,
                       plot_years: Optional[List[int]] = None) -> Dict[str, Parameter]:
    """
    Run postprocessing on a scenario and return derived parameters.

    Args:
        scenario: ScenarioData containing input parameters and result variables
        nodeloc: Optional node location filter
        plot_years: Optional list of years to include (default: 2020-2050 by 5)

    Returns:
        Dict of parameter_name -> Parameter objects
    """
    processor = ResultsPostprocessor(scenario)

    if plot_years:
        processor.set_plot_years(plot_years)

    return processor.process(nodeloc)


def add_postprocessed_results(scenario: ScenarioData,
                              nodeloc: Optional[str] = None,
                              plot_years: Optional[List[int]] = None) -> int:
    """
    Run postprocessing and add results directly to the scenario.

    Args:
        scenario: ScenarioData to add results to
        nodeloc: Optional node location filter
        plot_years: Optional list of years to include

    Returns:
        Number of parameters added
    """
    parameters = run_postprocessing(scenario, nodeloc, plot_years)

    count = 0
    for name, param in parameters.items():
        scenario.add_parameter(param, mark_modified=False, add_to_history=False)
        count += 1

    return count
