"""
Tests for parameter_utils.py - Parameter creation utility functions
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from core.data_models import Parameter
from utils.parameter_utils import create_parameter_from_data


class TestCreateParameterFromData:
    """Test the create_parameter_from_data function"""

    def test_create_parameter_basic(self):
        """Test basic parameter creation with simple data"""
        param_name = "test_param"
        param_data = [
            ["node1", "tech1", 100.0],
            ["node2", "tech1", 200.0],
            ["node1", "tech2", 150.0]
        ]
        headers = ["node", "technology", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert result.name == param_name
        assert len(result.df) == 3
        assert list(result.df.columns) == headers
        assert result.metadata['dims'] == ["node", "technology"]
        assert result.metadata['value_column'] == "value"

    def test_create_parameter_empty_data(self):
        """Test parameter creation with empty data returns None"""
        param_name = "empty_param"
        param_data = []
        headers = ["col1", "col2"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is None

    def test_create_parameter_no_headers(self):
        """Test parameter creation with no headers returns None"""
        param_name = "no_headers_param"
        param_data = [["data1", "data2"]]
        headers = []

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is None

    def test_create_parameter_none_conversion(self):
        """Test that None values are converted to NaN"""
        param_name = "none_param"
        param_data = [
            ["node1", None, 100.0],
            [None, "tech1", 200.0],
            ["node1", "tech1", None]
        ]
        headers = ["node", "technology", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert pd.isna(result.df.loc[0, "technology"])
        assert pd.isna(result.df.loc[1, "node"])
        assert pd.isna(result.df.loc[2, "value"])

    def test_create_parameter_integer_to_float_conversion(self):
        """Test that integer columns with NaN are converted to float"""
        param_name = "int_to_float_param"
        param_data = [
            ["node1", 1, 100],
            ["node2", 2, 200],
            ["node3", None, 300]  # This should trigger int->float conversion
        ]
        headers = ["node", "level", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        # level column should be float64 due to NaN
        assert result.df["level"].dtype == np.float64
        assert pd.isna(result.df.loc[2, "level"])

    def test_create_parameter_all_zero_columns_filtered(self):
        """Test that all-zero columns are treated as empty (converted to NaN)"""
        param_name = "zero_columns_param"
        param_data = [
            ["node1", 0, 100.0],
            ["node2", 0, 200.0],
            ["node3", 0, 300.0]
        ]
        headers = ["node", "zero_col", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        # zero_col should be all NaN
        assert result.df["zero_col"].isna().all()

    def test_create_parameter_remove_empty_rows(self):
        """Test that completely empty rows are removed"""
        param_name = "empty_rows_param"
        param_data = [
            ["node1", "tech1", 100.0],
            [None, None, None],  # Empty row
            ["node2", "tech2", 200.0],
            [None, None, None]   # Another empty row
        ]
        headers = ["node", "technology", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert len(result.df) == 2  # Only non-empty rows remain
        assert result.df.iloc[0]["node"] == "node1"
        assert result.df.iloc[1]["node"] == "node2"

    def test_create_parameter_single_column(self):
        """Test parameter with single column (no dimensions)"""
        param_name = "single_col_param"
        param_data = [
            [100.0],
            [200.0],
            [300.0]
        ]
        headers = ["value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert result.metadata['dims'] == []
        assert result.metadata['value_column'] == "value"

    def test_create_parameter_metadata_overrides(self):
        """Test parameter creation with metadata overrides"""
        param_name = "override_param"
        param_data = [
            ["node1", "tech1", 100.0],
            ["node2", "tech2", 200.0]
        ]
        headers = ["node", "technology", "value"]
        metadata_overrides = {
            'units': 'GW',
            'desc': 'Custom description',
            'custom_field': 'custom_value'
        }

        result = create_parameter_from_data(param_name, param_data, headers, metadata_overrides)

        assert result is not None
        assert result.metadata['units'] == 'GW'
        assert result.metadata['desc'] == 'Custom description'
        assert result.metadata['custom_field'] == 'custom_value'
        # Default metadata should still be present
        assert 'dims' in result.metadata
        assert 'value_column' in result.metadata

    def test_create_parameter_exception_handling(self):
        """Test that exceptions during parameter creation are handled gracefully"""
        param_name = "exception_param"
        param_data = [
            ["valid", "data", 100.0]
        ]
        headers = ["col1", "col2", "col3"]

        # Mock pd.DataFrame to raise an exception
        with patch('pandas.DataFrame', side_effect=Exception("Test exception")):
            result = create_parameter_from_data(param_name, param_data, headers)

        assert result is None

    def test_create_parameter_mixed_data_types(self):
        """Test parameter creation with mixed data types"""
        param_name = "mixed_types_param"
        param_data = [
            ["node1", 1, 100.5, True],
            ["node2", 2, 200.0, False],
            ["node3", 3, 300.25, True]
        ]
        headers = ["node", "level", "value", "flag"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert len(result.df) == 3
        assert result.df["value"].dtype == np.float64  # Should be float
        assert result.df["level"].dtype == np.int64    # Should remain int (no NaN)
        # Pandas stores boolean columns as bool dtype, not object
        assert result.df["flag"].dtype == bool



    def test_create_parameter_large_dataset(self):
        """Test parameter creation with larger dataset"""
        param_name = "large_param"
        # Create 1000 rows of data
        param_data = [["node{}".format(i), "tech{}".format(i % 10), float(i * 10)]
                     for i in range(1000)]
        headers = ["node", "technology", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert len(result.df) == 1000
        assert result.df["value"].sum() == sum(float(i * 10) for i in range(1000))

    def test_create_parameter_special_characters(self):
        """Test parameter creation with special characters in data"""
        param_name = "special_chars_param"
        param_data = [
            ["node-1_2", "tech@#$%", 100.5],
            ["node/\\3", "tech<>&", -50.25]
        ]
        headers = ["node", "technology", "value"]

        result = create_parameter_from_data(param_name, param_data, headers)

        assert result is not None
        assert len(result.df) == 2
        assert result.df.loc[0, "node"] == "node-1_2"
        assert result.df.loc[1, "technology"] == "tech<>&"
