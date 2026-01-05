"""
Tests for UI Components

Tests for the extracted UI components from MainWindow refactoring.
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import Parameter, ScenarioData


@pytest.fixture
def sample_parameter():
    """Create a sample parameter for testing"""
    data = [
        ['tech1', 'region1', 2020, 100.0],
        ['tech1', 'region1', 2025, 120.0],
        ['tech2', 'region1', 2020, 80.0],
        ['tech2', 'region1', 2025, 90.0],
    ]
    headers = ['technology', 'region', 'year', 'value']
    df = pd.DataFrame(data, columns=headers)

    metadata = {
        'units': 'MW',
        'dims': ['technology', 'region', 'year'],
        'value_column': 'value',
        'shape': df.shape
    }

    return Parameter('test_param', df, metadata)


@pytest.fixture
def sample_scenario(sample_parameter):
    """Create a sample scenario for testing"""
    scenario = ScenarioData()
    scenario.add_parameter(sample_parameter.name, sample_parameter)
    scenario.sets = {
        'technology': ['tech1', 'tech2'],
        'region': ['region1'],
        'year': [2020, 2025]
    }
    return scenario


class TestDataDisplayWidget:
    """Test DataDisplayWidget functionality"""

    @patch('PyQt5.QtWidgets.QApplication')
    def test_initialization(self, mock_app, sample_parameter):
        """Test DataDisplayWidget initializes correctly"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Check that UI elements are created
        assert hasattr(widget, 'param_title')
        assert hasattr(widget, 'view_toggle_button')
        assert hasattr(widget, 'param_table')
        assert hasattr(widget, 'selector_container')

        # Check initial state
        assert widget.table_display_mode == "raw"
        assert widget.hide_empty_columns == False

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_parameter_raw_mode(self, mock_app, sample_parameter):
        """Test displaying parameter data in raw mode"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Check title was updated
        assert "Parameter: test_param" in widget.param_title.text()

        # Check table was populated (we can't easily test the actual table contents
        # without mocking more Qt components, but we can check the method ran)
        assert widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_parameter_advanced_mode(self, mock_app, sample_parameter):
        """Test displaying parameter data in advanced mode"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Switch to advanced mode
        widget.table_display_mode = "advanced"
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Check title was updated
        assert "Parameter: test_param" in widget.param_title.text()
        assert widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_data_table_parameter(self, mock_app, sample_parameter):
        """Test unified display_data_table method for parameters"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()
        widget.display_data_table(sample_parameter, "Parameter", is_results=False)

        # Check title was updated correctly
        assert "Parameter: test_param" in widget.param_title.text()
        assert widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_data_table_result(self, mock_app, sample_parameter):
        """Test unified display_data_table method for results"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()
        widget.display_data_table(sample_parameter, "Result", is_results=True)

        # Check title was updated correctly
        assert "Result: test_param" in widget.param_title.text()
        assert widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_data_table_empty_dataframe(self, mock_app):
        """Test unified display_data_table method with empty DataFrame"""
        from ui.components.data_display_widget import DataDisplayWidget
        from core.data_models import Parameter
        import pandas as pd

        # Create parameter with empty DataFrame
        empty_df = pd.DataFrame()
        empty_param = Parameter('empty_param', empty_df, {})

        widget = DataDisplayWidget()
        widget.display_data_table(empty_param, "Parameter", is_results=False)

        # Check that table is cleared and button is disabled
        assert not widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_clear_table_display(self, mock_app, sample_parameter):
        """Test _clear_table_display method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # First populate the table
        widget.display_data_table(sample_parameter, "Parameter", is_results=False)
        assert widget.view_toggle_button.isEnabled()

        # Then clear it
        widget._clear_table_display()
        assert not widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_get_current_filters(self, mock_app):
        """Test _get_current_filters method"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QComboBox

        widget = DataDisplayWidget()

        # Mock property selectors
        mock_combo1 = QComboBox()
        mock_combo1.addItem("All")
        mock_combo1.addItem("value1")
        mock_combo1.setCurrentText("value1")

        mock_combo2 = QComboBox()
        mock_combo2.addItem("All")
        mock_combo2.addItem("value2")
        mock_combo2.setCurrentText("All")

        widget.property_selectors = {
            'col1': mock_combo1,
            'col2': mock_combo2
        }

        filters = widget._get_current_filters()

        # Should only include non-"All" selections
        assert 'col1' in filters
        assert filters['col1'] == 'value1'
        assert 'col2' not in filters

    @patch('PyQt5.QtWidgets.QApplication')
    def test_toggle_display_mode(self, mock_app):
        """Test toggling between raw and advanced display modes"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Initially raw mode
        assert widget.table_display_mode == "raw"
        assert not widget.selector_container.isVisible()

        # Toggle to advanced
        widget.view_toggle_button.setChecked(True)
        widget._toggle_display_mode()

        assert widget.table_display_mode == "advanced"
        assert widget.view_toggle_button.text() == "Advanced Display"
        # Note: selector_container visibility would be True but we can't test Qt visibility easily

        # Toggle back to raw
        widget.view_toggle_button.setChecked(False)
        widget._toggle_display_mode()

        assert widget.table_display_mode == "raw"
        assert widget.view_toggle_button.text() == "Raw Display"


class TestChartWidget:
    """Test ChartWidget functionality"""

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_initialization(self, mock_webview, mock_app):
        """Test ChartWidget initializes correctly"""
        from ui.components.chart_widget import ChartWidget

        widget = ChartWidget()

        # Check that UI elements are created
        assert hasattr(widget, 'param_chart')
        assert hasattr(widget, 'simple_bar_btn')
        assert hasattr(widget, 'stacked_bar_btn')
        assert hasattr(widget, 'line_chart_btn')
        assert hasattr(widget, 'stacked_area_btn')

        # Check initial state
        assert widget.current_chart_type == 'bar'
        assert widget.simple_bar_btn.isChecked()

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_chart_type_buttons(self, mock_webview, mock_app):
        """Test chart type button interactions"""
        from ui.components.chart_widget import ChartWidget

        widget = ChartWidget()

        # Test button states
        assert widget.simple_bar_btn.isChecked()
        assert not widget.stacked_bar_btn.isChecked()
        assert not widget.line_chart_btn.isChecked()
        assert not widget.stacked_area_btn.isChecked()

        # Simulate clicking stacked bar button
        widget._on_chart_type_changed('stacked_bar')
        assert widget.current_chart_type == 'stacked_bar'
        # Note: We can't easily test button checked states without more mocking

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    @patch('plotly.graph_objects.Figure')
    @patch('ui.components.chart_widget.pio')
    def test_update_chart(self, mock_pio, mock_figure, mock_webview, mock_app, sample_parameter):
        """Test updating chart with data"""
        from ui.components.chart_widget import ChartWidget

        widget = ChartWidget()

        # Create transformed DataFrame for chart
        chart_df = sample_parameter.df.pivot_table(
            values='value',
            index='year',
            columns=['technology', 'region'],
            aggfunc='first'
        )

        widget.update_chart(chart_df, sample_parameter.name)

        # Verify chart rendering was attempted
        # (We can't test the actual chart content without more complex mocking)
        assert widget.current_chart_type == 'bar'


class TestParameterTreeWidget:
    """Test ParameterTreeWidget functionality"""

    @patch('PyQt5.QtWidgets.QApplication')
    def test_initialization(self, mock_app):
        """Test ParameterTreeWidget initializes correctly"""
        from ui.components.parameter_tree_widget import ParameterTreeWidget

        widget = ParameterTreeWidget()

        # Check initial state
        assert widget.current_view == "input"
        assert widget.headerItem().text(0) == "Parameters"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_update_parameters(self, mock_app, sample_scenario):
        """Test updating parameter tree with scenario data"""
        from ui.components.parameter_tree_widget import ParameterTreeWidget

        widget = ParameterTreeWidget()
        widget.update_parameters(sample_scenario)

        # Check that tree was populated (we can't easily verify the exact structure
        # without more Qt mocking, but we can check the method ran without error)
        assert widget.headerItem().text(0) == "Parameters"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_update_results(self, mock_app, sample_scenario):
        """Test updating parameter tree with results data"""
        from ui.components.parameter_tree_widget import ParameterTreeWidget

        widget = ParameterTreeWidget()
        widget.update_results(sample_scenario)

        # Check view mode changed appropriately
        assert widget.headerItem().text(0) == "Parameters"  # Still shows parameters

    @patch('PyQt5.QtWidgets.QApplication')
    def test_set_view_mode(self, mock_app):
        """Test setting view mode between parameters and results"""
        from ui.components.parameter_tree_widget import ParameterTreeWidget

        widget = ParameterTreeWidget()

        # Test parameters view
        widget.set_view_mode(False)
        assert widget.current_view == "input"
        assert widget.headerItem().text(0) == "Parameters"

        # Test results view
        widget.set_view_mode(True)
        assert widget.current_view == "results"
        assert widget.headerItem().text(0) == "Results"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_categorize_parameter(self, mock_app, sample_parameter):
        """Test parameter categorization logic"""
        from ui.components.parameter_tree_widget import ParameterTreeWidget

        widget = ParameterTreeWidget()

        # Test different parameter names
        test_cases = [
            ('cost_parameter', 'Economic'),
            ('capacity_factor', 'Capacity & Investment'),
            ('demand_load', 'Demand & Consumption'),
            ('efficiency_ratio', 'Technical'),
            ('emission_factor', 'Environmental'),
            ('duration_param', 'Temporal'),
            ('operation_cost', 'Operational'),
            ('bound_limit', 'Bounds & Constraints'),
            ('unknown_param', 'Other'),
        ]

        for param_name, expected_category in test_cases:
            # Create a mock parameter with the test name
            mock_param = MagicMock()
            mock_param.metadata = {}

            category = widget._categorize_parameter(param_name, mock_param)
            assert category == expected_category


class TestFileNavigatorWidget:
    """Test FileNavigatorWidget functionality"""

    @patch('PyQt5.QtWidgets.QApplication')
    def test_initialization(self, mock_app):
        """Test FileNavigatorWidget initializes correctly"""
        from ui.components.file_navigator_widget import FileNavigatorWidget

        widget = FileNavigatorWidget()

        # Check that navigator is created
        assert hasattr(widget, 'navigator')
        assert widget.navigator is not None

    @patch('PyQt5.QtWidgets.QApplication')
    def test_update_input_files(self, mock_app):
        """Test updating input files display"""
        from ui.components.file_navigator_widget import FileNavigatorWidget

        widget = FileNavigatorWidget()
        test_files = ['/path/to/file1.xlsx', '/path/to/file2.xlsx']

        # This should not raise an exception
        widget.update_input_files(test_files)

    @patch('PyQt5.QtWidgets.QApplication')
    def test_update_result_files(self, mock_app):
        """Test updating results files display"""
        from ui.components.file_navigator_widget import FileNavigatorWidget

        widget = FileNavigatorWidget()
        test_files = ['/path/to/results1.xlsx', '/path/to/results2.xlsx']

        # This should not raise an exception
        widget.update_result_files(test_files)

    @patch('PyQt5.QtWidgets.QApplication')
    def test_add_recent_file(self, mock_app):
        """Test adding a file to recent files"""
        from ui.components.file_navigator_widget import FileNavigatorWidget

        widget = FileNavigatorWidget()

        # This should not raise an exception
        widget.add_recent_file('/path/to/test.xlsx', 'input')
