"""
Sector domain analyzer for MESSAGEix results.

Handles:
- Sector energy use (industry, buildings, transport, feedstock)
- Buildings energy by fuel
- Industry energy by fuel
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from analysis.base_analyzer import BaseAnalyzer


class SectorAnalyzer(BaseAnalyzer):
    """Handles sector energy use calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all sector calculations and populate self.results."""
        self._calculate_sector_results(nodeloc, yr)
        self._calculate_buildings_by_fuel(nodeloc, yr)
        self._calculate_industry_by_fuel(nodeloc, yr)

    def _calculate_sector_results(self, nodeloc: str, yr: int) -> None:
        """Calculate sectoral energy use."""
        order = self._get_commodity_order()

        # Transport
        output_par = self.msg.par("output", {"commodity": ["transport"]})
        if not output_par.empty:
            tecs = list(set(output_par.technology))
            df, df2 = self._model_output(tecs, nodeloc, "input")
            if not df.empty:
                df = self._group(df, ["year_act", "commodity"], "product", 0.0, yr)
                df_hist = self._add_history(tecs, nodeloc, df2, "commodity")
                df = self._com_order(df.add(df_hist, fill_value=0), order)
                self.results["Energy use Transport (PJ)"] = df * self.UNIT_GWA_TO_PJ

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

    def _calculate_buildings_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate buildings sector energy use by fuel."""
        df = self._calculate_fuel_use_by_sector(["rc_spec", "rc_therm", "non-comm"], nodeloc, yr)
        if not df.empty:
            self.results["Buildings energy by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ

    def _calculate_industry_by_fuel(self, nodeloc: str, yr: int) -> None:
        """Calculate industry sector energy use by fuel."""
        df = self._calculate_fuel_use_by_sector(["i_spec", "i_therm"], nodeloc, yr)
        if not df.empty:
            self.results["Industry energy by fuel (PJ)"] = df * self.UNIT_GWA_TO_PJ
