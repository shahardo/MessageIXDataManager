"""
Tests for Dashboard Calculation Methods in ResultsAnalyzer
"""

import os
import sys
import pytest
import pandas as pd

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from managers.results_analyzer import ResultsAnalyzer
from core.data_models import ScenarioData, Parameter


class TestDashboardCalculations:
    """Test cases for dashboard calculation methods"""

    @pytest.fixture
    def sample_scenario_with_primary_energy(self):
        """Create a scenario with primary energy data"""
        scenario = ScenarioData()

        # Add primary energy parameter with yearly data
        primary_energy_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [100.0, 120.0, 140.0, 150.0]
        })
        primary_energy_param = Parameter("Primary energy supply (PJ)", primary_energy_df, {'result_type': 'variable'})
        scenario.add_parameter(primary_energy_param)

        return scenario

    @pytest.fixture
    def sample_scenario_with_electricity(self):
        """Create a scenario with electricity data"""
        scenario = ScenarioData()

        # Add electricity parameter
        electricity_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [80.0, 90.0, 100.0, 110.0]
        })
        electricity_param = Parameter("Electricity generation (TWh)", electricity_df, {'result_type': 'variable'})
        scenario.add_parameter(electricity_param)

        # Add electricity by source
        electricity_source_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1', 'R1', 'R1', 'R1', 'R1'],
            'technology': ['coal', 'gas', 'nuclear', 'solar', 'coal', 'gas', 'nuclear', 'solar'],
            'year': [2020, 2020, 2020, 2020, 2050, 2050, 2050, 2050],
            'value': [20.0, 30.0, 20.0, 10.0, 15.0, 50.0, 35.0, 10.0]  # 2050: coal=15, gas=50, nuclear=35, solar=10 (clean total=45)
        })
        electricity_source_param = Parameter("Electricity generation (TWh)", electricity_source_df, {'result_type': 'variable'})
        scenario.add_parameter(electricity_source_param)

        return scenario

    @pytest.fixture
    def sample_scenario_with_emissions(self):
        """Create a scenario with emissions data"""
        scenario = ScenarioData()

        # Add emissions parameter
        emissions_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [100.0, 90.0, 80.0, 70.0]
        })
        emissions_param = Parameter("Total GHG emissions (MtCeq)", emissions_df, {'result_type': 'variable'})
        scenario.add_parameter(emissions_param)

        return scenario

    @pytest.fixture
    def complete_scenario(self, sample_scenario_with_primary_energy, sample_scenario_with_electricity, sample_scenario_with_emissions):
        """Create a complete scenario with all data types"""
        scenario = ScenarioData()

        # Add all parameters from fixtures
        for param in sample_scenario_with_primary_energy.parameters.values():
            scenario.add_parameter(param)
        for param in sample_scenario_with_electricity.parameters.values():
            scenario.add_parameter(param)
        for param in sample_scenario_with_emissions.parameters.values():
            scenario.add_parameter(param)

        return scenario

    def test_calculate_dashboard_metrics_empty_scenario(self):
        """Test dashboard metrics calculation with empty scenario"""
        analyzer = ResultsAnalyzer()
        empty_scenario = ScenarioData()

        metrics = analyzer.calculate_dashboard_metrics(empty_scenario)

        assert metrics['primary_energy_2050'] == 0.0
        assert metrics['electricity_2050'] == 0.0
        assert metrics['clean_electricity_pct'] == 0.0
        assert metrics['emissions_2050'] == 0.0

    def test_calculate_dashboard_metrics_primary_energy_only(self, sample_scenario_with_primary_energy):
        """Test dashboard metrics with primary energy data only"""
        analyzer = ResultsAnalyzer()

        metrics = analyzer.calculate_dashboard_metrics(sample_scenario_with_primary_energy)

        assert metrics['primary_energy_2050'] == 150.0
        assert metrics['electricity_2050'] == 0.0  # No electricity data
        assert metrics['clean_electricity_pct'] == 0.0
        assert metrics['emissions_2050'] == 0.0

    def test_calculate_dashboard_metrics_electricity_only(self, sample_scenario_with_electricity):
        """Test dashboard metrics with electricity data only"""
        analyzer = ResultsAnalyzer()

        metrics = analyzer.calculate_dashboard_metrics(sample_scenario_with_electricity)

        assert metrics['primary_energy_2050'] == 0.0
        assert metrics['electricity_2050'] == 110.0
        # Clean electricity: nuclear(35) + solar(10) = 45 out of total 110 = 40.91%
        assert abs(metrics['clean_electricity_pct'] - 40.91) < 0.01
        assert metrics['emissions_2050'] == 0.0

    def test_calculate_dashboard_metrics_emissions_only(self, sample_scenario_with_emissions):
        """Test dashboard metrics with emissions data only"""
        analyzer = ResultsAnalyzer()

        metrics = analyzer.calculate_dashboard_metrics(sample_scenario_with_emissions)

        assert metrics['primary_energy_2050'] == 0.0
        assert metrics['electricity_2050'] == 0.0
        assert metrics['clean_electricity_pct'] == 0.0
        assert metrics['emissions_2050'] == 70.0

    def test_calculate_dashboard_metrics_complete_scenario(self, complete_scenario):
        """Test dashboard metrics with complete scenario"""
        analyzer = ResultsAnalyzer()

        metrics = analyzer.calculate_dashboard_metrics(complete_scenario)

        assert metrics['primary_energy_2050'] == 150.0
        assert metrics['electricity_2050'] == 110.0
        assert abs(metrics['clean_electricity_pct'] - 40.91) < 0.01  # 45/110 * 100
        assert metrics['emissions_2050'] == 70.0

    def test_dashboard_parameter_access(self, sample_scenario_with_primary_energy):
        """Test that dashboard can access specific parameters by name"""
        # Test primary energy supply parameter access (exists in fixture)
        pe_param = sample_scenario_with_primary_energy.get_parameter('Primary energy supply (PJ)')
        assert pe_param is not None  # Parameter exists in test data

        # Test electricity generation parameter access
        elec_param = sample_scenario_with_primary_energy.get_parameter('Electricity generation (TWh)')
        assert elec_param is None  # Parameter doesn't exist in test data

        # Add the expected parameters to test data
        pe_supply_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [100.0, 120.0, 140.0, 150.0]
        })
        pe_supply_param = Parameter("Primary energy supply (PJ)", pe_supply_df, {'result_type': 'variable'})
        sample_scenario_with_primary_energy.add_parameter(pe_supply_param)

        elec_gen_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [80.0, 90.0, 100.0, 110.0]
        })
        elec_gen_param = Parameter("Electricity generation (TWh)", elec_gen_df, {'result_type': 'variable'})
        sample_scenario_with_primary_energy.add_parameter(elec_gen_param)

        # Now test that parameters can be accessed
        pe_param = sample_scenario_with_primary_energy.get_parameter('Primary energy supply (PJ)')
        assert pe_param is not None
        assert not pe_param.df.empty
        assert len(pe_param.df) == 4

        elec_param = sample_scenario_with_primary_energy.get_parameter('Electricity generation (TWh)')
        assert elec_param is not None
        assert not elec_param.df.empty
        assert len(elec_param.df) == 4



    def test_clean_electricity_calculation_edge_cases(self):
        """Test clean electricity calculation edge cases"""
        analyzer = ResultsAnalyzer()

        # Test with no electricity data
        scenario1 = ScenarioData()
        metrics1 = analyzer.calculate_dashboard_metrics(scenario1)
        assert metrics1['clean_electricity_pct'] == 0.0

        # Test with electricity data but no source breakdown
        electricity_df = pd.DataFrame({
            'region': ['R1'],
            'year': [2050],
            'value': [100.0]
        })
        electricity_param = Parameter("var_electricity", electricity_df, {'result_type': 'variable'})
        scenario2 = ScenarioData()
        scenario2.add_parameter(electricity_param)

        metrics2 = analyzer.calculate_dashboard_metrics(scenario2)
        assert metrics2['electricity_2050'] == 100.0
        assert metrics2['clean_electricity_pct'] == 0.0  # No source breakdown

    def test_multiple_electricity_parameter_names(self):
        """Test that multiple electricity parameter names are tried"""
        analyzer = ResultsAnalyzer()

        # Test with var_electricity_generation
        electricity_gen_df = pd.DataFrame({
            'region': ['R1'],
            'year': [2050],
            'value': [120.0]
        })
        electricity_gen_param = Parameter("Electricity generation (TWh)", electricity_gen_df, {'result_type': 'variable'})
        scenario = ScenarioData()
        scenario.add_parameter(electricity_gen_param)

        metrics = analyzer.calculate_dashboard_metrics(scenario)
        assert metrics['electricity_2050'] == 120.0

        # Test with var_electricity_consumption
        electricity_cons_df = pd.DataFrame({
            'region': ['R1'],
            'year': [2050],
            'value': [130.0]
        })
        electricity_cons_param = Parameter("var_electricity_consumption", electricity_cons_df, {'result_type': 'variable'})
        scenario2 = ScenarioData()
        scenario2.add_parameter(electricity_cons_param)

        metrics2 = analyzer.calculate_dashboard_metrics(scenario2)
        assert metrics2['electricity_2050'] == 130.0

    def test_calculate_dashboard_metrics_with_correct_parameter_names(self):
        """Test dashboard metrics with the correct MESSAGEix parameter names"""
        analyzer = ResultsAnalyzer()

        # Create scenario with correct MESSAGEix names
        scenario = ScenarioData()

        # Add primary energy supply parameter
        pe_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'coal': [40.0, 45.0, 50.0, 55.0],
            'gas': [30.0, 35.0, 40.0, 45.0],
            'nuclear': [20.0, 25.0, 30.0, 35.0],
            'renewables': [10.0, 15.0, 20.0, 25.0]
        })
        pe_param = Parameter("Primary energy supply (PJ)", pe_df, {'result_type': 'variable'})
        scenario.add_parameter(pe_param)

        # Add electricity generation parameter
        elec_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'coal': [15.0, 17.0, 19.0, 20.0],
            'gas': [25.0, 27.0, 29.0, 30.0],
            'nuclear': [15.0, 17.0, 19.0, 25.0],
            'solar': [5.0, 7.0, 9.0, 15.0],
            'wind': [3.0, 5.0, 7.0, 10.0]
        })
        elec_param = Parameter("Electricity generation (TWh)", elec_df, {'result_type': 'variable'})
        scenario.add_parameter(elec_param)

        # Add emissions parameter
        emissions_df = pd.DataFrame({
            'region': ['R1', 'R1', 'R1', 'R1'],
            'year': [2020, 2030, 2040, 2050],
            'value': [120.0, 110.0, 100.0, 90.0]
        })
        emissions_param = Parameter("Total GHG emissions (MtCeq)", emissions_df, {'result_type': 'variable'})
        scenario.add_parameter(emissions_param)

        metrics = analyzer.calculate_dashboard_metrics(scenario)

        # Primary energy 2050: 55 + 45 + 35 + 25 = 160
        assert metrics['primary_energy_2050'] == 160.0

        # Electricity 2050: 20 + 30 + 25 + 15 + 10 = 100
        assert metrics['electricity_2050'] == 100.0

        # Clean electricity 2050: nuclear(25) + solar(15) + wind(10) = 50, so 50/100 = 50%
        assert abs(metrics['clean_electricity_pct'] - 50.0) < 0.01

        # Emissions 2050: 90
        assert metrics['emissions_2050'] == 90.0
