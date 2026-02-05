"""
Base class for dashboard widgets with common functionality.
Provides shared web view setup, placeholder management, and HTML generation.

Extracted common code from input_file_dashboard.py and results_file_dashboard.py.
"""
from typing import Dict, Optional, List, Any
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import pyqtSignal
from PyQt5 import uic
import plotly.graph_objects as go
import plotly.io as pio


class BaseDashboard(QWidget):
    """
    Base class for file dashboard widgets.

    Provides common functionality for:
    - Loading UI from .ui files
    - Setting up web views with proper settings
    - Showing placeholder messages
    - Rendering Plotly charts

    Subclasses should implement:
    - _create_web_view_mapping(): Map web views from UI to self.web_views dict
    - _on_scenario_updated(): Called when update_dashboard() is invoked
    """

    # Signal when dashboard needs refresh
    refresh_requested = pyqtSignal()

    def __init__(self, ui_file: Optional[str] = None, parent: Optional[QWidget] = None):
        """
        Initialize the base dashboard.

        Args:
            ui_file: Optional path to .ui file to load
            parent: Parent widget
        """
        super().__init__(parent)
        self.web_views: Dict[str, QWebEngineView] = {}
        self.current_scenario = None
        self._ui_loaded = False

        # Load UI if file provided
        if ui_file:
            self._load_ui(ui_file)

    def _load_ui(self, ui_file: str) -> bool:
        """
        Load UI from .ui file.

        Args:
            ui_file: Path to the .ui file

        Returns:
            True if UI loaded successfully
        """
        try:
            uic.loadUi(ui_file, self)
            print(f"Dashboard UI loaded successfully from {ui_file}")
            self._ui_loaded = True
            return True
        except Exception as e:
            print(f"Error loading UI from {ui_file}: {e}")
            self._ui_loaded = False
            return False

    @property
    def ui_loaded(self) -> bool:
        """Check if UI was loaded successfully."""
        return self._ui_loaded

    def setup_web_views(self, web_views: Dict[str, QWebEngineView]) -> None:
        """
        Set up web views with common settings.

        Args:
            web_views: Dictionary mapping names to QWebEngineView instances
        """
        self.web_views = web_views

        for web_view in self.web_views.values():
            self._configure_web_view(web_view)

    def _configure_web_view(self, web_view: QWebEngineView) -> None:
        """
        Configure a single web view with standard settings.

        Args:
            web_view: The web view to configure
        """
        settings = web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

        # Allow loading of local files
        profile = web_view.page().profile()
        profile.setPersistentCookiesPolicy(0)  # No persistent cookies

        web_view.setEnabled(True)
        web_view.setVisible(True)
        web_view.setMinimumSize(200, 200)

    def show_placeholder(self, view_name: str, message: str) -> None:
        """
        Show a placeholder message in a web view.

        Args:
            view_name: Name of the web view (key in self.web_views)
            message: Message to display
        """
        if view_name not in self.web_views:
            return

        self._show_placeholder(self.web_views[view_name], message)

    def _show_placeholder(self, web_view: QWebEngineView, message: str) -> None:
        """
        Show a placeholder message in a specific web view.

        Args:
            web_view: The web view to update
            message: Message to display
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    color: #666;
                    background-color: #f5f5f5;
                }}
                p {{
                    text-align: center;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <p>{message}</p>
        </body>
        </html>
        """
        web_view.setHtml(html)

    def show_all_placeholders(self, message: str) -> None:
        """
        Show the same placeholder message in all web views.

        Args:
            message: Message to display
        """
        for web_view in self.web_views.values():
            self._show_placeholder(web_view, message)

    def render_plotly_chart(self, view_name: str, fig: go.Figure) -> None:
        """
        Render a Plotly figure in a web view.

        Args:
            view_name: Name of the web view
            fig: Plotly Figure to render
        """
        if view_name not in self.web_views:
            return

        self._render_plotly_chart(self.web_views[view_name], fig)

    def _render_plotly_chart(self, web_view: QWebEngineView, fig: go.Figure) -> None:
        """
        Render a Plotly figure in a specific web view.

        Args:
            web_view: The web view to render in
            fig: Plotly Figure to render
        """
        html = pio.to_html(fig, include_plotlyjs='cdn', full_html=True)
        web_view.setHtml(html)

    def render_html_table(
        self,
        view_name: str,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        additional_style: str = ""
    ) -> None:
        """
        Render an HTML table in a web view.

        Args:
            view_name: Name of the web view
            title: Table title
            headers: Column headers
            rows: Table rows (list of lists)
            additional_style: Additional CSS to include
        """
        if view_name not in self.web_views:
            return

        # Build header row
        header_html = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"

        # Build data rows
        rows_html = ""
        for row in rows:
            cells = "".join(f"<td>{cell}</td>" for cell in row)
            rows_html += f"<tr>{cells}</tr>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 10px;
                    background-color: #ffffff;
                }}
                h2 {{
                    color: #333;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 5px;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-top: 10px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #fafafa;
                }}
                tr:hover {{
                    background-color: #f0f0f0;
                }}
                {additional_style}
            </style>
        </head>
        <body>
            <h2>{title}</h2>
            <table>
                <thead>{header_html}</thead>
                <tbody>{rows_html}</tbody>
            </table>
        </body>
        </html>
        """
        self.web_views[view_name].setHtml(html)

    def update_dashboard(self, scenario: Any) -> None:
        """
        Update the dashboard with scenario data.

        This is the main entry point for updating the dashboard.
        Subclasses should override _on_scenario_updated() for custom logic.

        Args:
            scenario: The scenario data to display
        """
        self.current_scenario = scenario

        if not scenario:
            self.show_all_placeholders("No data available")
            return

        try:
            self._on_scenario_updated(scenario)
        except Exception as e:
            print(f"Error updating dashboard: {e}")
            self.show_all_placeholders(f"Error: {str(e)}")

    def _on_scenario_updated(self, scenario: Any) -> None:
        """
        Called when scenario is updated. Override in subclass.

        Args:
            scenario: The scenario data to display
        """
        raise NotImplementedError("Subclass must implement _on_scenario_updated()")

    def clear(self) -> None:
        """Clear all dashboard content."""
        self.current_scenario = None
        self.show_all_placeholders("No data loaded")

    @staticmethod
    def generate_overview_html(
        title: str,
        metrics: Dict[str, Any],
        description: str = ""
    ) -> str:
        """
        Generate HTML for an overview section.

        Args:
            title: Section title
            metrics: Dictionary of metric name -> value
            description: Optional description text

        Returns:
            HTML string
        """
        metrics_html = ""
        for name, value in metrics.items():
            metrics_html += f"""
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-name">{name}</div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #ffffff;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .description {{
                    color: #666;
                    margin-bottom: 20px;
                }}
                .metrics-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-top: 20px;
                }}
                .metric-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    min-width: 150px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .metric-value {{
                    font-size: 28px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .metric-name {{
                    font-size: 14px;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {f'<p class="description">{description}</p>' if description else ''}
            <div class="metrics-container">
                {metrics_html}
            </div>
        </body>
        </html>
        """
