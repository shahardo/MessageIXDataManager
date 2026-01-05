"""
Tests for Solver Manager
"""

import pytest
import os
import sys
import tempfile
import threading
import time
from unittest.mock import patch, MagicMock, call

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from managers.solver_manager import SolverManager


class TestSolverManager:
    """Test cases for SolverManager"""

    def test_initialization(self):
        """Test SolverManager initialization"""
        manager = SolverManager()
        assert manager.current_process is None
        assert not manager.is_running
        assert manager.execution_thread is None
        assert manager.output_callback is None
        assert manager.status_callback is None

    def test_set_callbacks(self):
        """Test setting output and status callbacks"""
        manager = SolverManager()

        def output_cb(msg):
            pass

        def status_cb(status):
            pass

        manager.set_output_callback(output_cb)
        manager.set_status_callback(status_cb)

        assert manager.output_callback == output_cb
        assert manager.status_callback == status_cb

    def test_detect_messageix_environment_available(self):
        """Test detecting message_ix environment when available"""
        manager = SolverManager()

        with patch.dict('sys.modules', {'ixmp': MagicMock(), 'message_ix': MagicMock()}):
            result = manager.detect_messageix_environment()
            assert result is True

    def test_detect_messageix_environment_unavailable(self):
        """Test detecting message_ix environment when unavailable"""
        manager = SolverManager()

        # Remove message_ix modules if they exist
        modules_to_remove = ['ixmp', 'message_ix']
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]

        # Mock import to raise ImportError
        with patch.dict('sys.modules', {}, clear=True):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'ixmp'")):
                result = manager.detect_messageix_environment()
                assert result is False

    def test_get_available_solvers(self):
        """Test getting available solvers"""
        manager = SolverManager()
        solvers = manager.get_available_solvers()

        assert isinstance(solvers, list)
        assert len(solvers) > 0  # Should always return at least glpk

        # Should include glpk as fallback
        assert 'glpk' in solvers

    def test_get_available_solvers_with_cplex(self):
        """Test detecting CPLEX solver"""
        manager = SolverManager()

        with patch.dict('sys.modules', {'cplex': MagicMock()}):
            solvers = manager.get_available_solvers()
            assert 'cplex' in solvers

    def test_get_available_solvers_with_gurobi(self):
        """Test detecting Gurobi solver"""
        manager = SolverManager()

        with patch.dict('sys.modules', {'gurobipy': MagicMock()}):
            solvers = manager.get_available_solvers()
            assert 'gurobi' in solvers

    def test_build_solver_command(self):
        """Test building solver command"""
        manager = SolverManager()
        cmd = manager._build_solver_command('/path/to/input.xlsx', 'glpk')

        assert isinstance(cmd, list)
        assert len(cmd) >= 3
        assert 'mock_solver.py' in cmd[1]
        assert cmd[2] == '/path/to/input.xlsx'
        assert cmd[3] == 'glpk'

    def test_build_solver_command_with_config(self):
        """Test building solver command with configuration"""
        manager = SolverManager()
        config = {'timeout': 300, 'threads': 4}
        cmd = manager._build_solver_command('/path/to/input.xlsx', 'glpk', config)

        assert isinstance(cmd, list)
        # Config is not used in current implementation, but command should still be built
        assert 'mock_solver.py' in cmd[1]

    def test_run_solver_file_not_found(self):
        """Test running solver with nonexistent file"""
        manager = SolverManager()

        result = manager.run_solver('/nonexistent/file.xlsx', 'glpk')
        assert result is False

    @patch('subprocess.Popen')
    def test_run_solver_success(self, mock_popen):
        """Test successful solver execution"""
        manager = SolverManager()

        # Create a temp input file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        # Mock the process
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Success
        mock_process.stdout.readline.return_value = ''
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = manager.run_solver(tmp_path, 'glpk')
        assert result is True
        assert manager.is_running is True

        # Verify Popen was called
        mock_popen.assert_called_once()

        os.unlink(tmp_path)

    @patch('subprocess.Popen')
    def test_run_solver_already_running(self, mock_popen):
        """Test running solver when already running"""
        manager = SolverManager()
        manager.is_running = True

        result = manager.run_solver('/path/to/file.xlsx', 'glpk')
        assert result is False

        # Popen should not have been called
        mock_popen.assert_not_called()

    @patch('subprocess.Popen')
    def test_run_solver_failure(self, mock_popen):
        """Test solver execution failure"""
        manager = SolverManager()

        # Create a temp input file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        # Mock the process
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Failure
        mock_process.stdout.readline.return_value = ''
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = manager.run_solver(tmp_path, 'glpk')
        assert result is True  # Started successfully, even if solver failed

        os.unlink(tmp_path)

    def test_stop_solver_not_running(self):
        """Test stopping solver when not running"""
        manager = SolverManager()

        result = manager.stop_solver()
        assert result is False

    def test_stop_solver_running(self):
        """Test stopping a running solver"""
        manager = SolverManager()
        manager.is_running = True
        manager.current_process = MagicMock()

        result = manager.stop_solver()
        assert result is True
        assert not manager.is_running

        # Verify terminate was called
        manager.current_process.terminate.assert_called_once()

    def test_stop_solver_force_kill(self):
        """Test force killing solver if terminate doesn't work"""
        manager = SolverManager()
        manager.is_running = True
        mock_process = MagicMock()
        mock_process.terminate.side_effect = Exception("Terminate failed")
        manager.current_process = mock_process

        result = manager.stop_solver()
        assert result is False  # Should return False on exception

    def test_is_solver_running(self):
        """Test checking if solver is running"""
        manager = SolverManager()

        assert not manager.is_solver_running()

        manager.is_running = True
        assert manager.is_solver_running()

    def test_log_output_with_callback(self):
        """Test logging output with callback"""
        manager = SolverManager()

        output_calls = []
        def output_callback(msg):
            output_calls.append(msg)

        manager.set_output_callback(output_callback)
        manager._log_output("Test message")

        assert len(output_calls) == 1
        assert output_calls[0] == "Test message"

    def test_log_output_without_callback(self):
        """Test logging output without callback"""
        manager = SolverManager()

        # Should not raise exception
        manager._log_output("Test message")

    def test_update_status_with_callback(self):
        """Test updating status with callback"""
        manager = SolverManager()

        status_calls = []
        def status_callback(status):
            status_calls.append(status)

        manager.set_status_callback(status_callback)
        manager._update_status("Running")

        assert len(status_calls) == 1
        assert status_calls[0] == "Running"

    def test_update_status_without_callback(self):
        """Test updating status without callback"""
        manager = SolverManager()

        # Should not raise exception
        manager._update_status("Running")

    @patch('threading.Thread')
    @patch('subprocess.Popen')
    def test_execution_thread_creation(self, mock_popen, mock_thread):
        """Test that execution thread is created properly"""
        manager = SolverManager()

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        # Mock process and thread
        mock_process = MagicMock()
        mock_process.poll.return_value = 0
        mock_popen.return_value = mock_process

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        manager.run_solver(tmp_path, 'glpk')

        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

        os.unlink(tmp_path)

    def test_solver_execution_with_output_reading(self):
        """Test that solver output is read correctly"""
        manager = SolverManager()

        output_messages = []
        def output_callback(msg):
            output_messages.append(msg.strip())

        manager.set_output_callback(output_callback)

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_path = tmp.name

        with patch('subprocess.Popen') as mock_popen, \
             patch('time.sleep'):

            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, 0]  # Running, running, finished
            mock_process.stdout.readline.side_effect = ['Line 1\n', 'Line 2\n', '']
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            manager.run_solver(tmp_path, 'glpk')

            # Give some time for the thread to execute
            time.sleep(0.1)

            # Check that output was captured
            assert 'Line 1' in output_messages
            assert 'Line 2' in output_messages

        os.unlink(tmp_path)
