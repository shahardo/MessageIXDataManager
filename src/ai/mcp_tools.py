"""
MCP tool layer for the AI assistant.

Wraps ScenarioData read/write operations as Anthropic tool_use functions
so the LLM can read and modify MESSAGEix scenario parameters.
"""

import io
import json
import math
import sys
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal

from core.data_models import ScenarioData
from managers.commands import Command


# ---------------------------------------------------------------------------
# Undo command — snapshot-based for bulk AI edits
# ---------------------------------------------------------------------------

class AIBatchEditCommand(Command):
    """Undo/redo command that snapshots a parameter DataFrame before/after AI edits.

    Using full-DataFrame snapshots (rather than per-cell EditCellCommand) is
    necessary because AI edits may add new rows or change many cells at once.
    """

    def __init__(self, scenario: ScenarioData, param_name: str,
                 old_df: pd.DataFrame, new_df: pd.DataFrame):
        super().__init__(f"AI edit {param_name}")
        self.scenario = scenario
        self.param_name = param_name
        self.old_df = old_df.copy()
        self.new_df = new_df.copy()

    def do(self) -> bool:
        param = self.scenario.get_parameter(self.param_name)
        if param is None:
            return False
        param.df = self.new_df.copy()
        self.scenario.mark_modified(self.param_name)
        return True

    def undo(self) -> bool:
        param = self.scenario.get_parameter(self.param_name)
        if param is None:
            return False
        param.df = self.old_df.copy()
        self.scenario.mark_modified(self.param_name)
        return True


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic input_schema format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_scenario_info",
        "description": (
            "Get an overview of the currently loaded scenario: parameter count, "
            "set count, year range, and scenario options."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_parameters",
        "description": (
            "List all parameters in the scenario with their dimensions, units, "
            "shape (rows × cols), and short description."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_parameter",
        "description": (
            "Return data rows from a parameter. Optionally filter by dimension "
            "values and limit the number of rows returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
                "filters": {
                    "type": "object",
                    "description": "Dict of column_name → value to filter rows",
                    "additionalProperties": {"type": "string"},
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return (default 200)",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "set_parameter_values",
        "description": (
            "Set values in a parameter. Each entry in 'rows' is a dict that "
            "identifies a row by its dimension values plus a 'value' key with "
            "the new numeric value. Existing matching rows are updated; "
            "non-matching rows are inserted."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Parameter name"},
                "rows": {
                    "type": "array",
                    "description": (
                        "List of dicts. Each dict contains dimension column keys "
                        "identifying the row, plus a 'value' key for the new value."
                    ),
                    "items": {"type": "object"},
                },
            },
            "required": ["name", "rows"],
        },
    },
    {
        "name": "list_sets",
        "description": "List all sets in the scenario with their sizes.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_set",
        "description": "Return the members of a specific set.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Set name"}},
            "required": ["name"],
        },
    },
    {
        "name": "execute_python",
        "description": (
            "Execute Python code for calculations. "
            "numpy (as np) and pandas (as pd) are available. "
            "Assign the variable 'result' to return a value. "
            "Use this for: np.linspace(), unit conversions, interpolation, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
            },
            "required": ["code"],
        },
    },
]

# Groq / OpenAI-compatible format — generated from the Anthropic definitions above.
TOOL_DEFINITIONS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOL_DEFINITIONS
]


# ---------------------------------------------------------------------------
# MCPTools
# ---------------------------------------------------------------------------

class MCPTools(QObject):
    """Exposes ScenarioData as Anthropic tool_use callable functions.

    All tool methods return JSON strings (required by the Anthropic tool_result API).

    Signals:
        parameter_changed(str): Emitted after set_parameter_values with the
            parameter name.  Connected to the UI to refresh the displayed table.
    """

    parameter_changed = pyqtSignal(str)

    def __init__(
        self,
        scenario_accessor: Callable[[], Optional[ScenarioData]],
        undo_manager_accessor: Callable[[], Any],
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._scenario_accessor = scenario_accessor
        self._undo_manager_accessor = undo_manager_accessor

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, tool_name: str, tool_input: dict) -> str:
        """Route an Anthropic tool_use call to the correct method."""
        dispatch_map = {
            "get_scenario_info": lambda: self.get_scenario_info(),
            "list_parameters": lambda: self.list_parameters(),
            "get_parameter": lambda: self.get_parameter(**tool_input),
            "set_parameter_values": lambda: self.set_parameter_values(**tool_input),
            "list_sets": lambda: self.list_sets(),
            "get_set": lambda: self.get_set(**tool_input),
            "execute_python": lambda: self.execute_python(**tool_input),
        }
        handler = dispatch_map.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            return handler()
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    # ------------------------------------------------------------------
    # Tool: get_scenario_info
    # ------------------------------------------------------------------

    def get_scenario_info(self) -> str:
        """Return overview of the loaded scenario."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        return json.dumps({
            "parameter_count": len(scenario.parameters),
            "set_count": len(scenario.sets),
            "min_year": scenario.options.get("MinYear"),
            "max_year": scenario.options.get("MaxYear"),
            "modified_parameters": scenario.get_modified_parameters(),
        })

    # ------------------------------------------------------------------
    # Tool: list_parameters
    # ------------------------------------------------------------------

    def list_parameters(self) -> str:
        """Return list of all parameters with metadata."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        result = []
        for name in sorted(scenario.get_parameter_names()):
            param = scenario.get_parameter(name)
            if param is None:
                continue
            meta = param.metadata or {}
            result.append({
                "name": name,
                "dims": meta.get("dims", []),
                "units": meta.get("units", ""),
                "desc": meta.get("desc", ""),
                "shape": list(param.df.shape),
            })
        return json.dumps(result)

    # ------------------------------------------------------------------
    # Tool: get_parameter
    # ------------------------------------------------------------------

    def get_parameter(self, name: str, filters: Optional[dict] = None,
                      limit: int = 200) -> str:
        """Return rows from a parameter, optionally filtered."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        param = scenario.get_parameter(name)
        if param is None:
            return json.dumps({"error": f"Parameter '{name}' not found. "
                               f"Use list_parameters to see available names."})
        df = param.df.copy()
        if filters:
            for col, val in filters.items():
                if col not in df.columns:
                    continue
                dtype = df[col].dtype
                if pd.api.types.is_integer_dtype(dtype):
                    val = int(val)
                elif pd.api.types.is_float_dtype(dtype):
                    val = float(val)
                df = df[df[col] == val]
        df = df.head(limit)
        # Convert to JSON-serialisable dict
        rows = df.where(pd.notnull(df), None).to_dict(orient="records")
        return json.dumps({"name": name, "rows": rows, "total_shown": len(rows)})

    # ------------------------------------------------------------------
    # Tool: set_parameter_values
    # ------------------------------------------------------------------

    def set_parameter_values(self, name: str, rows: list) -> str:
        """Update or insert rows in a parameter, with undo/redo support."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        param = scenario.get_parameter(name)
        if param is None:
            return json.dumps({"error": f"Parameter '{name}' not found."})

        value_col = param.metadata.get("value_column", "value")
        old_df = param.df.copy()
        new_df = old_df.copy()

        updated = 0
        inserted = 0
        errors = []

        for row_dict in rows:
            row_dict = {str(k): v for k, v in row_dict.items()}
            # Extract the new value
            if "value" in row_dict:
                raw_value = row_dict.pop("value")
            elif value_col in row_dict:
                raw_value = row_dict.pop(value_col)
            else:
                errors.append(f"Row missing 'value' key: {row_dict}")
                continue

            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                errors.append(f"Cannot convert value to float: {raw_value!r}")
                continue

            # Coerce dimension values to match DataFrame column dtypes
            dim_dict = self._coerce_dims(row_dict, new_df)

            # Build boolean mask over all provided dimension columns
            mask = pd.Series([True] * len(new_df), index=new_df.index)
            for col, val in dim_dict.items():
                if col in new_df.columns:
                    mask = mask & (new_df[col] == val)

            matching = new_df[mask]
            if len(matching) > 0:
                new_df.loc[mask, value_col] = value
                updated += len(matching)
            else:
                new_row = {**dim_dict, value_col: value}
                new_df = pd.concat([new_df, pd.DataFrame([new_row])],
                                   ignore_index=True)
                inserted += 1

        # Apply via undo-able command
        cmd = AIBatchEditCommand(scenario, name, old_df, new_df)
        undo_mgr = self._undo_manager_accessor()
        if undo_mgr is not None:
            undo_mgr.execute(cmd)
        else:
            cmd.do()

        self.parameter_changed.emit(name)

        summary = f"Updated {updated} rows, inserted {inserted} rows in '{name}'"
        result: dict = {"status": "ok", "updated": updated, "inserted": inserted,
                        "summary": summary}
        if errors:
            result["errors"] = errors
        return json.dumps(result)

    @staticmethod
    def _coerce_dims(dim_dict: dict, df: pd.DataFrame) -> dict:
        """Coerce dimension values to match the DataFrame column dtypes."""
        coerced = {}
        for col, val in dim_dict.items():
            if col in df.columns:
                dtype = df[col].dtype
                try:
                    if pd.api.types.is_integer_dtype(dtype):
                        val = int(val)
                    elif pd.api.types.is_float_dtype(dtype):
                        val = float(val)
                    else:
                        val = str(val)
                except (TypeError, ValueError):
                    val = str(val)
            coerced[col] = val
        return coerced

    # ------------------------------------------------------------------
    # Tool: list_sets
    # ------------------------------------------------------------------

    def list_sets(self) -> str:
        """Return list of all sets with their sizes."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        result = []
        for name, data in sorted(scenario.sets.items()):
            if isinstance(data, pd.DataFrame):
                size = len(data)
            elif isinstance(data, pd.Series):
                size = len(data)
            else:
                size = 0
            result.append({"name": name, "size": size})
        return json.dumps(result)

    # ------------------------------------------------------------------
    # Tool: get_set
    # ------------------------------------------------------------------

    def get_set(self, name: str) -> str:
        """Return the members of a set."""
        scenario = self._scenario_accessor()
        if scenario is None:
            return json.dumps({"error": "No scenario loaded"})
        if name not in scenario.sets:
            return json.dumps({"error": f"Set '{name}' not found."})
        data = scenario.sets[name]
        if isinstance(data, pd.Series):
            members = data.tolist()
        elif isinstance(data, pd.DataFrame):
            # Multi-column mapping set — return as list of dicts
            members = data.to_dict(orient="records")
        else:
            members = []
        return json.dumps({"name": name, "members": members})

    # ------------------------------------------------------------------
    # Tool: execute_python
    # ------------------------------------------------------------------

    def execute_python(self, code: str) -> str:
        """Execute Python code for calculations and return stdout + result."""
        stdout_buf = io.StringIO()
        namespace: dict = {
            "np": np,
            "pd": pd,
            "math": math,
            "result": None,
        }
        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            exec(code, namespace)  # noqa: S102
            output = stdout_buf.getvalue()
            result = namespace.get("result")
            # Convert numpy/pandas objects to JSON-serialisable types
            result = self._to_json_serialisable(result)
            return json.dumps({"stdout": output, "result": result})
        except Exception as exc:
            output = stdout_buf.getvalue()
            return json.dumps({
                "error": f"{type(exc).__name__}: {exc}",
                "stdout": output,
            })
        finally:
            sys.stdout = old_stdout

    @staticmethod
    def _to_json_serialisable(obj: Any) -> Any:
        """Recursively convert numpy/pandas types to plain Python."""
        if obj is None:
            return None
        if isinstance(obj, (bool, int, float, str)):
            return obj
        if hasattr(obj, "tolist"):          # numpy array / scalar
            return obj.tolist()
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        if isinstance(obj, pd.Series):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: MCPTools._to_json_serialisable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [MCPTools._to_json_serialisable(v) for v in obj]
        return obj
