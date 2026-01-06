"""
Chart Widget - Handles chart rendering and management

Extracted from MainWindow to provide focused chart display functionality.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QIcon
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import tempfile
import threading
import os
from typing import Optional

from core.data_models import Parameter
from ..ui_styler import UIStyler


class ChartWidget(QWidget):
    """Handles chart rendering and management"""

    # Define PyQt signals
    chart_type_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_chart_type = 'bar'  # 'bar', 'stacked_bar', 'line', 'stacked_area'

        self.setup_ui()

    def setup_ui(self):
        """Set up the UI components"""
        layout = QVBoxLayout(self)

        # Chart type buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 5)  # Add space above and below

        self.simple_bar_btn = QPushButton("Simple Bar")
        UIStyler.setup_chart_button(self.simple_bar_btn)
        self.simple_bar_btn.setChecked(True)
        self.simple_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('bar'))

        self.stacked_bar_btn = QPushButton("Stacked Bar")
        UIStyler.setup_chart_button(self.stacked_bar_btn)
        self.stacked_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_bar'))

        self.line_chart_btn = QPushButton("Line Chart")
        UIStyler.setup_chart_button(self.line_chart_btn)
        self.line_chart_btn.clicked.connect(lambda: self._on_chart_type_changed('line'))

        self.stacked_area_btn = QPushButton("Stacked Area")
        UIStyler.setup_chart_button(self.stacked_area_btn)
        self.stacked_area_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_area'))

        button_layout.addWidget(self.simple_bar_btn)
        button_layout.addWidget(self.stacked_bar_btn)
        button_layout.addWidget(self.line_chart_btn)
        button_layout.addWidget(self.stacked_area_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Chart view
        self.param_chart = QWebEngineView()

        # Enable JavaScript for parameter chart
        chart_settings = self.param_chart.settings()
        chart_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        chart_settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        layout.addWidget(self.param_chart)

        self.setLayout(layout)

    def _initialize_from_existing_widgets(self):
        """Initialize component to use existing UI widgets instead of creating new layout"""
        # Connect signals for existing widgets
        if hasattr(self.simple_bar_btn, 'clicked'):
            self.simple_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('bar'))
        if hasattr(self.stacked_bar_btn, 'clicked'):
            self.stacked_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_bar'))
        if hasattr(self.line_chart_btn, 'clicked'):
            self.line_chart_btn.clicked.connect(lambda: self._on_chart_type_changed('line'))
        if hasattr(self.stacked_area_btn, 'clicked'):
            self.stacked_area_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_area'))

        # Initialize state
        self.current_chart_type = 'bar'
        self.simple_bar_btn.setChecked(True)
        self.stacked_bar_btn.setChecked(False)
        self.line_chart_btn.setChecked(False)
        self.stacked_area_btn.setChecked(False)

        # Apply chart button styling using UIStyler
        for btn in [self.simple_bar_btn, self.stacked_bar_btn, self.line_chart_btn, self.stacked_area_btn]:
            UIStyler.setup_chart_button(btn)

    def update_chart(self, df: pd.DataFrame, parameter_name: str, is_results: bool = False):
        """Update the chart with data from a DataFrame"""
        # Ensure button states reflect current chart type
        self._update_button_states()

        if df.empty or df.shape[1] == 0:
            self._show_chart_placeholder("No data available for chart")
            return

        # Create chart based on current chart type
        fig = go.Figure()

        # Get years from index (should be years in advanced view)
        years = df.index.tolist()

        # Check if index is sequential integers starting from 1, and if so, map to actual years
        if (len(years) > 0 and all(isinstance(y, (int, float)) and y == int(y) for y in years) and
            sorted(years) == list(range(1, len(years) + 1))):
            # Try to get actual years from scenario - this will need to be passed in or accessed differently
            # For now, keep original years
            pass

        # Add traces based on chart type
        for col_idx, col_name in enumerate(df.columns):
            col_data = df[col_name]
            if isinstance(col_data, pd.DataFrame):
                # Handle duplicate column names by taking the first column
                col_data = col_data.iloc[:, 0]
            values = col_data.fillna(0).tolist()

            if self.current_chart_type == 'line':
                fig.add_trace(go.Scatter(
                    x=years,
                    y=values,
                    mode='lines+markers',
                    name=str(col_name),
                    hovertemplate=f'{col_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
                ))
            elif self.current_chart_type == 'stacked_area':
                fig.add_trace(go.Scatter(
                    x=years,
                    y=values,
                    mode='lines',
                    stackgroup='one',  # This enables stacking
                    name=str(col_name),
                    hovertemplate=f'{col_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
                ))
            else:  # bar or stacked_bar
                fig.add_trace(go.Bar(
                    x=years,
                    y=values,
                    name=str(col_name),
                    hovertemplate=f'{col_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
                ))

        # Update layout based on chart type
        layout_kwargs = {
            'title': f"{parameter_name} - Data Overview",
            'xaxis_title': "Year",
            'yaxis_title': "Value",
            'template': 'plotly_white',
            'showlegend': True,
            'legend': dict(
                orientation="h",
                yanchor="top",
                y=-0.3,
                xanchor="center",
                x=0.5
            ),
            'margin': dict(b=120)  # Add bottom margin for legend space
        }

        if self.current_chart_type == 'stacked_bar':
            layout_kwargs['barmode'] = 'stack'
        elif self.current_chart_type == 'bar':
            layout_kwargs['barmode'] = 'group'

        fig.update_layout(**layout_kwargs)

        # Update axes
        fig.update_xaxes(tickmode='linear')
        fig.update_yaxes(automargin=True)

        # Render the chart
        self._render_chart_to_view(fig, f"{parameter_name} Chart")

    def _update_button_states(self):
        """Update button checked states to match current chart type"""
        self.simple_bar_btn.setChecked(self.current_chart_type == 'bar')
        self.stacked_bar_btn.setChecked(self.current_chart_type == 'stacked_bar')
        self.line_chart_btn.setChecked(self.current_chart_type == 'line')
        self.stacked_area_btn.setChecked(self.current_chart_type == 'stacked_area')

    def _on_chart_type_changed(self, chart_type: str):
        """Handle chart type selection change"""
        self.current_chart_type = chart_type

        # Update button states
        self._update_button_states()

        # Emit signal to refresh chart (will be connected by parent)
        self.chart_type_changed.emit(chart_type)

    def _render_chart_to_view(self, fig, title: str):
        """Render a Plotly figure to the QWebEngineView"""
        try:
            # Save to temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                # Simple configuration
                config = {
                    'displayModeBar': True,
                    'displaylogo': False,
                    'responsive': True,
                    'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d', 'autoScale2d']
                }

                # Generate HTML content
                html_content = pio.to_html(
                    fig,
                    full_html=False,
                    include_plotlyjs=False,
                    config=config,
                    div_id='parameter-chart'
                )

                # Create complete HTML structure
                plotly_js_url = "https://cdn.plot.ly/plotly-2.27.0.min.js"
                complete_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{title}</title>
                    <script src="{plotly_js_url}"></script>
                    <style>
                        body {{
                            margin: 0;
                            padding: 5px;
                            font-family: Arial, sans-serif;
                            overflow: hidden;
                        }}
                        #parameter-chart {{
                            width: 100%;
                            height: 100%;
                        }}
                    </style>
                </head>
                <body style="height: 100%; margin: 0;">
                    {html_content}
                </body>
                </html>
                """

                f.write(complete_html)
                temp_file = f.name

            # Load in web view
            self.param_chart.setUrl(QUrl.fromLocalFile(temp_file))

            # Schedule cleanup
            def cleanup():
                import time
                time.sleep(2)  # Wait for chart to load
                try:
                    os.unlink(temp_file)
                except:
                    pass  # Ignore cleanup errors

            threading.Thread(target=cleanup, daemon=True).start()

        except Exception as e:
            self._show_chart_placeholder(f"Error rendering chart: {str(e)}")

    def _show_chart_placeholder(self, message: str = "Select a parameter to view chart"):
        """Show placeholder in chart view when no data is available"""
        html = f"""
        <html>
        <body style="display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial, sans-serif; background-color: #f5f5f5;">
            <div style="text-align: center; color: #666; padding: 20px;">
                <h4>{message}</h4>
            </div>
        </body>
        </html>
        """

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name

        self.param_chart.setUrl(QUrl.fromLocalFile(temp_file))

        # Cleanup
        def cleanup():
            import time
            time.sleep(1)
            try:
                os.unlink(temp_file)
            except:
                pass

        threading.Thread(target=cleanup, daemon=True).start()

    def show_placeholder(self, message: str = "Select a parameter to view chart"):
        """Public method to show placeholder"""
        self._show_chart_placeholder(message)
