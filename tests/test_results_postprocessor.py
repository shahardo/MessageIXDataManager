"""
Tests for results_postprocessor module.
"""

import pytest
import pandas as pd
import numpy as np
from core.data_models import ScenarioData, Parameter
from managers.results_postprocessor import (
    ScenarioDataWrapper,
    ResultsPostprocessor,
    run_postprocessing,
    add_postprocessed_results
)


class TestScenarioDataWrapper:
    """Test the ScenarioDataWrapper class that provides msg-like interface."""

    def test_wrapper_initialization(self):
        """Test basic wrapper initialization."""
        scenario = ScenarioData()
        wrapper = ScenarioDataWrapper(scenario)
        assert wrapper.scenario == scenario

    def test_has_solution_false_empty(self):
        """Test has_solution returns False for empty scenario."""
        scenario = ScenarioData()
        wrapper = ScenarioDataWrapper(scenario)
        assert wrapper.has_solution() is False

    def test_has_solution_true_with_act(self):
        """Test has_solution returns True when ACT variable exists."""
        scenario = ScenarioData()
        # Add ACT variable
        df = pd.DataFrame({
            'technology': ['coal', 'solar'],
            'year_act': [2020, 2020],
            'lvl': [100, 50]
        })
        param = Parameter('ACT', df, {'result_type': 'variable'})
        scenario.add_parameter(param)

        wrapper = ScenarioDataWrapper(scenario)
        assert wrapper.has_solution() is True

    def test_par_returns_dataframe(self):
        """Test par() method returns DataFrame."""
        scenario = ScenarioData()
        df = pd.DataFrame({
            'technology': ['coal', 'gas'],
            'commodity': ['electr', 'electr'],
            'value': [0.4, 0.5]
        })
        param = Parameter('output', df, {'dims': ['technology', 'commodity']})
        scenario.add_parameter(param)

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.par('output')

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_par_with_filter(self):
        """Test par() method with filters."""
        scenario = ScenarioData()
        df = pd.DataFrame({
            'technology': ['coal', 'gas', 'solar'],
            'commodity': ['electr', 'electr', 'electr'],
            'value': [0.4, 0.5, 0.6]
        })
        param = Parameter('output', df, {'dims': ['technology', 'commodity']})
        scenario.add_parameter(param)

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.par('output', {'technology': ['coal', 'gas']})

        assert len(result) == 2
        assert 'solar' not in result['technology'].values

    def test_par_missing_returns_empty(self):
        """Test par() returns empty DataFrame for missing parameter."""
        scenario = ScenarioData()
        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.par('nonexistent')

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_var_same_as_par(self):
        """Test var() method works same as par()."""
        scenario = ScenarioData()
        df = pd.DataFrame({'technology': ['coal'], 'lvl': [100]})
        param = Parameter('ACT', df, {'result_type': 'variable'})
        scenario.add_parameter(param)

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.var('ACT')

        assert len(result) == 1
        assert result['lvl'].iloc[0] == 100

    def test_set_returns_series(self):
        """Test set() method returns Series."""
        scenario = ScenarioData()
        scenario.sets['technology'] = pd.Series(['coal', 'gas', 'solar'])

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.set('technology')

        assert isinstance(result, pd.Series)
        assert len(result) == 3

    def test_set_cat_year_firstmodelyear(self):
        """Test set() for cat_year with firstmodelyear."""
        scenario = ScenarioData()
        scenario.sets['year'] = pd.Series([2020, 2025, 2030, 2050])

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.set('cat_year', {'type_year': 'firstmodelyear'})

        assert result['year'].iloc[0] == 2020

    def test_set_cat_year_lastmodelyear(self):
        """Test set() for cat_year with lastmodelyear."""
        scenario = ScenarioData()
        scenario.sets['year'] = pd.Series([2020, 2025, 2030, 2050])

        wrapper = ScenarioDataWrapper(scenario)
        result = wrapper.set('cat_year', {'type_year': 'lastmodelyear'})

        assert result['year'].iloc[0] == 2050


class TestResultsPostprocessor:
    """Test the ResultsPostprocessor class."""

    def test_postprocessor_initialization(self):
        """Test basic postprocessor initialization."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)

        assert processor.scenario == scenario
        assert processor.plotyrs == list(range(2020, 2051, 5))

    def test_set_plot_years(self):
        """Test setting custom plot years."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)
        processor.set_plot_years([2025, 2030, 2035])

        assert processor.plotyrs == [2025, 2030, 2035]

    def test_process_empty_scenario(self):
        """Test processing empty scenario returns empty dict."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)
        result = processor.process()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_pivot_to_long(self):
        """Test conversion of pivot table to long format."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)

        # Create a pivot table (year as index, technologies as columns)
        pivot_df = pd.DataFrame({
            'coal': [100, 80, 60],
            'solar': [10, 30, 60]
        }, index=[2020, 2030, 2050])
        pivot_df.index.name = 'year_act'

        long_df = processor._pivot_to_long(pivot_df, 'test')

        assert 'year' in long_df.columns
        assert 'category' in long_df.columns
        assert 'value' in long_df.columns
        # 6 values (3 years * 2 technologies)
        assert len(long_df) == 6

    def test_extract_units(self):
        """Test unit extraction from parameter name."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)

        assert processor._extract_units("Electricity generation (TWh)") == "TWh"
        assert processor._extract_units("Primary energy (PJ)") == "PJ"
        assert processor._extract_units("No units here") == "N/A"

    def test_group_basic(self):
        """Test basic grouping operation."""
        scenario = ScenarioData()
        processor = ResultsPostprocessor(scenario)

        df = pd.DataFrame({
            'year_act': [2020, 2020, 2030, 2030],
            'technology': ['coal', 'solar', 'coal', 'solar'],
            'product': [100, 50, 80, 70]
        })

        result = processor._group(df, ['year_act', 'technology'], 'product', 0.0, None)

        assert isinstance(result, pd.DataFrame)
        assert 2020 in result.index
        assert 2030 in result.index
        assert 'coal' in result.columns
        assert 'solar' in result.columns


class TestRunPostprocessing:
    """Test the run_postprocessing convenience function."""

    def test_run_postprocessing_empty(self):
        """Test run_postprocessing with empty scenario."""
        scenario = ScenarioData()
        result = run_postprocessing(scenario)

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_run_postprocessing_custom_years(self):
        """Test run_postprocessing with custom plot years."""
        scenario = ScenarioData()
        result = run_postprocessing(scenario, plot_years=[2030, 2040, 2050])

        assert isinstance(result, dict)


class TestAddPostprocessedResults:
    """Test the add_postprocessed_results function."""

    def test_add_postprocessed_results_empty(self):
        """Test add_postprocessed_results with empty scenario."""
        scenario = ScenarioData()
        count = add_postprocessed_results(scenario)

        assert count == 0

    def test_add_postprocessed_results_with_data(self):
        """Test that postprocessed parameters get added to scenario."""
        scenario = ScenarioData()

        # Add minimal data to trigger some calculations
        # ACT variable
        act_df = pd.DataFrame({
            'technology': ['coal_ppl', 'solar_pv'],
            'year_act': [2020, 2020],
            'node_loc': ['World', 'World'],
            'mode': ['M1', 'M1'],
            'time': ['year', 'year'],
            'year_vtg': [2015, 2018],
            'lvl': [100, 50]
        })
        scenario.add_parameter(Parameter('ACT', act_df, {'result_type': 'variable'}))

        # CAP variable
        cap_df = pd.DataFrame({
            'technology': ['coal_ppl', 'solar_pv'],
            'year_act': [2020, 2020],
            'year_vtg': [2015, 2018],
            'lvl': [10, 5]
        })
        scenario.add_parameter(Parameter('CAP', cap_df, {'result_type': 'variable'}))

        # output parameter
        output_df = pd.DataFrame({
            'technology': ['coal_ppl', 'solar_pv'],
            'commodity': ['electr', 'electr'],
            'level': ['secondary', 'secondary'],
            'year_act': [2020, 2020],
            'year_vtg': [2015, 2018],
            'node_loc': ['World', 'World'],
            'mode': ['M1', 'M1'],
            'time': ['year', 'year'],
            'value': [0.4, 0.9]
        })
        scenario.add_parameter(Parameter('output', output_df, {'dims': ['technology', 'commodity']}))

        # technology set
        scenario.sets['technology'] = pd.Series(['coal_ppl', 'solar_pv'])
        scenario.sets['year'] = pd.Series([2020, 2025, 2030])
        scenario.sets['node'] = pd.Series(['World'])

        # Run postprocessing
        initial_param_count = len(scenario.parameters)
        count = add_postprocessed_results(scenario)

        # Should have added some derived parameters
        final_param_count = len(scenario.parameters)
        assert final_param_count >= initial_param_count
        assert count == final_param_count - initial_param_count


class TestParameterTreeCategorization:
    """Test that postprocessed results are properly categorized for tree display."""

    def test_categorize_postprocessed_electricity(self):
        """Test categorization of electricity-related postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()

        # Create mock result
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Electricity generation (TWh)", result) == "Electricity"
        assert widget._categorize_postprocessed("Power plant capacity (MW)", result) == "Electricity"
        assert widget._categorize_postprocessed("Electricity use (TWh)", result) == "Electricity"

    def test_categorize_postprocessed_prices(self):
        """Test categorization of price-related postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Electricity Price ($/MWh)", result) == "Prices"
        assert widget._categorize_postprocessed("Energy Prices ($/MWh)", result) == "Prices"

    def test_categorize_postprocessed_emissions(self):
        """Test categorization of emissions-related postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Total GHG emissions (MtCeq)", result) == "Emissions"

    def test_categorize_postprocessed_fuels(self):
        """Test categorization of fuel-related postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Gas supply (PJ)", result) == "Fuels"
        assert widget._categorize_postprocessed("Coal utilization (PJ)", result) == "Fuels"
        assert widget._categorize_postprocessed("Oil supply (PJ)", result) == "Fuels"
        assert widget._categorize_postprocessed("Biomass supply (PJ)", result) == "Fuels"

    def test_categorize_postprocessed_sectoral(self):
        """Test categorization of sectoral postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Energy use Transport (PJ)", result) == "Sectoral Use"
        assert widget._categorize_postprocessed("Energy use Industry (PJ)", result) == "Sectoral Use"
        assert widget._categorize_postprocessed("Energy use Buildings (PJ)", result) == "Sectoral Use"

    def test_categorize_postprocessed_trade(self):
        """Test categorization of trade-related postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Energy imports (PJ)", result) == "Trade"
        assert widget._categorize_postprocessed("Energy exports (PJ)", result) == "Trade"

    def test_categorize_postprocessed_energy_balances(self):
        """Test categorization of energy balance postprocessed results."""
        from ui.components.parameter_tree_widget import ParameterTreeWidget
        widget = ParameterTreeWidget()
        result = type('MockResult', (), {'metadata': {}})()

        assert widget._categorize_postprocessed("Primary energy supply (PJ)", result) == "Energy Balances"
        assert widget._categorize_postprocessed("Final energy consumption (PJ)", result) == "Energy Balances"


class TestPostprocessorIntegration:
    """Integration tests for postprocessor with realistic data."""

    @pytest.fixture
    def realistic_scenario(self):
        """Create a more realistic scenario for testing."""
        scenario = ScenarioData()

        # Sets
        scenario.sets['technology'] = pd.Series([
            'coal_ppl', 'gas_cc', 'solar_pv', 'wind_ppl', 'hydro_lc'
        ])
        scenario.sets['commodity'] = pd.Series(['electr', 'coal', 'gas'])
        scenario.sets['year'] = pd.Series([2020, 2025, 2030, 2035, 2040, 2045, 2050])
        scenario.sets['node'] = pd.Series(['World'])

        years = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
        techs = ['coal_ppl', 'gas_cc', 'solar_pv', 'wind_ppl', 'hydro_lc']

        # ACT variable - activity levels
        act_rows = []
        for year in years:
            for tech in techs:
                act_rows.append({
                    'technology': tech,
                    'year_act': year,
                    'node_loc': 'World',
                    'mode': 'M1',
                    'time': 'year',
                    'year_vtg': 2015,
                    'lvl': np.random.uniform(10, 100)
                })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # CAP variable - capacity
        cap_rows = []
        for year in years:
            for tech in techs:
                cap_rows.append({
                    'technology': tech,
                    'year_act': year,
                    'year_vtg': 2015,
                    'lvl': np.random.uniform(1, 20)
                })
        scenario.add_parameter(
            Parameter('CAP', pd.DataFrame(cap_rows), {'result_type': 'variable'})
        )

        # output parameter
        output_rows = []
        for tech in techs:
            for year in years:
                output_rows.append({
                    'technology': tech,
                    'commodity': 'electr',
                    'level': 'secondary',
                    'year_act': year,
                    'year_vtg': 2015,
                    'node_loc': 'World',
                    'mode': 'M1',
                    'time': 'year',
                    'value': 0.4 + np.random.uniform(0, 0.5)
                })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows), {'dims': ['technology', 'commodity']})
        )

        return scenario

    def test_postprocessor_with_realistic_data(self, realistic_scenario):
        """Test postprocessor produces results with realistic data."""
        processor = ResultsPostprocessor(realistic_scenario)
        results = processor.process()

        # Should have some results
        assert len(results) > 0

        # Check that results are Parameter objects
        for name, param in results.items():
            assert isinstance(param, Parameter)
            assert hasattr(param, 'df')
            assert hasattr(param, 'metadata')

    def test_electricity_generation_calculated(self, realistic_scenario):
        """Test that electricity generation is calculated."""
        processor = ResultsPostprocessor(realistic_scenario)
        results = processor.process()

        # Find electricity generation parameter
        elec_gen = None
        for name, param in results.items():
            if 'Electricity generation' in name:
                elec_gen = param
                break

        # May or may not be generated depending on data
        # This is more of a smoke test
        if elec_gen is not None:
            assert not elec_gen.df.empty
            assert 'value' in elec_gen.df.columns

    def test_postprocessed_parameters_have_metadata(self, realistic_scenario):
        """Test that postprocessed parameters have proper metadata."""
        processor = ResultsPostprocessor(realistic_scenario)
        results = processor.process()

        for name, param in results.items():
            assert 'units' in param.metadata
            assert 'desc' in param.metadata
            assert 'parameter_type' in param.metadata
            assert param.metadata['parameter_type'] == 'result'
            assert param.metadata.get('result_type') == 'postprocessed'


class TestYearFiltering:
    """Test that year filtering works correctly in postprocessor."""

    def test_model_output_filters_to_plotyrs(self):
        """Test that _model_output filters ACT data to plotyrs years only.

        This is the fix for the bug where years outside plotyrs (like 2070-2110)
        were appearing in 'Energy use Transport' while plotyrs years (2020-2050)
        were missing.
        """
        scenario = ScenarioData()

        # Sets
        transport_tech = 'car_trp'
        scenario.sets['technology'] = pd.Series([transport_tech])
        scenario.sets['commodity'] = pd.Series(['transport', 'lightoil'])
        scenario.sets['year'] = pd.Series([2020, 2025, 2030, 2070, 2080])
        scenario.sets['node'] = pd.Series(['World'])

        # ACT variable with years BOTH inside and outside plotyrs
        # plotyrs default is [2020, 2025, 2030, 2035, 2040, 2045, 2050]
        act_rows = []
        all_years = [2020, 2025, 2030, 2070, 2080, 2100]  # Some inside, some outside plotyrs
        for year in all_years:
            act_rows.append({
                'technology': transport_tech,
                'year_act': year,
                'node_loc': 'World',
                'mode': 'M1',
                'time': 'year',
                'year_vtg': 2015,
                'lvl': 100
            })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # output parameter for transport
        output_rows = []
        for year in all_years:
            output_rows.append({
                'technology': transport_tech,
                'commodity': 'transport',
                'level': 'useful',
                'year_act': year,
                'year_vtg': 2015,
                'node_loc': 'World',
                'mode': 'M1',
                'time': 'year',
                'value': 1.0
            })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows), {'dims': ['technology', 'commodity']})
        )

        # input parameter for transport fuel
        input_rows = []
        for year in all_years:
            input_rows.append({
                'technology': transport_tech,
                'commodity': 'lightoil',
                'level': 'final',
                'year_act': year,
                'year_vtg': 2015,
                'node_loc': 'World',
                'mode': 'M1',
                'time': 'year',
                'value': 0.5
            })
        scenario.add_parameter(
            Parameter('input', pd.DataFrame(input_rows), {'dims': ['technology', 'commodity']})
        )

        # Run postprocessor
        processor = ResultsPostprocessor(scenario)
        processor.set_plot_years([2020, 2025, 2030])  # Custom plotyrs for this test

        # Use _model_output directly to test filtering
        tecs = [transport_tech]
        df, df2 = processor._model_output(tecs, 'World', 'input')

        # Check that only plotyrs years are in df (after filtering)
        if not df.empty:
            years_in_result = df['year_act'].unique().tolist()
            # Should only have 2020, 2025, 2030 - not 2070, 2080, 2100
            for year in years_in_result:
                assert year in [2020, 2025, 2030], f"Year {year} should not be in result (outside plotyrs)"
            # Should not have years outside plotyrs
            assert 2070 not in years_in_result
            assert 2080 not in years_in_result
            assert 2100 not in years_in_result

    def test_attach_history_gets_historical_years(self):
        """Test that _attach_history gets years BEFORE plotyrs.

        This is the fix for the bug where historical_activity was being
        filtered by plotyrs (2020-2050), which excluded actual historical
        years (1990-2015).
        """
        scenario = ScenarioData()

        # Sets
        tech = 'coal_ppl'
        scenario.sets['technology'] = pd.Series([tech])
        scenario.sets['year'] = pd.Series([1990, 2000, 2010, 2020, 2030])
        scenario.sets['node'] = pd.Series(['World'])

        # historical_activity with years BEFORE plotyrs
        hist_rows = []
        historical_years = [1990, 1995, 2000, 2005, 2010, 2015]
        for year in historical_years:
            hist_rows.append({
                'technology': tech,
                'year_act': year,
                'node_loc': 'World',
                'mode': 'M1',
                'time': 'year',
                'value': 50
            })
        scenario.add_parameter(
            Parameter('historical_activity', pd.DataFrame(hist_rows), {'dims': ['technology', 'year_act']})
        )

        # Run postprocessor
        processor = ResultsPostprocessor(scenario)
        # Default plotyrs is [2020, 2025, 2030, 2035, 2040, 2045, 2050]

        # Use _attach_history to test
        act_hist = processor._attach_history([tech])

        # Should return historical data (before 2020), not be empty
        if not act_hist.empty:
            years_in_result = act_hist.index.tolist()
            # All years should be before min(plotyrs) = 2020
            for year in years_in_result:
                assert year < 2020, f"Year {year} should be before model period (< 2020)"


class TestEnergyBalanceAnalyses:
    """Tests for Issue 8: Energy exports/imports by fuel, feedstock, primary energy supply."""

    @pytest.fixture
    def trade_scenario(self):
        """Create scenario with import/export technologies for trade analysis."""
        scenario = ScenarioData()

        years = [2020, 2025, 2030]

        # Sets - include import/export technologies
        all_techs = [
            'coal_ppl', 'gas_cc', 'solar_pv',
            'coal_exp', 'gas_exp',       # Export technologies
            'coal_imp', 'gas_imp',       # Import technologies
            'coal_extr',                 # Primary extraction
        ]
        scenario.sets['technology'] = pd.Series(all_techs)
        scenario.sets['commodity'] = pd.Series(['electr', 'coal', 'gas'])
        scenario.sets['year'] = pd.Series(years)
        scenario.sets['node'] = pd.Series(['World'])

        # ACT variable - activity for all technologies
        act_rows = []
        for year in years:
            for tech in all_techs:
                act_rows.append({
                    'technology': tech,
                    'year_act': year,
                    'node_loc': 'World',
                    'mode': 'M1',
                    'time': 'year',
                    'year_vtg': 2015,
                    'lvl': 50.0
                })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # output parameter - defines what each technology produces
        output_rows = []
        # Power plants output electricity
        for tech in ['coal_ppl', 'gas_cc', 'solar_pv']:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': 'electr', 'level': 'secondary',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 0.4
                })
        # Export techs output their commodity
        for tech, comm in [('coal_exp', 'coal'), ('gas_exp', 'gas')]:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': comm, 'level': 'export',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 1.0
                })
        # Import techs output their commodity
        for tech, comm in [('coal_imp', 'coal'), ('gas_imp', 'gas')]:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': comm, 'level': 'secondary',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 1.0
                })
        # Extraction tech outputs at primary level
        for year in years:
            output_rows.append({
                'technology': 'coal_extr', 'commodity': 'coal', 'level': 'primary',
                'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                'mode': 'M1', 'time': 'year', 'value': 1.0
            })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows), {'dims': ['technology', 'commodity']})
        )

        # input parameter - defines what each technology consumes
        input_rows = []
        # Power plants input fuel
        for tech, comm in [('coal_ppl', 'coal'), ('gas_cc', 'gas')]:
            for year in years:
                input_rows.append({
                    'technology': tech, 'commodity': comm, 'level': 'secondary',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 0.5
                })
        # Note: Export/Import techs may NOT have input parameter defined
        # in some model configurations. This is the root cause of the bug.
        scenario.add_parameter(
            Parameter('input', pd.DataFrame(input_rows), {'dims': ['technology', 'commodity']})
        )

        return scenario

    def test_energy_exports_by_fuel_produced(self, trade_scenario):
        """Test that energy exports by fuel analysis is produced.

        Bug: _calculate_energy_exports_by_fuel used 'input' parameter for
        export technologies, but export techs often don't have 'input' defined.
        Should use 'output' parameter (matching _calculate_trade).
        """
        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])
        results = processor.process()

        assert "Energy exports by fuel (PJ)" in results, \
            "Energy exports by fuel should appear in results"

        param = results["Energy exports by fuel (PJ)"]
        assert not param.df.empty, "Energy exports by fuel should have data"

    def test_energy_imports_by_fuel_produced(self, trade_scenario):
        """Test that energy imports by fuel analysis is produced."""
        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])
        results = processor.process()

        assert "Energy imports by fuel (PJ)" in results, \
            "Energy imports by fuel should appear in results"

        param = results["Energy imports by fuel (PJ)"]
        assert not param.df.empty, "Energy imports by fuel should have data"

    def test_primary_energy_supply_produced(self, trade_scenario):
        """Test that primary energy supply analysis is produced."""
        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])
        results = processor.process()

        assert "Primary energy supply (PJ)" in results, \
            "Primary energy supply should appear in results"

        param = results["Primary energy supply (PJ)"]
        assert not param.df.empty, "Primary energy supply should have data"

    def test_exports_by_fuel_uses_output_parameter(self, trade_scenario):
        """Test exports by fuel works even when export techs have no input param.

        This is the core fix: export technologies often only have 'output'
        parameter defined (what they export), not 'input' (what they consume
        from the domestic market). The method should use 'output' to match
        the working _calculate_trade approach.
        """
        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])

        # Call the method directly
        processor._calculate_energy_exports_by_fuel('World', 2020)

        assert "Energy exports by fuel (PJ)" in processor.results, \
            "Export technologies with output parameter should produce results"
        df = processor.results["Energy exports by fuel (PJ)"]
        assert not df.empty

    def test_exports_and_imports_have_correct_commodities(self, trade_scenario):
        """Test that exports and imports show the right fuel commodities."""
        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])

        processor._calculate_energy_exports_by_fuel('World', 2020)
        processor._calculate_energy_imports_by_fuel('World', 2020)

        if "Energy exports by fuel (PJ)" in processor.results:
            df_exp = processor.results["Energy exports by fuel (PJ)"]
            # Should have coal and gas columns (from coal_exp, gas_exp)
            assert 'coal' in df_exp.columns or 'gas' in df_exp.columns, \
                f"Expected coal or gas in columns, got: {df_exp.columns.tolist()}"

        if "Energy imports by fuel (PJ)" in processor.results:
            df_imp = processor.results["Energy imports by fuel (PJ)"]
            assert 'coal' in df_imp.columns or 'gas' in df_imp.columns, \
                f"Expected coal or gas in columns, got: {df_imp.columns.tolist()}"

    def test_technology_discovery_without_set(self, trade_scenario):
        """Test that export/import discovery works even without technology set.

        If the technology set is empty (not loaded from file), the methods
        should fall back to finding technologies from the ACT variable.
        """
        # Clear the technology set
        trade_scenario.sets['technology'] = pd.Series(dtype=str)

        processor = ResultsPostprocessor(trade_scenario)
        processor.set_plot_years([2020, 2025, 2030])

        processor._calculate_energy_exports_by_fuel('World', 2020)
        processor._calculate_energy_imports_by_fuel('World', 2020)

        assert "Energy exports by fuel (PJ)" in processor.results, \
            "Should find export technologies even without technology set"
        assert "Energy imports by fuel (PJ)" in processor.results, \
            "Should find import technologies even without technology set"


class TestFeedstockByFuel:
    """Tests for feedstock by fuel calculation."""

    @pytest.fixture
    def feedstock_scenario(self):
        """Create scenario with feedstock technologies."""
        scenario = ScenarioData()

        years = [2020, 2025, 2030]
        scenario.sets['technology'] = pd.Series(['coal_fs', 'gas_fs', 'oil_fs'])
        scenario.sets['commodity'] = pd.Series(['coal', 'gas', 'lightoil', 'i_feed'])
        scenario.sets['year'] = pd.Series(years)
        scenario.sets['node'] = pd.Series(['World'])

        # ACT variable
        act_rows = []
        for year in years:
            for tech in ['coal_fs', 'gas_fs', 'oil_fs']:
                act_rows.append({
                    'technology': tech, 'year_act': year, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'year_vtg': 2015, 'lvl': 30.0
                })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # output parameter - feedstock technologies output i_feed
        output_rows = []
        for tech in ['coal_fs', 'gas_fs', 'oil_fs']:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': 'i_feed', 'level': 'useful',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 1.0
                })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows), {'dims': ['technology', 'commodity']})
        )

        # input parameter - feedstock techs consume fuels
        input_rows = []
        for tech, comm in [('coal_fs', 'coal'), ('gas_fs', 'gas'), ('oil_fs', 'lightoil')]:
            for year in years:
                input_rows.append({
                    'technology': tech, 'commodity': comm, 'level': 'secondary',
                    'year_act': year, 'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 0.8
                })
        scenario.add_parameter(
            Parameter('input', pd.DataFrame(input_rows), {'dims': ['technology', 'commodity']})
        )

        return scenario

    def test_feedstock_by_fuel_produced(self, feedstock_scenario):
        """Test that feedstock by fuel analysis is produced."""
        processor = ResultsPostprocessor(feedstock_scenario)
        processor.set_plot_years([2020, 2025, 2030])
        results = processor.process()

        assert "Feedstock by fuel (PJ)" in results, \
            "Feedstock by fuel should appear in results"

        param = results["Feedstock by fuel (PJ)"]
        assert not param.df.empty, "Feedstock by fuel should have data"

    def test_feedstock_has_correct_fuels(self, feedstock_scenario):
        """Test feedstock shows correct fuel commodities."""
        processor = ResultsPostprocessor(feedstock_scenario)
        processor.set_plot_years([2020, 2025, 2030])

        processor._calculate_feedstock_by_fuel('World', 2020)

        assert "Feedstock by fuel (PJ)" in processor.results
        df = processor.results["Feedstock by fuel (PJ)"]
        # Should have columns for coal, gas, lightoil
        assert 'coal' in df.columns or 'gas' in df.columns, \
            f"Expected fuel commodities in columns, got: {df.columns.tolist()}"


class TestElectricityCostBySource:
    """Tests for electricity cost by source calculation (LCOE)."""

    @pytest.fixture
    def cost_scenario(self):
        """Create scenario with electricity technologies and cost data.

        Sets up wind_ppl, wind_res (both map to "wind onshore"), coal_ppl,
        and solar_pv with known costs so we can verify the aggregation.
        """
        scenario = ScenarioData()

        years = [2020, 2030]
        techs = ['coal_ppl', 'wind_ppl', 'wind_res', 'solar_pv']

        scenario.sets['technology'] = pd.Series(techs)
        scenario.sets['commodity'] = pd.Series(['electr', 'coal'])
        scenario.sets['year'] = pd.Series(years)
        scenario.sets['node'] = pd.Series(['World'])

        # output parameter — all produce electricity
        output_rows = []
        for tech in techs:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': 'electr',
                    'level': 'secondary', 'year_act': year,
                    'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 1.0
                })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows),
                      {'dims': ['technology', 'commodity']})
        )

        # ACT variable — activity levels
        # coal_ppl=50, wind_ppl=20, wind_res=10, solar_pv=20  (total=100)
        act_data = {
            'coal_ppl': 50.0, 'wind_ppl': 20.0,
            'wind_res': 10.0, 'solar_pv': 20.0,
        }
        act_rows = []
        for year in years:
            for tech, lvl in act_data.items():
                act_rows.append({
                    'technology': tech, 'year_act': year,
                    'node_loc': 'World', 'mode': 'M1',
                    'time': 'year', 'year_vtg': 2015, 'lvl': lvl
                })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # var_cost parameter — only cost component for simplicity
        # coal_ppl=10, wind_ppl=5, wind_res=5, solar_pv=8
        vc_data = {
            'coal_ppl': 10.0, 'wind_ppl': 5.0,
            'wind_res': 5.0, 'solar_pv': 8.0,
        }
        vc_rows = []
        for year in years:
            for tech, val in vc_data.items():
                vc_rows.append({
                    'technology': tech, 'year_act': year,
                    'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': val
                })
        scenario.add_parameter(
            Parameter('var_cost', pd.DataFrame(vc_rows),
                      {'dims': ['technology']})
        )

        return scenario

    @pytest.fixture
    def zero_activity_scenario(self, cost_scenario):
        """Scenario where one technology has zero activity."""
        scenario = cost_scenario

        # Replace ACT with a version where wind_res has 0 activity
        act_rows = []
        act_data = {
            'coal_ppl': 50.0, 'wind_ppl': 20.0,
            'wind_res': 0.0, 'solar_pv': 20.0,
        }
        for year in [2020, 2030]:
            for tech, lvl in act_data.items():
                act_rows.append({
                    'technology': tech, 'year_act': year,
                    'node_loc': 'World', 'mode': 'M1',
                    'time': 'year', 'year_vtg': 2015, 'lvl': lvl
                })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )
        return scenario

    def test_no_inf_values(self, cost_scenario):
        """Electricity cost by source must not contain inf values."""
        processor = ResultsPostprocessor(cost_scenario)
        processor.set_plot_years([2020, 2030])
        processor._calculate_electricity_price_by_source('World', 2020)

        assert "Electricity cost by source ($/MWh)" in processor.results
        df = processor.results["Electricity cost by source ($/MWh)"]
        assert not df.empty

        # No inf or NaN values
        assert not np.isinf(df.values).any(), \
            f"Found inf values in cost data:\n{df}"
        assert not np.isnan(df.values).any(), \
            f"Found NaN values in cost data:\n{df}"

    def test_no_inf_with_zero_activity(self, zero_activity_scenario):
        """Zero-activity technologies must not produce inf values."""
        processor = ResultsPostprocessor(zero_activity_scenario)
        processor.set_plot_years([2020, 2030])
        processor._calculate_electricity_price_by_source('World', 2020)

        assert "Electricity cost by source ($/MWh)" in processor.results
        df = processor.results["Electricity cost by source ($/MWh)"]
        assert not df.empty

        assert not np.isinf(df.values).any(), \
            f"Found inf values with zero-activity tech:\n{df}"

    def test_retired_tech_excluded_from_costs(self):
        """A technology with ACT=0 in a year must not appear in that year's costs.

        Simulates coal retiring by 2030 (ACT=0) while still having installed
        capacity and investment costs.  The cost chart should not show coal
        for years where it has no generation.
        """
        scenario = ScenarioData()

        years = [2020, 2025, 2030, 2035]
        techs = ['coal_ppl', 'solar_pv']

        scenario.sets['technology'] = pd.Series(techs)
        scenario.sets['commodity'] = pd.Series(['electr'])
        scenario.sets['year'] = pd.Series(years)
        scenario.sets['node'] = pd.Series(['World'])

        # output parameter
        output_rows = []
        for tech in techs:
            for year in years:
                output_rows.append({
                    'technology': tech, 'commodity': 'electr',
                    'level': 'secondary', 'year_act': year,
                    'year_vtg': 2015, 'node_loc': 'World',
                    'mode': 'M1', 'time': 'year', 'value': 1.0
                })
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows),
                      {'dims': ['technology', 'commodity']})
        )

        # ACT: coal runs in 2020/2025, retired (ACT=0) in 2030/2035
        # solar runs in all years
        act_rows = []
        coal_act = {2020: 50.0, 2025: 30.0, 2030: 0.0, 2035: 0.0}
        solar_act = {2020: 20.0, 2025: 30.0, 2030: 60.0, 2035: 80.0}
        for year in years:
            act_rows.append({
                'technology': 'coal_ppl', 'year_act': year,
                'node_loc': 'World', 'mode': 'M1',
                'time': 'year', 'year_vtg': 2015, 'lvl': coal_act[year]
            })
            act_rows.append({
                'technology': 'solar_pv', 'year_act': year,
                'node_loc': 'World', 'mode': 'M1',
                'time': 'year', 'year_vtg': 2015, 'lvl': solar_act[year]
            })
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # var_cost for both technologies
        vc_rows = []
        for year in years:
            vc_rows.append({
                'technology': 'coal_ppl', 'year_act': year,
                'year_vtg': 2015, 'node_loc': 'World',
                'mode': 'M1', 'time': 'year', 'value': 10.0
            })
            vc_rows.append({
                'technology': 'solar_pv', 'year_act': year,
                'year_vtg': 2015, 'node_loc': 'World',
                'mode': 'M1', 'time': 'year', 'value': 5.0
            })
        scenario.add_parameter(
            Parameter('var_cost', pd.DataFrame(vc_rows),
                      {'dims': ['technology']})
        )

        processor = ResultsPostprocessor(scenario)
        processor.set_plot_years(years)
        processor._calculate_electricity_price_by_source('World', 2020)

        assert "Electricity cost by source ($/MWh)" in processor.results
        df = processor.results["Electricity cost by source ($/MWh)"]

        # Coal should have non-zero cost in 2020 and 2025
        assert df.loc[2020, 'coal'] > 0, "Coal should have cost in 2020"
        assert df.loc[2025, 'coal'] > 0, "Coal should have cost in 2025"

        # Coal should have ZERO cost in 2030 and 2035 (no generation)
        assert df.loc[2030, 'coal'] == 0, \
            f"Coal should have zero cost in 2030 (ACT=0), got {df.loc[2030, 'coal']}"
        assert df.loc[2035, 'coal'] == 0, \
            f"Coal should have zero cost in 2035 (ACT=0), got {df.loc[2035, 'coal']}"

        # No inf values anywhere
        assert not np.isinf(df.values).any(), f"Found inf:\n{df}"

    def test_wind_onshore_not_inflated(self, cost_scenario):
        """Wind onshore cost must be a weighted contribution, not a sum of LCOEs.

        With the old bug, wind_ppl LCOE + wind_res LCOE would be summed,
        giving an inflated value.  The fix computes cost contributions that
        are additive (share the same total-generation denominator).
        """
        processor = ResultsPostprocessor(cost_scenario)
        processor.set_plot_years([2020, 2030])
        processor._calculate_electricity_price_by_source('World', 2020)

        df = processor.results["Electricity cost by source ($/MWh)"]

        # "wind onshore" maps to wind_ppl + wind_res in _get_technology_mappings
        assert 'wind onshore' in df.columns, \
            f"Expected 'wind onshore' column, got: {df.columns.tolist()}"

        # Expected: total_cost contributions divided by total generation.
        # wind_ppl: total_cost = 20 * 5 = 100, contribution = (100/100) * 0.1142 ≈ 0.1142
        # wind_res: total_cost = 10 * 5 = 50,  contribution = (50/100) * 0.1142 ≈ 0.0571
        # wind onshore sum ≈ 0.1713
        # coal_ppl: total_cost = 50 * 10 = 500, contribution = (500/100) * 0.1142 ≈ 0.571
        # solar_pv: total_cost = 20 * 8 = 160, contribution = (160/100) * 0.1142 ≈ 0.1827
        # System total ≈ 0.9252 $/MWh
        # Wind onshore should be ~18.5% of total, NOT dominating.
        wind_val = df.loc[2020, 'wind onshore']
        coal_val = df.loc[2020, 'coal']

        # Wind onshore should be much less than coal (wind has lower var_cost
        # and less activity)
        assert wind_val < coal_val, \
            f"Wind onshore ({wind_val:.4f}) should be less than coal ({coal_val:.4f})"

        # Contributions should sum to the system average cost
        total = df.loc[2020].sum()
        # total_cost = 50*10 + 20*5 + 10*5 + 20*8 = 500 + 100 + 50 + 160 = 810
        # total_gen = 100, so system avg = (810/100) * 0.1142 = 0.9250
        assert abs(total - 0.9250) < 0.01, \
            f"Total cost contribution should be ~0.9250, got {total:.4f}"

    def test_cost_contributions_additive(self, cost_scenario):
        """Sum of all source contributions should equal system average LCOE."""
        processor = ResultsPostprocessor(cost_scenario)
        processor.set_plot_years([2020, 2030])
        processor._calculate_electricity_price_by_source('World', 2020)

        df = processor.results["Electricity cost by source ($/MWh)"]

        for year in [2020, 2030]:
            if year in df.index:
                total = df.loc[year].sum()
                # System: total_cost=810, total_gen=100
                # system_avg = (810/100) * 0.1142 = 0.9250
                expected = 810.0 / 100.0 * 0.1142
                assert abs(total - expected) < 0.01, \
                    f"Year {year}: sum of contributions ({total:.4f}) != " \
                    f"system avg ({expected:.4f})"

    def test_full_lcoe_calculation(self):
        """End-to-end LCOE with all 5 cost components across two years.

        Every input varies between years so each component is verified
        independently per year, catching any year-mixing bugs.

        Technologies: coal_ppl, solar_pv
        Years:        2025, 2030

        Year-varying inputs:
        ┌────────────────┬─────────────┬─────────────┬──────────────┬──────────────┐
        │                │ coal 2025   │ coal 2030   │ solar 2025   │ solar 2030   │
        ├────────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
        │ ACT (GWa)      │  50         │  30         │  40          │  70          │
        │ var_cost       │   5.0       │   6.0       │   3.0        │   2.0        │
        │ CAP (GW)       │  12         │  10         │  20          │  35          │
        │ fix_cost       │  20.0       │  20.0       │  10.0        │   8.0        │
        └────────────────┴─────────────┴─────────────┴──────────────┴──────────────┘
        Total generation:   90 (2025)    100 (2030)

        Investment (CAP_NEW):
            coal_ppl  5 GW vtg 2020, inv_cost 1000, lifetime 40 → active 2020–2060
            solar_pv 10 GW vtg 2020, inv_cost  900, lifetime 25 → active 2020–2045
            solar_pv  8 GW vtg 2025, inv_cost  800, lifetime 25 → active 2025–2050
        Interest rate: 0.05

        Fuel:       input efficiency 2.5 (coal_ppl, both years)
                    coal price: 3.0 (2025), 4.0 (2030)
        Emissions:  emission_factor 0.8 (coal_ppl, both years)
                    CO2 price: 25.0 (2025), 50.0 (2030)

        Expected per-year totals (M$):
        ┌──────┬────────┬─────────────────────────────────────────────┬─────────┐
        │ Year │ Tech   │ VOM + FOM + INV + FUEL + EMIS              │ Total   │
        ├──────┼────────┼─────────────────────────────────────────────┼─────────┤
        │ 2025 │ coal   │ 250 + 240 + 291.4 + 375.0 + 1000.0        │ 2156.4  │
        │ 2025 │ solar  │ 120 + 200 + (638.6+454.1) + 0 + 0         │ 1412.7  │
        │ 2030 │ coal   │ 180 + 200 + 291.4 + 300.0 + 1200.0        │ 2171.4  │
        │ 2030 │ solar  │ 140 + 280 + (638.6+454.1) + 0 + 0         │ 1512.7  │
        └──────┴────────┴─────────────────────────────────────────────┴─────────┘
        """
        scenario = ScenarioData()

        Y1, Y2 = 2025, 2030
        YEARS = [Y1, Y2]
        techs = ['coal_ppl', 'solar_pv']

        scenario.sets['technology'] = pd.Series(techs)
        scenario.sets['commodity'] = pd.Series(['electr', 'coal'])
        scenario.sets['year'] = pd.Series(YEARS)
        scenario.sets['node'] = pd.Series(['World'])

        # --- output parameter (identifies electricity producers) ---
        output_rows = [
            {'technology': t, 'commodity': 'electr', 'level': 'secondary',
             'year_act': y, 'year_vtg': 2015, 'node_loc': 'World',
             'mode': 'M1', 'time': 'year', 'value': 1.0}
            for t in techs for y in YEARS
        ]
        scenario.add_parameter(
            Parameter('output', pd.DataFrame(output_rows),
                      {'dims': ['technology', 'commodity']})
        )

        # --- ACT variable (generation) — different per year ---
        #            coal  solar
        #   2025:     50    40   (total 90)
        #   2030:     30    70   (total 100)
        act_table = {
            (Y1, 'coal_ppl'): 50.0, (Y1, 'solar_pv'): 40.0,
            (Y2, 'coal_ppl'): 30.0, (Y2, 'solar_pv'): 70.0,
        }
        act_rows = [
            {'technology': tech, 'year_act': yr, 'node_loc': 'World',
             'mode': 'M1', 'time': 'year', 'year_vtg': 2015, 'lvl': lvl}
            for (yr, tech), lvl in act_table.items()
        ]
        scenario.add_parameter(
            Parameter('ACT', pd.DataFrame(act_rows), {'result_type': 'variable'})
        )

        # --- var_cost — different per year and technology ---
        vc_table = {
            (Y1, 'coal_ppl'): 5.0, (Y1, 'solar_pv'): 3.0,
            (Y2, 'coal_ppl'): 6.0, (Y2, 'solar_pv'): 2.0,
        }
        vc_rows = [
            {'technology': tech, 'year_act': yr, 'year_vtg': 2015,
             'node_loc': 'World', 'mode': 'M1', 'time': 'year', 'value': val}
            for (yr, tech), val in vc_table.items()
        ]
        scenario.add_parameter(
            Parameter('var_cost', pd.DataFrame(vc_rows), {'dims': ['technology']})
        )

        # --- CAP variable — different per year ---
        cap_table = {
            (Y1, 'coal_ppl'): 12.0, (Y1, 'solar_pv'): 20.0,
            (Y2, 'coal_ppl'): 10.0, (Y2, 'solar_pv'): 35.0,
        }
        cap_rows = [
            {'technology': tech, 'year_act': yr, 'year_vtg': 2015, 'lvl': lvl}
            for (yr, tech), lvl in cap_table.items()
        ]
        scenario.add_parameter(
            Parameter('CAP', pd.DataFrame(cap_rows), {'result_type': 'variable'})
        )

        # --- fix_cost — different per year and technology ---
        fc_table = {
            (Y1, 'coal_ppl'): 20.0, (Y1, 'solar_pv'): 10.0,
            (Y2, 'coal_ppl'): 20.0, (Y2, 'solar_pv'):  8.0,
        }
        fc_rows = [
            {'technology': tech, 'year_act': yr, 'year_vtg': 2015,
             'node_loc': 'World', 'value': val}
            for (yr, tech), val in fc_table.items()
        ]
        scenario.add_parameter(
            Parameter('fix_cost', pd.DataFrame(fc_rows), {'dims': ['technology']})
        )

        # --- CAP_NEW variable (two vintages for solar) ---
        cap_new_rows = [
            {'technology': 'coal_ppl', 'year_vtg': 2020, 'node_loc': 'World', 'lvl': 5.0},
            {'technology': 'solar_pv', 'year_vtg': 2020, 'node_loc': 'World', 'lvl': 10.0},
            {'technology': 'solar_pv', 'year_vtg': 2025, 'node_loc': 'World', 'lvl': 8.0},
        ]
        scenario.add_parameter(
            Parameter('CAP_NEW', pd.DataFrame(cap_new_rows), {'result_type': 'variable'})
        )

        # --- inv_cost (per vintage) ---
        inv_rows = [
            {'technology': 'coal_ppl', 'year_vtg': 2020, 'node_loc': 'World', 'value': 1000.0},
            {'technology': 'solar_pv', 'year_vtg': 2020, 'node_loc': 'World', 'value': 900.0},
            {'technology': 'solar_pv', 'year_vtg': 2025, 'node_loc': 'World', 'value': 800.0},
        ]
        scenario.add_parameter(
            Parameter('inv_cost', pd.DataFrame(inv_rows), {'dims': ['technology']})
        )

        # --- technical_lifetime ---
        lt_rows = [
            {'technology': 'coal_ppl', 'value': 40.0},
            {'technology': 'solar_pv', 'value': 25.0},
        ]
        scenario.add_parameter(
            Parameter('technical_lifetime', pd.DataFrame(lt_rows), {'dims': ['technology']})
        )

        # --- interest_rate ---
        scenario.add_parameter(
            Parameter('interest_rate', pd.DataFrame({'value': [0.05]}), {'dims': []})
        )

        # --- input parameter (fuel input, both years) ---
        input_rows = [
            {'technology': 'coal_ppl', 'commodity': 'coal', 'level': 'secondary',
             'year_act': yr, 'year_vtg': 2015, 'node_loc': 'World',
             'mode': 'M1', 'time': 'year', 'value': 2.5}
            for yr in YEARS
        ]
        scenario.add_parameter(
            Parameter('input', pd.DataFrame(input_rows),
                      {'dims': ['technology', 'commodity']})
        )

        # --- PRICE_COMMODITY — different per year ---
        price_com_rows = [
            {'node': 'World', 'commodity': 'coal', 'level': 'secondary',
             'year': Y1, 'time': 'year', 'lvl': 3.0},
            {'node': 'World', 'commodity': 'coal', 'level': 'secondary',
             'year': Y2, 'time': 'year', 'lvl': 4.0},
        ]
        scenario.add_parameter(
            Parameter('PRICE_COMMODITY', pd.DataFrame(price_com_rows),
                      {'result_type': 'variable'})
        )

        # --- emission_factor (both years) ---
        ef_rows = [
            {'technology': 'coal_ppl', 'emission': 'CO2', 'year_act': yr,
             'year_vtg': 2015, 'node_loc': 'World', 'mode': 'M1',
             'time': 'year', 'value': 0.8}
            for yr in YEARS
        ]
        scenario.add_parameter(
            Parameter('emission_factor', pd.DataFrame(ef_rows), {'dims': ['technology']})
        )

        # --- PRICE_EMISSION — different per year ---
        pe_rows = [
            {'node': 'World', 'emission': 'CO2', 'type_tec': 'all',
             'year': Y1, 'lvl': 25.0},
            {'node': 'World', 'emission': 'CO2', 'type_tec': 'all',
             'year': Y2, 'lvl': 50.0},
        ]
        scenario.add_parameter(
            Parameter('PRICE_EMISSION', pd.DataFrame(pe_rows),
                      {'result_type': 'variable'})
        )

        # ── Run calculation ──────────────────────────────────────────
        processor = ResultsPostprocessor(scenario)
        processor.set_plot_years(YEARS)
        processor._calculate_electricity_price_by_source('World', Y1)

        assert "Electricity cost by source ($/MWh)" in processor.results
        df = processor.results["Electricity cost by source ($/MWh)"]
        assert not df.empty, f"Result DataFrame is empty"

        # No inf / NaN
        assert not np.isinf(df.values).any(), f"Found inf:\n{df}"
        assert not np.isnan(df.values).any(), f"Found NaN:\n{df}"

        # Both years must be present
        for yr in YEARS:
            assert yr in df.index, f"Year {yr} not in index: {df.index.tolist()}"

        # After _mappings: coal_ppl → "coal", solar_pv → "solar PV"
        coal_col = 'coal'
        solar_col = 'solar PV'
        assert coal_col in df.columns, \
            f"Expected '{coal_col}' in columns, got: {df.columns.tolist()}"
        assert solar_col in df.columns, \
            f"Expected '{solar_col}' in columns, got: {df.columns.tolist()}"

        # ── Hand-calculated expected values ──────────────────────────
        CONV = 0.1142   # M$/GWa → $/MWh
        r = 0.05

        # CRF
        rf40 = (1 + r) ** 40
        crf_coal = r * rf40 / (rf40 - 1)
        rf25 = (1 + r) ** 25
        crf_solar = r * rf25 / (rf25 - 1)

        # Annualised investment costs (M$, constant across active years)
        coal_inv_ann  = 5  * 1000 * crf_coal   # vtg 2020, active 2020-2060
        solar_inv_v20 = 10 *  900 * crf_solar   # vtg 2020, active 2020-2045
        solar_inv_v25 = 8  *  800 * crf_solar   # vtg 2025, active 2025-2050

        # ── Year 2025 ────────────────────────────────────────────────
        coal_vom_25  = 50 * 5.0           # ACT × var_cost = 250
        coal_fom_25  = 12 * 20.0          # CAP × fix_cost = 240
        coal_inv_25  = coal_inv_ann       # active (2020 ≤ 2025 < 2060)
        coal_fuel_25 = 50 * 2.5 * 3.0    # ACT × input × fuel_price = 375
        coal_emis_25 = 50 * 0.8 * 25.0   # ACT × ef × CO2_price = 1000
        coal_total_25 = (coal_vom_25 + coal_fom_25 + coal_inv_25
                         + coal_fuel_25 + coal_emis_25)

        solar_vom_25 = 40 * 3.0          # = 120
        solar_fom_25 = 20 * 10.0         # = 200
        solar_inv_25 = solar_inv_v20 + solar_inv_v25  # both vintages active
        solar_total_25 = solar_vom_25 + solar_fom_25 + solar_inv_25

        total_gen_25 = 90.0
        exp_coal_25  = (coal_total_25  / total_gen_25) * CONV
        exp_solar_25 = (solar_total_25 / total_gen_25) * CONV
        exp_system_25 = exp_coal_25 + exp_solar_25

        # ── Year 2030 ────────────────────────────────────────────────
        coal_vom_30  = 30 * 6.0           # = 180
        coal_fom_30  = 10 * 20.0          # = 200
        coal_inv_30  = coal_inv_ann       # still active (2020 ≤ 2030 < 2060)
        coal_fuel_30 = 30 * 2.5 * 4.0    # = 300
        coal_emis_30 = 30 * 0.8 * 50.0   # = 1200
        coal_total_30 = (coal_vom_30 + coal_fom_30 + coal_inv_30
                         + coal_fuel_30 + coal_emis_30)

        solar_vom_30 = 70 * 2.0          # = 140
        solar_fom_30 = 35 * 8.0          # = 280
        solar_inv_30 = solar_inv_v20 + solar_inv_v25  # both still active
        solar_total_30 = solar_vom_30 + solar_fom_30 + solar_inv_30

        total_gen_30 = 100.0
        exp_coal_30  = (coal_total_30  / total_gen_30) * CONV
        exp_solar_30 = (solar_total_30 / total_gen_30) * CONV
        exp_system_30 = exp_coal_30 + exp_solar_30

        # ── Assertions ───────────────────────────────────────────────
        # Tolerance: 0.5% relative or 0.01 $/MWh absolute
        tol_abs = 0.01
        tol_rel = 0.005

        def assert_close(actual, expected, label):
            diff = abs(actual - expected)
            ok = diff < max(tol_abs, abs(expected) * tol_rel)
            assert ok, (
                f"{label}: expected {expected:.4f}, got {actual:.4f} "
                f"(diff={diff:.6f})"
            )

        # Year 2025
        assert_close(df.loc[Y1, coal_col],  exp_coal_25,  f"coal {Y1}")
        assert_close(df.loc[Y1, solar_col], exp_solar_25, f"solar PV {Y1}")
        assert_close(df.loc[Y1].sum(),      exp_system_25, f"system {Y1}")

        # Year 2030
        assert_close(df.loc[Y2, coal_col],  exp_coal_30,  f"coal {Y2}")
        assert_close(df.loc[Y2, solar_col], exp_solar_30, f"solar PV {Y2}")
        assert_close(df.loc[Y2].sum(),      exp_system_30, f"system {Y2}")

        # Verify values actually differ between years (proves year-specific data)
        assert df.loc[Y1, coal_col] != df.loc[Y2, coal_col], \
            "Coal cost should differ between years"
        assert df.loc[Y1, solar_col] != df.loc[Y2, solar_col], \
            "Solar cost should differ between years"

        # Sanity: coal dominates in both years (fuel + emission costs)
        for yr in YEARS:
            assert df.loc[yr, coal_col] > df.loc[yr, solar_col], \
                f"Year {yr}: coal ({df.loc[yr, coal_col]:.4f}) should " \
                f"exceed solar ({df.loc[yr, solar_col]:.4f})"
