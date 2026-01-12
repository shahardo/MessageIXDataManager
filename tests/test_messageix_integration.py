"""
Integration Tests for MessageIX/GAMS Integration

Tests the complete workflow from Excel input to GAMS solving and result analysis.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.core.data_models import ScenarioData, Parameter
from src.managers.messageix_scenario_manager import MessageIXScenarioManager
from src.managers.gams_solver import GAMSSolver
from src.managers.solver_manager import SolverManager


class TestMessageIXIntegration:
    """Integration tests for the complete MessageIX/GAMS workflow"""

    def setup_method(self):
        """Set up test fixtures"""
        # Mock platform creation during initialization
        with patch('ixmp.Platform') as mock_platform_class, \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform
            self.scenario_manager = MessageIXScenarioManager()
            # Ensure the mock platform is set
            self.scenario_manager.ixmp_platform = mock_platform

        self.gams_solver = GAMSSolver()
        self.solver_manager = SolverManager()

    def teardown_method(self):
        """Clean up after tests"""
        if self.scenario_manager.ixmp_platform:
            try:
                self.scenario_manager.close()
            except:
                pass

    def test_end_to_end_workflow_simulation(self):
        """Test complete workflow: Excel → MessageIX → GAMS → Results"""
        # Create test scenario data
        scenario_data = self._create_test_scenario_data()

        # Mock all external dependencies
        with patch.dict('sys.modules', {
            'ixmp': MagicMock(),
            'message_ix': MagicMock(),
            'gamsapi': MagicMock()
        }), \
             patch('src.config.settings.config.detect_gams_path', return_value='/mock/gams'), \
             patch('src.config.settings.config.detect_messageix_db_path', return_value='/tmp/test.db'), \
             patch('os.makedirs'), \
             patch('ixmp.Platform') as mock_platform_class:

            # Mock IXMP platform and scenario
            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            mock_scenario = MagicMock()
            mock_scenario.model = "MESSAGE"
            mock_scenario.scenario = "integration_test"
            mock_scenario.version = "new"
            mock_scenario.solve = MagicMock()
            mock_scenario.var_list.return_value = ['OBJ']
            mock_scenario.var.return_value = {'value': 1000.0}
            mock_scenario.equ_list.return_value = []
            mock_scenario.par_list.return_value = []

            mock_platform.scenario.create.return_value = mock_scenario

            # Step 1: Create MessageIX scenario from Excel data
            scenario = self.scenario_manager.create_scenario_from_excel(
                scenario_data, "MESSAGE", "integration_test"
            )

            assert scenario == mock_scenario
            mock_platform.scenario.create.assert_called_once()

            # Step 2: Solve the scenario
            solve_result = self.scenario_manager.solve_scenario(scenario)

            assert solve_result['success']
            assert solve_result['status'] == 'optimal'
            assert solve_result['objective_value'] == 1000.0

            # Step 3: Export results
            results = self.scenario_manager.export_results(scenario)

            assert results['variables']['OBJ'] == {'value': 1000.0}
            assert results['metadata']['has_solution'] is True
            assert results['metadata']['model'] == "MESSAGE"

    def test_solver_manager_integration(self):
        """Test SolverManager integration with MessageIX/GAMS"""
        # Test that GAMS is detected in available solvers
        with patch('src.managers.solver_manager.gamsapi') as mock_gamsapi:
            mock_gamsapi.return_value = True  # Simulate GAMS available

            solvers = self.solver_manager.get_available_solvers()

            # GAMS should be in the list when gamsapi is available
            assert 'gams' in solvers

    def test_gams_solver_messageix_integration(self):
        """Test GAMS solver integration with MessageIX scenarios"""
        self.gams_solver.gams_path = '/mock/gams/path'

        with patch.object(self.gams_solver, 'is_available', return_value=True), \
             patch.object(self.gams_solver, 'run_gams_direct') as mock_run:

            # Mock successful GAMS execution
            mock_run.return_value = {
                'success': True,
                'return_code': 0,
                'output': ['Optimal solution found'],
                'execution_time': 2.5,
                'lst_file': '/tmp/model.lst'
            }

            # Test option file creation
            options = self.gams_solver.get_solver_options()
            assert 'solver' in options
            assert options['solver'] == 'CPLEX'

            with tempfile.TemporaryDirectory() as temp_dir:
                opt_file = self.gams_solver.create_option_file(options, temp_dir)
                assert os.path.exists(opt_file)

    def test_error_handling_integration(self):
        """Test error handling across the integration"""
        # Test scenario creation failure
        with patch.object(self.scenario_manager, 'is_available', return_value=False):
            scenario_data = ScenarioData()
            result = self.scenario_manager.create_scenario_from_excel(scenario_data)
            assert result is None

        # Test solve failure
        with patch.object(self.scenario_manager, 'is_available', return_value=True):
            mock_scenario = MagicMock()
            mock_scenario.solve.side_effect = Exception("Solver error")

            result = self.scenario_manager.solve_scenario(mock_scenario)
            assert not result['success']
            assert 'Solver error' in result['message']

        # Test GAMS unavailability
        self.gams_solver.gams_path = None
        assert not self.gams_solver.is_available()

        with patch.object(self.gams_solver, 'is_available', return_value=False):
            result = self.gams_solver.run_gams_direct('/fake.gms', '/tmp')
            assert not result['success']

    def test_configuration_integration(self):
        """Test configuration system integration"""
        from src.config import config

        # Test that config provides expected paths
        gams_path = config.detect_gams_path()
        db_path = config.detect_messageix_db_path()

        # Paths should be strings or None
        assert isinstance(gams_path, (str, type(None)))
        assert isinstance(db_path, (str, type(None)))

        # Test environment validation with mocked MessageIX check
        from src.config.settings import Config
        with patch.object(Config, '_check_messageix_availability', return_value={
            'available': False,
            'warnings': ['MessageIX not available for testing'],
            'errors': []
        }):
            validation = config.validate_environment()
            assert isinstance(validation, dict)
            assert 'gams_available' in validation
            assert 'messageix_available' in validation

    def test_data_conversion_integration(self):
        """Test data conversion from application format to MessageIX format"""
        # Create test parameter data
        param_df = MagicMock()
        param_df.empty = False
        param_df.copy.return_value = param_df
        param_df.columns = ['node', 'technology', 'year', 'value']
        param_df.set_index.return_value = MagicMock()
        param_df.set_index.return_value.to_dict.return_value = {'test': 1.0}

        parameter = Parameter(name="test_param", df=param_df, metadata={'units': 'test', 'desc': 'Test parameter', 'dims': []})

        # Test parameter conversion
        result = self.scenario_manager._convert_parameter_data(parameter)

        assert result is not None
        assert 'value' in result
        assert 'unit' in result
        assert result['unit'] == 'dimensionless'

        # Test with empty parameter
        param_df.empty = True
        parameter_empty = Parameter(name="empty_param", df=param_df, metadata={'units': 'test', 'desc': 'Empty parameter', 'dims': []})
        result_empty = self.scenario_manager._convert_parameter_data(parameter_empty)
        assert result_empty is None

    def test_scenario_lifecycle_integration(self):
        """Test complete scenario lifecycle"""
        with patch.dict('sys.modules', {
            'ixmp': MagicMock(),
            'message_ix': MagicMock()
        }), \
             patch('ixmp.Platform') as mock_platform_class:

            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            # Create scenario
            mock_scenario = MagicMock()
            mock_scenario.scenario = "lifecycle_test"
            mock_platform.scenario.create.return_value = mock_scenario

            scenario_data = self._create_test_scenario_data()
            scenario = self.scenario_manager.create_scenario_from_excel(
                scenario_data, "MESSAGE", "lifecycle_test"
            )

            assert scenario == mock_scenario

            # Clone scenario
            mock_cloned = MagicMock()
            mock_scenario.clone.return_value = mock_cloned

            cloned = self.scenario_manager.clone_scenario(scenario, "cloned_scenario")
            assert cloned == mock_cloned

            # Delete scenario
            result = self.scenario_manager.delete_scenario(scenario)
            assert result is True
            mock_scenario.remove.assert_called_once()

            # List scenarios
            mock_scenarios = [{'model': 'MESSAGE', 'scenario': 'test'}]
            mock_platform.scenario.list.return_value = [mock_scenarios]

            scenarios = self.scenario_manager.list_scenarios()
            assert scenarios == mock_scenarios

    def test_performance_integration(self):
        """Test performance aspects of the integration"""
        import time

        # Test scenario creation performance
        scenario_data = self._create_test_scenario_data()

        with patch.dict('sys.modules', {
            'ixmp': MagicMock(),
            'message_ix': MagicMock()
        }), \
             patch('ixmp.Platform') as mock_platform_class:

            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            mock_scenario = MagicMock()
            mock_platform.scenario.create.return_value = mock_scenario

            start_time = time.time()
            scenario = self.scenario_manager.create_scenario_from_excel(scenario_data)
            end_time = time.time()

            # Should complete in reasonable time (not too long)
            assert end_time - start_time < 60.0  # Should complete within a minute
            assert scenario is not None

    def test_memory_management_integration(self):
        """Test memory management and cleanup"""
        with patch.dict('sys.modules', {
            'ixmp': MagicMock(),
            'message_ix': MagicMock()
        }), \
             patch('ixmp.Platform') as mock_platform_class:

            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            # Create multiple scenarios
            scenarios = []
            for i in range(5):
                mock_scenario = MagicMock()
                mock_scenario.scenario = f"test_{i}"
                scenarios.append(mock_scenario)

            mock_platform.scenario.create.side_effect = scenarios

            # Test platform cleanup
            self.scenario_manager.close()

            mock_platform.close.assert_called_once()
            assert self.scenario_manager.ixmp_platform is None

    def _create_test_scenario_data(self) -> ScenarioData:
        """Create test scenario data for integration tests"""
        scenario_data = ScenarioData()

        # Create mock parameter dataframes
        param_dfs = {
            'demand': self._create_mock_dataframe(['node', 'technology', 'year', 'value'],
                                                [['World', 'Coal', 2020, 100.0]]),
            'capacity': self._create_mock_dataframe(['node', 'technology', 'value'],
                                                  [['World', 'Coal', 50.0]]),
            'cost': self._create_mock_dataframe(['node', 'technology', 'year', 'value'],
                                              [['World', 'Coal', 2020, 25.0]])
        }

        # Create parameters
        for param_name, param_df in param_dfs.items():
            parameter = Parameter(name=param_name, df=param_df, metadata={'units': 'test', 'desc': f'Test {param_name}', 'dims': []})
            scenario_data.parameters[param_name] = parameter

        return scenario_data

    def _create_mock_dataframe(self, columns, data):
        """Create a mock DataFrame for testing"""
        df = MagicMock()
        df.empty = False
        df.columns = columns

        # Mock unique values for each column
        unique_values = []
        for col_idx, col_name in enumerate(columns):
            if col_name == 'value':
                continue
            col_values = list(set(row[col_idx] for row in data))
            unique_values.append(col_values)

        df.dropna.return_value.unique.side_effect = unique_values
        df.copy.return_value = df

        return df


class TestMessageIXSolverIntegration:
    """Test SolverManager integration with MessageIX components"""

    def test_solver_manager_messageix_detection(self):
        """Test that SolverManager properly detects MessageIX availability"""
        solver_manager = SolverManager()

        # Test with MessageIX available
        with patch.dict('sys.modules', {
            'ixmp': MagicMock(),
            'message_ix': MagicMock()
        }):
            assert solver_manager.detect_messageix_environment()

        # Test without MessageIX
        with patch.dict('sys.modules', {'ixmp': None, 'message_ix': None}):
            assert not solver_manager.detect_messageix_environment()

    def test_solver_manager_gams_integration(self):
        """Test SolverManager GAMS solver integration"""
        solver_manager = SolverManager()

        # Test GAMS detection
        with patch('src.managers.solver_manager.gamsapi', create=True):
            # Mock gamsapi import success
            import sys
            mock_gamsapi = MagicMock()
            sys.modules['gamsapi'] = mock_gamsapi

            try:
                solvers = solver_manager.get_available_solvers()
                assert 'gams' in solvers
            finally:
                # Clean up
                if 'gamsapi' in sys.modules:
                    del sys.modules['gamsapi']

    def test_solver_manager_fallback_behavior(self):
        """Test SolverManager fallback behavior when solvers unavailable"""
        solver_manager = SolverManager()

        # Ensure at least GLPK is always available as fallback
        solvers = solver_manager.get_available_solvers()
        assert 'glpk' in solvers
        assert len(solvers) >= 1


class TestMessageIXUIIntegration:
    """Test UI integration points (mocked)"""

    def test_solver_status_integration(self):
        """Test solver status reporting integration"""
        solver_manager = SolverManager()

        status_updates = []

        def mock_callback(status):
            status_updates.append(status)

        solver_manager.set_status_callback(mock_callback)

        # Simulate status update (this would normally happen during solving)
        solver_manager._update_status("Test status")

        assert "Test status" in status_updates

    def test_output_callback_integration(self):
        """Test output callback integration"""
        solver_manager = SolverManager()

        output_messages = []

        def mock_callback(message):
            output_messages.append(message)

        solver_manager.set_output_callback(mock_callback)

        # Simulate output message
        solver_manager._log_output("Test output")

        assert "Test output" in output_messages


class TestMessageIXRobustness:
    """Test robustness and edge cases in the integration"""

    def test_partial_system_availability(self):
        """Test behavior when only some components are available"""
        # Mock platform creation during manager initialization
        with patch('ixmp.Platform') as mock_platform_class, \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            scenario_manager = MessageIXScenarioManager()
            scenario_manager.ixmp_platform = mock_platform

        gams_solver = GAMSSolver()

        # Test with MessageIX but no GAMS
        with patch('src.managers.gams_solver.GAMSSolver._detect_gams_path', return_value=None):
            # Scenario manager should work
            assert scenario_manager.is_available()

            # GAMS solver should not be available
            assert not gams_solver.is_available()

            # But scenario operations should still work
            mock_scenario = MagicMock()
            result = scenario_manager.solve_scenario(mock_scenario)
            assert not result['success']  # But doesn't crash

    def test_concurrent_operations(self):
        """Test concurrent operations safety"""
        import threading

        # Mock platform creation during manager initialization
        with patch('ixmp.Platform') as mock_platform_class, \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            scenario_manager = MessageIXScenarioManager()
            scenario_manager.ixmp_platform = mock_platform

        results = []

        def run_operation():
            # Simple operation that doesn't require actual MessageIX
            result = scenario_manager.is_available()
            results.append(result)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=run_operation)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All operations should complete
        assert len(results) == 10
        # Results should be consistent (all True or all False)
        assert all(r == results[0] for r in results)

    def test_resource_cleanup(self):
        """Test proper resource cleanup"""
        # Mock platform creation during manager initialization
        with patch('ixmp.Platform') as mock_platform_class, \
             patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            mock_platform = MagicMock()
            mock_platform_class.return_value = mock_platform

            scenario_manager = MessageIXScenarioManager()
            # Ensure the mock platform is set
            scenario_manager.ixmp_platform = mock_platform

            # Use the manager (triggers platform creation)
            available = scenario_manager.is_available()
            assert available  # Should be available with mock platform

            # Close resources
            scenario_manager.close()

            # Platform should be closed
            mock_platform.close.assert_called_once()
            assert scenario_manager.ixmp_platform is None
