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
            self.chart_views = {
                'primary_energy_demand': self.primary_energy_demand_chart,
                'electricity_generation': self.electricity_generation_chart,
                'primary_energy_pie': self.primary_energy_pie_chart,
                'electricity_pie': self.electricity_pie_chart
            }

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
            self.metric_labels = {}



    def _setup_chart_views(self):
        """Set up chart view settings"""
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings

        for chart_view in self.chart_views.values():
            settings = chart_view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

            # Allow loading of local files
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

                print(f"DEBUG: Dashboard metrics updated - Primary: {primary_energy:.1f} PJ, Electricity: {electricity:.1f} TWh, Clean: {clean_pct:.1f}%, Emissions: {emissions:.1f} ktCO₂e")

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

        except Exception as e:
            print(f"Error rendering charts: {str(e)}")
            for chart_view in self.chart_views.values():
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

        print(f"DEBUG: {title} - years: {years}, data: {data_dict}")

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

        print(f"DEBUG: {title} - 2050 data: {data_dict}")

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

        # Print the whole HTML to terminal
        print(f"Generated HTML for {title}:")
        print(complete_html)

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
