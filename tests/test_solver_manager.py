"""
Tests for SolverManager and SolverWorker.

SolverManager is a plain Python class (no Qt dependency), so all detection
and command-building tests run without a QApplication.

SolverWorker tests require a running QApplication; pytest-qt provides the
``qtbot`` fixture which arranges that automatically.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from managers.solver_manager import SolverManager


# ===========================================================================
# SolverManager — MESSAGEix environment detection
# ===========================================================================

class TestDetectMessageix:
    """
    detect_messageix() runs the probe in a subprocess; we mock subprocess.run
    to control the simulated outcome without spawning a real process.
    """

    def _make_proc(self, returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_available(self):
        manager = SolverManager()
        with patch("subprocess.run", return_value=self._make_proc(0, stdout="OK")):
            assert manager.detect_messageix() is True

    def test_unavailable_nonzero_exit(self):
        manager = SolverManager()
        with patch("subprocess.run",
                   return_value=self._make_proc(1, stderr="No module named 'ixmp'")):
            assert manager.detect_messageix() is False

    def test_unavailable_crash(self):
        """Subprocess crash (exception from subprocess.run) → False, not a crash."""
        manager = SolverManager()
        with patch("subprocess.run", side_effect=Exception("process crashed")):
            assert manager.detect_messageix() is False

    def test_backward_compat_alias(self):
        """detect_messageix_environment() must delegate to detect_messageix()."""
        manager = SolverManager()
        with patch.object(manager, "detect_messageix", return_value=True) as m:
            result = manager.detect_messageix_environment()
            assert result is True
            m.assert_called_once()


# ===========================================================================
# SolverManager — GAMS detection
# ===========================================================================

class TestDetectGams:
    def test_gams_on_path(self):
        manager = SolverManager()
        with patch("shutil.which", return_value="/usr/local/bin/gams"):
            assert manager.detect_gams() is True

    def test_gams_not_on_path_no_env(self):
        manager = SolverManager()
        with patch("shutil.which", return_value=None), \
             patch.dict("os.environ", {}, clear=True), \
             patch("os.path.isdir", return_value=False):  # block common-path fallback
            assert manager.detect_gams() is False

    def test_gams_via_gamsdir_env(self, tmp_path):
        gams_exe = tmp_path / "gams.exe"
        gams_exe.touch()
        manager = SolverManager()
        with patch("shutil.which", return_value=None), \
             patch.dict("os.environ", {"GAMSDIR": str(tmp_path)}):
            assert manager.detect_gams() is True

    def test_gamsdir_present_but_exe_absent(self, tmp_path):
        manager = SolverManager()
        with patch("shutil.which", return_value=None), \
             patch.dict("os.environ", {"GAMSDIR": str(tmp_path)}), \
             patch("os.path.isdir", return_value=False):  # block common-path fallback
            assert manager.detect_gams() is False


# ===========================================================================
# SolverManager — solver discovery
# ===========================================================================

class TestGetAvailableSolvers:
    def test_no_gams_returns_empty(self):
        manager = SolverManager()
        with patch.object(manager, "detect_gams", return_value=False):
            assert manager.get_available_solvers() == []

    def test_gams_present_always_includes_glpk(self):
        """GLPK is bundled with every GAMS installation — always included."""
        manager = SolverManager()
        with patch.object(manager, "detect_gams", return_value=True), \
             patch.dict("sys.modules", {"cplex": None, "gurobipy": None}):
            solvers = manager.get_available_solvers()
            assert "glpk" in solvers
            assert "cplex" not in solvers
            assert "gurobi" not in solvers

    def test_cplex_detected_when_package_importable(self):
        manager = SolverManager()
        with patch.object(manager, "detect_gams", return_value=True), \
             patch.object(manager, "_glpk_available_via_gams", return_value=True), \
             patch.dict("sys.modules", {"cplex": MagicMock(), "gurobipy": None}):
            assert "cplex" in manager.get_available_solvers()

    def test_gurobi_detected_when_package_importable(self):
        manager = SolverManager()
        with patch.object(manager, "detect_gams", return_value=True), \
             patch.object(manager, "_glpk_available_via_gams", return_value=True), \
             patch.dict("sys.modules", {"cplex": None, "gurobipy": MagicMock()}):
            assert "gurobi" in manager.get_available_solvers()


# ===========================================================================
# SolverManager — command building
# ===========================================================================

class TestBuildSolverCommand:
    def test_returns_list_with_run_messageix(self, tmp_path):
        manager = SolverManager()
        input_file = str(tmp_path / "model.xlsx")
        cmd = manager.build_solver_command(input_file, "glpk", "TestModel", "base")

        assert isinstance(cmd, list)
        assert cmd[0] == sys.executable
        assert "run_messageix.py" in cmd[1]

    def test_all_required_flags_present(self, tmp_path):
        manager = SolverManager()
        input_file = str(tmp_path / "model.xlsx")
        cmd = manager.build_solver_command(input_file, "cplex", "MyModel", "scenario1")

        assert "--input" in cmd and input_file in cmd
        assert "--solver" in cmd and "cplex" in cmd
        assert "--model" in cmd and "MyModel" in cmd
        assert "--scenario" in cmd and "scenario1" in cmd
        assert "--output-dir" in cmd

    def test_default_output_dir_is_input_dir(self, tmp_path):
        manager = SolverManager()
        input_file = str(tmp_path / "model.xlsx")
        cmd = manager.build_solver_command(input_file, "glpk", "M", "s")

        idx = cmd.index("--output-dir")
        assert cmd[idx + 1] == str(tmp_path)

    def test_explicit_output_dir(self, tmp_path):
        manager = SolverManager()
        input_file = str(tmp_path / "model.xlsx")
        out_dir = str(tmp_path / "out")
        cmd = manager.build_solver_command(input_file, "glpk", "M", "s",
                                           output_dir=out_dir)

        idx = cmd.index("--output-dir")
        assert cmd[idx + 1] == out_dir


# ===========================================================================
# SolverManager — create_worker
# ===========================================================================

class TestCreateWorker:
    def test_returns_solver_worker_instance(self, qtbot):
        """create_worker() must return a SolverWorker that is not yet running."""
        from managers.solver_worker import SolverWorker
        manager = SolverManager()
        worker = manager.create_worker(["echo", "hello"])
        assert isinstance(worker, SolverWorker)
        assert not worker.isRunning()


# ===========================================================================
# SolverWorker — subprocess integration (requires QApplication via qtbot)
# ===========================================================================

class TestSolverWorker:
    def test_emits_output_lines_and_finished(self, qtbot):
        """Worker streams stdout and emits finished(0, '') for a trivial cmd."""
        from managers.solver_worker import SolverWorker

        cmd = [sys.executable, "-c",
               "print('hello'); print('world')"]
        worker = SolverWorker(cmd)

        lines = []
        exit_codes = []
        result_files = []

        worker.output_line.connect(lines.append)
        worker.finished.connect(lambda code, path: (
            exit_codes.append(code), result_files.append(path)
        ))

        with qtbot.waitSignal(worker.finished, timeout=10_000):
            worker.start()

        assert "hello" in lines
        assert "world" in lines
        assert exit_codes == [0]
        assert result_files == [""]

    def test_propagates_nonzero_exit_code(self, qtbot):
        """A failing subprocess must emit finished with exit_code != 0."""
        from managers.solver_worker import SolverWorker

        cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
        worker = SolverWorker(cmd)

        exit_codes = []
        worker.finished.connect(lambda code, _: exit_codes.append(code))

        with qtbot.waitSignal(worker.finished, timeout=10_000):
            worker.start()

        assert exit_codes == [42]

    def test_captures_result_file_prefix_not_forwarded_to_console(self, qtbot):
        """[RESULT_FILE] lines must be captured and not emitted as output_line."""
        from managers.solver_worker import SolverWorker

        result_path = "/tmp/some_results.xlsx"
        script = (
            f"print('before'); "
            f"print('[RESULT_FILE] {result_path}'); "
            f"print('after')"
        )
        cmd = [sys.executable, "-c", script]
        worker = SolverWorker(cmd)

        lines = []
        result_files = []
        worker.output_line.connect(lines.append)
        worker.finished.connect(lambda _, path: result_files.append(path))

        with qtbot.waitSignal(worker.finished, timeout=10_000):
            worker.start()

        assert result_files == [result_path]
        assert not any("[RESULT_FILE]" in ln for ln in lines)
        assert "before" in lines
        assert "after" in lines

    def test_stop_terminates_running_process(self, qtbot):
        """stop() must terminate a long-running subprocess without blocking."""
        from managers.solver_worker import SolverWorker

        # Subprocess prints 'started' so we know it is running, then sleeps.
        cmd = [sys.executable, "-c",
               "import time, sys; "
               "print('started', flush=True); "
               "time.sleep(60)"]
        worker = SolverWorker(cmd)

        exit_codes = []
        worker.finished.connect(lambda code, _: exit_codes.append(code))

        # Wait for first output line to guarantee subprocess is alive
        with qtbot.waitSignal(worker.output_line, timeout=5_000):
            worker.start()

        # stop() is non-blocking; finished arrives once the thread exits
        with qtbot.waitSignal(worker.finished, timeout=10_000):
            worker.stop()

        # Terminated process exits with non-zero code
        assert exit_codes and exit_codes[0] != 0
