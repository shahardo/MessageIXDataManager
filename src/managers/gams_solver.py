"""
GAMS Solver Integration

Provides specialized functionality for GAMS solver integration with MessageIX,
including path detection, solver configuration, and execution monitoring.
"""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from ..config import config, GAMS_PATH
from .logging_manager import logging_manager


class GAMSSolver:
    """
    GAMS Solver integration for MessageIX.

    Handles GAMS executable detection, solver configuration, and provides
    an interface for running GAMS through MessageIX scenarios.
    """

    def __init__(self, gams_path: Optional[str] = None):
        """
        Initialize GAMS Solver.

        Args:
            gams_path: Optional path to GAMS executable
        """
        self.gams_path = gams_path or self._detect_gams_path()
        self._validate_gams_installation()

    def _detect_gams_path(self) -> Optional[str]:
        """
        Auto-detect GAMS installation path.

        Returns:
            Path to GAMS executable if found, None otherwise
        """
        # Use config detection
        return config.detect_gams_path()

    def _validate_gams_installation(self) -> bool:
        """
        Validate GAMS installation.

        Returns:
            True if GAMS is properly installed, False otherwise
        """
        if not self.gams_path or not os.path.exists(self.gams_path):
            logging_manager.log_warning("GAMS executable not found")
            return False

        # Try to run GAMS with version check
        try:
            result = subprocess.run(
                [self.gams_path, "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_info = result.stdout.strip()
                logging_manager.log_info(f"GAMS version detected: {version_info}")
                return True
            else:
                logging_manager.log_warning(f"GAMS version check failed: {result.stderr}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logging_manager.log_error(f"GAMS validation failed: {e}")
            return False

    def is_available(self) -> bool:
        """
        Check if GAMS is available and properly configured.

        Returns:
            True if GAMS is available, False otherwise
        """
        return self.gams_path is not None and os.path.exists(self.gams_path)

    def get_solver_options(self) -> Dict[str, Any]:
        """
        Get available GAMS solver options.

        Returns:
            Dictionary of solver options with defaults
        """
        return {
            'solver': 'CPLEX',  # Default solver
            'optfile': 1,       # Use option file
            'reslim': 1000,    # Time limit in seconds
            'iterlim': 100000, # Iteration limit
            'optcr': 0.0,      # Optimality criterion
            'optca': 0.0,      # Absolute optimality criterion
            'threads': 0,      # Number of threads (0 = auto)
            'nodlim': 1000000, # Node limit for MIP
            'lp': 'CPLEX',     # LP solver
            'nlp': 'CONOPT',   # NLP solver
            'mip': 'CPLEX',    # MIP solver
        }

    def create_option_file(self, options: Dict[str, Any], work_dir: str) -> str:
        """
        Create GAMS option file.

        Args:
            options: Solver options dictionary
            work_dir: Working directory for the option file

        Returns:
            Path to created option file
        """
        option_file_path = os.path.join(work_dir, "gams.opt")

        with open(option_file_path, 'w') as f:
            for key, value in options.items():
                if key != 'solver':  # solver is handled separately
                    f.write(f"{key} {value}\n")

        logging_manager.log_debug(f"Created GAMS option file: {option_file_path}")
        return option_file_path

    def prepare_solve_environment(
        self,
        scenario_name: str,
        work_dir: Optional[str] = None
    ) -> str:
        """
        Prepare environment for GAMS solve.

        Args:
            scenario_name: Name of the scenario
            work_dir: Optional working directory

        Returns:
            Path to working directory
        """
        if work_dir is None:
            work_dir = os.path.join(
                config.MESSAGEIX_DB_PATH or str(Path.home() / '.messageix'),
                'gams_work',
                f"{scenario_name}_{int(time.time())}"
            )

        os.makedirs(work_dir, exist_ok=True)
        logging_manager.log_debug(f"Prepared GAMS work directory: {work_dir}")

        return work_dir

    def run_gams_direct(
        self,
        gms_file: str,
        work_dir: str,
        options: Optional[Dict[str, Any]] = None,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Run GAMS directly (for testing or standalone execution).

        Args:
            gms_file: Path to GAMS model file (.gms)
            work_dir: Working directory
            options: Solver options
            output_callback: Callback for real-time output

        Returns:
            Dictionary with execution results
        """
        result = {
            'success': False,
            'return_code': None,
            'output': [],
            'error_output': [],
            'execution_time': None,
            'lst_file': None
        }

        if not self.is_available():
            result['error'] = 'GAMS not available'
            return result

        if not os.path.exists(gms_file):
            result['error'] = f'GAMS file not found: {gms_file}'
            return result

        # Prepare command
        cmd = [self.gams_path, gms_file, 'curdir', work_dir]

        # Add solver option if specified
        if options and 'solver' in options:
            cmd.extend(['solver', options['solver']])

        # Create option file if options provided
        if options:
            option_file = self.create_option_file(options, work_dir)
            cmd.extend(['optfile', '1'])

        logging_manager.log_info(f"Running GAMS command: {' '.join(cmd)}")

        start_time = time.time()

        try:
            # Run GAMS
            process = subprocess.Popen(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output in real-time
            while process.poll() is None:
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        result['output'].append(line.strip())
                        if output_callback:
                            output_callback(line.strip())

                time.sleep(0.1)

            # Read any remaining output
            if process.stdout:
                remaining = process.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        result['output'].append(line.strip())
                        if output_callback:
                            output_callback(line.strip())

            if process.stderr:
                error_output = process.stderr.read()
                if error_output:
                    result['error_output'].extend(error_output.splitlines())

            result['return_code'] = process.returncode
            result['execution_time'] = time.time() - start_time
            result['success'] = process.returncode == 0

            # Check for LST file
            lst_file = os.path.join(work_dir, os.path.splitext(os.path.basename(gms_file))[0] + '.lst')
            if os.path.exists(lst_file):
                result['lst_file'] = lst_file

            if result['success']:
                logging_manager.log_info(f"GAMS execution completed successfully in {result['execution_time']:.2f}s")
            else:
                logging_manager.log_error(f"GAMS execution failed with return code {result['return_code']}")

        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
            logging_manager.log_error(f"GAMS execution error: {e}")

        return result

    def get_gams_version(self) -> Optional[str]:
        """
        Get GAMS version information.

        Returns:
            Version string if available, None otherwise
        """
        if not self.is_available():
            return None

        try:
            result = subprocess.run(
                [self.gams_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Unknown (return code: {result.returncode})"

        except Exception as e:
            logging_manager.log_error(f"Failed to get GAMS version: {e}")
            return None

    def list_available_solvers(self) -> List[str]:
        """
        List solvers available in GAMS installation.

        Returns:
            List of available solver names
        """
        if not self.is_available():
            return []

        # Common GAMS solvers (this could be expanded with actual detection)
        common_solvers = [
            'CPLEX', 'Gurobi', 'CONOPT', 'IPOPT', 'IPOPTH', 'KNITRO',
            'MINOS', 'SNOPT', 'BARON', 'LGO', 'SCIP', 'XPRESS', 'CBC'
        ]

        # For now, return common solvers - could be enhanced to actually check
        # GAMS installation for available solvers
        return common_solvers

    def validate_solver_option(self, solver_name: str) -> bool:
        """
        Validate if a solver is available in GAMS.

        Args:
            solver_name: Name of the solver to check

        Returns:
            True if solver is available, False otherwise
        """
        available_solvers = self.list_available_solvers()
        return solver_name.upper() in [s.upper() for s in available_solvers]

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information for GAMS compatibility.

        Returns:
            Dictionary with system information
        """
        return {
            'platform': platform.system(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'gams_path': self.gams_path,
            'gams_version': self.get_gams_version(),
            'available_solvers': self.list_available_solvers()
        }
