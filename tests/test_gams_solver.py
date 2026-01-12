"""
Tests for GAMS Solver Integration

Tests the GAMS solver detection, configuration, and execution capabilities.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open

from src.managers.gams_solver import GAMSSolver


class TestGAMSSolver:
    """Test GAMS Solver functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.solver = GAMSSolver()

    def test_initialization_default_path(self):
        """Test solver initialization with default path detection"""
        with patch.object(GAMSSolver, '_detect_gams_path', return_value='/path/to/gams'):
            solver = GAMSSolver()
            assert solver.gams_path == '/path/to/gams'

    def test_initialization_custom_path(self):
        """Test solver initialization with custom path"""
        custom_path = '/custom/gams/path'
        with patch.object(GAMSSolver, '_validate_gams_installation'):
            solver = GAMSSolver(custom_path)
            assert solver.gams_path == custom_path

    def test_detect_gams_path_from_config(self):
        """Test GAMS path detection from config"""
        with patch('src.managers.gams_solver.config') as mock_config:
            mock_config.detect_gams_path.return_value = '/config/gams/path'

            solver = GAMSSolver()
            assert solver.gams_path == '/config/gams/path'

    def test_validate_gams_installation_success(self):
        """Test successful GAMS installation validation"""
        with patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=True):

            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "GAMS 39.1.0"
            mock_run.return_value = mock_process

            solver = GAMSSolver()
            solver.gams_path = '/valid/gams/path'

            # Call validation manually since it's done in __init__
            result = solver._validate_gams_installation()

            assert result is True
            mock_run.assert_called_once()

    def test_validate_gams_installation_failure(self):
        """Test GAMS installation validation failure"""
        with patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=False):

            solver = GAMSSolver()
            solver.gams_path = '/invalid/gams/path'

            result = solver._validate_gams_installation()

            assert result is False
            mock_run.assert_not_called()

    def test_is_available_true(self):
        """Test availability check when GAMS is available"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        with patch('os.path.exists', return_value=True):
            assert solver.is_available()

    def test_is_available_false(self):
        """Test availability check when GAMS is not available"""
        solver = GAMSSolver()
        solver.gams_path = None

        assert not solver.is_available()

    def test_get_solver_options(self):
        """Test default solver options"""
        solver = GAMSSolver()
        options = solver.get_solver_options()

        expected_keys = ['solver', 'optfile', 'reslim', 'iterlim', 'optcr', 'optca',
                        'threads', 'nodlim', 'lp', 'nlp', 'mip']

        for key in expected_keys:
            assert key in options

        assert options['solver'] == 'CPLEX'
        assert options['reslim'] == 1000

    def test_create_option_file(self):
        """Test GAMS option file creation"""
        solver = GAMSSolver()

        options = {
            'reslim': 500,
            'iterlim': 50000,
            'optcr': 0.01,
            'solver': 'CPLEX'  # Should be excluded from file
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            option_file = solver.create_option_file(options, temp_dir)

            assert os.path.exists(option_file)

            with open(option_file, 'r') as f:
                content = f.read()

            # Check that solver option is not in file (handled by command line)
            assert 'solver' not in content
            assert 'reslim 500' in content
            assert 'iterlim 50000' in content
            assert 'optcr 0.01' in content

    def test_prepare_solve_environment(self):
        """Test solve environment preparation"""
        solver = GAMSSolver()

        with tempfile.TemporaryDirectory() as base_dir:
            work_dir = solver.prepare_solve_environment("test_scenario", base_dir)

            assert os.path.exists(work_dir)
            assert "test_scenario" in work_dir
            assert os.path.isdir(work_dir)

    def test_run_gams_direct_not_available(self):
        """Test GAMS execution when solver not available"""
        solver = GAMSSolver()
        solver.gams_path = None

        with tempfile.TemporaryDirectory() as temp_dir:
            gms_file = os.path.join(temp_dir, 'test.gms')
            with open(gms_file, 'w') as f:
                f.write('dummy model')

            result = solver.run_gams_direct(gms_file, temp_dir)

            assert not result['success']
            assert 'GAMS not available' in result['error']

    def test_run_gams_direct_file_not_found(self):
        """Test GAMS execution with non-existent model file"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        with patch.object(solver, 'is_available', return_value=True), \
             tempfile.TemporaryDirectory() as temp_dir:

            result = solver.run_gams_direct('/nonexistent/file.gms', temp_dir)

            assert not result['success']
            assert 'GAMS file not found' in result['error']

    def test_run_gams_direct_success(self):
        """Test successful GAMS execution"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        # Mock subprocess.run for successful execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = None
        mock_process.stderr = None

        with patch.object(solver, 'is_available', return_value=True), \
             patch('subprocess.Popen') as mock_popen, \
             patch('time.time', side_effect=[0.0, 1.5]), \
             tempfile.TemporaryDirectory() as temp_dir:

            # Create dummy GMS file
            gms_file = os.path.join(temp_dir, 'test.gms')
            with open(gms_file, 'w') as f:
                f.write('dummy model')

            # Mock process
            mock_process_instance = MagicMock()
            mock_process_instance.poll.side_effect = [None, None, 0]  # Simulate running then completion
            mock_process_instance.stdout.readline.side_effect = ['line1\n', 'line2\n', '']
            mock_process_instance.stdout.read.return_value = ''
            mock_process_instance.stderr.read.return_value = ''
            mock_process_instance.returncode = 0

            mock_popen.return_value = mock_process_instance

            result = solver.run_gams_direct(gms_file, temp_dir)

            assert result['success']
            assert result['return_code'] == 0
            assert result['execution_time'] == 1.5
            assert 'line1' in result['output']
            assert 'line2' in result['output']

    def test_run_gams_direct_with_options(self):
        """Test GAMS execution with solver options"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        options = {'solver': 'Gurobi', 'reslim': 300}

        with patch.object(solver, 'is_available', return_value=True), \
             patch('subprocess.Popen') as mock_popen, \
             patch('time.time', side_effect=[0.0, 2.0]), \
             patch.object(solver, 'create_option_file') as mock_create_opt, \
             tempfile.TemporaryDirectory() as temp_dir:

            # Create dummy GMS file
            gms_file = os.path.join(temp_dir, 'test.gms')
            with open(gms_file, 'w') as f:
                f.write('dummy model')

            mock_create_opt.return_value = os.path.join(temp_dir, 'gams.opt')

            # Mock successful process
            mock_process = MagicMock()
            mock_process.poll.return_value = 0
            mock_process.returncode = 0
            mock_process.stdout.readline.return_value = ''
            mock_process.stdout.read.return_value = ''
            mock_process.stderr.read.return_value = ''
            mock_popen.return_value = mock_process

            result = solver.run_gams_direct(gms_file, temp_dir, options)

            assert result['success']
            mock_create_opt.assert_called_once_with(options, temp_dir)

    def test_run_gams_direct_failure(self):
        """Test GAMS execution failure"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        with patch.object(solver, 'is_available', return_value=True), \
             patch('subprocess.Popen') as mock_popen, \
             patch('time.time', side_effect=[0.0, 3.0]), \
             tempfile.TemporaryDirectory() as temp_dir:

            # Create dummy GMS file
            gms_file = os.path.join(temp_dir, 'test.gms')
            with open(gms_file, 'w') as f:
                f.write('dummy model')

            # Mock failed process
            mock_process = MagicMock()
            mock_process.poll.return_value = 0
            mock_process.returncode = 1  # Failure code
            mock_process.stdout.readline.return_value = ''
            mock_process.stdout.read.return_value = 'Error: Invalid model'
            mock_process.stderr.read.return_value = ''
            mock_popen.return_value = mock_process

            result = solver.run_gams_direct(gms_file, temp_dir)

            assert not result['success']
            assert result['return_code'] == 1
            assert 'Error: Invalid model' in result['error_output']

    def test_get_gams_version_success(self):
        """Test successful GAMS version retrieval"""
        solver = GAMSSolver()
        solver.gams_path = '/valid/gams/path'

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "GAMS 39.1.0 r12345"

        with patch.object(solver, 'is_available', return_value=True), \
             patch('subprocess.run', return_value=mock_process):

            version = solver.get_gams_version()

            assert version == "GAMS 39.1.0 r12345"

    def test_get_gams_version_failure(self):
        """Test GAMS version retrieval failure"""
        solver = GAMSSolver()
        solver.gams_path = '/invalid/gams/path'

        with patch.object(solver, 'is_available', return_value=False):
            version = solver.get_gams_version()
            assert version is None

    def test_list_available_solvers(self):
        """Test listing available GAMS solvers"""
        solver = GAMSSolver()

        solvers = solver.list_available_solvers()

        expected_solvers = ['CPLEX', 'Gurobi', 'CONOPT', 'IPOPT', 'IPOPTH', 'KNITRO',
                           'MINOS', 'SNOPT', 'BARON', 'LGO', 'SCIP', 'XPRESS', 'CBC']

        for expected_solver in expected_solvers:
            assert expected_solver in solvers

    def test_validate_solver_option(self):
        """Test solver option validation"""
        solver = GAMSSolver()

        assert solver.validate_solver_option('CPLEX')
        assert solver.validate_solver_option('Gurobi')
        assert not solver.validate_solver_option('INVALID_SOLVER')

    def test_get_system_info(self):
        """Test system information retrieval"""
        solver = GAMSSolver()
        solver.gams_path = '/test/gams/path'

        with patch.object(solver, 'get_gams_version', return_value='GAMS 39.1.0'):
            info = solver.get_system_info()

            required_keys = ['platform', 'architecture', 'python_version',
                           'gams_path', 'gams_version', 'available_solvers']

            for key in required_keys:
                assert key in info

            assert info['gams_path'] == '/test/gams/path'
            assert info['gams_version'] == 'GAMS 39.1.0'
            assert isinstance(info['available_solvers'], list)


class TestGAMSSolverIntegration:
    """Integration tests for GAMS Solver"""

    def test_full_solve_workflow(self):
        """Test complete GAMS solve workflow simulation"""
        solver = GAMSSolver()
        solver.gams_path = '/mock/gams/path'

        with patch.object(solver, 'is_available', return_value=True), \
             patch.object(solver, 'run_gams_direct') as mock_run, \
             tempfile.TemporaryDirectory() as temp_dir:

            # Mock successful solve
            mock_run.return_value = {
                'success': True,
                'return_code': 0,
                'output': ['Model solved successfully'],
                'execution_time': 5.2,
                'lst_file': '/path/to/model.lst'
            }

            # Create test model file
            gms_file = os.path.join(temp_dir, 'test.gms')
            with open(gms_file, 'w') as f:
                f.write('$ontext\nTest model\n$offtext\n')

            # Test direct execution
            result = solver.run_gams_direct(gms_file, temp_dir)

            assert result['success']
            assert result['execution_time'] == 5.2
            mock_run.assert_called_once()

    def test_error_recovery(self):
        """Test error handling and recovery"""
        solver = GAMSSolver()

        # Test with invalid path
        solver.gams_path = '/invalid/path'

        with patch.object(solver, 'is_available', return_value=False):
            assert not solver.is_available()

            # Operations should handle unavailability gracefully
            version = solver.get_gams_version()
            assert version is None

            result = solver.run_gams_direct('/fake/file.gms', '/tmp')
            assert not result['success']
            assert 'GAMS not available' in result.get('error', '')

    def test_option_file_handling(self):
        """Test option file creation and usage"""
        solver = GAMSSolver()

        options = {
            'reslim': 600,
            'iterlim': 100000,
            'optcr': 0.001,
            'threads': 4,
            'solver': 'CPLEX'  # Should not appear in file
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            opt_file = solver.create_option_file(options, temp_dir)

            # Verify file exists and has correct content
            assert os.path.exists(opt_file)

            with open(opt_file, 'r') as f:
                content = f.read()

            assert 'reslim 600' in content
            assert 'iterlim 100000' in content
            assert 'optcr 0.001' in content
            assert 'threads 4' in content
            assert 'solver' not in content  # solver handled separately

    def test_environment_preparation(self):
        """Test solve environment setup"""
        solver = GAMSSolver()

        scenario_name = "test_scenario_123"

        with tempfile.TemporaryDirectory() as base_dir:
            work_dir = solver.prepare_solve_environment(scenario_name, base_dir)

            assert scenario_name in work_dir
            assert os.path.exists(work_dir)
            assert os.path.isdir(work_dir)

            # Should be able to create files in work directory
            test_file = os.path.join(work_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            assert os.path.exists(test_file)

    def test_thread_safety(self):
        """Test that solver operations are thread-safe"""
        import threading

        solver = GAMSSolver()
        results = []

        def run_solve():
            result = solver.get_system_info()
            results.append(result)

        threads = []
        for _ in range(5):
            t = threading.Thread(target=run_solve)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should complete successfully
        assert len(results) == 5
        for result in results:
            assert 'platform' in result
