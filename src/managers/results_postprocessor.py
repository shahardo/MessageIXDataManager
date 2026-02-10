"""
Results Postprocessor - calculates derived metrics from MESSAGEix results.

Adapted from postprocessor_SHRD.py to work with the MessageIX Data Manager app.
Takes raw result variables (ACT, CAP, etc.) and input parameters (output, input, etc.)
and calculates aggregated metrics like:
- Electricity generation by technology
- Primary energy supply
- Final energy consumption
- Sectoral energy use
- Emissions
- Prices
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from core.data_models import ScenarioData, Parameter


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
        # Look for common result variables
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
        # Try with var_ prefix for variables (ACT, CAP, etc.)
        param = self.scenario.get_parameter(param_name)
        if param is None:
            # Try with var_ prefix
            param = self.scenario.get_parameter(f"var_{param_name}")
        if param is None:
            return pd.DataFrame()

        df = param.df.copy()

        if filters:
            for col, values in filters.items():
                if col in df.columns:
                    before_count = len(df)
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
        # Variables are stored as parameters in the app
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
        # Handle cat_year specially
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


class ResultsPostprocessor:
    """
    Calculates derived metrics from MESSAGEix scenario results.

    Takes ScenarioData containing both input parameters and result variables,
    then calculates aggregated metrics and adds them as new parameters.
    """

    # Unit conversion factors
    UNIT_GWA_TO_PJ = 8.76 * 3.6      # GWa to PJ
    UNIT_GWA_TO_TWH = 8760 / 1000   # GWa to TWh
    UNIT_GW_TO_MW = 1000            # GW to MW

    def __init__(self, scenario: ScenarioData):
        """
        Initialize the postprocessor.

        Args:
            scenario: ScenarioData containing input parameters and result variables
        """
        self.scenario = scenario
        self.msg = ScenarioDataWrapper(scenario)
        self.results: Dict[str, pd.DataFrame] = {}

        # Default plot years - can be overridden
        self.plotyrs = list(range(2020, 2051, 5))

    def set_plot_years(self, years: List[int]):
        """Set the years to include in calculations."""
        self.plotyrs = years

    def process(self, nodeloc: Optional[str] = None) -> Dict[str, Parameter]:
        """
        Run all postprocessing calculations and return derived parameters.

        Args:
            nodeloc: Optional node location filter (e.g., 'World')

        Returns:
            Dict of parameter_name -> Parameter objects
        """
        if not self.msg.has_solution():
            print("Warning: Scenario has no solution - cannot run postprocessing")
            return {}

        # DEBUG: Check what's in ACT at the start
        act_param = self.scenario.get_parameter("ACT")
        if act_param is not None:
            act_df = act_param.df
            all_tecs = act_df['technology'].unique().tolist() if 'technology' in act_df.columns else []
            # Check for transport technologies specifically
            trp_tecs = [t for t in all_tecs if '_trp' in str(t)]

        # Get first/last model years
        try:
            yr = int(self.msg.set('cat_year', {'type_year': 'firstmodelyear'})['year'].iloc[0])
        except:
            yr = min(self.plotyrs)

        # Auto-detect node location if not provided
        if nodeloc is None:
            nodeloc = self._detect_node_location()

        # Run calculations - existing
        self._calculate_power_plant_results(nodeloc, yr)
        self._calculate_electricity_use(nodeloc, yr)
        self._calculate_gas_results(nodeloc, yr)
        self._calculate_coal_results(nodeloc, yr)
        self._calculate_oil_results(nodeloc, yr)
        self._calculate_biomass_results(nodeloc, yr)
        self._calculate_sector_results(nodeloc, yr)
        self._calculate_energy_balances(nodeloc, yr)
        self._calculate_trade(nodeloc, yr)
        self._calculate_emissions(nodeloc, yr)
        self._calculate_prices(nodeloc, yr)

        # New calculations - Electricity
        self._calculate_electricity_generation_by_source(nodeloc, yr)
        self._calculate_electricity_use_by_sector(nodeloc, yr)
        self._calculate_power_capacity_with_renewables(nodeloc, yr)

        # New calculations - Emissions
        self._calculate_emissions_by_sector(nodeloc, yr)
        self._calculate_emissions_by_type(nodeloc, yr)
        self._calculate_emissions_by_fuel(nodeloc, yr)

        # New calculations - Energy Balance
        self._calculate_energy_exports_by_fuel(nodeloc, yr)
        self._calculate_energy_imports_by_fuel(nodeloc, yr)
        self._calculate_feedstock_by_fuel(nodeloc, yr)
        self._calculate_oil_derivatives_supply(nodeloc, yr)
        self._calculate_oil_derivatives_use(nodeloc, yr)

        # New calculations - Fuels
        self._calculate_gas_supply_by_source(nodeloc, yr)
        self._calculate_gas_utilization_by_sector(nodeloc, yr)

        # New calculations - Sectoral Use
        self._calculate_buildings_by_fuel(nodeloc, yr)
        self._calculate_industry_by_fuel(nodeloc, yr)

        # New calculations - Prices
        self._calculate_prices_by_sector(nodeloc, yr)
        self._calculate_prices_by_fuel(nodeloc, yr)
        self._calculate_electricity_lcoe(nodeloc, yr)
        self._calculate_electricity_price_by_source(nodeloc, yr)

        # Convert results to Parameters
        return self._create_parameters()

    def _get_all_technology_names(self) -> List[str]:
        """Get all technology names, falling back to ACT variable if set is empty.

        The technology set may not be loaded (e.g., when only ZIP data files
        are available). In that case, extract unique technology names from
        the ACT variable.
        """
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
        # Try to get from sets
        nodes = self.msg.set('node')
        if len(nodes) > 0:
            return nodes.iloc[0]

        # Try to get from ACT variable
        act = self.msg.var('ACT')
        if not act.empty and 'node_loc' in act.columns:
            return act['node_loc'].iloc[0]

        return 'World'  # Default fallback

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

        # Only keep groupby columns + result column to avoid summing unwanted columns
        # (e.g., the original 'value' column from input parameters)
        cols_to_keep = groupby + [result]
        df = df[cols_to_keep].groupby(groupby, as_index=False).sum()

        if keep_long:
            # Return long format - rename result column to 'value'
            df = df.rename(columns={result: 'value'})
            return df
        else:
            # Pivot to wide format (original behavior)
            df = pd.pivot_table(
                df, index=groupby[0], columns=groupby[1], values=result, fill_value=0
            )
            return df

    def _multiply_df(self, df1: pd.DataFrame, column1: str,
                     df2: pd.DataFrame, column2: str) -> pd.DataFrame:
        """Merge and multiply two dataframes.

        Uses a simpler merge strategy that avoids year_vtg mismatches:
        - Aggregates the parameter (df2) by technology (and commodity if present)
        - Merges on technology to get coefficients, preserving commodity info
        This ensures renewable technologies get matched even when vintage years differ.
        """
        if df1.empty or df2.empty:
            return pd.DataFrame()

        # Determine aggregation columns - technology required, commodity optional
        agg_cols = ["technology"]
        if "commodity" in df2.columns:
            agg_cols.append("commodity")

        # Aggregate df2 to get average coefficient per technology (and commodity)
        df2_agg = df2.groupby(agg_cols, as_index=False)[column2].mean()

        # Merge on technology only - commodity comes from df2_agg if present
        df = df1.merge(df2_agg, how="left", on="technology")
        df["product"] = df.loc[:, column1] * df.loc[:, column2]

        return df

    def _attach_history(self, tec: List[str]) -> pd.DataFrame:
        """Get historical activity data."""
        parname = "historical_activity"
        act_hist = self.msg.par(parname, {"technology": tec, "year_act": self.plotyrs})
        if act_hist.empty:
            return pd.DataFrame(index=self.plotyrs)

        act_hist = act_hist[["technology", "year_act", "value"]]
        act_hist = act_hist.pivot(index="year_act", columns="technology").fillna(0)
        act_hist = act_hist[act_hist.columns[(act_hist > 0).any()]]
        if len(act_hist.columns) > 0:
            act_hist.columns = act_hist.columns.droplevel(0)
        return act_hist

    def _add_history(self, tecs: List[str], nodeloc: str,
                     df2: pd.DataFrame, groupby: str) -> pd.DataFrame:
        """Add historical data to results."""
        df1_hist = self.msg.par(
            "historical_activity", {"technology": tecs, "node_loc": nodeloc}
        )
        if df1_hist.empty:
            return pd.DataFrame(index=self.plotyrs)

        df1_hist = df1_hist.rename({"value": "lvl"}, axis=1)

        df2_hist = (
            df2.groupby(
                ["year_act", "technology", "mode", "node_loc", "commodity", "time"],
                as_index=False
            )
            .mean(numeric_only=True)
        )
        if 'year_vtg' in df2_hist.columns:
            df2_hist = df2_hist.drop(["year_vtg"], axis=1)

        df_hist = self._multiply_df(df1_hist, "lvl", df2_hist, "value")
        df_hist = self._group(df_hist, ["year_act", groupby], "product", 0.0, None)
        return df_hist

    def _add_history_long(self, tecs: List[str], df2: pd.DataFrame,
                          groupby: str) -> pd.DataFrame:
        """Add historical data in long format (preserving node_loc).

        Similar to _add_history but returns long format DataFrame with columns:
        [node_loc, year_act, <groupby>, value]
        """
        # Get historical_activity for all nodes (not filtered)
        df1_hist = self.msg.par("historical_activity", {"technology": tecs})
        if df1_hist.empty:
            return pd.DataFrame()

        df1_hist = df1_hist.rename({"value": "lvl"}, axis=1)

        # Average the input/output coefficients across vintages
        groupby_cols = ["year_act", "technology", "mode", "node_loc", "commodity", "time"]
        df2_hist = df2.groupby(groupby_cols, as_index=False).mean(numeric_only=True)
        if 'year_vtg' in df2_hist.columns:
            df2_hist = df2_hist.drop(["year_vtg"], axis=1)

        # Multiply historical activity by input coefficients
        df_hist = self._multiply_df(df1_hist, "lvl", df2_hist, "value")
        if df_hist.empty:
            return pd.DataFrame()

        # Group by node_loc, year_act, and the specified groupby column (e.g., "commodity")
        # Keep long format
        df_hist = self._group(df_hist, ["node_loc", "year_act", groupby], "product", 0.0, None, keep_long=True)
        return df_hist

    def _model_output(self, tecs: List[str], nodeloc: str,
                      parname: str, coms: Optional[Any] = None):
        """Get model output by combining activity with parameters.

        Note: nodeloc parameter is kept for API compatibility but NOT used for filtering.
        Data from all nodes is aggregated together in the results.
        """
        # Get ACT filtered by technology only (not by node - aggregate all nodes)
        df1 = self.msg.var("ACT", {"technology": tecs})

        # Get input/output parameter filtered by technology only
        df2 = self.msg.par(parname, {"technology": tecs})

        if df1.empty or df2.empty:
            return pd.DataFrame(), pd.DataFrame()

        if coms:
            if isinstance(coms, str):
                coms = [coms]
            df2 = df2.loc[df2["commodity"].isin(coms)]

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

        # Use the actual years from the data, not self.plotyrs
        # This ensures the join works correctly
        data_years = df.index.tolist()
        df_sec = pd.DataFrame(index=data_years)

        if groupby == "sector":
            dict_sectors = self._get_sector_mappings(df)
        else:
            dict_sectors = self._get_technology_mappings(df)

        # Map entries to labels
        for label, tecs in dict_sectors.items():
            if tecs:  # Only process non-empty lists
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

    def _calculate_power_plant_results(self, nodeloc: str, yr: int):
        """Calculate power plant activity and capacity metrics."""
        cap = self.msg.var("CAP", {"year_vtg": self.plotyrs})
        cap_new = self.msg.var("CAP_NEW", {"year_vtg": self.plotyrs})
        cap_hist = self.msg.par("historical_new_capacity", {"year_vtg": self.plotyrs})

        # Get electricity-producing technologies
        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tec = output_par["technology"].tolist()
        tec = list(set(tec + ["stor_ppl"]))

        # Power plant capacity
        if not cap.empty:
            ppl_cap = cap.loc[cap.technology.isin(tec)][["technology", "year_act", "lvl"]]
            ppl_cap = ppl_cap.groupby(["technology", "year_act"], as_index=False).sum(numeric_only=True)
            ppl_cap = ppl_cap.pivot(index="year_act", columns="technology")
            ppl_cap = ppl_cap[ppl_cap.columns[(ppl_cap != 0).any()]]
            if len(ppl_cap.columns) > 0:
                ppl_cap.columns = ppl_cap.columns.droplevel(0)
            ppl_cap = ppl_cap.loc[:, (ppl_cap > 0).any()]

            ppl_cap_mapped = self._mappings(ppl_cap, groupby="technology")
            self.results["Power plant capacity (MW)"] = ppl_cap_mapped * self.UNIT_GW_TO_MW

        # Power plant new capacity
        if not cap_new.empty:
            ppl_cap_new = cap_new.loc[(cap_new.technology.isin(tec)) & (cap_new.lvl > 0)][
                ["technology", "year_vtg", "lvl"]
            ]
            if not ppl_cap_new.empty:
                ppl_cap_new = ppl_cap_new.pivot(index="year_vtg", columns="technology")
                if len(ppl_cap_new.columns) > 0:
                    ppl_cap_new.columns = ppl_cap_new.columns.droplevel(0)

                # Add historical capacity
                if not cap_hist.empty:
                    ppl_cap_hist = cap_hist.loc[(cap_hist.technology.isin(tec)) & (cap_hist.value > 0)][
                        ["technology", "year_vtg", "value"]
                    ]
                    if not ppl_cap_hist.empty:
                        ppl_cap_hist = ppl_cap_hist.pivot(index="year_vtg", columns="technology")
                        if len(ppl_cap_hist.columns) > 0:
                            ppl_cap_hist.columns = ppl_cap_hist.columns.droplevel(0)
                        ppl_cap_new = ppl_cap_new.add(ppl_cap_hist, fill_value=0)

                cap_new_tot = ppl_cap_new.fillna(0)
                cap_new_tot = cap_new_tot[cap_new_tot.columns[(cap_new_tot > 0.001).any()]]
                cap_new_mapped = self._mappings(cap_new_tot, groupby="technology")
                self.results["Power plant new capacity (MW)"] = cap_new_mapped * self.UNIT_GW_TO_MW

        # Power plant activity (electricity generation)
        elec = self._plotdf(tec, ["electr"], "output", yr)

        # Handle storage losses
        if not elec.empty and "stor_ppl" in elec.columns:
            d_stor = self.msg.par("input", {"technology": "stor_ppl"})
            d_stor = d_stor.loc[d_stor["year_act"].isin(self.plotyrs)][
                ["technology", "year_act", "value"]
            ]
            if not d_stor.empty:
                d_stor = d_stor.groupby(["year_act"]).mean(numeric_only=True)
                elec["stor_ppl"] *= -d_stor["value"]

        elec_mapped = self._mappings(elec, groupby="technology")
        self.results["Electricity generation (TWh)"] = elec_mapped * self.UNIT_GWA_TO_TWH

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

        # Get activity
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

        # Add historical activity
        act_hist = self._attach_history(tec)
        activity_tot = activity.add(act_hist, fill_value=0)

        df_plot = inputs * activity_tot
        df_plot = df_plot.fillna(0)
        df_plot = df_plot[df_plot.columns[(df_plot > 0).any()]]
        return df_plot

    def _calculate_electricity_use(self, nodeloc: str, yr: int):
        """Calculate electricity usage by sector."""
        tecs = list(
            set(self.msg.par("input", {"commodity": "electr", "level": "final"}).get("technology", []))
        )
        tecs = tecs + ["stor_ppl"]

        df, df2 = self._model_output(tecs, nodeloc, "input", "electr")
        if df.empty:
            return

        df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)

        # Add historical data
        df_hist = self._add_history(tecs, nodeloc, df2, "technology")
        df = df.add(df_hist, fill_value=0)

        # Rename sectors
        rename_map = {
            "sp_el_RC": "buildings",
            "sp_el_I": "industry",
            "elec_trp": "transport"
        }
        df = df.rename(rename_map, axis=1)

        self.results["Electricity use (TWh)"] = df * self.UNIT_GWA_TO_TWH

    def _calculate_gas_results(self, nodeloc: str, yr: int):
        """Calculate natural gas supply and usage."""
        # Gas supply
        gas_tecs = ["gas_t_d", "gas_t_d_ch4", "gas_bal"]
        output_par = self.msg.par("output", {"commodity": "gas"})
        if not output_par.empty:
            tecs = list(set(output_par.technology) - set(gas_tecs))
            df, df2 = self._model_output(tecs, nodeloc, "output", "gas")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Gas supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Gas usage
        input_par = self.msg.par("input", {"commodity": "gas"})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(gas_tecs))
            df, df2 = self._model_output(tecs, nodeloc, "input", "gas")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Gas utilization (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_coal_results(self, nodeloc: str, yr: int):
        """Calculate coal supply and usage."""
        # Coal supply
        coal_tecs = ["coal_t_d", "coal_bal", "coal_exp"]
        output_par = self.msg.par("output", {"commodity": "coal"})
        if not output_par.empty:
            tecs = list(set(output_par.technology) - set(coal_tecs))
            df, df2 = self._model_output(tecs, nodeloc, "output", "coal")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Coal supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Coal usage
        coal_tecs = ["coal_t_d", "coal_bal", "coal_extr", "coal_extr_ch4"]
        input_par = self.msg.par("input", {"commodity": "coal"})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(coal_tecs))
            df, df2 = self._model_output(tecs, nodeloc, "input", "coal")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Coal utilization (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_oil_results(self, nodeloc: str, yr: int):
        """Calculate oil supply and derivatives."""
        # Oil derivatives supply
        output_par = self.msg.par("output", {"commodity": ["fueloil", "lightoil"], "level": ["secondary"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "output", ["fueloil", "lightoil"])
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Oil derivative supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Oil derivatives use
        input_par = self.msg.par("input", {"commodity": ["fueloil", "lightoil"]})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(["loil_t_d", "foil_t_d"]))
            df, df2 = self._model_output(tecs, nodeloc, "input", ["fueloil", "lightoil"])
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Oil derivative use (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Oil supply
        output_par = self.msg.par("output", {"commodity": ["crudeoil"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology) - set(["oil_bal", "oil_exp"]))
            df, df2 = self._model_output(tecs, nodeloc, "output", "crudeoil")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Oil supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_biomass_results(self, nodeloc: str, yr: int):
        """Calculate biomass supply and usage."""
        # Biomass supply
        output_par = self.msg.par("output", {"commodity": ["biomass"], "level": ["primary"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Biomass supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Biomass use
        input_par = self.msg.par("input", {"commodity": ["biomass"], "level": ["primary", "final"]})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(["biomass_t_d"]))
            df, df2 = self._model_output(tecs, nodeloc, "input", "biomass")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Biomass utilization (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_sector_results(self, nodeloc: str, yr: int):
        """Calculate energy use by sector."""
        order = self._get_commodity_order()

        # Transport
        # Step 1: Find technologies that output "transport" commodity
        output_par = self.msg.par("output", {"commodity": ["transport"]})
        if not output_par.empty:

            # Step 2: Get unique technologies (e.g., loil_trp, elec_trp, etc.)
            tecs = list(set(output_par.technology))

            # Step 3: Get ACT for these technologies and multiply by input coefficients
            df, df2 = self._model_output(tecs, nodeloc, "input")

            if not df.empty:
                # Step 4: Group by node, year and commodity to get energy use by fuel type
                # Keep long format to preserve node_loc for filtering in UI
                df = self._group(df, ["node_loc", "year_act", "commodity"], "product", 0.0, yr, keep_long=True)

                # Apply unit conversion
                df['value'] = df['value'] * self.UNIT_GWA_TO_PJ

                # Rename columns for clarity
                df = df.rename(columns={'year_act': 'year', 'commodity': 'category'})

                # Store as long-format DataFrame (already has unit conversion applied)
                self.results["Energy use Transport (PJ)"] = df

        # Industry
        output_par = self.msg.par("output", {"commodity": ["i_spec", "i_therm"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy use Industry (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Non-energy feedstock
        output_par = self.msg.par("output", {"commodity": ["i_feed"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Non-energy use Feedstock (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Buildings
        output_par = self.msg.par("output", {"commodity": ["rc_spec", "rc_therm", "non-comm"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy use Buildings (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_energy_balances(self, nodeloc: str, yr: int):
        """Calculate primary, final, and useful energy."""
        order = self._get_commodity_order()

        # Primary energy supply
        output_par = self.msg.par("output", {"level": ["primary"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)

                # Add renewables
                input_par = self.msg.par("input", {"level": ["renewable"]})
                if not input_par.empty:
                    tecs_re = list(set(input_par.technology))
                    df_re, df2_re = self._model_output(tecs_re, nodeloc, "input")
                    if not df_re.empty:
                        df_re = self._group(df_re, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_re = self._add_history(tecs_re, nodeloc, df2_re, "commodity")
                        df = df.add(self._com_order(df_re.add(df_hist_re, fill_value=0), order), fill_value=0)

                # Handle imports/exports
                tecs_imp = [x for x in self._get_all_technology_names() if str(x).endswith("_imp")]
                if tecs_imp:
                    df_imp, df2_imp = self._model_output(tecs_imp, nodeloc, "output")
                    if not df_imp.empty:
                        df_imp = self._group(df_imp, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_imp = self._add_history(tecs_imp, nodeloc, df2_imp, "commodity")
                        df_imp = self._com_order(df_imp.add(df_hist_imp, fill_value=0), order)
                        df = df.add(df_imp, fill_value=0)

                tecs_exp = [x for x in self._get_all_technology_names() if "_exp" in str(x)]
                if tecs_exp:
                    df_exp, df2_exp = self._model_output(tecs_exp, nodeloc, "output")
                    if not df_exp.empty:
                        df_exp = self._group(df_exp, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_exp = self._add_history(tecs_exp, nodeloc, df2_exp, "commodity")
                        df_exp = self._com_order(df_exp.add(df_hist_exp, fill_value=0), order)
                        df = df.add(-df_exp, fill_value=0)

                self.results["Primary energy supply (PJ)"] = self._com_order(df, order) * self.UNIT_GWA_TO_PJ

        # Final energy consumption
        # Final energy = fuel consumed by end-use technologies serving final demand sectors
        # These are technologies that OUTPUT to: transport, industry (i_spec, i_therm),
        # and buildings (rc_spec, rc_therm, non-comm)
        end_use_commodities = ["transport", "i_spec", "i_therm", "rc_spec", "rc_therm", "non-comm"]
        output_par = self.msg.par("output", {"commodity": end_use_commodities})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            # Get INPUT (fuel consumption) for these end-use technologies
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = df.add(df_hist, fill_value=0)
                df = self._com_order(df, order)
                self.results["Final energy consumption (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Useful energy
        output_par = self.msg.par("output", {"level": ["useful"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                self.results["Useful energy (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_trade(self, nodeloc: str, yr: int):
        """Calculate energy imports and exports."""
        order = self._get_commodity_order()

        # Exports
        tecs_exp = [x for x in self.msg.set("technology") if "_exp" in str(x)]
        if tecs_exp:
            df, df2 = self._model_output(tecs_exp, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs_exp, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy exports (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Imports
        tecs_imp = [x for x in self.msg.set("technology") if str(x).endswith("_imp")]
        if tecs_imp:
            df, df2 = self._model_output(tecs_imp, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs_imp, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy imports (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_emissions(self, nodeloc: str, yr: int):
        """Calculate total GHG emissions.

        Combines model EMISS variable with historical_emission parameter.
        Gets all emission types available in the data.
        """
        # Get EMISS variable - try multiple emission type patterns
        # First try to get all emissions (no filter)
        df_model = self.msg.var("EMISS", {"node": nodeloc})

        if df_model.empty:
            # Try without node filter as fallback
            df_model = self.msg.var("EMISS")

        # Get historical emissions from historical_emission parameter
        df_hist = self.msg.par("historical_emission", {"node": nodeloc})
        if df_hist.empty:
            df_hist = self.msg.par("historical_emission")

        # Determine year column for model data
        year_col = 'year' if 'year' in df_model.columns else 'year_act' if 'year_act' in df_model.columns else None

        result_df = pd.DataFrame()

        # Process model emissions
        if not df_model.empty and year_col:
            # Filter to plot years
            df_model = df_model[df_model[year_col].isin(self.plotyrs)]

            if 'emission' in df_model.columns:
                # Group by year and emission type
                model_grouped = df_model.groupby([year_col, 'emission'])['lvl'].sum().reset_index()
                model_pivot = model_grouped.pivot(index=year_col, columns='emission', values='lvl').fillna(0)
                result_df = model_pivot

        # Process historical emissions
        if not df_hist.empty:
            hist_year_col = 'year' if 'year' in df_hist.columns else 'year_act' if 'year_act' in df_hist.columns else None
            if hist_year_col and 'emission' in df_hist.columns:
                # Filter to plot years
                df_hist = df_hist[df_hist[hist_year_col].isin(self.plotyrs)]

                if not df_hist.empty:
                    value_col = 'value' if 'value' in df_hist.columns else 'lvl'
                    hist_grouped = df_hist.groupby([hist_year_col, 'emission'])[value_col].sum().reset_index()
                    hist_pivot = hist_grouped.pivot(index=hist_year_col, columns='emission', values=value_col).fillna(0)

                    # Combine historical and model data
                    if result_df.empty:
                        result_df = hist_pivot
                    else:
                        # Add historical data for years not in model
                        result_df = result_df.combine_first(hist_pivot).fillna(0)

        if not result_df.empty:
            # Sort by year index
            result_df = result_df.sort_index()
            # Filter out columns that are all zeros
            result_df = result_df.loc[:, (result_df != 0).any()]

            if not result_df.empty:
                self.results["Total GHG emissions (MtCeq)"] = result_df

    def _calculate_prices(self, nodeloc: str, yr: int):
        """Calculate commodity prices."""
        # Electricity price
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc, "level": "secondary"})
        if not price.empty:
            price = price.loc[price.year.isin(self.plotyrs)]
            df1 = price[["year", "commodity", "lvl"]]
            df1 = df1.loc[df1["commodity"] == "electr"].copy()
            df1["lvl"] = df1["lvl"] * 0.1142  # convert $/GWa -> $/MWh
            df = self._group(df1, ["year", "commodity"], "lvl", 0.0, yr)
            self.results["Electricity Price ($/MWh)"] = df

        # Primary energy prices
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc, "level": "primary"})
        if not price.empty:
            df1 = price[["year", "commodity", "lvl"]]
            df = self._group(df1, ["year", "commodity"], "lvl", 0.0, yr)
            self.results["Primary Energy Prices ($/MWh)"] = df

        # Secondary energy prices
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc, "level": "secondary"})
        if not price.empty:
            df1 = price[["year", "commodity", "lvl"]]
            df = self._group(df1, ["year", "commodity"], "lvl", 0.0, yr)
            self.results["Secondary Energy Prices ($/MWh)"] = df

        # Useful energy prices
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc, "level": "useful"})
        if not price.empty:
            df1 = price[["year", "commodity", "lvl"]]
            df1 = df1.loc[df1.commodity.isin(['i_spec', 'i_therm', 'rc_spec', 'rc_therm', 'transport'])].copy()
            df1["lvl"] = df1["lvl"] * 0.1142  # convert $/GWa -> $/MWh
            df = self._group(df1, ["year", "commodity"], "lvl", 0.0, yr)
            self.results["Energy Prices ($/MWh)"] = df

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

    # =========================================================================
    # Common Helper Methods for Sector/Fuel Mapping
    # =========================================================================

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

    def _map_technologies_to_sectors(self, technologies: List[str]) -> Dict[str, List[str]]:
        """Map technologies to sectors based on their output commodity."""
        sector_coms = self._get_sector_commodities()
        sector_tecs = {sector: [] for sector in sector_coms}
        sector_tecs["Other"] = []

        output_par = self.msg.par("output")

        if output_par.empty:
            # If no output parameter, try to map by technology name patterns
            return self._map_technologies_to_sectors_by_name(technologies, sector_tecs)

        # Determine technology column name (could be 'technology' or 'tec')
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
        """Fallback: Map technologies to sectors by name patterns when output parameter is unavailable."""
        # Define name patterns for each sector
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

    def _get_technologies_by_input_fuel(self, fuel_commodities: List[str]) -> List[str]:
        """Get technologies that use specific input commodities."""
        input_par = self.msg.par("input", {"commodity": fuel_commodities})
        if input_par.empty:
            return []
        # Handle column name variations (technology vs tec)
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

    def _get_renewable_technologies(self) -> List[str]:
        """Get technologies that use renewable inputs."""
        input_par = self.msg.par("input", {"level": ["renewable"]})
        if input_par.empty:
            return []
        return list(input_par['technology'].unique())

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
    # Electricity Analyses
    # =========================================================================

    def _calculate_electricity_generation_by_source(self, nodeloc: str, yr: int):
        """Calculate electricity generation grouped by source/fuel type."""
        # Get ALL electricity-producing technologies (not just secondary level)
        # This ensures renewables are included regardless of output level
        output_par = self.msg.par("output", {"commodity": ["electr"]})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        # Also include technologies with renewable inputs that produce electricity
        renewable_tecs = self._get_renewable_technologies()
        for tec in renewable_tecs:
            # Check if this renewable tech outputs electricity
            tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
            if not tec_output.empty and tec not in tecs:
                tecs.append(tec)

        # Also catch any technologies with renewable-related names
        all_tecs = self.msg.set("technology")
        if len(all_tecs) > 0:
            renewable_patterns = ['solar', 'wind', 'hydro', 'geo', 'bio_ppl', 'csp']
            for tec in all_tecs:
                tec_str = str(tec).lower()
                if any(pattern in tec_str for pattern in renewable_patterns):
                    # Check if outputs electricity
                    tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
                    if not tec_output.empty and tec not in tecs:
                        tecs.append(tec)

        if not tecs:
            return

        # Get activity and multiply by output coefficient
        df, df2 = self._model_output(tecs, nodeloc, "output", "electr")
        if df.empty:
            return

        # Group by technology to get generation by source
        df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)

        # Map to technology categories (includes renewable mappings)
        df_mapped = self._mappings(df, groupby="technology")

        self.results["Electricity generation by source (TWh)"] = df_mapped * self.UNIT_GWA_TO_TWH

    def _calculate_electricity_use_by_sector(self, nodeloc: str, yr: int):
        """Calculate electricity consumption by consuming technologies.

        Gets technologies that consume (input) electricity at the final level,
        excluding power generation technologies. Groups by technology name
        to show actual consuming technologies like elec_i, hp_el_i, etc.

        Also calculates:
        - Storage losses (input - output for storage technologies)
        - Grid/T&D losses (input - output for transmission technologies)
        - Renewables curtailment (if curtailment data is available)
        """
        # First, get ALL technologies that input electricity (any level)
        # to identify storage and grid technologies for loss calculations
        all_input_par = self.msg.par("input", {"commodity": ["electr"]})
        if all_input_par.empty:
            return

        all_elec_tecs = list(set(all_input_par['technology'].tolist()))

        # Identify storage and grid technologies (will calculate losses separately)
        storage_tecs = [t for t in all_elec_tecs if "stor" in t.lower()]
        grid_tecs = [t for t in all_elec_tecs if any(g in t.lower() for g in ["elec_t_d", "grid", "t_d"])]

        # Get technologies that input electricity at the "final" level for end-use
        final_input_par = self.msg.par("input", {"commodity": ["electr"], "level": ["final"]})
        if not final_input_par.empty:
            final_elec_tecs = list(set(final_input_par['technology'].tolist()))
        else:
            # Fallback: use all if no final level exists
            final_elec_tecs = all_elec_tecs

        # Get power generation technologies to EXCLUDE them
        # Power plants produce electricity, they don't consume it as end users
        output_elec = self.msg.par("output", {"commodity": ["electr"], "level": ["secondary"]})
        power_gen_tecs = set(output_elec['technology'].tolist()) if not output_elec.empty else set()

        # Exclude power generation, storage, and grid from consumer list
        exclude_tecs = power_gen_tecs | set(storage_tecs) | set(grid_tecs)

        # Filter to only end-use consumer technologies
        consumer_tecs = [t for t in final_elec_tecs if t not in exclude_tecs]

        # Initialize result DataFrame
        result_df = pd.DataFrame()

        # 1. Calculate end-use consumption by technology
        if consumer_tecs:
            df, df2 = self._model_output(consumer_tecs, nodeloc, "input", "electr")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(consumer_tecs, nodeloc, df2, "technology")
                if not df_hist.empty and len(df_hist.columns) > 0:
                    df = df.add(df_hist, fill_value=0)
                result_df = df

        # 2. Calculate storage losses (input - output)
        storage_losses = self._calculate_losses(storage_tecs, nodeloc, yr)
        if storage_losses is not None and not storage_losses.empty:
            result_df["Storage losses"] = storage_losses

        # 3. Calculate grid/T&D losses (input - output)
        grid_losses = self._calculate_losses(grid_tecs, nodeloc, yr)
        if grid_losses is not None and not grid_losses.empty:
            result_df["Grid losses"] = grid_losses

        # 4. Calculate renewables curtailment
        curtailment = self._calculate_curtailment(nodeloc, yr)
        if curtailment is not None and not curtailment.empty:
            result_df["Curtailment"] = curtailment

        # Fill NaN values with 0 (e.g., years without storage/grid activity)
        if not result_df.empty:
            result_df = result_df.fillna(0)

        # Filter out columns with all zeros
        if not result_df.empty:
            result_df = result_df.loc[:, (result_df != 0).any()]

        if result_df.empty:
            return

        # Convert GWa to TWh and store
        self.results["Electricity use by sector (TWh)"] = result_df * self.UNIT_GWA_TO_TWH

    def _calculate_losses(self, tecs: List[str], nodeloc: str, yr: int) -> Optional[pd.Series]:
        """Calculate losses for storage or grid technologies.

        Losses = input electricity - output electricity (positive = loss)
        """
        if not tecs:
            return None

        # Get input (electricity consumed)
        df_in, _ = self._model_output(tecs, nodeloc, "input", "electr")
        if df_in.empty:
            return None

        # Get output (electricity produced)
        df_out, _ = self._model_output(tecs, nodeloc, "output", "electr")

        # Group by year
        input_by_year = df_in.groupby("year_act")["product"].sum()

        if not df_out.empty:
            output_by_year = df_out.groupby("year_act")["product"].sum()
            # Losses = input - output
            losses = input_by_year.subtract(output_by_year, fill_value=0)
        else:
            # No output means all input is "lost" (though this is unusual)
            losses = input_by_year

        # Only return positive losses
        losses = losses.clip(lower=0)

        return losses if not losses.empty and losses.sum() > 0 else None

    def _calculate_curtailment(self, nodeloc: str, yr: int) -> Optional[pd.Series]:
        """Calculate renewables curtailment.

        Curtailment is calculated as the difference between potential generation
        (capacity * capacity factor) and actual generation for renewable technologies.
        """
        # Get renewable technologies
        renewable_tecs = self._get_renewable_technologies()
        if not renewable_tecs:
            return None

        # Get actual generation (ACT)
        act = self.msg.var("ACT", {"technology": renewable_tecs})
        if act.empty:
            return None

        # Get capacity (CAP)
        cap = self.msg.var("CAP", {"technology": renewable_tecs})
        if cap.empty:
            return None

        # Get capacity factor from output parameter
        output_par = self.msg.par("output", {"technology": renewable_tecs, "commodity": ["electr"]})
        if output_par.empty:
            return None

        # Calculate actual generation by year
        act_by_year = act.groupby("year_act")["lvl"].sum()

        # Calculate potential generation: CAP * 8760 hours * avg capacity factor
        # This is a simplified calculation
        cap_by_year = cap.groupby("year_act")["lvl"].sum()
        avg_cf = output_par["value"].mean() if not output_par.empty else 0.3

        # Potential = CAP * hours_per_year * capacity_factor (approximate)
        # 1 GW for 1 year at 100% CF = 8.76 TWh (in GWa units, that's 1 GWa)
        potential_by_year = cap_by_year * avg_cf

        # Curtailment = potential - actual (only if positive)
        curtailment = potential_by_year.subtract(act_by_year, fill_value=0)
        curtailment = curtailment.clip(lower=0)

        return curtailment if not curtailment.empty and curtailment.sum() > 0 else None

    def _calculate_power_capacity_with_renewables(self, nodeloc: str, yr: int):
        """Calculate power plant capacity including renewables."""
        cap = self.msg.var("CAP", {"year_vtg": self.plotyrs})
        if cap.empty:
            return

        # Get ALL electricity-producing technologies (any level, not just secondary)
        output_par = self.msg.par("output", {"commodity": ["electr"]})
        tecs_elec = list(set(output_par.technology)) if not output_par.empty else []

        # Also include technologies with renewable inputs
        renewable_tecs = self._get_renewable_technologies()
        for tec in renewable_tecs:
            tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
            if not tec_output.empty and tec not in tecs_elec:
                tecs_elec.append(tec)

        # Also catch technologies with renewable-related names
        all_tecs_in_model = self.msg.set("technology")
        if len(all_tecs_in_model) > 0:
            renewable_patterns = ['solar', 'wind', 'hydro', 'geo', 'bio_ppl', 'csp']
            for tec in all_tecs_in_model:
                tec_str = str(tec).lower()
                if any(pattern in tec_str for pattern in renewable_patterns):
                    tec_output = self.msg.par("output", {"technology": [tec], "commodity": ["electr"]})
                    if not tec_output.empty and tec not in tecs_elec:
                        tecs_elec.append(tec)

        all_tecs = list(set(tecs_elec + ["stor_ppl"]))

        # Get capacity for these technologies
        ppl_cap = cap.loc[cap.technology.isin(all_tecs)][["technology", "year_act", "lvl"]]
        if ppl_cap.empty:
            return

        ppl_cap = ppl_cap.groupby(["technology", "year_act"], as_index=False).sum(numeric_only=True)
        ppl_cap = ppl_cap.pivot(index="year_act", columns="technology")
        ppl_cap = ppl_cap[ppl_cap.columns[(ppl_cap != 0).any()]]
        if len(ppl_cap.columns) > 0:
            ppl_cap.columns = ppl_cap.columns.droplevel(0)
        ppl_cap = ppl_cap.loc[:, (ppl_cap > 0).any()]

        ppl_cap_mapped = self._mappings(ppl_cap, groupby="technology")
        self.results["Power capacity with renewables (MW)"] = ppl_cap_mapped * self.UNIT_GW_TO_MW

    # =========================================================================
    # Emissions Analyses
    # =========================================================================

    def _calculate_emissions_by_sector(self, nodeloc: str, yr: int):
        """Calculate CO2 emissions by technology based on fuel consumption.

        For each technology that consumes fossil fuels:
        1. Get fuel input from 'input' parameter
        2. Get activity from ACT variable
        3. Calculate: emissions = ACT × input_coefficient × fuel_emission_factor
        4. Group by technology name
        """
        # Standard CO2 emission factors (Mt CO2 per GWa of fuel consumed)
        fuel_emission_factors = {
            # Coal
            "coal": 3.0, "coal_rc": 3.0, "coal_i": 3.0,
            # Oil products
            "crudeoil": 2.4, "lightoil": 2.4, "loil_rc": 2.4, "loil_i": 2.4,
            "fueloil": 2.6, "foil_rc": 2.6, "foil_i": 2.6,
            # Gas
            "gas": 1.8, "gas_rc": 1.8, "gas_i": 1.8,
        }

        # Get ACT variable
        act = self.msg.var("ACT")
        if act.empty:
            return

        # Get input parameter
        input_par = self.msg.par("input")
        if input_par.empty:
            return

        # Determine column names
        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        input_tec_col = 'technology' if 'technology' in input_par.columns else 'tec' if 'tec' in input_par.columns else None

        if not act_year_col or not act_tec_col or not input_tec_col:
            return

        # Filter ACT to plot years
        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return

        # Get all fossil fuel commodities
        fossil_commodities = list(fuel_emission_factors.keys())

        # Filter input to fossil fuels only
        fossil_input = input_par[input_par['commodity'].isin(fossil_commodities)]
        if fossil_input.empty:
            return

        # Get unique technologies that consume fossil fuels
        fossil_tecs = list(fossil_input[input_tec_col].unique())

        tech_results = {}

        for tec in fossil_tecs:
            # Get input coefficients for this technology (fuel -> technology)
            tec_input = fossil_input[fossil_input[input_tec_col] == tec]
            if tec_input.empty:
                continue

            # Get activity for this technology
            tec_act = act[act[act_tec_col] == tec]
            if tec_act.empty:
                continue

            # Sum activity by year
            act_by_year = tec_act.groupby(act_year_col)['lvl'].sum()

            # Calculate emissions for each fuel this technology uses
            total_emissions = pd.Series(0.0, index=act_by_year.index)

            for _, row in tec_input.iterrows():
                commodity = row['commodity']
                input_coef = row['value']
                ef = fuel_emission_factors.get(commodity, 0)

                if ef > 0 and input_coef > 0:
                    # emissions = activity × input_coefficient × emission_factor
                    fuel_emissions = act_by_year * input_coef * ef
                    total_emissions = total_emissions.add(fuel_emissions, fill_value=0)

            if total_emissions.sum() > 0:
                tech_results[tec] = total_emissions

        if tech_results:
            result_df = pd.DataFrame(tech_results)
            result_df = result_df.sort_index()
            # Filter out columns that are all zeros
            result_df = result_df.loc[:, (result_df != 0).any()]
            # Sort columns by total emissions (descending)
            if not result_df.empty:
                col_totals = result_df.sum().sort_values(ascending=False)
                result_df = result_df[col_totals.index]
                self.results["Emissions by technology (Mt CO2)"] = result_df

    def _calculate_emissions_from_activity_by_sector(self) -> Dict[str, pd.Series]:
        """Calculate emissions from ACT × emission_factor, grouped by sector.

        This is a fallback when EMISS variable is not available.
        Returns dict of {sector_name: pd.Series with year index}.
        """
        sector_results = {}

        # Get emission_factor parameter
        ef = self.msg.par("emission_factor")
        if ef.empty:
            return sector_results

        # Get ACT variable
        act = self.msg.var("ACT")
        if act.empty:
            return sector_results

        # Get year column and technology column for ACT
        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        if not act_year_col or not act_tec_col:
            return sector_results

        # Filter to plot years
        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return sector_results

        # Get technology column for emission_factor
        ef_tec_col = 'technology' if 'technology' in ef.columns else 'tec' if 'tec' in ef.columns else None
        if not ef_tec_col:
            return sector_results

        all_tecs = list(ef[ef_tec_col].unique())
        if not all_tecs:
            return sector_results

        # Map technologies to sectors
        sector_tecs = self._map_technologies_to_sectors(all_tecs)

        # Calculate emissions for each sector
        for sector, tecs in sector_tecs.items():
            if not tecs:
                continue

            # Get activity for these technologies
            sector_act = act[act[act_tec_col].isin(tecs)]
            if sector_act.empty:
                continue

            # Get emission factors for these technologies
            sector_ef = ef[ef[ef_tec_col].isin(tecs)]
            if sector_ef.empty:
                continue

            # Calculate emissions = ACT × emission_factor
            # Average emission factor by technology and year
            ef_year_col = 'year_act' if 'year_act' in sector_ef.columns else 'year' if 'year' in sector_ef.columns else None
            if ef_year_col:
                ef_avg = sector_ef.groupby([ef_year_col, ef_tec_col])['value'].mean().reset_index()
            else:
                ef_avg = sector_ef.groupby([ef_tec_col])['value'].mean().reset_index()
                ef_avg[act_year_col] = self.plotyrs[0]  # Use first plot year if no year in ef

            # Merge and calculate
            act_grouped = sector_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            if ef_year_col:
                merged = act_grouped.merge(
                    ef_avg,
                    left_on=[act_year_col, act_tec_col],
                    right_on=[ef_year_col, ef_tec_col],
                    how='inner'
                )
            else:
                merged = act_grouped.merge(
                    ef_avg,
                    left_on=[act_tec_col],
                    right_on=[ef_tec_col],
                    how='inner'
                )

            if merged.empty:
                continue

            merged['emissions'] = merged['lvl'] * merged['value']
            sector_sum = merged.groupby(act_year_col)['emissions'].sum()
            if not sector_sum.empty:
                sector_results[sector] = sector_sum

        return sector_results

    def _calculate_emissions_by_type(self, nodeloc: str, yr: int):
        """Calculate emissions grouped by emission type (CO2, CH4, N2O, etc.).

        Uses the 'emission' column in EMISS variable to group by emission type.
        """
        emiss = self.msg.var("EMISS")
        emission_results = {}

        if not emiss.empty:
            year_col = 'year' if 'year' in emiss.columns else 'year_act' if 'year_act' in emiss.columns else None

            if year_col and 'emission' in emiss.columns:
                emiss_filtered = emiss[emiss[year_col].isin(self.plotyrs)]

                if not emiss_filtered.empty:
                    for emission_type in emiss_filtered['emission'].unique():
                        type_data = emiss_filtered[emiss_filtered['emission'] == emission_type]
                        if type_data.empty:
                            continue
                        type_sum = type_data.groupby(year_col)['lvl'].sum()
                        if type_sum.sum() > 0:
                            display_name = str(emission_type).upper()
                            emission_results[display_name] = type_sum

        if emission_results:
            result_df = pd.DataFrame(emission_results)
            result_df = result_df.sort_index()
            result_df = result_df.loc[:, (result_df != 0).any()]
            if not result_df.empty:
                self.results["Emissions by type (Mt)"] = result_df

    def _calculate_emissions_by_fuel(self, nodeloc: str, yr: int):
        """Calculate CO2 emissions by fuel type based on technology activity.

        Calculates emissions from fuel consumption using:
        1. Get technologies that consume each fuel (from input parameter)
        2. Get their activity (ACT variable)
        3. Apply standard CO2 emission factors per fuel type
        4. Sum by fuel category

        Emission factors are approximate values in Mt CO2 per GWa of fuel input.
        """
        # Standard emission factors (Mt CO2 per GWa of fuel consumed)
        # Based on typical carbon content: coal ~95, oil ~75, gas ~56 kg CO2/GJ
        # 1 GWa = 31.536 PJ, so multiply kg/GJ by 31.536 to get Mt/GWa (and divide by 1000 for Mt)
        emission_factors = {
            "Coal": 3.0,      # ~95 kg CO2/GJ × 31.536 / 1000 ≈ 3.0 Mt/GWa
            "Oil": 2.4,       # ~75 kg CO2/GJ × 31.536 / 1000 ≈ 2.4 Mt/GWa
            "Gas": 1.8,       # ~56 kg CO2/GJ × 31.536 / 1000 ≈ 1.8 Mt/GWa
            "Biomass": 0.0,   # Considered carbon-neutral (biogenic CO2)
        }

        # Get ACT variable
        act = self.msg.var("ACT")
        if act.empty:
            return

        # Determine column names
        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None

        if not act_year_col or not act_tec_col:
            return

        # Filter to plot years
        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return

        # Get input parameter to find fuel consumption
        input_par = self.msg.par("input")
        if input_par.empty:
            return

        input_tec_col = 'technology' if 'technology' in input_par.columns else 'tec' if 'tec' in input_par.columns else None
        if not input_tec_col:
            return

        fuel_results = {}

        # Define fuel commodities to look for
        fuel_commodities = {
            "Coal": ["coal", "coal_rc", "coal_i"],
            "Oil": ["crudeoil", "lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i"],
            "Gas": ["gas", "gas_rc", "gas_i"],
            "Biomass": ["biomass", "biomass_rc", "biomass_nc"],
        }

        for fuel_name, commodities in fuel_commodities.items():
            emission_factor = emission_factors.get(fuel_name, 0)
            if emission_factor == 0:
                continue  # Skip zero-emission fuels

            # Find technologies that input this fuel
            fuel_input = input_par[input_par['commodity'].isin(commodities)]
            if fuel_input.empty:
                continue

            fuel_tecs = list(fuel_input[input_tec_col].unique())

            # Get activity for these technologies
            fuel_act = act[act[act_tec_col].isin(fuel_tecs)]
            if fuel_act.empty:
                continue

            # Get input coefficients (how much fuel per unit activity)
            # Average input coefficient per technology and year
            input_year_col = 'year_act' if 'year_act' in fuel_input.columns else 'year' if 'year' in fuel_input.columns else None
            if input_year_col:
                input_coef = fuel_input.groupby([input_year_col, input_tec_col])['value'].mean().reset_index()
            else:
                input_coef = fuel_input.groupby([input_tec_col])['value'].mean().reset_index()

            # Sum activity by year and technology
            act_grouped = fuel_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            # Merge activity with input coefficients
            if input_year_col:
                merged = act_grouped.merge(
                    input_coef,
                    left_on=[act_year_col, act_tec_col],
                    right_on=[input_year_col, input_tec_col],
                    how='inner'
                )
            else:
                merged = act_grouped.merge(
                    input_coef,
                    left_on=[act_tec_col],
                    right_on=[input_tec_col],
                    how='inner'
                )

            if merged.empty:
                continue

            # Calculate fuel consumption = activity × input coefficient
            # Then emissions = fuel consumption × emission factor
            merged['fuel_use'] = merged['lvl'] * merged['value']
            merged['emissions'] = merged['fuel_use'] * emission_factor

            # Sum emissions by year
            fuel_sum = merged.groupby(act_year_col)['emissions'].sum()
            if fuel_sum.sum() > 0:
                fuel_results[fuel_name] = fuel_sum

        if fuel_results:
            result_df = pd.DataFrame(fuel_results)
            result_df = result_df.sort_index()
            result_df = result_df.loc[:, (result_df != 0).any()]
            if not result_df.empty:
                self.results["Emissions by fuel (Mt CO2)"] = result_df

    def _map_technologies_to_fuels_by_name(self, technologies: List[str]) -> Dict[str, List[str]]:
        """Map technologies to fuel types by name patterns when input parameter is unavailable."""
        fuel_tecs = {fuel: [] for fuel in self._get_fuel_commodities().keys()}

        # Define name patterns for each fuel
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

    def _calculate_emissions_from_activity_by_fuel(self) -> Dict[str, pd.Series]:
        """Calculate emissions from ACT × emission_factor, grouped by fuel.

        This is a fallback when EMISS variable is not available.
        Returns dict of {fuel_name: pd.Series with year index}.
        """
        fuel_results = {}

        # Get emission_factor parameter
        ef = self.msg.par("emission_factor")
        if ef.empty:
            return fuel_results

        # Get ACT variable
        act = self.msg.var("ACT")
        if act.empty:
            return fuel_results

        # Get year column and technology column for ACT
        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        if not act_year_col or not act_tec_col:
            return fuel_results

        # Filter to plot years
        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return fuel_results

        # Get technology column for emission_factor
        ef_tec_col = 'technology' if 'technology' in ef.columns else 'tec' if 'tec' in ef.columns else None
        if not ef_tec_col:
            return fuel_results

        all_tecs = list(ef[ef_tec_col].unique())
        if not all_tecs:
            return fuel_results

        fuel_coms = self._get_fuel_commodities()

        # Try to get technologies by input fuel first
        fuel_tecs_mapping = {}
        use_name_fallback = True

        for fuel_name, commodities in fuel_coms.items():
            fuel_tecs = self._get_technologies_by_input_fuel(commodities)
            if fuel_tecs:
                fuel_tecs_mapping[fuel_name] = fuel_tecs
                use_name_fallback = False

        # If input parameter doesn't work, fall back to name-based mapping
        if use_name_fallback:
            fuel_tecs_mapping = self._map_technologies_to_fuels_by_name(all_tecs)

        # Calculate emissions for each fuel type
        for fuel_name, fuel_tecs in fuel_tecs_mapping.items():
            matching_tecs = [t for t in all_tecs if t in fuel_tecs]

            if not matching_tecs:
                continue

            # Get activity for these technologies
            fuel_act = act[act[act_tec_col].isin(matching_tecs)]
            if fuel_act.empty:
                continue

            # Get emission factors for these technologies
            fuel_ef = ef[ef[ef_tec_col].isin(matching_tecs)]
            if fuel_ef.empty:
                continue

            # Calculate emissions = ACT × emission_factor
            ef_year_col = 'year_act' if 'year_act' in fuel_ef.columns else 'year' if 'year' in fuel_ef.columns else None
            if ef_year_col:
                ef_avg = fuel_ef.groupby([ef_year_col, ef_tec_col])['value'].mean().reset_index()
            else:
                ef_avg = fuel_ef.groupby([ef_tec_col])['value'].mean().reset_index()
                ef_avg[act_year_col] = self.plotyrs[0]

            # Merge and calculate
            act_grouped = fuel_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            if ef_year_col:
                merged = act_grouped.merge(
                    ef_avg,
                    left_on=[act_year_col, act_tec_col],
                    right_on=[ef_year_col, ef_tec_col],
                    how='inner'
                )
            else:
                merged = act_grouped.merge(
                    ef_avg,
                    left_on=[act_tec_col],
                    right_on=[ef_tec_col],
                    how='inner'
                )

            if merged.empty:
                continue

            merged['emissions'] = merged['lvl'] * merged['value']
            fuel_sum = merged.groupby(act_year_col)['emissions'].sum()
            if not fuel_sum.empty:
                fuel_results[fuel_name] = fuel_sum

        return fuel_results

    # =========================================================================
    # Energy Balance Analyses
    # =========================================================================

    def _calculate_energy_exports_by_fuel(self, nodeloc: str, yr: int):
        """Calculate energy exports grouped by fuel commodity."""
        order = self._get_commodity_order()
        tecs_exp = [x for x in self._get_all_technology_names() if "_exp" in str(x)]
        if not tecs_exp:
            return

        # Use "output" parameter - export techs may not have "input" defined
        df, df2 = self._model_output(tecs_exp, nodeloc, "output")
        if df.empty:
            return

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
        df_hist = self._add_history(tecs_exp, nodeloc, df2, "commodity")
        df = self._com_order(df.add(df_hist, fill_value=0), order)
        self.results["Energy exports by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_energy_imports_by_fuel(self, nodeloc: str, yr: int):
        """Calculate energy imports grouped by fuel commodity."""
        order = self._get_commodity_order()
        tecs_imp = [x for x in self._get_all_technology_names() if str(x).endswith("_imp")]
        if not tecs_imp:
            return

        df, df2 = self._model_output(tecs_imp, nodeloc, "output")
        if df.empty:
            return

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
        df_hist = self._add_history(tecs_imp, nodeloc, df2, "commodity")
        df = self._com_order(df.add(df_hist, fill_value=0), order)
        self.results["Energy imports by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_feedstock_by_fuel(self, nodeloc: str, yr: int):
        """
        Calculate non-energy feedstock consumption by fuel type.
        
        Output: "Feedstock by fuel (PJ)"
        
        Calculation:
        1. Get technologies from `output` where `commodity = "i_feed"` (industrial feedstock)
        2. These are technologies using fuels for non-energy purposes (petrochemicals, etc.)
        3. Get `ACT` for these technologies
        4. Multiply by `input` parameter to get fuel consumption for feedstock
        5. Group by input commodity (fuel type)
        
        **Implementation Details:**
        - Uses `_model_output()` to get activity * input coefficients
        - Groups by input commodity to show fuel type breakdown
        - Adds historical data via `_add_history()`
        - Unit conversion: 31.536 (GWa → PJ)
        """
        print("\n=== FEEDSTOCK DEBUG ===")
        print(f"nodeloc={nodeloc}, yr={yr}")
        
        # Get technologies that output feedstock commodity
        output_par = self.msg.par("output", {"commodity": ["i_feed"]})
        print(f"Output parameter shape: {output_par.shape if not output_par.empty else 'empty'}")
        
        if output_par.empty:
            print("No output data for 'i_feed' commodity")
            # Try without filter to see what commodities exist
            all_output = self.msg.par("output")
            if not all_output.empty:
                print(f"All output commodities: {all_output['commodity'].unique().tolist()}")
            print("=== END FEEDSTOCK DEBUG ===\n")
            return
        
        tecs = list(set(output_par.technology))
        print(f"Technologies outputting 'i_feed': {tecs}")
        
        if not tecs:
            print("No technologies found")
            print("=== END FEEDSTOCK DEBUG ===\n")
            return
        
        # Get ACT for these technologies
        act_data = self.msg.var("ACT", {"technology": tecs})
        print(f"ACT data shape: {act_data.shape if not act_data.empty else 'empty'}")
        
        # Get INPUT parameter for these technologies
        input_par = self.msg.par("input", {"technology": tecs})
        print(f"Input parameter shape: {input_par.shape if not input_par.empty else 'empty'}")
        
        if not input_par.empty:
            print(f"Input commodities for feedstock techs: {input_par['commodity'].unique().tolist()}")
        
        # Get model output (ACT * input coefficient) for feedstock technologies
        df, df2 = self._model_output(tecs, nodeloc, "input")
        print(f"Model output df shape: {df.shape if not df.empty else 'empty'}")
        print(f"Model output df2 shape: {df2.shape if not df2.empty else 'empty'}")
        
        if df.empty:
            print("Model output is empty - no data to process")
            print("=== END FEEDSTOCK DEBUG ===\n")
            return
        
        print(f"Model output columns: {df.columns.tolist()}")
        
        # Group by year and input commodity (fuel type)
        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
        print(f"After grouping: {df.shape if not df.empty else 'empty'}")
        
        # Add historical data
        df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
        print(f"Historical data shape: {df_hist.shape if not df_hist.empty else 'empty'}")
        
        # Combine historical and model results
        if not df_hist.empty:
            df = df.add(df_hist, fill_value=0)
        
        # Get commodity order
        order = self._get_commodity_order()
        df = self._com_order(df, order)
        
        print(f"Final result shape: {df.shape if not df.empty else 'empty'}")
        if not df.empty:
            print(f"Final result columns: {df.columns.tolist()}")
            print(f"Final result:\n{df}")
        
        # Convert to PJ
        self.results["Feedstock by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ
        print("=== END FEEDSTOCK DEBUG ===\n")

    def _calculate_oil_derivatives_supply(self, nodeloc: str, yr: int):
        """Calculate oil derivatives production and supply."""
        # Oil product commodities
        oil_products = ["lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i",
                        "diesel", "gasoline", "kerosene", "naphtha", "lpg"]

        # Get refinery technologies (output oil products)
        output_par = self.msg.par("output", {"commodity": oil_products})
        if output_par.empty:
            return

        refinery_tecs = list(set(output_par.technology))
        df, df2 = self._model_output(refinery_tecs, nodeloc, "output")
        if df.empty:
            return

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)

        # Filter to only oil products
        if isinstance(df, pd.DataFrame):
            df = df[[col for col in df.columns if col in oil_products]]

        self.results["Oil derivatives supply (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_oil_derivatives_use(self, nodeloc: str, yr: int):
        """
        Calculate oil derivatives consumption by sector.
        
        Output: "Oil derivatives use by sector (PJ)"
        
        Calculation:
        1. Get technologies that input oil products: `input` where commodity in oil_products
        2. Map to sectors using `output` parameter:
           - Power generation: output "electr"
           - Industry: output "i_spec", "i_therm"
           - Buildings: output "rc_spec", "rc_therm"
           - Transport: output "transport"
           - Other: remaining technologies
        3. Get `ACT` for these technologies
        4. Multiply by `input` parameter value
        5. Group by sector and oil product type
        
        **Implementation Details:**
        - Uses `_map_technologies_to_sectors()` for sector mapping
        - Filters out refinery technologies (they produce, not consume)
        - Handles column name variations (technology vs tec)
        - Unit conversion: 31.536 (GWa → PJ)
        """
        # Oil product commodities
        oil_products = ["lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i",
                        "diesel", "gasoline", "kerosene", "naphtha", "lpg"]
        
        # Get technologies that input oil products
        input_par = self.msg.par("input", {"commodity": oil_products})
        if input_par.empty:
            return
        
        all_oil_tecs = list(set(input_par['technology']))
        if not all_oil_tecs:
            return
        
        # Get refinery technologies (output oil products) - EXCLUDE these as they produce, not consume
        output_par = self.msg.par("output", {"commodity": oil_products})
        refinery_tecs = list(set(output_par['technology'])) if not output_par.empty else []
        
        # Filter out refinery technologies from consumption analysis
        consumer_tecs = [t for t in all_oil_tecs if t not in refinery_tecs]
        
        if not consumer_tecs:
            return
        
        # Map technologies to sectors
        sector_tecs = self._map_technologies_to_sectors(consumer_tecs)
        
        # Remove exports from sectors (handle separately)
        export_tecs = [t for t in consumer_tecs if '_exp' in str(t).lower() or 'export' in str(t).lower()]
        for sector in list(sector_tecs.keys()):
            sector_tecs[sector] = [t for t in sector_tecs.get(sector, []) if t not in export_tecs]
        
        # Add exports as a separate category
        if export_tecs:
            sector_tecs["Exports"] = export_tecs
        
        # DEBUG: Print sector mapping
        print("\n=== OIL DERIVATIVES USE SECTOR MAPPING ===")
        for sector, tecs in sector_tecs.items():
            if tecs:
                print(f"{sector}: {tecs}")
        print("=== END SECTOR MAPPING ===\n")
        
        # Helper function to calculate oil use from technologies
        def calculate_oil_use_from_tecs(tecs, commodity_filter=None):
            """Calculate oil use from a list of technologies."""
            if not tecs:
                return pd.Series(dtype=float)
            
            # Get activity data
            df_act = self.msg.var("ACT", {"technology": tecs})
            if df_act.empty:
                return pd.Series(dtype=float)
            
            # Get input parameter data
            filters = {"technology": tecs}
            if commodity_filter:
                filters["commodity"] = commodity_filter
            
            df_par = self.msg.par("input", filters)
            if df_par.empty:
                return pd.Series(dtype=float)
            
            # Determine technology column name
            tec_col = 'technology' if 'technology' in df_act.columns else 'tec'
            
            # Determine commodity column name
            com_col = 'commodity' if 'commodity' in df_par.columns else None
            
            # Aggregate parameter values by technology (and commodity if present)
            if com_col:
                df_par_agg = df_par.groupby([tec_col, com_col], as_index=False)['value'].mean()
            else:
                df_par_agg = df_par.groupby([tec_col], as_index=False)['value'].mean()
            
            # Merge activity with parameter
            df_merge = df_act.merge(df_par_agg, how="left", left_on=tec_col, right_on=tec_col)
            
            # Calculate product (activity * coefficient)
            if 'lvl' in df_merge.columns and 'value' in df_merge.columns:
                df_merge['product'] = df_merge['lvl'] * df_merge['value']
            elif 'value' in df_merge.columns:
                df_merge['product'] = df_merge['value']
            else:
                return pd.Series(dtype=float)
            
            # Determine year column
            year_col = 'year_act' if 'year_act' in df_merge.columns else 'year_vtg'
            
            # Group by year and sum
            if com_col and 'commodity' in df_merge.columns:
                result = df_merge.groupby([year_col, 'commodity'])['product'].sum().reset_index()
                return result
            else:
                result = df_merge.groupby(year_col)['product'].sum()
                return result
        
        # Calculate oil use by sector
        sector_results = {}
        domestic_sectors = ["Power", "Industry", "Buildings", "Transport", "Other"]
        
        for sector in domestic_sectors:
            tecs = sector_tecs.get(sector, [])
            if not tecs:
                continue
            
            oil_result = calculate_oil_use_from_tecs(tecs, commodity_filter=oil_products)
            
            if isinstance(oil_result, pd.DataFrame) and not oil_result.empty:
                yearly = oil_result.groupby('year_act')['product'].sum()
                sector_results[sector] = yearly
            elif isinstance(oil_result, pd.Series) and not oil_result.empty:
                sector_results[sector] = oil_result
        
        # Calculate exports separately
        if export_tecs:
            export_result = calculate_oil_use_from_tecs(export_tecs, commodity_filter=oil_products)
            
            if isinstance(export_result, pd.DataFrame) and not export_result.empty:
                yearly = export_result.groupby('year_act')['product'].sum()
                sector_results["Exports"] = yearly
            elif isinstance(export_result, pd.Series) and not export_result.empty:
                sector_results["Exports"] = export_result
        
        if sector_results:
            # Align all series to the same index (years)
            all_years = set()
            for series in sector_results.values():
                if isinstance(series, pd.Series):
                    all_years.update(series.index.tolist())
            
            if all_years:
                aligned_results = {}
                for name, series in sector_results.items():
                    if isinstance(series, pd.Series):
                        aligned_results[name] = series.reindex(sorted(all_years), fill_value=0)
                
                result_df = pd.DataFrame(aligned_results)
                
                # Convert from GWa to PJ (1 GWa = 31.536 PJ)
                self.results["Oil derivatives use by sector (PJ)"] = result_df * 31.536

    # =========================================================================
    # Fuels Analyses
    # =========================================================================

    def _calculate_gas_supply_by_source(self, nodeloc: str, yr: int):
        """
        Calculate gas supply by source (production, imports, exports).
        
        Output: "Gas supply by source (PJ)"
        
        Calculation:
        1. Domestic production: output where commodity = "gas" and level = "primary"
        2. Imports: Gas import technologies ("gas_imp" or similar)
        3. Exports: Gas export technologies ("gas_exp" or similar)
        4. Get ACT for all these technologies
        5. Multiply by relevant parameter values
        6. Present as: Production + Imports - Exports = Total Supply
        """
        gas_commodities = ["gas"]
        results = {}
        
        # Helper function to calculate gas supply from technologies
        def calculate_gas_supply_from_tecs(tecs, par_name,
                                           commodity_filter=None,
                                           level_filter=None):
            """Calculate gas supply from a list of technologies."""
            if not tecs:
                return pd.Series(dtype=float)
            
            # Get activity data
            df_act = self.msg.var("ACT", {"technology": tecs})
            if df_act.empty:
                return pd.Series(dtype=float)
            
            # Get parameter data
            filters = {"technology": tecs}
            if commodity_filter:
                filters["commodity"] = commodity_filter
            if level_filter:
                filters["level"] = level_filter
            
            df_par = self.msg.par(par_name, filters)
            if df_par.empty:
                return pd.Series(dtype=float)
            
            # Determine technology column name
            tec_col = 'technology' if 'technology' in df_act.columns else 'tec'
            
            # Determine commodity column name
            com_col = 'commodity' if 'commodity' in df_par.columns else None
            
            # Aggregate parameter values by technology (and commodity if present)
            if com_col:
                df_par_agg = df_par.groupby([tec_col, com_col], as_index=False)['value'].mean()
            else:
                df_par_agg = df_par.groupby([tec_col], as_index=False)['value'].mean()
            
            # Merge activity with parameter
            df_merge = df_act.merge(df_par_agg, how="left", left_on=tec_col, right_on=tec_col)
            
            # Calculate product (activity * coefficient)
            if 'lvl' in df_merge.columns and 'value' in df_merge.columns:
                df_merge['product'] = df_merge['lvl'] * df_merge['value']
            elif 'value' in df_merge.columns:
                df_merge['product'] = df_merge['value']
            else:
                return pd.Series(dtype=float)
            
            # Determine year column
            year_col = 'year_act' if 'year_act' in df_merge.columns else 'year_vtg'
            
            # Group by year and sum
            if com_col and 'commodity' in df_merge.columns:
                # Include commodity in grouping
                result = df_merge.groupby([year_col, 'commodity'])['product'].sum().reset_index()
                return result
            else:
                result = df_merge.groupby([year_col])['product'].sum()
                return result
        
        # 1. Domestic production - technologies outputting gas at primary level
        prod_par = self.msg.par("output", {"commodity": gas_commodities, "level": ["primary"]})
        if not prod_par.empty:
            prod_tecs = list(set(prod_par['technology'])) if 'technology' in prod_par.columns else []
            if prod_tecs:
                prod_result = calculate_gas_supply_from_tecs(prod_tecs, "output",
                                                             commodity_filter=gas_commodities,
                                                             level_filter="primary")
                if isinstance(prod_result, pd.DataFrame) and not prod_result.empty:
                    # Aggregate by year only
                    prod_yearly = prod_result.groupby('year_act')['product'].sum()
                    results["Production"] = prod_yearly
                elif isinstance(prod_result, pd.Series) and not prod_result.empty:
                    results["Production"] = prod_result
        
        # 2. Imports - technologies with "gas" and "_imp" in name
        all_tecs = list(self.msg.set("technology"))
        if hasattr(all_tecs, '__iter__'):
            gas_imp_tecs = [x for x in all_tecs if "gas" in str(x).lower() and "_imp" in str(x).lower()]
        else:
            gas_imp_tecs = []
        
        # Also try to find import technologies from input parameter
        input_par = self.msg.par("input")
        if not input_par.empty:
            if 'commodity' in input_par.columns:
                imp_from_input = input_par[input_par['commodity'].isin(gas_commodities)]['technology'].unique().tolist()
                gas_imp_tecs.extend([t for t in imp_from_input if t not in gas_imp_tecs])
        
        if gas_imp_tecs:
            # Get output parameter for imports (imported gas comes in via output)
            imp_result = calculate_gas_supply_from_tecs(gas_imp_tecs, "output")
            if isinstance(imp_result, pd.DataFrame) and not imp_result.empty:
                imp_yearly = imp_result.groupby('year_act')['product'].sum()
                results["Imports"] = imp_yearly
            elif isinstance(imp_result, pd.Series) and not imp_result.empty:
                results["Imports"] = imp_result
        
        # 3. Exports - technologies with "gas" and "_exp" in name
        gas_exp_tecs = [x for x in all_tecs if "gas" in str(x).lower() and "_exp" in str(x).lower()] if hasattr(all_tecs, '__iter__') else []
        
        # Also try to find export technologies from output parameter
        output_par = self.msg.par("output")
        if not output_par.empty:
            if 'commodity' in output_par.columns:
                exp_from_output = output_par[output_par['commodity'].isin(gas_commodities)]['technology'].unique().tolist()
                gas_exp_tecs.extend([t for t in exp_from_output if t not in gas_exp_tecs])
        
        if gas_exp_tecs:
            # Get input parameter for exports (gas exported is consumed from the system)
            exp_result = calculate_gas_supply_from_tecs(gas_exp_tecs, "input",
                                                        commodity_filter=gas_commodities)
            if isinstance(exp_result, pd.DataFrame) and not exp_result.empty:
                exp_yearly = exp_result.groupby('year_act')['product'].sum()
                results["Exports"] = -exp_yearly  # Negative for exports
            elif isinstance(exp_result, pd.Series) and not exp_result.empty:
                results["Exports"] = -exp_result
        
        if results:
            # Align all series to the same index (years)
            all_years = set()
            for series in results.values():
                if isinstance(series, pd.Series):
                    all_years.update(series.index.tolist())
            
            if all_years:
                aligned_results = {}
                for name, series in results.items():
                    if isinstance(series, pd.Series):
                        aligned_results[name] = series.reindex(sorted(all_years), fill_value=0)
                
                result_df = pd.DataFrame(aligned_results)
                
                # Calculate total supply
                result_df["Total Supply"] = result_df.get("Production", 0) + \
                                             result_df.get("Imports", 0) + \
                                             result_df.get("Exports", 0)
                
                # Convert from GWa to PJ (1 GWa = 31.536 PJ)
                # This is: 1 GWa * 8760 hours/GWa * 3600 sec/hour * 1 MJ/3.6MJ * 1 PJ/10^6 MJ
                # = 8760 * 3600 / 3.6 / 10^6 = 31.536
                self.results["Gas supply by source (PJ)"] = result_df * 31.536

    
    def _calculate_gas_utilization_by_sector(self, nodeloc: str, yr: int):
        """
        Calculate gas consumption by sector.
        
        Output: "Gas use by sector (PJ)"
        
        Calculation:
        1. Get technologies that input gas: `input` where `commodity = "gas"`
        2. Map to sectors using `output` parameter:
           - Power generation: output "electr"
           - Industry: output "i_spec", "i_therm"
           - Buildings: output "rc_spec", "rc_therm"
           - Transport: output "transport"
           - Exports: technology names containing "_exp" or "export"
        3. Get `ACT` for these technologies
        4. Multiply by `input` parameter value
        5. Group by sector
        
        **Implementation Details:**
        - Simplified commodity filter to ["gas"]
        - Added export detection via technology naming conventions
        - Uses `_map_technologies_to_sectors()` for sector mapping
        - Handles column name variations (technology vs tec)
        - Unit conversion: 31.536 (GWa → PJ)
        - Removes empty "Other" column from results
        """
        gas_commodities = ["gas"]
        sector_results = {}
        
        # Get technologies that input gas
        input_par = self.msg.par("input", {"commodity": gas_commodities})
        if input_par.empty:
            return
        
        # Get all unique technologies that input gas
        all_gas_tecs = list(set(input_par['technology'])) if 'technology' in input_par.columns else []
        
        if not all_gas_tecs:
            return
        
        # Map technologies to sectors (excluding exports)
        sector_tecs = self._map_technologies_to_sectors(all_gas_tecs)
        
        # Identify export technologies separately
        export_tecs = [t for t in all_gas_tecs if '_exp' in str(t).lower() or 'export' in str(t).lower()]
        
        # Remove exports from "Other" and any other sector
        for sector in list(sector_tecs.keys()):
            sector_tecs[sector] = [t for t in sector_tecs.get(sector, []) if t not in export_tecs]
        
        # Get "Other" technologies that don't map to standard sectors
        other_tecs = sector_tecs.get("Other", [])
        
        # Remove "Other" from sector_tecs temporarily
        del sector_tecs["Other"]
        
        # Filter out balance/virtual technologies from "Other"
        balance_patterns = ['_bal', 'balance', 'bal_', 'gas_bal', 'dummy', '虚拟']
        filtered_other = [t for t in other_tecs if not any(p in str(t).lower() for p in balance_patterns)]
        
        # Put remaining "Other" technologies back into sector_tecs to be summed
        if filtered_other:
            sector_tecs["Other"] = filtered_other
        
        # Add exports as a separate category
        if export_tecs:
            sector_tecs["Exports"] = export_tecs
        
        # DEBUG: Print sector mapping
        print("\n=== GAS UTILIZATION SECTOR MAPPING ===")
        for sector, tecs in sector_tecs.items():
            print(f"{sector}: {tecs}")
        if other_tecs != filtered_other:
            print(f"Filtered out (balance/virtual): {[t for t in other_tecs if t not in filtered_other]}")
        print("=== END SECTOR MAPPING ===\n")
        
        # Helper function to calculate gas use for a list of technologies
        def calculate_gas_use_from_tecs(tecs, commodity_filter=None):
            """Calculate gas use from a list of technologies."""
            if not tecs:
                return pd.Series(dtype=float)
            
            # Get activity data
            df_act = self.msg.var("ACT", {"technology": tecs})
            if df_act.empty:
                return pd.Series(dtype=float)
            
            # Get input parameter data
            filters = {"technology": tecs}
            if commodity_filter:
                filters["commodity"] = commodity_filter
            
            df_par = self.msg.par("input", filters)
            if df_par.empty:
                return pd.Series(dtype=float)
            
            # Determine technology column name
            tec_col = 'technology' if 'technology' in df_act.columns else 'tec'
            
            # Determine commodity column name
            com_col = 'commodity' if 'commodity' in df_par.columns else None
            
            # Aggregate parameter values by technology (and commodity if present)
            if com_col:
                df_par_agg = df_par.groupby([tec_col, com_col], as_index=False)['value'].mean()
            else:
                df_par_agg = df_par.groupby([tec_col], as_index=False)['value'].mean()
            
            # Merge activity with parameter
            df_merge = df_act.merge(df_par_agg, how="left", left_on=tec_col, right_on=tec_col)
            
            # Calculate product (activity * coefficient)
            if 'lvl' in df_merge.columns and 'value' in df_merge.columns:
                df_merge['product'] = df_merge['lvl'] * df_merge['value']
            elif 'value' in df_merge.columns:
                df_merge['product'] = df_merge['value']
            else:
                return pd.Series(dtype=float)
            
            # Determine year column
            year_col = 'year_act' if 'year_act' in df_merge.columns else 'year_vtg'
            
            # Group by year and sum
            if com_col and 'commodity' in df_merge.columns:
                result = df_merge.groupby([year_col, 'commodity'])['product'].sum().reset_index()
                return result
            else:
                result = df_merge.groupby([year_col])['product'].sum()
                return result
        
        # Calculate gas use by standard sectors (including filtered "Other")
        domestic_sectors = ["Power", "Industry", "Buildings", "Transport", "Other"]
        for sector in domestic_sectors:
            tecs = sector_tecs.get(sector, [])
            if not tecs:
                continue
            
            gas_result = calculate_gas_use_from_tecs(tecs, commodity_filter=gas_commodities)
            
            if isinstance(gas_result, pd.DataFrame) and not gas_result.empty:
                yearly = gas_result.groupby('year_act')['product'].sum()
                sector_results[sector] = yearly
            elif isinstance(gas_result, pd.Series) and not gas_result.empty:
                sector_results[sector] = gas_result
        
        # Calculate exports separately
        if export_tecs:
            export_result = calculate_gas_use_from_tecs(export_tecs, commodity_filter=gas_commodities)
            
            if isinstance(export_result, pd.DataFrame) and not export_result.empty:
                yearly = export_result.groupby('year_act')['product'].sum()
                sector_results["Exports"] = yearly
            elif isinstance(export_result, pd.Series) and not export_result.empty:
                sector_results["Exports"] = export_result
        
        if sector_results:
            # Align all series to the same index (years)
            all_years = set()
            for series in sector_results.values():
                if isinstance(series, pd.Series):
                    all_years.update(series.index.tolist())
            
            if all_years:
                aligned_results = {}
                for name, series in sector_results.items():
                    if isinstance(series, pd.Series):
                        aligned_results[name] = series.reindex(sorted(all_years), fill_value=0)
                
                result_df = pd.DataFrame(aligned_results)
                
                # Convert from GWa to PJ (1 GWa = 31.536 PJ)
                self.results["Gas use by sector (PJ)"] = result_df * 31.536


    # =========================================================================
    # Sectoral Use Analyses
    # =========================================================================

    def _calculate_buildings_by_fuel(self, nodeloc: str, yr: int):
        """Calculate buildings sector energy use by fuel."""
        df = self._calculate_fuel_use_by_sector(["rc_spec", "rc_therm", "non-comm"], nodeloc, yr)
        if not df.empty:
            self.results["Buildings energy by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_industry_by_fuel(self, nodeloc: str, yr: int):
        """Calculate industry sector energy use by fuel."""
        df = self._calculate_fuel_use_by_sector(["i_spec", "i_therm"], nodeloc, yr)
        if not df.empty:
            self.results["Industry energy by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    # =========================================================================
    # Price Analyses
    # =========================================================================

    def _calculate_prices_by_sector(self, nodeloc: str, yr: int):
        """Calculate energy prices by end-use sector."""
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc})
        if price.empty:
            return

        # Sector commodities
        sector_coms = {
            "Transport": "transport",
            "Industry (specific)": "i_spec",
            "Industry (thermal)": "i_therm",
            "Buildings (specific)": "rc_spec",
            "Buildings (thermal)": "rc_therm",
        }

        sector_results = {}
        for sector, com in sector_coms.items():
            sector_price = price[price['commodity'] == com]
            if sector_price.empty:
                continue

            year_col = 'year' if 'year' in sector_price.columns else 'year_act'
            if year_col in sector_price.columns:
                avg_price = sector_price.groupby(year_col)['lvl'].mean()
                sector_results[sector] = avg_price * 0.1142  # $/GWa -> $/MWh

        if sector_results:
            result_df = pd.DataFrame(sector_results)
            self.results["Energy price by sector ($/MWh)"] = result_df

    def _calculate_prices_by_fuel(self, nodeloc: str, yr: int):
        """Calculate energy prices by fuel type at final level."""
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc, "level": ["final", "secondary"]})
        if price.empty:
            return

        fuel_coms = ["electr", "gas", "lightoil", "fueloil", "coal", "biomass", "hydrogen"]
        price_filtered = price[price['commodity'].isin(fuel_coms)]
        if price_filtered.empty:
            return

        year_col = 'year' if 'year' in price_filtered.columns else 'year_act'
        fuel_results = {}
        for com in fuel_coms:
            com_price = price_filtered[price_filtered['commodity'] == com]
            if com_price.empty:
                continue
            if year_col in com_price.columns:
                avg_price = com_price.groupby(year_col)['lvl'].mean()
                fuel_results[com] = avg_price * 0.1142

        if fuel_results:
            result_df = pd.DataFrame(fuel_results)
            self.results["Energy price by fuel ($/MWh)"] = result_df

    def _calculate_electricity_lcoe(self, nodeloc: str, yr: int):
        """Calculate Levelized Cost of Electricity (LCOE) by source."""
        # Get electricity-producing technologies
        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        # Get activity for weighting
        act = self.msg.var("ACT", {"technology": tecs})
        if act.empty:
            return

        # Get cost parameters
        inv_cost = self.msg.par("inv_cost", {"technology": tecs})
        fix_cost = self.msg.par("fix_cost", {"technology": tecs})
        var_cost = self.msg.par("var_cost", {"technology": tecs})

        lcoe_results = {}

        for tec in tecs:
            tec_act = act[act['technology'] == tec]
            if tec_act.empty:
                continue

            # Get technology-specific costs
            tec_inv = inv_cost[inv_cost['technology'] == tec] if not inv_cost.empty else pd.DataFrame()
            tec_fix = fix_cost[fix_cost['technology'] == tec] if not fix_cost.empty else pd.DataFrame()
            tec_var = var_cost[var_cost['technology'] == tec] if not var_cost.empty else pd.DataFrame()

            year_col = 'year_act' if 'year_act' in tec_act.columns else 'year'

            # Simple LCOE estimation: (annualized capex + fixed + variable) / output
            # This is a simplified calculation - full LCOE requires more detailed data
            for _, row in tec_act.iterrows():
                year = row.get(year_col, row.get('year_vtg'))
                activity = row.get('lvl', 0)
                if activity <= 0 or year not in self.plotyrs:
                    continue

                # Get costs for this year
                var = tec_var[tec_var['year_act'] == year]['value'].mean() if not tec_var.empty else 0
                if pd.isna(var):
                    var = 0

                if year not in lcoe_results:
                    lcoe_results[year] = {}
                if tec not in lcoe_results[year]:
                    lcoe_results[year][tec] = {'cost': var * 0.1142, 'activity': activity}
                else:
                    lcoe_results[year][tec]['activity'] += activity

        # Convert to DataFrame - average LCOE weighted by activity
        if lcoe_results:
            year_lcoe = {}
            for year, tec_data in lcoe_results.items():
                total_act = sum(d['activity'] for d in tec_data.values())
                if total_act > 0:
                    weighted_lcoe = sum(d['cost'] * d['activity'] for d in tec_data.values()) / total_act
                    year_lcoe[year] = weighted_lcoe

            if year_lcoe:
                result_df = pd.DataFrame({'LCOE': year_lcoe}).T
                result_df.index.name = 'year'
                self.results["Electricity LCOE ($/MWh)"] = result_df

    def _calculate_crf(self, interest_rate: float, lifetime: float) -> float:
        """Calculates Capital Recovery Factor."""
        if interest_rate == 0:
            return 1 / lifetime if lifetime > 0 else 0
        if lifetime <= 0:
            return 0
        # Cap lifetime to avoid overflow
        lifetime = min(lifetime, 100)
        rate_factor = (1 + interest_rate) ** lifetime
        return (interest_rate * rate_factor) / (rate_factor - 1)

    def _calculate_electricity_price_by_source(self, nodeloc: str, yr: int):
        """Calculate electricity generation cost breakdown by source."""
        # Get electricity-producing technologies
        output_par = self.msg.par("output", {"commodity": "electr", "level": "secondary"})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))

        # Get Activity (Generation)
        act = self.msg.var("ACT", {"technology": tecs})
        if act.empty:
            return
        
        # Filter for plot years
        act = act[act['year_act'].isin(self.plotyrs)]
        if act.empty:
            return
        
        # Group ACT by year and technology
        act_grouped = act.groupby(['year_act', 'technology'])['lvl'].sum().reset_index()
        
        # Initialize cost dataframe with activity
        costs = act_grouped.copy()
        costs['total_cost'] = 0.0
        
        # 1. Variable O&M
        var_cost = self.msg.par("var_cost", {"technology": tecs})
        if not var_cost.empty:
            vc_avg = var_cost.groupby(['year_act', 'technology'])['value'].mean().reset_index()
            costs = costs.merge(vc_avg, on=['year_act', 'technology'], how='left', suffixes=('', '_vc'))
            costs['total_cost'] += costs['lvl'] * costs['value'].fillna(0)
            costs.drop(columns=['value'], inplace=True)

        # 2. Fixed O&M
        cap = self.msg.var("CAP", {"technology": tecs})
        fix_cost = self.msg.par("fix_cost", {"technology": tecs})
        
        if not cap.empty and not fix_cost.empty:
            cap = cap[cap['year_act'].isin(self.plotyrs)]
            cap_grouped = cap.groupby(['year_act', 'technology'])['lvl'].sum().reset_index()
            
            fc_avg = fix_cost.groupby(['year_act', 'technology'])['value'].mean().reset_index()
            
            fc_calc = cap_grouped.merge(fc_avg, on=['year_act', 'technology'], how='inner')
            fc_calc['fom_cost'] = fc_calc['lvl'] * fc_calc['value']
            
            costs = costs.merge(fc_calc[['year_act', 'technology', 'fom_cost']], on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['fom_cost'].fillna(0)
            costs.drop(columns=['fom_cost'], inplace=True)

        # 3. Investment Cost (Annualized)
        cap_new = self.msg.var("CAP_NEW", {"technology": tecs})
        inv_cost = self.msg.par("inv_cost", {"technology": tecs})
        lifetime = self.msg.par("technical_lifetime", {"technology": tecs})
        
        r = 0.05
        ir_param = self.msg.par("interest_rate")
        if not ir_param.empty:
            r = ir_param['value'].mean()

        if not cap_new.empty and not inv_cost.empty:
            inv_cost_renamed = inv_cost.rename(columns={'value': 'value_cost'})
            inv_data = cap_new.merge(inv_cost_renamed, on=['node_loc', 'technology', 'year_vtg'])
            
            if not lifetime.empty:
                lt_avg = lifetime.groupby('technology')['value'].mean().reset_index()
                lt_avg = lt_avg.rename(columns={'value': 'lifetime'})
                inv_data = inv_data.merge(lt_avg, on='technology', how='left')
                inv_data['lifetime'] = inv_data['lifetime'].fillna(30)
            else:
                inv_data['lifetime'] = 30
            
            inv_data['crf'] = inv_data['lifetime'].apply(lambda l: self._calculate_crf(r, l))
            inv_data['ann_cost'] = inv_data['lvl'] * inv_data['value_cost'] * inv_data['crf']
            
            ann_costs = []
            for _, row in inv_data.iterrows():
                vtg = int(row['year_vtg'])
                life = int(row['lifetime'])
                cost = row['ann_cost']
                tech = row['technology']
                
                end_year = vtg + life
                for y in self.plotyrs:
                    if vtg <= y < end_year:
                        ann_costs.append({'year_act': y, 'technology': tech, 'inv_cost': cost})
            
            if ann_costs:
                ac_df = pd.DataFrame(ann_costs)
                ac_grouped = ac_df.groupby(['year_act', 'technology'])['inv_cost'].sum().reset_index()
                
                costs = costs.merge(ac_grouped, on=['year_act', 'technology'], how='left')
                costs['total_cost'] += costs['inv_cost'].fillna(0)
                costs.drop(columns=['inv_cost'], inplace=True)

        # 4. Fuel Costs
        input_par = self.msg.par("input", {"technology": tecs})
        price_com = self.msg.var("PRICE_COMMODITY", {"node": nodeloc})
        
        if not input_par.empty and not price_com.empty:
            in_avg = input_par.groupby(['year_act', 'technology', 'commodity'])['value'].mean().reset_index()
            pr_avg = price_com.groupby(['year', 'commodity'])['lvl'].mean().reset_index()
            
            fuel_calc = in_avg.merge(pr_avg, left_on=['year_act', 'commodity'], right_on=['year', 'commodity'], how='inner')
            fuel_calc['fuel_unit_cost'] = fuel_calc['value'] * fuel_calc['lvl']
            
            fuel_cost_per_act = fuel_calc.groupby(['year_act', 'technology'])['fuel_unit_cost'].sum().reset_index()
            
            costs = costs.merge(fuel_cost_per_act, on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['lvl'] * costs['fuel_unit_cost'].fillna(0)
            costs.drop(columns=['fuel_unit_cost'], inplace=True)

        # 5. Emission Costs
        emission_factor = self.msg.par("emission_factor", {"technology": tecs})
        emission_price = self.msg.var("PRICE_EMISSION", {"node": nodeloc})
        
        if not emission_factor.empty and not emission_price.empty:
            ef_avg = emission_factor.groupby(['year_act', 'technology', 'emission'])['value'].mean().reset_index()
            ep_avg = emission_price.groupby(['year', 'emission'])['lvl'].mean().reset_index()
            
            em_calc = ef_avg.merge(ep_avg, left_on=['year_act', 'emission'], right_on=['year', 'emission'], how='inner')
            em_calc['em_unit_cost'] = em_calc['value'] * em_calc['lvl']
            
            em_cost_per_act = em_calc.groupby(['year_act', 'technology'])['em_unit_cost'].sum().reset_index()
            
            costs = costs.merge(em_cost_per_act, on=['year_act', 'technology'], how='left')
            costs['total_cost'] += costs['lvl'] * costs['em_unit_cost'].fillna(0)
            costs.drop(columns=['em_unit_cost'], inplace=True)

        # Calculate Unit Cost ($/MWh)
        # 0.1142 conversion factor from M$/GWa to $/MWh
        costs['unit_cost'] = (costs['total_cost'] / costs['lvl']) * 0.1142
        
        # Format for result
        result_df = costs[['year_act', 'technology', 'unit_cost']].pivot(index='year_act', columns='technology', values='unit_cost')
        
        # Map
        result_mapped = self._mappings(result_df, groupby="technology")
        self.results["Electricity cost by source ($/MWh)"] = result_mapped

    def _create_parameters(self) -> Dict[str, Parameter]:
        """Convert pivot table results to Parameter objects."""
        parameters = {}

        for name, df in self.results.items():
            if df.empty:
                continue

            # Convert pivot table to long format
            # The pivot table has year as index and categories as columns
            long_df = self._pivot_to_long(df, name)

            if long_df.empty:
                continue

            # Determine dimension column name based on result type
            dims = list(long_df.columns[:-1])  # All columns except 'value'

            metadata = {
                'units': self._extract_units(name),
                'desc': f'Postprocessed result: {name}',
                'dims': dims,
                'value_column': 'value',
                'parameter_type': 'result',
                'result_type': 'postprocessed',
                'source': 'postprocessor'
            }

            param = Parameter(name, long_df, metadata)
            parameters[name] = param

        return parameters

    def _pivot_to_long(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """Convert pivot table (year index, categories columns) to long format.

        If the DataFrame is already in long format (has 'value' column), it is
        returned as-is after filtering out zero values.
        """
        if df.empty:
            return pd.DataFrame()

        # Check if already in long format by looking for 'value' column
        # and checking that the index is a simple RangeIndex (not year-based)
        col_list = list(df.columns)
        is_long_format = (
            'value' in col_list and
            isinstance(df.index, pd.RangeIndex) and
            ('year' in col_list or 'year_act' in col_list)
        )

        if is_long_format:
            # Already long format - filter zeros using query to handle potential duplicate columns
            try:
                long_df = df.query('value != 0').reset_index(drop=True)
            except Exception:
                # Fallback: use numpy array access
                value_col_idx = col_list.index('value')
                mask = df.iloc[:, value_col_idx].values != 0
                long_df = df[mask].reset_index(drop=True)
            return long_df

        # Reset index to make year a column
        df = df.reset_index()

        # Get the index column name (usually year_act or year)
        index_col = df.columns[0]
        value_cols = [col for col in df.columns if col != index_col]

        if not value_cols:
            return pd.DataFrame()

        # Melt to long format
        long_df = df.melt(
            id_vars=[index_col],
            value_vars=value_cols,
            var_name='category',
            value_name='value'
        )

        # Rename index column to 'year' for consistency
        if index_col != 'year':
            long_df = long_df.rename(columns={index_col: 'year'})

        # Remove rows with zero values
        long_df = long_df[long_df['value'] != 0]

        return long_df

    def _extract_units(self, name: str) -> str:
        """Extract units from parameter name."""
        # Look for units in parentheses
        if '(' in name and ')' in name:
            start = name.rfind('(')
            end = name.rfind(')')
            return name[start+1:end]
        return 'N/A'


def run_postprocessing(scenario: ScenarioData,
                       nodeloc: Optional[str] = None,
                       plot_years: Optional[List[int]] = None) -> Dict[str, Parameter]:
    """
    Run postprocessing on a scenario and return derived parameters.

    This is the main entry point for postprocessing.

    Args:
        scenario: ScenarioData containing input parameters and result variables
        nodeloc: Optional node location filter
        plot_years: Optional list of years to include (default: 2020-2050 by 5)

    Returns:
        Dict of parameter_name -> Parameter objects
    """
    processor = ResultsPostprocessor(scenario)

    if plot_years:
        processor.set_plot_years(plot_years)

    return processor.process(nodeloc)


def add_postprocessed_results(scenario: ScenarioData,
                              nodeloc: Optional[str] = None,
                              plot_years: Optional[List[int]] = None) -> int:
    """
    Run postprocessing and add results directly to the scenario.

    Args:
        scenario: ScenarioData to add results to
        nodeloc: Optional node location filter
        plot_years: Optional list of years to include

    Returns:
        Number of parameters added
    """
    parameters = run_postprocessing(scenario, nodeloc, plot_years)

    count = 0
    for name, param in parameters.items():
        scenario.add_parameter(param, mark_modified=False, add_to_history=False)
        count += 1

    return count
