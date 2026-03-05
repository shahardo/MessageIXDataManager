"""
Results File Dashboard - displays specific metrics and charts for results files

Shows a dashboard with metrics at the top and 4 charts in a 2x2 grid when a results file is selected.
"""

from typing import Any, Optional

import pandas as pd

from .dashboard_chart_mixin import DashboardChartMixin
from ui.components.base_dashboard import BaseDashboard


class ResultsFileDashboard(DashboardChartMixin, BaseDashboard):
    """
    Dashboard widget for displaying results file specific visualizations.

    Shows metrics at the top and 4 charts in a 2x2 grid:
    - Top row: Total primary energy (2050), Total electricity (2050),
               % Clean electricity (2050), Total emissions (2050)
    - Charts: Primary energy demand over years, Electricity generation by source,
              Primary energy mix pie (2050), Electricity sources pie (2050)
    """

    def __init__(self, results_analyzer):
        super().__init__(ui_file='src/ui/results_file_dashboard.ui')
        self.results_analyzer = results_analyzer

        if self._ui_loaded and hasattr(self, 'primary_energy_demand_chart'):
            # Overview tab charts
            self.chart_views = {
                'primary_energy_demand': self.primary_energy_demand_chart,
                'electricity_generation': self.electricity_generation_chart,
                'primary_energy_pie': self.primary_energy_pie_chart,
                'electricity_pie': self.electricity_pie_chart
            }

            # Electricity tab charts and table
            self.electricity_chart_views = {
                'electricity_generation_by_fuel': self.electricity_generation_by_fuel_chart,
                'electricity_costs_by_fuel': self.electricity_costs_by_fuel_chart
            }

            # Cost breakdown table
            if hasattr(self, 'cost_breakdown_table'):
                self.cost_breakdown_table = self.cost_breakdown_table

            # Map metric labels from UI file
            self.metric_labels = {
                'primary_energy_2050': self.metric1_value,
                'electricity_2050': self.metric2_value,
                'clean_electricity_pct': self.metric3_value,
                'emissions_2050': self.metric4_value
            }

            # Enable JavaScript for chart views
            self.setup_chart_view_settings(self.chart_views)
            self.setup_chart_view_settings(self.electricity_chart_views)
        else:
            # For testing without UI
            self.chart_views = {}
            self.electricity_chart_views = {}
            self.metric_labels = {}

    def update_dashboard(self, scenario: Any):
        """Update the dashboard with the metrics and charts"""
        self.current_scenario = scenario
        self._render_metrics()
        self._render_charts()

    def _render_metrics(self):
        """Calculate and display the dashboard metrics"""
        try:
            if not self.current_scenario:
                # Clear metrics if no scenario loaded
                for label in self.metric_labels.values():
                    label.setText("--")
                return

            # Calculate metrics using the results analyzer
            metrics = self.results_analyzer.calculate_dashboard_metrics(self.current_scenario)

            # Update metric labels with formatted values (only if labels exist)
            if 'primary_energy_2050' in self.metric_labels:
                # Primary energy (PJ)
                primary_energy = metrics['primary_energy_2050']
                self.metric_labels['primary_energy_2050'].setText(f"{primary_energy:.1f} PJ")

                # Electricity (TWh)
                electricity = metrics['electricity_2050']
                self.metric_labels['electricity_2050'].setText(f"{electricity:.1f} TWh")

                # Clean electricity percentage
                clean_pct = metrics['clean_electricity_pct']
                self.metric_labels['clean_electricity_pct'].setText(f"{clean_pct:.1f}%")

                # Emissions (ktCO2e)
                emissions = metrics['emissions_2050']
                self.metric_labels['emissions_2050'].setText(f"{emissions:.1f} ktCO₂e")

        except Exception as e:
            print(f"Error calculating metrics: {str(e)}")
            # Show error in metric labels
            for label in self.metric_labels.values():
                label.setText("Error")

    def _get_electricity_param(self) -> Optional[object]:
        """
        Return the 'Electricity generation (TWh)' parameter, building it on-the-fly
        from var_ACT when the postprocessed parameter is absent (e.g. raw data file).

        Returns a Parameter-like object with a wide-format DataFrame (year × technology),
        or None if no usable activity data is found.
        """
        from core.data_models import Parameter

        # 1. Prefer already-postprocessed parameter
        param = self.current_scenario.get_parameter('Electricity generation (TWh)')
        if param is not None and not param.df.empty:
            return param

        # 2. Fall back to raw var_ACT (or var_act)
        act_param = None
        for name in ('ACT', 'var_ACT', 'var_act', 'activity'):
            act_param = self.current_scenario.get_parameter(name)
            if act_param is not None and not act_param.df.empty:
                break
        if act_param is None:
            return None

        act_df = act_param.df.copy()

        # Normalise column names (var_* uses node_loc / lvl)
        if 'node_loc' in act_df.columns and 'node' not in act_df.columns:
            act_df = act_df.rename(columns={'node_loc': 'node'})
        if 'year_act' not in act_df.columns and 'year' in act_df.columns:
            act_df = act_df.rename(columns={'year': 'year_act'})
        val_col = 'lvl' if 'lvl' in act_df.columns else 'value'

        # Discover electricity-producing technologies via the output parameter
        elec_techs = None
        output_param = self.current_scenario.get_parameter('output')
        if output_param is not None and not output_param.df.empty:
            odf = output_param.df
            commodity_col = next((c for c in ('commodity',) if c in odf.columns), None)
            if commodity_col:
                mask = odf[commodity_col].str.lower().isin(('electr', 'electricity', 'elec'))
                elec_techs = odf.loc[mask, 'technology'].unique().tolist()

        if elec_techs:
            act_df = act_df[act_df['technology'].isin(elec_techs)]

        if act_df.empty or 'year_act' not in act_df.columns:
            return None

        # Aggregate and pivot to wide format (year × technology)
        grouped = (
            act_df.groupby(['year_act', 'technology'])[val_col]
            .sum()
            .reset_index()
        )
        wide = grouped.pivot(index='year_act', columns='technology', values=val_col).fillna(0)
        wide.index.name = 'year'
        wide = wide.reset_index()

        # Drop all-zero technology columns
        tech_cols = [c for c in wide.columns if c != 'year']
        wide = wide[[c for c in wide.columns if c == 'year' or wide[c].abs().max() > 0.001]]

        if wide.shape[1] <= 1:  # only the year column remains
            return None

        return Parameter('Electricity generation (TWh)', wide, {'units': 'GWa (raw var_ACT)'})

    def _render_charts(self):
        """Render all 4 charts: primary energy demand, electricity generation, and pie charts"""
        try:
            if not self.current_scenario:
                # Show placeholder if no scenario loaded
                for chart_view in self.chart_views.values():
                    self.show_chart_placeholder(chart_view, "No data loaded")
                return

            # Primary energy chart: get data from "Primary energy supply (PJ)" parameter
            primary_energy_param = self.current_scenario.get_parameter('Primary energy supply (PJ)')
            if primary_energy_param and not primary_energy_param.df.empty and 'primary_energy_demand' in self.chart_views:
                self.render_energy_chart(
                    primary_energy_param,
                    self.chart_views['primary_energy_demand'],
                    'Primary Energy Supply (PJ)',
                    'Primary Energy Supply by Source'
                )
            elif 'primary_energy_demand' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['primary_energy_demand'],
                    "No primary energy supply data available"
                )

            # Electricity chart
            electricity_param = self._get_electricity_param()
            if electricity_param and 'electricity_generation' in self.chart_views:
                self.render_energy_chart(
                    electricity_param,
                    self.chart_views['electricity_generation'],
                    'Electricity Generation (TWh)',
                    'Electricity Generation by Source'
                )
            elif 'electricity_generation' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['electricity_generation'],
                    "No electricity generation data available"
                )

            # Primary energy pie chart: get data from "Primary energy supply (PJ)" parameter, year 2050
            primary_energy_param = self.current_scenario.get_parameter('Primary energy supply (PJ)')
            if primary_energy_param and not primary_energy_param.df.empty and 'primary_energy_pie' in self.chart_views:
                self.render_energy_pie_chart(
                    primary_energy_param,
                    self.chart_views['primary_energy_pie'],
                    'Primary Energy Mix (2050)',
                    'Primary Energy Mix by Fuel in 2050'
                )
            elif 'primary_energy_pie' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['primary_energy_pie'],
                    "No primary energy supply data available"
                )

            # Electricity pie chart (reuse already-resolved param)
            if electricity_param and 'electricity_pie' in self.chart_views:
                self.render_energy_pie_chart(
                    electricity_param,
                    self.chart_views['electricity_pie'],
                    'Electricity Sources (2050)',
                    'Electricity Sources in 2050'
                )
            elif 'electricity_pie' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['electricity_pie'],
                    "No electricity generation data available"
                )

            # Render electricity tab charts
            self._render_electricity_charts()

        except Exception as e:
            print(f"Error rendering charts: {str(e)}")
            for chart_view in self.chart_views.values():
                self.show_chart_placeholder(chart_view, f"Error: {str(e)}")
            for chart_view in self.electricity_chart_views.values():
                self.show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_electricity_charts(self):
        """Render electricity tab charts: generation and costs by fuel"""
        try:
            if not self.current_scenario:
                # Show placeholder if no scenario loaded
                for chart_view in self.electricity_chart_views.values():
                    self.show_chart_placeholder(chart_view, "No data loaded")
                return

            # Electricity generation chart (same as overview but different title)
            electricity_param = self._get_electricity_param()
            if electricity_param and 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self.render_energy_chart(
                    electricity_param,
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    'Electricity Generation by Fuel Source',
                    'Electricity Generation by Fuel Source'
                )
            elif 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    "No electricity generation data available"
                )

            # Electricity costs chart
            if 'electricity_costs_by_fuel' in self.electricity_chart_views:
                self._render_electricity_costs_chart()

        except Exception as e:
            print(f"Error rendering electricity charts: {str(e)}")
            for chart_view in self.electricity_chart_views.values():
                self.show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_electricity_costs_chart(self):
        """Render electricity costs by fuel source chart"""
        try:
            # Calculate electricity costs breakdown
            cost_df = self.results_analyzer.calculate_electricity_cost_breakdown(self.current_scenario)

            if cost_df.empty:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No electricity cost data available"
                )
                return

            # Map technologies to fuel categories for aggregation
            fuel_mapping = {
                'Coal': ['coal'],
                'Fuels': ['heavy fuel oil', 'light oil'],
                'Natural Gas': ['natural gas (ST + CT)', 'natural gas (CC)'],
                'Nuclear': ['nuclear'],
                'Solar': ['solar PV', 'solar CSP'],
                'Wind': ['wind onshore', 'wind offshore'],
                'Hydro': ['hydro'],
                'Biomass': ['biomass'],
                'Geothermal': ['geothermal'],
            }

            cost_df['fuel_category'] = 'Other'
            for fuel, techs in fuel_mapping.items():
                mask = cost_df['technology'].str.lower().isin([t.lower() for t in techs])
                cost_df.loc[mask, 'fuel_category'] = fuel

            # Aggregate by fuel category and year
            fuel_costs = cost_df.groupby(['fuel_category', 'year_act'])['Unit_Total_LCOE_Proxy'].sum().reset_index()

            # Populate the cost breakdown table
            self._populate_cost_breakdown_table(cost_df)

            # Pivot to get years as columns, fuels as rows for charting
            pivot_df = fuel_costs.pivot(index='fuel_category', columns='year_act', values='Unit_Total_LCOE_Proxy').fillna(0)

            years = sorted(pivot_df.columns.tolist())
            data_dict = {}
            for fuel in pivot_df.index:
                data_dict[fuel] = pivot_df.loc[fuel, years].tolist()

            if not data_dict:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No cost data to display"
                )
                return

            self.render_stacked_bar_chart(
                self.electricity_chart_views['electricity_costs_by_fuel'],
                years,
                data_dict,
                'Electricity Costs by Fuel Source ($/MWh)',
                'Electricity Costs by Fuel Source'
            )

        except Exception as e:
            print(f"Error calculating electricity costs: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_chart_placeholder(
                self.electricity_chart_views['electricity_costs_by_fuel'],
                "Error calculating electricity costs"
            )

    def _populate_cost_breakdown_table(self, cost_df):
        """Populate the cost breakdown table with technology cost data"""
        try:
            if not hasattr(self, 'cost_breakdown_table'):
                return

            # Clear existing table
            self.cost_breakdown_table.clear()
            self.cost_breakdown_table.setRowCount(0)
            self.cost_breakdown_table.setColumnCount(0)

            if cost_df.empty:
                return

            # Get unique technologies and years
            technologies = sorted(cost_df['technology'].unique())
            years = sorted(cost_df['year_act'].unique())

            # Set up table dimensions
            num_rows = 6  # Capex, Fixed Opex, Var Opex, Fuel, Emissions, Total LCOE
            num_cols = len(technologies) + 1  # +1 for the row headers

            self.cost_breakdown_table.setRowCount(num_rows)
            self.cost_breakdown_table.setColumnCount(num_cols)

            # Set column headers (technologies)
            self.cost_breakdown_table.setHorizontalHeaderLabels(['Cost Component'] + technologies)

            # Set row labels
            row_labels = ['Capex ($/MWh)', 'Fixed Opex ($/MWh)', 'Var Opex ($/MWh)',
                         'Fuel ($/MWh)', 'Emissions ($/MWh)', 'Total LCOE ($/MWh)']
            self.cost_breakdown_table.setVerticalHeaderLabels(row_labels)

            # Define cost components
            cost_components = ['Unit_capex', 'Unit_fom', 'Unit_vom', 'Unit_fuel', 'Unit_em', 'Unit_Total_LCOE_Proxy']

            # Populate table data
            for row_idx, component in enumerate(cost_components):
                # First column: cost component name
                from PyQt5.QtWidgets import QTableWidgetItem
                self.cost_breakdown_table.setItem(row_idx, 0, QTableWidgetItem(row_labels[row_idx]))

                # Subsequent columns: values for each technology
                for col_idx, tech in enumerate(technologies, 1):
                    tech_data = cost_df[cost_df['technology'] == tech]

                    if not tech_data.empty and component in tech_data.columns:
                        # Calculate average across all years for this technology
                        avg_cost = tech_data[component].mean()
                        cost_str = f"{avg_cost:.1f}"
                    else:
                        cost_str = "0.0"

                    self.cost_breakdown_table.setItem(row_idx, col_idx, QTableWidgetItem(cost_str))

            # Resize columns to fit content
            self.cost_breakdown_table.resizeColumnsToContents()

        except Exception as e:
            print(f"Error populating cost breakdown table: {str(e)}")
            import traceback
            traceback.print_exc()
