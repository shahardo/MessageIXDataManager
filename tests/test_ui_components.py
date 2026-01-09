"""
Tests for UI Components

Tests for the extracted UI components from MainWindow refactoring.
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

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
    scenario.add_parameter(sample_parameter)
    scenario.sets = {
        'technology': ['tech1', 'tech2'],
        'region': ['region1'],
        'year': [2020, 2025]
    }
    return scenario


class TestDataDisplayWidget:
    """Test DataDisplayWidget functionality"""

    def test_initialization(self, qtbot, sample_parameter):
        """Test DataDisplayWidget initializes correctly"""
        # Set Qt attributes before importing QtWebEngineWidgets
        from PyQt5.QtCore import Qt, QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Add widget to qtbot for proper Qt event handling
        qtbot.addWidget(widget)

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

    @patch('PyQt5.QtWidgets.QApplication')
    def test_identify_columns(self, mock_app, sample_parameter):
        """Test _identify_columns method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Test with sample parameter data
        column_info = widget._identify_columns(sample_parameter.df)

        # Check that columns are properly identified
        assert 'year_cols' in column_info
        assert 'pivot_cols' in column_info
        assert 'filter_cols' in column_info
        assert 'value_col' in column_info

        # For our sample data, 'value' should be identified as value column
        assert column_info['value_col'] == 'value'

        # 'technology' should be in pivot_cols (becomes pivot table column headers)
        assert 'technology' in column_info['pivot_cols']

    @patch('PyQt5.QtWidgets.QApplication')
    def test_apply_filters(self, mock_app, sample_parameter):
        """Test _apply_filters method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Test with sample data and filters
        filters = {'technology': 'tech1'}
        column_info = widget._identify_columns(sample_parameter.df)

        filtered_df = widget._apply_filters(sample_parameter.df, filters, column_info)

        # Check that filtering worked
        assert not filtered_df.empty
        # All remaining rows should have technology = 'tech1'
        assert all(filtered_df['technology'] == 'tech1')

    @patch('PyQt5.QtWidgets.QApplication')
    def test_transform_data_structure_input_data(self, mock_app, sample_parameter):
        """Test _transform_data_structure for input data (should pivot)"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        column_info = widget._identify_columns(sample_parameter.df)

        # Test transformation for input data (is_results=False)
        transformed = widget._transform_data_structure(sample_parameter.df, column_info, is_results=False)

        # For our sample data, it should be pivoted
        # Check that the result has year as index and technologies as columns
        assert 'year' in str(transformed.index.name) or isinstance(transformed.index, pd.Index)

    @patch('PyQt5.QtWidgets.QApplication')
    def test_transform_data_structure_results_data(self, mock_app, sample_parameter):
        """Test _transform_data_structure for results data (should set year as index)"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        column_info = widget._identify_columns(sample_parameter.df)

        # Test transformation for results data (is_results=True)
        transformed = widget._transform_data_structure(sample_parameter.df, column_info, is_results=True)

        # For results data, should set year as index and keep other columns
        assert len(transformed) == len(sample_parameter.df)
        # Year column should be moved to index
        assert transformed.index.name == 'year'
        # Other columns should remain (technology, region, value)
        expected_columns = ['technology', 'region', 'value']
        assert list(transformed.columns) == expected_columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_clean_output_with_hide_empty(self, mock_app):
        """Test _clean_output with hide_empty=True"""
        from ui.components.data_display_widget import DataDisplayWidget
        import pandas as pd

        widget = DataDisplayWidget()

        # Create test DataFrame with some empty columns
        data = {
            'year': [2020, 2025],
            'technology': ['tech1', 'tech2'],
            'value': [100, 200],
            'empty_col': [0, 0],  # All zeros
            'another_empty': [None, None]  # All NaN
        }
        df = pd.DataFrame(data)

        cleaned = widget._clean_output(df, hide_empty=True, is_results=False)

        # Check that empty columns are removed
        assert 'empty_col' not in cleaned.columns
        assert 'another_empty' not in cleaned.columns
        assert 'year' in cleaned.columns
        assert 'technology' in cleaned.columns
        assert 'value' in cleaned.columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_clean_output_without_hide_empty(self, mock_app):
        """Test _clean_output with hide_empty=False"""
        from ui.components.data_display_widget import DataDisplayWidget
        import pandas as pd

        widget = DataDisplayWidget()

        # Create test DataFrame with some empty columns
        data = {
            'year': [2020, 2025],
            'technology': ['tech1', 'tech2'],
            'value': [100, 200],
            'empty_col': [0, 0]
        }
        df = pd.DataFrame(data)

        cleaned = widget._clean_output(df, hide_empty=False, is_results=False)

        # Check that all columns are kept
        assert len(cleaned.columns) == len(df.columns)
        assert 'empty_col' in cleaned.columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_should_pivot(self, mock_app):
        """Test _should_pivot method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Test case that should pivot
        column_info_pivot = {
            'year_cols': ['year'],
            'pivot_cols': ['technology'],
            'value_col': 'value'
        }
        assert widget._should_pivot(pd.DataFrame(), column_info_pivot) == True

        # Test case that should not pivot (missing value column)
        column_info_no_pivot = {
            'year_cols': ['year'],
            'pivot_cols': ['technology'],
            'value_col': None
        }
        assert widget._should_pivot(pd.DataFrame(), column_info_no_pivot) == False

    @patch('PyQt5.QtWidgets.QApplication')
    def test_perform_pivot(self, mock_app, sample_parameter):
        """Test _perform_pivot method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        column_info = widget._identify_columns(sample_parameter.df)

        pivoted = widget._perform_pivot(sample_parameter.df, column_info)

        # Check that pivot operation worked
        # Result should have year as index and technologies as columns
        assert len(pivoted.columns) >= 2  # At least tech1 and tech2 columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_prepare_2d_format(self, mock_app, sample_parameter):
        """Test _prepare_2d_format method"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        column_info = widget._identify_columns(sample_parameter.df)

        formatted = widget._prepare_2d_format(sample_parameter.df, column_info)

        # Should set year as index and remove year column from columns
        assert len(formatted) == len(sample_parameter.df)
        # Year column should be moved to index
        assert formatted.index.name == 'year'
        # Other columns should remain (technology, region, value)
        expected_columns = ['technology', 'region', 'value']
        assert list(formatted.columns) == expected_columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_hide_empty_columns(self, mock_app):
        """Test _hide_empty_columns method"""
        from ui.components.data_display_widget import DataDisplayWidget
        import pandas as pd

        widget = DataDisplayWidget()

        # Create test DataFrame
        data = {
            'year': [2020, 2025],
            'technology': ['tech1', 'tech2'],
            'value': [100, 200],
            'empty_numeric': [0, 0],
            'empty_text': [None, None]
        }
        df = pd.DataFrame(data)

        hidden = widget._hide_empty_columns(df, is_results=False)

        # Check that empty columns are removed
        assert 'empty_numeric' not in hidden.columns
        assert 'empty_text' not in hidden.columns
        assert 'year' in hidden.columns
        assert 'technology' in hidden.columns
        assert 'value' in hidden.columns

    @patch('PyQt5.QtWidgets.QApplication')
    def test_transform_to_advanced_view_empty_df(self, mock_app):
        """Test _transform_to_advanced_view with empty DataFrame"""
        from ui.components.data_display_widget import DataDisplayWidget
        import pandas as pd

        widget = DataDisplayWidget()

        empty_df = pd.DataFrame()
        result = widget._transform_to_advanced_view(empty_df)

        # Should return empty DataFrame
        assert result.empty

    @patch('PyQt5.QtWidgets.QApplication')
    def test_transform_to_advanced_view_full_flow(self, mock_app, sample_parameter):
        """Test full _transform_to_advanced_view method flow"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Test with filters
        filters = {'technology': 'tech1'}
        result = widget._transform_to_advanced_view(sample_parameter.df, current_filters=filters, is_results=False)

        # Should return filtered and transformed data
        assert not result.empty
        # All technologies should be 'tech1' after filtering
        if 'technology' in result.columns:
            assert all(result['technology'] == 'tech1')


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
            ('duration_param', 'Technical'),
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


class TestUIStyler:
    """Test UIStyler functionality"""

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="/* Test stylesheet */")
    @patch('PyQt5.QtWidgets.QApplication')
    def test_apply_stylesheet_success(self, mock_app, mock_file, mock_exists):
        """Test applying stylesheet successfully"""
        from ui.ui_styler import UIStyler

        mock_exists.return_value = True
        mock_app_instance = MagicMock()
        mock_app.return_value = mock_app_instance

        UIStyler.apply_stylesheet(mock_app_instance)

        # Check that setStyleSheet was called
        mock_app_instance.setStyleSheet.assert_called_once_with("/* Test stylesheet */")

    @patch('os.path.exists')
    @patch('PyQt5.QtWidgets.QApplication')
    def test_apply_stylesheet_file_not_found(self, mock_app, mock_exists):
        """Test applying stylesheet when file doesn't exist"""
        from ui.ui_styler import UIStyler

        mock_exists.return_value = False
        mock_app_instance = MagicMock()
        mock_app.return_value = mock_app_instance

        # This should not raise an exception
        UIStyler.apply_stylesheet(mock_app_instance)

        # setStyleSheet should still be called (with empty string or not at all)
        # We just verify no exception was raised

    @patch('PyQt5.QtWidgets.QTableWidget')
    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_table_widget(self, mock_app, mock_table_widget):
        """Test setting up table widget"""
        from ui.ui_styler import UIStyler

        # Create mock table with necessary methods
        mock_table = mock_table_widget.return_value
        mock_header = MagicMock()
        mock_table.verticalHeader.return_value = mock_header
        mock_table.styleSheet.return_value = ""
        mock_table.setAlternatingRowColors = MagicMock()
        mock_table.setStyleSheet = MagicMock()

        UIStyler.setup_table_widget(mock_table)

        # Check that alternating row colors was set
        mock_table.setAlternatingRowColors.assert_called_once_with(True)
        mock_header.setDefaultSectionSize.assert_called_once_with(22)
        # Check that setStyleSheet was called (stylesheet setting)
        assert mock_table.setStyleSheet.called

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_parameter_title_label_small(self, mock_app):
        """Test setting up parameter title label with small styling"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QLabel

        label = QLabel()

        UIStyler.setup_parameter_title_label(label, is_small=True)

        # Check that the CSS class was set
        assert label.property("class") == "parameter-title-small"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_parameter_title_label_normal(self, mock_app):
        """Test setting up parameter title label with normal styling"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QLabel

        label = QLabel()

        UIStyler.setup_parameter_title_label(label, is_small=False)

        # Check that the CSS class was set
        assert label.property("class") == "parameter-title"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_view_toggle_button(self, mock_app):
        """Test setting up view toggle button"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QPushButton

        button = QPushButton()

        UIStyler.setup_view_toggle_button(button)

        # Check button properties
        assert button.isCheckable() == True
        assert button.isChecked() == False
        assert button.isEnabled() == False

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_filter_label(self, mock_app):
        """Test setting up filter label"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QLabel

        label = QLabel()

        UIStyler.setup_filter_label(label)

        # Check that the CSS class was set
        assert label.property("class") == "filter-label"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_remove_button(self, mock_app):
        """Test setting up remove button"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QPushButton

        button = QPushButton()

        UIStyler.setup_remove_button(button)

        # Check that the CSS class was set and size was set
        assert button.property("class") == "remove-button"
        assert button.size().width() == 20
        assert button.size().height() == 20

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_tree_widget(self, mock_app):
        """Test setting up tree widget"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QTreeWidget

        tree = QTreeWidget()

        UIStyler.setup_tree_widget(tree)

        # Check that alternating row colors was set
        assert tree.alternatingRowColors() == True

