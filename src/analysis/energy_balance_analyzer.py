"""
Energy Balance domain analyzer for MESSAGEix results.

Handles:
- Primary/final/useful energy supply and consumption
- Energy trade (imports/exports)
- Energy exports/imports by fuel
- Feedstock by fuel
- Oil derivatives supply and use by sector
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from analysis.base_analyzer import BaseAnalyzer


class EnergyBalanceAnalyzer(BaseAnalyzer):
    """Handles energy balance domain calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all energy balance calculations and populate self.results."""
        self._calculate_energy_balances(nodeloc, yr)
        self._calculate_trade(nodeloc, yr)
        self._calculate_energy_exports_by_fuel(nodeloc, yr)
        self._calculate_energy_imports_by_fuel(nodeloc, yr)
        self._calculate_feedstock_by_fuel(nodeloc, yr)
        self._calculate_oil_derivatives_supply(nodeloc, yr)
        self._calculate_oil_derivatives_use(nodeloc, yr)

    def _calculate_energy_balances(self, nodeloc: str, yr: int) -> None:
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
        end_use_commodities = ["transport", "i_spec", "i_therm", "rc_spec", "rc_therm", "non-comm"]
        output_par = self.msg.par("output", {"commodity": end_use_commodities})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
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

    def _calculate_trade(self, nodeloc: str, yr: int) -> None:
        """Calculate energy imports and exports (totals across all commodities).

        Convention in MESSAGEix: export technologies are named *_exp, import
        technologies are named *_imp.  We use the 'output' parameter because that
        tells us what commodity is being traded and its volume coefficient.
        """
        order = self._get_commodity_order()

        # Export techs: query from the technology *set* (not ACT fallback)
        # so we only see technologies that are actually defined for this region
        tecs_exp = [x for x in self.msg.set("technology") if "_exp" in str(x)]
        if tecs_exp:
            df, df2 = self._model_output(tecs_exp, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs_exp, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy exports (PJ)"] = df * self.UNIT_GWA_TO_PJ

        # Import techs: strict _imp suffix to avoid matching e.g. 'simple_ppl'
        tecs_imp = [x for x in self.msg.set("technology") if str(x).endswith("_imp")]
        if tecs_imp:
            df, df2 = self._model_output(tecs_imp, nodeloc, "output")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs_imp, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy imports (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_energy_exports_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate energy exports grouped by fuel commodity.

        Uses _get_all_technology_names() (which falls back to ACT when the
        technology set is empty) so the result is robust to partially-loaded data.
        Uses the 'output' parameter rather than 'input' because export technologies
        often only define what they export (output) not what they consume (input).
        """
        order = self._get_commodity_order()
        # Fall back to ACT-based discovery if technology set was not loaded
        tecs_exp = [x for x in self._get_all_technology_names() if "_exp" in str(x)]
        if not tecs_exp:
            return

        # output parameter: tells us which commodity is being exported and how much
        df, df2 = self._model_output(tecs_exp, nodeloc, "output")
        if df.empty:
            return

        # Aggregate by (year, commodity) and apply commodity ordering
        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
        df_hist = self._add_history(tecs_exp, nodeloc, df2, "commodity")
        df = self._com_order(df.add(df_hist, fill_value=0), order)
        self.results["Energy exports by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_energy_imports_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate energy imports grouped by fuel commodity.

        Mirror of _calculate_energy_exports_by_fuel. Import technologies output
        the imported commodity so 'output' is the correct parameter to query.
        """
        order = self._get_commodity_order()
        # Strict suffix _imp (not just contains) to avoid false positives
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

    def _calculate_feedstock_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate non-energy feedstock consumption by fuel type."""
        output_par = self.msg.par("output", {"commodity": ["i_feed"]})
        if output_par.empty:
            return

        tecs = list(set(output_par.technology))
        if not tecs:
            return

        df, df2 = self._model_output(tecs, nodeloc, "input")
        if df.empty:
            return

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)

        df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
        if not df_hist.empty:
            df = df.add(df_hist, fill_value=0)

        order = self._get_commodity_order()
        df = self._com_order(df, order)

        self.results["Feedstock by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_oil_derivatives_supply(self, nodeloc: str, yr: int) -> None:
        """Calculate oil derivatives production and supply."""
        oil_products = ["lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i",
                        "diesel", "gasoline", "kerosene", "naphtha", "lpg"]

        output_par = self.msg.par("output", {"commodity": oil_products})
        if output_par.empty:
            return

        refinery_tecs = list(set(output_par.technology))
        df, df2 = self._model_output(refinery_tecs, nodeloc, "output")
        if df.empty:
            return

        df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)

        if isinstance(df, pd.DataFrame):
            df = df[[col for col in df.columns if col in oil_products]]

        self.results["Oil derivatives supply (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_oil_derivatives_use(self, nodeloc: str, yr: int) -> None:
        """Calculate oil derivatives consumption by sector."""
        oil_products = ["lightoil", "loil_rc", "loil_i", "fueloil", "foil_rc", "foil_i",
                        "diesel", "gasoline", "kerosene", "naphtha", "lpg"]

        input_par = self.msg.par("input", {"commodity": oil_products})
        if input_par.empty:
            return

        all_oil_tecs = list(set(input_par['technology']))
        if not all_oil_tecs:
            return

        output_par = self.msg.par("output", {"commodity": oil_products})
        refinery_tecs = list(set(output_par['technology'])) if not output_par.empty else []

        consumer_tecs = [t for t in all_oil_tecs if t not in refinery_tecs]
        if not consumer_tecs:
            return

        sector_tecs = self._map_technologies_to_sectors(consumer_tecs)

        export_tecs = [t for t in consumer_tecs if '_exp' in str(t).lower() or 'export' in str(t).lower()]
        for sector in list(sector_tecs.keys()):
            sector_tecs[sector] = [t for t in sector_tecs.get(sector, []) if t not in export_tecs]

        if export_tecs:
            sector_tecs["Exports"] = export_tecs

        def _calc_oil_use(tecs, commodity_filter=None):
            """Inner helper: calculate oil use for given technologies."""
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
                return df_merge.groupby(year_col)['product'].sum()

        sector_results = {}
        for sector in ["Power", "Industry", "Buildings", "Transport", "Other", "Exports"]:
            tecs = sector_tecs.get(sector, [])
            if not tecs:
                continue

            oil_result = _calc_oil_use(tecs, commodity_filter=oil_products)

            if isinstance(oil_result, pd.DataFrame) and not oil_result.empty:
                yearly = oil_result.groupby('year_act')['product'].sum()
                sector_results[sector] = yearly
            elif isinstance(oil_result, pd.Series) and not oil_result.empty:
                sector_results[sector] = oil_result

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
                self.results["Oil derivatives use by sector (PJ)"] = result_df * 31.536
