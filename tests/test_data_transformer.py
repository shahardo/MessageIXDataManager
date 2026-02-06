"""
Tests for DataTransformer utility class
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from core.data_models import Parameter, ScenarioData
from utils.data_transformer import DataTransformer


class TestDataTransformer:
    """Test cases for DataTransformer class"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create sample input parameter data (raw format)
        self.input_data = pd.DataFrame({
            'region': ['Region1', 'Region1', 'Region2', 'Region2'],
            'technology': ['Tech1', 'Tech2', 'Tech1', 'Tech2'],
            'year': [2020, 2020, 2025, 2025],
            'value': [100.0, 200.0, 150.0, 250.0]
        })

        # Create sample results data (already pivoted format)
        self.results_data = pd.DataFrame({
            'technology': ['Tech1', 'Tech2'],
            'variable': ['var1', 'var2']
        }, index=[2020, 2025])

        # Create mock parameter objects
        self.input_param = Mock(spec=Parameter)
        self.input_param.df = self.input_data
        self.input_param.name = "test_input_param"

        self.results_param = Mock(spec=Parameter)
        self.results_param.df = self.results_data
        self.results_param.name = "test_results_param"

    def test_prepare_chart_data_input_parameter(self):
        """Test preparing chart data for input parameters"""
        scenario_options = {
            'YearsLimitEnabled': True,
            'MinYear': 2020,
            'MaxYear': 2030
        }

        result = DataTransformer.prepare_chart_data(
            self.input_param,
            is_results=False,
            scenario_options=scenario_options
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        # After pivoting, year should be index, technologies should be columns
        assert result.index.name == 'year'
        assert 'Tech1' in result.columns
        assert 'Tech2' in result.columns

    def test_prepare_chart_data_results_parameter(self):
        """Test preparing chart data for results parameters"""
        scenario_options = {
            'YearsLimitEnabled': True,
            'MinYear': 2020,
            'MaxYear': 2030
        }

        result = DataTransformer.prepare_chart_data(
            self.results_param,
            is_results=True,
            scenario_options=scenario_options
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)

    def test_prepare_chart_data_empty_parameter(self):
        """Test preparing chart data for empty parameter"""
        empty_param = Mock(spec=Parameter)
        empty_param.df = pd.DataFrame()
        empty_param.name = "empty_param"

        result = DataTransformer.prepare_chart_data(empty_param)
        assert result is None

    def test_prepare_chart_data_none_parameter(self):
        """Test preparing chart data for None parameter"""
        result = DataTransformer.prepare_chart_data(None)  # type: ignore
        assert result is None

    def test_apply_year_filtering_with_year_column(self):
        """Test year filtering on DataFrame with year column"""
        df = pd.DataFrame({
            'year': [2015, 2020, 2025, 2030],
            'value': [10, 20, 30, 40]
        })

        scenario_options = {
            'YearsLimitEnabled': True,
            'MinYear': 2020,
            'MaxYear': 2025
        }

        result = DataTransformer.apply_year_filtering(df, scenario_options)

        assert len(result) == 2
        assert result['year'].tolist() == [2020, 2025]
        assert result['value'].tolist() == [20, 30]

    def test_apply_year_filtering_with_year_index(self):
        """Test year filtering on DataFrame with year as index"""
        df = pd.DataFrame({
            'value': [10, 20, 30, 40]
        }, index=[2015, 2020, 2025, 2030])
        df.index.name = 'year'

        scenario_options = {
            'YearsLimitEnabled': True,
            'MinYear': 2020,
            'MaxYear': 2025
        }

        result = DataTransformer.apply_year_filtering(df, scenario_options)

        assert len(result) == 2
        assert result.index.tolist() == [2020, 2025]
        assert result['value'].tolist() == [20, 30]

    def test_apply_year_filtering_disabled(self):
        """Test year filtering when disabled"""
        df = pd.DataFrame({
            'year': [2015, 2020, 2025, 2030],
            'value': [10, 20, 30, 40]
        })

        scenario_options = {
            'YearsLimitEnabled': False,
            'MinYear': 2020,
            'MaxYear': 2025
        }

        result = DataTransformer.apply_year_filtering(df, scenario_options)

        assert len(result) == 4  # No filtering applied
        assert result['year'].tolist() == [2015, 2020, 2025, 2030]

    def test_apply_year_filtering_empty_dataframe(self):
        """Test year filtering on empty DataFrame"""
        df = pd.DataFrame()
        scenario_options = {'YearsLimitEnabled': True, 'MinYear': 2020, 'MaxYear': 2030}

        result = DataTransformer.apply_year_filtering(df, scenario_options)
        assert result.empty

    def test_transform_for_display_raw_mode_input(self):
        """Test transforming to raw display mode for input data"""
        result = DataTransformer.transform_for_display(
            self.input_data,
            is_results=False,
            display_mode="raw"
        )

        # Raw mode should return data as-is
        pd.testing.assert_frame_equal(result, self.input_data)

    def test_transform_for_display_advanced_mode_input(self):
        """Test transforming to advanced display mode for input data"""
        result = DataTransformer.transform_for_display(
            self.input_data,
            is_results=False,
            display_mode="advanced"
        )

        # Should be pivoted with year as index
        assert result.index.name == 'year'
        assert 'Tech1' in result.columns
        assert 'Tech2' in result.columns

    def test_transform_for_display_results_data(self):
        """Test transforming results data"""
        result = DataTransformer.transform_for_display(
            self.results_data,
            is_results=True,
            display_mode="advanced"
        )

        # Results should be prepared for 2D display
        assert isinstance(result, pd.DataFrame)

    def test_identify_columns_input_data(self):
        """Test column identification for input data"""
        result = DataTransformer._identify_columns(self.input_data)

        year_cols = result['year_cols']
        pivot_cols = result['pivot_cols']
        value_col = result['value_col']
        filter_cols = result['filter_cols']

        assert isinstance(year_cols, list) and 'year' in year_cols
        assert isinstance(pivot_cols, list) and 'technology' in pivot_cols
        assert value_col == 'value'
        assert isinstance(filter_cols, list) and 'region' in filter_cols

    def test_apply_filters(self):
        """Test filter application"""
        df = pd.DataFrame({
            'region': ['A', 'A', 'B', 'B'],
            'value': [1, 2, 3, 4]
        })

        filters = {'region': 'A'}
        result = DataTransformer._apply_filters(df, filters)

        assert len(result) == 2
        assert all(result['region'] == 'A')

    def test_perform_pivot(self):
        """Test pivot operation"""
        column_info = {
            'year_cols': ['year'],
            'pivot_cols': ['technology'],
            'value_col': 'value'
        }

        result = DataTransformer._perform_pivot(self.input_data, column_info)

        assert result.index.name == 'year'
        assert 'Tech1' in result.columns
        assert 'Tech2' in result.columns

    def test_hide_empty_columns(self):
        """Test hiding empty columns"""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [0, 0, 0],  # All zeros
            'col3': [None, None, None],  # All NaN
            'col4': ['a', 'b', 'c']  # Non-empty
        })

        result = DataTransformer._hide_empty_columns(df, is_results=False)

        assert 'col1' in result.columns
        assert 'col4' in result.columns
        assert 'col2' not in result.columns  # Should be hidden
        assert 'col3' not in result.columns  # Should be hidden

    def test_identify_columns_postprocessed_data(self):
        """Test column identification for postprocessed results with 'category' column"""
        # Postprocessed data has year, category, value columns
        df = pd.DataFrame({
            'year': [2020, 2020, 2030, 2030],
            'category': ['coal', 'solar', 'coal', 'solar'],
            'value': [100, 50, 80, 120]
        })

        result = DataTransformer._identify_columns(df, is_results=True)

        year_cols = result['year_cols']
        pivot_cols = result['pivot_cols']
        value_col = result['value_col']

        # 'category' should be in pivot_cols so it becomes the column headers
        assert 'year' in year_cols
        assert 'category' in pivot_cols
        assert value_col == 'value'

    def test_pivot_postprocessed_data(self):
        """Test pivoting postprocessed data with category column"""
        df = pd.DataFrame({
            'year': [2020, 2020, 2030, 2030],
            'category': ['coal', 'solar', 'coal', 'solar'],
            'value': [100, 50, 80, 120]
        })

        column_info = {
            'year_cols': ['year'],
            'pivot_cols': ['category'],
            'value_col': 'value'
        }

        result = DataTransformer._perform_pivot(df, column_info)

        # Should have year as index and categories as columns
        assert result.index.name == 'year'
        assert 'coal' in result.columns
        assert 'solar' in result.columns
        assert result.loc[2020, 'coal'] == 100
        assert result.loc[2030, 'solar'] == 120

    def test_transform_error_handling(self):
        """Test error handling in transform methods"""
        # Test with invalid data that might cause errors
        invalid_df = pd.DataFrame({
            'invalid_col': [1, 2, 3]
        })

        result = DataTransformer.transform_for_display(invalid_df)
        # Should return original DataFrame as fallback
        pd.testing.assert_frame_equal(result, invalid_df)
