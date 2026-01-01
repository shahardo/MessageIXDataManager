"""
Solver Manager - handles message_ix solver execution
"""

import os
import sys
import subprocess
import threading
import time
from typing import Optional, Callable, Dict, Any
import signal

from .logging_manager import logging_manager


class SolverManager:
    """Manages message_ix solver execution"""

    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.execution_thread: Optional[threading.Thread] = None
        self.output_callback: Optional[Callable[[str], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback for console output"""
        self.output_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates"""
        self.status_callback = callback

    def detect_messageix_environment(self) -> bool:
        """Check if message_ix is available in the environment"""
        try:
            # Try to import message_ix
            import ixmp
            import message_ix
            self._log_output("message_ix environment detected")
            return True
        except ImportError:
            self._log_output("message_ix not found in environment")
            return False

    def get_available_solvers(self) -> list[str]:
        """Get list of available solvers"""
        # This is a simplified check - in reality would detect installed solvers
        solvers = []

        # Check for common solvers (simplified)
        try:
            import cplex
            solvers.append("cplex")
        except ImportError:
            pass

        try:
            import gurobipy
            solvers.append("gurobi")
        except ImportError:
            pass

        # GLPK is usually available through pyomo or other interfaces
        solvers.append("glpk")  # Assume available

        return solvers if solvers else ["glpk"]  # Default fallback

    def run_solver(self, input_file_path: str, solver_name: str = "glpk",
                  config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Execute message_ix solver

        Args:
            input_file_path: Path to input Excel file
            solver_name: Name of solver to use
            config: Additional solver configuration

        Returns:
            True if execution completed successfully
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

    def _build_solver_command(self, input_file: str, solver: str,
                            config: Optional[Dict[str, Any]] = None) -> list[str]:
        """Build the solver command (simplified placeholder)"""
        # This is a placeholder - real implementation would construct
        # proper message_ix command based on the framework's API

        # For now, simulate with a simple Python script that mimics solver output
        script_path = os.path.join(os.path.dirname(__file__), "mock_solver.py")

        return [sys.executable, script_path, input_file, solver]

    def _execute_solver(self, cmd: list[str]):
        """Execute solver in subprocess with real-time output"""
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
        """Stop the currently running solver"""
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
        """Check if solver is currently running"""
        return self.is_running

    def _log_output(self, message: str):
        """Log output message"""
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)  # Fallback to console

    def _update_status(self, status: str):
        """Update status"""
        if self.status_callback:
            self.status_callback(status)
