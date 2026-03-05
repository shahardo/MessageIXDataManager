"""
ResultsExporter — writes a solved message_ix.Scenario's variables and
equations to an Excel workbook compatible with the existing ResultsAnalyzer.

Sheet naming follows the convention expected by ResultParsingStrategy:
- Variables  → sheets named ``var_<NAME>``
- Equations  → sheets named ``equ_<NAME>``

All available variables and equations are exported automatically, so the
sheet list adapts to whatever the solver produced without needing a
hardcoded allowlist.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Standard MESSAGEix variables and equations to export.
# These are exported first (in this order) so the most important sheets
# appear near the front of the workbook.  Any additional var/equ found on
# the scenario are appended afterwards.
_PRIMARY_VARIABLES: List[str] = [
    "ACT",
    "CAP",
    "CAP_NEW",
    "EMISS",
    "COST_NODAL",
    "COST_NODAL_NET",
    "PRICE_COMMODITY",
    "PRICE_EMISSION",
    "EXT",
    "STOCK",
    "LAND",
    "STORAGE_CHARGE",
    # STORAGE_CONTENT is only present in models with storage; omit from the
    # primary list to avoid a noisy warning on every standard run.
]

_PRIMARY_EQUATIONS: List[str] = [
    "COMMODITY_BALANCE_GT",
    "COMMODITY_BALANCE_LT",
    "RESOURCE_HORIZON",
]


class ResultsExporter:
    """
    Static helper that exports a solved message_ix.Scenario to Excel.
    """

    @staticmethod
    def export_to_excel(
        scenario: Any,
        output_path: str,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Export all variables and equations from a solved scenario to Excel.

        Args:
            scenario:    A ``message_ix.Scenario`` that has been solved.
            output_path: Absolute path for the output ``.xlsx`` file.
            log_fn:      Optional callable(str) for progress messages.

        Returns:
            The output_path that was written.

        Raises:
            Exception: If the Excel file cannot be written.
        """
        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)
            logger.info(msg)

        # ------------------------------------------------------------------
        # Collect all variable and equation names available on this scenario
        # ------------------------------------------------------------------
        all_var_names: List[str] = ResultsExporter._collect_names(
            scenario, "var_list", _PRIMARY_VARIABLES, _log
        )
        all_equ_names: List[str] = ResultsExporter._collect_names(
            scenario, "equ_list", _PRIMARY_EQUATIONS, _log
        )

        _log(f"  Exporting {len(all_var_names)} variable(s) and "
             f"{len(all_equ_names)} equation(s)...")

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            written = 0

            for var_name in all_var_names:
                written += ResultsExporter._write_sheet(
                    writer, scenario, "var", var_name, _log
                )

            for equ_name in all_equ_names:
                written += ResultsExporter._write_sheet(
                    writer, scenario, "equ", equ_name, _log
                )

        _log(f"  Wrote {written} sheet(s) to {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_names(
        scenario: Any,
        list_attr: str,
        primary: List[str],
        log_fn: Callable[[str], None],
    ) -> List[str]:
        """
        Build an ordered list of names to export.

        Primary names come first (in the given order), then any additional
        names discovered on the scenario, deduplicating throughout.
        """
        try:
            available = list(getattr(scenario, list_attr)())
        except Exception as exc:
            log_fn(f"  Warning: could not query {list_attr}: {exc}")
            available = []

        available_set = set(available)

        # Primary names first (only those that actually exist), then any extras.
        seen: set = set()
        ordered: list = []
        for name in primary:
            if name in available_set and name not in seen:
                seen.add(name)
                ordered.append(name)
        for name in available:
            if name not in seen:
                seen.add(name)
                ordered.append(name)

        return ordered

    @staticmethod
    def _write_sheet(
        writer: pd.ExcelWriter,
        scenario: Any,
        kind: str,           # 'var' or 'equ'
        name: str,
        log_fn: Callable[[str], None],
    ) -> int:
        """
        Fetch one variable/equation from the scenario and write it as a sheet.

        Returns 1 if the sheet was written, 0 if it was empty or raised an error.
        """
        sheet_name = f"{kind}_{name}"
        fetch_fn = getattr(scenario, kind, None)
        if fetch_fn is None:
            return 0

        try:
            df = fetch_fn(name)
        except Exception as exc:
            log_fn(f"  Warning: could not fetch {sheet_name}: {exc}")
            return 0

        if df is None:
            return 0

        # ixmp returns a plain dict {lvl: value, mrg: value} for scalar
        # variables / equations; wrap it so the rest of the code sees a DataFrame.
        if isinstance(df, dict):
            df = pd.DataFrame([df])

        if not isinstance(df, pd.DataFrame) or df.empty:
            return 0

        # Excel sheet names are limited to 31 characters
        safe_sheet = sheet_name[:31]

        df.to_excel(writer, sheet_name=safe_sheet, index=False)
        return 1
