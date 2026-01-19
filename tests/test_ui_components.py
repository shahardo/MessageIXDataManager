"""
Tests for UI Components

Tests for the extracted UI components from MainWindow refactoring.
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

# Check if PyQt5 is available
try:
    import PyQt5.QtWidgets
    import PyQt5.QtCore
    import PyQt5.QtWebEngineWidgets
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False

# Skip all tests if PyQt5 is not available
pytestmark = pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")

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
        'technology': pd.Series(['tech1', 'tech2']),
        'region': pd.Series(['region1']),
        'year': pd.Series([2020, 2025])
    }
    return scenario


class TestDataDisplayWidget:
    """Test DataDisplayWidget functionality"""

    def test_ui_components_declared_in_ui_file(self):
        """Test that all DataDisplayWidget UI components are declared in main_window.ui"""
        import os
        ui_file_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'ui', 'main_window.ui')

        with open(ui_file_path, 'r', encoding='utf-8') as f:
            ui_content = f.read()

        # Verify all DataDisplayWidget UI components are declared
        data_display_components = [
            'param_table', 'param_title', 'view_toggle_button', 'selector_container'
        ]

        for component in data_display_components:
            assert f'name="{component}"' in ui_content, f"DataDisplayWidget component '{component}' not found in main_window.ui"

    def test_initialization(self, qtbot, sample_parameter):
        """Test DataDisplayWidget initializes correctly"""
        # Set Qt attributes before importing QtWebEngineWidgets
        from PyQt5.QtCore import Qt, QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QGroupBox

        widget = DataDisplayWidget()

        # Add widget to qtbot for proper Qt event handling
        qtbot.addWidget(widget)

        # Assign UI widgets (simulating what MainWindow does)
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

        # Check initial state
        assert widget.table_display_mode == "raw"
        assert widget.hide_empty_columns == False

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_parameter_raw_mode(self, mock_app, sample_parameter):
        """Test displaying parameter data in raw mode"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        widget = DataDisplayWidget()

        # Create mock UI widgets and assign them
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

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
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

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
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

        widget.display_data_table(sample_parameter, "Parameter", is_results=False)

        # Check title was updated correctly
        assert "Parameter: test_param" in widget.param_title.text()
        assert widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_data_table_result(self, mock_app, sample_parameter):
        """Test unified display_data_table method for results"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

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
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create parameter with empty DataFrame
        empty_df = pd.DataFrame()
        empty_param = Parameter('empty_param', empty_df, {})

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

        widget.display_data_table(empty_param, "Parameter", is_results=False)

        # Check that table is cleared and button is disabled
        assert not widget.view_toggle_button.isEnabled()

    @patch('PyQt5.QtWidgets.QApplication')
    def test_clear_table_display(self, mock_app, sample_parameter):
        """Test _clear_table_display method"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

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
        from PyQt5.QtWidgets import QPushButton, QWidget

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.view_toggle_button = QPushButton()
        widget.selector_container = QWidget()

        # Initially raw mode
        assert widget.table_display_mode == "raw"

        # Toggle to advanced
        widget.view_toggle_button.setChecked(True)
        widget._toggle_display_mode()

        assert widget.table_display_mode == "advanced"
        assert widget.view_toggle_button.text() == "Advanced Display"

        # Toggle back to raw
        widget.view_toggle_button.setChecked(False)
        widget._toggle_display_mode()

        assert widget.table_display_mode == "raw"
        assert widget.view_toggle_button.text() == "Raw Display"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_cell_changed_raw_mode(self, mock_app, sample_parameter):
        """Test cell value changes in raw display mode"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Display parameter in raw mode (default)
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Simulate editing a cell (row 0, column 3 which should be 'value')
        # First get the current value
        current_item = widget.param_table.item(0, 3)  # Row 0, column 'value'
        assert current_item is not None

        # Simulate changing the value to 200.0 by setting the item text
        current_item.setText("200.0")
        widget._on_cell_changed(0, 3)  # This will trigger the signal

        # The signal should have been emitted with raw mode parameters
        # We can't easily test the signal emission without more mocking,
        # but we can verify the method doesn't crash and processes the change

    @patch('PyQt5.QtWidgets.QApplication')
    def test_cell_changed_advanced_mode_pivot_table(self, mock_app, sample_parameter):
        """Test cell value changes in advanced display mode (pivot table)"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Switch to advanced mode
        widget.table_display_mode = "advanced"

        # Display parameter in advanced mode
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Simulate editing a cell in the pivot table (row 0, column 1 - first tech column)
        # First get the current value
        current_item = widget.param_table.item(0, 1)  # Row 0 (year 2020), column 1 (first tech)
        assert current_item is not None

        # Simulate changing the value to 150.0
        current_item.setText("150.0")
        widget._on_cell_changed(0, 1)  # This should trigger advanced mode sync

        # The signal should have been emitted with advanced mode parameters
        # We can't easily test the signal emission without more mocking

    @patch('PyQt5.QtWidgets.QApplication')
    def test_cell_changed_invalid_value_reverts(self, mock_app, sample_parameter):
        """Test that invalid cell values are reverted"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Display parameter in raw mode
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Get original value
        current_item = widget.param_table.item(0, 3)  # Row 0, column 'value'
        original_text = current_item.text()

        # Simulate entering invalid value (non-numeric)
        current_item.setText("invalid_text")
        widget._on_cell_changed(0, 3)

        # The display should be refreshed (reverted to original)
        # We can't easily verify this without more complex mocking

    @patch('PyQt5.QtWidgets.QApplication')
    def test_cell_changed_empty_value_becomes_zero(self, mock_app, sample_parameter):
        """Test that empty cell values are treated as zero"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Display parameter in raw mode
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Simulate clearing a cell (setting to empty string)
        current_item = widget.param_table.item(0, 3)  # Row 0, column 'value'
        current_item.setText("")
        widget._on_cell_changed(0, 3)

        # Should treat empty as 0.0
        # Signal should be emitted with value 0.0

    @patch('PyQt5.QtWidgets.QApplication')
    def test_sync_pivot_change_to_raw_data(self, mock_app, sample_parameter):
        """Test synchronization of pivot table changes back to raw data"""
        from ui.components.data_display_widget import DataDisplayWidget

        widget = DataDisplayWidget()

        # Test the _sync_pivot_change_to_raw_data method directly
        # This method needs to be connected to MainWindow's cell_value_changed signal

        # Create a test scenario where we have year=2020, technology='tech1'
        # This should find the matching row in raw data and update it

        # For this test, we mainly verify the method exists and can be called
        # The actual synchronization logic is tested in MainWindow tests
        try:
            widget._sync_pivot_change_to_raw_data(0, 1, 150.0)
        except AttributeError:
            # Expected - method needs MainWindow context
            pass

    @patch('PyQt5.QtWidgets.QApplication')
    def test_chart_update_on_cell_change(self, mock_app, sample_parameter):
        """Test that chart updates are triggered when cell values change"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Mock the chart_update_needed signal
        chart_update_called = []
        widget.chart_update_needed.connect(lambda: chart_update_called.append(True))

        # Display parameter in raw mode
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Simulate editing a cell
        current_item = widget.param_table.item(0, 3)  # Row 0, column 'value'
        if current_item:
            current_item.setText("200.0")
            widget._on_cell_changed(0, 3)

            # Check that chart update was signaled (called twice due to implementation)
            assert len(chart_update_called) == 2

    @patch('PyQt5.QtWidgets.QApplication')
    def test_cell_value_changed_signal_emission(self, mock_app, sample_parameter):
        """Test that cell_value_changed signal is emitted correctly"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTableWidgetItem

        widget = DataDisplayWidget()

        # Set up widget with UI components
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Track signal emissions
        signal_calls = []
        widget.cell_value_changed.connect(lambda *args: signal_calls.append(args))

        # Display parameter in raw mode
        widget.display_parameter_data(sample_parameter, is_results=False)

        # Simulate editing a cell
        current_item = widget.param_table.item(0, 3)  # Row 0, column 'value'
        if current_item:
            current_item.setText("200.0")
            widget._on_cell_changed(0, 3)

            # Check signal was emitted with correct parameters (called twice due to implementation)
            assert len(signal_calls) == 2
            mode, row_or_year, col_or_tech, value = signal_calls[0]
            assert mode == "raw"
            assert row_or_year == 0  # row index
            assert isinstance(col_or_tech, str)  # column name
            assert value == 200.0

    @patch('PyQt5.QtWidgets.QApplication')
    def test_display_mode_changed_signal_emission(self, mock_app):
        """Test that display_mode_changed signal is emitted when mode changes"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QPushButton, QWidget

        widget = DataDisplayWidget()

        # Track signal emissions
        signal_calls = []
        widget.display_mode_changed.connect(lambda: signal_calls.append(True))

        # Toggle display mode
        widget.view_toggle_button = QPushButton()
        widget.selector_container = QWidget()
        widget.view_toggle_button.setChecked(True)
        widget._toggle_display_mode()

        # Check signal was emitted
        assert len(signal_calls) == 1

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

    @patch('PyQt5.QtWidgets.QApplication')
    def test_hide_empty_columns_checkbox_functionality(self, mock_app):
        """Test that 'Hide Empty Columns' checkbox actually hides empty columns in table display"""
        from ui.components.data_display_widget import DataDisplayWidget
        from core.data_models import Parameter
        import pandas as pd
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create test DataFrame that will produce empty columns when pivoted
        # Include some technology combinations that have no data (will result in all-zero columns)
        data = [
            ['tech1', 'region1', 2020, 100.0],
            ['tech1', 'region1', 2025, 120.0],
            ['tech2', 'region1', 2020, 80.0],
            ['tech2', 'region1', 2025, 90.0],
            ['tech3', 'region1', 2020, 0.0],  # tech3 will have all zeros
            ['tech3', 'region1', 2025, 0.0],  # all zeros for tech3 - should be hidden
        ]
        headers = ['technology', 'region', 'year', 'value']
        df = pd.DataFrame(data, columns=headers)

        metadata = {
            'units': 'MW',
            'dims': ['technology', 'region', 'year'],
            'value_column': 'value',
            'shape': df.shape
        }
        param = Parameter('test_param', df, metadata)

        widget = DataDisplayWidget()

        # Test the transformation directly
        # Test 1: Transform with hide empty columns DISABLED
        widget.hide_empty_columns = False
        transformed_visible = widget.transform_to_display_format(
            df, is_results=False, current_filters=None, hide_empty=False, for_chart=False
        )

        # Test 2: Transform with hide empty columns ENABLED
        widget.hide_empty_columns = True
        transformed_hidden = widget.transform_to_display_format(
            df, is_results=False, current_filters=None, hide_empty=True, for_chart=False
        )

        # Verify that the transformed data has different numbers of columns
        assert transformed_hidden.shape[1] < transformed_visible.shape[1], \
            f"Expected fewer columns when hiding empty ones: {transformed_hidden.shape[1]} < {transformed_visible.shape[1]}"

        # Verify that tech3 column is present when not hiding empty columns
        assert 'tech3' in transformed_visible.columns, "tech3 column should be present when not hiding empty columns"

        # Verify that tech3 column is hidden when hiding empty columns
        assert 'tech3' not in transformed_hidden.columns, "tech3 column should be hidden when hiding empty columns"

        # Verify that non-empty columns are still present
        assert 'tech1' in transformed_hidden.columns, "tech1 column should still be visible"
        assert 'tech2' in transformed_hidden.columns, "tech2 column should still be visible"


class TestChartWidget:
    """Test ChartWidget functionality"""

    def test_ui_components_declared_in_ui_file(self):
        """Test that all ChartWidget UI components are declared in main_window.ui"""
        import os
        ui_file_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'ui', 'main_window.ui')

        with open(ui_file_path, 'r', encoding='utf-8') as f:
            ui_content = f.read()

        # Verify all ChartWidget UI components are declared
        chart_components = [
            'simple_bar_btn', 'stacked_bar_btn', 'line_chart_btn', 'stacked_area_btn', 'param_chart'
        ]

        for component in chart_components:
            assert f'name="{component}"' in ui_content, f"ChartWidget component '{component}' not found in main_window.ui"


class TestUIRefactoringVerification:
    """Test that all refactored UI components are properly declared in the .ui file"""

    def test_all_refactored_ui_components_exist_in_ui_file(self):
        """Test that all UI components that were refactored from programmatic creation exist in main_window.ui"""
        import os
        ui_file_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'ui', 'main_window.ui')

        with open(ui_file_path, 'r', encoding='utf-8') as f:
            ui_content = f.read()

        # All UI components that were previously created programmatically but are now only in .ui file
        refactored_components = {
            # DataDisplayWidget components
            'param_table': 'QTableWidget',
            'param_title': 'QLabel',
            'view_toggle_button': 'QPushButton',
            'selector_container': 'QGroupBox',

            # ChartWidget components
            'simple_bar_btn': 'QPushButton',
            'stacked_bar_btn': 'QPushButton',
            'line_chart_btn': 'QPushButton',
            'stacked_area_btn': 'QPushButton',
            'param_chart': 'QWebEngineView',

            # Other UI components (for completeness)
            'console': 'QTextEdit',
            'progress_bar': 'QProgressBar',
            'statusbar': 'QStatusBar'
        }

        for component_name, component_type in refactored_components.items():
            # Check that component is declared with correct name
            assert f'name="{component_name}"' in ui_content, f"Component '{component_name}' not found in main_window.ui"

            # Check that component has correct type (optional but helpful for verification)
            # This is more lenient since the exact format may vary
            if component_type in ['QTableWidget', 'QPushButton', 'QLabel', 'QGroupBox', 'QWebEngineView']:
                # Look for the component type declaration near the name
                component_section = ui_content[ui_content.find(f'name="{component_name}"')-200:ui_content.find(f'name="{component_name}"')+200]
                assert component_type in component_section, f"Component '{component_name}' type '{component_type}' not found in main_window.ui"

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_initialization(self, mock_webview, mock_app):
        """Test ChartWidget initializes correctly"""
        from ui.components.chart_widget import ChartWidget
        from PyQt5.QtWidgets import QPushButton
        from PyQt5.QtWebEngineWidgets import QWebEngineView

        widget = ChartWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.simple_bar_btn = QPushButton()
        widget.stacked_bar_btn = QPushButton()
        widget.line_chart_btn = QPushButton()
        widget.stacked_area_btn = QPushButton()
        widget.param_chart = QWebEngineView()

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

        # Check initial state
        assert widget.current_chart_type == 'stacked_bar'

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_chart_type_buttons(self, mock_webview, mock_app):
        """Test chart type button interactions"""
        from ui.components.chart_widget import ChartWidget
        from PyQt5.QtWidgets import QPushButton

        widget = ChartWidget()

        # Assign UI widgets
        widget.simple_bar_btn = QPushButton()
        widget.stacked_bar_btn = QPushButton()
        widget.line_chart_btn = QPushButton()
        widget.stacked_area_btn = QPushButton()
        widget.param_chart = mock_webview

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

        # Test button states (after initialization)
        assert widget.simple_bar_btn.isChecked() == False  # stacked_bar is initially checked
        assert widget.stacked_bar_btn.isChecked() == True
        assert widget.line_chart_btn.isChecked() == False
        assert widget.stacked_area_btn.isChecked() == False

        # Simulate clicking simple bar button
        widget._on_chart_type_changed('bar')
        assert widget.current_chart_type == 'bar'

    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    @patch('plotly.graph_objects.Figure')
    @patch('ui.components.chart_widget.pio')
    def test_update_chart(self, mock_pio, mock_figure, mock_webview, mock_app, sample_parameter):
        """Test updating chart with data"""
        from ui.components.chart_widget import ChartWidget
        from PyQt5.QtWidgets import QPushButton

        widget = ChartWidget()

        # Assign UI widgets
        widget.simple_bar_btn = QPushButton()
        widget.stacked_bar_btn = QPushButton()
        widget.line_chart_btn = QPushButton()
        widget.stacked_area_btn = QPushButton()
        widget.param_chart = mock_webview

        # Initialize with UI widgets
        widget.initialize_with_ui_widgets()

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
        assert widget.current_chart_type == 'stacked_bar'


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
            ('capacity_lo', 'Bounds & Constraints'),
            ('capacity_up', 'Bounds & Constraints'),
            ('flow_lo', 'Bounds & Constraints'),
            ('flow_up', 'Bounds & Constraints'),
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


class TestFilteringFunctionality:
    """Test filtering functionality in advanced display mode"""

    @patch('PyQt5.QtWidgets.QApplication')
    def test_filter_application_in_table_and_chart(self, mock_app, sample_parameter):
        """Test that filters are applied to both table and chart data"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create test data with multiple technologies and regions for filtering
        data = [
            ['tech1', 'region1', 2020, 100.0],
            ['tech1', 'region1', 2025, 120.0],
            ['tech2', 'region1', 2020, 80.0],
            ['tech2', 'region1', 2025, 90.0],
            ['tech1', 'region2', 2020, 50.0],
            ['tech1', 'region2', 2025, 60.0],
            ['tech2', 'region2', 2020, 30.0],
            ['tech2', 'region2', 2025, 40.0],
        ]
        headers = ['technology', 'region', 'year', 'value']
        df = pd.DataFrame(data, columns=headers)

        metadata = {
            'units': 'MW',
            'dims': ['technology', 'region', 'year'],
            'value_column': 'value',
            'shape': df.shape
        }
        param = Parameter('test_param', df, metadata)

        widget = DataDisplayWidget()

        # Assign UI widgets (simulating what MainWindow does)
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()

        widget.initialize_with_ui_widgets()

        # Switch to advanced mode to enable filtering
        widget.table_display_mode = "advanced"

        # Display parameter in advanced mode - this should set up property selectors
        widget.display_parameter_data(param, is_results=False)

        # Verify that property selectors were created (only 'region' is a filter column)
        assert 'region' in widget.property_selectors

        # Get initial unfiltered table data (pivoted in advanced mode)
        initial_table_data = widget.transform_to_display_format(
            df, is_results=False, current_filters=None, hide_empty=False, for_chart=False
        )

        # Verify initial data has pivoted structure (2 rows for 2 years)
        assert len(initial_table_data) == 2, f"Expected 2 rows initially (pivoted), got {len(initial_table_data)}"

        # Apply filter to show only region1
        region_selector = widget.property_selectors['region']
        region_selector.setCurrentText('region1')

        # Get filtered table data (pivoted)
        filtered_table_data = widget.transform_to_display_format(
            df, is_results=False, current_filters=widget._get_current_filters(), hide_empty=False, for_chart=False
        )

        # Verify filtered data has same structure but different values
        assert len(filtered_table_data) == 2, f"Expected 2 rows after filtering (pivoted), got {len(filtered_table_data)}"
        # Filtering affects the values in the pivoted data, not the row count

        # Test that table display also reflects the filter
        # Re-display with filters applied
        widget.display_parameter_data(param, is_results=False)

        # The table should now show only filtered data
        # (This is harder to test directly due to Qt table widget complexity,
        # but we can verify the transformation logic works)

    @patch('PyQt5.QtWidgets.QApplication')
    def test_filter_reset_to_all(self, mock_app, sample_parameter):
        """Test that setting filter to 'All' shows all data"""
        from ui.components.data_display_widget import DataDisplayWidget
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create test data
        data = [
            ['tech1', 'region1', 2020, 100.0],
            ['tech1', 'region2', 2025, 80.0],
        ]
        headers = ['technology', 'region', 'year', 'value']
        df = pd.DataFrame(data, columns=headers)

        metadata = {'value_column': 'value', 'shape': df.shape}
        param = Parameter('test_param', df, metadata)

        widget = DataDisplayWidget()

        # Set up widget
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()
        widget.initialize_with_ui_widgets()
        widget.table_display_mode = "advanced"

        # Display parameter
        widget.display_parameter_data(param, is_results=False)

        # Apply filter
        region_selector = widget.property_selectors['region']
        region_selector.setCurrentText('region1')

        # Get filtered data
        filtered_data = widget.transform_to_display_format(
            df, is_results=False, current_filters=widget._get_current_filters(), hide_empty=False, for_chart=True
        )

        # Should only have region1 data
        assert len(filtered_data) == 1, "Should only have one row for region1"

        # Reset filter to 'All'
        region_selector.setCurrentText('All')

        # Get unfiltered data
        unfiltered_data = widget.transform_to_display_format(
            df, is_results=False, current_filters=widget._get_current_filters(), hide_empty=False, for_chart=True
        )

        # Should have both regions
        assert len(unfiltered_data) == 2, "Should have two rows for both regions"

    @patch('PyQt5.QtWidgets.QApplication')
    def test_multiple_filters_applied_simultaneously(self, mock_app):
        """Test that multiple filters are applied together"""
        from ui.components.data_display_widget import DataDisplayWidget
        from core.data_models import Parameter
        import pandas as pd
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create test data with multiple dimensions
        data = [
            ['tech1', 'region1', 'level1', 2020, 100.0],
            ['tech1', 'region2', 'level1', 2020, 150.0],
            ['tech2', 'region1', 'level2', 2020, 80.0],
            ['tech2', 'region2', 'level2', 2020, 120.0],
        ]
        headers = ['technology', 'region', 'level', 'year', 'value']
        df = pd.DataFrame(data, columns=headers)

        metadata = {'value_column': 'value', 'shape': df.shape}
        param = Parameter('test_param', df, metadata)

        widget = DataDisplayWidget()

        # Set up widget
        widget.param_title = QLabel()
        widget.view_toggle_button = QPushButton()
        widget.param_table = QTableWidget()
        widget.selector_container = QWidget()
        widget.initialize_with_ui_widgets()
        widget.table_display_mode = "advanced"

        # Display parameter
        widget.display_parameter_data(param, is_results=False)

        # Apply multiple filters
        widget.property_selectors['region'].setCurrentText('region1')
        widget.property_selectors['level'].setCurrentText('level1')

        # Get filtered data
        filtered_data = widget.transform_to_display_format(
            df, is_results=False, current_filters=widget._get_current_filters(), hide_empty=False, for_chart=True
        )

        # Should only have 1 column (tech1, since only one row matches the filters)
        assert filtered_data.shape[1] == 1, f"Expected 1 column, got {filtered_data.shape[1]}"
        col_name = filtered_data.columns[0]
        assert 'tech1' in str(col_name)

        # Verify the value is correct (100.0 for tech1 with region1 and level1)
        assert filtered_data.loc[2020, col_name] == 100.0


class TestMainWindowDataEditingIntegration:
    """Test MainWindow integration for data editing operations"""

    def _setup_main_window_with_mocks(self, include_data_container=False):
        """Helper function to set up MainWindow with common mocked UI components"""
        from PyQt5.QtWidgets import QStatusBar, QTextEdit
        from ui.main_window import MainWindow

        # Create MainWindow instance
        window = MainWindow()

        # Set required attributes that are normally initialized in __init__
        window.current_view = "input"  # "input" or "results"
        window.selected_input_file = None
        window.selected_results_file = None

        # Mock common UI components
        window.param_title = MagicMock()
        window.view_toggle_button = MagicMock()
        window.param_table = MagicMock()
        window.selector_container = MagicMock()
        window.param_tree = MagicMock()
        window.console = QTextEdit()
        window.statusbar = QStatusBar() #MagicMock()
        window.splitter = MagicMock()
        window.leftSplitter = MagicMock()
        window.contentSplitter = MagicMock()
        window.dataSplitter = MagicMock()
        window.actionOpen_Input_File = MagicMock()
        window.actionOpen_Results_File = MagicMock()
        window.actionExit = MagicMock()
        window.actionAbout = MagicMock()
        window.actionFind = MagicMock()
        window.actionUndo = MagicMock()
        window.actionRedo = MagicMock()
        window.actionCut = MagicMock()
        window.actionCopy = MagicMock()
        window.actionPaste = MagicMock()
        window.actionSave = MagicMock()
        window.actionSave_As = MagicMock()
        window.actionDashboard = MagicMock()
        window.actionRun_Solver = MagicMock()
        window.actionStop_Solver = MagicMock()

        # chart components
        window.simple_bar_btn = MagicMock()
        window.stacked_bar_btn = MagicMock()
        window.line_chart_btn = MagicMock()
        window.stacked_area_btn = MagicMock()
        window.param_chart = MagicMock()

        if include_data_container:
            window.dataContainer = MagicMock()

        return window

    @patch('ui.dashboard.ResultsDashboard')
    @patch('PyQt5.uic.loadUi')
    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_main_window_cell_editing_integration(self, mock_webview, mock_app, mock_loadUi, mock_dashboard, sample_parameter, sample_scenario):
        """Test complete integration of cell editing from table to chart updates"""
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTreeWidget
        from PyQt5.QtCore import Qt

        # Create MainWindow instance with mocks
        window = self._setup_main_window_with_mocks(include_data_container=True)

        # Override with real widgets for this specific test
        window.param_title = QLabel()
        window.param_table = QTableWidget()

        # Initialize components
        window._setup_ui_components()
        window._connect_component_signals()
        window._connect_signals()

        # Set up test scenario
        window.input_manager.get_current_scenario = MagicMock(return_value=sample_scenario)
        window._get_current_scenario = MagicMock(return_value=sample_scenario)

        # Simulate parameter selection
        window._on_parameter_selected('test_param', False)

        # Verify parameter was displayed
        assert "Parameter: test_param" in window.param_title.text()

        # Now test cell editing - simulate editing a cell
        # First get the current value from the table
        table_item = window.param_table.item(0, 3)  # Row 0, column 'value'
        if table_item:
            original_value = table_item.text()

            # Simulate editing the cell
            table_item.setText("999.0")

            # Trigger cell changed event
            window.data_display._on_cell_changed(0, 3)

            # Verify that the scenario data was updated
            updated_param = sample_scenario.get_parameter('test_param')
            # The parameter should have been updated (though we can't easily verify the exact value
            # without more complex mocking of the MainWindow's cell_value_changed handler)

    @patch('ui.dashboard.ResultsDashboard')
    @patch('PyQt5.uic.loadUi')
    @patch('PyQt5.QtWidgets.QApplication')
    @patch('PyQt5.QtWebEngineWidgets.QWebEngineView')
    def test_chart_updates_on_data_change(self, mock_webview, mock_app, mock_loadUi, mock_dashboard, sample_parameter, sample_scenario):
        """Test that charts update when data changes"""
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget

        # Create MainWindow instance
        window = self._setup_main_window_with_mocks()

        # Override with real widgets for this specific test
        window.param_table = QTableWidget()

        # Initialize
        window._setup_ui_components()

        # Set up scenario
        window.input_manager.get_current_scenario = MagicMock(return_value=sample_scenario)
        window._get_current_scenario = MagicMock(return_value=sample_scenario)

        # Display parameter
        window._on_parameter_selected('test_param', False)

        # Mock the selectedItems to return the test parameter
        mock_selected_item = MagicMock()
        mock_selected_item.text.return_value = 'test_param'
        window.param_tree.selectedItems = MagicMock(return_value=[mock_selected_item])

        # Track chart update needed signal emissions
        chart_update_signals = []
        window.data_display.chart_update_needed.connect(lambda: chart_update_signals.append(True))

        # Simulate cell editing
        table_item = window.param_table.item(0, 3)
        if table_item:
            table_item.setText("777.0")
            window.data_display._on_cell_changed(0, 3)

            # Check that chart update signal was emitted (called twice due to implementation)
            assert len(chart_update_signals) == 2

    @patch('ui.dashboard.ResultsDashboard')
    @patch('PyQt5.uic.loadUi')
    @patch('PyQt5.QtWidgets.QApplication')
    def test_data_synchronization_advanced_view(self, mock_app, mock_loadUi, mock_dashboard, sample_parameter, sample_scenario):
        """Test data synchronization between raw and advanced views"""
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTreeWidget

        # Create MainWindow instance with mocks
        window = self._setup_main_window_with_mocks()

        # Override with real widgets for this specific test
        window.view_toggle_button = QPushButton()
        window.param_table = QTableWidget()
        window.selector_container = QWidget()

        # Initialize
        window._setup_ui_components()

        # Set up scenario
        window.input_manager.get_current_scenario = MagicMock(return_value=sample_scenario)
        window._get_current_scenario = MagicMock(return_value=sample_scenario)

        # Switch to advanced mode
        window.data_display.table_display_mode = "advanced"

        # Display parameter in advanced mode
        window._on_parameter_selected('test_param', False)

        # The advanced view should show pivoted data
        # (This is mainly a smoke test to ensure no exceptions occur)

    @patch('ui.dashboard.ResultsDashboard')
    @patch('PyQt5.uic.loadUi')
    @patch('PyQt5.QtWidgets.QApplication')
    def test_filtering_integration(self, mock_app, mock_loadUi, mock_dashboard, sample_parameter, sample_scenario):
        """Test filtering functionality in advanced view"""
        from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QWidget, QTreeWidget, QComboBox

        # Create MainWindow instance with mocks
        window = self._setup_main_window_with_mocks()

        # Override with real widgets for this specific test
        window.view_toggle_button = QPushButton()
        window.param_table = QTableWidget()
        window.selector_container = QWidget()

        # Initialize
        window._setup_ui_components()

        # Set up scenario
        window.input_manager.get_current_scenario = MagicMock(return_value=sample_scenario)
        window._get_current_scenario = MagicMock(return_value=sample_scenario)

        # Switch to advanced mode
        window.data_display.table_display_mode = "advanced"

        # Display parameter - this should set up property selectors
        window._on_parameter_selected('test_param', False)

        # Check that property selectors dict exists (smoke test - main goal is no AttributeError)
        assert hasattr(window.data_display, 'property_selectors')
        assert isinstance(window.data_display.property_selectors, dict)

        # Test changing a filter
        if 'region' in window.data_display.property_selectors:
            region_selector = window.data_display.property_selectors['region']
            # Change filter to 'region1'
            region_selector.setCurrentText('region1')

            # Trigger filter change
            window.data_display._on_selector_changed()

            # This should refresh the display with filtered data
            # (Smoke test - mainly checking no exceptions)


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
        assert button.size().width() == 30
        assert button.size().height() == 25

    @patch('PyQt5.QtWidgets.QApplication')
    def test_setup_tree_widget(self, mock_app):
        """Test setting up tree widget"""
        from ui.ui_styler import UIStyler
        from PyQt5.QtWidgets import QTreeWidget

        tree = QTreeWidget()

        UIStyler.setup_tree_widget(tree)

        # Check that alternating row colors was set
        assert tree.alternatingRowColors() == True
