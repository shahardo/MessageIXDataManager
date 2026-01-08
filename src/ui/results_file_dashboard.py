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
        try:
            uic.loadUi(ui_file, self)
            print("Results file dashboard UI loaded successfully")
        except Exception as e:
            print(f"Error loading UI: {e}")
            raise

        # Map chart views from UI file
        self.chart_views = {
            'primary_energy_demand': self.primary_energy_demand_chart,
            'electricity_generation': self.electricity_generation_chart,
            'primary_energy_pie': self.primary_energy_pie_chart,
            'electricity_pie': self.electricity_pie_chart
        }

        # Enable JavaScript for chart views
        self._setup_chart_views()



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
        """Update the dashboard with the charts"""
        self.current_scenario = scenario
        self._render_charts()

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
            if primary_energy_param and not primary_energy_param.df.empty:
                self._render_primary_energy_chart(primary_energy_param)
            else:
                self._show_chart_placeholder(
                    self.chart_views['primary_energy_demand'],
                    "No primary energy supply data available"
                )

            # Electricity chart: get data from 'Electricity generation (TWh)' parameter
            electricity_param = self.current_scenario.get_parameter('Electricity generation (TWh)')
            if electricity_param and not electricity_param.df.empty:
                self._render_electricity_chart(electricity_param)
            else:
                self._show_chart_placeholder(
                    self.chart_views['electricity_generation'],
                    "No electricity generation data available"
                )

            # For pie charts, use demo data for now
            self._render_demo_pie_charts()

        except Exception as e:
            print(f"Error rendering charts: {str(e)}")
            for chart_view in self.chart_views.values():
                self._show_chart_placeholder(chart_view, f"Error: {str(e)}")

    def _render_primary_energy_chart(self, param):
        """Render primary energy chart from parameter data"""
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        # render stacked bar chart with 'year_act' as years, and the rest of the columns as data
        years = df[year_col].unique().tolist()
        data_dict = {}
        for col in df.columns:
            if col != year_col and col != 'value':
                data_dict[col] = df.groupby(year_col)[col].sum().tolist()

        print(f"DEBUG: Primary energy chart - years: {years}, data: {data_dict}")

        self._render_stacked_bar_chart(
            self.chart_views['primary_energy_demand'],
            years,
            data_dict,
            'Primary Energy Supply (PJ)',
            'Primary Energy Supply by Source'
        )
        return

    def _render_electricity_chart(self, param):
        """Render electricity chart from parameter data"""
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        # render stacked bar chart with 'year_act' as years, and the rest of the columns as data
        years = df[year_col].unique().tolist()
        data_dict = {}
        for col in df.columns:
            if col != year_col and col != 'value':
                data_dict[col] = df.groupby(year_col)[col].sum().tolist()

        print(f"DEBUG: Primary energy chart - years: {years}, data: {data_dict}")

        self._render_stacked_bar_chart(
            self.chart_views['electricity_generation'],
            years,
            data_dict,
            'Electricity Generation (TWh)',
            'Electricity Generation by Source'
        )
        return

    def _render_demo_pie_charts(self):
        """Render demo pie charts for energy mix"""
        # Primary energy pie chart
        primary_energy_data = {
            'Coal': 18.7,
            'Gas': 72.1,
            'Oil': 15.9,
            'Nuclear': 48.3,
            'Renewables': 42.6
        }
        self._render_pie_chart(
            self.chart_views['primary_energy_pie'],
            primary_energy_data,
            'Primary Energy Mix (2050)',
            'Primary Energy Mix by Fuel in 2050'
        )

        # Electricity sources pie chart
        electricity_data = {
            'Coal': 12.3,
            'Gas': 58.9,
            'Oil': 2.7,
            'Nuclear': 45.6,
            'Renewables': 38.2
        }
        self._render_pie_chart(
            self.chart_views['electricity_pie'],
            electricity_data,
            'Electricity Sources (2050)',
            'Electricity Sources in 2050'
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
