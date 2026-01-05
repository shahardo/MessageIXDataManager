#!/usr/bin/env python3
"""
Simple test to verify the refactoring of _transform_to_advanced_view method
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from unittest.mock import patch, MagicMock

def test_transform_to_advanced_view():
    """Test the refactored _transform_to_advanced_view and its helper methods"""

    print("Testing refactored _transform_to_advanced_view method...")

    # Mock QApplication to avoid GUI issues
    with patch('PyQt5.QtWidgets.QApplication'):
        from ui.components.data_display_widget import DataDisplayWidget

        # Create widget
        widget = DataDisplayWidget()

        # Create test data
        data = [
            ['tech1', 'region1', 2020, 100.0],
            ['tech1', 'region1', 2025, 120.0],
            ['tech2', 'region1', 2020, 80.0],
            ['tech2', 'region1', 2025, 90.0],
        ]
        df = pd.DataFrame(data, columns=['technology', 'region', 'year', 'value'])

        print("1. Testing _identify_columns...")
        column_info = widget._identify_columns(df)
        assert 'value_col' in column_info
        assert column_info['value_col'] == 'value'
        assert 'year_cols' in column_info
        assert 'year' in column_info['year_cols']
        print("   ✓ _identify_columns works correctly")

        print("2. Testing _apply_filters...")
        filters = {'technology': 'tech1'}
        filtered_df = widget._apply_filters(df, filters, column_info)
        assert len(filtered_df) == 2  # Should have 2 rows for tech1
        assert all(filtered_df['technology'] == 'tech1')
        print("   ✓ _apply_filters works correctly")

        print("3. Testing _should_pivot...")
        should_pivot = widget._should_pivot(df, column_info)
        assert should_pivot == True  # Should pivot since we have year, property, and value columns
        print("   ✓ _should_pivot works correctly")

        print("4. Testing _perform_pivot...")
        pivoted = widget._perform_pivot(df, column_info)
        assert not pivoted.empty
        # Should have year as index and technologies as columns
        assert len(pivoted.columns) >= 2
        print("   ✓ _perform_pivot works correctly")

        print("5. Testing _hide_empty_columns...")
        # Create DataFrame with empty columns
        test_df = pd.DataFrame({
            'year': [2020, 2025],
            'technology': ['tech1', 'tech2'],
            'value': [100, 200],
            'empty_col': [0, 0],
            'empty_text': [None, None]
        })
        hidden = widget._hide_empty_columns(test_df, is_results=False)
        assert 'empty_col' not in hidden.columns
        assert 'empty_text' not in hidden.columns
        assert 'year' in hidden.columns
        assert 'technology' in hidden.columns
        assert 'value' in hidden.columns
        print("   ✓ _hide_empty_columns works correctly")

        print("6. Testing full _transform_to_advanced_view...")
        result = widget._transform_to_advanced_view(df, current_filters={'technology': 'tech1'}, is_results=False)
        assert not result.empty
        print("   ✓ _transform_to_advanced_view works correctly")

        print("\n🎉 All refactored methods work correctly!")
        return True

if __name__ == "__main__":
    try:
        test_transform_to_advanced_view()
        print("\n✅ transform_to_advanced_view() verification completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
