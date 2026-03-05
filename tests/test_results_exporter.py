"""
Tests for ResultsExporter.

ResultsExporter is a static-method-only class, so all tests use its methods
directly without requiring an ixmp/message_ix installation.  Scenario objects
are replaced by simple mocks that expose the required interface.
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from managers.results_exporter import ResultsExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_log():
    """Return a list and a log function that appends to it."""
    msgs = []
    return msgs, lambda m: msgs.append(m)


def _make_scenario(var_list=None, equ_list=None, var_data=None, equ_data=None):
    """
    Build a minimal mock scenario with controllable var/equ data.

    var_data / equ_data: dict of name → DataFrame or dict (simulates scalar)
    """
    scenario = MagicMock()
    scenario.var_list.return_value = var_list or []
    scenario.equ_list.return_value = equ_list or []

    def _var(name):
        return (var_data or {}).get(name, pd.DataFrame())

    def _equ(name):
        return (equ_data or {}).get(name, pd.DataFrame())

    scenario.var.side_effect = _var
    scenario.equ.side_effect = _equ
    return scenario


# ---------------------------------------------------------------------------
# _collect_names
# ---------------------------------------------------------------------------

class TestCollectNames:
    """_collect_names() merges a priority list with the scenario's actual list."""

    def test_primary_names_come_first(self):
        scenario = _make_scenario(var_list=["CAP", "ACT", "EMISS"])
        _, log = _mock_log()
        result = ResultsExporter._collect_names(scenario, "var_list", ["ACT", "CAP"], log)
        assert result[:2] == ["ACT", "CAP"]

    def test_extra_names_appended_after_primary(self):
        scenario = _make_scenario(var_list=["ACT", "CAP", "EMISS"])
        _, log = _mock_log()
        result = ResultsExporter._collect_names(scenario, "var_list", ["ACT", "CAP"], log)
        assert "EMISS" in result
        assert result.index("EMISS") > result.index("ACT")

    def test_primary_names_not_in_available_are_excluded(self):
        """Primary names that don't exist in var_list should not appear in output."""
        scenario = _make_scenario(var_list=["ACT"])
        _, log = _mock_log()
        result = ResultsExporter._collect_names(
            scenario, "var_list", ["ACT", "STORAGE_CONTENT"], log
        )
        assert "STORAGE_CONTENT" not in result
        assert "ACT" in result

    def test_no_duplicates(self):
        scenario = _make_scenario(var_list=["ACT", "CAP"])
        _, log = _mock_log()
        result = ResultsExporter._collect_names(scenario, "var_list", ["ACT", "ACT", "CAP"], log)
        assert result.count("ACT") == 1
        assert result.count("CAP") == 1

    def test_empty_var_list(self):
        scenario = _make_scenario(var_list=[])
        _, log = _mock_log()
        result = ResultsExporter._collect_names(scenario, "var_list", ["ACT", "CAP"], log)
        assert result == []

    def test_var_list_raises_logs_warning(self):
        scenario = MagicMock()
        scenario.var_list.side_effect = RuntimeError("ixmp error")
        msgs, log = _mock_log()
        result = ResultsExporter._collect_names(scenario, "var_list", ["ACT"], log)
        assert result == []
        assert any("Warning" in m for m in msgs)


# ---------------------------------------------------------------------------
# _write_sheet — DataFrame result
# ---------------------------------------------------------------------------

class TestWriteSheetDataFrame:
    """_write_sheet() for a normal DataFrame variable."""

    def test_writes_dataframe_returns_1(self, tmp_path):
        df = pd.DataFrame({"technology": ["coal"], "year_act": [2020], "lvl": [100.0]})
        scenario = _make_scenario(var_data={"ACT": df})
        _, log = _mock_log()
        # Use a real file so to_excel can write without error
        out = str(tmp_path / "out.xlsx")
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            result = ResultsExporter._write_sheet(writer, scenario, "var", "ACT", log)
        assert result == 1

    def test_empty_dataframe_returns_0(self):
        # Returns 0 before calling to_excel, so a MagicMock writer is sufficient
        scenario = _make_scenario(var_data={"ACT": pd.DataFrame()})
        _, log = _mock_log()
        result = ResultsExporter._write_sheet(MagicMock(), scenario, "var", "ACT", log)
        assert result == 0

    def test_none_result_returns_0(self):
        scenario = _make_scenario(var_data={"ACT": None})
        _, log = _mock_log()
        result = ResultsExporter._write_sheet(MagicMock(), scenario, "var", "ACT", log)
        assert result == 0

    def test_fetch_exception_returns_0_and_logs_warning(self):
        scenario = MagicMock()
        scenario.var.side_effect = RuntimeError("no such variable")
        msgs, log = _mock_log()
        result = ResultsExporter._write_sheet(MagicMock(), scenario, "var", "MISSING", log)
        assert result == 0
        assert any("Warning" in m for m in msgs)


# ---------------------------------------------------------------------------
# _write_sheet — dict result (scalar variables)
# ---------------------------------------------------------------------------

class TestWriteSheetDict:
    """ixmp returns a plain dict for scalar variables; _write_sheet must handle it."""

    def test_dict_wrapped_in_dataframe_returns_1(self):
        """A dict like {'lvl': 1234.5, 'mrg': 0.0} should be written as a 1-row DataFrame."""
        scalar_dict = {"lvl": 1234.5, "mrg": 0.0}
        scenario = _make_scenario(var_data={"OBJ": scalar_dict})
        _, log = _mock_log()

        # Use a real ExcelWriter backed by BytesIO to verify the write succeeds
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            result = ResultsExporter._write_sheet(writer, scenario, "var", "OBJ", log)

        assert result == 1
        # Verify the sheet was actually written with the expected data
        buf.seek(0)
        written = pd.read_excel(buf, sheet_name="var_OBJ")
        assert list(written.columns) == ["lvl", "mrg"]
        assert written["lvl"].iloc[0] == pytest.approx(1234.5)

    def test_empty_dict_returns_0(self):
        """An empty dict produces an empty DataFrame and should return 0."""
        scenario = _make_scenario(var_data={"OBJ": {}})
        _, log = _mock_log()
        # Returns 0 before to_excel is called, so MagicMock writer is fine
        result = ResultsExporter._write_sheet(MagicMock(), scenario, "var", "OBJ", log)
        assert result == 0


# ---------------------------------------------------------------------------
# _write_sheet — sheet name truncation
# ---------------------------------------------------------------------------

class TestWriteSheetNameTruncation:
    """Excel sheet names must not exceed 31 characters."""

    def test_long_name_truncated_to_31_chars(self):
        long_name = "VERY_LONG_VARIABLE_NAME_EXCEEDING"  # 33 chars → truncated
        full_sheet = f"var_{long_name}"
        assert len(full_sheet) > 31

        df = pd.DataFrame({"lvl": [1.0]})
        scenario = _make_scenario(var_data={long_name: df})
        _, log = _mock_log()

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            result = ResultsExporter._write_sheet(writer, scenario, "var", long_name, log)

        assert result == 1
        buf.seek(0)
        xl = pd.ExcelFile(buf)
        sheet = xl.sheet_names[0]
        assert len(sheet) <= 31
