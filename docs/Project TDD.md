# Technical Design Document: MESSAGEix Data Manager

**Version**: 2.0
**Date**: March 2026
**Status**: Current — reflects implemented codebase

---

## 1. Introduction

### 1.1 Purpose
This document describes the technical architecture and design of the MESSAGEix Data Manager as implemented. It serves as the primary reference for understanding component responsibilities, data flows, and extension points.

### 1.2 Scope
The system is a PyQt5 desktop application enabling energy systems modelers to:
- Load, view, edit, and save MESSAGEix Excel input files
- Execute MESSAGEix model solves via GAMS
- Load, analyze, and visualize solver results
- Manage multiple named scenarios and compare results

### 1.3 Key Technology Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| GUI Framework | **PyQt5** | Native performance; seamless Python integration; `QWebEngineView` for Plotly |
| Excel I/O | **openpyxl + pandas** | Full read/write; DataFrame-based in-memory model |
| Visualization | **Plotly** (offline) rendered in `QWebEngineView` | Interactive HTML charts without a server |
| Solver Execution | Subprocess: `run_messageix.py` | Process isolation; streams stdout to UI via QThread |
| Solver Backend | **ixmp + GAMS** | Standard MESSAGEix integration; HSQLDB temp platform |
| Java Bridge | **JPype** | Required by ixmp for the JDBC/HSQLDB backend |
| Session Storage | JSON files | Lightweight; no database dependency for session state |
| Testing | **pytest + pytest-qt** | Broad coverage; Qt widget testing |

---

## 2. System Architecture

### 2.1 Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     UI Layer (PyQt5)                        │
│                                                             │
│  MainWindow                                                 │
│  ├── FileNavigatorWidget      (scenario/file browser)       │
│  ├── ParameterTreeWidget      (categorized parameter nav)   │
│  ├── DataDisplayWidget        (pivot table + chart)         │
│  ├── ChartWidget              (Plotly in QWebEngineView)    │
│  ├── InputFileDashboard       (set/parameter overview)      │
│  ├── ResultsFileDashboard     (wide-format results charts)  │
│  ├── PostprocessingDashboard  (domain analysis charts)      │
│  └── WarningSummaryDialog     (solver warning review)       │
├─────────────────────────────────────────────────────────────┤
│                  Managers / Logic Layer                     │
│                                                             │
│  InputManager         — parse input Excel → ScenarioData   │
│  DataFileManager      — load ZIP/CSV or Excel (var_/equ_)  │
│  ResultsAnalyzer      — load wide-format results Excel     │
│  ResultsPostprocessor — orchestrate domain analyzers       │
│  ResultsExporter      — write solved scenario to Excel     │
│  SolverManager        — detect GAMS/solvers, build cmd     │
│  SolverWorker         — QThread subprocess runner          │
│  run_messageix.py     — standalone solver script           │
│  ScenarioLoader       — load Excel → ixmp Platform         │
│  WarningAnalyzer      — classify warnings, suggest fixes   │
│  SessionManager       — persist scenario state to JSON     │
│  ParameterManager     — parameter validation/creation      │
│  DataExportManager    — CSV/Excel export                   │
│  UndoManager          — Command-pattern undo/redo stack    │
├─────────────────────────────────────────────────────────────┤
│              Analysis Layer (src/analysis/)                 │
│                                                             │
│  ScenarioDataWrapper  — msg.par()/var()/set() interface    │
│  BaseAnalyzer         — shared helpers and state           │
│  ElectricityAnalyzer  — generation, capacity, LCOE, costs  │
│  EmissionsAnalyzer    — GHG by type/sector/fuel            │
│  EnergyBalanceAnalyzer — primary/final energy, trade       │
│  FuelAnalyzer         — gas, coal, oil, biomass flows      │
│  SectorAnalyzer       — buildings, industry, transport     │
│  PriceAnalyzer        — energy prices by level/sector      │
├─────────────────────────────────────────────────────────────┤
│                    Data / Utility Layer                     │
│                                                             │
│  parsing_strategies.py  — Strategy pattern for sheet types │
│  parameter_factory.py   — Factory for Parameter creation   │
│  technology_classifier.py — tech grouping & level mapping  │
│  data_transformer.py    — DataFrame transformations        │
│  Excel I/O (openpyxl/pandas)                               │
│  ixmp HSQLDB (temp dir per solve)                          │
│  JSON session files                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Key Connections
- `MainWindow` orchestrates all managers and wires signals/slots
- `SignalRegistry` tracks signal-slot connections for centralized management
- `UserPreferences` (shared QObject) keeps year-range filter synchronized between `DataDisplayWidget` and `PostprocessingDashboard`
- `DashboardChartMixin` provides shared chart rendering to `ResultsFileDashboard` and `PostprocessingDashboard`

---

## 3. Component Details

### 3.1 InputManager
- Reads Excel workbooks with `openpyxl`; parses each sheet via `ParsingStrategy` subclasses
- Produces `ScenarioData` (sets dict + parameters dict)
- Strategy subclasses: `SetParsingStrategy`, `ParameterParsingStrategy`, `MappingParsingStrategy`
- Used when loading the input file (`.xlsx`) into the editor

### 3.2 DataFileManager
- Supports two formats:
  - **ZIP archive** of CSV files with `set_*` / `par_*` / `var_*` / `equ_*` prefixes
  - **Excel workbook** with sheets named `var_<NAME>` / `equ_<NAME>` / `par_<NAME>` / `set_<NAME>`
- Returns `(ScenarioData, replaced_items)` tuple; merged into existing scenario data
- Used for: manually loaded data files, and auto-loading solver result Excel after a successful solve
- `_load_excel_data()` does a first pass on `par_output` to discover electricity technologies before processing all sheets

### 3.3 ResultsAnalyzer
- Loads wide-format (pre-pivoted) results Excel files
- Uses `ParsingStrategy` subclasses for each sheet type
- Feeds `ResultsPostprocessor` for derived metric calculation
- Distinct from `DataFileManager`: expects pivoted tables, not long-format `var_*` sheets

### 3.4 ResultsPostprocessor
- Thin facade: takes `ScenarioData`, detects node location and plot years, instantiates each domain analyzer, calls `calculate()`, collects results
- Converts `results` dict entries to `Parameter` objects and merges into `ScenarioData`
- Domain analyzers: `ElectricityAnalyzer`, `EmissionsAnalyzer`, `EnergyBalanceAnalyzer`, `FuelAnalyzer`, `SectorAnalyzer`, `PriceAnalyzer`

### 3.5 ScenarioDataWrapper (in base_analyzer.py)
- Provides `msg.par(name, filters)`, `msg.var(name, filters)`, `msg.set(name)` interface
- Normalizes year columns (`year_act`, `year_vtg`, `year_rel`, `year`) to `int64` on access — prevents type-mismatch errors when merging input params (strings) with result vars (integers)
- Used by all domain analyzers via `self.msg`

### 3.6 Solver Pipeline

```
User clicks "Run Solver"
  → MainWindow._run_solver()
  → SolverManager.get_available_solvers()   # detect GAMS + CPLEX/Gurobi
  → _SolverSelectionDialog                  # user picks solver
  → SolverManager.build_solver_command()    # builds: python run_messageix.py --input ... --solver ...
  → SolverManager.create_worker(cmd)        # creates SolverWorker(QThread)
  → worker signals connected:
      output_line   → _append_to_console()
      status_changed → status bar
      finished      → _on_solver_finished()
  → worker.start()

Inside SolverWorker.run() (background thread):
  → subprocess.Popen(cmd)
  → reads stdout line by line:
      [RESULT_FILE] path  → captured as _result_file
      other lines         → output_line signal emitted
  → process.wait()
  → finished(exit_code, result_file) emitted

Inside run_messageix.py (subprocess):
  → _setup_environment()   # auto-detects JAVA_HOME, IXMP_GAMS_PATH
  → ixmp.Platform(backend='jdbc', driver='hsqldb', url=temp_dir)
  → ScenarioLoader.load_from_excel()   # parse input Excel → ixmp Platform
  → scenario.solve(model='MESSAGE', solve_options=...)
  → ResultsExporter.export_to_excel()  # writes var_*/equ_* sheets
  → prints [RESULT_FILE] <path>

Back in MainWindow._on_solver_finished():
  → DataFileManager._load_excel_data(result_file)   # loads var_*/equ_* into ScenarioData
  → file_navigator.update_scenarios()               # shows file in Data File slot
  → _switch_to_multi_section_view()                 # refreshes parameter tree
  → WarningSummaryDialog (if warnings collected)
```

### 3.7 ScenarioLoader
- Parses input Excel via `InputManager` into `ScenarioData`
- Creates `message_ix.Scenario(version='new')` on an `ixmp.Platform`
- Adds 1-D sets first (building a case-insensitive lookup for casing normalization), then mapping sets
- Skips ixmp-internal sets (`ix_type_mapping`)
- For each parameter, calls `_prepare_parameter_df()` → `scenario.add_par()`
  - Applies `KNOWN_UNIT_MAP` substitutions
  - On unit rejection: retries with `unit="-"` (dimensionless fallback)
- Commits scenario; returns it ready for `scenario.solve()`

### 3.8 ResultsExporter
- Queries `scenario.var_list()` and `scenario.equ_list()` for all available names
- Writes primary names first (ordered list), then any extras not in the primary list
- Sheet names: `var_<NAME>` / `equ_<NAME>` (truncated to 31 chars for Excel)
- Handles dict return from `scenario.var()` for scalar variables (wraps in single-row DataFrame)

### 3.9 WarningAnalyzer + WarningSummaryDialog
- `WarningAnalyzer` parses console lines during the solve, classifies warnings by type (unit errors, missing sets, solver infeasibility, etc.)
- `KNOWN_UNIT_MAP` maps invalid unit strings to valid ixmp equivalents or `"-"`
- `WarningSummaryDialog`: non-modal dialog displayed after solve if warnings exist
  - `navigate_requested` signal → `MainWindow._navigate_to_parameter()`
  - `autofix_requested` signal → `MainWindow._autofix_parameter_unit()` (replaces unit in the loaded parameter DataFrame)

### 3.10 TechnologyClassifier
- `build_level_technology_map()`: discovers energy levels from input scenario sets
- `filter_by_energy_level()`: filters var_* DataFrame to technologies at a given level
- `apply_technology_grouping()`: aggregates technologies by `TECHNOLOGY_GROUPS` patterns (prefix/suffix matching)
- `_EMISSION_TECH_PATTERNS`: regex for dynamically detecting emission technologies

---

## 4. Data Models

### 4.1 Core In-Memory Models (data_models.py)

```python
class Parameter:
    name: str
    df: pd.DataFrame       # columns: dim1, ..., dimN, value [, unit]
    metadata: dict         # {'units': str, 'description': str, 'dims': list[str],
                           #  'result_type': 'variable'|'equation'|None}

class ScenarioData:
    sets: dict[str, pd.Series | pd.DataFrame]   # 1-D or mapping sets
    parameters: dict[str, Parameter]
    modified: set[str]
    change_history: list[dict]

    def get_parameter(name) -> Parameter | None
    def add_parameter(param, mark_modified, add_to_history)
    def get_summary() -> str

class Scenario:
    name: str
    input_file: str | None          # .xlsx input file path
    message_scenario_file: str | None  # data file path (.zip or results .xlsx)
    results_file: str | None        # wide-format results .xlsx path
    data: ScenarioData | None
```

### 4.2 Year Column Normalization

All `year_*` dimension columns are normalized to `int64` when accessed via `ScenarioDataWrapper.par()`. This prevents `ValueError: merge on int64 and object columns` when joining input parameters (loaded as strings) with result variables (loaded as integers from Excel).

```python
_YEAR_COLS = frozenset({"year_act", "year_vtg", "year_rel", "year"})

def _normalize_year_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in _YEAR_COLS:
        if col in df.columns and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("int64")
    return df
```

### 4.3 Parameter result_type Metadata

Parameters loaded from `var_*` sheets have `metadata['result_type'] = 'variable'`.
Parameters loaded from `equ_*` sheets have `metadata['result_type'] = 'equation'`.
This metadata drives:
- `TechnologyClassifier` filtering
- `DataDisplayWidget` value column detection (`lvl` vs `value`)
- `ScenarioData.get_summary()` counting vars/equs separately

---

## 5. Key Technical Approaches

### 5.1 Excel Round-Trip
- Input loading: `InputManager` → `ParsingStrategy` subclasses → `ScenarioData`
- Saving: serialize `Parameter.df` back to sheets in the original workbook; preserve formatting
- Solver input: `ScenarioLoader` re-parses the saved Excel; writes into temporary ixmp Platform

### 5.2 Validation
- Type checks on cell edit in `DataDisplayWidget` / `edit_handler.py`
- Unit validation during ixmp `add_par()` → retry-with-`"-"` fallback
- `WarningAnalyzer` post-solve classification

### 5.3 Undo/Redo
- Command pattern in `src/managers/commands.py`
- `UndoManager` (aliased as `TableUndoManager`) holds a stack of `Command` objects
- Each `Command` implements `do()` / `undo()`
- `DataDisplayWidget` executes commands for all cell edits

### 5.4 Background Solver Execution
- `SolverWorker(QThread)`: subprocess is launched in `run()`; stdout read line-by-line; each line emitted via `output_line` signal using Qt's queued connection (safe cross-thread UI update)
- `stop()`: calls `proc.terminate()`; worker detects EOF, waits 5 s, then force-kills
- `[RESULT_FILE]` prefix in stdout used as a structured IPC mechanism to pass the output path back to the parent

### 5.5 Technology Grouping for Results Display
1. `TechnologyClassifier.build_level_technology_map()` — enumerate levels from `level` set + ACT data
2. `filter_by_energy_level(df, level)` — keep only technologies at the selected energy level; emission technologies matched by regex
3. `apply_technology_grouping(df)` — collapse individual technology columns into group columns (e.g., `coal_ppl` + `coal_adv` → `"Coal"`)
4. `DataDisplayWidget` pivots the result on `technology` (or `commodity`, `emission`, etc.) with `sum` aggregation

---

## 6. File Organization

```
src/
├── core/           # Pure data structures; no PyQt5 imports
├── managers/       # Business logic; minimal UI coupling
├── analysis/       # Pure computation; no PyQt5 imports
├── ui/             # PyQt5 widgets, controllers, dashboards
└── utils/          # Stateless helpers and utilities

tests/              # pytest; mirrors src/ structure
docs/               # PRD, TDD, devplan
assets/             # Icons, QSS stylesheets
files/              # Sample MESSAGEix data files
```

---

## 7. Testing Strategy

### 7.1 Scope
- **Unit tests**: individual managers, parsers, analyzers, utility functions
- **Integration tests**: end-to-end file loading pipelines, undo/redo flows
- **UI tests**: `pytest-qt` for widget interactions, signal/slot connections

### 7.2 Current Status
- ~591 tests collected
- ~589 pass; ~4 skip
- 1 pre-existing failure: `test_data_models::test_mark_modified` (test expectation mismatch)
- Full suite exit code 1 due to Qt/WebEngine teardown crash on exit (not a test failure)

### 7.3 Test Scope Policy
- Run only tests for modified files (not the full suite on every change)
- Example: editing `data_file_manager.py` → `pytest tests/test_data_file_manager.py`

### 7.4 Known Test Gaps
- Solver pipeline integration tests require ixmp/GAMS installation
- Mock solver tests in `test_z_mock_solver.py` cover the subprocess protocol

---

## 8. Development Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | MVP: single-scenario core, parameter tree, solver execution, results loading | ✅ Complete |
| 2 | Input editing, validation, undo/redo, save/save-as, search | ✅ Complete |
| 3 | Full solver pipeline, domain analyzers, dashboards, warning analysis | ✅ Complete |
| 4 | Multi-scenario comparison, overlay charts | 🚧 In Progress |
| 5 | Cross-platform, packaging, documentation | 📋 Planned |

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| ixmp/MESSAGEix API changes | Isolated in `ScenarioLoader` and `ResultsExporter`; unit tests for round-trip |
| Java/GAMS environment detection | Auto-detection of `JAVA_HOME` + `IXMP_GAMS_PATH` in `run_messageix.py`; clear `[ERROR]` messages |
| Unit string rejections by ixmp | `KNOWN_UNIT_MAP` pre-processing + retry-with-`"-"` dynamic fallback |
| JPype JVM teardown errors | `sys.unraisablehook` override in `run_messageix.py` suppresses known `AttributeError: 'NoneType'.IxException` |
| Type mismatch on year columns | `_normalize_year_cols()` in `ScenarioDataWrapper.par()` casts `object` → `int64` |
| Large file performance | Virtual table view; background threads for I/O |
| Cross-platform Qt issues | Primary target Windows 10/11; CI on Windows |

---

## 10. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial draft |
| 1.1 | 2026-01-16 | Added logging layer, deferred Configurations Manager, testing strategy |
| 2.0 | 2026-03-05 | Full rewrite to reflect implemented state: PyQt5 (not PySide6), actual component list, solver pipeline, DataFileManager Excel support, ScenarioDataWrapper year normalization, WarningAnalyzer, ResultsExporter, phase status |
