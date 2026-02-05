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
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QPushButton
    from PyQt5.QtWebEngineWidgets import QWebEngineView

from core.data_models import Parameter
from ..ui_styler import UIStyler


class ChartWidget(QWidget):
    """Handles chart rendering and management"""

    # Mapping from dimension names to display names for better readability (same as DataDisplayWidget)
    DIMENSION_DISPLAY_NAMES = {
        'tec': 'technology',
        'node_loc': 'location',
        'node_dest': 'destination',
        'node_origin': 'origin',
        'node_rel': 'relation node',
        'node_share': 'share node',
        'year_vtg': 'vintage year',
        'year_act': 'active year',
        'year_rel': 'relation year',
        'type_tec': 'technology type',
        'type_emiss': 'emission type',
        'type_addon': 'addon type',
        'type_year': 'year type',
        'type_emission': 'emission type',
        'type_rel': 'relation type',
        'commodity': 'commodity',
        'level': 'level',
        'mode': 'mode',
        'time': 'time',
        'time_origin': 'origin time',
        'time_dest': 'destination time',
        'emission': 'emission',
        'land_scenario': 'land scenario',
        'land_type': 'land type',
        'rating': 'rating',
        'grade': 'grade',
        'shares': 'shares',
        'relation': 'relation',
        'value': 'value'
    }

    # Define PyQt signals
    chart_type_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_chart_type = 'stacked_bar'  # 'bar', 'stacked_bar', 'line', 'stacked_area'

        # Widgets will be assigned externally from .ui file
        self.simple_bar_btn: QPushButton
        self.stacked_bar_btn: QPushButton
        self.line_chart_btn: QPushButton
        self.stacked_area_btn: QPushButton
        self.param_chart: QWebEngineView

    def initialize_with_ui_widgets(self):
        """Initialize component with UI widgets assigned externally from .ui file"""
        # Set icons for chart type buttons
        from PyQt5.QtCore import QSize

        self.simple_bar_btn.setIcon(QIcon('assets/icons/icon-bar_chart.png'))
        self.simple_bar_btn.setIconSize(QSize(28, 28))
        self.stacked_bar_btn.setIcon(QIcon('assets/icons/icon-stacked_bar.png'))
        self.stacked_bar_btn.setIconSize(QSize(28, 28))
        self.line_chart_btn.setIcon(QIcon('assets/icons/icon-line_chart.png'))
        self.line_chart_btn.setIconSize(QSize(28, 28))
        self.stacked_area_btn.setIcon(QIcon('assets/icons/icon-area_chart.png'))
        self.stacked_area_btn.setIconSize(QSize(28, 28))

        # Remove text and set tooltips
        self.simple_bar_btn.setText('')
        self.simple_bar_btn.setToolTip('Simple Bar Chart')

        self.stacked_bar_btn.setText('')
        self.stacked_bar_btn.setToolTip('Stacked Bar Chart')

        self.line_chart_btn.setText('')
        self.line_chart_btn.setToolTip('Line Chart')

        self.stacked_area_btn.setText('')
        self.stacked_area_btn.setToolTip('Stacked Area Chart')

        # Connect signals for existing widgets
        self.simple_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('bar'))
        self.stacked_bar_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_bar'))
        self.line_chart_btn.clicked.connect(lambda: self._on_chart_type_changed('line'))
        self.stacked_area_btn.clicked.connect(lambda: self._on_chart_type_changed('stacked_area'))

        # Make buttons checkable
        for btn in [self.simple_bar_btn, self.stacked_bar_btn, self.line_chart_btn, self.stacked_area_btn]:
            btn.setCheckable(True)

        # Initialize state
        self.current_chart_type = 'stacked_bar'
        self.simple_bar_btn.setChecked(False)
        self.stacked_bar_btn.setChecked(True)
        self.line_chart_btn.setChecked(False)
        self.stacked_area_btn.setChecked(False)

        # Apply chart button styling using UIStyler
        for btn in [self.simple_bar_btn, self.stacked_bar_btn, self.line_chart_btn, self.stacked_area_btn]:
            UIStyler.setup_chart_button(btn)

    def update_chart(self, df: pd.DataFrame, parameter_name: str, is_results: bool = False):
        """Update the chart with data from a DataFrame"""
        try:
            # Ensure button states reflect current chart type
            self._update_button_states()

            if df.empty or df.shape[1] == 0:
                self._show_chart_placeholder("No data available for chart")
                return

        except Exception as e:
            print(f"ERROR in update_chart setup: {e}")
            import traceback
            traceback.print_exc()
            return

        # Create chart based on current chart type
        fig = go.Figure()

        # Get years from index (should be years in advanced view)
        years = df.index.tolist()

        # For results data, the years should already be correct from the data transformation
        # Don't try to override them with sequential integers or other mappings

        # Add traces based on chart type
        for col_idx, col_name in enumerate(df.columns):
            col_data = df[col_name]
            if isinstance(col_data, pd.DataFrame):
                # Handle duplicate column names by taking the first column
                col_data = col_data.iloc[:, 0]
            values = col_data.fillna(0).tolist()

            # Skip columns that are entirely empty (all zeros)
            if all(v == 0 for v in values):
                continue

            # Use display name for the trace name
            display_name = self.DIMENSION_DISPLAY_NAMES.get(str(col_name), str(col_name))

            if self.current_chart_type == 'line':
                fig.add_trace(go.Scatter(
                    x=years,
                    y=values,
                    mode='lines+markers',
                    name=display_name,
                    hovertemplate=f'{display_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
                ))
            elif self.current_chart_type == 'stacked_area':
                fig.add_trace(go.Scatter(
                    x=years,
                    y=values,
                    mode='lines',
                    stackgroup='one',  # This enables stacking
                    name=display_name,
                    hovertemplate=f'{display_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
                ))
            else:  # bar or stacked_bar
                fig.add_trace(go.Bar(
                    x=years,
                    y=values,
                    name=display_name,
                    hovertemplate=f'{display_name}<br>Year: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
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

        # Update axes - use exact years from data, not automatic linear ticks
        fig.update_xaxes(
            tickmode='array',
            tickvals=years,
            ticktext=[str(year) for year in years]
        )
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
