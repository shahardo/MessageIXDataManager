"""
Technology Classifier - Maps technologies to energy levels and provides grouping.

Builds technology-to-energy-level mappings by querying the `input` and `output`
parameters from the input scenario. Also provides technology grouping to aggregate
similar technologies (e.g., solar_pv + solar_res → "Solar PV").
"""

import re
import pandas as pd
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.data_models import ScenarioData


# ---------------------------------------------------------------------------
# Technology group mappings
# ---------------------------------------------------------------------------
# Each entry maps a display group name → list of technology name patterns.
# A technology matches if its name equals or starts with any pattern.
# Extracted and generalized from ResultsPostprocessor._get_technology_mappings()
# and helpers/message_relations.csv.

TECHNOLOGY_GROUPS = {
    # --- Main energy technologies (broad prefix groups) ---
    # Patterns ending with '_' match any continuation via prefix matching.
    # When "Group Technologies" is enabled, ALL technologies sharing a prefix
    # are lumped together (e.g., gas_cc + gas_ct + gas_ppl → "natural gas").
    "coal": ["coal_", "igcc", "lignite_"],
    "heavy fuel oil": ["foil_"],
    "light oil": ["loil_"],
    "natural gas": ["gas_"],
    "oil": ["oil_"],
    "nuclear": ["nuc_"],
    "hydro": ["hydro_"],
    "biomass": ["bio_"],
    "wind": ["wind_"],
    "solar": ["solar_", "csp_"],
    "geothermal": ["geo_"],
    "storage": ["stor_"],
    "hydrogen": ["h2_", "h2b_"],
    "electricity": ["elec_"],
    "refinery": ["ref_"],
    "synfuels": ["syn_", "meth_", "eth_", "liq_"],

    # --- Emissions & CO2 capture ---
    # Suffix patterns (_co2scr, _co2_scrub) are checked BEFORE prefix patterns
    # so that bio_ppl_co2scr → "CO2 scrubbing", not "biomass".
    "cement emissions": ["cement_"],
    "flaring emissions": ["flaring_"],
    "CO2 scrubbing": ["co2_tr", "bco2_", "_co2scr", "_co2_scrub", "mvac_co2"],

    # --- Emission species accounting ---
    # Technologies named after emission species (CO2_TCE, CH4_Emission, etc.)
    "CO2 emissions": ["CO2_"],
    "CH4 emissions": ["CH4_"],
    "N2O emissions": ["N2O_", "N2On_", "N2Oo"],
    "SO2 emissions": ["SO2_"],
    "SF6 emissions": ["SF6_"],
    "CF4 emissions": ["CF4_"],
    "HFC emissions": ["HFC_", "HFCo_", "HFCequiv"],
    "NOx emissions": ["NOx_"],
    "other emissions": ["BCA_", "OCA_", "VOC_", "NH3_", "PM2_", "CO_E"],
    "total emissions": ["TCE_", "TCH4_", "TCO2_", "TN2O_", "TSF6_", "TCF4_", "THFC_"],
    "emission mitigation": [
        "landfill_", "ent_red", "rice_red", "soil_red",
        "nitric_", "replacement_", "vertical_stud",
    ],

    # --- Trade (suffix patterns, checked before prefix) ---
    "imports": ["_imp"],
    "exports": ["_exp"],
}

# Patterns that should be treated as "emissions" level even if the
# input/output parameters assign them to another level.
# Covers: emission species prefixes (CO2_*, CH4_*, ...), total emission
# counters (TCE_*, TCO2_*, ...), *_TCE suffix, cement/flaring, CO2 capture,
# emission mitigation techs, and accounting link technologies.
_EMISSION_TECH_PATTERNS = re.compile(
    r"(?:"
    # Emission species prefixes (case-sensitive, uppercase species names)
    r"^(?:CO2|CH4|N2O|SO2|SF6|CF4|HFC|NOx|BCA|OCA|VOC|NH3|PM2|CO)_"
    # Total emission counters
    r"|^T(?:CE|CH4|CO2|N2O|SF6|CF4|HFC)_"
    # *_TCE suffix (Total Carbon Equivalent)
    r"|_TCE$"
    # Cement, flaring, forest emissions
    r"|^cement_|^flaring_|forest_CO2"
    # CO2 transport, scrubbing, capture
    r"|co2_tr|bco2_|_co2scr|_co2_scrub|mvac_co2"
    # SO2 reduction/scrubbing
    r"|^SO2_"
    # Emission mitigation technologies
    r"|^landfill_|^ent_red|^rice_red|^soil_red"
    r"|^nitric_|^replacement_|^vertical_stud"
    # Link technologies (emission accounting links)
    r"|Link$"
    # Emission factor patterns
    r"|_Emission"
    # N2O / HFC accounting variants
    r"|^N2On_|^N2Oo|^HFCo_|^HFCequiv"
    r"|^Ind(?:GDP|Therm)|^POP|^SolWa|^WasteGen"
    r")"
)


class TechnologyClassifier:
    """Maps technologies to energy levels and provides grouping utilities."""

    @staticmethod
    def build_level_technology_map(
        scenario: 'ScenarioData',
    ) -> Dict[str, List[str]]:
        """Build a mapping of energy level → list of technologies.

        Queries the ``output`` and ``input`` parameters from the input
        scenario to discover which technologies operate at each energy
        level (primary, secondary, final, useful, renewable, etc.).

        Also synthesises an **"emissions"** pseudo-level for emission
        accounting technologies (cement_CO2, flaring, CO2 scrubbers,
        etc.) that the model typically assigns to other levels.

        Args:
            scenario: Input ScenarioData containing ``output`` and
                ``input`` parameters with ``technology`` and ``level``
                columns.

        Returns:
            Dict mapping level name (str) → sorted list of technology
            names.  Returns empty dict if the parameters are missing.
        """
        level_map: Dict[str, set] = {}
        all_techs: set = set()

        # Query 'output' parameter for level → technology mapping
        output_param = scenario.get_parameter("output")
        if output_param is not None and not output_param.df.empty:
            _collect_levels(output_param.df, level_map, all_techs)

        # Query 'input' parameter – technologies that *consume* at a level
        input_param = scenario.get_parameter("input")
        if input_param is not None and not input_param.df.empty:
            _collect_levels(input_param.df, level_map, all_techs)

        # Synthesise an "emissions" pseudo-level from known patterns
        emissions_techs = {t for t in all_techs if _EMISSION_TECH_PATTERNS.search(t)}
        if emissions_techs:
            level_map.setdefault("emissions", set()).update(emissions_techs)
            # Remove these techs from other levels so they don't pollute
            for lvl, techs in level_map.items():
                if lvl != "emissions":
                    techs -= emissions_techs

        # Convert sets to sorted lists
        return {level: sorted(techs) for level, techs in sorted(level_map.items()) if techs}

    @staticmethod
    def get_technology_group_mappings() -> Dict[str, List[str]]:
        """Return the static technology group mapping.

        Returns:
            Dict mapping display group name → list of technology name
            patterns (prefixes).
        """
        return dict(TECHNOLOGY_GROUPS)

    @staticmethod
    def filter_by_energy_level(
        df: pd.DataFrame,
        level: str,
        level_tech_map: Dict[str, List[str]],
        tech_col: str = "technology",
    ) -> pd.DataFrame:
        """Filter a DataFrame to only include technologies at a given level.

        Args:
            df: DataFrame with a technology column.
            level: Energy level name (e.g. "primary", "secondary").
            level_tech_map: Mapping from ``build_level_technology_map()``.
            tech_col: Name of the technology column.

        Returns:
            Filtered DataFrame.  Returns empty DataFrame if the level
            is not in the map or the tech column is missing.
        """
        if tech_col not in df.columns:
            return df

        techs = level_tech_map.get(level, [])
        if not techs:
            return df.iloc[0:0]  # empty with same columns

        return df[df[tech_col].isin(techs)].copy()

    @staticmethod
    def apply_technology_grouping(
        df: pd.DataFrame,
        tech_col: str = "technology",
        value_col: str = "lvl",
    ) -> pd.DataFrame:
        """Replace individual technology names with group names and aggregate.

        Technologies matching a group pattern are renamed to the group
        display name.  Rows that share the same group + remaining
        dimensions are summed.  Technologies not matching any group
        keep their original name.

        Args:
            df: Raw DataFrame (pre-pivot) with a technology column.
            tech_col: Name of the technology column.
            value_col: Name of the numeric value column to aggregate.

        Returns:
            DataFrame with grouped technology names and aggregated
            values.
        """
        if df.empty or tech_col not in df.columns:
            return df

        result = df.copy()

        # Build reverse lookup: technology pattern → group name
        reverse_map = _build_reverse_group_map()

        # Map each technology to its group (or keep original)
        result[tech_col] = result[tech_col].apply(
            lambda t: _find_group(t, reverse_map)
        )

        # Determine which columns to group by (all non-value columns)
        # Exclude known value/marginal columns
        skip_cols = {value_col, "mrg", "value", "val"}
        group_cols = [
            c for c in result.columns
            if c not in skip_cols and c != value_col
        ]

        if not group_cols or value_col not in result.columns:
            return result

        # Aggregate: sum numeric values within each group
        try:
            grouped = (
                result.groupby(group_cols, as_index=False, dropna=False)
                .agg({value_col: "sum"})
            )
            return grouped
        except Exception:
            # Fallback: return with renamed techs but no aggregation
            return result


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _collect_levels(
    df: pd.DataFrame,
    level_map: Dict[str, set],
    all_techs: set,
) -> None:
    """Extract (level, technology) pairs from a DataFrame into *level_map*.

    Also populates *all_techs* with every technology encountered.
    Handles both ``technology`` and ``tec`` column names.
    """
    tech_col = "technology" if "technology" in df.columns else "tec" if "tec" in df.columns else None
    level_col = "level" if "level" in df.columns else None

    if tech_col is None or level_col is None:
        return

    for level_val, group in df.groupby(level_col):
        level_str = str(level_val).strip()
        if not level_str:
            continue
        if level_str not in level_map:
            level_map[level_str] = set()
        techs = set(group[tech_col].dropna().unique())
        level_map[level_str].update(techs)
        all_techs.update(techs)


def _build_reverse_group_map() -> Dict[str, str]:
    """Build a reverse mapping: technology pattern → group display name."""
    reverse = {}
    for group_name, patterns in TECHNOLOGY_GROUPS.items():
        for pattern in patterns:
            reverse[pattern] = group_name
    return reverse


def _find_group(tech_name: str, reverse_map: Dict[str, str]) -> str:
    """Find the group name for a technology, or return the original name.

    Matching rules (applied in order of priority):
    1. Exact match with a pattern.
    2. Suffix match — pattern starts with ``_`` and is contained in the
       tech name (e.g., ``_imp`` in ``gas_imp``).  Checked **before**
       prefix matching so that trade and CO2-scrubber techs are not
       swallowed by broad prefix groups.
    3. Prefix match — tech name starts with the pattern.  Patterns
       ending with ``_`` accept any continuation; other patterns require
       a word-boundary character (``_``, ``-``, or digit) after the
       pattern.

    Longer patterns are checked first within each pass to avoid
    partial mis-matches.
    """
    if not isinstance(tech_name, str):
        return tech_name

    sorted_patterns = sorted(reverse_map.keys(), key=len, reverse=True)

    # Pass 1: Exact match (longest-first)
    for pattern in sorted_patterns:
        if tech_name == pattern:
            return reverse_map[pattern]

    # Pass 2: Suffix patterns (higher priority than prefix)
    # e.g., _imp, _exp, _co2scr, _co2_scrub override broad prefixes
    for pattern in sorted_patterns:
        if pattern.startswith("_") and pattern in tech_name:
            return reverse_map[pattern]

    # Pass 3: Prefix match (longest-first)
    for pattern in sorted_patterns:
        if tech_name.startswith(pattern):
            next_pos = len(pattern)
            if next_pos >= len(tech_name):
                return reverse_map[pattern]
            # If the pattern itself ends with '_', any continuation is valid
            # (the underscore already acts as a word boundary).
            if pattern.endswith("_"):
                return reverse_map[pattern]
            next_char = tech_name[next_pos]
            if next_char in ('_', '-') or next_char.isdigit():
                return reverse_map[pattern]

    return tech_name
