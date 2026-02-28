"""
SolverWorker — QThread-based subprocess runner for MESSAGEix solver execution.

Runs the solver subprocess in a background thread and emits Qt signals for
real-time console output, status updates, and completion notification.

All signals are delivered to connected slots through Qt's queued-connection
mechanism, which guarantees that UI widgets (QTextEdit, QStatusBar, etc.) are
always updated from the main thread — even though the subprocess reads happen
on the worker thread.
"""

import subprocess
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal


class SolverWorker(QThread):
    """
    QThread that wraps a solver subprocess and streams its output via signals.

    Usage in the UI layer (main thread)::

        worker = solver_manager.create_worker(cmd)
        worker.output_line.connect(self._append_to_console)
        worker.status_changed.connect(self._update_status_from_solver)
        worker.finished.connect(self._on_solver_finished)
        worker.start()   # subprocess begins; signals arrive on the main thread

    Attributes:
        output_line:    Emitted for each stdout/stderr line produced by the solver.
        status_changed: Emitted at key milestones (starting, running, done).
        finished:       Emitted once when the subprocess exits.
                        Carries (exit_code: int, result_file: str).
                        result_file is the path announced by run_messageix.py via
                        the [RESULT_FILE] prefix, or an empty string when absent.
    """

    output_line: pyqtSignal = pyqtSignal(str)
    status_changed: pyqtSignal = pyqtSignal(str)
    # exit_code, result_file_path (empty string when not produced)
    finished: pyqtSignal = pyqtSignal(int, str)

    # run_messageix.py prints this prefix to announce the output file path
    RESULT_FILE_PREFIX = "[RESULT_FILE]"

    def __init__(self, cmd: List[str], parent=None) -> None:
        """
        Initialise the worker.

        Args:
            cmd:    Full command list passed directly to subprocess.Popen.
            parent: Optional QObject parent.
        """
        super().__init__(parent)
        self._cmd = cmd
        self._process: subprocess.Popen = None
        self._result_file: str = ""
        self._stop_requested: bool = False

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the subprocess and stream output via signals (worker thread)."""
        print(f"DEBUG SolverWorker.run: started, cmd={self._cmd}", flush=True)
        self.status_changed.emit("Running solver...")
        self._result_file = ""

        try:
            print("DEBUG SolverWorker.run: calling Popen...", flush=True)
            self._process = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            print(f"DEBUG SolverWorker.run: Popen succeeded, pid={self._process.pid}", flush=True)

            # Iterate lines as they arrive; this blocks until EOF
            for raw_line in self._process.stdout:
                line = raw_line.rstrip()
                if line.startswith(self.RESULT_FILE_PREFIX):
                    # Extract result file path; don't show this prefix in console
                    self._result_file = line[len(self.RESULT_FILE_PREFIX):].strip()
                else:
                    self.output_line.emit(line)

            # Wait for the process to fully terminate and collect exit code.
            # If stop() was called we give 5 extra seconds then force-kill.
            try:
                self._process.wait(timeout=5 if self._stop_requested else None)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            exit_code = self._process.returncode

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            print(f"DEBUG SolverWorker.run: exception: {exc!r}\n{tb}", flush=True)
            self.output_line.emit(f"Solver execution error: {exc}")
            self.output_line.emit(f"Traceback:\n{tb}")
            self.status_changed.emit("Solver error")
            self.finished.emit(1, "")
            return
        finally:
            self._process = None
            print("DEBUG SolverWorker.run: finally — _process cleared", flush=True)

        print(f"DEBUG SolverWorker.run: done, exit_code={exit_code} result_file={self._result_file!r}",
              flush=True)
        if exit_code == 0:
            self.status_changed.emit("Solver completed")
        else:
            self.status_changed.emit("Solver failed")

        self.finished.emit(exit_code, self._result_file)

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """
        Request termination of the running subprocess.

        Sends SIGTERM (TerminateProcess on Windows) and returns immediately.
        The worker thread will detect the process exit through its stdout
        loop, call wait(), and emit ``finished`` in the normal way.
        Force-killing after a timeout is handled inside run() via
        ``_stop_requested``.

        This method intentionally does NOT block the calling thread.
        """
        self._stop_requested = True
        proc = self._process
        if proc is not None:
            self.output_line.emit("Stopping solver...")
            self.status_changed.emit("Stopping solver...")
            proc.terminate()
