"""
Analysis package for MESSAGEix results postprocessing.

Domain-specific analyzers extracted from ResultsPostprocessor:
  - BaseAnalyzer: shared helpers and infrastructure
  - ElectricityAnalyzer: electricity generation, capacity, LCOE, costs
  - EmissionsAnalyzer: GHG emissions by sector, type, fuel
  - EnergyBalanceAnalyzer: primary/final energy, trade, feedstock
  - FuelAnalyzer: gas, coal, oil, biomass supply/use
  - SectorAnalyzer: buildings, industry, transport sector metrics
  - PriceAnalyzer: energy prices and indices
"""

from analysis.base_analyzer import BaseAnalyzer, ScenarioDataWrapper
from analysis.electricity_analyzer import ElectricityAnalyzer
from analysis.emissions_analyzer import EmissionsAnalyzer
from analysis.energy_balance_analyzer import EnergyBalanceAnalyzer
from analysis.fuel_analyzer import FuelAnalyzer
from analysis.sector_analyzer import SectorAnalyzer
from analysis.price_analyzer import PriceAnalyzer

__all__ = [
    'BaseAnalyzer',
    'ScenarioDataWrapper',
    'ElectricityAnalyzer',
    'EmissionsAnalyzer',
    'EnergyBalanceAnalyzer',
    'FuelAnalyzer',
    'SectorAnalyzer',
    'PriceAnalyzer',
]
