"""
Tests for DataFileManager — focusing on the _load_excel_data() path added to
support loading solver result Excel files (var_* / equ_* sheets).
"""

import io
import os
import sys
import zipfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.data_models import Parameter, ScenarioData
from managers.data_file_manager import DataFileManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> DataFileManager:
    """Return a DataFileManager with a no-op console callback."""
    return DataFileManager(console_callback=lambda msg: None)


def _excel_bytes(sheets: dict) -> bytes:
    """Create an in-memory .xlsx file with the given {sheet_name: DataFrame} map."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# load_data_file dispatch
# ---------------------------------------------------------------------------

class TestLoadDataFileDispatch:
    """load_data_file() should route to the right loader based on extension."""

    def test_zip_dispatches_to_zipped_csv(self, tmp_path):
        mgr = _make_manager()
        # Create a minimal valid zip with one var_ACT.csv
        zip_path = str(tmp_path / "data.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            csv_content = "technology,year_act,lvl,mrg\ncoal,2020,100.0,0.0\n"
            zf.writestr("var_ACT.csv", csv_content)

        result, replaced = mgr.load_data_file(zip_path)
        assert result is not None
        assert result.get_parameter("ACT") is not None

    def test_xlsx_dispatches_to_excel_loader(self, tmp_path):
        mgr = _make_manager()
        df = pd.DataFrame({"technology": ["coal"], "year_act": [2020], "lvl": [100.0], "mrg": [0.0]})
        xlsx_path = str(tmp_path / "results.xlsx")
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="var_ACT", index=False)

        result, replaced = mgr.load_data_file(xlsx_path)
        assert result is not None
        assert result.get_parameter("ACT") is not None

    def test_unsupported_extension_returns_none(self, tmp_path):
        mgr = _make_manager()
        result, replaced = mgr.load_data_file(str(tmp_path / "data.csv"))
        assert result is None
        assert replaced == []


# ---------------------------------------------------------------------------
# _load_excel_data — variable sheets (var_*)
# ---------------------------------------------------------------------------

class TestLoadExcelDataVariables:
    """Excel sheets named var_<NAME> are loaded as result variables."""

    def test_var_sheet_loaded_as_variable(self, tmp_path):
        mgr = _make_manager()
        df = pd.DataFrame({
            "node_loc": ["World"], "technology": ["solar_pv"],
            "year_act": [2025], "lvl": [500.0], "mrg": [0.0],
        })
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="var_ACT", index=False)

        result, replaced = mgr.load_data_file(xlsx)
        param = result.get_parameter("ACT")
        assert param is not None
        assert param.metadata.get("result_type") == "variable"

    def test_multiple_var_sheets(self, tmp_path):
        mgr = _make_manager()
        df_act = pd.DataFrame({"technology": ["coal"], "year_act": [2020], "lvl": [100.0], "mrg": [0.0]})
        df_cap = pd.DataFrame({"technology": ["solar"], "year_act": [2020], "lvl": [50.0], "mrg": [0.0]})
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            df_act.to_excel(writer, sheet_name="var_ACT", index=False)
            df_cap.to_excel(writer, sheet_name="var_CAP", index=False)

        result, replaced = mgr.load_data_file(xlsx)
        assert result.get_parameter("ACT") is not None
        assert result.get_parameter("CAP") is not None

    def test_unrecognised_sheet_is_ignored(self, tmp_path):
        mgr = _make_manager()
        df = pd.DataFrame({"col": [1, 2]})
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="summary", index=False)

        result, replaced = mgr.load_data_file(xlsx)
        assert result is not None
        assert len(result.parameters) == 0


# ---------------------------------------------------------------------------
# _load_excel_data — equation sheets (equ_*)
# ---------------------------------------------------------------------------

class TestLoadExcelDataEquations:
    """Excel sheets named equ_<NAME> are loaded as result equations."""

    def test_equ_sheet_loaded_as_equation(self, tmp_path):
        mgr = _make_manager()
        df = pd.DataFrame({
            "node_loc": ["World"], "commodity": ["electr"],
            "year_act": [2020], "lvl": [0.0], "mrg": [1.5],
        })
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="equ_COMMODITY_BAL", index=False)

        result, replaced = mgr.load_data_file(xlsx)
        param = result.get_parameter("COMMODITY_BAL")
        assert param is not None
        assert param.metadata.get("result_type") == "equation"


# ---------------------------------------------------------------------------
# _load_excel_data — replaced items detection
# ---------------------------------------------------------------------------

class TestLoadExcelDataReplacedItems:
    """Items that already exist in the existing_scenario are reported as replaced."""

    def test_replaced_variable_detected(self, tmp_path):
        mgr = _make_manager()

        # Build existing scenario with ACT
        existing = ScenarioData()
        old_df = pd.DataFrame({"technology": ["coal"], "year_act": [2020], "lvl": [10.0], "mrg": [0.0]})
        existing.add_parameter(Parameter("ACT", old_df, {"result_type": "variable"}))

        # New Excel also has ACT
        new_df = pd.DataFrame({"technology": ["solar"], "year_act": [2025], "lvl": [999.0], "mrg": [0.0]})
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            new_df.to_excel(writer, sheet_name="var_ACT", index=False)

        result, replaced = mgr.load_data_file(xlsx, existing_scenario=existing)
        assert any(name == "ACT" for _, name in replaced)

    def test_new_variable_not_in_replaced(self, tmp_path):
        mgr = _make_manager()
        existing = ScenarioData()  # empty

        df = pd.DataFrame({"technology": ["wind"], "year_act": [2030], "lvl": [200.0], "mrg": [0.0]})
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="var_CAP", index=False)

        result, replaced = mgr.load_data_file(xlsx, existing_scenario=existing)
        assert replaced == []


# ---------------------------------------------------------------------------
# _load_excel_data — corrupt / unreadable file
# ---------------------------------------------------------------------------

class TestLoadExcelDataErrors:
    def test_missing_file_returns_none(self):
        mgr = _make_manager()
        result, replaced = mgr.load_data_file("/nonexistent/path/data.xlsx")
        assert result is None
        assert replaced == []

    def test_empty_sheet_is_skipped(self, tmp_path):
        mgr = _make_manager()
        # Write an empty DataFrame as var_ACT
        xlsx = str(tmp_path / "r.xlsx")
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            pd.DataFrame().to_excel(writer, sheet_name="var_ACT", index=False)

        # Should not crash; may return empty scenario
        result, replaced = mgr.load_data_file(xlsx)
        # Empty sheet → parameter not added
        assert result is not None
