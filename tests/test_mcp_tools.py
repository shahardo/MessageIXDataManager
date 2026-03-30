"""
Unit tests for src/ai/mcp_tools.py

Tests the tool layer without making any real LLM API calls.
A minimal ScenarioData is constructed in each fixture.
"""

import json
import sys
import os

import numpy as np
import pandas as pd
import pytest

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import Parameter, ScenarioData
from ai.mcp_tools import AIBatchEditCommand, MCPTools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_fix_cost_df() -> pd.DataFrame:
    rows = []
    for tech in ["coal_ppl", "gas_ppl", "wind_ppl"]:
        for yr in [2020, 2030, 2040, 2050]:
            rows.append({"node": "World", "technology": tech,
                         "year_vtg": yr, "year_act": yr, "value": float(yr)})
    return pd.DataFrame(rows)


def _make_demand_df() -> pd.DataFrame:
    rows = []
    for yr in [2020, 2030, 2040, 2050]:
        rows.append({"node": "World", "commodity": "electr",
                     "level": "useful", "year": yr, "value": float(yr * 2)})
    return pd.DataFrame(rows)


@pytest.fixture
def scenario() -> ScenarioData:
    sd = ScenarioData()

    fix_cost = Parameter(
        "fix_cost",
        _make_fix_cost_df(),
        {"units": "USD/GW", "desc": "Fixed O&M cost",
         "dims": ["node", "technology", "year_vtg", "year_act"],
         "value_column": "value"},
    )
    demand = Parameter(
        "demand",
        _make_demand_df(),
        {"units": "GWa", "desc": "Energy demand",
         "dims": ["node", "commodity", "level", "year"],
         "value_column": "value"},
    )
    sd.add_parameter(fix_cost, mark_modified=False, add_to_history=False)
    sd.add_parameter(demand, mark_modified=False, add_to_history=False)
    sd.modified.clear()

    sd.sets["technology"] = pd.Series(["coal_ppl", "gas_ppl", "wind_ppl"])
    sd.sets["node"] = pd.Series(["World"])

    return sd


@pytest.fixture
def tools(scenario) -> MCPTools:
    # Import after path is set up; QApplication may not be running in tests
    # so we instantiate MCPTools without a parent QObject.
    return MCPTools(
        scenario_accessor=lambda: scenario,
        undo_manager_accessor=lambda: None,
    )


@pytest.fixture
def no_scenario_tools() -> MCPTools:
    return MCPTools(
        scenario_accessor=lambda: None,
        undo_manager_accessor=lambda: None,
    )


# ---------------------------------------------------------------------------
# get_scenario_info
# ---------------------------------------------------------------------------

class TestGetScenarioInfo:
    def test_returns_counts(self, tools):
        result = json.loads(tools.get_scenario_info())
        assert result["parameter_count"] == 2
        assert result["set_count"] == 2

    def test_no_scenario(self, no_scenario_tools):
        result = json.loads(no_scenario_tools.get_scenario_info())
        assert "error" in result


# ---------------------------------------------------------------------------
# list_parameters
# ---------------------------------------------------------------------------

class TestListParameters:
    def test_returns_all(self, tools):
        result = json.loads(tools.list_parameters())
        names = [r["name"] for r in result]
        assert "fix_cost" in names
        assert "demand" in names

    def test_includes_metadata(self, tools):
        result = json.loads(tools.list_parameters())
        entry = next(r for r in result if r["name"] == "fix_cost")
        assert "dims" in entry
        assert "units" in entry
        assert "shape" in entry
        assert entry["units"] == "USD/GW"

    def test_no_scenario(self, no_scenario_tools):
        result = json.loads(no_scenario_tools.list_parameters())
        assert "error" in result


# ---------------------------------------------------------------------------
# get_parameter
# ---------------------------------------------------------------------------

class TestGetParameter:
    def test_returns_rows(self, tools):
        result = json.loads(tools.get_parameter("fix_cost"))
        assert result["total_shown"] == 12  # 3 techs × 4 years

    def test_filter_by_technology(self, tools):
        result = json.loads(tools.get_parameter("fix_cost", filters={"technology": "coal_ppl"}))
        for row in result["rows"]:
            assert row["technology"] == "coal_ppl"
        assert result["total_shown"] == 4

    def test_filter_by_year_as_string(self, tools):
        # LLM may send year as string; should be coerced to int
        result = json.loads(tools.get_parameter("fix_cost", filters={"year_act": "2030"}))
        assert result["total_shown"] == 3  # 3 techs for year 2030

    def test_limit(self, tools):
        result = json.loads(tools.get_parameter("fix_cost", limit=2))
        assert result["total_shown"] == 2

    def test_unknown_parameter(self, tools):
        result = json.loads(tools.get_parameter("nonexistent"))
        assert "error" in result

    def test_no_scenario(self, no_scenario_tools):
        result = json.loads(no_scenario_tools.get_parameter("fix_cost"))
        assert "error" in result


# ---------------------------------------------------------------------------
# set_parameter_values
# ---------------------------------------------------------------------------

class TestSetParameterValues:
    def test_update_existing_row(self, tools, scenario):
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl",
             "year_vtg": 2030, "year_act": 2030, "value": 999.0}
        ])
        param = scenario.get_parameter("fix_cost")
        mask = (param.df["technology"] == "coal_ppl") & (param.df["year_act"] == 2030)
        assert param.df.loc[mask, "value"].iloc[0] == 999.0

    def test_update_marks_modified(self, tools, scenario):
        scenario.modified.clear()
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl",
             "year_vtg": 2030, "year_act": 2030, "value": 1.0}
        ])
        assert "fix_cost" in scenario.get_modified_parameters()

    def test_insert_new_row(self, tools, scenario):
        before = len(scenario.get_parameter("fix_cost").df)
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "new_tech",
             "year_vtg": 2020, "year_act": 2020, "value": 42.0}
        ])
        after = len(scenario.get_parameter("fix_cost").df)
        assert after == before + 1

    def test_summary_counts(self, tools):
        result = json.loads(tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl",
             "year_vtg": 2020, "year_act": 2020, "value": 1.0},
            {"node": "World", "technology": "new_tech",
             "year_vtg": 2020, "year_act": 2020, "value": 2.0},
        ]))
        assert result["updated"] == 1
        assert result["inserted"] == 1

    def test_year_coercion(self, tools, scenario):
        # LLM may send years as strings
        tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "gas_ppl",
             "year_vtg": "2040", "year_act": "2040", "value": 777.0}
        ])
        param = scenario.get_parameter("fix_cost")
        mask = (param.df["technology"] == "gas_ppl") & (param.df["year_act"] == 2040)
        assert param.df.loc[mask, "value"].iloc[0] == 777.0

    def test_emits_parameter_changed(self, tools, qtbot):
        with qtbot.waitSignal(tools.parameter_changed, timeout=1000) as blocker:
            tools.set_parameter_values("fix_cost", [
                {"node": "World", "technology": "coal_ppl",
                 "year_vtg": 2020, "year_act": 2020, "value": 5.0}
            ])
        assert blocker.args[0] == "fix_cost"

    def test_unknown_parameter_graceful(self, tools):
        result = json.loads(tools.set_parameter_values("nonexistent", [{"value": 1.0}]))
        assert "error" in result

    def test_no_scenario(self, no_scenario_tools):
        result = json.loads(no_scenario_tools.set_parameter_values("fix_cost", [{"value": 1.0}]))
        assert "error" in result

    def test_missing_value_key_reports_error(self, tools):
        result = json.loads(tools.set_parameter_values("fix_cost", [
            {"node": "World", "technology": "coal_ppl"}  # no 'value'
        ]))
        # Should succeed (0 updates) and report the error in 'errors' list
        assert result.get("status") == "ok"
        assert "errors" in result


# ---------------------------------------------------------------------------
# list_sets / get_set
# ---------------------------------------------------------------------------

class TestSets:
    def test_list_sets(self, tools):
        result = json.loads(tools.list_sets())
        names = [r["name"] for r in result]
        assert "technology" in names
        assert "node" in names

    def test_list_sets_sizes(self, tools):
        result = json.loads(tools.list_sets())
        tech = next(r for r in result if r["name"] == "technology")
        assert tech["size"] == 3

    def test_get_set_members(self, tools):
        result = json.loads(tools.get_set("technology"))
        assert "coal_ppl" in result["members"]

    def test_get_set_unknown(self, tools):
        result = json.loads(tools.get_set("nonexistent"))
        assert "error" in result

    def test_list_sets_no_scenario(self, no_scenario_tools):
        result = json.loads(no_scenario_tools.list_sets())
        assert "error" in result


# ---------------------------------------------------------------------------
# execute_python
# ---------------------------------------------------------------------------

class TestExecutePython:
    def test_basic_arithmetic(self, tools):
        result = json.loads(tools.execute_python("result = 2 + 2"))
        assert result["result"] == 4

    def test_numpy_linspace(self, tools):
        result = json.loads(tools.execute_python(
            "result = list(np.linspace(0, 10, 3))"
        ))
        assert result["result"] == [0.0, 5.0, 10.0]

    def test_stdout_captured(self, tools):
        result = json.loads(tools.execute_python("print('hello world')"))
        assert "hello world" in result["stdout"]

    def test_error_graceful(self, tools):
        result = json.loads(tools.execute_python("raise ValueError('bad input')"))
        assert "error" in result
        assert "ValueError" in result["error"]

    def test_none_result_by_default(self, tools):
        result = json.loads(tools.execute_python("x = 1 + 1"))
        assert result["result"] is None

    def test_numpy_array_serialised(self, tools):
        result = json.loads(tools.execute_python("result = np.array([1, 2, 3])"))
        assert result["result"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_routes_list_parameters(self, tools):
        result = json.loads(tools.dispatch("list_parameters", {}))
        assert isinstance(result, list)

    def test_routes_get_scenario_info(self, tools):
        result = json.loads(tools.dispatch("get_scenario_info", {}))
        assert "parameter_count" in result

    def test_unknown_tool_graceful(self, tools):
        result = json.loads(tools.dispatch("unknown_tool_xyz", {}))
        assert "error" in result

    def test_routes_execute_python(self, tools):
        result = json.loads(tools.dispatch("execute_python", {"code": "result = 42"}))
        assert result["result"] == 42


# ---------------------------------------------------------------------------
# AIBatchEditCommand
# ---------------------------------------------------------------------------

class TestAIBatchEditCommand:
    def test_do_updates_dataframe(self, scenario):
        param = scenario.get_parameter("fix_cost")
        old_df = param.df.copy()
        new_df = param.df.copy()
        new_df.loc[0, "value"] = -1.0

        cmd = AIBatchEditCommand(scenario, "fix_cost", old_df, new_df)
        assert cmd.do()
        assert param.df.loc[0, "value"] == -1.0

    def test_undo_restores_dataframe(self, scenario):
        param = scenario.get_parameter("fix_cost")
        original_val = param.df.loc[0, "value"]
        old_df = param.df.copy()
        new_df = param.df.copy()
        new_df.loc[0, "value"] = -1.0

        cmd = AIBatchEditCommand(scenario, "fix_cost", old_df, new_df)
        cmd.do()
        cmd.undo()
        assert param.df.loc[0, "value"] == original_val

    def test_do_marks_modified(self, scenario):
        scenario.modified.clear()
        param = scenario.get_parameter("fix_cost")
        cmd = AIBatchEditCommand(scenario, "fix_cost", param.df.copy(), param.df.copy())
        cmd.do()
        assert "fix_cost" in scenario.get_modified_parameters()
