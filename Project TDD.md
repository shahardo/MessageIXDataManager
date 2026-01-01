# Technical Design Document: message_ix Data Manager

**Version**: 1.1  
**Date**: January 16, 2026  
**Author**: Grok (based on PRD review and improvements)  
**Status**: Draft  

**Changes from v1.0**:
- Added centralized logging layer with database persistence for all major operations
- Deferred full Configurations Manager (backend + UI) to a dedicated later phase to prioritize single-scenario stability first
- Added comprehensive testing strategy with emphasis on unit and integration testing

## 1. Introduction

### 1.1 Purpose
This Technical Design Document (TDD) translates the Product Requirements Document (PRD) for the message_ix Data Manager into a concrete technical blueprint. It defines the system architecture, key components, data models, technology decisions, and phased implementation plan.

### 1.2 Scope
The system is a cross-platform desktop application that enables energy systems modelers to:
- Load, view, edit, and save message_ix Excel input files
- Configure and execute model solves
- Load, analyze, and visualize results
- Manage multiple configurations and compare scenarios

The design prioritizes Excel round-trip compatibility, validation, performance with large files, rich interactive visualizations, auditability via logging, and testability.

### 1.3 Key Decisions
- **GUI Framework**: PySide6 (Qt for Python) – native performance, seamless Python integration with message_ix/ixmp, and embedded web views.
- **Excel Handling**: openpyxl + pandas.
- **Visualization**: Plotly.py (offline) → HTML rendered in QWebEngineView.
- **Execution**: Subprocess with configurable solve scripts.
- **Storage**: SQLite for metadata, history, configurations, and logs; model data remains file-based.
- **Logging**: Centralized Python logging with custom SQLite handler for persistence.

## 2. High-Level Architecture 

**Key Connections**:
- UI Layer → Logic Layer → Data Layer (primary flow)
- Configurations Manager ↔ SQLite
- Input Manager ↔ Excel I/O
- Solver Manager ↔ Subprocess
- Results Analyzer ↔ Excel I/O
- Visualization Engine → Results Analyzer
- All core managers (Input, Solver, Results, Configurations) → Logging Manager → SQLite
- Optional API → Input Manager / Results Analyzer (dashed/loose coupling)

### 2.1 Layer Responsibilities
- **UI Layer**: Responsive layout, editors, charts, console.
- **Logic Layer**: Workflow orchestration, state management, logging.
- **Data Layer**: I/O, execution, persistent storage.

## 3. Component Details

### 3.1 Input Manager
- Parses Excel into in-memory ScenarioData.
- Provides tree view, grid editing, search/filter.
- Validation, change tracking, undo/redo.
- Save with backup/compaction.

### 3.2 Solver Manager
- Environment detection, solver configuration.
- Subprocess execution with real-time streaming, cancellation.
- Error handling and run history.

### 3.3 Results Analyzer
- Parses result Excel, computes derived metrics.
- Feeds Visualization Engine.

### 3.4 Visualization Engine
- Plotly figure generation (stacked area, bar, line, Sankey, etc.).
- Interactive HTML rendering, multi-scenario overlay/delta.
- Export support.

### 3.5 Configurations Manager 
- Manages multiple named configurations (create, duplicate, rename, delete, switch).
- Each configuration stores input/output paths, metadata, description.
- Persisted in SQLite.
- UI integration: navigator panel, selectors in dashboard/comparison screens.

### 3.6 Logging Manager
- Centralized logging using Python `logging` module.
- Custom handler writes to SQLite `logs` table.
- Logs all significant operations:
  - File load/save (paths, success/failure)
  - Parameter edits (parameter, old/new value summary)
  - Solver start/end/cancellation (command, duration, status)
  - Validation errors, application warnings/errors
  - Configuration changes
- Levels: DEBUG, INFO, WARNING, ERROR.
- Optional UI view for recent logs / audit trail.

## 4. Data Models

### 4.1 Persistent Data (SQLite Schema)

```sql
CREATE TABLE configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    input_path TEXT,
    output_path TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE execution_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id INTEGER REFERENCES configurations(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    command TEXT,
    status TEXT,
    log_text TEXT,
    duration_seconds REAL
);

CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,          -- DEBUG, INFO, WARNING, ERROR
    category TEXT NOT NULL,       -- e.g., INPUT_LOAD, PARAMETER_EDIT, SOLVER_START
    message TEXT NOT NULL,
    details JSON,                 -- optional structured data (e.g., paths, diffs)
    config_id INTEGER REFERENCES configurations(id)
);
```

### 4.2 In-Memory Data Models

``` python
class Parameter:
    def __init__(self, name: str, df: pd.DataFrame, metadata: dict):
        self.name = name
        self.df = df.reset_index()  # columns: dim1, dim2, ..., value
        self.metadata = metadata  # {'units': str, 'desc': str, 'dims': list[str]}

class ScenarioData:
    def __init__(self):
        self.sets: dict[str, pd.Series] = {}        # set_name → values
        self.parameters: dict[str, Parameter] = {}  # par_name → Parameter
        self.mappings: dict[str, pd.DataFrame] = {} # optional
        self.modified: set[str] = set()             # tracked changed parameters
        self.change_history: list[dict] = []        # undo/redo stack

class Configuration:
    def __init__(self, db_row):
        self.id = db_row['id']
        self.name = db_row['name']
        self.description = db_row['description']
        self.input_path = db_row['input_path']
        self.output_path = db_row['output_path']
        self.input_data: Optional[ScenarioData] = None
        self.results_data: Optional[ScenarioData] = None
```

## 5. Key Technical Approaches

- **Excel Round-Trip**: Load with openpyxl (preserve formatting). Parse to pandas. On save, write back to original workbook template with optional compaction.
- **Validation**: Type checks, dimension consistency against sets. Optional ixmp/message_ix schema integration.
- **Large File Handling**: Lazy loading, virtual mode QTableView, background threads.
- **Undo/Redo**: Command pattern with change stack.
- **Multi-Scenario Comparison**: Hold multiple results in memory; Visualization Engine generates overlaid/delta figures.
- **Logging Integration**: All managers emit structured logs via Logging Manager.

## 6. Testing Strategy
### 6.1 Objectives

- Ensure reliability (target crash rate <0.1%)
- Validate correctness of Excel round-trip, validation, visualizations
- Achieve high confidence before each phase delivery

### 6.2 Approach

- **Unit Testing**: pytest for individual modules/classes. Target >85% coverage.
- **Integration Testing**: End-to-end workflows (load → edit → save → solve → visualize).
- **Property-Based Testing**: hypothesis for edge cases.
- **UI Testing**: pytest-qt for interactions; manual exploratory for visuals.
- **Cross-Platform Testing**: CI on Windows, macOS, Linux.
- **Performance Testing**: Profile large files against NFRs.
- **Regression Suite**: Automated tests covering all PRD functional requirements.
- **Tools**: pytest, pytest-cov, pytest-qt, GitHub Actions CI/CD.

Each module must pass full unit tests before integration. Phase gates require 100% passing tests and >80% coverage.

## 7. Development Phases (Revised)
### Phase 1: MVP – Single-Scenario Core (Months 1-3)
**Goal**: Stable single-scenario workflow (no multi-configuration support yet)
**Tasks**:

- Project setup, main window, navigator (simple recent-files handling)
- Basic Excel loading/parsing (read-only)
- Parameter tree + table view
- Solver execution with console
- Results loading + 3 basic Plotly charts in dashboard
- Initial Logging Manager implementation

**Deliverable**: Prototype for single scenario

### Phase 2: Input Editing & Validation (Months 4-5)
**Goal**: Full editable input workflow
**Tasks**:

- Editable grid with validation, undo/redo
- Save/Save-As, backup, compaction
- Search/filter, metadata panel
- Intensive unit/integration testing

**Deliverable**: Beta with robust editing

### Phase 3: Advanced Visualization & Dashboard (Months 6-7)
**Goal**: Comprehensive single-scenario analysis
**Tasks**:

- Full chart library + interactivity
- Customizable dashboard, exports
- Performance optimizations
- Logging of visualization actions
- Full test coverage for visualization engine

**Deliverable**: Feature-complete single scenario

### Phase 4: Configurations Management & Multi-Scenario Comparison (Months 8-9)
**Goal**: Enable multi-configuration workflow and comparison
**Tasks**:

- Implement Configurations Manager (SQLite backend + UI integration)
- Multi-configuration loading/switching
- Comparative visualizations (overlay, delta, tables)
- Configuration metadata/description handling
- Logging of configuration operations
- End-to-end integration testing of multi-scenario flows

**Deliverable**: Release Candidate with full PRD scope

### Phase 5: Stabilization & Release (Month 10)
**Goal**: Production-ready v1.0
**Tasks**:

- Bug fixes, performance tuning
- Comprehensive testing (regression, cross-platform)
- Documentation, packaging (PyInstaller)
- Final audit of logging completeness

**Deliverable**: v1.0 release

## 8. Risks & Mitigations

- **Delayed multi-configuration features**: Mitigated by clear single-scenario MVP first; validates core before complexity.
- **Incomplete logging coverage**: Mitigated by defining log points early and testing via log table queries.
- **Large file performance**: Use pagination/virtual views; test with 200MB files early.
- **Excel format changes**: Abstract I/O layer; add unit tests for round-trip.
- **Solver integration**: Provide default solve script templates; extensive error parsing.
- **Cross-platform Qt issues**: CI testing on all platforms from Phase 1.

