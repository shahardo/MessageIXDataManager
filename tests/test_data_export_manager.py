"""
Tests for DataExportManager — round-trip write / read verification.

Each test builds an in-memory ScenarioData, saves it with DataExportManager,
then reloads it via ExcelParser (the same parser used by InputManager) and
asserts that all data survives the round trip intact.
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import Parameter, ScenarioData
from managers.data_export_manager import DataExportManager
from utils.parsing_strategies import ExcelParser
import openpyxl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scenario(*params, sets=None):
    """Build a ScenarioData from Parameter objects and an optional sets dict."""
    scenario = ScenarioData()
    for p in params:
        scenario.add_parameter(p, mark_modified=False, add_to_history=False)
    if sets:
        for name, values in sets.items():
            scenario.sets[name] = pd.Series(values)
    return scenario


def _roundtrip(scenario):
    """Save *scenario* to a temp file and reload it; return the reloaded ScenarioData."""
    mgr = DataExportManager()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        tmp_path = f.name
    try:
        ok = mgr.save_scenario(scenario, tmp_path)
        assert ok, "save_scenario returned False"
        wb = openpyxl.load_workbook(tmp_path)
        loaded = ScenarioData()
        ExcelParser().parse_workbook(wb, loaded, tmp_path)
        return loaded
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Round-trip tests: save then reload must reproduce the original data."""

    def test_single_parameter_preserved(self):
        """Values and column names survive a basic save/reload cycle."""
        df = pd.DataFrame({
            'node':       ['World', 'World'],
            'technology': ['coal_ppl', 'gas_ppl'],
            'year':       [2020, 2025],
            'value':      [1.5, 2.3],
        })
        scenario = _make_scenario(Parameter('inv_cost', df, {}))
        loaded = _roundtrip(scenario)

        assert 'inv_cost' in loaded.parameters
        df_out = loaded.get_parameter('inv_cost').df
        assert list(df_out.columns) == list(df.columns)
        assert len(df_out) == 2
        pd.testing.assert_frame_equal(
            df_out.reset_index(drop=True),
            df.reset_index(drop=True),
            check_dtype=False,
        )

    def test_multiple_parameters_all_preserved(self):
        """All parameters in a scenario are written and reloaded."""
        p1 = Parameter('inv_cost', pd.DataFrame({
            'node': ['R1'], 'technology': ['coal_ppl'], 'value': [100.0]
        }), {})
        p2 = Parameter('fix_cost', pd.DataFrame({
            'node': ['R1'], 'technology': ['gas_ppl'], 'value': [50.0]
        }), {})
        p3 = Parameter('demand', pd.DataFrame({
            'node': ['R1'], 'commodity': ['electr'], 'level': ['useful'], 'value': [200.0]
        }), {})

        loaded = _roundtrip(_make_scenario(p1, p2, p3))

        assert set(loaded.parameters.keys()) == {'inv_cost', 'fix_cost', 'demand'}

    def test_sets_preserved(self):
        """Sets written to the Sets sheet are reloaded correctly."""
        sets = {
            'technology': ['coal_ppl', 'gas_ppl', 'wind_ppl'],
            'node':       ['World', 'Europe'],
        }
        p = Parameter('dummy', pd.DataFrame({'value': [1.0]}), {})
        scenario = _make_scenario(p, sets=sets)
        loaded = _roundtrip(scenario)

        assert 'technology' in loaded.sets
        assert 'node' in loaded.sets
        assert set(loaded.sets['technology'].values) == {'coal_ppl', 'gas_ppl', 'wind_ppl'}
        assert set(loaded.sets['node'].values) == {'World', 'Europe'}

    def test_numeric_values_exact(self):
        """Integer and float values are written and read back without alteration."""
        df = pd.DataFrame({
            'node':  ['R1', 'R1', 'R1'],
            'year':  [2020,  2025,  2030],
            'value': [0.0,   1e6,   -3.14],
        })
        loaded = _roundtrip(_make_scenario(Parameter('test_param', df, {})))
        df_out = loaded.get_parameter('test_param').df
        pd.testing.assert_series_equal(
            df_out['value'].reset_index(drop=True),
            df['value'].reset_index(drop=True),
            check_dtype=False,
        )

    def test_nan_values_become_none(self):
        """NaN cells in the source DataFrame don't cause errors and reload as None/NaN."""
        df = pd.DataFrame({
            'node':  ['R1', 'R1'],
            'value': [1.0,  float('nan')],
        })
        # Save must succeed (no crash)
        loaded = _roundtrip(_make_scenario(Parameter('nan_param', df, {})))
        df_out = loaded.get_parameter('nan_param').df
        assert len(df_out) == 2

    def test_sheet_name_sanitisation(self):
        """Parameter names with invalid Excel chars are sanitised and still round-trip."""
        df = pd.DataFrame({'value': [42.0]})
        # '[' and ']' are invalid in sheet names
        p = Parameter('param[test]', df, {})
        loaded = _roundtrip(_make_scenario(p))
        # The parameter is reloaded under its sanitised sheet name
        assert len(loaded.parameters) == 1

    def test_long_parameter_name_truncated(self):
        """Names longer than 31 chars are truncated to a valid sheet name."""
        long_name = 'a' * 50          # 50 chars — exceeds Excel's 31-char limit
        df = pd.DataFrame({'dim': ['x'], 'value': [7.0]})
        loaded = _roundtrip(_make_scenario(Parameter(long_name, df, {})))
        assert len(loaded.parameters) == 1
        param = next(iter(loaded.parameters.values()))
        assert param.df['value'].iloc[0] == pytest.approx(7.0)

    def test_duplicate_truncated_names_deduplicated(self):
        """Two parameters whose names differ only beyond char 31 get unique sheet names."""
        df = pd.DataFrame({'value': [1.0]})
        prefix = 'x' * 30
        p1 = Parameter(prefix + 'A', df.copy(), {})
        p2 = Parameter(prefix + 'B', df.copy(), {})
        loaded = _roundtrip(_make_scenario(p1, p2))
        # Both parameters must survive
        assert len(loaded.parameters) == 2

    def test_empty_parameter_skipped(self):
        """Parameters with empty DataFrames are silently skipped."""
        good = Parameter('good', pd.DataFrame({'value': [1.0]}), {})
        empty = Parameter('empty', pd.DataFrame(), {})
        loaded = _roundtrip(_make_scenario(good, empty))
        assert 'good' in loaded.parameters
        assert 'empty' not in loaded.parameters

    def test_multicolumn_parameter_column_order(self):
        """Column order in the DataFrame is preserved through the round trip."""
        cols = ['node_loc', 'technology', 'year_vtg', 'time', 'value']
        df = pd.DataFrame([[f'v{i}' for i in range(len(cols) - 1)] + [9.9]], columns=cols)
        loaded = _roundtrip(_make_scenario(Parameter('output', df, {})))
        df_out = loaded.get_parameter('output').df
        assert list(df_out.columns) == cols

    def test_modified_only_ignored_all_params_saved(self):
        """save_scenario always writes all parameters regardless of modified_only."""
        p1 = Parameter('p1', pd.DataFrame({'value': [1.0]}), {})
        p2 = Parameter('p2', pd.DataFrame({'value': [2.0]}), {})
        scenario = _make_scenario(p1, p2)
        # Mark only p1 as modified
        scenario.modified.add('p1')

        mgr = DataExportManager()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            tmp_path = f.name
        try:
            mgr.save_scenario(scenario, tmp_path, modified_only=True)
            wb = openpyxl.load_workbook(tmp_path)
            loaded = ScenarioData()
            ExcelParser().parse_workbook(wb, loaded, tmp_path)
            # Both parameters must be present even though modified_only=True
            assert 'p1' in loaded.parameters
            assert 'p2' in loaded.parameters
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def test_save_returns_false_on_bad_path(self):
        """save_scenario returns False (not raises) when the path is invalid."""
        mgr = DataExportManager()
        scenario = _make_scenario(Parameter('p', pd.DataFrame({'v': [1]}), {}))
        result = mgr.save_scenario(scenario, '/nonexistent/dir/out.xlsx')
        assert result is False

    def test_has_modified_data_and_clear(self):
        """has_modified_data and clear_modified_flags behave correctly."""
        mgr = DataExportManager()
        scenario = _make_scenario(Parameter('p', pd.DataFrame({'v': [1]}), {}))

        assert not mgr.has_modified_data(scenario)
        assert mgr.get_modified_parameters_count(scenario) == 0

        scenario.modified.add('p')
        assert mgr.has_modified_data(scenario)
        assert mgr.get_modified_parameters_count(scenario) == 1

        mgr.clear_modified_flags(scenario)
        assert not mgr.has_modified_data(scenario)
