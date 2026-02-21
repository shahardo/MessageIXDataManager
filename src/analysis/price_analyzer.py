"""
Price domain analyzer for MESSAGEix results.

Handles:
- Commodity prices (electricity, primary, secondary, useful)
- Energy prices by sector
- Energy prices by fuel
"""

import pandas as pd
from typing import Dict, List, Optional, Any

from analysis.base_analyzer import BaseAnalyzer


class PriceAnalyzer(BaseAnalyzer):
    """Handles energy price calculations."""

    def calculate(self, nodeloc: str, yr: int) -> None:
        """Run all price calculations and populate self.results."""
        self._calculate_prices(nodeloc, yr)
        self._calculate_prices_by_sector(nodeloc, yr)
        self._calculate_prices_by_fuel(nodeloc, yr)

    def _calculate_prices(self, nodeloc: str, yr: int) -> None:
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

    def _calculate_prices_by_sector(self, nodeloc: str, yr: int) -> None:
        """Calculate energy prices by end-use sector."""
        price = self.msg.var("PRICE_COMMODITY", {"node": nodeloc})
        if price.empty:
            return

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

    def _calculate_prices_by_fuel(self, nodeloc: str, yr: int) -> None:
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
