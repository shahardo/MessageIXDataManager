"""
ScenarioLoader — converts a MESSAGEix input Excel file into a
message_ix.Scenario stored in an ixmp Platform.

The InputManager is used to parse the Excel workbook into ScenarioData
(sets + Parameter objects).  The resulting data is then written into the
ixmp Scenario using the standard ixmp API (add_set / add_par).

Column-name conventions in our Parameter DataFrames already match the ixmp
parameter index conventions (one column per dimension, plus a 'value'
column), so minimal transformation is required.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import pandas as pd

from core.data_models import ScenarioData
from managers.input_manager import InputManager

logger = logging.getLogger(__name__)


class ScenarioLoader:
    """
    Static helper that loads an input Excel file into an ixmp Platform as a
    message_ix.Scenario ready for solving.
    """

    @staticmethod
    def load_from_excel(
        platform: Any,
        input_file: str,
        model_name: str,
        scenario_name: str,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> Any:
        """
        Parse the input Excel file and populate a new message_ix.Scenario.

        Args:
            platform:       An open ``ixmp.Platform`` instance.
            input_file:     Absolute path to the MESSAGEix input Excel file.
            model_name:     MESSAGEix model name string.
            scenario_name:  MESSAGEix scenario name string.
            log_fn:         Optional callable(str) for progress messages.

        Returns:
            A ``message_ix.Scenario`` that has been committed and is ready
            for ``scenario.solve()``.

        Raises:
            ImportError:  If message_ix is not installed.
            ValueError:   If the Excel file cannot be parsed.
            Exception:    Any ixmp / message_ix error during data loading.
        """
        import message_ix

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)
            logger.info(msg)

        # ------------------------------------------------------------------
        # 1. Parse the Excel workbook into ScenarioData
        # ------------------------------------------------------------------
        _log(f"Parsing input Excel: {input_file}")
        manager = InputManager()
        try:
            scenario_data: ScenarioData = manager.load_excel_file(input_file)
        except Exception as exc:
            raise ValueError(f"Cannot parse input Excel '{input_file}': {exc}") from exc

        _log(f"  Loaded {len(scenario_data.sets)} sets, "
             f"{len(scenario_data.parameters)} parameters")

        # ------------------------------------------------------------------
        # 2. Create a new message_ix.Scenario in the Platform
        # ------------------------------------------------------------------
        _log(f"Creating ixmp Scenario '{model_name}' / '{scenario_name}'...")
        scenario = message_ix.Scenario(
            platform,
            model=model_name,
            scenario=scenario_name,
            version="new",
            # version="new" already puts the scenario in edit mode;
            # check_out() must NOT be called here (it requires a committed version).
        )

        # ------------------------------------------------------------------
        # 3. Add sets
        # ------------------------------------------------------------------
        _log("  Adding sets...")
        for set_name, set_series in scenario_data.sets.items():
            try:
                values = set_series.dropna().tolist()
                if not values:
                    continue
                scenario.add_set(set_name, values)
            except Exception as exc:
                _log(f"  Warning: could not add set '{set_name}': {exc}")

        # ------------------------------------------------------------------
        # 4. Add parameters
        # ------------------------------------------------------------------
        _log("  Adding parameters...")
        for par_name, param in scenario_data.parameters.items():
            try:
                df = ScenarioLoader._prepare_parameter_df(param.df, param.metadata)
                if df.empty:
                    continue
                scenario.add_par(par_name, df)
            except Exception as exc:
                _log(f"  Warning: could not add parameter '{par_name}': {exc}")

        # ------------------------------------------------------------------
        # 5. Commit
        # ------------------------------------------------------------------
        _log("Committing scenario...")
        scenario.commit("Loaded from Excel via MessageIX Data Manager")

        _log("Scenario ready for solving.")
        return scenario

    @staticmethod
    def _prepare_parameter_df(df: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Ensure the DataFrame is in the format expected by ixmp add_par().

        ixmp expects:
        - One column per index dimension (matching the parameter's dims list)
        - A 'value' column with numeric values
        - Optionally a 'unit' column (defaults to the metadata unit or '-')

        Our internal format already uses 'value' as the value column, so we
        mainly need to ensure 'unit' is present and drop any internal columns
        that ixmp does not recognise.
        """
        result = df.copy()

        # Add unit column if absent
        if "unit" not in result.columns:
            unit = metadata.get("units", "-") or "-"
            result["unit"] = unit

        # Drop any auxiliary columns that are not part of the ixmp schema
        internal_cols = {"result_type", "description"}
        result = result.drop(
            columns=[c for c in internal_cols if c in result.columns]
        )

        # Drop rows where value is NaN
        if "value" in result.columns:
            result = result.dropna(subset=["value"])

        return result
