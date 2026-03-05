"""
Base analyzer infrastructure for MESSAGEix results postprocessing.

Contains:
- ScenarioDataWrapper: wraps ScenarioData to provide msg.par()/var()/set() interface
- BaseAnalyzer: base class with shared helpers, unit conversions, and technology mappings
"""

import pandas as pd
from typing import Dict, List, Optional, Any, Tuple

from core.data_models import ScenarioData


_YEAR_COLS: frozenset = frozenset({"year_act", "year_vtg", "year_rel", "year"})


def _normalize_year_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Cast any year dimension columns stored as strings to int64."""
    for col in _YEAR_COLS:
        if col in df.columns and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("int64")
    return df


class ScenarioDataWrapper:
    """
    Wraps ScenarioData to provide msg.par(), msg.var(), msg.set() interface
    compatible with the postprocessor functions.
    """

    def __init__(self, scenario: ScenarioData):
        self.scenario = scenario
        self._solution_exists = self._check_solution()

    def _check_solution(self) -> bool:
        """Check if result variables exist (indicating a solution)."""
        result_vars = ['ACT', 'CAP', 'CAP_NEW', 'EMISS', 'PRICE_COMMODITY']
        for var in result_vars:
            if self.scenario.get_parameter(var):
                return True
        return False

    def has_solution(self) -> bool:
        """Check if the scenario has a solution."""
        return self._solution_exists

    def par(self, param_name: str, filters: Optional[Dict] = None) -> pd.DataFrame:
        """
        Get input parameter data, optionally filtered.

        Args:
            param_name: Name of the parameter (e.g., 'output', 'input')
            filters: Optional dict of {column: value(s)} to filter by

        Returns:
            DataFrame with parameter data
        """
        param = self.scenario.get_parameter(param_name)
        if param is None:
            param = self.scenario.get_parameter(f"var_{param_name}")
        if param is None:
            return pd.DataFrame()

        df = _normalize_year_cols(param.df.copy())

        if filters:
            for col, values in filters.items():
                if col in df.columns:
                    if isinstance(values, (list, tuple)):
                        df = df[df[col].isin(values)]
                    else:
                        df = df[df[col] == values]

        return df

    def var(self, var_name: str, filters: Optional[Dict] = None) -> pd.DataFrame:
        """
        Get result variable data, optionally filtered.

        Args:
            var_name: Name of the variable (e.g., 'ACT', 'CAP')
            filters: Optional dict of {column: value(s)} to filter by

        Returns:
            DataFrame with variable data
        """
        return self.par(var_name, filters)

    def set(self, set_name: str, filters: Optional[Dict] = None) -> pd.Series:
        """
        Get set values, optionally filtered.

        Args:
            set_name: Name of the set (e.g., 'commodity', 'technology', 'year')
            filters: Optional dict for cat_year filtering

        Returns:
            Series with set values, or DataFrame for cat_year
        """
        if set_name == 'cat_year':
            if filters and 'type_year' in filters:
                year_type = filters['type_year']
                years = self.scenario.sets.get('year', pd.Series())
                if len(years) == 0:
                    return pd.DataFrame({'year': []})
                if year_type == 'firstmodelyear':
                    return pd.DataFrame({'year': [min(years)]})
                elif year_type == 'lastmodelyear':
                    return pd.DataFrame({'year': [max(years)]})
            return pd.DataFrame({'year': []})

        return self.scenario.sets.get(set_name, pd.Series())


class BaseAnalyzer:
    """
    Base class for all domain-specific analyzers.

    Provides shared state, unit conversion constants, and helper methods
    used across all domain analyzers.
    """

    # Unit conversion factors
    UNIT_GWA_TO_PJ = 8.76 * 3.6    # GWa to PJ
    UNIT_GWA_TO_TWH = 8760 / 1000  # GWa to TWh
    UNIT_GW_TO_MW = 1000            # GW to MW

    def __init__(self, msg: ScenarioDataWrapper, scenario: ScenarioData,
                 plotyrs: List[int], results: Dict[str, Any]):
        """
        Initialize the analyzer with shared state references.

        Args:
            msg: ScenarioDataWrapper for data access
            scenario: ScenarioData with input parameters and result variables
            plotyrs: List of years to include in calculations
            results: Shared mutable dict where calculation results are stored
        """
        self.msg = msg
        self.scenario = scenario
        self.plotyrs = plotyrs
        self.results = results  # shared mutable dict

    # =========================================================================
    # Technology Discovery Helpers
    # =========================================================================

    def _get_all_technology_names(self) -> List[str]:
        """Get all technology names, falling back to ACT variable if set is empty."""
        techs = self.msg.set('technology')
        if len(techs) > 0:
            return techs.tolist()

        # Fallback: get from ACT variable
        act = self.msg.var('ACT')
        if not act.empty and 'technology' in act.columns:
            return act['technology'].unique().tolist()

        return []

    def _detect_node_location(self) -> str:
        """Auto-detect the node location from the data."""
        nodes = self.msg.set('node')
        if len(nodes) > 0:
            return nodes.iloc[0]

        act = self.msg.var('ACT')
        if not act.empty and 'node_loc' in act.columns:
            return act['node_loc'].iloc[0]

        return 'World'

    def _get_renewable_technologies(self) -> List[str]:
        """Get technologies that use renewable inputs."""
        input_par = self.msg.par("input", {"level": ["renewable"]})
        if input_par.empty:
            return []
        return list(input_par['technology'].unique())

    def _get_technologies_by_input_fuel(self, fuel_commodities: List[str]) -> List[str]:
        """Get technologies that use specific input commodities."""
        input_par = self.msg.par("input", {"commodity": fuel_commodities})
        if input_par.empty:
            return []
        tec_col = 'technology' if 'technology' in input_par.columns else 'tec' if 'tec' in input_par.columns else None
        if not tec_col:
            return []
        return list(input_par[tec_col].unique())

    def _get_technologies_by_output(self, commodities: List[str],
                                     level: Optional[str] = None) -> List[str]:
        """Get technologies that output specific commodities."""
        filters = {"commodity": commodities}
        if level:
            filters["level"] = [level]
        output_par = self.msg.par("output", filters)
        if output_par.empty:
            return []
        return list(output_par['technology'].unique())

    # =========================================================================
    # Commodity / Sector / Fuel Lookup Helpers
    # =========================================================================

    def _get_commodity_order(self) -> List[str]:
        """Get standard commodity ordering."""
        commodities = self.msg.set("commodity")
        crudes = [x for x in commodities if "crude_" in str(x)]
        gases = [x for x in commodities if "gas_" in str(x)]

        return (
            ["coal", "coal_rc", "coal_i", "crudeoil"]
            + crudes
            + ["fueloil", "foil_rc", "foil_i", "lightoil", "loil_rc", "loil_i"]
            + gases
            + [
                "biomass", "biomass_nc", "biomass_rc", "d_heat", "elec_rc", "electr",
                "ethanol", "gas", "gas_rc", "hp_el_rc", "hp_gas_rc", "hydro", "hydrogen",
                "methanol", "nuclear", "solar_csp", "solar_pv", "solar_rc", "sp_el_I",
                "sp_el_RC", "wind_offshore", "wind_onshore",
            ]
        )

    def _get_sector_commodities(self) -> Dict[str, List[str]]:
        """Get mapping of sectors to their output commodities."""
        return {
            "Power": ["electr"],
            "Transport": ["transport"],
            "Industry": ["i_spec", "i_therm"],
            "Buildings": ["rc_spec", "rc_therm", "non-comm"],
            "Feedstock": ["i_feed"],
        }

    def _get_fuel_commodities(self) -> Dict[str, List[str]]:
        """Get mapping of fuel categories to commodity names."""
        return {
            "Coal": ["coal", "coal_rc", "coal_i"],
            "Oil": ["crudeoil", "lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i"],
            "Gas": ["gas", "gas_rc", "gas_i"],
            "Electricity": ["electr", "elec_rc"],
            "Biomass": ["biomass", "biomass_rc", "biomass_nc"],
            "Hydrogen": ["hydrogen"],
            "Heat": ["d_heat", "hp_el_rc", "hp_gas_rc"],
            "Ethanol": ["ethanol"],
            "Methanol": ["methanol"],
        }

    # =========================================================================
    # Technology Mapping Helpers
    # =========================================================================

    def _map_technologies_to_sectors(self, technologies: List[str]) -> Dict[str, List[str]]:
        """Map technologies to sectors based on their output commodity."""
        sector_coms = self._get_sector_commodities()
        sector_tecs = {sector: [] for sector in sector_coms}
        sector_tecs["Other"] = []

        output_par = self.msg.par("output")

        if output_par.empty:
            return self._map_technologies_to_sectors_by_name(technologies, sector_tecs)

        tec_col = 'technology' if 'technology' in output_par.columns else 'tec' if 'tec' in output_par.columns else None
        if not tec_col:
            return self._map_technologies_to_sectors_by_name(technologies, sector_tecs)

        for tec in technologies:
            tec_output = output_par[output_par[tec_col] == tec]
            if tec_output.empty:
                sector_tecs["Other"].append(tec)
                continue

            assigned = False
            for sector, coms in sector_coms.items():
                if tec_output['commodity'].isin(coms).any():
                    sector_tecs[sector].append(tec)
                    assigned = True
                    break
            if not assigned:
                sector_tecs["Other"].append(tec)

        return sector_tecs

    def _map_technologies_to_sectors_by_name(self, technologies: List[str],
                                              sector_tecs: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Fallback: Map technologies to sectors by name patterns."""
        sector_patterns = {
            "Power": ["_ppl", "coal_ppl", "gas_ppl", "oil_ppl", "bio_ppl", "hydro", "wind", "solar",
                      "nuclear", "geo_ppl", "igcc", "stor_ppl", "elec_t_d", "grid"],
            "Transport": ["_trp", "transport", "vehicle", "car_", "bus_", "truck_", "train_",
                          "ship_", "air_", "moto_"],
            "Industry": ["_i", "ind_", "industry", "furnace_", "cement", "steel", "aluminum",
                         "petro", "refin"],
            "Buildings": ["_rc", "rc_", "resid", "comm_", "heat_", "cool_", "light_", "appl_"],
            "Feedstock": ["_feed", "feedstock", "petrochem"],
        }

        for tec in technologies:
            tec_lower = tec.lower()
            assigned = False
            for sector, patterns in sector_patterns.items():
                if any(pattern in tec_lower for pattern in patterns):
                    sector_tecs[sector].append(tec)
                    assigned = True
                    break
            if not assigned:
                sector_tecs["Other"].append(tec)

        return sector_tecs

    def _map_technologies_to_fuels_by_name(self, technologies: List[str]) -> Dict[str, List[str]]:
        """Map technologies to fuel types by name patterns."""
        fuel_tecs = {fuel: [] for fuel in self._get_fuel_commodities().keys()}

        fuel_patterns = {
            "Coal": ["coal", "_coal", "igcc"],
            "Oil": ["oil", "foil", "loil", "diesel", "gasoline", "petro", "refin"],
            "Gas": ["gas", "_gas", "ngcc", "ccgt", "ocgt"],
            "Biomass": ["bio", "biomass", "wood", "pellet"],
            "Hydrogen": ["h2", "hydrogen", "fuel_cell", "fuelcell"],
            "Electricity": ["elec", "_el_", "electric"],
            "Heat": ["heat", "_hp_", "boiler", "furnace"],
            "Ethanol": ["ethanol", "eth_"],
            "Methanol": ["methanol", "meth_"],
        }

        for tec in technologies:
            tec_lower = tec.lower()
            for fuel, patterns in fuel_patterns.items():
                if any(pattern in tec_lower for pattern in patterns):
                    fuel_tecs[fuel].append(tec)
                    break  # Only assign to first matching fuel

        return fuel_tecs

    def _calculate_fuel_use_by_sector(self, sector_commodities: List[str],
                                       nodeloc: str, yr: int) -> pd.DataFrame:
        """Calculate fuel consumption for technologies outputting to a sector.

        Common helper for Buildings, Industry, Transport fuel use calculations.
        Returns wide-format DataFrame with fuels as columns and years as index.
        """
        order = self._get_commodity_order()
        output_par = self.msg.par("output", {"commodity": sector_commodities})
        if output_par.empty:
            return pd.DataFrame()

        tecs = list(set(output_par.technology))
        df, df2 = self._model_output(tecs, nodeloc, "input")
        if df.empty:
            return pd.DataFrame()

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
        df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
        df = self._com_order(df.add(df_hist, fill_value=0), order)
        return df

    # =========================================================================
    # Core Calculation Helpers
    # =========================================================================

    def _group(self, df: pd.DataFrame, groupby: List[str],
               result: str, limit: float, lyr: Any,
               keep_long: bool = False) -> pd.DataFrame:
        """Group dataframe and optionally pivot.

        Args:
            df: DataFrame to group
            groupby: List of columns to group by
            result: Column name containing values to sum
            limit: Unused (kept for compatibility)
            lyr: Unused (kept for compatibility)
            keep_long: If True, return long format with all groupby columns.
                      If False (default), pivot to wide format.
        """
        if df.empty:
            return pd.DataFrame()

        # Keep only the columns we care about, then sum within each group
        cols_to_keep = groupby + [result]
        df = df[cols_to_keep].groupby(groupby, as_index=False).sum()

        if keep_long:
            # Standardize the value column name for long-format callers
            df = df.rename(columns={result: 'value'})
            return df
        else:
            # Pivot: groupby[0] → row index (usually year_act)
            #        groupby[1] → columns (usually commodity or technology)
            df = pd.pivot_table(
                df, index=groupby[0], columns=groupby[1], values=result, fill_value=0
            )
            return df

    def _multiply_df(self, df1: pd.DataFrame, column1: str,
                     df2: pd.DataFrame, column2: str) -> pd.DataFrame:
        """Merge and multiply two dataframes.

        Aggregates the parameter (df2) by technology (and commodity if present),
        then merges on technology to get coefficients.
        """
        if df1.empty or df2.empty:
            return pd.DataFrame()

        # Average efficiency/cost coefficients across modes/years before merging.
        # Including commodity in the group key keeps multi-commodity technologies
        # (e.g. a technology that produces both electricity and heat) correct.
        agg_cols = ["technology"]
        if "commodity" in df2.columns:
            agg_cols.append("commodity")

        df2_agg = df2.groupby(agg_cols, as_index=False)[column2].mean()
        # Left-join: every activity row gets the matching coefficient
        df = df1.merge(df2_agg, how="left", on="technology")
        # The 'product' column = activity × efficiency (e.g. GWa × PJ/GWa = PJ)
        df["product"] = df.loc[:, column1] * df.loc[:, column2]

        return df

    def _attach_history(self, tec: List[str]) -> pd.DataFrame:
        """Get historical activity data for technologies in plotyrs years.

        Returns a wide-format DataFrame (year_act index, technology columns).
        Note: filters to plotyrs, so pre-model historical years are not included.
        """
        parname = "historical_activity"
        # Only fetch rows whose year_act falls within the plot period
        act_hist = self.msg.par(parname, {"technology": tec, "year_act": self.plotyrs})
        if act_hist.empty:
            return pd.DataFrame(index=self.plotyrs)

        act_hist = act_hist[["technology", "year_act", "value"]]
        # Pivot to wide format: rows = years, columns = technologies
        act_hist = act_hist.pivot(index="year_act", columns="technology").fillna(0)
        # Drop all-zero technology columns (no historical activity)
        act_hist = act_hist[act_hist.columns[(act_hist > 0).any()]]
        if len(act_hist.columns) > 0:
            act_hist.columns = act_hist.columns.droplevel(0)  # remove multi-level header
        return act_hist

    def _add_history(self, tecs: List[str], nodeloc: str,
                     df2: pd.DataFrame, groupby: str) -> pd.DataFrame:
        """Add pre-model historical data to a model-period result DataFrame.

        Computes historical energy flow as:
            historical_activity × mean(efficiency/output coefficient)
        and groups by (year_act, groupby) to match the shape of model results.

        Args:
            tecs: Technology list to query historical_activity for
            nodeloc: Node location (region) to filter by
            df2: The efficiency/output parameter DataFrame (from _model_output)
            groupby: Column to pivot on (e.g. 'commodity' or 'technology')
        """
        df1_hist = self.msg.par(
            "historical_activity", {"technology": tecs, "node_loc": nodeloc}
        )
        if df1_hist.empty:
            return pd.DataFrame(index=self.plotyrs)

        # Rename 'value' → 'lvl' so _multiply_df can treat it like an ACT variable
        df1_hist = df1_hist.rename({"value": "lvl"}, axis=1)

        # Average the parameter (e.g. output efficiency) across vintage years and
        # other dimensions, keeping only the dimensional columns that _multiply_df needs
        df2_hist = (
            df2.groupby(
                ["year_act", "technology", "mode", "node_loc", "commodity", "time"],
                as_index=False
            )
            .mean(numeric_only=True)
        )
        if 'year_vtg' in df2_hist.columns:
            df2_hist = df2_hist.drop(["year_vtg"], axis=1)

        # Multiply historical activity by the efficiency coefficient
        df_hist = self._multiply_df(df1_hist, "lvl", df2_hist, "value")
        # Aggregate to wide format (year_act × groupby)
        df_hist = self._group(df_hist, ["year_act", groupby], "product", 0.0, None)
        return df_hist

    def _add_history_long(self, tecs: List[str], df2: pd.DataFrame,
                          groupby: str) -> pd.DataFrame:
        """Add historical data in long format (preserving node_loc)."""
        df1_hist = self.msg.par("historical_activity", {"technology": tecs})
        if df1_hist.empty:
            return pd.DataFrame()

        df1_hist = df1_hist.rename({"value": "lvl"}, axis=1)

        groupby_cols = ["year_act", "technology", "mode", "node_loc", "commodity", "time"]
        df2_hist = df2.groupby(groupby_cols, as_index=False).mean(numeric_only=True)
        if 'year_vtg' in df2_hist.columns:
            df2_hist = df2_hist.drop(["year_vtg"], axis=1)

        df_hist = self._multiply_df(df1_hist, "lvl", df2_hist, "value")
        if df_hist.empty:
            return pd.DataFrame()

        df_hist = self._group(df_hist, ["node_loc", "year_act", groupby], "product", 0.0, None, keep_long=True)
        return df_hist

    def _model_output(self, tecs: List[str], nodeloc: str,
                      parname: str, coms: Optional[Any] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get model output by combining activity with parameters.

        Core calculation pattern:  result = ACT × parameter_value
        e.g. electricity_output = activity(GWa) × output_efficiency(PJ/GWa)

        Returns a tuple of:
          - df: merged DataFrame with a 'product' column (activity × coefficient)
          - df2: the raw parameter DataFrame (needed by _add_history for coefficients)

        Note: nodeloc parameter is kept for API compatibility but NOT used for
        filtering. All nodes are aggregated, since most MESSAGEix scenarios are
        single-region and the 'World' node already covers everything.
        """
        # Get technology activity, filtered to plot years only.
        # This is the key fix for years outside plotyrs appearing in results.
        df1 = self.msg.var("ACT", {"technology": tecs})

        if not df1.empty and 'year_act' in df1.columns and self.plotyrs:
            df1 = df1[df1['year_act'].isin(self.plotyrs)]

        # Get the efficiency/output/input coefficient for these technologies
        df2 = self.msg.par(parname, {"technology": tecs})

        if df1.empty or df2.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Optionally restrict to specific output/input commodities
        if coms:
            if isinstance(coms, str):
                coms = [coms]
            df2 = df2.loc[df2["commodity"].isin(coms)]

        # Compute product = ACT × coefficient (energy flow)
        df = self._multiply_df(df1, "lvl", df2, "value")
        return df, df2

    def _com_order(self, df: pd.DataFrame, order: List[str]) -> pd.DataFrame:
        """Reorder columns according to specified order."""
        if df.empty:
            return df
        order = [x for x in order if x in df.columns]
        new_order = order + [x for x in df.columns if x not in order]
        return df.reindex(new_order, axis=1)

    def _mappings(self, df: pd.DataFrame, groupby: str = "sector") -> pd.DataFrame:
        """Aggregate by sector or technology groups."""
        if df.empty:
            return pd.DataFrame(index=self.plotyrs)

        data_years = df.index.tolist()
        df_sec = pd.DataFrame(index=data_years)

        if groupby == "sector":
            dict_sectors = self._get_sector_mappings(df)
        else:
            dict_sectors = self._get_technology_mappings(df)

        for label, tecs in dict_sectors.items():
            if tecs:
                filtered = df.filter(items=tecs)
                if not filtered.empty:
                    col_sum = filtered.sum(axis=1)
                    df_sec[label] = col_sum

        return df_sec.fillna(0)

    def _get_sector_mappings(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Get sector-based column mappings."""
        cols = df.columns.tolist()

        cols_ind = [col for col in cols if "_i" in col or "_I" in col]
        cols_ind = [x for x in cols_ind if not any(y in x for y in ["eth_ic", "meth_ic", "bio_is", "_imp"])]
        cols_trp = [col for col in cols if "_trp" in col]
        cols_rc = [col for col in cols if any(y in col for y in ["_rc", "_RC"])]
        cols_nc = [col for col in cols if "_nc" in col]
        cols_ene = [col for col in cols if "_fs" in col]
        cols_exp = [col for col in cols if "_exp" in col]
        cols_imp = [col for col in cols if "_imp" in col]
        cols_ppl = [
            col for col in cols if any(y in col for y in [
                "_ppl", "_adv", "bio_istig", "gas_cc", "gas_cc_ccs",
                "gas_ct", "igcc", "igcc_ccs", "loil_cc"
            ])
        ]
        cols_eth = [col for col in cols if any(y in col for y in ["eth_bio", "liq_bio"])]
        cols_meth = [col for col in cols if any(y in col for y in ["meth_ng", "meth_coal"])]
        cols_loil = [col for col in cols if any(y in col for y in ["syn_liq"])]
        cols_gas = [col for col in cols if any(y in col for y in ["coal_gas", "gas_bio"])]
        cols_hyd = [col for col in cols if any(y in col for y in ["h2_"])]
        cols_prod = [col for col in cols if any(y in col for y in [
            "_extr", "_extr_1", "_extr_2", "_extr_3", "_extr_4", "extr_ch4"
        ])]
        cols_prod2 = [col for col in cols if any(y in col for y in [
            "_extr_5", "_extr_6", "_extr_7", "_extr_8"
        ])]
        cols_ref = [col for col in cols if any(y in col for y in ["ref_h", "ref_l"])]

        return {
            "production": cols_prod,
            "production (unconv.)": cols_prod2,
            "refinery": cols_ref,
            "industry": cols_ind,
            "transport": cols_trp,
            "non-energy (feedstock)": cols_ene,
            "buildings": cols_rc,
            "non-commercial": cols_nc,
            "electricity generation": cols_ppl,
            "exports": cols_exp,
            "imports": cols_imp,
            "ethanol": cols_eth,
            "methanol": cols_meth,
            "light oil": cols_loil,
            "gasification": cols_gas,
            "hydrogen": cols_hyd,
        }

    def _get_technology_mappings(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Get technology-based column mappings for power plants."""
        cols = df.columns.tolist()

        return {
            "coal": [col for col in cols if any(y in col for y in ["coal_ppl", "coal_adv", "syn_liq", "igcc"])],
            "heavy fuel oil": [col for col in cols if any(y in col for y in ["foil_ppl", "foil_cc"]) or col == "oil_ppl"],
            "light oil": [col for col in cols if any(y in col for y in ["loil_ppl", "loil_cc"])],
            "natural gas (ST + CT)": [col for col in cols if any(y in col for y in ["gas_ppl", "gas_ct"])],
            "natural gas (CC)": [col for col in cols if any(y in col for y in ["gas_cc"])],
            "nuclear": [col for col in cols if any(y in col for y in ["nuc_hc", "nuc_lc"])],
            "hydro": [col for col in cols if any(y in col for y in ["hydro_lc", "hydro_hc"])],
            "biomass": [col for col in cols if any(y in col for y in ["bio_ppl", "bio_istig"])],
            "wind onshore": [col for col in cols if any(y in col for y in ["wind_ppl", "wind_res"])],
            "wind offshore": [col for col in cols if any(y in col for y in ["wind_ppf", "wind_ref"])],
            "solar PV": [col for col in cols if any(y in col for y in ["solar_pv", "solar_res"])],
            "solar CSP": [col for col in cols if any(y in col for y in ["csp_sm", "solar_th_ppl"])],
            "geothermal": [col for col in cols if any(y in col for y in ["geo_ppl"])],
        }

    def _plotdf(self, tec: List[str], com: List[str], direction: str, yr: int) -> pd.DataFrame:
        """Calculate output/input and attach historical data."""
        inputs = self.msg.par(direction)
        if inputs.empty:
            return pd.DataFrame(index=self.plotyrs)

        inputs = inputs.loc[inputs.year_act.isin(self.plotyrs)]
        inputs = inputs.loc[(inputs.technology.isin(tec)) & (inputs.commodity.isin(com))][
            ["technology", "year_act", "value"]
        ]
        if inputs.empty:
            return pd.DataFrame(index=self.plotyrs)

        inputs = inputs.groupby(["technology", "year_act"], as_index=False).mean(numeric_only=True)
        inputs = inputs.pivot(index="year_act", columns="technology")
        inputs = inputs[inputs.columns[(inputs != 0).any()]]
        if len(inputs.columns) > 0:
            inputs.columns = inputs.columns.droplevel(0)

        act = self.msg.var("ACT")
        if act.empty:
            return pd.DataFrame(index=self.plotyrs)

        act = act.loc[act.year_act.isin(self.plotyrs)]
        activity = act.loc[act.technology.isin(tec)][["technology", "year_act", "lvl"]]
        activity = activity.groupby(["technology", "year_act"], as_index=False).sum(numeric_only=True)
        activity = activity.pivot(index="year_act", columns="technology").fillna(0)
        activity = activity[activity.columns[(activity != 0).any()]]
        if len(activity.columns) > 0:
            activity.columns = activity.columns.droplevel(0)

        act_hist = self._attach_history(tec)
        activity_tot = activity.add(act_hist, fill_value=0)

        df_plot = inputs * activity_tot
        df_plot = df_plot.fillna(0)
        df_plot = df_plot[df_plot.columns[(df_plot > 0).any()]]
        return df_plot
