"""
Tests for ComparisonDataWidget — DataFrame merging and delta computation.
"""

import sys
import os

import pandas as pd
import numpy as np
import pytest

src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.data_models import Parameter
from ui.scenarios_comparison.comparison_data_widget import merge_parameters


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _param(name: str, rows: list, value_col: str = 'value') -> Parameter:
    """Build a Parameter from a list of (tec, year, value) tuples."""
    df = pd.DataFrame(rows, columns=['tec', 'year', value_col])
    return Parameter(name=name, df=df, metadata={'dims': ['tec', 'year'], 'units': '-'})


# ---------------------------------------------------------------------------
# merge_parameters
# ---------------------------------------------------------------------------

class TestMergeParameters:

    def test_common_rows_produce_both_values(self):
        p_a = _param('inv_cost', [('coal', 2025, 100), ('gas', 2025, 200)])
        p_b = _param('inv_cost', [('coal', 2025, 120), ('gas', 2025, 180)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert 'Value (A)' in merged.columns
        assert 'Value (B)' in merged.columns
        assert len(merged) == 2

    def test_delta_calculation(self):
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 130)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert merged['Δ'].iloc[0] == pytest.approx(30.0)

    def test_delta_negative(self):
        p_a = _param('inv_cost', [('coal', 2025, 150)])
        p_b = _param('inv_cost', [('coal', 2025, 100)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert merged['Δ'].iloc[0] == pytest.approx(-50.0)

    def test_delta_pct_calculation(self):
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 125)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert merged['Δ%'].iloc[0] == pytest.approx(25.0)

    def test_delta_pct_zero_denominator_is_na(self):
        """Δ% when value_A == 0 and value_B != 0 must be NaN (no baseline)."""
        p_a = _param('inv_cost', [('coal', 2025, 0)])
        p_b = _param('inv_cost', [('coal', 2025, 50)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert pd.isna(merged['Δ%'].iloc[0])

    def test_delta_pct_both_zero_is_zero(self):
        """Δ% when both A == 0 and B == 0 must be 0, not NaN."""
        p_a = _param('inv_cost', [('coal', 2025, 0)])
        p_b = _param('inv_cost', [('coal', 2025, 0)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert merged['Δ%'].iloc[0] == pytest.approx(0.0)

    def test_outer_join_a_only_row(self):
        """Row in A but not B → Value(B) is NaN."""
        p_a = _param('inv_cost', [('coal', 2025, 100), ('nuclear', 2025, 300)])
        p_b = _param('inv_cost', [('coal', 2025, 120)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        nuclear_row = merged[merged['tec'] == 'nuclear']
        assert len(nuclear_row) == 1
        assert pd.isna(nuclear_row['Value (B)'].iloc[0])

    def test_outer_join_b_only_row(self):
        """Row in B but not A → Value(A) is NaN."""
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 120), ('wind', 2025, 50)])
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        wind_row = merged[merged['tec'] == 'wind']
        assert len(wind_row) == 1
        assert pd.isna(wind_row['Value (A)'].iloc[0])

    def test_lvl_column_treated_as_value(self):
        """Variables use 'lvl' instead of 'value' — merge_parameters handles it."""
        p_a = _param('var_ACT', [('coal', 2025, 500)], value_col='lvl')
        p_b = _param('var_ACT', [('coal', 2025, 600)], value_col='lvl')
        merged = merge_parameters(p_a, p_b, 'A', 'B')
        assert merged['Δ'].iloc[0] == pytest.approx(100.0)

    def test_column_labels_reflect_scenario_names(self):
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 100)])
        merged = merge_parameters(p_a, p_b, 'Baseline', 'ETS')
        assert 'Value (Baseline)' in merged.columns
        assert 'Value (ETS)' in merged.columns


# ---------------------------------------------------------------------------
# ComparisonDataWidget (smoke / UI tests)
# ---------------------------------------------------------------------------

class TestComparisonDataWidget:

    def _make_params(self):
        p_a = _param('inv_cost', [('coal', 2025, 100), ('gas', 2025, 200),
                                   ('coal', 2030, 110), ('gas', 2030, 210)])
        p_b = _param('inv_cost', [('coal', 2025, 120), ('gas', 2025, 180),
                                   ('coal', 2030, 115), ('gas', 2030, 225)])
        return p_a, p_b

    def test_display_populates_table(self, qtbot):
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        p_a, p_b = self._make_params()
        w.display(p_a, p_b, 'A', 'B')
        # Table visible state is True even before the top-level widget is shown
        assert not w._table.isHidden()
        assert w._table.rowCount() == 4

    def test_table_has_delta_columns(self, qtbot):
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        p_a, p_b = self._make_params()
        w.display(p_a, p_b, 'A', 'B')
        headers = [w._table.horizontalHeaderItem(i).text()
                   for i in range(w._table.columnCount())]
        assert 'Δ' in headers
        assert 'Δ%' in headers

    def test_positive_delta_cell_green(self, qtbot):
        from PyQt5.QtGui import QColor
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget, _GREEN
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        # A=100, B=150 → Δ = +50 → green
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 150)])
        w.display(p_a, p_b, 'A', 'B')
        headers = [w._table.horizontalHeaderItem(i).text()
                   for i in range(w._table.columnCount())]
        delta_col = headers.index('Δ')
        cell = w._table.item(0, delta_col)
        assert cell.background().color() == _GREEN

    def test_negative_delta_cell_red(self, qtbot):
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget, _RED
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        # A=200, B=100 → Δ = -100 → red
        p_a = _param('inv_cost', [('coal', 2025, 200)])
        p_b = _param('inv_cost', [('coal', 2025, 100)])
        w.display(p_a, p_b, 'A', 'B')
        headers = [w._table.horizontalHeaderItem(i).text()
                   for i in range(w._table.columnCount())]
        delta_col = headers.index('Δ')
        cell = w._table.item(0, delta_col)
        assert cell.background().color() == _RED

    def test_zero_delta_cell_default_background(self, qtbot):
        from PyQt5.QtGui import QColor
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget, _GREEN, _RED
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        p_a = _param('inv_cost', [('coal', 2025, 100)])
        p_b = _param('inv_cost', [('coal', 2025, 100)])
        w.display(p_a, p_b, 'A', 'B')
        headers = [w._table.horizontalHeaderItem(i).text()
                   for i in range(w._table.columnCount())]
        delta_col = headers.index('Δ')
        cell = w._table.item(0, delta_col)
        # Should NOT be green or red
        bg = cell.background().color()
        assert bg != _GREEN
        assert bg != _RED

    def test_get_merged_df_returns_dataframe(self, qtbot):
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        p_a, p_b = self._make_params()
        w.display(p_a, p_b, 'A', 'B')
        df = w.get_merged_df()
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_clear_hides_table(self, qtbot):
        from ui.scenarios_comparison.comparison_data_widget import ComparisonDataWidget
        w = ComparisonDataWidget()
        qtbot.addWidget(w)
        p_a, p_b = self._make_params()
        w.display(p_a, p_b, 'A', 'B')
        w.clear()
        assert not w._table.isVisible()
        assert w.get_merged_df() is None
