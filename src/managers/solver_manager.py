"""
Solver Manager — environment detection and command construction for
MESSAGEix solver execution.

Subprocess execution and real-time output streaming are intentionally
*not* handled here; that responsibility belongs to SolverWorker (QThread)
so that Qt signal-slot connections can be made in the UI layer before the
worker thread starts.

Typical call sequence in main_window.py::

    worker = self.solver_manager.create_worker(
        self.solver_manager.build_solver_command(input_file, solver, model, scen)
    )
    worker.output_line.connect(self._append_to_console)
    worker.status_changed.connect(self._update_status_from_solver)
    worker.finished.connect(self._on_solver_finished)
    worker.start()
"""

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .logging_manager import logging_manager
from .solver_worker import SolverWorker


class SolverManager:
    """
    Handles MESSAGEix environment detection, solver discovery, and command
    construction.

    Does not own any subprocess state.  SolverWorker instances are created
    here and owned by the caller (main_window.py).
    """

    # Default LP-solver options forwarded to run_messageix.py for each
    # solver type.  These are the standard MESSAGEix/GAMS CPLEX defaults.
    SOLVER_OPTIONS: Dict[str, Dict[str, Any]] = {
        "glpk":   {},
        "cplex":  {"advind": 0, "epopt": 1e-6, "lpmethod": 4, "threads": 4},
        "gurobi": {"method": 2},
    }

    # ------------------------------------------------------------------
    # Environment detection
    # ------------------------------------------------------------------

    def detect_messageix(self) -> bool:
        """
        Return True if both ixmp and message_ix are importable.

        The check is intentionally run in a *subprocess* so that a hard
        crash inside ixmp (e.g. JPype/JVM segfault when Java is missing or
        a DLL cannot be loaded on Windows) does not kill the main process.
        """
        print("DEBUG detect_messageix: probing via subprocess...", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import ixmp; import message_ix; print('OK')"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            rc = result.returncode
            print(f"DEBUG detect_messageix: rc={rc} stdout={stdout!r} stderr={stderr[:200]!r}",
                  flush=True)
            return rc == 0 and stdout == "OK"
        except Exception as exc:
            print(f"DEBUG detect_messageix: probe subprocess error — {exc!r}", flush=True)
            return False

    def detect_messageix_environment(self) -> bool:
        """Alias of detect_messageix() kept for backward compatibility."""
        return self.detect_messageix()

    def detect_gams(self) -> bool:
        """
        Return True if a GAMS executable can be found.

        Checks (in order):
        1. ``gams`` on the system PATH (``shutil.which``).
        2. ``GAMSDIR`` environment variable.
        3. Common Windows installation paths (C:\\GAMS, C:\\bin\\GAMS).
        """
        return self._locate_gams_dir() is not None

    def _locate_gams_dir(self) -> Optional[str]:
        """Return the GAMS system directory (containing gams.exe), or None."""
        # 1. On PATH
        on_path = shutil.which("gams")
        print(f"DEBUG _locate_gams_dir: shutil.which('gams')={on_path!r}", flush=True)
        if on_path:
            return os.path.dirname(os.path.abspath(on_path))

        # 2. GAMSDIR env var
        gams_dir = os.environ.get("GAMSDIR", "")
        print(f"DEBUG _locate_gams_dir: GAMSDIR env={gams_dir!r}", flush=True)
        if gams_dir:
            for exe_name in ("gams.exe", "gams"):
                if os.path.isfile(os.path.join(gams_dir, exe_name)):
                    return gams_dir

        # 3. Common Windows installation paths
        for base in (r"C:\GAMS", r"C:\bin\GAMS"):
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base), reverse=True):
                    candidate = os.path.join(base, entry)
                    if os.path.isfile(os.path.join(candidate, "gams.exe")):
                        print(f"DEBUG _locate_gams_dir: found at {candidate!r}", flush=True)
                        return candidate

        print("DEBUG _locate_gams_dir: GAMS not found", flush=True)
        return None

    def _locate_gams(self) -> Optional[str]:
        """Return the full path to the GAMS executable, or None."""
        gams_dir = self._locate_gams_dir()
        if gams_dir:
            for exe in ("gams.exe", "gams"):
                exe_path = os.path.join(gams_dir, exe)
                if os.path.isfile(exe_path):
                    return exe_path
        return None

    def _query_gams_solvers(self) -> str:
        """
        Run ``gams ?`` and return the combined stdout+stderr output.

        Returns an empty string if GAMS is not found or the subprocess fails.
        The result is cached on this instance after the first call.
        """
        if hasattr(self, "_gams_solver_output"):
            return self._gams_solver_output  # type: ignore[attr-defined]

        gams_exe = self._locate_gams()
        if not gams_exe:
            self._gams_solver_output = ""
            return ""

        try:
            result = subprocess.run(
                [gams_exe, "?"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self._gams_solver_output = result.stdout + result.stderr
        except Exception as exc:
            print(f"DEBUG _query_gams_solvers: subprocess error {exc!r}", flush=True)
            self._gams_solver_output = ""

        print(f"DEBUG _query_gams_solvers: output (first 300 chars): "
              f"{self._gams_solver_output[:300]!r}", flush=True)
        return self._gams_solver_output

    def _glpk_available_via_gams(self) -> bool:
        """
        Return True if the GAMS installation includes the GLPK solver.

        GLPK is bundled with every GAMS distribution, so if GAMS is present
        we can assume GLPK is available.  If the GAMS interrogation itself
        fails for any reason (e.g. licence issues at startup) we fall back to
        True so the user can at least attempt the solve.
        """
        gams_exe = self._locate_gams()
        print(f"DEBUG _glpk_available_via_gams: gams_exe={gams_exe!r}", flush=True)
        if not gams_exe:
            return False

        combined = self._query_gams_solvers()
        if not combined:
            # Cannot query GAMS — assume GLPK ships with it (safe default)
            print("DEBUG _glpk_available_via_gams: no output — defaulting to True", flush=True)
            return True

        found = "GLPK" in combined or "glpk" in combined.lower()
        print(f"DEBUG _glpk_available_via_gams: GLPK found={found}", flush=True)
        return found

    def _cplex_available_via_gams(self) -> bool:
        """
        Return True if the GAMS installation includes a licensed CPLEX solver.

        Detection checks (in order):
        1. CPLEX solver DLL present in the GAMS system directory
           (``gcplex*.dll`` / ``cplex*.dll`` on Windows) — most reliable.
        2. ``gams ?`` output contains "CPLEX" — text-based fallback.
        3. Python ``cplex`` package is importable — last-resort fallback.
        """
        import glob as _glob

        gams_dir = self._locate_gams_dir()
        print(f"DEBUG _cplex_available_via_gams: gams_dir={gams_dir!r}", flush=True)

        if gams_dir:
            # Check for the GAMS/CPLEX link DLL (e.g. gcplex130.dll, cplex*.dll)
            patterns = [
                os.path.join(gams_dir, "gcplex*.dll"),
                os.path.join(gams_dir, "cplex*.dll"),
                os.path.join(gams_dir, "gcplex*"),   # non-Windows / no extension
            ]
            dll_hits = [p for pat in patterns for p in _glob.glob(pat)]
            print(f"DEBUG _cplex_available_via_gams: DLL search hits={dll_hits}", flush=True)
            if dll_hits:
                return True

            # Fall back to gams ? text output
            combined = self._query_gams_solvers()
            if combined:
                found = "CPLEX" in combined or "cplex" in combined.lower()
                print(f"DEBUG _cplex_available_via_gams: gams ? text check found={found}",
                      flush=True)
                if found:
                    return True

        # Last resort: Python cplex package
        try:
            import cplex  # type: ignore # noqa: F401
            print("DEBUG _cplex_available_via_gams: Python cplex package found", flush=True)
            return True
        except ImportError:
            pass

        print("DEBUG _cplex_available_via_gams: CPLEX not found", flush=True)
        return False

    # ------------------------------------------------------------------
    # Solver discovery
    # ------------------------------------------------------------------

    def get_available_solvers(self) -> List[str]:
        """
        Return the list of LP solvers available through the installed GAMS.

        Returns an empty list when GAMS is not found on the system.

        Detection logic:
        - **GLPK**: bundled with *all* GAMS distributions unconditionally.
          ``gams ?`` does not reliably list solvers across GAMS versions, so
          we simply include GLPK whenever GAMS itself is found.
        - **CPLEX**: included when the ``cplex`` Python package is importable
          (used as a proxy for a valid CPLEX licence).
        - **Gurobi**: included when the ``gurobipy`` Python package is
          importable.
        """
        if not self.detect_gams():
            print("DEBUG get_available_solvers: GAMS not found — returning []", flush=True)
            return []

        # GLPK ships with every GAMS installation — no further probe needed
        solvers: List[str] = ["glpk"]
        print(f"DEBUG get_available_solvers: GAMS found — GLPK included by default", flush=True)

        if self._cplex_available_via_gams():
            solvers.append("cplex")
            print("DEBUG get_available_solvers: CPLEX available", flush=True)

        try:
            import gurobipy  # type: ignore # noqa: F401
            solvers.append("gurobi")
            print("DEBUG get_available_solvers: gurobipy package found", flush=True)
        except ImportError:
            pass

        print(f"DEBUG get_available_solvers: returning {solvers}", flush=True)
        return solvers

    # ------------------------------------------------------------------
    # Command construction
    # ------------------------------------------------------------------

    def build_solver_command(
        self,
        input_file: str,
        solver: str,
        model_name: str,
        scenario_name: str,
        output_dir: Optional[str] = None,
    ) -> List[str]:
        """
        Build the command list that will be passed to SolverWorker.

        The command invokes run_messageix.py as a subprocess using the same
        Python interpreter that is running the application.

        Args:
            input_file:     Path to the MESSAGEix input Excel file.
            solver:         LP solver name ('glpk', 'cplex', 'gurobi').
            model_name:     MESSAGEix model name.
            scenario_name:  MESSAGEix scenario name.
            output_dir:     Directory in which to write the results Excel file.
                            Defaults to the directory containing input_file.

        Returns:
            List of strings suitable for subprocess.Popen.
        """
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(input_file))

        script_path = os.path.join(os.path.dirname(__file__), "run_messageix.py")

        cmd = [
            sys.executable, script_path,
            "--input",    input_file,
            "--solver",   solver,
            "--model",    model_name,
            "--scenario", scenario_name,
            "--output-dir", output_dir,
        ]

        logging_manager.log_solver_execution(" ".join(cmd), "prepared")
        return cmd

    # ------------------------------------------------------------------
    # Worker lifecycle helpers
    # ------------------------------------------------------------------

    def create_worker(self, cmd: List[str]) -> SolverWorker:
        """
        Create a SolverWorker for the given command.

        The caller must connect the worker's signals before calling
        ``worker.start()``.

        Args:
            cmd: Command list as returned by build_solver_command().

        Returns:
            A SolverWorker instance that has not yet been started.
        """
        return SolverWorker(cmd)
