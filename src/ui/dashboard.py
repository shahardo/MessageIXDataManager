"""
Dashboard component for displaying results visualizations
"""

import plotly.graph_objects as go
import plotly.io as pio
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import tempfile
import os


class ResultsDashboard(QWidget):
    """Dashboard widget for displaying result visualizations"""

    def __init__(self, results_analyzer):
        super().__init__()
        self.results_analyzer = results_analyzer
        self.current_chart_type = 'line'
        self.current_result = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dashboard UI"""
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        # Result selector
        controls_layout.addWidget(QLabel("Result:"))
        self.result_combo = QComboBox()
        self.result_combo.currentTextChanged.connect(self._on_result_changed)
        controls_layout.addWidget(self.result_combo)

        # Chart type selector
        controls_layout.addWidget(QLabel("Chart Type:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(['line', 'bar', 'area'])
        self.chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        controls_layout.addWidget(self.chart_type_combo)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_chart)
        controls_layout.addWidget(refresh_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Chart display
        self.chart_view = QWebEngineView()
        self.chart_view.setMinimumHeight(400)

        # Enable JavaScript and other web features
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings
        settings = self.chart_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        layout.addWidget(self.chart_view)

        # Show placeholder
        self._show_placeholder()

    def update_results(self, results_available: bool = True):
        """Update dashboard when results are loaded"""
        if results_available and self.results_analyzer.current_results:
            result_names = self.results_analyzer.get_all_result_names()
            self.result_combo.clear()
            self.result_combo.addItems(result_names)

            if result_names:
                self.result_combo.setCurrentIndex(0)
                self._update_chart()
            else:
                self._show_placeholder()
        else:
            self.result_combo.clear()
            self._show_placeholder()

    def _on_result_changed(self, result_name: str):
        """Handle result selection change"""
        if result_name:
            self.current_result = result_name
            self._update_chart()

    def _on_chart_type_changed(self, chart_type: str):
        """Handle chart type selection change"""
        if chart_type:
            self.current_chart_type = chart_type
            self._update_chart()

    def _refresh_chart(self):
        """Refresh the current chart"""
        self._update_chart()

    def _update_chart(self):
        """Update the displayed chart"""
        if not self.current_result:
            return

        # Get chart data from results analyzer
        chart_data = self.results_analyzer.prepare_chart_data(
            self.current_result, self.current_chart_type
        )

        if chart_data:
            self._render_chart(chart_data)
        else:
            self._show_placeholder("No data available for charting")

    def _render_chart(self, chart_data: dict):
        """Render chart using Plotly"""
        try:
            # Create figure based on chart type
            if self.current_chart_type == 'line':
                fig = go.Figure()
                for trace_data in chart_data['data']:
                    fig.add_trace(go.Scatter(
                        x=trace_data['x'],
                        y=trace_data['y'],
                        mode='lines+markers',
                        name=trace_data.get('name', 'Data')
                    ))

            elif self.current_chart_type == 'bar':
                fig = go.Figure()
                for trace_data in chart_data['data']:
                    fig.add_trace(go.Bar(
                        x=trace_data['x'],
                        y=trace_data['y'],
                        name=trace_data.get('name', 'Data')
                    ))

            elif self.current_chart_type == 'area':
                fig = go.Figure()
                for trace_data in chart_data['data']:
                    fig.add_trace(go.Scatter(
                        x=trace_data['x'],
                        y=trace_data['y'],
                        fill='tozeroy',
                        mode='lines',
                        name=trace_data.get('name', 'Data')
                    ))

            # Update layout
            fig.update_layout(
                title=chart_data.get('title', 'Results Chart'),
                xaxis_title=chart_data.get('x_label', 'X'),
                yaxis_title=chart_data.get('y_label', 'Y'),
                template='plotly_white'
            )

            # Save to temporary HTML file with simplified configuration
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                # Simple configuration to avoid issues
                config = {
                    'displayModeBar': True,
                    'displaylogo': False,
                    'responsive': True
                }

                # Generate minimal HTML without Plotly.js initially
                html_content = pio.to_html(
                    fig,
                    full_html=False,
                    include_plotlyjs=False,
                    config=config,
                    div_id='plotly-chart'
                )

                # Add simple CSS override to fix styling issues (removed problematic :focus-visible rule)
                css_override = """
                <style>
                /* Basic Plotly styling */
                .js-plotly-plot .plotly {
                    font-family: Arial, sans-serif;
                }

                .js-plotly-plot .plotly .modebar {
                    background: rgba(255, 255, 255, 0.9) !important;
                }

                .js-plotly-plot .plotly .modebar-btn {
                    border: 1px solid #ccc !important;
                    background: #fff !important;
                }

                .js-plotly-plot .plotly .modebar-btn:hover {
                    background: #f0f0f0 !important;
                }

                /* Override any problematic focus styles */
                .js-plotly-plot .plotly .modebar-btn:focus {
                    outline: 1px solid #007bff;
                    outline-offset: 1px;
                    border-radius: 3px;
                }
                </style>
                """

                # Create complete HTML structure with Plotly.js loaded from CDN
                plotly_js_url = "https://cdn.plot.ly/plotly-2.27.0.min.js"
                complete_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>{chart_data.get('title', 'Results Chart')}</title>
                    <script src="{plotly_js_url}"></script>
                    {css_override}
                </head>
                <body>
                    {html_content}
                    <script>
                    // Wait for Plotly to be available and initialize
                    function initChart() {{
                        if (typeof Plotly !== 'undefined') {{
                            console.log('Plotly loaded successfully');
                            // Chart should already be rendered by plotly's to_html
                        }} else {{
                            console.error('Plotly failed to load');
                        }}
                    }}

                    // Check if already loaded, otherwise wait
                    if (typeof Plotly !== 'undefined') {{
                        initChart();
                    }} else {{
                        window.addEventListener('load', function() {{
                            setTimeout(initChart, 100);
                        }});
                    }}
                    </script>
                </body>
                </html>
                """

                f.write(complete_html)
                temp_file = f.name

            # Load in web view
            self.chart_view.setUrl(QUrl.fromLocalFile(temp_file))

            # Schedule cleanup (after a delay to ensure loading)
            import threading
            def cleanup():
                import time
                time.sleep(2)  # Wait for chart to load
                try:
                    os.unlink(temp_file)
                except:
                    pass  # Ignore cleanup errors

            threading.Thread(target=cleanup, daemon=True).start()

        except Exception as e:
            self._show_placeholder(f"Error rendering chart: {str(e)}")

    def _show_placeholder(self, message: str = "Load results to view charts"):
        """Show placeholder when no chart is available"""
        html = f"""
        <html>
        <body style="display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial, sans-serif;">
            <div style="text-align: center; color: #666;">
                <h3>{message}</h3>
                <p>Use File → Open Results File to load data for visualization</p>
            </div>
        </body>
        </html>
        """

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
            temp_file = f.name

        self.chart_view.setUrl(QUrl.fromLocalFile(temp_file))

        # Cleanup
        import threading
        def cleanup():
            import time
            time.sleep(1)
            try:
                os.unlink(temp_file)
            except:
                pass

        threading.Thread(target=cleanup, daemon=True).start()
