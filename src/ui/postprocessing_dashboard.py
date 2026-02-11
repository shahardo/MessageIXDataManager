"""
Postprocessing Dashboard - displays metrics and charts from postprocessed analysis.

Shows a dashboard with metrics at the top and charts in tabs when the
"Postprocessed Results" section header is clicked in the parameter tree.
Uses the same layout and metrics as the Results File Dashboard but reads
from postprocessed parameters (e.g. "Primary energy supply (PJ)",
"Electricity generation by source (TWh)").

Controls:
- "Limit years" checkbox: when checked, bar charts show only years within
  the MainWindow min_year–max_year range (from the data_display year options).
- "Pie year" combo: selects the representative year for pie charts.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5 import uic
import pandas as pd
from typing import Any, Optional

from core.data_models import Parameter
from core.user_preferences import UserPreferences
from .dashboard_chart_mixin import DashboardChartMixin



class PostprocessingDashboard(DashboardChartMixin, QWidget):
    """
    Dashboard widget for displaying postprocessing analysis visualizations.

    Shows metrics at the top and charts in two tabs:
    - Overview tab: 2x2 grid with primary energy bar, electricity by source bar,
                    primary energy pie, electricity sources pie
    - Electricity tab: generation by fuel bar, costs by fuel bar, cost breakdown table

    A controls row between metrics and tabs provides:
    - Checkbox to limit bar-chart years to model-year steps (default on)
    - ComboBox to choose the representative year for pie charts (default 2050)
    """

    def __init__(self, results_analyzer, user_prefs: Optional[UserPreferences] = None):
        super().__init__()
        self.results_analyzer = results_analyzer
        self.current_scenario = None

        # Default control references (overwritten by uic.loadUi when successful)
        self.limitYearsCheckbox = None
        self.pieYearCombo = None
        self.userPreferencesButton = None

        # Shared user preferences (fallback to standalone instance for tests)
        self.user_prefs: UserPreferences = user_prefs or UserPreferences(parent=self)
        self.user_prefs.changed.connect(self._on_user_prefs_changed)

        # Load UI from .ui file
        ui_file = 'src/ui/postprocessing_dashboard.ui'
        ui_loaded = False
        try:
            uic.loadUi(ui_file, self)
            print("Postprocessing dashboard UI loaded successfully")
            ui_loaded = True
        except Exception as e:
            print(f"Error loading postprocessing dashboard UI: {e}")

        if ui_loaded and hasattr(self, 'primary_energy_demand_chart'):
            # Overview tab charts
            self.chart_views = {
                'primary_energy_demand': self.primary_energy_demand_chart,
                'electricity_generation': self.electricity_generation_chart,
                'primary_energy_pie': self.primary_energy_pie_chart,
                'electricity_pie': self.electricity_pie_chart
            }

            # Electricity tab charts
            self.electricity_chart_views = {
                'electricity_generation_by_fuel': self.electricity_generation_by_fuel_chart,
                'electricity_costs_by_fuel': self.electricity_costs_by_fuel_chart
            }

            # Energy Balance tab charts
            self.energy_balance_chart_views = {
                'eb_primary_supply': self.eb_primary_supply_chart,
                'eb_final_consumption': self.eb_final_consumption_chart,
                'eb_imports': self.eb_imports_chart,
                'eb_exports': self.eb_exports_chart,
            }

            # Fuels tab charts
            self.fuels_chart_views = {
                'fuels_gas_supply': self.fuels_gas_supply_chart,
                'fuels_gas_use': self.fuels_gas_use_chart,
                'fuels_oil_supply': self.fuels_oil_supply_chart,
                'fuels_oil_use': self.fuels_oil_use_chart,
            }

            # Sectoral Use tab charts
            self.sectoral_chart_views = {
                'sectoral_buildings': self.sectoral_buildings_chart,
                'sectoral_industry': self.sectoral_industry_chart,
                'sectoral_electricity': self.sectoral_electricity_chart,
                'sectoral_transport': self.sectoral_transport_chart,
            }

            # Emissions tab charts
            self.emissions_chart_views = {
                'emissions_total': self.emissions_total_chart,
                'emissions_by_tech': self.emissions_by_tech_chart,
                'emissions_by_type': self.emissions_by_type_chart,
                'emissions_by_fuel': self.emissions_by_fuel_chart,
            }

            # Cost breakdown table
            if hasattr(self, 'cost_breakdown_table'):
                self.cost_breakdown_table = self.cost_breakdown_table

            # Metric labels
            self.metric_labels = {
                'primary_energy_2050': self.metric1_value,
                'electricity_2050': self.metric2_value,
                'clean_electricity_pct': self.metric3_value,
                'emissions_2050': self.metric4_value
            }

            # Configure chart view settings via mixin
            self.setup_chart_view_settings(self.chart_views)
            self.setup_chart_view_settings(self.electricity_chart_views)
            self.setup_chart_view_settings(self.energy_balance_chart_views)
            self.setup_chart_view_settings(self.fuels_chart_views)
            self.setup_chart_view_settings(self.sectoral_chart_views)
            self.setup_chart_view_settings(self.emissions_chart_views)

            # Sync checkbox to current prefs (UI default may differ)
            self.limitYearsCheckbox.setChecked(self.user_prefs.limit_enabled)

            # Connect control signals — re-render charts when changed
            self.limitYearsCheckbox.toggled.connect(self._on_controls_changed)
            self.pieYearCombo.currentIndexChanged.connect(self._on_controls_changed)
            if self.userPreferencesButton is not None:
                self.userPreferencesButton.clicked.connect(self._show_year_options_dialog)
        else:
            # For testing without UI
            self.chart_views = {}
            self.electricity_chart_views = {}
            self.energy_balance_chart_views = {}
            self.fuels_chart_views = {}
            self.sectoral_chart_views = {}
            self.emissions_chart_views = {}
            self.metric_labels = {}

    # ------------------------------------------------------------------
    # Control helpers
    # ------------------------------------------------------------------

    def _get_pie_year(self) -> int:
        """Return the currently selected pie-chart year (default 2050)."""
        if self.pieYearCombo is not None and self.pieYearCombo.count() > 0:
            text = self.pieYearCombo.currentText()
            try:
                return int(text)
            except (ValueError, TypeError):
                pass
        return 2050

    def _is_limit_years(self) -> bool:
        """Return True if year limiting is enabled in shared preferences."""
        return self.user_prefs.limit_enabled

    def _populate_year_combo(self):
        """Populate the pie-year combo from available data years."""
        if self.pieYearCombo is None:
            return

        years = set()
        if self.current_scenario:
            for name in ('Primary energy supply (PJ)',
                         'Electricity generation by source (TWh)',
                         'Electricity generation (TWh)'):
                param = self.current_scenario.get_parameter(name)
                if param and not param.df.empty:
                    year_col = 'year' if 'year' in param.df.columns else 'year_act'
                    years.update(int(y) for y in param.df[year_col].unique())

        # Remember previous selection so we can restore it
        prev = self.pieYearCombo.currentText()

        self.pieYearCombo.blockSignals(True)
        self.pieYearCombo.clear()
        for y in sorted(years):
            self.pieYearCombo.addItem(str(y))

        # Restore previous selection, or default to 2050
        target = prev if prev in [str(y) for y in years] else '2050'
        idx = self.pieYearCombo.findText(target)
        if idx >= 0:
            self.pieYearCombo.setCurrentIndex(idx)
        elif self.pieYearCombo.count() > 0:
            # Fall back to last available year
            self.pieYearCombo.setCurrentIndex(self.pieYearCombo.count() - 1)
        self.pieYearCombo.blockSignals(False)

    def _filter_param_years(self, param) -> 'Parameter':
        """Return a Parameter with years filtered to the min–max range.

        When the 'Limit years' checkbox is checked, filters on ALL year
        columns found (year, year_act, year_vtg) — matching the behaviour
        of data_display_widget._apply_year_filtering.  Otherwise returns
        the param as-is.
        """
        if param is None:
            return param
        if not self._is_limit_years():
            print(f"DEBUG _filter: limit OFF → returning all for '{param.name}'")
            return param
        df = param.df
        filtered_df = df.copy()
        filtered_any = False
        for year_col in ('year', 'year_act', 'year_vtg'):
            if year_col in filtered_df.columns:
                try:
                    year_values = pd.to_numeric(filtered_df[year_col], errors='coerce')
                    mask = (year_values >= self.user_prefs.min_year) & (year_values <= self.user_prefs.max_year)
                    before = len(filtered_df)
                    filtered_df = filtered_df[mask]
                    filtered_any = True
                    print(f"DEBUG _filter: '{param.name}' col={year_col} "
                          f"range=[{self.user_prefs.min_year},{self.user_prefs.max_year}] "
                          f"{before}→{len(filtered_df)} rows")
                except (TypeError, ValueError):
                    pass
        if not filtered_any or filtered_df.empty:
            print(f"DEBUG _filter: no effect or empty → returning original for '{param.name}'")
            return param
        return Parameter(param.name, filtered_df, param.metadata)

    def _show_year_options_dialog(self):
        """Show the year range options dialog (same as DataDisplayWidget's)."""
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QLineEdit,
            QDialogButtonBox, QMessageBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Year Range Options")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # Create form layout for options
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # MinYear field
        min_year_edit = QLineEdit(str(self.user_prefs.min_year))
        form_layout.addRow("Min Year:", min_year_edit)

        # MaxYear field
        max_year_edit = QLineEdit(str(self.user_prefs.max_year))
        form_layout.addRow("Max Year:", max_year_edit)

        # Save / Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(
            lambda: self._save_year_options(dialog, min_year_edit, max_year_edit)
        )
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.resize(250, 120)
        dialog.exec_()

    def _save_year_options(self, dialog, min_year_edit, max_year_edit):
        """Save year options from the dialog to shared UserPreferences."""
        from PyQt5.QtWidgets import QMessageBox

        try:
            min_year = int(min_year_edit.text())
            max_year = int(max_year_edit.text())

            if min_year >= max_year:
                QMessageBox.warning(
                    self, "Invalid Input",
                    "Min Year must be less than Max Year.",
                )
                return

            # Bulk-update emits changed once → _on_user_prefs_changed fires
            self.user_prefs.update_from_dict({
                'MinYear': min_year,
                'MaxYear': max_year,
            })

            dialog.accept()
        except ValueError:
            QMessageBox.warning(
                self, "Invalid Input",
                "Please enter valid integer values for years.",
            )

    def _on_controls_changed(self):
        """Re-render charts when a control value changes.

        Also syncs the checkbox state back to the shared UserPreferences
        so other consumers (e.g. DataDisplayWidget) stay in sync.
        When the checkbox changes limit_enabled, _on_user_prefs_changed
        already re-renders via the changed signal, so we only render
        here for other control changes (e.g. pie-year combo).
        """
        prefs_changed = False
        if self.limitYearsCheckbox is not None:
            new_val = self.limitYearsCheckbox.isChecked()
            if new_val != self.user_prefs.limit_enabled:
                self.user_prefs.limit_enabled = new_val
                prefs_changed = True
        # Only render if prefs didn't change (that path already re-renders)
        if not prefs_changed and self.current_scenario:
            self._render_charts()

    def _on_user_prefs_changed(self):
        """React to shared UserPreferences being changed externally.

        Syncs checkbox and re-renders charts.
        """
        print(f"DEBUG _on_user_prefs_changed: limit={self.user_prefs.limit_enabled} "
              f"range=[{self.user_prefs.min_year},{self.user_prefs.max_year}] "
              f"has_scenario={self.current_scenario is not None}")
        # Sync checkbox state
        if self.limitYearsCheckbox is not None:
            self.limitYearsCheckbox.blockSignals(True)
            self.limitYearsCheckbox.setChecked(self.user_prefs.limit_enabled)
            self.limitYearsCheckbox.blockSignals(False)
        # Re-render charts
        if self.current_scenario:
            self._render_charts()

    # ------------------------------------------------------------------
    # Dashboard update
    # ------------------------------------------------------------------

    def update_dashboard(self, scenario: Any):
        """Update the dashboard with postprocessing metrics and charts.

        Year-range settings are read from the shared UserPreferences
        object passed at construction time.

        Args:
            scenario: ScenarioData containing postprocessed parameters.
        """
        self.current_scenario = scenario
        self._populate_year_combo()
        self._render_metrics()
        self._render_charts()

    def _render_metrics(self):
        """Calculate and display the dashboard metrics from postprocessed data."""
        try:
            if not self.current_scenario:
                for label in self.metric_labels.values():
                    label.setText("--")
                return

            # Reuse results_analyzer metric calculation — it already looks up
            # the same postprocessed parameter names we produce.
            metrics = self.results_analyzer.calculate_dashboard_metrics(self.current_scenario)

            if 'primary_energy_2050' in self.metric_labels:
                primary_energy = metrics['primary_energy_2050']
                self.metric_labels['primary_energy_2050'].setText(f"{primary_energy:.1f} PJ")

                electricity = metrics['electricity_2050']
                self.metric_labels['electricity_2050'].setText(f"{electricity:.1f} TWh")

                clean_pct = metrics['clean_electricity_pct']
                self.metric_labels['clean_electricity_pct'].setText(f"{clean_pct:.1f}%")

                emissions = metrics['emissions_2050']
                self.metric_labels['emissions_2050'].setText(f"{emissions:.1f} Mt")

        except Exception as e:
            print(f"Error calculating postprocessing metrics: {str(e)}")
            for label in self.metric_labels.values():
                label.setText("Error")

    def _render_charts(self):
        """Render all overview and electricity tab charts."""
        try:
            if not self.current_scenario:
                for chart_view in self.chart_views.values():
                    self.show_chart_placeholder(chart_view, "No postprocessing data loaded")
                return

            pie_year = self._get_pie_year()

            # --- Overview tab ---

            # Primary energy supply stacked bar
            primary_param = self.current_scenario.get_parameter('Primary energy supply (PJ)')
            filtered_primary = self._filter_param_years(primary_param)
            if filtered_primary and not filtered_primary.df.empty and 'primary_energy_demand' in self.chart_views:
                self.render_energy_chart(
                    filtered_primary,
                    self.chart_views['primary_energy_demand'],
                    'Primary Energy Supply (PJ)',
                    'Primary Energy Supply by Source'
                )
            elif 'primary_energy_demand' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['primary_energy_demand'],
                    "No primary energy supply data available"
                )

            # Electricity generation by source stacked bar
            # Prefer the detailed "by source" parameter; fall back to aggregate
            elec_param = (
                self.current_scenario.get_parameter('Electricity generation by source (TWh)')
                or self.current_scenario.get_parameter('Electricity generation (TWh)')
            )
            filtered_elec = self._filter_param_years(elec_param)
            if filtered_elec and not filtered_elec.df.empty and 'electricity_generation' in self.chart_views:
                self.render_energy_chart(
                    filtered_elec,
                    self.chart_views['electricity_generation'],
                    'Electricity Generation by Source (TWh)',
                    'Electricity Generation by Source'
                )
            elif 'electricity_generation' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['electricity_generation'],
                    "No electricity generation data available"
                )

            # Primary energy pie chart (selected year)
            if primary_param and not primary_param.df.empty and 'primary_energy_pie' in self.chart_views:
                self.render_energy_pie_chart(
                    primary_param,
                    self.chart_views['primary_energy_pie'],
                    f'Primary Energy Mix ({pie_year})',
                    f'Primary Energy Mix by Fuel in {pie_year}',
                    target_year=pie_year
                )
            elif 'primary_energy_pie' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['primary_energy_pie'],
                    "No primary energy supply data available"
                )

            # Electricity sources pie chart (selected year)
            if elec_param and not elec_param.df.empty and 'electricity_pie' in self.chart_views:
                self.render_energy_pie_chart(
                    elec_param,
                    self.chart_views['electricity_pie'],
                    f'Electricity Sources ({pie_year})',
                    f'Electricity Sources in {pie_year}',
                    target_year=pie_year
                )
            elif 'electricity_pie' in self.chart_views:
                self.show_chart_placeholder(
                    self.chart_views['electricity_pie'],
                    "No electricity generation data available"
                )

            # --- Electricity tab ---
            self._render_electricity_charts()

            # --- New category tabs ---
            self._render_energy_balance_charts()
            self._render_fuels_charts()
            self._render_sectoral_charts()
            self._render_emissions_charts()

        except Exception as e:
            print(f"Error rendering postprocessing charts: {str(e)}")
            all_views = [
                self.chart_views,
                self.electricity_chart_views,
                self.energy_balance_chart_views,
                self.fuels_chart_views,
                self.sectoral_chart_views,
                self.emissions_chart_views,
            ]
            for views_dict in all_views:
                for chart_view in views_dict.values():
                    self.show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_electricity_charts(self):
        """Render electricity tab charts: generation by fuel and costs."""
        try:
            if not self.current_scenario:
                for chart_view in self.electricity_chart_views.values():
                    self.show_chart_placeholder(chart_view, "No postprocessing data loaded")
                return

            # Electricity generation by fuel source
            elec_param = (
                self.current_scenario.get_parameter('Electricity generation by source (TWh)')
                or self.current_scenario.get_parameter('Electricity generation (TWh)')
            )
            filtered_elec = self._filter_param_years(elec_param)
            if filtered_elec and not filtered_elec.df.empty and 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self.render_energy_chart(
                    filtered_elec,
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    'Electricity Generation by Fuel Source',
                    'Electricity Generation by Fuel Source'
                )
            elif 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    "No electricity generation data available"
                )

            # Electricity cost by source (from postprocessed LCOE data)
            cost_param = self.current_scenario.get_parameter('Electricity cost by source ($/MWh)')
            filtered_cost = self._filter_param_years(cost_param)
            if filtered_cost and not filtered_cost.df.empty and 'electricity_costs_by_fuel' in self.electricity_chart_views:
                self.render_energy_chart(
                    filtered_cost,
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    'Electricity Cost by Source ($/MWh)',
                    'Electricity Cost by Source'
                )
            elif 'electricity_costs_by_fuel' in self.electricity_chart_views:
                # Fallback: try results_analyzer cost breakdown
                self._render_electricity_costs_fallback()

            # Populate cost breakdown table if LCOE data available
            if cost_param and not cost_param.df.empty:
                self._populate_cost_table_from_param(cost_param)

        except Exception as e:
            print(f"Error rendering postprocessing electricity charts: {str(e)}")
            for chart_view in self.electricity_chart_views.values():
                self.show_chart_placeholder(chart_view, f"Error: {str(e)}")

    # ------------------------------------------------------------------
    # Generic tab chart renderer
    # ------------------------------------------------------------------

    def _render_tab_charts(self, chart_views: dict, chart_specs: dict):
        """Render a set of charts for a tab using parameter names.

        Args:
            chart_views: dict mapping chart key → QWebEngineView widget
            chart_specs: dict mapping chart key → (param_name, chart_title)
        """
        if not self.current_scenario:
            for view in chart_views.values():
                self.show_chart_placeholder(view, "No postprocessing data loaded")
            return

        for key, (param_name, title) in chart_specs.items():
            if key not in chart_views:
                continue
            view = chart_views[key]
            param = self.current_scenario.get_parameter(param_name)
            filtered = self._filter_param_years(param)
            if filtered and not filtered.df.empty:
                self.render_energy_chart(filtered, view, title, title)
            else:
                self.show_chart_placeholder(view, f"No data: {param_name}")

    # ------------------------------------------------------------------
    # Energy Balance tab
    # ------------------------------------------------------------------

    def _render_energy_balance_charts(self):
        """Render energy balance tab charts."""
        charts = {
            'eb_primary_supply': ('Primary energy supply (PJ)', 'Primary Energy Supply (PJ)'),
            'eb_final_consumption': ('Final energy consumption (PJ)', 'Final Energy Consumption (PJ)'),
            'eb_imports': ('Energy imports by fuel (PJ)', 'Energy Imports by Fuel (PJ)'),
            'eb_exports': ('Energy exports by fuel (PJ)', 'Energy Exports by Fuel (PJ)'),
        }
        self._render_tab_charts(self.energy_balance_chart_views, charts)

    # ------------------------------------------------------------------
    # Fuels tab
    # ------------------------------------------------------------------

    def _render_fuels_charts(self):
        """Render fuels tab charts."""
        charts = {
            'fuels_gas_supply': ('Gas supply by source (PJ)', 'Gas Supply by Source (PJ)'),
            'fuels_gas_use': ('Gas use by sector (PJ)', 'Gas Use by Sector (PJ)'),
            'fuels_oil_supply': ('Oil derivatives supply (PJ)', 'Oil Derivatives Supply (PJ)'),
            'fuels_oil_use': ('Oil derivatives use by sector (PJ)', 'Oil Derivatives Use by Sector (PJ)'),
        }
        self._render_tab_charts(self.fuels_chart_views, charts)

    # ------------------------------------------------------------------
    # Sectoral Use tab
    # ------------------------------------------------------------------

    def _render_sectoral_charts(self):
        """Render sectoral use tab charts."""
        charts = {
            'sectoral_buildings': ('Buildings energy by fuel (PJ)', 'Buildings Energy by Fuel (PJ)'),
            'sectoral_industry': ('Industry energy by fuel (PJ)', 'Industry Energy by Fuel (PJ)'),
            'sectoral_electricity': ('Electricity use by sector (TWh)', 'Electricity Use by Sector (TWh)'),
            'sectoral_transport': ('Energy use Transport (PJ)', 'Transportation Energy by Fuel (PJ)'),
        }
        self._render_tab_charts(self.sectoral_chart_views, charts)

    # ------------------------------------------------------------------
    # Emissions tab
    # ------------------------------------------------------------------

    def _render_emissions_charts(self):
        """Render emissions tab charts."""
        charts = {
            'emissions_total': ('Total GHG emissions (MtCeq)', 'Total GHG Emissions (MtCeq)'),
            'emissions_by_tech': ('Emissions by technology (Mt CO2)', 'Emissions by Technology (Mt CO2)'),
            'emissions_by_type': ('Emissions by type (Mt)', 'Emissions by Type (Mt)'),
            'emissions_by_fuel': ('Emissions by fuel (Mt CO2)', 'Emissions by Fuel (Mt CO2)'),
        }
        self._render_tab_charts(self.emissions_chart_views, charts)

    def _render_electricity_costs_fallback(self):
        """Fallback: use results_analyzer to calculate electricity costs."""
        try:
            cost_df = self.results_analyzer.calculate_electricity_cost_breakdown(self.current_scenario)
            if cost_df.empty:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No electricity cost data available"
                )
                return

            # Group by fuel categories
            fuel_mapping = {
                'Coal': ['coal', 'heavy fuel oil', 'light oil'],
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

            fuel_costs = cost_df.groupby(['fuel_category', 'year_act'])['Unit_Total_LCOE_Proxy'].sum().reset_index()
            pivot_df = fuel_costs.pivot(
                index='fuel_category', columns='year_act', values='Unit_Total_LCOE_Proxy'
            ).fillna(0)

            years = sorted(pivot_df.columns.tolist())
            data_dict = {fuel: pivot_df.loc[fuel, years].tolist() for fuel in pivot_df.index}

            if data_dict:
                self.render_stacked_bar_chart(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    years, data_dict,
                    'Electricity Costs by Fuel Source ($/MWh)',
                    'Electricity Costs by Fuel Source'
                )

                # Also populate cost table
                self._populate_cost_breakdown_table(cost_df)
            else:
                self.show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No cost data to display"
                )

        except Exception as e:
            print(f"Error in electricity costs fallback: {str(e)}")
            self.show_chart_placeholder(
                self.electricity_chart_views['electricity_costs_by_fuel'],
                "Error calculating electricity costs"
            )

    def _populate_cost_table_from_param(self, cost_param):
        """Populate cost breakdown table from a postprocessed cost Parameter."""
        try:
            if not hasattr(self, 'cost_breakdown_table'):
                return

            df = cost_param.df
            if df.empty:
                return

            self.cost_breakdown_table.clear()
            self.cost_breakdown_table.setRowCount(0)
            self.cost_breakdown_table.setColumnCount(0)

            year_col = 'year' if 'year' in df.columns else 'year_act'

            # Pivot: categories as rows, years as columns
            if 'category' in df.columns and 'value' in df.columns:
                pivot = df.pivot_table(index='category', columns=year_col, values='value', aggfunc='sum').fillna(0)
            else:
                return

            from PyQt5.QtWidgets import QTableWidgetItem

            categories = list(pivot.index)
            years = [str(y) for y in sorted(pivot.columns)]

            self.cost_breakdown_table.setRowCount(len(categories))
            self.cost_breakdown_table.setColumnCount(len(years))
            self.cost_breakdown_table.setHorizontalHeaderLabels(years)
            self.cost_breakdown_table.setVerticalHeaderLabels(categories)

            for row_idx, cat in enumerate(categories):
                for col_idx, yr in enumerate(sorted(pivot.columns)):
                    val = pivot.loc[cat, yr]
                    self.cost_breakdown_table.setItem(
                        row_idx, col_idx, QTableWidgetItem(f"{val:.1f}")
                    )

            self.cost_breakdown_table.resizeColumnsToContents()

        except Exception as e:
            print(f"Error populating cost table from param: {str(e)}")

    def _populate_cost_breakdown_table(self, cost_df):
        """Populate the cost breakdown table from a results_analyzer DataFrame."""
        try:
            if not hasattr(self, 'cost_breakdown_table'):
                return

            self.cost_breakdown_table.clear()
            self.cost_breakdown_table.setRowCount(0)
            self.cost_breakdown_table.setColumnCount(0)

            if cost_df.empty:
                return

            technologies = sorted(cost_df['technology'].unique())
            num_rows = 6
            num_cols = len(technologies) + 1

            self.cost_breakdown_table.setRowCount(num_rows)
            self.cost_breakdown_table.setColumnCount(num_cols)
            self.cost_breakdown_table.setHorizontalHeaderLabels(['Cost Component'] + technologies)

            row_labels = ['Capex ($/MWh)', 'Fixed Opex ($/MWh)', 'Var Opex ($/MWh)',
                         'Fuel ($/MWh)', 'Emissions ($/MWh)', 'Total LCOE ($/MWh)']
            self.cost_breakdown_table.setVerticalHeaderLabels(row_labels)

            cost_components = ['Unit_capex', 'Unit_fom', 'Unit_vom', 'Unit_fuel', 'Unit_em', 'Unit_Total_LCOE_Proxy']

            from PyQt5.QtWidgets import QTableWidgetItem

            for row_idx, component in enumerate(cost_components):
                self.cost_breakdown_table.setItem(row_idx, 0, QTableWidgetItem(row_labels[row_idx]))
                for col_idx, tech in enumerate(technologies, 1):
                    tech_data = cost_df[cost_df['technology'] == tech]
                    if not tech_data.empty and component in tech_data.columns:
                        avg_cost = tech_data[component].mean()
                        cost_str = f"{avg_cost:.1f}"
                    else:
                        cost_str = "0.0"
                    self.cost_breakdown_table.setItem(row_idx, col_idx, QTableWidgetItem(cost_str))

            self.cost_breakdown_table.resizeColumnsToContents()

        except Exception as e:
            print(f"Error populating cost breakdown table: {str(e)}")
