"""
WarningAnalyzer — parses and classifies warning lines emitted by the
MESSAGEix solver subprocess (scenario_loader.py) and suggests fixes.

Warning lines from scenario_loader.py follow these patterns:
    "  Warning: could not add set 'name': <exception message>"
    "  Warning: could not add parameter 'name': <exception message>"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Known unit mappings: bad unit → suggested valid ixmp unit
# ---------------------------------------------------------------------------
KNOWN_UNIT_MAP: dict[str, str] = {
    # Scaling words / scientific notation — ixmp does not accept these as units
    "million":       "-",
    "Million":       "-",
    "billion":       "-",
    "Billion":       "-",
    "1e3":           "-",
    "1e6":           "-",
    "1e9":           "-",
    "1E3":           "-",
    "1E6":           "-",
    "1E9":           "-",
    # Common energy / power units — already valid in ixmp, listed for completeness
    "GW":            "GW",
    "MW":            "MW",
    "kW":            "kW",
    "GWa":           "GWa",
    "MWa":           "MWa",
    "kWa":           "kWa",
    "GWh":           "GWh",
    "MWh":           "MWh",
    "kWh":           "kWh",
    "EJ":            "EJ",
    "PJ":            "PJ",
    "TJ":            "TJ",
    "GJ":            "GJ",
    "MJ":            "MJ",
    "ktoe":          "ktoe",
    "Mtoe":          "Mtoe",
    # Currency
    "USD":           "USD",
    "kUSD":          "kUSD",
    "MUSD":          "MUSD",
    # Mass / emissions
    "Mt":            "Mt CO2", # often means megatonne CO2
    "tCO2":          "tCO2",
    "MtCO2":         "MtCO2",
    # Dimensionless variants
    "%":             "%",
    "percent":       "%",
    "fraction":      "-",
    "unitless":      "-",
    "dimensionless": "-",
    "none":          "-",
    "None":          "-",
    "NA":            "-",
    "N/A":           "-",
    # Time
    "year":          "year",
    "years":         "year",
    "yr":            "year",
}

# ---------------------------------------------------------------------------
# Warning categories
# ---------------------------------------------------------------------------
CATEGORY_UNIT_NOT_FOUND  = "unit_not_found"
CATEGORY_NO_VALUES       = "no_values"
CATEGORY_DUPLICATE       = "duplicate"
CATEGORY_UNKNOWN         = "unknown"

# Human-readable labels for display
CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_UNIT_NOT_FOUND: "Invalid unit",
    CATEGORY_NO_VALUES:      "No values",
    CATEGORY_DUPLICATE:      "Duplicate entries",
    CATEGORY_UNKNOWN:        "Other error",
}

# Regex that matches both set and parameter warning lines from scenario_loader
_WARNING_RE = re.compile(
    r"\s*Warning:\s+could not add\s+(set|parameter)\s+'([^']+)':\s*(.*)",
    re.IGNORECASE,
)

# Regex to extract the bad unit from the exception message
_UNIT_RE = re.compile(
    r"unit\s+'([^']+)'|'([^']+)'\s+does not exist",
    re.IGNORECASE,
)


@dataclass
class SolverWarning:
    """Represents a single parsed warning from the solver output."""
    kind: str           # "parameter" | "set" | "unknown"
    name: str           # parameter / set name
    raw_message: str    # full original line
    exception_text: str # the exception part after the colon
    category: str = CATEGORY_UNKNOWN
    fix_description: str = ""
    fix_available: bool = False
    # For unit fixes: the bad unit and its suggested replacement
    bad_unit: str = ""
    good_unit: str = ""


class WarningAnalyzer:
    """
    Parses raw solver output lines into SolverWarning objects,
    classifies them, and suggests fixes.
    """

    @staticmethod
    def parse_line(line: str) -> Optional[SolverWarning]:
        """
        Try to parse a single output line as a solver warning.

        Returns a SolverWarning if the line matches, otherwise None.
        """
        m = _WARNING_RE.match(line)
        if not m:
            return None

        kind = m.group(1).lower()          # "set" or "parameter"
        name = m.group(2)                  # e.g. "bound_activity_lo"
        exception_text = m.group(3).strip()

        warning = SolverWarning(
            kind=kind,
            name=name,
            raw_message=line.rstrip(),
            exception_text=exception_text,
        )
        WarningAnalyzer._classify(warning)
        return warning

    @staticmethod
    def _classify(warning: SolverWarning) -> None:
        """Fill in category, fix_description, fix_available, bad/good unit."""
        exc = warning.exception_text.lower()

        # --- Unit not found ---------------------------------------------------
        if "does not exist in the database" in exc or "unit" in exc and "not" in exc:
            warning.category = CATEGORY_UNIT_NOT_FOUND
            # Try to extract the bad unit from the exception text
            um = _UNIT_RE.search(warning.exception_text)
            bad = um.group(1) or um.group(2) if um else ""
            good = KNOWN_UNIT_MAP.get(bad, "")
            warning.bad_unit = bad
            warning.good_unit = good
            if good:
                warning.fix_description = (
                    f"Unit '{bad}' is not recognised by ixmp. "
                    f"Suggested replacement: '{good}'. "
                    "Use 'Auto-fix Unit' or edit the 'unit' column manually."
                )
                warning.fix_available = True
            else:
                warning.fix_description = (
                    f"Unit '{bad}' is not recognised by ixmp. "
                    "Open the parameter and correct the 'unit' column to a "
                    "valid ixmp unit (e.g. 'GWh', 'Mt CO2', '-', '1')."
                )
                warning.fix_available = False

        # --- No values --------------------------------------------------------
        elif "no parameter values" in exc or "empty" in exc:
            warning.category = CATEGORY_NO_VALUES
            warning.fix_description = (
                "The parameter sheet contains no data rows, or this is a "
                "MESSAGEix mapping set (e.g. balance_equality, cat_emission) "
                "that was incorrectly parsed as a parameter. Check whether "
                "this name is a set — if so, its Excel sheet should contain "
                "only string columns (no numeric value column). Otherwise, "
                "add data rows or remove the sheet."
            )
            warning.fix_available = False

        # --- Duplicates -------------------------------------------------------
        elif "duplicate" in exc:
            warning.category = CATEGORY_DUPLICATE
            warning.fix_description = (
                "The parameter contains duplicate index combinations. "
                "Open the parameter in the table view and remove duplicate rows."
            )
            warning.fix_available = False

        # --- Unknown ----------------------------------------------------------
        else:
            warning.category = CATEGORY_UNKNOWN
            warning.fix_description = (
                f"An unexpected error occurred: {warning.exception_text}. "
                "Open the parameter to inspect the data."
            )
            warning.fix_available = False

    @staticmethod
    def category_label(category: str) -> str:
        """Return a human-readable label for a category constant."""
        return CATEGORY_LABELS.get(category, "Other error")
