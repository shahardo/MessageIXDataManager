# Fix Plan: Solver Integration & Real MESSAGEix Execution

## Overview

This document describes all bugs in the current solver implementation and the full
plan to replace the mock solver with a real MESSAGEix execution via `ixmp` /
`message_ix` Python API, supporting GAMS with CPLEX/Gurobi as the LP solver and
GAMS with GLPK as the open-source fallback.

---

## Part 1 — Bug Fixes

### Bug 1 (Critical): Thread-Safety — UI Updates from Background Thread

**Location**: `src/managers/solver_manager.py` → `_execute_solver()`, and the
callbacks set in `src/ui/main_window.py` lines 357–358.

**Problem**: `_execute_solver` runs on a daemon `threading.Thread`. It calls
`output_callback` (→ `self.console.append()`) and `status_callback`
(→ `self.statusbar.showMessage()`) directly. Qt forbids touching any widget from a
non-main thread; doing so causes crashes or silent data corruption.

**Fix**: Replace the plain `threading.Thread` in `SolverManager` with a
`QThread`-based worker that emits Qt signals. The UI connects slots to those signals
— Qt guarantees cross-thread signal delivery is queued and safe.

Implementation sketch:

```python
# src/managers/solver_worker.py  (new file)
from PyQt5.QtCore import QThread, pyqtSignal

class SolverWorker(QThread):
    output_line = pyqtSignal(str)   # emitted for each console line
    status_changed = pyqtSignal(str)  # emitted for status-bar updates
    finished = pyqtSignal(int)       # emitted with exit code when done

    def __init__(self, cmd: list[str]):
        super().__init__()
        self._cmd = cmd
        self._process = None

    def run(self):
        import subprocess, time
        self._process = subprocess.Popen(
            self._cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        while self._process.poll() is None:
            line = self._process.stdout.readline()
            if line:
                self.output_line.emit(line.rstrip())
        remaining = self._process.stdout.read()
        for line in remaining.splitlines():
            self.output_line.emit(line.rstrip())
        self.finished.emit(self._process.returncode)

    def stop(self):
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
```

`SolverManager` holds a `SolverWorker` instance, connects its signals to the
callbacks, and replaces `is_running` with `worker.isRunning()`.

In `main_window.py` the connections become:

```python
self._solver_worker.output_line.connect(self._append_to_console)
self._solver_worker.status_changed.connect(self._update_status_from_solver)
self._solver_worker.finished.connect(self._on_solver_finished)
```

---

### Bug 2: `is_running` Race Condition

**Location**: `solver_manager.py` lines 152–178.

**Problem**: `is_running` is set to `True` inside `_execute_solver()`, which runs on
the new thread. Between `execution_thread.start()` returning and the thread actually
executing its first line, `is_running` is still `False`. A second call to
`run_solver()` can pass the guard and start a second subprocess.

**Fix**: Set `is_running = True` (or start the `QThread`) before the thread begins
executing. With the `QThread` approach this is automatic — `QThread.isRunning()`
returns `True` the moment `start()` is called.

```python
# In SolverManager.run_solver():
self._worker = SolverWorker(cmd)
self._worker.output_line.connect(...)
self._worker.finished.connect(self._on_worker_finished)
self._worker.start()          # isRunning() is True from this point
```

---

### Bug 3: GLPK Unconditionally Listed as Available

**Location**: `solver_manager.py` lines 121–124.

**Problem**: `get_available_solvers()` always appends `"glpk"` and returns at least
`["glpk"]`, so `_run_solver`'s "No Solvers Available" guard is dead code. GLPK may
not actually be installed or accessible from GAMS.

**Fix**: Probe GLPK availability properly. Within the MESSAGEix/GAMS context, GLPK
is accessed through GAMS, not as a standalone Python package. The correct check is
whether GAMS is on the system PATH and whether the GLPK solver licence is present
in the GAMS distribution.

```python
def _glpk_available_via_gams(self) -> bool:
    """Return True if GAMS is on PATH and its GLPK solver is accessible."""
    import subprocess, shutil
    if not shutil.which("gams"):
        return False
    try:
        result = subprocess.run(
            ["gams", "?"], capture_output=True, text=True, timeout=5)
        return "GLPK" in result.stdout or "glpk" in result.stdout.lower()
    except Exception:
        return False
```

Also test for the `message_ix` / `ixmp` Python packages separately, since those are
required regardless of which LP solver is used.

---

### Bug 4: Input File Selection Uses Last Loaded File

**Location**: `main_window.py` lines 1391–1398.

**Problem**: When multiple scenarios are loaded, the solver receives
`input_paths[-1]` (the last one). The user may have a different scenario selected.

**Fix**: Use the currently selected scenario's input file.

```python
# In _run_solver():
scenario = self.selected_scenario
if scenario is None or not scenario.input_file:
    QMessageBox.warning(self, "No Scenario Selected",
                        "Please select a scenario with a loaded input file.")
    return
input_path = scenario.input_file
```

---

## Part 2 — Real MESSAGEix Solver Integration

### How MESSAGEix Solving Works

MESSAGEix uses a two-layer architecture:

```
message_ix.Scenario.solve()
    ↓
ixmp.model.gams.GAMSModel
    ↓
GAMS executable (writes GDX input, reads GDX output)
    ↓
LP solver: CPLEX / Gurobi / GLPK (configured inside GAMS)
```

The Python packages (`ixmp`, `message_ix`) manage the data pipeline. The GAMS
executable is a separate installation. The LP solver is configured as a GAMS option,
not as a Python dependency.

GLPK is bundled with GAMS (free tier). CPLEX/Gurobi require paid licences.

### Prerequisites

| Requirement | Check |
|-------------|-------|
| `ixmp` Python package | `import ixmp` |
| `message_ix` Python package | `import message_ix` |
| GAMS executable | `shutil.which("gams")` or `GAMSDIR` env var |
| Java (for ixmp HSQLDB backend) | `shutil.which("java")` |
| GLPK solver in GAMS | `gams ?` lists GLPK |
| CPLEX in GAMS | valid GAMS/CPLEX licence |

### Data Flow: Excel ScenarioData → ixmp Scenario

The app reads MESSAGEix input from Excel files and holds the data as `ScenarioData`
(sets + `Parameter` objects with long-format DataFrames). To use the Python API the
data must be written into an `ixmp.Platform` database first.

```
ScenarioData (in-memory)
    ↓  ScenarioExporter (new class)
ixmp.Platform  (temporary local HSQLDB)
    ↓
message_ix.Scenario (populated)
    ↓  scenario.solve(model='MESSAGE', ...)
GAMS + LP solver
    ↓
message_ix.Scenario (with solution variables)
    ↓  ResultsExtractor (new class)
Results Excel  (compatible with ResultsAnalyzer)
```

---

## Part 3 — Implementation Plan

### Step 1: New File — `src/managers/solver_worker.py`

Create a `QThread`-based worker that runs a subprocess and emits Qt signals.

**Contents**:
- `SolverWorker(QThread)` with signals: `output_line`, `status_changed`, `finished`
- `run()`: Popen + real-time readline loop
- `stop()`: graceful terminate → force kill on timeout
- No direct UI references

---

### Step 2: Refactor `src/managers/solver_manager.py`

**Remove**:
- `self.is_running: bool` (replaced by `QThread.isRunning()`)
- `self.execution_thread: threading.Thread`
- `self.current_process` (moved to worker)
- `_execute_solver()` method
- All `time.sleep()` calls
- `mock_solver.py` reference from `_build_solver_command`

**Add**:
- `self._worker: Optional[SolverWorker] = None`
- `get_available_solvers()` — detect message_ix, gams, CPLEX/Gurobi/GLPK properly
- `detect_gams()` — check PATH + GAMSDIR env var
- `detect_messageix()` — try `import ixmp; import message_ix`
- `_build_real_solver_command()` — constructs the command for the message_ix runner
  script (see Step 3)
- `is_solver_running()` — delegate to `self._worker.isRunning()` if worker exists

**Updated `run_solver()`**:
```python
def run_solver(self, input_file: str, solver: str, model_name: str,
               scenario_name: str) -> bool:
    if self.is_solver_running():
        return False
    cmd = self._build_real_solver_command(
        input_file, solver, model_name, scenario_name)
    self._worker = SolverWorker(cmd)
    self._worker.output_line.connect(self._log_output)
    self._worker.status_changed.connect(self._update_status)
    self._worker.finished.connect(self._on_finished)
    self._update_status("Starting solver...")
    self._worker.start()
    return True
```

---

### Step 3: New File — `src/managers/run_messageix.py`

A standalone Python script (run as a subprocess) that:
1. Accepts CLI args: `--input <file>`, `--solver <glpk|cplex|gurobi>`,
   `--model <name>`, `--scenario <name>`, `--output-dir <dir>`
2. Imports `ixmp` and `message_ix`
3. Creates a temporary local ixmp Platform (HSQLDB in a temp directory)
4. Calls `ScenarioLoader.load_from_excel(platform, input_file, model, scenario_name)`
   to populate the scenario (see Step 4)
5. Calls `scenario.solve(model='MESSAGE', solve_options=solver_options)`
6. Calls `ResultsExporter.export_to_excel(scenario, output_dir)` to write a
   results Excel file compatible with the existing `ResultsAnalyzer`
7. Prints structured progress lines (prefixed with `[PROGRESS]`, `[STATUS]`,
   `[ERROR]`, `[RESULT_FILE]`) so the GUI can parse them

This runs in a separate process so the GUI never blocks, even if ixmp/GAMS hangs.

**Solver options by solver**:

```python
SOLVER_OPTIONS = {
    "glpk":   {"solver": "glpk"},
    "cplex":  {"advind": 0, "epopt": 1e-6, "lpmethod": 4, "threads": 4},
    "gurobi": {"method": 2},
}
```

---

### Step 4: New File — `src/managers/scenario_loader.py`

Converts `ScenarioData` (in-memory) into a populated `message_ix.Scenario`.

**Key method**:
```python
def load_from_excel(
    platform: "ixmp.Platform",
    input_file: str,
    model_name: str,
    scenario_name: str,
) -> "message_ix.Scenario":
    ...
```

**Steps inside**:
1. Use `InputManager` to load the Excel (or re-use the already-loaded ScenarioData
   if passed directly)
2. Create `message_ix.Scenario(platform, model_name, scenario_name, version='new')`
3. Call `scenario.check_out()`
4. Add all sets: `scenario.add_set(name, data)` for each set in ScenarioData
5. Add all parameters: `scenario.add_par(name, df)` for each Parameter
   - DataFrames must use ixmp column conventions (index columns + `value` column)
   - Already matches the app's internal format
6. Call `scenario.commit("Loaded from Excel")`
7. Return the scenario object

---

### Step 5: New File — `src/managers/results_exporter.py`

Reads the solved `message_ix.Scenario` and writes a results Excel file.

**Key method**:
```python
def export_to_excel(scenario: "message_ix.Scenario", output_path: str) -> str:
    ...
```

**Exports**:
- `var_ACT`, `var_CAP`, `var_EMISS`, `COST_NODAL`, etc. via
  `scenario.var(name)` → DataFrame
- Writes each variable as a sheet in the output Excel
- Naming convention matches the existing `ResultsAnalyzer` sheet parser
- Returns the path to the written file

---

### Step 6: Update `src/ui/main_window.py` — `_run_solver()`

Replace the current implementation:

```python
def _run_solver(self):
    if self.solver_manager.is_solver_running():
        self._append_to_console("Solver is already running")
        return

    # Use selected scenario, not last loaded file
    scenario = self.selected_scenario
    if scenario is None or not scenario.input_file:
        QMessageBox.warning(self, "No Scenario Selected",
                            "Select a scenario with an input file first.")
        return

    # Check prerequisites
    if not self.solver_manager.detect_messageix():
        QMessageBox.critical(
            self, "MESSAGEix Not Found",
            "The 'ixmp' and 'message_ix' Python packages are required.\n"
            "Install them with: pip install message-ix")
        return
    if not self.solver_manager.detect_gams():
        QMessageBox.critical(
            self, "GAMS Not Found",
            "GAMS executable not found on PATH.\n"
            "Install GAMS and ensure it is on your system PATH.")
        return

    # Solver selection dialog (simple)
    solvers = self.solver_manager.get_available_solvers()
    solver_name, ok = QInputDialog.getItem(
        self, "Select Solver", "Solver:", solvers, 0, False)
    if not ok:
        return

    self._append_to_console(f"Starting MESSAGEix solver...")
    self._append_to_console(f"Input: {scenario.input_file}")
    self._append_to_console(f"Solver: {solver_name}")

    self.solver_manager.run_solver(
        input_file=scenario.input_file,
        solver=solver_name,
        model_name=scenario.name,
        scenario_name="base",
    )

def _on_solver_finished(self, exit_code: int, result_file: Optional[str]):
    if exit_code == 0 and result_file:
        self._append_to_console(f"Solver finished. Loading results: {result_file}")
        # Auto-load the results file into the ResultsAnalyzer
        self.results_file_handler.load_files(
            [result_file], self.update_progress, self._append_to_console)
    elif exit_code == 0:
        self._append_to_console("Solver completed successfully.")
    else:
        self._append_to_console(f"Solver failed (exit code {exit_code}).")
```

---

### Step 7: Update `get_available_solvers()` in `solver_manager.py`

```python
def get_available_solvers(self) -> List[str]:
    """Return solvers available within the installed GAMS distribution."""
    solvers = []
    if not self.detect_gams():
        return solvers  # nothing works without GAMS

    # GLPK: bundled with all GAMS distributions
    if self._glpk_available_via_gams():
        solvers.append("glpk")

    # Commercial solvers: check Python package as proxy for licence
    try:
        import cplex  # noqa: F401
        solvers.append("cplex")
    except ImportError:
        pass

    try:
        import gurobipy  # noqa: F401
        solvers.append("gurobi")
    except ImportError:
        pass

    return solvers
```

---

### Step 8: Delete `src/managers/mock_solver.py`

The file is no longer needed once the real solver pipeline is in place.

---

## Part 4 — File Checklist

| Action | File |
|--------|------|
| Create | `src/managers/solver_worker.py` |
| Create | `src/managers/run_messageix.py` |
| Create | `src/managers/scenario_loader.py` |
| Create | `src/managers/results_exporter.py` |
| Refactor | `src/managers/solver_manager.py` |
| Update | `src/ui/main_window.py` (`_run_solver`, `_on_solver_finished`) |
| Delete | `src/managers/mock_solver.py` |

---

## Part 5 — Testing Plan

| Test | File |
|------|------|
| `SolverWorker` emits signals from thread (no crash) | `tests/test_solver_worker.py` |
| `SolverManager.get_available_solvers()` — mock GAMS absent | `tests/test_solver_manager.py` |
| `SolverManager.get_available_solvers()` — mock GAMS present, GLPK only | `tests/test_solver_manager.py` |
| `ScenarioLoader.load_from_excel()` with a minimal test Excel | `tests/test_scenario_loader.py` |
| `ResultsExporter.export_to_excel()` round-trip | `tests/test_results_exporter.py` |
| `_run_solver()` uses `selected_scenario`, not last path | `tests/test_main_window_solver.py` |
| `_run_solver()` shows error when message_ix absent | `tests/test_main_window_solver.py` |

---

## Part 6 — Open Questions / Risks

1. **ixmp backend**: The simplest local backend is HSQLDB (requires Java). If Java is
   not installed the Platform cannot be created. Consider adding a Java check to the
   prerequisite detection, or exploring the `ixmp` `local` backend if available in
   newer versions.

2. **Data format gaps**: The app's `ScenarioData` may be missing some sets
   (`type_year`, `type_tec`, etc.) that MESSAGEix requires internally. The
   `ScenarioLoader` will need to either derive these from the data or read them
   from the Excel file's sets sheets.

3. **Results schema**: The existing `ResultsAnalyzer` expects specific sheet names
   and column layouts. The `ResultsExporter` must produce exactly this format, or the
   `ResultsAnalyzer` must be extended to also accept ixmp-style DataFrames directly.

4. **GAMS licence**: Without a GAMS licence, the solver cannot run even with GLPK.
   GAMS provides a free academic and trial licence; users must install it themselves.

5. **Long-running solves**: Large MESSAGEix models can take hours. The `QThread`
   approach keeps the UI responsive. Consider adding a progress dialog with a
   "Cancel" button that calls `worker.stop()`.
