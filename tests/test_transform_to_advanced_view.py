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
    widget.years_limit_checkbox = None
    widget.options_button = None
    widget.decipher_names = False
    widget._code_display_names = {}
    widget.tech_descriptions = {}
    # Create a YearPreferences before using property accessors
    from core.user_preferences import UserPreferences
    widget.user_prefs = UserPreferences(min_year=2020, max_year=2050, limit_enabled=False)

    # Bind methods to the instance
    widget._identify_columns = DataDisplayWidget._identify_columns.__get__(widget, DataDisplayWidget)
    widget._apply_filters = DataDisplayWidget._apply_filters.__get__(widget, DataDisplayWidget)
    widget._should_pivot = DataDisplayWidget._should_pivot.__get__(widget, DataDisplayWidget)
    widget._perform_pivot = DataDisplayWidget._perform_pivot.__get__(widget, DataDisplayWidget)
    widget._hide_empty_columns = DataDisplayWidget._hide_empty_columns.__get__(widget, DataDisplayWidget)
    widget._transform_to_advanced_view = DataDisplayWidget._transform_to_advanced_view.__get__(widget, DataDisplayWidget)
    widget.transform_to_display_format = DataDisplayWidget.transform_to_display_format.__get__(widget, DataDisplayWidget)
    widget._configure_table = DataDisplayWidget._configure_table.__get__(widget, DataDisplayWidget)
    widget._apply_year_filtering = DataDisplayWidget._apply_year_filtering.__get__(widget, DataDisplayWidget)

    # Mock table widget with required methods
    mock_table = type('MockTable', (), {
        'setRowCount': lambda *args: None,
        'setColumnCount': lambda *args: None,
        'setVerticalHeaderLabels': lambda *args: None,
        'setHorizontalHeaderLabels': lambda *args: None,
        'setHorizontalHeaderItem': lambda *args: None,
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
             patch.object(sample_widget.param_table, 'setHorizontalHeaderItem'):

            # Set to advanced mode
            sample_widget.table_display_mode = "advanced"

            # Configure table with the transformed data
            sample_widget._configure_table(transformed_df)

            # Verify that vertical headers are set to years
            mock_set_vertical_headers.assert_called_with(['2020', '2025'])  # Years as row labels

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


class TestIdentifyColumnsSchema:
    """Verify _identify_columns covers all MESSAGE_IX_PARAMETERS dimensions."""

    def test_all_messageix_dims_classified(self, sample_widget):
        """Every dimension from MESSAGE_IX_PARAMETERS must be classified."""
        from core.message_ix_schema import MESSAGE_IX_PARAMETERS

        # Collect all unique dimension names across all parameters
        all_dims = set()
        for pdef in MESSAGE_IX_PARAMETERS.values():
            all_dims.update(pdef.get("dims", []))

        # Build a dummy DataFrame with all dims + 'value'
        cols = sorted(all_dims) + ["value"]
        df = pd.DataFrame([["x"] * len(cols)], columns=cols)

        info = sample_widget._identify_columns(df, is_results=False)
        classified = set(
            info["year_cols"]
            + info["pivot_cols"]
            + info["filter_cols"]
            + info["ignored_cols"]
        )
        if info["value_col"]:
            classified.add(info["value_col"])

        unclassified = set(cols) - classified
        assert not unclassified, f"Unclassified columns: {unclassified}"

    def test_bound_emission_pivots(self, sample_widget):
        """bound_emission (input param) should have year, pivot, and value cols."""
        df = pd.DataFrame({
            "node": ["R11_AFR", "R11_AFR"],
            "type_emission": ["CO2", "CH4"],
            "type_tec": ["all", "all"],
            "type_year": ["cumulative", "cumulative"],
            "value": [100.0, 50.0],
        })
        info = sample_widget._identify_columns(df, is_results=False)
        assert info["year_cols"], "type_year should be a year column"
        assert info["pivot_cols"], "type_emission/type_tec should be pivot columns"
        assert info["value_col"] == "value"
        # Pivot should be possible
        assert sample_widget._should_pivot(df, info)

    def test_emission_scaling_columns(self, sample_widget):
        """emission_scaling has dims [type_emission, emission] — both should be classified."""
        df = pd.DataFrame({
            "type_emission": ["CO2", "CH4"],
            "emission": ["CO2_TCE", "CH4_TCE"],
            "value": [1.0, 25.0],
        })
        info = sample_widget._identify_columns(df, is_results=False)
        assert "type_emission" in info["pivot_cols"]
        assert "emission" in info["filter_cols"]
        assert info["value_col"] == "value"

    def test_share_constraint_columns(self, sample_widget):
        """share_commodity_up has dims [shares, node_share, year_act, time]."""
        df = pd.DataFrame({
            "shares": ["share_grp"],
            "node_share": ["R11_AFR"],
            "year_act": [2030],
            "time": ["year"],
            "value": [0.5],
        })
        info = sample_widget._identify_columns(df, is_results=False)
        assert "shares" in info["pivot_cols"]
        assert "node_share" in info["filter_cols"]
        assert "year_act" in info["year_cols"]
        assert "time" in info["ignored_cols"]

    def test_land_use_columns(self, sample_widget):
        """land_use has dims [node, land_scenario, year, land_type]."""
        df = pd.DataFrame({
            "node": ["R11_AFR"],
            "land_scenario": ["SSP2"],
            "year": [2030],
            "land_type": ["forest"],
            "value": [100.0],
        })
        info = sample_widget._identify_columns(df, is_results=False)
        assert "land_scenario" in info["pivot_cols"]
        assert "land_type" in info["filter_cols"]
        assert "year" in info["year_cols"]

    def test_data_transformer_matches_widget(self):
        """DataTransformer._identify_columns must match DataDisplayWidget's classification."""
        from utils.data_transformer import DataTransformer
        from core.message_ix_schema import MESSAGE_IX_PARAMETERS

        # Collect all unique dimension names
        all_dims = set()
        for pdef in MESSAGE_IX_PARAMETERS.values():
            all_dims.update(pdef.get("dims", []))

        cols = sorted(all_dims) + ["value"]
        df = pd.DataFrame([["x"] * len(cols)], columns=cols)

        info = DataTransformer._identify_columns(df, is_results=False)
        classified = set(
            info["year_cols"] + info["pivot_cols"]
            + info["filter_cols"] + info["ignored_cols"]
        )
        if info["value_col"]:
            classified.add(info["value_col"])

        unclassified = set(cols) - classified
        assert not unclassified, f"DataTransformer has unclassified columns: {unclassified}"

    def test_data_transformer_bound_emission_pivots(self):
        """DataTransformer chart path should pivot bound_emission correctly."""
        from utils.data_transformer import DataTransformer

        df = pd.DataFrame({
            "node": ["R11_AFR", "R11_AFR", "R11_CPA", "R11_CPA"],
            "type_emission": ["CO2", "CH4", "CO2", "CH4"],
            "type_tec": ["all", "all", "all", "all"],
            "type_year": ["cumulative", "cumulative", "cumulative", "cumulative"],
            "value": [100.0, 50.0, 200.0, 75.0],
        })
        result = DataTransformer.transform_for_display(
            df, is_results=False, display_mode="advanced",
            filters=None, hide_empty=False, for_chart=True
        )
        # Should be pivoted (not the raw 4-row table)
        assert result.shape != df.shape, "DataFrame should have been pivoted"


class TestYearFiltering:
    """Tests for year filtering including type_year column."""

    def test_widget_filters_type_year_numeric(self, sample_widget):
        """Widget year filtering should filter numeric type_year values."""
        # Set up year limits
        sample_widget.user_prefs.min_year = 2025
        sample_widget.user_prefs.max_year = 2040

        df = pd.DataFrame({
            "node": ["A", "A", "A", "A"],
            "type_emission": ["CO2", "CO2", "CO2", "CO2"],
            "type_tec": ["all", "all", "all", "all"],
            "type_year": [2020, 2030, 2040, 2050],
            "value": [10.0, 20.0, 30.0, 40.0],
        })
        result = sample_widget._apply_year_filtering(df)
        # Should keep 2030 and 2040, filter out 2020 and 2050
        assert len(result) == 2
        assert list(result["type_year"]) == [2030, 2040]

    def test_widget_keeps_non_numeric_type_year(self, sample_widget):
        """Non-numeric type_year values (e.g. 'cumulative') should be kept."""
        sample_widget.user_prefs.min_year = 2025
        sample_widget.user_prefs.max_year = 2040

        df = pd.DataFrame({
            "node": ["A", "A", "A"],
            "type_emission": ["CO2", "CO2", "CO2"],
            "type_tec": ["all", "all", "all"],
            "type_year": ["cumulative", 2020, 2030],
            "value": [100.0, 10.0, 20.0],
        })
        result = sample_widget._apply_year_filtering(df)
        # Should keep "cumulative" (non-numeric) and 2030 (in range), drop 2020
        assert len(result) == 2
        kept_years = list(result["type_year"])
        assert "cumulative" in kept_years
        assert 2030 in kept_years

    def test_transformer_filters_type_year(self):
        """DataTransformer should filter type_year when applying year limits."""
        from utils.data_transformer import DataTransformer

        df = pd.DataFrame({
            "node": ["A", "A", "A", "A"],
            "type_emission": ["CO2", "CO2", "CO2", "CO2"],
            "type_tec": ["all", "all", "all", "all"],
            "type_year": [2020, 2030, 2040, 2050],
            "value": [10.0, 20.0, 30.0, 40.0],
        })
        options = {"YearsLimitEnabled": True, "MinYear": 2025, "MaxYear": 2040}
        result = DataTransformer.apply_year_filtering(df, options)
        assert len(result) == 2
        assert list(result["type_year"]) == [2030, 2040]

    def test_transformer_keeps_non_numeric_type_year(self):
        """DataTransformer should keep non-numeric type_year values."""
        from utils.data_transformer import DataTransformer

        df = pd.DataFrame({
            "node": ["A", "A", "A"],
            "type_emission": ["CO2", "CO2", "CO2"],
            "type_tec": ["all", "all", "all"],
            "type_year": ["cumulative", 2020, 2030],
            "value": [100.0, 10.0, 20.0],
        })
        options = {"YearsLimitEnabled": True, "MinYear": 2025, "MaxYear": 2040}
        result = DataTransformer.apply_year_filtering(df, options)
        assert len(result) == 2
        kept_years = list(result["type_year"])
        assert "cumulative" in kept_years
        assert 2030 in kept_years

    def test_standard_year_column_still_works(self, sample_widget):
        """Standard 'year' column filtering should still work correctly."""
        sample_widget.user_prefs.min_year = 2025
        sample_widget.user_prefs.max_year = 2040

        df = pd.DataFrame({
            "node": ["A", "A", "A"],
            "technology": ["t1", "t1", "t1"],
            "year": [2020, 2030, 2050],
            "value": [10.0, 20.0, 30.0],
        })
        result = sample_widget._apply_year_filtering(df)
        assert len(result) == 1
        assert list(result["year"]) == [2030]
