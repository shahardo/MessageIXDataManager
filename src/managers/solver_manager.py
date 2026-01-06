"""
Solver Manager - handles MESSAGEix solver execution

Provides functionality to execute MESSAGEix optimization solvers with support for
multiple solver types, real-time output monitoring, and graceful process management.
"""

import os
import sys
import subprocess
import threading
import time
from typing import Optional, Callable, Dict, Any, List

from .logging_manager import logging_manager


class SolverManager:
    """
    SolverManager class for managing MESSAGEix solver execution.

    Handles the execution of MESSAGEix optimization solvers, providing support for
    different solver types (CPLEX, Gurobi, GLPK), real-time output monitoring,
    and proper process management with logging capabilities.

    Attributes:
        current_process: Currently running solver process, if any
        is_running: Boolean indicating if a solver is currently executing
        execution_thread: Background thread for solver execution
        output_callback: Callback function for console output
        status_callback: Callback function for status updates
    """

    def __init__(self) -> None:
        """
        Initialize the SolverManager.

        Sets up the manager with no active processes and initializes callback handlers.
        """
        self.current_process: Optional[subprocess.Popen[str]] = None
        self.is_running: bool = False
        self.execution_thread: Optional[threading.Thread] = None
        self.output_callback: Optional[Callable[[str], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

    def set_output_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for console output.

        Configures a callback function that will be called with solver output messages
        for real-time display in the UI.

        Args:
            callback: Function that accepts a string message parameter
        """
        self.output_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for status updates.

        Configures a callback function that will be called with status update messages
        to inform the UI about solver execution progress.

        Args:
            callback: Function that accepts a string status parameter
        """
        self.status_callback = callback

    def get_available_solvers(self) -> List[str]:
        """
        Get list of available solvers.

        Detects which optimization solvers are installed and available for use.
        Checks for common solvers like CPLEX, Gurobi, and GLPK.

        Returns:
            List of available solver names (strings)
        """
        # This is a simplified check - in reality would detect installed solvers
        solvers: List[str] = []

        # Check for common solvers (simplified)
        try:
            import cplex  # type: ignore # noqa: F401
            solvers.append("cplex")
        except ImportError:
            pass

        try:
            import gurobipy  # type: ignore # noqa: F401
            solvers.append("gurobi")
        except ImportError:
            pass

        # GLPK is usually available through pyomo or other interfaces
        solvers.append("glpk")  # Assume available

        return solvers if solvers else ["glpk"]  # Default fallback

    def run_solver(
        self,
        input_file_path: str,
        solver_name: str = "glpk",
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute MESSAGEix solver.

        Starts the specified optimization solver on the given input file in a
        background thread, providing real-time output monitoring and status updates.

        Args:
            input_file_path: Path to the MESSAGEix input Excel file
            solver_name: Name of the solver to use (e.g., "glpk", "cplex", "gurobi")
            config: Optional dictionary of additional solver configuration parameters

        Returns:
            True if solver execution was started successfully, False otherwise

        Example:
            >>> manager = SolverManager()
            >>> success = manager.run_solver("model.xlsx", "glpk")
            >>> if success:
            ...     print("Solver started successfully")
        """
        if self.is_running:
            self._log_output("Solver is already running")
            return False

        if not os.path.exists(input_file_path):
            self._log_output(f"Input file not found: {input_file_path}")
            return False

        # Basic command construction (simplified)
        # In reality, this would construct proper message_ix commands
        cmd = self._build_solver_command(input_file_path, solver_name, config)

        self._log_output(f"Starting solver with command: {' '.join(cmd)}")
        self._update_status("Running solver...")

        # Log solver start
        logging_manager.log_solver_execution(' '.join(cmd), 'started')

        # Start execution in background thread
        self.execution_thread = threading.Thread(
            target=self._execute_solver,
            args=(cmd,),
            daemon=True
        )
        self.execution_thread.start()

        return True

    def _build_solver_command(
        self,
        input_file: str,
        solver: str,
        config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Build the solver command (simplified placeholder).

        Constructs the command line arguments needed to execute the solver.
        This is a placeholder implementation - real implementation would construct
        proper MESSAGEix command based on the framework's API.

        Args:
            input_file: Path to the input file
            solver: Name of the solver to use
            config: Optional solver configuration

        Returns:
            List of command line arguments
        """
        # This is a placeholder - real implementation would construct
        # proper message_ix command based on the framework's API

        # For now, simulate with a simple Python script that mimics solver output
        script_path = os.path.join(os.path.dirname(__file__), "mock_solver.py")

        return [sys.executable, script_path, input_file, solver]

    def _execute_solver(self, cmd: List[str]) -> None:
        """
        Execute solver in subprocess with real-time output.

        Runs the solver command in a subprocess, monitoring output in real-time
        and providing status updates through callbacks.

        Args:
            cmd: List of command line arguments to execute
        """
        self.is_running = True

        try:
            # Start subprocess
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output in real-time
            while self.current_process.poll() is None:
                if self.current_process.stdout:
                    line = self.current_process.stdout.readline()
                    if line:
                        self._log_output(line.strip())

                time.sleep(0.1)  # Small delay to prevent busy waiting

            # Read any remaining output
            if self.current_process.stdout:
                remaining = self.current_process.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        self._log_output(line.strip())

            # Check exit code
            exit_code = self.current_process.returncode
            if exit_code == 0:
                self._log_output("Solver completed successfully")
                self._update_status("Solver completed")
                logging_manager.log_solver_execution(' '.join(cmd), 'completed')
            else:
                self._log_output(f"Solver failed with exit code: {exit_code}")
                self._update_status("Solver failed")
                logging_manager.log_solver_execution(' '.join(cmd), 'failed')

        except Exception as e:
            self._log_output(f"Solver execution error: {str(e)}")
            self._update_status("Solver error")

        finally:
            self.is_running = False
            self.current_process = None

    def stop_solver(self) -> bool:
        """
        Stop the currently running solver.

        Attempts to gracefully terminate the running solver process. If graceful
        termination fails within 5 seconds, forces termination.

        Returns:
            True if solver was successfully stopped, False otherwise

        Example:
            >>> manager = SolverManager()
            >>> # ... start solver ...
            >>> stopped = manager.stop_solver()
            >>> print(f"Solver stopped: {stopped}")
        """
        if not self.is_running or not self.current_process:
            return False

        try:
            self._log_output("Stopping solver...")
            self._update_status("Stopping solver...")

            # Try graceful termination first
            self.current_process.terminate()

            # Wait a bit for graceful shutdown
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination failed
                self.current_process.kill()
                self.current_process.wait()

            self._log_output("Solver stopped")
            self._update_status("Solver stopped")
            self.is_running = False
            return True

        except Exception as e:
            self._log_output(f"Error stopping solver: {str(e)}")
            return False

    def is_solver_running(self) -> bool:
        """
        Check if solver is currently running.

        Returns:
            True if a solver process is currently executing, False otherwise

        Example:
            >>> manager = SolverManager()
            >>> is_running = manager.is_solver_running()
            >>> print(f"Solver running: {is_running}")
        """
        return self.is_running

    def _log_output(self, message: str) -> None:
        """
        Log output message.

        Sends the message to the configured output callback, or prints to console
        if no callback is configured.

        Args:
            message: The message to log
        """
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)  # Fallback to console

    def _update_status(self, status: str) -> None:
        """
        Update status.

        Sends the status message to the configured status callback if available.

        Args:
            status: The status message to send
        """
        if self.status_callback:
            self.status_callback(status)
