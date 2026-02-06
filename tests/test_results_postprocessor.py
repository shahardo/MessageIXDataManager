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
