"""
Tests for the advanced view transformation and pivot functionality
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def sample_widget():
    """Create a DataDisplayWidget instance with mocked Qt"""
    from ui.components.data_display_widget import DataDisplayWidget

    # Create widget without calling __init__ to avoid Qt operations
    widget = DataDisplayWidget.__new__(DataDisplayWidget)

    # Mock the methods and attributes that the tests use
    widget.table_display_mode = "raw"
    widget.hide_empty_columns = False
    widget.property_selectors = {}
    widget.hide_empty_checkbox = None

    # Bind methods to the instance
    widget._identify_columns = DataDisplayWidget._identify_columns.__get__(widget, DataDisplayWidget)
    widget._apply_filters = DataDisplayWidget._apply_filters.__get__(widget, DataDisplayWidget)
    widget._should_pivot = DataDisplayWidget._should_pivot.__get__(widget, DataDisplayWidget)
    widget._perform_pivot = DataDisplayWidget._perform_pivot.__get__(widget, DataDisplayWidget)
    widget._hide_empty_columns = DataDisplayWidget._hide_empty_columns.__get__(widget, DataDisplayWidget)
    widget._transform_to_advanced_view = DataDisplayWidget._transform_to_advanced_view.__get__(widget, DataDisplayWidget)
    widget.transform_to_display_format = DataDisplayWidget.transform_to_display_format.__get__(widget, DataDisplayWidget)
    widget._configure_table = DataDisplayWidget._configure_table.__get__(widget, DataDisplayWidget)

    # Mock table widget with required methods
    mock_table = type('MockTable', (), {
        'setRowCount': lambda *args: None,
        'setColumnCount': lambda *args: None,
        'setVerticalHeaderLabels': lambda *args: None,
        'setHorizontalHeaderLabels': lambda *args: None,
    })()
    widget.param_table = mock_table

    return widget


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing"""
    data = [
        ['tech1', 'region1', 2020, 100.0],
        ['tech1', 'region1', 2025, 120.0],
        ['tech2', 'region1', 2020, 80.0],
        ['tech2', 'region1', 2025, 90.0],
    ]
    return pd.DataFrame(data, columns=['technology', 'region', 'year', 'value'])


@pytest.fixture
def complex_dataframe():
    """Create a more complex DataFrame with all column types"""
    test_data = [
        ['commodity1', 'region1', 'level1', 2020, 100.0, 'some_unit', 'time_val'],
        ['commodity1', 'region1', 'level1', 2025, 120.0, 'some_unit', 'time_val'],
        ['commodity2', 'region1', 'level1', 2020, 80.0, 'some_unit', 'time_val'],
        ['commodity2', 'region1', 'level1', 2025, 90.0, 'some_unit', 'time_val'],
        ['commodity1', 'region2', 'level1', 2020, 110.0, 'some_unit', 'time_val'],
        ['commodity1', 'region2', 'level1', 2025, 130.0, 'some_unit', 'time_val'],
    ]
    return pd.DataFrame(test_data, columns=['commodity', 'region', 'level', 'year', 'value', 'unit', 'time'])


class TestTransformToAdvancedView:
    """Test the advanced view transformation functionality"""

    def test_advanced_view_results_year_handling(self, sample_widget):
        """Test that in advanced view for results, year column is hidden and years are used as row indices"""
        # Create test data similar to results data with year column
        results_data = [
            ['region1', 'tech1', 2020, 100.0],
            ['region1', 'tech1', 2025, 120.0],
            ['region1', 'tech2', 2020, 80.0],
            ['region1', 'tech2', 2025, 90.0],
        ]
        results_df = pd.DataFrame(results_data, columns=['region', 'technology', 'year', 'value'])

        # Transform to advanced view as results (is_results=True)
        transformed_df = sample_widget._transform_to_advanced_view(results_df, is_results=True)

        # For results in advanced view, year should be the index (row labels)
        # and year column should not be visible in columns
        assert 'year' not in transformed_df.columns, "Year column should be hidden in advanced view for results"
        assert transformed_df.index.name == 'year' or 'year' in str(transformed_df.index.name), "Year should be used as index"

        # The index values should be the actual year values
        expected_years = [2020, 2025]
        actual_years = sorted(transformed_df.index.unique())
        assert actual_years == expected_years, f"Expected index {expected_years}, got {actual_years}"

    def test_advanced_view_results_table_configuration(self, sample_widget):
        """Test that table is configured correctly for results in advanced view"""
        from unittest.mock import patch

        # Create test data
        results_data = [
            ['region1', 'tech1', 2020, 100.0],
            ['region1', 'tech1', 2025, 120.0],
        ]
        results_df = pd.DataFrame(results_data, columns=['region', 'technology', 'year', 'value'])

        # Transform using the same logic as the chart (what the table now uses)
        transformed_df = sample_widget.transform_to_display_format(
            results_df,
            is_results=True,
            current_filters=None,
            hide_empty=False,
            for_chart=True
        )

        # Mock the table methods to capture calls
        with patch.object(sample_widget.param_table, 'setRowCount') as mock_set_row_count, \
             patch.object(sample_widget.param_table, 'setColumnCount') as mock_set_column_count, \
             patch.object(sample_widget.param_table, 'setVerticalHeaderLabels') as mock_set_vertical_headers, \
             patch.object(sample_widget.param_table, 'setHorizontalHeaderLabels') as mock_set_horizontal_headers:

            # Set to advanced mode
            sample_widget.table_display_mode = "advanced"

            # Configure table with the transformed data
            sample_widget._configure_table(transformed_df, is_results=True)

            # Verify that vertical headers are set to years
            mock_set_vertical_headers.assert_called_with(['2020', '2025'])  # Years as row labels
            mock_set_horizontal_headers.assert_called_with(['region', 'technology', 'value'])  # Year column hidden

    def test_identify_columns_basic(self, sample_widget, sample_dataframe):
        """Test basic column identification"""
        column_info = sample_widget._identify_columns(sample_dataframe)

        assert column_info['value_col'] == 'value'
        assert 'year' in column_info['year_cols']
        assert len(column_info['filter_cols']) > 0

    def test_apply_filters(self, sample_widget, sample_dataframe):
        """Test filter application"""
        column_info = sample_widget._identify_columns(sample_dataframe)
        filters = {'technology': 'tech1'}

        filtered_df = sample_widget._apply_filters(sample_dataframe, filters, column_info)

        assert len(filtered_df) == 2
        assert all(filtered_df['technology'] == 'tech1')

    def test_should_pivot(self, sample_widget, sample_dataframe):
        """Test pivot decision logic"""
        column_info = sample_widget._identify_columns(sample_dataframe)
        should_pivot = sample_widget._should_pivot(sample_dataframe, column_info)

        assert should_pivot is True

    def test_perform_pivot(self, sample_widget, sample_dataframe):
        """Test pivot operation"""
        column_info = sample_widget._identify_columns(sample_dataframe)
        pivoted = sample_widget._perform_pivot(sample_dataframe, column_info)

        assert not pivoted.empty
        assert len(pivoted.columns) >= 2
        assert len(pivoted.index) > 0

    def test_hide_empty_columns(self, sample_widget):
        """Test hiding empty columns"""
        test_df = pd.DataFrame({
            'year': [2020, 2025],
            'technology': ['tech1', 'tech2'],
            'value': [100, 200],
            'empty_col': [0, 0],
            'empty_text': [None, None]
        })

        hidden = sample_widget._hide_empty_columns(test_df, is_results=False)

        assert 'empty_col' not in hidden.columns
        assert 'empty_text' not in hidden.columns
        assert 'year' in hidden.columns
        assert 'technology' in hidden.columns
        assert 'value' in hidden.columns

    def test_full_transform_to_advanced_view(self, sample_widget, sample_dataframe):
        """Test the complete transformation pipeline"""
        result = sample_widget._transform_to_advanced_view(
            sample_dataframe,
            current_filters={'technology': 'tech1'},
            is_results=False
        )

        assert not result.empty

    def test_column_classification_complex(self, sample_widget, complex_dataframe):
        """Test refined column classification with complex data"""
        column_info = sample_widget._identify_columns(complex_dataframe)

        pivot_cols = column_info.get('pivot_cols', [])
        filter_cols = column_info.get('filter_cols', [])
        year_cols = column_info.get('year_cols', [])
        ignored_cols = column_info.get('ignored_cols', [])
        value_col = column_info.get('value_col')

        # Verify column classifications
        assert pivot_cols and 'commodity' in pivot_cols
        assert filter_cols and 'region' in filter_cols
        assert filter_cols and 'level' in filter_cols
        assert year_cols and 'year' in year_cols
        assert value_col == 'value'
        assert ignored_cols and 'unit' in ignored_cols
        assert ignored_cols and 'time' in ignored_cols

    def test_pivot_with_complex_data(self, sample_widget, complex_dataframe):
        """Test pivot operation with complex column classification"""
        column_info = sample_widget._identify_columns(complex_dataframe)

        # Verify pivot decision
        should_pivot = sample_widget._should_pivot(complex_dataframe, column_info)
        assert should_pivot is True

        # Test actual pivot
        pivoted = sample_widget._perform_pivot(complex_dataframe, column_info)

        assert not pivoted.empty
        assert len(pivoted.index) > 0  # Should have years as rows
        assert len(pivoted.columns) > 0  # Should have commodities as columns

        # Check that commodity values became column headers
        column_headers = [str(col) for col in pivoted.columns]
        assert any('commodity1' in header for header in column_headers)
        assert any('commodity2' in header for header in column_headers)

    def test_filtering_with_complex_data(self, sample_widget, complex_dataframe):
        """Test filtering with complex data"""
        column_info = sample_widget._identify_columns(complex_dataframe)
        filters = {'region': 'region1'}

        filtered = sample_widget._apply_filters(complex_dataframe, filters, column_info)

        assert len(filtered) == 4  # Should have 4 rows for region1
        assert all(filtered['region'] == 'region1')

    def test_full_pipeline_complex_data(self, sample_widget, complex_dataframe):
        """Test complete transformation pipeline with complex data"""
        filters = {'region': 'region1'}

        full_result = sample_widget._transform_to_advanced_view(
            complex_dataframe,
            filters,
            is_results=False
        )

        assert not full_result.empty
        assert isinstance(full_result.index, pd.Index)
