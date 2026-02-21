"""
Fuel domain analyzer for MESSAGEix results.

Handles:
- Gas results (demand/supply)
- Coal results
- Oil results
- Biomass results
- Gas supply by source (production/imports/exports)
- Gas utilization by sector
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from analysis.base_analyzer import BaseAnalyzer


class FuelAnalyzer(BaseAnalyzer):
    """Handles fuel supply and demand domain calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all fuel calculations and populate self.results."""
        self._calculate_gas_results(nodeloc, yr)
        self._calculate_coal_results(nodeloc, yr)
        self._calculate_oil_results(nodeloc, yr)
        self._calculate_biomass_results(nodeloc, yr)
        self._calculate_gas_supply_by_source(nodeloc, yr)
        self._calculate_gas_utilization_by_sector(nodeloc, yr)

    def _calculate_gas_results(self, nodeloc: str, yr: int) -> None:
        """Calculate natural gas demand by sector.

        Pattern used for all fuel demand calculations:
          1. Find technologies that consume the fuel (via 'input' parameter)
          2. Compute energy flow: ACT × input_efficiency = fuel consumed (GWa)
          3. Group by (year, technology), add historical data
          4. Map technologies to sectors via _mappings() and convert to PJ
        """
        order = self._get_commodity_order()
        gas_tecs = self._get_technologies_by_input_fuel(["gas"])

        if gas_tecs:
            df, df2 = self._model_output(gas_tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(gas_tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                # _mappings() aggregates technologies into sector groups (Power, Industry, etc.)
                self.results["Gas demand (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_coal_results(self, nodeloc: str, yr: int) -> None:
        """Calculate coal demand by sector."""
        coal_tecs = self._get_technologies_by_input_fuel(["coal", "coal_rc", "coal_i"])

        if coal_tecs:
            df, df2 = self._model_output(coal_tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(coal_tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Coal demand (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_oil_results(self, nodeloc: str, yr: int) -> None:
        """Calculate oil demand by sector."""
        oil_commodities = ["lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i", "crudeoil"]
        oil_tecs = self._get_technologies_by_input_fuel(oil_commodities)

        if oil_tecs:
            df, df2 = self._model_output(oil_tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(oil_tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Oil demand (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_biomass_results(self, nodeloc: str, yr: int) -> None:
        """Calculate biomass demand by sector."""
        biomass_tecs = self._get_technologies_by_input_fuel(["biomass", "biomass_rc", "biomass_nc"])

        if biomass_tecs:
            df, df2 = self._model_output(biomass_tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "technology"], "product", 0.0, yr)
                df_hist = self._add_history(biomass_tecs, nodeloc, df2, "technology")
                df = df.add(df_hist, fill_value=0)
                self.results["Biomass demand (PJ)"] = self._mappings(df) * self.UNIT_GWA_TO_PJ

    def _calculate_gas_supply_by_source(self, nodeloc: str, yr: int) -> None:
        """Calculate gas supply by source (production, imports, exports).

        Total supply = domestic production + imports − exports.
        Each source is stored separately so the stacked chart shows the breakdown.
        Exports appear as a negative bar in the chart.
        """
        gas_commodities = ["gas"]
        results = {}

        def _calc_gas_supply(tecs, par_name, commodity_filter=None, level_filter=None):
            """Inner helper: calculate gas supply from technologies."""
            if not tecs:
                return pd.Series(dtype=float)

            df_act = self.msg.var("ACT", {"technology": tecs})
            if df_act.empty:
                return pd.Series(dtype=float)

            filters = {"technology": tecs}
            if commodity_filter:
                filters["commodity"] = commodity_filter
            if level_filter:
                filters["level"] = level_filter

            df_par = self.msg.par(par_name, filters)
            if df_par.empty:
                return pd.Series(dtype=float)

            tec_col = 'technology' if 'technology' in df_act.columns else 'tec'
            com_col = 'commodity' if 'commodity' in df_par.columns else None

            if com_col:
                df_par_agg = df_par.groupby([tec_col, com_col], as_index=False)['value'].mean()
            else:
                df_par_agg = df_par.groupby([tec_col], as_index=False)['value'].mean()

            df_merge = df_act.merge(df_par_agg, how="left", left_on=tec_col, right_on=tec_col)

            if 'lvl' in df_merge.columns and 'value' in df_merge.columns:
                df_merge['product'] = df_merge['lvl'] * df_merge['value']
            elif 'value' in df_merge.columns:
                df_merge['product'] = df_merge['value']
            else:
                return pd.Series(dtype=float)

            year_col = 'year_act' if 'year_act' in df_merge.columns else 'year_vtg'

            if com_col and 'commodity' in df_merge.columns:
                return df_merge.groupby([year_col, 'commodity'])['product'].sum().reset_index()
            else:
                return df_merge.groupby([year_col])['product'].sum()

        # 1. Domestic production - technologies outputting gas at primary level
        prod_par = self.msg.par("output", {"commodity": gas_commodities, "level": ["primary"]})
        if not prod_par.empty:
            prod_tecs = list(set(prod_par['technology'])) if 'technology' in prod_par.columns else []
            if prod_tecs:
                prod_result = _calc_gas_supply(prod_tecs, "output",
                                               commodity_filter=gas_commodities,
                                               level_filter="primary")
                if isinstance(prod_result, pd.DataFrame) and not prod_result.empty:
                    prod_yearly = prod_result.groupby('year_act')['product'].sum()
                    results["Production"] = prod_yearly
                elif isinstance(prod_result, pd.Series) and not prod_result.empty:
                    results["Production"] = prod_result

        # 2. Imports - technologies with "gas" and "_imp" in name
        all_tecs = list(self.msg.set("technology"))
        gas_imp_tecs = [x for x in all_tecs if "gas" in str(x).lower() and "_imp" in str(x).lower()] if all_tecs else []

        if gas_imp_tecs:
            imp_result = _calc_gas_supply(gas_imp_tecs, "output")
            if isinstance(imp_result, pd.DataFrame) and not imp_result.empty:
                results["Imports"] = imp_result.groupby('year_act')['product'].sum()
            elif isinstance(imp_result, pd.Series) and not imp_result.empty:
                results["Imports"] = imp_result

        # 3. Exports - technologies with "gas" and "_exp" in name
        gas_exp_tecs = [x for x in all_tecs if "gas" in str(x).lower() and "_exp" in str(x).lower()] if all_tecs else []

        if gas_exp_tecs:
            exp_result = _calc_gas_supply(gas_exp_tecs, "input",
                                          commodity_filter=gas_commodities)
            if isinstance(exp_result, pd.DataFrame) and not exp_result.empty:
                results["Exports"] = -exp_result.groupby('year_act')['product'].sum()
            elif isinstance(exp_result, pd.Series) and not exp_result.empty:
                results["Exports"] = -exp_result

        if results:
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
                result_df["Total Supply"] = (
                    result_df.get("Production", 0) +
                    result_df.get("Imports", 0) +
                    result_df.get("Exports", 0)
                )
                self.results["Gas supply by source (PJ)"] = result_df * 31.536

    def _calculate_gas_utilization_by_sector(self, nodeloc: str, yr: int) -> None:
        """Calculate gas consumption by sector."""
        gas_commodities = ["gas"]

        input_par = self.msg.par("input", {"commodity": gas_commodities})
        if input_par.empty:
            return

        all_gas_tecs = list(set(input_par['technology'])) if 'technology' in input_par.columns else []
        if not all_gas_tecs:
            return

        sector_tecs = self._map_technologies_to_sectors(all_gas_tecs)

        export_tecs = [t for t in all_gas_tecs if '_exp' in str(t).lower() or 'export' in str(t).lower()]

        for sector in list(sector_tecs.keys()):
            sector_tecs[sector] = [t for t in sector_tecs.get(sector, []) if t not in export_tecs]

        other_tecs = sector_tecs.get("Other", [])
        if "Other" in sector_tecs:
            del sector_tecs["Other"]

        balance_patterns = ['_bal', 'balance', 'bal_', 'gas_bal', 'dummy']
        filtered_other = [t for t in other_tecs if not any(p in str(t).lower() for p in balance_patterns)]

        if filtered_other:
            sector_tecs["Other"] = filtered_other

        if export_tecs:
            sector_tecs["Exports"] = export_tecs

        def _calc_gas_use(tecs, commodity_filter=None):
            """Inner helper: calculate gas use for given technologies."""
            if not tecs:
                return pd.Series(dtype=float)

            df_act = self.msg.var("ACT", {"technology": tecs})
            if df_act.empty:
                return pd.Series(dtype=float)

            filters = {"technology": tecs}
            if commodity_filter:
                filters["commodity"] = commodity_filter

            df_par = self.msg.par("input", filters)
            if df_par.empty:
                return pd.Series(dtype=float)

            tec_col = 'technology' if 'technology' in df_act.columns else 'tec'
            com_col = 'commodity' if 'commodity' in df_par.columns else None

            if com_col:
                df_par_agg = df_par.groupby([tec_col, com_col], as_index=False)['value'].mean()
            else:
                df_par_agg = df_par.groupby([tec_col], as_index=False)['value'].mean()

            df_merge = df_act.merge(df_par_agg, how="left", left_on=tec_col, right_on=tec_col)

            if 'lvl' in df_merge.columns and 'value' in df_merge.columns:
                df_merge['product'] = df_merge['lvl'] * df_merge['value']
            elif 'value' in df_merge.columns:
                df_merge['product'] = df_merge['value']
            else:
                return pd.Series(dtype=float)

            year_col = 'year_act' if 'year_act' in df_merge.columns else 'year_vtg'

            if com_col and 'commodity' in df_merge.columns:
                return df_merge.groupby([year_col, 'commodity'])['product'].sum().reset_index()
            else:
                return df_merge.groupby([year_col])['product'].sum()

        sector_results = {}
        for sector in ["Power", "Industry", "Buildings", "Transport", "Other", "Exports"]:
            tecs = sector_tecs.get(sector, [])
            if not tecs:
                continue

            gas_result = _calc_gas_use(tecs, commodity_filter=gas_commodities)

            if isinstance(gas_result, pd.DataFrame) and not gas_result.empty:
                sector_results[sector] = gas_result.groupby('year_act')['product'].sum()
            elif isinstance(gas_result, pd.Series) and not gas_result.empty:
                sector_results[sector] = gas_result

        if sector_results:
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
                self.results["Gas use by sector (PJ)"] = result_df * 31.536
