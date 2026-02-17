"""
Dashboard Chart Mixin - shared chart rendering methods for dashboard widgets.

Provides reusable Plotly chart rendering (stacked bar, pie) and QWebEngineView
setup used by both ResultsFileDashboard and PostprocessingDashboard.
"""

import plotly.graph_objects as go
import plotly.io as pio
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

from core.message_ix_schema import generate_legend_tooltip_script

# Plotly CDN URL used across all dashboards
PLOTLY_CDN_URL = "https://cdn.plot.ly/plotly-2.27.0.min.js"


class DashboardChartMixin:
    """Mixin providing shared chart rendering for dashboard widgets."""

    def setup_chart_view_settings(self, chart_views: dict):
        """Configure QWebEngineView settings for a dict of chart views.

        Args:
            chart_views: Dict mapping names to QWebEngineView instances.
        """
        for chart_view in chart_views.values():
            settings = chart_view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

            profile = chart_view.page().profile()
            profile.setPersistentCookiesPolicy(0)  # No persistent cookies

    def render_energy_chart(self, param, chart_view, title, html_title):
        """Render a stacked bar chart from a Parameter's DataFrame.

        Supports both long format (year, category, value) and wide format.
        """
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        if 'category' in df.columns and 'value' in df.columns:
            # Long format: pivot to wide for charting
            wide_df = df.pivot_table(
                index=year_col, columns='category', values='value', aggfunc='sum'
            ).fillna(0)
            years = wide_df.index.tolist()
            data_dict = {col: wide_df[col].tolist() for col in wide_df.columns}
        else:
            # Wide format: each non-year column is a data series
            years = df[year_col].unique().tolist()
            data_dict = {}
            for col in df.columns:
                if col != year_col and col != 'value':
                    data_dict[col] = df.groupby(year_col)[col].sum().tolist()

        self.render_stacked_bar_chart(chart_view, years, data_dict, title, html_title)

    def render_energy_pie_chart(self, param, chart_view, title, html_title, target_year=2050):
        """Render a pie chart from a Parameter's DataFrame for a given year.

        Args:
            param: Parameter with DataFrame containing year and value columns.
            chart_view: QWebEngineView to render into.
            title: Chart title shown in the Plotly chart.
            html_title: HTML page title.
            target_year: Year to filter data for (default 2050).
        """
        df = param.df
        year_col = 'year' if 'year' in df.columns else 'year_act'

        # Filter for target year
        df_year = df[df[year_col] == target_year]
        if df_year.empty:
            self.show_chart_placeholder(chart_view, f"No data available for year {target_year}")
            return

        # Sum values for each source in the target year
        data_dict = {}
        if 'category' in df_year.columns and 'value' in df_year.columns:
            grouped = df_year.groupby('category')['value'].sum()
            for category, total in grouped.items():
                if total > 0:
                    data_dict[category] = total
        else:
            for col in df_year.columns:
                if col != year_col and col != 'value':
                    total = df_year[col].sum()
                    if total > 0:
                        data_dict[col] = total

        if not data_dict:
            self.show_chart_placeholder(chart_view, f"No positive values for year {target_year}")
            return

        self.render_pie_chart(chart_view, data_dict, title, html_title)

    def render_stacked_bar_chart(self, chart_view, years, data_dict, title, html_title):
        """Render a Plotly stacked bar chart in a QWebEngineView."""
        fig = go.Figure()

        for source, values in data_dict.items():
            fig.add_trace(go.Bar(x=years, y=values, name=source))

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

        plot_html = pio.to_html(fig, full_html=False, include_plotlyjs=False, config=config)
        complete_html = self._wrap_plotly_html(plot_html, html_title)
        chart_view.setHtml(complete_html)

    def render_pie_chart(self, chart_view, data_dict, title, html_title):
        """Render a Plotly pie chart in a QWebEngineView."""
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

        plot_html = pio.to_html(fig, full_html=False, include_plotlyjs=False, config=config)
        complete_html = self._wrap_plotly_html(plot_html, html_title)
        chart_view.setHtml(complete_html)

    def show_chart_placeholder(self, chart_view: QWebEngineView, message: str):
        """Show a placeholder message in a chart view."""
        html = f"""
        <html style="height: 100%; margin: 0;">
        <body style="display: flex; justify-content: center; align-items: center;
                     height: 100%; margin: 0; font-family: Arial, sans-serif;
                     background: #f8f9fa; overflow: hidden;">
            <div style="text-align: center; color: #666;">
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        chart_view.setHtml(html)

    def _wrap_plotly_html(self, plot_html: str, html_title: str) -> str:
        """Wrap Plotly chart HTML with CDN script and styling."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{html_title}</title>
            <script src="{PLOTLY_CDN_URL}"></script>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                    font-family: Arial, sans-serif;
                }}
                .js-plotly-plot, .plotly-graph-div {{
                    width: 100% !important;
                    height: 100% !important;
                }}
                .js-plotly-plot .plotly .modebar-btn:focus {{
                    outline: 1px solid #007bff;
                    outline-offset: 1px;
                    border-radius: 3px;
                }}
            </style>
        </head>
        <body>
            {plot_html}
            {generate_legend_tooltip_script()}
            <script>
                // Resize chart to fill viewport on load and window resize
                window.addEventListener('load', function() {{
                    var gd = document.querySelector('.plotly-graph-div');
                    if (gd) {{
                        Plotly.relayout(gd, {{
                            width: window.innerWidth,
                            height: window.innerHeight
                        }});
                    }}
                }});
                window.addEventListener('resize', function() {{
                    var gd = document.querySelector('.plotly-graph-div');
                    if (gd) {{
                        Plotly.relayout(gd, {{
                            width: window.innerWidth,
                            height: window.innerHeight
                        }});
                    }}
                }});
            </script>
        </body>
        </html>
        """
