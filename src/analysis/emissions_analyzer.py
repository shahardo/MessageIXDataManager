"""
Emissions domain analyzer for MESSAGEix results.

Handles:
- Total GHG emissions (from EMISS variable and historical_emission parameter)
- Emissions by technology (sector proxy)
- Emissions by emission type (CO2, CH4, N2O, etc.)
- Emissions by fuel type
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from analysis.base_analyzer import BaseAnalyzer


class EmissionsAnalyzer(BaseAnalyzer):
    """Handles emissions domain calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all emissions calculations and populate self.results."""
        self._calculate_emissions(nodeloc, yr)
        self._calculate_emissions_by_sector(nodeloc, yr)
        self._calculate_emissions_by_type(nodeloc, yr)
        self._calculate_emissions_by_fuel(nodeloc, yr)

    def _calculate_emissions(self, nodeloc: str, yr: int) -> None:
        """Calculate total GHG emissions.

        Combines model EMISS variable with historical_emission parameter.
        """
        df_model = self.msg.var("EMISS", {"node": nodeloc})
        if df_model.empty:
            df_model = self.msg.var("EMISS")

        df_hist = self.msg.par("historical_emission", {"node": nodeloc})
        if df_hist.empty:
            df_hist = self.msg.par("historical_emission")

        year_col = 'year' if 'year' in df_model.columns else 'year_act' if 'year_act' in df_model.columns else None

        result_df = pd.DataFrame()

        if not df_model.empty and year_col:
            df_model = df_model[df_model[year_col].isin(self.plotyrs)]

            if 'emission' in df_model.columns:
                model_grouped = df_model.groupby([year_col, 'emission'])['lvl'].sum().reset_index()
                model_pivot = model_grouped.pivot(index=year_col, columns='emission', values='lvl').fillna(0)
                result_df = model_pivot

        if not df_hist.empty:
            hist_year_col = 'year' if 'year' in df_hist.columns else 'year_act' if 'year_act' in df_hist.columns else None
            if hist_year_col and 'emission' in df_hist.columns:
                df_hist = df_hist[df_hist[hist_year_col].isin(self.plotyrs)]

                if not df_hist.empty:
                    value_col = 'value' if 'value' in df_hist.columns else 'lvl'
                    hist_grouped = df_hist.groupby([hist_year_col, 'emission'])[value_col].sum().reset_index()
                    hist_pivot = hist_grouped.pivot(index=hist_year_col, columns='emission', values=value_col).fillna(0)

                    if result_df.empty:
                        result_df = hist_pivot
                    else:
                        result_df = result_df.combine_first(hist_pivot).fillna(0)

        if not result_df.empty:
            result_df = result_df.sort_index()
            result_df = result_df.loc[:, (result_df != 0).any()]

            if not result_df.empty:
                self.results["Total GHG emissions (MtCeq)"] = result_df

    def _calculate_emissions_by_sector(self, nodeloc: str, yr: int) -> None:
        """Calculate CO2 emissions by technology based on fuel consumption."""
        fuel_emission_factors = {
            "coal": 3.0, "coal_rc": 3.0, "coal_i": 3.0,
            "crudeoil": 2.4, "lightoil": 2.4, "loil_rc": 2.4, "loil_i": 2.4,
            "fueloil": 2.6, "foil_rc": 2.6, "foil_i": 2.6,
            "gas": 1.8, "gas_rc": 1.8, "gas_i": 1.8,
        }

        act = self.msg.var("ACT")
        if act.empty:
            return

        input_par = self.msg.par("input")
        if input_par.empty:
            return

        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        input_tec_col = 'technology' if 'technology' in input_par.columns else 'tec' if 'tec' in input_par.columns else None

        if not act_year_col or not act_tec_col or not input_tec_col:
            return

        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return

        fossil_commodities = list(fuel_emission_factors.keys())
        fossil_input = input_par[input_par['commodity'].isin(fossil_commodities)]
        if fossil_input.empty:
            return

        fossil_tecs = list(fossil_input[input_tec_col].unique())
        tech_results = {}

        for tec in fossil_tecs:
            tec_input = fossil_input[fossil_input[input_tec_col] == tec]
            if tec_input.empty:
                continue

            tec_act = act[act[act_tec_col] == tec]
            if tec_act.empty:
                continue

            act_by_year = tec_act.groupby(act_year_col)['lvl'].sum()
            total_emissions = pd.Series(0.0, index=act_by_year.index)

            for _, row in tec_input.iterrows():
                commodity = row['commodity']
                input_coef = row['value']
                ef = fuel_emission_factors.get(commodity, 0)

                if ef > 0 and input_coef > 0:
                    fuel_emissions = act_by_year * input_coef * ef
                    total_emissions = total_emissions.add(fuel_emissions, fill_value=0)

            if total_emissions.sum() > 0:
                tech_results[tec] = total_emissions

        if tech_results:
            result_df = pd.DataFrame(tech_results)
            result_df = result_df.sort_index()
            result_df = result_df.loc[:, (result_df != 0).any()]
            if not result_df.empty:
                col_totals = result_df.sum().sort_values(ascending=False)
                result_df = result_df[col_totals.index]
                self.results["Emissions by technology (Mt CO2)"] = result_df

    def _calculate_emissions_from_activity_by_sector(self) -> Dict[str, pd.Series]:
        """Calculate emissions from ACT × emission_factor, grouped by sector.

        Fallback when EMISS variable is not available.
        Returns dict of {sector_name: pd.Series with year index}.
        """
        sector_results = {}

        ef = self.msg.par("emission_factor")
        if ef.empty:
            return sector_results

        act = self.msg.var("ACT")
        if act.empty:
            return sector_results

        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        if not act_year_col or not act_tec_col:
            return sector_results

        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return sector_results

        ef_tec_col = 'technology' if 'technology' in ef.columns else 'tec' if 'tec' in ef.columns else None
        if not ef_tec_col:
            return sector_results

        all_tecs = list(ef[ef_tec_col].unique())
        if not all_tecs:
            return sector_results

        sector_tecs = self._map_technologies_to_sectors(all_tecs)

        for sector, tecs in sector_tecs.items():
            if not tecs:
                continue

            sector_act = act[act[act_tec_col].isin(tecs)]
            if sector_act.empty:
                continue

            sector_ef = ef[ef[ef_tec_col].isin(tecs)]
            if sector_ef.empty:
                continue

            ef_year_col = 'year_act' if 'year_act' in sector_ef.columns else 'year' if 'year' in sector_ef.columns else None
            if ef_year_col:
                ef_avg = sector_ef.groupby([ef_year_col, ef_tec_col])['value'].mean().reset_index()
            else:
                ef_avg = sector_ef.groupby([ef_tec_col])['value'].mean().reset_index()
                ef_avg[act_year_col] = self.plotyrs[0]

            act_grouped = sector_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            if ef_year_col:
                merged = act_grouped.merge(
                    ef_avg, left_on=[act_year_col, act_tec_col],
                    right_on=[ef_year_col, ef_tec_col], how='inner'
                )
            else:
                merged = act_grouped.merge(
                    ef_avg, left_on=[act_tec_col], right_on=[ef_tec_col], how='inner'
                )

            if merged.empty:
                continue

            merged['emissions'] = merged['lvl'] * merged['value']
            sector_sum = merged.groupby(act_year_col)['emissions'].sum()
            if not sector_sum.empty:
                sector_results[sector] = sector_sum

        return sector_results

    def _calculate_emissions_by_type(self, nodeloc: str, yr: int) -> None:
        """Calculate emissions grouped by emission type (CO2, CH4, N2O, etc.)."""
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

    def _calculate_emissions_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate CO2 emissions by fuel type based on technology activity."""
        emission_factors = {
            "Coal": 3.0,
            "Oil": 2.4,
            "Gas": 1.8,
            "Biomass": 0.0,
        }

        act = self.msg.var("ACT")
        if act.empty:
            return

        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None

        if not act_year_col or not act_tec_col:
            return

        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return

        input_par = self.msg.par("input")
        if input_par.empty:
            return

        input_tec_col = 'technology' if 'technology' in input_par.columns else 'tec' if 'tec' in input_par.columns else None
        if not input_tec_col:
            return

        fuel_results = {}

        fuel_commodities = {
            "Coal": ["coal", "coal_rc", "coal_i"],
            "Oil": ["crudeoil", "lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i"],
            "Gas": ["gas", "gas_rc", "gas_i"],
            "Biomass": ["biomass", "biomass_rc", "biomass_nc"],
        }

        for fuel_name, commodities in fuel_commodities.items():
            emission_factor = emission_factors.get(fuel_name, 0)
            if emission_factor == 0:
                continue

            fuel_input = input_par[input_par['commodity'].isin(commodities)]
            if fuel_input.empty:
                continue

            fuel_tecs = list(fuel_input[input_tec_col].unique())

            fuel_act = act[act[act_tec_col].isin(fuel_tecs)]
            if fuel_act.empty:
                continue

            input_year_col = 'year_act' if 'year_act' in fuel_input.columns else 'year' if 'year' in fuel_input.columns else None
            if input_year_col:
                input_coef = fuel_input.groupby([input_year_col, input_tec_col])['value'].mean().reset_index()
            else:
                input_coef = fuel_input.groupby([input_tec_col])['value'].mean().reset_index()

            act_grouped = fuel_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            if input_year_col:
                merged = act_grouped.merge(
                    input_coef,
                    left_on=[act_year_col, act_tec_col],
                    right_on=[input_year_col, input_tec_col],
                    how='inner'
                )
            else:
                merged = act_grouped.merge(
                    input_coef, left_on=[act_tec_col], right_on=[input_tec_col], how='inner'
                )

            if merged.empty:
                continue

            merged['fuel_use'] = merged['lvl'] * merged['value']
            merged['emissions'] = merged['fuel_use'] * emission_factor

            fuel_sum = merged.groupby(act_year_col)['emissions'].sum()
            if fuel_sum.sum() > 0:
                fuel_results[fuel_name] = fuel_sum

        if fuel_results:
            result_df = pd.DataFrame(fuel_results)
            result_df = result_df.sort_index()
            result_df = result_df.loc[:, (result_df != 0).any()]
            if not result_df.empty:
                self.results["Emissions by fuel (Mt CO2)"] = result_df

    def _calculate_emissions_from_activity_by_fuel(self) -> Dict[str, pd.Series]:
        """Calculate emissions from ACT × emission_factor, grouped by fuel.

        Fallback when EMISS variable is not available.
        Returns dict of {fuel_name: pd.Series with year index}.
        """
        fuel_results = {}

        ef = self.msg.par("emission_factor")
        if ef.empty:
            return fuel_results

        act = self.msg.var("ACT")
        if act.empty:
            return fuel_results

        act_year_col = 'year_act' if 'year_act' in act.columns else 'year' if 'year' in act.columns else None
        act_tec_col = 'technology' if 'technology' in act.columns else 'tec' if 'tec' in act.columns else None
        if not act_year_col or not act_tec_col:
            return fuel_results

        act = act[act[act_year_col].isin(self.plotyrs)]
        if act.empty:
            return fuel_results

        ef_tec_col = 'technology' if 'technology' in ef.columns else 'tec' if 'tec' in ef.columns else None
        if not ef_tec_col:
            return fuel_results

        all_tecs = list(ef[ef_tec_col].unique())
        if not all_tecs:
            return fuel_results

        fuel_coms = self._get_fuel_commodities()

        fuel_tecs_mapping = {}
        use_name_fallback = True

        for fuel_name, commodities in fuel_coms.items():
            fuel_tecs = self._get_technologies_by_input_fuel(commodities)
            if fuel_tecs:
                fuel_tecs_mapping[fuel_name] = fuel_tecs
                use_name_fallback = False

        if use_name_fallback:
            fuel_tecs_mapping = self._map_technologies_to_fuels_by_name(all_tecs)

        for fuel_name, fuel_tecs in fuel_tecs_mapping.items():
            matching_tecs = [t for t in all_tecs if t in fuel_tecs]
            if not matching_tecs:
                continue

            fuel_act = act[act[act_tec_col].isin(matching_tecs)]
            if fuel_act.empty:
                continue

            fuel_ef = ef[ef[ef_tec_col].isin(matching_tecs)]
            if fuel_ef.empty:
                continue

            ef_year_col = 'year_act' if 'year_act' in fuel_ef.columns else 'year' if 'year' in fuel_ef.columns else None
            if ef_year_col:
                ef_avg = fuel_ef.groupby([ef_year_col, ef_tec_col])['value'].mean().reset_index()
            else:
                ef_avg = fuel_ef.groupby([ef_tec_col])['value'].mean().reset_index()
                ef_avg[act_year_col] = self.plotyrs[0]

            act_grouped = fuel_act.groupby([act_year_col, act_tec_col])['lvl'].sum().reset_index()

            if ef_year_col:
                merged = act_grouped.merge(
                    ef_avg, left_on=[act_year_col, act_tec_col],
                    right_on=[ef_year_col, ef_tec_col], how='inner'
                )
            else:
                merged = act_grouped.merge(
                    ef_avg, left_on=[act_tec_col], right_on=[ef_tec_col], how='inner'
                )

            if merged.empty:
                continue

            merged['emissions'] = merged['lvl'] * merged['value']
            fuel_sum = merged.groupby(act_year_col)['emissions'].sum()
            if not fuel_sum.empty:
                fuel_results[fuel_name] = fuel_sum

        return fuel_results
