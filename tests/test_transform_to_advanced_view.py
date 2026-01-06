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
    with patch('PyQt5.QtWidgets.QApplication'):
        from ui.components.data_display_widget import DataDisplayWidget
        return DataDisplayWidget()


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
