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
        param = self.scenario.get_parameter(param_name)
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

        # Run calculations
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

        # Convert results to Parameters
        return self._create_parameters()

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
        """Merge and multiply two dataframes."""
        if df1.empty or df2.empty:
            return pd.DataFrame()

        index = [
            x for x in ["mode", "node_loc", "technology", "time", "year_act", "year_vtg"]
            if x in df1.columns
        ]
        df = df1.merge(df2, how="outer", on=index)
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

        df_sec = pd.DataFrame(index=self.plotyrs)

        if groupby == "sector":
            dict_sectors = self._get_sector_mappings(df)
        else:
            dict_sectors = self._get_technology_mappings(df)

        # Map entries to labels
        for label, tecs in dict_sectors.items():
            if tecs:  # Only process non-empty lists
                filtered = df.filter(items=tecs)
                if not filtered.empty:
                    df[label] = filtered.sum(axis=1)
                    df_sec = df_sec.join(df[[label]])

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
        df = (df_hist + df).fillna(0)

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
                df = (df_hist + df).fillna(0)
                self.results["Gas supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Gas usage
        input_par = self.msg.par("input", {"commodity": "gas"})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(gas_tecs))
            df, df2 = self._model_output(tecs, nodeloc, "input", "gas")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = (df_hist + df).fillna(0)
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
                df = (df + df_hist).fillna(0)
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
                df = (df + df_hist).fillna(0)
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
                df = (df + df_hist).fillna(0)
                self.results["Oil derivative supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Oil derivatives use
        input_par = self.msg.par("input", {"commodity": ["fueloil", "lightoil"]})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(["loil_t_d", "foil_t_d"]))
            df, df2 = self._model_output(tecs, nodeloc, "input", ["fueloil", "lightoil"])
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = (df + df_hist).fillna(0)
                self.results["Oil derivative use (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Oil supply
        output_par = self.msg.par("output", {"commodity": ["crudeoil"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology) - set(["oil_bal", "oil_exp"]))
            df, df2 = self._model_output(tecs, nodeloc, "output", "crudeoil")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = (df + df_hist).fillna(0)
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
                df = (df + df_hist).fillna(0)
                self.results["Biomass supply (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

        # Biomass use
        input_par = self.msg.par("input", {"commodity": ["biomass"], "level": ["primary", "final"]})
        if not input_par.empty:
            tecs = list(set(input_par.technology) - set(["biomass_t_d"]))
            df, df2 = self._model_output(tecs, nodeloc, "input", "biomass")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = (df + df_hist).fillna(0)
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
                df = self._com_order((df_hist + df).fillna(0), order)
                self.results["Energy use Industry (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Non-energy feedstock
        output_par = self.msg.par("output", {"commodity": ["i_feed"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order((df_hist + df).fillna(0), order)
                self.results["Non-energy use Feedstock (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Buildings
        output_par = self.msg.par("output", {"commodity": ["rc_spec", "rc_therm", "non-comm"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "technology")
                df = self._com_order((df_hist + df).fillna(0), order)
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
                df = self._com_order((df_hist + df).fillna(0), order)

                # Add renewables
                input_par = self.msg.par("input", {"level": ["renewable"]})
                if not input_par.empty:
                    tecs_re = list(set(input_par.technology))
                    df_re, df2_re = self._model_output(tecs_re, nodeloc, "input")
                    if not df_re.empty:
                        df_re = self._group(df_re, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_re = self._add_history(tecs_re, nodeloc, df2_re, "commodity")
                        df = df.add(self._com_order((df_hist_re + df_re).fillna(0), order), fill_value=0)

                # Handle imports/exports
                tecs_imp = [x for x in self.msg.set("technology") if str(x).endswith("_imp")]
                if tecs_imp:
                    df_imp, df2_imp = self._model_output(tecs_imp, nodeloc, "output")
                    if not df_imp.empty:
                        df_imp = self._group(df_imp, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_imp = self._add_history(tecs_imp, nodeloc, df2_imp, "commodity")
                        df_imp = self._com_order((df_hist_imp + df_imp).fillna(0), order)
                        df = df.add(df_imp, fill_value=0)

                tecs_exp = [x for x in self.msg.set("technology") if "_exp" in str(x)]
                if tecs_exp:
                    df_exp, df2_exp = self._model_output(tecs_exp, nodeloc, "output")
                    if not df_exp.empty:
                        df_exp = self._group(df_exp, ["year_act", "commodity"], "product", 0.0, yr)
                        df_hist_exp = self._add_history(tecs_exp, nodeloc, df2_exp, "commodity")
                        df_exp = self._com_order((df_hist_exp + df_exp).fillna(0), order)
                        df = df.add(-df_exp, fill_value=0)

                self.results["Primary energy supply (PJ)"] = self._com_order(df, order) * self.UNIT_GWA_TO_PJ

        # Final energy consumption
        output_par = self.msg.par("output", {"level": ["final"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order((df_hist + df).fillna(0), order)
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
                df = self._com_order((df_hist + df).fillna(0), order)
                self.results["Energy exports (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Imports
        tecs_imp = [x for x in self.msg.set("technology") if str(x).endswith("_imp")]
        if tecs_imp:
            df, df2 = self._model_output(tecs_imp, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs_imp, nodeloc, df2, "commodity")
                df = self._com_order((df_hist + df).fillna(0), order)
                self.results["Energy imports (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_emissions(self, nodeloc: str, yr: int):
        """Calculate total GHG emissions."""
        ems = ["TCE"]
        df1 = self.msg.var("EMISS", {"emission": ems, "node": nodeloc})
        if not df1.empty:
            df = self._group(df1, ["year", "emission"], "lvl", 0.0, yr)
            self.results["Total GHG emissions (MtCeq)"] = df

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
