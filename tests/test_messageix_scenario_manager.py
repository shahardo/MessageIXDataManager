"""
Tests for MessageIX Scenario Manager

Tests the MessageIX scenario creation, management, and solving capabilities.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open

from src.core.data_models import ScenarioData, Parameter
from src.managers.messageix_scenario_manager import MessageIXScenarioManager


class TestMessageIXScenarioManager:
    """Test MessageIX Scenario Manager functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = MessageIXScenarioManager()

    def teardown_method(self):
        """Clean up after tests"""
        if self.manager.ixmp_platform:
            try:
                self.manager.close()
            except:
                pass

    def test_initialization_without_messageix(self):
        """Test manager initialization when MessageIX not available"""
        with patch.dict('sys.modules', {'ixmp': None, 'message_ix': None}):
            manager = MessageIXScenarioManager()
            assert not manager.is_available()
            assert manager.ixmp_platform is None

    def test_initialization_with_messageix(self):
        """Test manager initialization when MessageIX is available"""
        mock_platform = MagicMock()
        with patch('ixmp.Platform') as mock_ixmp_platform, \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            mock_ixmp_platform.return_value = mock_platform

            manager = MessageIXScenarioManager()
            assert manager.is_available()
            assert manager.ixmp_platform == mock_platform

    def test_create_scenario_from_excel_no_platform(self):
        """Test scenario creation when platform not available"""
        with patch.object(self.manager, 'is_available', return_value=False):
            scenario_data = ScenarioData()
            result = self.manager.create_scenario_from_excel(scenario_data)
            assert result is None

    def test_create_scenario_from_excel_success(self):
        """Test successful scenario creation"""
        # Mock scenario data
        scenario_data = ScenarioData()
        param_df = MagicMock()
        param_df.empty = False
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.dropna.return_value.unique.return_value = ['World', 'Coal', 2020, 100]

        parameter = Parameter(name="test_param", df=param_df)
        scenario_data.parameters = {"test_param": parameter}

        # Mock MessageIX objects
        mock_scenario = MagicMock()
        mock_scenario.model = "MESSAGE"
        mock_scenario.scenario = "test_scenario"
        mock_scenario.version = "new"

        mock_platform = MagicMock()
        mock_scenario_create = MagicMock()
        mock_platform.scenario.create = mock_scenario_create
        mock_scenario_create.return_value = mock_scenario

        with patch.object(self.manager, 'ixmp_platform', mock_platform), \
             patch.object(self.manager, '_populate_scenario', return_value=True), \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):

            result = self.manager.create_scenario_from_excel(
                scenario_data, "MESSAGE", "test_scenario"
            )

            assert result == mock_scenario
            mock_scenario_create.assert_called_once()
            mock_scenario.commit.assert_called_once()

    def test_populate_scenario_sets_and_parameters(self):
        """Test scenario population with sets and parameters"""
        mock_scenario = MagicMock()

        # Create test scenario data
        scenario_data = ScenarioData()
        param_df = MagicMock()
        param_df.empty = False
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.dropna.return_value.unique.return_value = ['World', 'Coal', 2020, 100]

        parameter = Parameter(name="test_param", df=param_df)
        scenario_data.parameters = {"test_param": parameter}

        with patch.object(self.manager, '_add_sets_to_scenario') as mock_add_sets, \
             patch.object(self.manager, '_add_parameters_to_scenario') as mock_add_params:

            result = self.manager._populate_scenario(mock_scenario, scenario_data)

            assert result is True
            mock_add_sets.assert_called_once_with(mock_scenario, scenario_data)
            mock_add_params.assert_called_once_with(mock_scenario, scenario_data)

    def test_add_sets_to_scenario(self):
        """Test adding sets to scenario"""
        mock_scenario = MagicMock()

        scenario_data = ScenarioData()
        param_df = MagicMock()
        param_df.empty = False
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.dropna.return_value.unique.side_effect = [
            ['World'], ['Coal'], [2020], [100]  # Return different values for each call
        ]

        parameter = Parameter(name="test_param", df=param_df)
        scenario_data.parameters = {"test_param": parameter}

        self.manager._add_sets_to_scenario(mock_scenario, scenario_data)

        # Verify add_set was called for each set type
        expected_calls = [
            ((set_name,),) for set_name in ['node', 'technology', 'year']
        ]
        mock_scenario.add_set.assert_called()
        assert mock_scenario.add_set.call_count >= 3

    def test_add_parameters_to_scenario(self):
        """Test adding parameters to scenario"""
        mock_scenario = MagicMock()

        scenario_data = ScenarioData()
        param_df = MagicMock()
        param_df.empty = False
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.dropna.return_value.unique.return_value = ['World']

        parameter = Parameter(name="test_param", df=param_df)
        scenario_data.parameters = {"test_param": parameter}

        with patch.object(self.manager, '_convert_parameter_data') as mock_convert:
            mock_convert.return_value = {'value': {'test': 1.0}, 'unit': 'GW'}

            self.manager._add_parameters_to_scenario(mock_scenario, scenario_data)

            mock_convert.assert_called_once_with(parameter)
            mock_scenario.add_par.assert_called_once_with("test_param", {'value': {'test': 1.0}, 'unit': 'GW'})

    def test_convert_parameter_data_valid(self):
        """Test parameter data conversion with valid data"""
        param_df = MagicMock()
        param_df.copy.return_value = param_df
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.set_index.return_value = MagicMock()
        param_df.set_index.return_value.to_dict.return_value = {'test': 1.0}

        parameter = Parameter(name="test_param", df=param_df)

        result = self.manager._convert_parameter_data(parameter)

        assert result is not None
        assert 'value' in result
        assert 'unit' in result
        assert result['unit'] == 'dimensionless'  # default unit

    def test_convert_parameter_data_no_index_cols(self):
        """Test parameter data conversion with no index columns"""
        param_df = MagicMock()
        param_df.copy.return_value = param_df
        param_df.columns = ['value']  # Only value column

        parameter = Parameter(name="test_param", df=param_df)

        result = self.manager._convert_parameter_data(parameter)

        assert result is None

    def test_solve_scenario_no_platform(self):
        """Test scenario solving when platform not available"""
        with patch.object(self.manager, 'is_available', return_value=False):
            mock_scenario = MagicMock()
            result = self.manager.solve_scenario(mock_scenario)

            assert not result['success']
            assert 'MessageIX platform not available' in result['message']

    def test_solve_scenario_success(self):
        """Test successful scenario solving"""
        mock_scenario = MagicMock()
        mock_scenario.solve = MagicMock()
        mock_scenario.var_list.return_value = ['OBJ']
        mock_scenario.var.return_value = {'value': 1000.0}

        with patch.object(self.manager, 'is_available', return_value=True), \
             patch('time.time', side_effect=[0.0, 1.5]):

            result = self.manager.solve_scenario(mock_scenario)

            assert result['success']
            assert result['status'] == 'optimal'
            assert result['solve_time'] == 1.5
            assert result['objective_value'] == 1000.0

    def test_solve_scenario_failure(self):
        """Test scenario solving failure"""
        mock_scenario = MagicMock()
        mock_scenario.solve.side_effect = Exception("Solver error")

        with patch.object(self.manager, 'is_available', return_value=True), \
             patch('time.time', side_effect=[0.0, 2.0]):

            result = self.manager.solve_scenario(mock_scenario)

            assert not result['success']
            assert 'Solver error' in result['message']
            assert result['solve_time'] == 2.0

    def test_export_results_no_platform(self):
        """Test results export when platform not available"""
        with patch.object(self.manager, 'is_available', return_value=False):
            mock_scenario = MagicMock()
            results = self.manager.export_results(mock_scenario)

            assert results['variables'] == {}
            assert results['equations'] == {}
            assert results['parameters'] == {}

    def test_export_results_success(self):
        """Test successful results export"""
        mock_scenario = MagicMock()
        mock_scenario.var_list.return_value = ['OBJ']
        mock_scenario.var.return_value = {'test': 1.0}
        mock_scenario.equ_list.return_value = []
        mock_scenario.par_list.return_value = []
        mock_scenario.model = "MESSAGE"
        mock_scenario.scenario = "test"
        mock_scenario.version = "1"

        with patch.object(self.manager, 'is_available', return_value=True):
            results = self.manager.export_results(mock_scenario)

            assert 'OBJ' in results['variables']
            assert results['metadata']['model'] == "MESSAGE"
            assert results['metadata']['has_solution'] is True

    def test_clone_scenario(self):
        """Test scenario cloning"""
        mock_scenario = MagicMock()
        mock_cloned = MagicMock()
        mock_scenario.clone.return_value = mock_cloned

        with patch.object(self.manager, 'is_available', return_value=True):
            result = self.manager.clone_scenario(mock_scenario, "new_name")

            assert result == mock_cloned
            mock_scenario.clone.assert_called_once_with("new_name", keep_solution=False)

    def test_delete_scenario(self):
        """Test scenario deletion"""
        mock_scenario = MagicMock()

        with patch.object(self.manager, 'is_available', return_value=True):
            result = self.manager.delete_scenario(mock_scenario)

            assert result is True
            mock_scenario.remove.assert_called_once()

    def test_list_scenarios_no_platform(self):
        """Test scenario listing when platform not available"""
        with patch.object(self.manager, 'is_available', return_value=False):
            scenarios = self.manager.list_scenarios()
            assert scenarios == []

    def test_list_scenarios_success(self):
        """Test successful scenario listing"""
        mock_scenarios = [{'model': 'MESSAGE', 'scenario': 'test'}]

        with patch.object(self.manager, 'is_available', return_value=True):
            self.manager.ixmp_platform.scenario.list.return_value = [mock_scenarios]

            result = self.manager.list_scenarios()
            assert result == mock_scenarios

    def test_close_platform(self):
        """Test platform closing"""
        mock_platform = MagicMock()
        self.manager.ixmp_platform = mock_platform

        self.manager.close()

        mock_platform.close.assert_called_once()
        assert self.manager.ixmp_platform is None


class TestMessageIXScenarioManagerIntegration:
    """Integration tests for MessageIX Scenario Manager"""

    def test_full_workflow_simulation(self):
        """Test simulated full workflow without actual MessageIX"""
        manager = MessageIXScenarioManager()

        # Mock the platform and scenario
        mock_scenario = MagicMock()
        mock_scenario.model = "MESSAGE"
        mock_scenario.scenario = "integration_test"
        mock_scenario.version = "new"
        mock_scenario.var_list.return_value = ['OBJ']
        mock_scenario.var.return_value = {'value': 500.0}

        with patch.object(manager, 'ixmp_platform') as mock_platform, \
             patch.object(manager, 'is_available', return_value=True), \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):

            # Mock platform scenario creation
            mock_platform.scenario.create.return_value = mock_scenario

            # Create test scenario data
            scenario_data = ScenarioData()
            param_df = MagicMock()
            param_df.empty = False
            param_df.columns = ['node', 'technology', 'year', 'value']
            param_df.dropna.return_value.unique.return_value = ['World']

            parameter = Parameter(name="demand", df=param_df)
            scenario_data.parameters = {"demand": parameter}

            # Test scenario creation
            scenario = manager.create_scenario_from_excel(scenario_data, "MESSAGE", "integration_test")
            assert scenario == mock_scenario

            # Test solving
            solve_result = manager.solve_scenario(scenario)
            assert solve_result['success']

            # Test results export
            results = manager.export_results(scenario)
            assert 'OBJ' in results['variables']
            assert results['metadata']['has_solution']

    def test_error_handling(self):
        """Test error handling in various scenarios"""
        manager = MessageIXScenarioManager()

        # Test with unavailable platform
        with patch.object(manager, 'is_available', return_value=False):
            assert not manager.solve_scenario(MagicMock())['success']
            assert manager.list_scenarios() == []
            assert not manager.delete_scenario(MagicMock())

        # Test scenario creation failure
        with patch.object(manager, 'is_available', return_value=True), \
             patch.object(manager, 'ixmp_platform') as mock_platform:

            mock_platform.scenario.create.side_effect = Exception("Creation failed")

            scenario_data = ScenarioData()
            result = manager.create_scenario_from_excel(scenario_data)
            assert result is None

    def test_parameter_conversion_edge_cases(self):
        """Test parameter conversion with edge cases"""
        manager = MessageIXScenarioManager()

        # Test with empty dataframe
        param_df = MagicMock()
        param_df.empty = True
        parameter = Parameter(name="empty_param", df=param_df)

        result = manager._convert_parameter_data(parameter)
        assert result is None

        # Test with minimal valid data
        param_df = MagicMock()
        param_df.copy.return_value = param_df
        param_df.columns = ['region', 'value']
        param_df.set_index.return_value = MagicMock()
        param_df.set_index.return_value.to_dict.return_value = {'test': 1.0}

        parameter = Parameter(name="minimal_param", df=param_df)
        result = manager._convert_parameter_data(parameter)

        assert result is not None
        assert 'value' in result
        assert 'unit' in result
