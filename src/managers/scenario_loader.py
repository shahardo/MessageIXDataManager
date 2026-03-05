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
from core.message_ix_schema import MESSAGE_IX_SET_NAMES, MESSAGE_IX_PAR_NAMES
from managers.input_manager import InputManager
from managers.warning_analyzer import KNOWN_UNIT_MAP

logger = logging.getLogger(__name__)

# Sets that ixmp manages internally and must NOT be written by user code.
# ix_type_mapping: maps every registered item name → its ix_type ('set', 'par',
#   'var', 'equ'); ixmp auto-populates this whenever add_set/add_par is called.
#   Its 'item' column is not a registered ixmp set, so init_set would fail.
_IXMP_INTERNAL_SETS: frozenset = frozenset({
    "ix_type_mapping",
})


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
        #
        # 1-D sets must be added before mapping sets so that ixmp can
        # validate membership.  We also build a case-insensitive lookup
        # map so that mapping set values can be normalised to the exact
        # capitalisation used in the 1-D sets (e.g. 'ethanol' → 'Ethanol').
        # ------------------------------------------------------------------
        _log("  Adding sets...")

        # Separate into 1-D (Series) and mapping (DataFrame) sets, preserving
        # the original insertion order within each group.
        one_d_sets = {
            k: v for k, v in scenario_data.sets.items()
            if not isinstance(v, pd.DataFrame)
        }
        mapping_sets = {
            k: v for k, v in scenario_data.sets.items()
            if isinstance(v, pd.DataFrame)
        }

        # --- Pass 1: 1-D sets -----------------------------------------------
        # Build a case-insensitive lookup {set_name: {lower_value: canonical}}
        # as sets are successfully added.
        set_lookup: dict = {}  # set_name → {lowercase → canonical}

        for set_name, set_data in one_d_sets.items():
            if set_name in MESSAGE_IX_PAR_NAMES:
                _log(f"  Note: '{set_name}' is a parameter, not a set — "
                     "re-adding as parameter.")
                try:
                    df_par = set_data.to_frame(name="value")
                    df_par = ScenarioLoader._prepare_parameter_df(df_par, {})
                    if not df_par.empty:
                        scenario.add_par(set_name, df_par)
                except Exception as exc:
                    _log(f"  Warning: could not re-add '{set_name}' as parameter: {exc}")
                continue

            values = set_data.dropna().tolist()
            if not values:
                continue
            try:
                scenario.add_set(set_name, values)
            except Exception:
                # Set not yet declared in the schema — initialise it first,
                # then retry.  This handles custom/extension sets like 'sector'
                # that are not part of the standard MESSAGEix schema.
                try:
                    scenario.init_set(set_name)
                    scenario.add_set(set_name, values)
                except Exception as exc2:
                    _log(f"  Warning: could not add set '{set_name}': {exc2}")
                    continue
            # Record canonical casing for use when normalising mapping sets
            set_lookup[set_name] = {str(v).lower(): str(v) for v in values}

        # --- Pass 2: mapping sets -------------------------------------------
        for set_name, set_data in mapping_sets.items():
            if set_name in _IXMP_INTERNAL_SETS:
                # ixmp auto-manages these tables; writing them manually would
                # corrupt the platform's internal state.
                _log(f"  Skipping internal ixmp set '{set_name}'")
                continue

            if set_name in MESSAGE_IX_PAR_NAMES:
                _log(f"  Note: '{set_name}' is a parameter, not a set — "
                     "re-adding as parameter.")
                try:
                    df_par = ScenarioLoader._prepare_parameter_df(set_data, {})
                    if not df_par.empty:
                        scenario.add_par(set_name, df_par)
                except Exception as exc:
                    _log(f"  Warning: could not re-add '{set_name}' as parameter: {exc}")
                continue

            df_clean = set_data.dropna()
            if df_clean.empty:
                continue

            # Normalise each column's values to match the canonical casing of
            # the corresponding 1-D set (handles e.g. 'ethanol' vs 'Ethanol').
            df_clean = df_clean.copy()
            for col in df_clean.columns:
                if col in set_lookup:
                    lut = set_lookup[col]
                    df_clean[col] = df_clean[col].apply(
                        lambda v, lut=lut: lut.get(str(v).lower(), v)
                        if pd.notna(v) else v
                    )

            try:
                scenario.add_set(set_name, df_clean)
            except Exception:
                # Set not declared — initialise with its columns as index sets,
                # then retry.
                try:
                    cols = list(df_clean.columns)
                    scenario.init_set(set_name, cols, cols)
                    scenario.add_set(set_name, df_clean)
                except Exception as exc2:
                    _log(f"  Warning: could not add set '{set_name}': {exc2}")

        # ------------------------------------------------------------------
        # 4. Add parameters
        # ------------------------------------------------------------------
        _log("  Adding parameters...")
        for par_name, param in scenario_data.parameters.items():
            # Sanity-check: if the name is a known MESSAGEix set, the Excel
            # parser mis-routed it — reclassify and add as a set instead.
            if par_name in MESSAGE_IX_SET_NAMES:
                _log(f"  Note: '{par_name}' is a set, not a parameter — "
                     "re-adding as set.")
                try:
                    df_set = param.df.drop(
                        columns=[c for c in ("value", "unit") if c in param.df.columns]
                    ).dropna()
                    if not df_set.empty:
                        if len(df_set.columns) == 1:
                            scenario.add_set(par_name, df_set.iloc[:, 0].tolist())
                        else:
                            scenario.add_set(par_name, df_set)
                except Exception as exc:
                    _log(f"  Warning: could not re-add '{par_name}' as set: {exc}")
                continue

            try:
                df = ScenarioLoader._prepare_parameter_df(param.df, param.metadata)
                if df.empty:
                    continue
                scenario.add_par(par_name, df)
            except Exception as exc:
                exc_str = str(exc)
                # If ixmp rejected the unit(s), retry with the dimensionless
                # placeholder "-" so at least the data gets loaded.
                if "does not exist in the database" in exc_str and "unit" in exc_str.lower():
                    try:
                        bad_units = (
                            df["unit"].unique().tolist() if "unit" in df.columns else []
                        )
                        df = df.copy()
                        df["unit"] = "-"
                        scenario.add_par(par_name, df)
                        _log(
                            f"  Note: replaced unrecognized unit(s) {bad_units} "
                            f"in '{par_name}' with '-'"
                        )
                    except Exception as exc2:
                        _log(f"  Warning: could not add parameter '{par_name}': {exc2}")
                else:
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

        # Remap units that are known to be invalid in ixmp to their
        # correct equivalents so that the solver doesn't reject them.
        if "unit" in result.columns:
            for bad, good in KNOWN_UNIT_MAP.items():
                mask = result["unit"] == bad
                if mask.any():
                    logger.info(
                        "Auto-correcting unit '%s' → '%s' in parameter DataFrame",
                        bad, good,
                    )
                    result.loc[mask, "unit"] = good

        return result
