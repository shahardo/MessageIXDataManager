"""
Results File Dashboard - displays specific metrics and charts for results files

Shows a dashboard with metrics at the top and 4 charts in a 2x2 grid when a results file is selected.
"""

import plotly.graph_objects as go
import plotly.io as pio
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5 import uic
from typing import Any


class ResultsFileDashboard(QWidget):
    """
    Dashboard widget for displaying results file specific visualizations.

    Shows metrics at the top and 4 charts in a 2x2 grid:
    - Top row: Total primary energy (2050), Total electricity (2050),
               % Clean electricity (2050), Total emissions (2050)
    - Charts: Primary energy demand over years, Electricity generation by source,
              Primary energy mix pie (2050), Electricity sources pie (2050)
    """

    def __init__(self, results_analyzer):
        super().__init__()
        self.results_analyzer = results_analyzer
        self.current_scenario = None

        # Load UI from .ui file
        ui_file = 'src/ui/results_file_dashboard.ui'
        ui_loaded = False
        try:
            uic.loadUi(ui_file, self)
            print("Results file dashboard UI loaded successfully")
            ui_loaded = True
        except Exception as e:
            print(f"Error loading UI: {e}")
            # Continue without UI for testing purposes

            # Map chart views from UI file or create mocks for testing
        if ui_loaded and hasattr(self, 'primary_energy_demand_chart'):
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
            self._setup_chart_views()
        else:
            # For testing without UI
            self.chart_views = {}
            self.electricity_chart_views = {}
            self.metric_labels = {}



    def _setup_chart_views(self):
        """Set up chart view settings"""
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings

        # Setup overview tab charts
        for chart_view in self.chart_views.values():
            settings = chart_view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

            # Allow loading of local files
            profile = chart_view.page().profile()
            profile.setPersistentCookiesPolicy(0)  # No persistent cookies

        # Setup electricity tab charts
        for chart_view in self.electricity_chart_views.values():
            settings = chart_view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

            # Allow loading of local filese
            profile = chart_view.page().profile()
            profile.setPersistentCookiesPolicy(0)  # No persistent cookies

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

    def _render_charts(self):
        """Render all 4 charts: primary energy demand, electricity generation, and pie charts"""
        try:
            if not self.current_scenario:
                # Show placeholder if no scenario loaded
                for chart_view in self.chart_views.values():
                    self._show_chart_placeholder(chart_view, "No data loaded")
                return

            # Primary energy chart: get data from "Primary energy supply (PJ)" parameter
            primary_energy_param = self.current_scenario.get_parameter('Primary energy supply (PJ)')
            if primary_energy_param and not primary_energy_param.df.empty and 'primary_energy_demand' in self.chart_views:
                self._render_energy_chart(
                    primary_energy_param,
                    self.chart_views['primary_energy_demand'],
                    'Primary Energy Supply (PJ)',
                    'Primary Energy Supply by Source'
                )
            elif 'primary_energy_demand' in self.chart_views:
                self._show_chart_placeholder(
                    self.chart_views['primary_energy_demand'],
                    "No primary energy supply data available"
                )

            # Electricity chart: get data from 'Electricity generation (TWh)' parameter
            electricity_param = self.current_scenario.get_parameter('Electricity generation (TWh)')
            if electricity_param and not electricity_param.df.empty and 'electricity_generation' in self.chart_views:
                self._render_energy_chart(
                    electricity_param,
                    self.chart_views['electricity_generation'],
                    'Electricity Generation (TWh)',
                    'Electricity Generation by Source'
                )
            elif 'electricity_generation' in self.chart_views:
                self._show_chart_placeholder(
                    self.chart_views['electricity_generation'],
                    "No electricity generation data available"
                )

            # Primary energy pie chart: get data from "Primary energy supply (PJ)" parameter, year 2050
            primary_energy_param = self.current_scenario.get_parameter('Primary energy supply (PJ)')
            if primary_energy_param and not primary_energy_param.df.empty and 'primary_energy_pie' in self.chart_views:
                self._render_energy_pie_chart(
                    primary_energy_param,
                    self.chart_views['primary_energy_pie'],
                    'Primary Energy Mix (2050)',
                    'Primary Energy Mix by Fuel in 2050'
                )
            elif 'primary_energy_pie' in self.chart_views:
                self._show_chart_placeholder(
                    self.chart_views['primary_energy_pie'],
                    "No primary energy supply data available"
                )

            # Electricity pie chart: get data from 'Electricity generation (TWh)' parameter, year 2050
            electricity_param = self.current_scenario.get_parameter('Electricity generation (TWh)')
            if electricity_param and not electricity_param.df.empty and 'electricity_pie' in self.chart_views:
                self._render_energy_pie_chart(
                    electricity_param,
                    self.chart_views['electricity_pie'],
                    'Electricity Sources (2050)',
                    'Electricity Sources in 2050'
                )
            elif 'electricity_pie' in self.chart_views:
                self._show_chart_placeholder(
                    self.chart_views['electricity_pie'],
                    "No electricity generation data available"
                )

            # Render electricity tab charts
            self._render_electricity_charts()

        except Exception as e:
            print(f"Error rendering charts: {str(e)}")
            for chart_view in self.chart_views.values():
                self._show_chart_placeholder(chart_view, f"Error: {str(e)}")
            for chart_view in self.electricity_chart_views.values():
                self._show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_energy_chart(self, param, chart_view, title, html_title):
        """Render energy chart from parameter data"""
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        # render stacked bar chart with 'year_act' as years, and the rest of the columns as data
        years = df[year_col].unique().tolist()
        data_dict = {}
        for col in df.columns:
            if col != year_col and col != 'value':
                data_dict[col] = df.groupby(year_col)[col].sum().tolist()

        self._render_stacked_bar_chart(
            chart_view,
            years,
            data_dict,
            title,
            html_title
        )
        return

    def _render_energy_pie_chart(self, param, chart_view, title, html_title):
        """Render energy pie chart from parameter data for year 2050"""
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        # Filter for year 2050
        df_2050 = df[df[year_col] == 2050]
        if df_2050.empty:
            self._show_chart_placeholder(chart_view, "No data available for year 2050")
            return

        # Sum values for each source in 2050
        data_dict = {}
        for col in df_2050.columns:
            if col != year_col and col != 'value':
                total = df_2050[col].sum()
                if total > 0:  # Only include positive values
                    data_dict[col] = total

        if not data_dict:
            self._show_chart_placeholder(chart_view, "No positive values for year 2050")
            return

        self._render_pie_chart(
            chart_view,
            data_dict,
            title,
            html_title
        )



    def _render_stacked_bar_chart(self, chart_view, years, data_dict, title, html_title):
        """Render a stacked bar chart"""
        fig = go.Figure()

        for source, values in data_dict.items():
            fig.add_trace(go.Bar(
                x=years,
                y=values,
                name=source
            ))

        fig.update_layout(
            title=title,
            xaxis_title='Year',
            yaxis_title='Energy (units)',
            barmode='stack',
            showlegend=True,
            template='plotly_white',
            margin=dict(l=20, r=20, t=40, b=20)
        )

        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'responsive': True,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
        }

        # Generate HTML without Plotly included
        plot_html = pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs=False,
            config=config
        )

        # Create complete HTML with Plotly CDN
        plotly_js_url = "https://cdn.plot.ly/plotly-2.27.0.min.js"
        complete_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{html_title}</title>
            <script src="{plotly_js_url}"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                }}
                .js-plotly-plot {{
                    width: 100% !important;
                    height: 100% !important;
                }}
                /* Remove problematic CSS rules */
                .js-plotly-plot .plotly .modebar-btn:focus {{
                    outline: 1px solid #007bff;
                    outline-offset: 1px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            {plot_html}
        </body>
        </html>
        """

        # Load in web view
        chart_view.setHtml(complete_html)

    def _render_pie_chart(self, chart_view, data_dict, title, html_title):
        """Render a pie chart"""
        fig = go.Figure()

        labels = list(data_dict.keys())
        values = list(data_dict.values())

        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            textinfo='percent+label',
            insidetextorientation='radial'
        ))

        fig.update_layout(
            title=title,
            template='plotly_white',
            margin=dict(l=20, r=20, t=40, b=20)
        )

        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'responsive': True,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
        }

        # Generate HTML without Plotly included
        plot_html = pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs=False,
            config=config
        )

        # Create complete HTML with Plotly CDN
        plotly_js_url = "https://cdn.plot.ly/plotly-2.27.0.min.js"
        complete_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{html_title}</title>
            <script src="{plotly_js_url}"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                }}
                .js-plotly-plot {{
                    width: 100% !important;
                    height: 100% !important;
                }}
                /* Remove problematic CSS rules */
                .js-plotly-plot .plotly .modebar-btn:focus {{
                    outline: 1px solid #007bff;
                    outline-offset: 1px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            {plot_html}
        </body>
        </html>
        """

        # Load in web view
        chart_view.setHtml(complete_html)

    def _render_electricity_charts(self):
        """Render electricity tab charts: generation and costs by fuel"""
        try:
            if not self.current_scenario:
                # Show placeholder if no scenario loaded
                for chart_view in self.electricity_chart_views.values():
                    self._show_chart_placeholder(chart_view, "No data loaded")
                return

            # Electricity generation chart (same as overview but different title)
            electricity_param = self.current_scenario.get_parameter('Electricity generation (TWh)')
            if electricity_param and not electricity_param.df.empty and 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self._render_energy_chart(
                    electricity_param,
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    'Electricity Generation by Fuel Source',
                    'Electricity Generation by Fuel Source'
                )
            elif 'electricity_generation_by_fuel' in self.electricity_chart_views:
                self._show_chart_placeholder(
                    self.electricity_chart_views['electricity_generation_by_fuel'],
                    "No electricity generation data available"
                )

            # Electricity costs chart (new functionality)
            if 'electricity_costs_by_fuel' in self.electricity_chart_views:
                self._render_electricity_costs_chart()

        except Exception as e:
            print(f"Error rendering electricity charts: {str(e)}")
            for chart_view in self.electricity_chart_views.values():
                self._show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_electricity_costs_chart(self):
        """Render electricity costs by fuel source chart"""
        try:
            print("DEBUG: Starting electricity costs chart rendering")
            # Calculate electricity costs breakdown
            cost_df = self.results_analyzer.calculate_electricity_cost_breakdown(self.current_scenario)
            print(f"DEBUG: Cost DataFrame shape: {cost_df.shape}")
            print(f"DEBUG: Cost DataFrame columns: {cost_df.columns.tolist()}")
            print(f"DEBUG: Cost DataFrame empty? {cost_df.empty}")

            if cost_df.empty:
                print("DEBUG: Cost DataFrame is empty, showing placeholder")
                self._show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No electricity cost data available"
                )
                return

            # Group by fuel categories and aggregate costs
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

            print(f"DEBUG: Original technologies: {cost_df['technology'].unique().tolist()}")

            # Map technologies to fuel categories
            cost_df['fuel_category'] = 'Other'  # Default
            for fuel, techs in fuel_mapping.items():
                mask = cost_df['technology'].str.lower().isin([t.lower() for t in techs])
                cost_df.loc[mask, 'fuel_category'] = fuel

            print(f"DEBUG: Fuel categories: {cost_df['fuel_category'].unique().tolist()}")

            # Aggregate by fuel category and year
            fuel_costs = cost_df.groupby(['fuel_category', 'year_act'])['Unit_Total_LCOE_Proxy'].sum().reset_index()
            print(f"DEBUG: Fuel costs shape: {fuel_costs.shape}")
            print(f"DEBUG: Fuel costs sample: {fuel_costs.head()}")

            # Create detailed cost breakdown table (technologies as columns, cost components as rows)
            print("\n" + "="*120)
            print("ELECTRICITY COST BREAKDOWN BY TECHNOLOGY ($/MWh)")
            print("="*120)

            # Get all unique years and technologies
            years = sorted(cost_df['year_act'].unique())
            technologies = sorted(cost_df['technology'].unique())

            # Create table with technologies as columns, years as sub-headers
            # Header row 1: Technology names
            header1 = "Cost Component".ljust(15)
            for tech in technologies:
                header1 += f"{tech[:10]:>12}"  # Truncate technology names
            print(header1)

            # Header row 2: Years under each technology
            header2 = "".ljust(15)
            for tech in technologies:
                tech_years = sorted(cost_df[cost_df['technology'] == tech]['year_act'].unique())
                year_str = "/".join([str(y) for y in tech_years[:3]])  # Show first 3 years
                if len(tech_years) > 3:
                    year_str += "+"
                header2 += f"{year_str:>12}"
            print(header2)
            print("-" * len(header1))

            # Create table rows for each cost component
            cost_components = ['Unit_capex', 'Unit_fom', 'Unit_vom', 'Unit_fuel', 'Unit_em', 'Unit_Total_LCOE_Proxy']
            component_names = ['Capex', 'Fixed Opex', 'Var Opex', 'Fuel', 'Emissions', 'Total LCOE']

            for component, comp_name in zip(cost_components, component_names):
                if component in cost_df.columns:
                    row = comp_name.ljust(15)
                    for tech in technologies:
                        tech_data = cost_df[cost_df['technology'] == tech]
                        if not tech_data.empty and component in tech_data.columns:
                            # Get costs for each year for this technology
                            tech_costs = []
                            for year in years:
                                year_data = tech_data[tech_data['year_act'] == year]
                                if not year_data.empty and component in year_data.columns:
                                    cost_val = year_data[component].iloc[0] if len(year_data) > 0 else 0.0
                                    tech_costs.append(f"{cost_val:.1f}")
                                else:
                                    tech_costs.append("0.0")

                            # Join year costs with slashes, limit to 3 years for readability
                            cost_str = "/".join(tech_costs[:3])
                            if len(tech_costs) > 3:
                                cost_str += "+"
                            row += f"{cost_str:>12}"
                        else:
                            row += "     0.0/0.0"[:12].rjust(12)
                    print(row)

            print("="*120)

            # Also show the original format for reference
            print("\nAVERAGE COST BREAKDOWN BY FUEL SOURCE ($/MWh)")
            print("-" * 60)
            for fuel in sorted(cost_df['fuel_category'].unique()):
                fuel_data = cost_df[cost_df['fuel_category'] == fuel]
                print(f"\n{fuel.upper()}:")
                for _, row in fuel_data.iterrows():
                    print(f"  {row['year_act']}: Total=${row['Unit_Total_LCOE_Proxy']:.2f}/MWh "
                          f"(Capex=${row.get('Unit_capex',0):.2f}, "
                          f"FOM=${row.get('Unit_fom',0):.2f}, "
                          f"VOM=${row.get('Unit_vom',0):.2f}, "
                          f"Fuel=${row.get('Unit_fuel',0):.2f}, "
                          f"Em=${row.get('Unit_em',0):.2f})")

            # Populate the cost breakdown table in the dashboard
            self._populate_cost_breakdown_table(cost_df)

            # Also show detailed breakdown by fuel category
            print("\nCOST BREAKDOWN BY FUEL CATEGORY:")
            print("-" * 50)
            for fuel in sorted(cost_df['fuel_category'].unique()):
                fuel_data = cost_df[cost_df['fuel_category'] == fuel]
                print(f"\n{fuel.upper()}:")
                for _, row in fuel_data.iterrows():
                    print(f"  {row['year_act']}: Total=${row['Unit_Total_LCOE_Proxy']:.2f}/MWh "
                          f"(Capex=${row.get('Unit_capex',0):.2f}, "
                          f"FOM=${row.get('Unit_fom',0):.2f}, "
                          f"VOM=${row.get('Unit_vom',0):.2f}, "
                          f"Fuel=${row.get('Unit_fuel',0):.2f}, "
                          f"Em=${row.get('Unit_em',0):.2f})")

            # Pivot to get years as columns, fuels as series
            pivot_df = fuel_costs.pivot(index='fuel_category', columns='year_act', values='Unit_Total_LCOE_Proxy').fillna(0)
            print(f"DEBUG: Pivot DataFrame shape: {pivot_df.shape}")
            print(f"DEBUG: Pivot DataFrame: {pivot_df}")

            # Prepare data for stacked bar chart
            years = sorted(pivot_df.columns.tolist())
            data_dict = {}
            for fuel in pivot_df.index:
                data_dict[fuel] = pivot_df.loc[fuel, years].tolist()

            print(f"DEBUG: Years: {years}")
            print(f"DEBUG: Data dict: {data_dict}")

            if not data_dict:
                print("DEBUG: No data to plot, showing placeholder")
                self._show_chart_placeholder(
                    self.electricity_chart_views['electricity_costs_by_fuel'],
                    "No cost data to display"
                )
                return

            self._render_stacked_bar_chart(
                self.electricity_chart_views['electricity_costs_by_fuel'],
                years,
                data_dict,
                'Electricity Costs by Fuel Source ($/MWh)',
                'Electricity Costs by Fuel Source'
            )
            print("DEBUG: Chart rendering completed successfully")

        except Exception as e:
            print(f"Error calculating electricity costs: {str(e)}")
            import traceback
            traceback.print_exc()
            self._show_chart_placeholder(
                self.electricity_chart_views['electricity_costs_by_fuel'],
                "Error calculating electricity costs"
            )

    def _populate_cost_breakdown_table(self, cost_df):
        """Populate the cost breakdown table with technology cost data"""
        try:
            if not hasattr(self, 'cost_breakdown_table'):
                print("DEBUG: Cost breakdown table widget not found")
                return

            # Clear existing table
            self.cost_breakdown_table.clear()
            self.cost_breakdown_table.setRowCount(0)
            self.cost_breakdown_table.setColumnCount(0)

            if cost_df.empty:
                print("DEBUG: Cost DataFrame is empty, not populating table")
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
            print(f"DEBUG: Populated cost breakdown table with {len(technologies)} technologies and {len(years)} years")

        except Exception as e:
            print(f"Error populating cost breakdown table: {str(e)}")
            import traceback
            traceback.print_exc()

    def _show_chart_placeholder(self, chart_view: QWebEngineView, message: str):
        """Show placeholder in a chart view"""
        html = f"""
        <html>
        <body style="display: flex; justify-content: center; align-items: center;
                     height: 100%; font-family: Arial, sans-serif; background: #f8f9fa;">
            <div style="text-align: center; color: #666;">
                <p>{message}</p>
            </div>
        </body>
        </html>
        """

        chart_view.setHtml(html)
