"""Tests for TechnologyClassifier utility."""

import pandas as pd
import pytest
from unittest.mock import MagicMock

from utils.technology_classifier import (
    TechnologyClassifier,
    _build_reverse_group_map,
    _find_group,
    _collect_levels,
    TECHNOLOGY_GROUPS,
    _EMISSION_TECH_PATTERNS,
)
from core.data_models import Parameter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_output_df():
    """Output parameter DataFrame with technology, level, commodity columns."""
    return pd.DataFrame({
        "node_loc": ["R11_AFR"] * 12,
        "technology": [
            "coal_extr", "gas_extr_1",          # primary
            "coal_ppl", "gas_cc",                # secondary
            "elec_trp", "gas_rc",                # final
            "solar_pv", "wind_ppl",              # secondary (renewables)
            "cement_CO2", "flaring_CO2",         # emission techs (assigned to secondary)
            "CH4_TCE", "CO2_TCE",                # emission accounting (assigned to secondary)
        ],
        "level": [
            "primary", "primary",
            "secondary", "secondary",
            "final", "final",
            "secondary", "secondary",
            "secondary", "secondary",
            "secondary", "secondary",
        ],
        "commodity": [
            "coal", "gas",
            "electr", "electr",
            "transport", "rc_spec",
            "electr", "electr",
            "electr", "electr",
            "GHGs", "GHGs",
        ],
        "value": [1.0] * 12,
    })


@pytest.fixture
def sample_input_df():
    """Input parameter DataFrame – renewable level technologies."""
    return pd.DataFrame({
        "node_loc": ["R11_AFR"] * 4,
        "technology": ["solar_pv", "wind_ppl", "solar_res", "hydro_lc"],
        "level": ["renewable", "renewable", "renewable", "renewable"],
        "commodity": ["solar", "wind", "solar", "water"],
        "value": [1.0] * 4,
    })


@pytest.fixture
def mock_scenario(sample_output_df, sample_input_df):
    """Mock ScenarioData with output and input parameters."""
    scenario = MagicMock()

    def get_parameter(name):
        if name == "output":
            return Parameter("output", sample_output_df, {})
        elif name == "input":
            return Parameter("input", sample_input_df, {})
        return None

    scenario.get_parameter = get_parameter
    return scenario


@pytest.fixture
def sample_var_act_df():
    """Sample var_act DataFrame for testing grouping and filtering."""
    return pd.DataFrame({
        "node_loc": ["R11_AFR"] * 10,
        "technology": [
            "coal_ppl", "coal_adv", "gas_cc", "gas_ppl",
            "solar_pv", "solar_res", "wind_ppl", "wind_res",
            "nuc_hc", "hydro_lc",
        ],
        "year_act": [2030] * 10,
        "mode": ["M1"] * 10,
        "lvl": [100.0, 50.0, 200.0, 80.0, 120.0, 30.0, 90.0, 10.0, 150.0, 60.0],
    })


# ---------------------------------------------------------------------------
# Tests: build_level_technology_map
# ---------------------------------------------------------------------------

class TestBuildLevelTechnologyMap:
    def test_basic_mapping(self, mock_scenario):
        """Levels and technologies are correctly extracted."""
        result = TechnologyClassifier.build_level_technology_map(mock_scenario)

        assert "primary" in result
        assert "secondary" in result
        assert "final" in result
        assert "renewable" in result

        assert "coal_extr" in result["primary"]
        assert "gas_extr_1" in result["primary"]
        assert "coal_ppl" in result["secondary"]
        assert "gas_cc" in result["secondary"]
        assert "solar_pv" in result["renewable"]
        assert "wind_ppl" in result["renewable"]

    def test_emissions_level_synthesised(self, mock_scenario):
        """Emission techs are moved to a synthetic 'emissions' level."""
        result = TechnologyClassifier.build_level_technology_map(mock_scenario)

        assert "emissions" in result
        assert "cement_CO2" in result["emissions"]
        assert "flaring_CO2" in result["emissions"]
        assert "CH4_TCE" in result["emissions"]
        assert "CO2_TCE" in result["emissions"]
        # They should NOT remain in secondary
        assert "cement_CO2" not in result.get("secondary", [])
        assert "flaring_CO2" not in result.get("secondary", [])
        assert "CH4_TCE" not in result.get("secondary", [])
        assert "CO2_TCE" not in result.get("secondary", [])

    def test_technologies_sorted(self, mock_scenario):
        """Technology lists are sorted alphabetically."""
        result = TechnologyClassifier.build_level_technology_map(mock_scenario)
        for level, techs in result.items():
            assert techs == sorted(techs), f"Techs for level '{level}' are not sorted"

    def test_levels_sorted(self, mock_scenario):
        """Level keys are sorted alphabetically."""
        result = TechnologyClassifier.build_level_technology_map(mock_scenario)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_empty_scenario(self):
        """Empty scenario returns empty mapping."""
        scenario = MagicMock()
        scenario.get_parameter.return_value = None
        result = TechnologyClassifier.build_level_technology_map(scenario)
        assert result == {}

    def test_missing_output_param(self, sample_input_df):
        """Works with only input parameter (no output)."""
        scenario = MagicMock()

        def get_parameter(name):
            if name == "input":
                return Parameter("input", sample_input_df, {})
            return None

        scenario.get_parameter = get_parameter
        result = TechnologyClassifier.build_level_technology_map(scenario)
        assert "renewable" in result
        assert "primary" not in result

    def test_empty_dataframe(self):
        """Empty DataFrames produce empty mapping."""
        scenario = MagicMock()
        scenario.get_parameter.return_value = Parameter("output", pd.DataFrame(), {})
        result = TechnologyClassifier.build_level_technology_map(scenario)
        assert result == {}

    def test_technology_appears_in_multiple_levels(self):
        """A technology can appear in multiple levels."""
        df = pd.DataFrame({
            "technology": ["tech_a", "tech_a", "tech_b"],
            "level": ["primary", "secondary", "secondary"],
            "value": [1.0, 1.0, 1.0],
        })
        scenario = MagicMock()

        def get_parameter(name):
            if name == "output":
                return Parameter("output", df, {})
            return None

        scenario.get_parameter = get_parameter
        result = TechnologyClassifier.build_level_technology_map(scenario)
        assert "tech_a" in result["primary"]
        assert "tech_a" in result["secondary"]


# ---------------------------------------------------------------------------
# Tests: _EMISSION_TECH_PATTERNS
# ---------------------------------------------------------------------------

class TestEmissionPatterns:
    """Verify the regex catches known emission-related technology names."""

    @pytest.mark.parametrize("tech", [
        # Emission species prefixes
        "CO2_TCE", "CH4_TCE", "N2O_TCE", "SF6_TCE", "CF4_TCE", "HFC_TCE",
        "CO2_Emission", "CH4_Emission", "SO2_Emission", "NOx_Emission",
        "CO2_cc", "CO2_feedstocks", "CO2_shipping",
        "CH4_Emission_bunkers", "CH4_nonenergy",
        # Total emission counters
        "TCE_Emission", "TCH4_Emission", "TCO2_Emission",
        "TN2O_Emission", "TSF6_Emission", "TCF4_Emission", "THFC_Emission",
        # Cement, flaring
        "cement_CO2", "cement_co2scr", "cement_pro",
        "flaring_CO2", "flaring_co2",
        # CO2 scrubbing / transport
        "co2_tr_dis", "bco2_tr_dis", "mvac_co2",
        "bio_ppl_co2scr", "g_ppl_co2scr", "igcc_co2scr",
        "h2_co2_scrub", "h2b_co2_scrub",
        # SO2
        "SO2_red_ref", "SO2_scrub_ref", "SO2_elec",
        # Mitigation
        "landfill_flaring", "landfill_compost1",
        "ent_red1", "rice_red2", "soil_red3",
        "nitric_catalytic1", "replacement_so2", "vertical_stud",
        # Link technologies
        "IndGDPAdLink", "POPtoSolvent", "WasteGenToCH4Link",
        "SolWaPOPLink",
        # N2O / HFC variants
        "N2On_adipic_red", "N2Oother", "HFCo_TCE", "HFCequivOther",
        # forest CO2
        "forest_CO2",
    ])
    def test_emission_tech_detected(self, tech):
        """Known emission technologies are matched by the regex."""
        assert _EMISSION_TECH_PATTERNS.search(tech), f"{tech} should match emission pattern"

    @pytest.mark.parametrize("tech", [
        # Non-emission technologies should NOT match
        "coal_ppl", "gas_cc", "solar_pv", "wind_ppl",
        "elec_t_d", "hydro_lc", "nuc_hc",
        "oil_extr_1", "gas_extr_2", "bio_ppl",
        "ref_hil", "ref_lol", "stor_ppl",
        "h2_smr", "h2_elec",
        "unknown_tech",
    ])
    def test_non_emission_tech_not_detected(self, tech):
        """Non-emission technologies are not matched by the regex."""
        assert not _EMISSION_TECH_PATTERNS.search(tech), f"{tech} should NOT match emission pattern"


# ---------------------------------------------------------------------------
# Tests: filter_by_energy_level
# ---------------------------------------------------------------------------

class TestFilterByEnergyLevel:
    def test_basic_filter(self, sample_var_act_df):
        """Filter returns only technologies at the specified level."""
        level_map = {
            "secondary": ["coal_ppl", "coal_adv", "gas_cc", "gas_ppl", "solar_pv", "wind_ppl", "nuc_hc"],
            "renewable": ["solar_pv", "solar_res", "wind_ppl", "wind_res", "hydro_lc"],
        }

        result = TechnologyClassifier.filter_by_energy_level(
            sample_var_act_df, "renewable", level_map
        )
        assert set(result["technology"]) == {"solar_pv", "solar_res", "wind_ppl", "wind_res", "hydro_lc"}
        assert len(result) == 5

    def test_unknown_level(self, sample_var_act_df):
        """Unknown level returns empty DataFrame."""
        level_map = {"primary": ["coal_extr"]}
        result = TechnologyClassifier.filter_by_energy_level(
            sample_var_act_df, "unknown_level", level_map
        )
        assert result.empty
        # Columns should be preserved
        assert list(result.columns) == list(sample_var_act_df.columns)

    def test_missing_tech_column(self):
        """DataFrame without technology column is returned as-is."""
        df = pd.DataFrame({"year": [2030], "value": [100]})
        result = TechnologyClassifier.filter_by_energy_level(df, "primary", {"primary": ["x"]})
        assert len(result) == 1  # unchanged

    def test_empty_df(self):
        """Empty DataFrame returns empty."""
        df = pd.DataFrame(columns=["technology", "lvl"])
        result = TechnologyClassifier.filter_by_energy_level(df, "primary", {"primary": ["x"]})
        assert result.empty


# ---------------------------------------------------------------------------
# Tests: apply_technology_grouping
# ---------------------------------------------------------------------------

class TestApplyTechnologyGrouping:
    def test_broad_grouping(self, sample_var_act_df):
        """All techs with same prefix are lumped together."""
        result = TechnologyClassifier.apply_technology_grouping(sample_var_act_df)

        # coal_ppl (100) + coal_adv (50) → "coal" (150)
        coal_rows = result[result["technology"] == "coal"]
        assert len(coal_rows) == 1
        assert coal_rows["lvl"].iloc[0] == 150.0

        # gas_cc (200) + gas_ppl (80) → "natural gas" (280)
        gas_rows = result[result["technology"] == "natural gas"]
        assert len(gas_rows) == 1
        assert gas_rows["lvl"].iloc[0] == 280.0

        # solar_pv (120) + solar_res (30) → "solar" (150)
        solar_rows = result[result["technology"] == "solar"]
        assert len(solar_rows) == 1
        assert solar_rows["lvl"].iloc[0] == 150.0

        # wind_ppl (90) + wind_res (10) → "wind" (100)
        wind_rows = result[result["technology"] == "wind"]
        assert len(wind_rows) == 1
        assert wind_rows["lvl"].iloc[0] == 100.0

    def test_unmapped_preserved(self, sample_var_act_df):
        """Technologies matching a group are grouped; mapped techs get group name."""
        result = TechnologyClassifier.apply_technology_grouping(sample_var_act_df)

        # hydro_lc → "hydro" (mapped via hydro_ prefix)
        hydro_rows = result[result["technology"] == "hydro"]
        assert len(hydro_rows) == 1
        assert hydro_rows["lvl"].iloc[0] == 60.0

        # nuc_hc → "nuclear" (mapped via nuc_ prefix)
        nuc_rows = result[result["technology"] == "nuclear"]
        assert len(nuc_rows) == 1
        assert nuc_rows["lvl"].iloc[0] == 150.0

    def test_truly_unmapped_preserved(self):
        """Technologies not matching any group keep their original name."""
        df = pd.DataFrame({
            "technology": ["unknown_tech", "another_thing"],
            "year_act": [2030, 2030],
            "lvl": [10.0, 20.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        assert "unknown_tech" in result["technology"].values
        assert "another_thing" in result["technology"].values

    def test_numbered_extraction_grouped(self):
        """Numbered extraction techs (gas_extr_1, _2, _3) grouped under broad prefix."""
        df = pd.DataFrame({
            "technology": ["gas_extr_1", "gas_extr_2", "gas_extr_3", "gas_cc"],
            "year_act": [2030] * 4,
            "lvl": [100.0, 80.0, 60.0, 200.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        # All gas_* techs → "natural gas"
        gas_rows = result[result["technology"] == "natural gas"]
        assert len(gas_rows) == 1
        assert gas_rows["lvl"].iloc[0] == 440.0

    def test_curtailment_grouped(self):
        """Curtailment technologies grouped under broad prefix."""
        df = pd.DataFrame({
            "technology": ["solar_curtailment_1", "solar_curtailment_2", "solar_pv"],
            "year_act": [2030] * 3,
            "lvl": [10.0, 20.0, 100.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        # All solar_* techs → "solar"
        solar_rows = result[result["technology"] == "solar"]
        assert len(solar_rows) == 1
        assert solar_rows["lvl"].iloc[0] == 130.0

    def test_refinery_grouped(self):
        """Refinery technologies (ref_hil, ref_lol) are grouped."""
        df = pd.DataFrame({
            "technology": ["ref_hil", "ref_lol"],
            "year_act": [2030, 2030],
            "lvl": [100.0, 200.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        ref_rows = result[result["technology"] == "refinery"]
        assert len(ref_rows) == 1
        assert ref_rows["lvl"].iloc[0] == 300.0

    def test_hydrogen_grouped(self):
        """Hydrogen technologies are grouped."""
        df = pd.DataFrame({
            "technology": ["h2_smr", "h2_coal", "h2_elec", "h2_bio"],
            "year_act": [2030] * 4,
            "lvl": [100.0, 50.0, 30.0, 20.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        h2_rows = result[result["technology"] == "hydrogen"]
        assert len(h2_rows) == 1
        assert h2_rows["lvl"].iloc[0] == 200.0

    def test_emission_species_grouped(self):
        """Emission species accounting technologies are grouped."""
        df = pd.DataFrame({
            "technology": ["CO2_TCE", "CO2_Emission", "CH4_TCE", "CH4_Emission"],
            "year_act": [2030] * 4,
            "lvl": [50.0, 10.0, 30.0, 5.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        co2_rows = result[result["technology"] == "CO2 emissions"]
        assert len(co2_rows) == 1
        assert co2_rows["lvl"].iloc[0] == 60.0
        ch4_rows = result[result["technology"] == "CH4 emissions"]
        assert len(ch4_rows) == 1
        assert ch4_rows["lvl"].iloc[0] == 35.0

    def test_cement_grouped(self):
        """Cement emission technologies are grouped; co2scr goes to CO2 scrubbing."""
        df = pd.DataFrame({
            "technology": ["cement_CO2", "cement_co2scr", "cement_pro"],
            "year_act": [2030] * 3,
            "lvl": [50.0, 10.0, 5.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        # cement_CO2 + cement_pro → "cement emissions" (prefix match)
        cem_rows = result[result["technology"] == "cement emissions"]
        assert len(cem_rows) == 1
        assert cem_rows["lvl"].iloc[0] == 55.0
        # cement_co2scr → "CO2 scrubbing" (suffix _co2scr takes priority)
        scrub_rows = result[result["technology"] == "CO2 scrubbing"]
        assert len(scrub_rows) == 1
        assert scrub_rows["lvl"].iloc[0] == 10.0

    def test_suffix_overrides_prefix(self):
        """Suffix patterns (_imp, _exp) take priority over broad prefix."""
        df = pd.DataFrame({
            "technology": ["gas_imp", "gas_cc", "coal_imp", "oil_exp"],
            "year_act": [2030] * 4,
            "lvl": [100.0, 200.0, 50.0, 30.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        # gas_imp → "imports" (not "natural gas")
        imp_rows = result[result["technology"] == "imports"]
        assert len(imp_rows) == 1
        assert imp_rows["lvl"].iloc[0] == 150.0
        # gas_cc → "natural gas" (prefix match)
        gas_rows = result[result["technology"] == "natural gas"]
        assert len(gas_rows) == 1
        assert gas_rows["lvl"].iloc[0] == 200.0
        # oil_exp → "exports" (suffix overrides "oil" prefix)
        exp_rows = result[result["technology"] == "exports"]
        assert len(exp_rows) == 1
        assert exp_rows["lvl"].iloc[0] == 30.0

    def test_co2scr_suffix_overrides_prefix(self):
        """_co2scr suffix takes priority over broad prefix (e.g., bio_)."""
        df = pd.DataFrame({
            "technology": ["bio_ppl_co2scr", "igcc_co2scr", "bio_ppl"],
            "year_act": [2030] * 3,
            "lvl": [10.0, 15.0, 100.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)
        # bio_ppl_co2scr + igcc_co2scr → "CO2 scrubbing" (suffix match)
        scrub_rows = result[result["technology"] == "CO2 scrubbing"]
        assert len(scrub_rows) == 1
        assert scrub_rows["lvl"].iloc[0] == 25.0
        # bio_ppl → "biomass" (prefix match)
        bio_rows = result[result["technology"] == "biomass"]
        assert len(bio_rows) == 1
        assert bio_rows["lvl"].iloc[0] == 100.0

    def test_empty_df(self):
        """Empty DataFrame returns empty."""
        df = pd.DataFrame(columns=["technology", "lvl"])
        result = TechnologyClassifier.apply_technology_grouping(df)
        assert result.empty

    def test_no_tech_column(self):
        """DataFrame without technology column returned as-is."""
        df = pd.DataFrame({"year": [2030], "value": [100]})
        result = TechnologyClassifier.apply_technology_grouping(df)
        assert len(result) == 1

    def test_preserves_other_dimensions(self):
        """Grouping preserves node_loc, year_act, mode dimensions."""
        df = pd.DataFrame({
            "node_loc": ["A", "A", "B", "B"],
            "technology": ["solar_pv", "solar_res", "solar_pv", "solar_res"],
            "year_act": [2030, 2030, 2030, 2030],
            "mode": ["M1", "M1", "M1", "M1"],
            "lvl": [100.0, 50.0, 200.0, 80.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)

        # Should be 2 rows: "solar" at node A, "solar" at node B
        assert len(result) == 2
        a_row = result[result["node_loc"] == "A"]
        assert a_row["lvl"].iloc[0] == 150.0
        b_row = result[result["node_loc"] == "B"]
        assert b_row["lvl"].iloc[0] == 280.0

    def test_multiple_years(self):
        """Grouping respects year boundaries."""
        df = pd.DataFrame({
            "technology": ["coal_ppl", "coal_adv", "coal_ppl", "coal_adv"],
            "year_act": [2030, 2030, 2040, 2040],
            "lvl": [100.0, 50.0, 80.0, 40.0],
        })
        result = TechnologyClassifier.apply_technology_grouping(df)

        # 2 rows: coal 2030 (150), coal 2040 (120)
        assert len(result) == 2
        row_2030 = result[result["year_act"] == 2030]
        assert row_2030["lvl"].iloc[0] == 150.0
        row_2040 = result[result["year_act"] == 2040]
        assert row_2040["lvl"].iloc[0] == 120.0


# ---------------------------------------------------------------------------
# Tests: get_technology_group_mappings
# ---------------------------------------------------------------------------

class TestGetTechnologyGroupMappings:
    def test_returns_dict(self):
        """Returns a dict with expected keys."""
        result = TechnologyClassifier.get_technology_group_mappings()
        assert isinstance(result, dict)
        assert "coal" in result
        assert "solar" in result
        assert "wind" in result
        assert "natural gas" in result
        assert "refinery" in result
        assert "hydrogen" in result
        assert "CO2 emissions" in result
        assert "CH4 emissions" in result

    def test_returns_copy(self):
        """Returns a copy, not the original."""
        a = TechnologyClassifier.get_technology_group_mappings()
        b = TechnologyClassifier.get_technology_group_mappings()
        a["new_key"] = ["test"]
        assert "new_key" not in b


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_build_reverse_group_map(self):
        """Reverse map contains all patterns."""
        reverse = _build_reverse_group_map()
        assert reverse["coal_"] == "coal"
        assert reverse["solar_"] == "solar"
        assert reverse["gas_"] == "natural gas"
        assert reverse["ref_"] == "refinery"
        assert reverse["h2_"] == "hydrogen"
        assert reverse["CO2_"] == "CO2 emissions"
        assert reverse["_imp"] == "imports"
        assert reverse["_co2scr"] == "CO2 scrubbing"

    def test_find_group_exact_match(self):
        """Exact match returns group name."""
        reverse = _build_reverse_group_map()
        assert _find_group("igcc", reverse) == "coal"
        assert _find_group("mvac_co2", reverse) == "CO2 scrubbing"
        assert _find_group("vertical_stud", reverse) == "emission mitigation"

    def test_find_group_prefix_match(self):
        """Prefix match works with broad prefixes."""
        reverse = _build_reverse_group_map()
        assert _find_group("coal_ppl", reverse) == "coal"
        assert _find_group("coal_extr_1", reverse) == "coal"
        assert _find_group("gas_cc", reverse) == "natural gas"
        assert _find_group("gas_extr_2", reverse) == "natural gas"
        assert _find_group("solar_pv", reverse) == "solar"
        assert _find_group("solar_curtailment_1", reverse) == "solar"
        assert _find_group("h2_smr", reverse) == "hydrogen"
        assert _find_group("h2_coal_ccs", reverse) == "hydrogen"
        assert _find_group("ref_hil", reverse) == "refinery"
        assert _find_group("elec_t_d", reverse) == "electricity"
        assert _find_group("CO2_TCE", reverse) == "CO2 emissions"
        assert _find_group("CH4_Emission", reverse) == "CH4 emissions"

    def test_find_group_suffix_before_prefix(self):
        """Suffix patterns take priority over prefix patterns."""
        reverse = _build_reverse_group_map()
        # _imp overrides gas_ prefix
        assert _find_group("gas_imp", reverse) == "imports"
        assert _find_group("coal_imp", reverse) == "imports"
        # _exp overrides oil_ prefix
        assert _find_group("oil_exp", reverse) == "exports"
        # _co2scr overrides bio_ prefix
        assert _find_group("bio_ppl_co2scr", reverse) == "CO2 scrubbing"
        assert _find_group("igcc_co2scr", reverse) == "CO2 scrubbing"
        # _co2_scrub overrides h2_ prefix
        assert _find_group("h2_co2_scrub", reverse) == "CO2 scrubbing"

    def test_find_group_no_match(self):
        """Unmatched technology returns original name."""
        reverse = _build_reverse_group_map()
        assert _find_group("unknown_tech", reverse) == "unknown_tech"

    def test_find_group_non_string(self):
        """Non-string input returned as-is."""
        reverse = _build_reverse_group_map()
        assert _find_group(None, reverse) is None
        assert _find_group(42, reverse) == 42

    def test_collect_levels_with_tec_column(self):
        """_collect_levels works with 'tec' column name."""
        df = pd.DataFrame({
            "tec": ["tech_a", "tech_b"],
            "level": ["primary", "secondary"],
        })
        level_map = {}
        all_techs = set()
        _collect_levels(df, level_map, all_techs)
        assert "tech_a" in level_map["primary"]
        assert "tech_b" in level_map["secondary"]
        assert all_techs == {"tech_a", "tech_b"}
