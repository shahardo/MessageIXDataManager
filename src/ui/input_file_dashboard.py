"""
Input File Dashboard - displays comprehensive overview of input file data

Shows tables listing all commodities, technologies, years, and regions from all parameters,
along with summary tables showing parameter coverage.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5 import uic
from typing import Any, Dict, List, Set
import pandas as pd

class InputFileDashboard(QWidget):
    """
    Dashboard widget for displaying input file comprehensive overview.

    Shows:
    - Table listing all commodities from all parameters
    - Table listing all technologies from all parameters
    - Table listing all years from all parameters
    - Table listing all regions from all parameters
    - Summary table with technologies vs parameters (green 'V' for presence)
    - Summary table with commodities vs parameters (green 'V' for presence)
    """

    def __init__(self, input_manager):
        super().__init__()
        self.input_manager = input_manager
        self.current_scenario = None

        # Load UI from .ui file
        ui_file = 'src/ui/input_file_dashboard.ui'
        ui_loaded = False
        try:
            uic.loadUi(ui_file, self)
            print("Input file dashboard UI loaded successfully")
            ui_loaded = True
        except Exception as e:
            print(f"Error loading UI: {e}")
            # Continue without UI for testing purposes

        if not ui_loaded or not hasattr(self, 'dashboardTabs'):
            # UI load failed or in test environment
            self.web_views = {}
            return

        self.dashboardTabs.currentChanged.connect(self._on_tab_changed)

        # Map web views from UI file or create mocks for testing
        self.web_views = {
            'overview': self.overviewWebView,
            'commodities': self.commoditiesWebView,
            'technologies': self.technologiesWebView,
            'years': self.yearsWebView,
            'regions': self.regionsWebView,
            'tech_summary': self.techSummaryWebView,
            'commodity_summary': self.commoditySummaryWebView
        }

        # Enable JavaScript for web views
        self._setup_web_views()

    def _setup_web_views(self):
        """Set up web view settings"""
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings

        for web_view in self.web_views.values():
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

    def update_dashboard(self, scenario: Any):
        """Update the dashboard with data from the input scenario"""
        self.current_scenario = scenario

        if not scenario or not scenario.parameters:
            # Show placeholder if no scenario loaded
            for web_view in self.web_views.values():
                self._show_placeholder(web_view, "No input file data available")
            return

        try:
            # Extract all unique values from all parameters
            commodities, technologies, years, regions = self._extract_unique_values(scenario)

            # Create parameter coverage mappings
            tech_coverage, commodity_coverage = self._create_coverage_mappings(scenario)

            # Generate HTML content for each tab
            self._render_overview_tab(len(commodities), len(technologies), len(years), len(regions), len(scenario.parameters))
            self._render_list_tab('commodities', sorted(commodities), "All Commodities")
            self._render_list_tab('technologies', sorted(technologies), "All Technologies")
            self._render_list_tab('years', sorted(years), "All Years")
            self._render_list_tab('regions', sorted(regions), "All Regions")
            self._render_tech_summary_tab(tech_coverage, list(technologies))
            self._render_commodity_summary_tab(commodity_coverage, list(commodities))

        except Exception as e:
            print(f"Error updating input file dashboard: {str(e)}")
            for web_view in self.web_views.values():
                self._show_placeholder(web_view, f"Error: {str(e)}")

    def _extract_unique_values(self, scenario) -> tuple[Set[str], Set[str], Set[str], Set[str]]:
        """Extract unique commodities, technologies, years, and regions from all parameters"""
        commodities = set()
        technologies = set()
        years = set()
        regions = set()

        # Common dimension names to look for
        dim_mappings = {
            'commodity': ['commodity', 'com'],
            'technology': ['tec', 'technology'],
            'year': ['year', 'year_act', 'year_vtg'],
            'region': ['node', 'node_loc', 'node_origin', 'node_dest', 'node_loc']
        }

        for param_name, parameter in scenario.parameters.items():
            df = parameter.df
            if df is None or df.empty:
                continue

            # Check each dimension type
            for dim_type, possible_cols in dim_mappings.items():
                for col in possible_cols:
                    if col in df.columns:
                        # Get unique values, convert to string, and filter out empty/NaN
                        unique_vals = df[col].dropna().unique()
                        clean_vals = [str(val).strip() for val in unique_vals if str(val).strip()]

                        if dim_type == 'commodity':
                            commodities.update(clean_vals)
                        elif dim_type == 'technology':
                            technologies.update(clean_vals)
                        elif dim_type == 'year':
                            # Convert years to integers if possible
                            for val in clean_vals:
                                try:
                                    years.add(int(float(val)))
                                except (ValueError, TypeError):
                                    years.add(val)
                        elif dim_type == 'region':
                            regions.update(clean_vals)

        return commodities, technologies, years, regions

    def _create_coverage_mappings(self, scenario) -> tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """Create mappings of which parameters reference which technologies and commodities"""
        tech_coverage = {}  # param_name -> set of technologies
        commodity_coverage = {}  # param_name -> set of commodities

        # Common dimension names
        tech_cols = ['tec', 'technology']
        commodity_cols = ['commodity', 'com']

        for param_name, parameter in scenario.parameters.items():
            df = parameter.df
            if df is None or df.empty:
                continue

            # Find technologies in this parameter
            param_techs = set()
            for col in tech_cols:
                if col in df.columns:
                    unique_vals = df[col].dropna().unique()
                    clean_vals = [str(val).strip() for val in unique_vals if str(val).strip()]
                    param_techs.update(clean_vals)

            if param_techs:
                tech_coverage[param_name] = param_techs

            # Find commodities in this parameter
            param_commodities = set()
            for col in commodity_cols:
                if col in df.columns:
                    unique_vals = df[col].dropna().unique()
                    clean_vals = [str(val).strip() for val in unique_vals if str(val).strip()]
                    param_commodities.update(clean_vals)

            if param_commodities:
                commodity_coverage[param_name] = param_commodities

        return tech_coverage, commodity_coverage

    def _render_overview_tab(self, commodity_count: int, tech_count: int, year_count: int, region_count: int, param_count: int):
        """Render the overview tab with summary statistics"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .stats-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 5px;
                }}
                .stat-label {{
                    font-size: 10px;
                    color: #7f8c8d;
                }}
                .summary-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .summary-table th, .summary-table td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                    font-size: 11px;
                }}
                .summary-table th {{
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                }}
                .summary-table tr:hover {{
                    background-color: #f5f5f5;
                }}
                h2 {{
                    color: #2c3e50;
                    margin-bottom: 20px;
                    font-size: 18px;
                }}
                h3 {{
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <h2>Input File Overview</h2>

            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-value">{param_count}</div>
                    <div class="stat-label">Total Parameters</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{tech_count}</div>
                    <div class="stat-label">Unique Technologies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{commodity_count}</div>
                    <div class="stat-label">Unique Commodities</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{year_count}</div>
                    <div class="stat-label">Unique Years</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{region_count}</div>
                    <div class="stat-label">Unique Regions</div>
                </div>
            </div>

            <h3>Parameter Summary</h3>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Parameter Name</th>
                        <th>Technologies</th>
                        <th>Commodities</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add parameter rows (show first 20 parameters to avoid overwhelming the table)
        param_names = list(self.current_scenario.parameters.keys())[:20]
        for param_name in param_names:
            parameter = self.current_scenario.parameters[param_name]
            tech_count = self._count_dimension_values(parameter, ['tec', 'technology'])
            commodity_count = self._count_dimension_values(parameter, ['commodity', 'com'])

            html += f"""
                    <tr>
                        <td>{param_name}</td>
                        <td>{tech_count}</td>
                        <td>{commodity_count}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </body>
        </html>
        """

        if 'overview' in self.web_views:
            self.web_views['overview'].setHtml(html)

    def _count_dimension_values(self, parameter, dimension_names: List[str]) -> int:
        """Count unique values for a dimension in a parameter"""
        df = parameter.df
        if df is None or df.empty:
            return 0

        for dim_name in dimension_names:
            if dim_name in df.columns:
                return len(df[dim_name].dropna().unique())

        return 0

    def _render_list_tab(self, tab_name: str, items: List[str], title: str):
        """Render a tab showing a list of items"""
        if tab_name not in self.web_views:
            return

        # Split items into chunks for pagination (100 items per page)
        chunk_size = 100
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

        if not chunks:
            html = self._create_empty_list_html(title)
        else:
            html = self._create_list_html(title, chunks[0])

            # Add pagination if needed
            if len(chunks) > 1:
                html = html.replace('</body>', f"""
                    <div style="margin-top: 20px; text-align: center;">
                        <span>Showing {min(chunk_size, len(items))} of {len(items)} items</span>
                    </div>
                    </body>
                """)

        self.web_views[tab_name].setHtml(html)

    def _create_empty_list_html(self, title: str) -> str:
        """Create HTML for empty list"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .empty-message {{
                    text-align: center;
                    padding: 40px;
                    color: #7f8c8d;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <h2>{title}</h2>
            <div class="empty-message">
                No items found
            </div>
        </body>
        </html>
        """

    def _create_list_html(self, title: str, items: List[str]) -> str:
        """Create HTML for item list"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .item-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 10px;
                    margin-top: 10px;
                }}
                .item-card {{
                    background-color: white;
                    border-radius: 4px;
                    padding: 8px 12px;
                    border: 1px solid #e0e0e0;
                    font-size: 12px;
                    color: #2c3e50;
                }}
                .item-card:hover {{
                    background-color: #f5f5f5;
                    border-color: #3498db;
                }}
                h2 {{
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 18px;
                }}
                .search-box {{
                    margin-bottom: 15px;
                    padding: 8px;
                    width: 100%;
                    box-sizing: border-box;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <h2>{title}</h2>
            <input type="text" class="search-box" placeholder="Search..." onkeyup="filterItems()">

            <div class="item-grid" id="itemGrid">
        """

        # Add items
        for item in items:
            html += f'                <div class="item-card">{item}</div>\n'

        html += """
            </div>

            <script>
                function filterItems() {
                    const searchBox = document.querySelector('.search-box');
                    const filter = searchBox.value.toLowerCase();
                    const items = document.querySelectorAll('.item-card');

                    items.forEach(item => {
                        const text = item.textContent.toLowerCase();
                        if (text.includes(filter)) {
                            item.style.display = '';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                }
            </script>
        </body>
        </html>
        """

        return html

    def _render_tech_summary_tab(self, tech_coverage: Dict[str, Set[str]], all_technologies: List[str]):
        """Render technology summary tab showing which parameters reference which technologies"""
        if 'tech_summary' not in self.web_views:
            return

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .summary-table {
                    width: 100%;
                    border-collapse: collapse;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .summary-table th, .summary-table td {
                    padding: 8px 12px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                    border-right: 1px solid #e0e0e0;
                    font-size: 12px;
                }
                .summary-table th:not(:first-child), .summary-table td:not(:first-child) {
                    max-width: 50px;
                    overflow: show;
                    white-space: normal; /* Allows text to wrap (this is the default) */
                }
                .summary-table th {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }
                .summary-table th:first-child {
                    left: 0;
                    z-index: 20;
                }
                .summary-table td:first-child {
                    left: 0;
                    background-color: white;
                    font-weight: bold;
                }
                .check-cell {
                    text-align: center;
                    background-color: #ecf0f1;
                }
                .check-mark {
                    color: #27ae60;
                    font-weight: bold;
                    font-size: 14px;
                }
                .table-container {
                    overflow-x: auto;
                    max-height: 600px;
                    overflow-y: auto;
                }
                h2 {
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 18px;
                }
                .search-box {
                    margin-bottom: 15px;
                    padding: 8px;
                    width: 100%;
                    box-sizing: border-box;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
            <h2>Technology Coverage by Parameters</h2>
            <input type="text" class="search-box" placeholder="Search technologies or parameters..." onkeyup="filterTable()">

            <div class="table-container">
                <table class="summary-table" id="techSummaryTable">
                    <thead>
                        <tr>
                            <th>Technology</th>
        """

        # Add parameter columns
        sorted_params = sorted(tech_coverage.keys())
        for param_name in sorted_params:
            html += f'                            <th>{param_name}</th>\n'

        html += """
                        </tr>
                    </thead>
                    <tbody>
        """

        # Add technology rows
        for tech in all_technologies:
            html += f'                        <tr><td>{tech}</td>\n'

            for param_name in sorted_params:
                has_tech = tech in tech_coverage.get(param_name, set())
                cell_content = '✓' if has_tech else ''
                cell_class = 'check-mark' if has_tech else ''
                html += f'                            <td class="check-cell">{cell_content}</td>\n'

            html += '                        </tr>\n'

        html += """
                    </tbody>
                </table>
            </div>

            <script>
                function filterTable() {
                    const searchBox = document.querySelector('.search-box');
                    const filter = searchBox.value.toLowerCase();
                    const rows = document.querySelectorAll('#techSummaryTable tbody tr');

                    rows.forEach(row => {
                        const techCell = row.cells[0];
                        const techText = techCell.textContent.toLowerCase();

                        let paramMatch = false;
                        for (let i = 1; i < row.cells.length; i++) {
                            const paramName = document.querySelectorAll('th')[i].textContent.toLowerCase();
                            if (paramName.includes(filter)) {
                                paramMatch = true;
                                break;
                            }
                        }

                        if (techText.includes(filter) || paramMatch) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                }
            </script>
        </body>
        </html>
        """

        self.web_views['tech_summary'].setHtml(html)
        self.web_views['tech_summary'].update()

    def _render_commodity_summary_tab(self, commodity_coverage: Dict[str, Set[str]], all_commodities: List[str]):
        """Render commodity summary tab showing which parameters reference which commodities"""
        if 'commodity_summary' not in self.web_views:
            return

        if not all_commodities:
            html = self._create_empty_list_html("Commodity Coverage by Parameters")
            self.web_views['commodity_summary'].setHtml(html)
            return

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .summary-table {
                    width: 100%;
                    border-collapse: collapse;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .summary-table th, .summary-table td {
                    padding: 8px 12px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                    border-right: 1px solid #e0e0e0;
                    font-size: 12px;
                }
                .summary-table th:not(:first-child), .summary-table td:not(:first-child) {
                    max-width: 50px;
                    overflow: show;
                    white-space: normal; /* Allows text to wrap (this is the default) */
                }
                .summary-table th {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }
                .summary-table th:first-child {
                    left: 0;
                    z-index: 20;
                }
                .summary-table td:first-child {
                    left: 0;
                    background-color: white;
                    font-weight: bold;
                }
                .check-cell {
                    text-align: center;
                    background-color: #ecf0f1;
                }
                .check-mark {
                    color: #27ae60;
                    font-weight: bold;
                    font-size: 14px;
                }
                .table-container {
                    overflow-x: auto;
                    max-height: 600px;
                    overflow-y: auto;
                }
                h2 {
                    color: #2c3e50;
                    margin-bottom: 15px;
                    font-size: 18px;
                }
                .search-box {
                    margin-bottom: 15px;
                    padding: 8px;
                    width: 100%;
                    box-sizing: border-box;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
            <h2>Commodity Coverage by Parameters</h2>
            <input type="text" class="search-box" placeholder="Search commodities or parameters..." onkeyup="filterTable()">

            <div class="table-container">
                <table class="summary-table" id="commoditySummaryTable">
                    <thead>
                        <tr>
                            <th>Commodity</th>
        """

        # Add parameter columns
        sorted_params = sorted(commodity_coverage.keys())
        for param_name in sorted_params:
            html += f'                            <th>{param_name}</th>\n'

        html += """
                        </tr>
                    </thead>
                    <tbody>
        """

        # Add commodity rows
        for commodity in all_commodities:
            html += f'                        <tr><td>{commodity}</td>\n'

            for param_name in sorted_params:
                has_commodity = commodity in commodity_coverage.get(param_name, set())
                cell_content = '✓' if has_commodity else ''
                html += f'                            <td class="check-cell">{cell_content}</td>\n'

            html += '                        </tr>\n'

        html += """
                    </tbody>
                </table>
            </div>

            <script>
                function filterTable() {
                    const searchBox = document.querySelector('.search-box');
                    const filter = searchBox.value.toLowerCase();
                    const rows = document.querySelectorAll('#commoditySummaryTable tbody tr');

                    rows.forEach(row => {
                        const commodityCell = row.cells[0];
                        const commodityText = commodityCell.textContent.toLowerCase();

                        let paramMatch = false;
                        for (let i = 1; i < row.cells.length; i++) {
                            const paramName = document.querySelectorAll('th')[i].textContent.toLowerCase();
                            if (paramName.includes(filter)) {
                                paramMatch = true;
                                break;
                            }
                        }

                        if (commodityText.includes(filter) || paramMatch) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                }
            </script>
        </body>
        </html>
        """

        self.web_views['commodity_summary'].setHtml(html)

    def _on_tab_changed(self, index):
        """Handle tab change to update the web view"""
        tab_names = ['overview', 'commodities', 'technologies', 'years', 'regions', 'tech_summary', 'commodity_summary']
        if 0 <= index < len(tab_names):
            tab_name = tab_names[index]
            if tab_name in self.web_views:
                self.web_views[tab_name].update()

    def _show_placeholder(self, web_view: QWebEngineView, message: str):
        """Show placeholder in a web view"""
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

        web_view.setHtml(html)
