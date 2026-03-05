# Product Requirements Document: MESSAGEix Data Manager

**Version**: 1.2
**Last Updated**: March 2026
**Status**: Active — Phases 1–3 complete, Phase 4 in progress

---

## 1. Executive Summary

### 1.1 Product Overview
The MESSAGEix Data Manager is a desktop application that streamlines the workflow of energy systems modelers working with the MESSAGEix framework. It provides an intuitive graphical interface for viewing and editing input parameters, executing model runs, and analyzing results through interactive visualizations.

### 1.2 Problem Statement
Working with MESSAGEix currently requires:
- Manual editing of Excel files with complex parameter structures
- Command-line execution of solvers
- Separate tools for result analysis and visualization
- Difficulty tracking changes and comparing multiple scenario runs

This fragmented workflow leads to inefficiencies, errors, and barriers to adoption for non-technical users.

### 1.3 Objectives
- Reduce time to configure and execute MESSAGEix models
- Enable non-programmers to work effectively with MESSAGEix
- Provide immediate visual feedback on model results
- Facilitate scenario comparison and sensitivity analysis

---

## 2. User Personas

### 2.1 Primary Persona: Energy Systems Analyst
- **Background**: PhD or Master's in energy/environmental engineering
- **Technical Skills**: Moderate programming (Python basics), strong Excel
- **Goals**: Run multiple scenarios, compare policy impacts, create visualizations for reports
- **Pain Points**: Command-line intimidation, time-consuming data preparation, difficulty tracking parameter changes

### 2.2 Secondary Persona: Research Manager
- **Background**: Senior researcher overseeing modeling projects
- **Technical Skills**: Limited programming, strategic thinker
- **Goals**: Review model configurations, validate results, make quick adjustments
- **Pain Points**: Dependency on technical staff, lack of visibility into model parameters

---

## 3. User Stories

### 3.1 Input Management
- As an analyst, I want to load an Excel input file and see all parameters in a structured view, so I can quickly understand the model configuration ✅
- As an analyst, I want to edit parameter values in a validated form, so I can avoid syntax errors and invalid data ✅
- As an analyst, I want to search and filter parameters, so I can quickly find relevant data in large models ✅
- As an analyst, I want to save my changes back to Excel format, so I can maintain compatibility with existing workflows ✅
- As an analyst, I want to handle several configurations and quickly move from one configuration to another ✅

### 3.2 Model Execution
- As an analyst, I want to trigger the solver with one click, so I don't need to use the command line ✅
- As an analyst, I want to see real-time progress and logs during solving, so I know the status of long-running models ✅
- As an analyst, I want to be notified when the solver completes (and see a warning summary), so I can review issues ✅
- As an analyst, I want solver results automatically loaded into the parameter tree ✅

### 3.3 Results Analysis
- As an analyst, I want to load result Excel files and see key metrics immediately ✅
- As an analyst, I want to create interactive charts of energy flows, capacity, costs, and emissions ✅
- As an analyst, I want to export data to CSV/Excel for further analysis ✅
- As an analyst, I want solver results assigned to the correct scenario in the file navigator ✅

### 3.4 Scenario Comparison
- As an analyst, I want to load results from multiple configurations simultaneously ✅
- As an analyst, I want to see interactive visualizations of scenarios

---

## 4. Functional Requirements

### 4.1 Input File Management ✅ IMPLEMENTED

#### FR-1.1: Load Input File
- Load MESSAGEix Excel input files (.xlsx, .xls) ✅
- Validate file structure; display errors for incorrect format ✅
- Parse all sheets: sets, parameters, mappings ✅

#### FR-1.2: Parameter Viewing
- Display parameters in a hierarchical tree view organized by category ✅
- Tabular view for each parameter with all dimensions visible ✅
- Graphical (chart) view for each parameter ✅
- Search functionality across parameter names ✅
- Show parameter metadata (units, dimensions, descriptions) ✅

#### FR-1.3: Parameter Editing
- Inline editing for parameter values with validation ✅
- Highlight modified cells and track change history ✅
- Undo/redo functionality ✅
- Bulk operations (copy/paste via clipboard) ✅

#### FR-1.4: Save Modified Input
- Save changes back to Excel format preserving original structure ✅
- Support "Save As" to create new scenarios ✅

#### FR-1.5: Configuration Management
- Manage multiple named scenarios ✅
- Assign input, data, and results files to scenarios ✅
- Switch between scenarios ✅
- Session persistence across restarts ✅

### 4.2 Model Execution ✅ IMPLEMENTED

#### FR-2.1: Solver Configuration
- Detect installed GAMS and available LP solvers (GLPK, CPLEX, Gurobi) ✅
- Allow selection of solver via dialog ✅
- Validate JAVA_HOME / GAMS environment before execution ✅

#### FR-2.2: Solver Execution
- Execute MESSAGEix solver in a background thread (no UI freeze) ✅
- Capture and display stdout/stderr in real-time console ✅
- Allow cancellation of running solve ✅
- Handle solver errors gracefully with user-friendly messages ✅
- Auto-load solver result Excel after successful run ✅
- Show warning summary dialog with auto-fix suggestions for unit errors ✅

#### FR-2.3: Result File Handling
- Solver output Excel (var_* / equ_* sheets) loaded via DataFileManager ✅
- Result file linked to scenario in file navigator ✅
- Unit validation errors auto-corrected during ixmp loading ✅

### 4.3 Results Analysis ✅ IMPLEMENTED

#### FR-3.1: Load Results
- Load solver result Excel (var_* / equ_* long-format sheets) via DataFileManager ✅
- Load wide-format results Excel via ResultsAnalyzer ✅
- Parse into Parameter objects with correct result_type metadata ✅

#### FR-3.2: Key Metrics Dashboard
- Electricity generation, capacity, LCOE, cost breakdown ✅
- Emissions by type, sector, fuel ✅
- Primary/final energy balance ✅
- Energy prices by level and sector ✅
- Buildings, industry, transport sector energy use ✅

#### FR-3.3: Interactive Visualizations
- Stacked bar/area charts for energy generation and capacity ✅
- Line charts for time series (emissions, costs) ✅
- All charts interactive (zoom, pan, hover tooltips) ✅
- Legend tooltips with deciphered technology/commodity names ✅

#### FR-3.4: Data Export
- Export filtered parameter data to CSV/Excel ✅

### 4.4 Scenario Comparison ✅ PARTIAL

#### FR-4.1: Multi-File Loading
- Load multiple scenarios simultaneously ✅
- File navigator shows each scenario's input/data/results files ✅

#### FR-4.2: Comparative Visualizations
- Overlay charts from multiple scenarios — planned

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **NFR-1.1**: Application startup < 10 seconds ✅
- **NFR-1.2**: UI response < 200ms for interactions ✅
- **NFR-1.3**: Support files up to 200MB ✅

### 5.2 Usability
- **NFR-2.1**: Search in parameter list and data table ✅
- **NFR-2.2**: All functionality accessible within 3 clicks ✅
- **NFR-2.3**: Tooltips for parameter names and code deciphering ✅
- **NFR-2.4**: Keyboard shortcuts (Ctrl+Z undo, Ctrl+F find, etc.) ✅

### 5.3 Reliability
- **NFR-3.1**: Graceful recovery from solver crashes ✅
- **NFR-3.2**: Session auto-restored on restart ✅
- **NFR-3.3**: Validate user inputs before processing ✅

### 5.4 Compatibility
- **NFR-4.1**: Windows 10/11 ✅ (primary platform)
- **NFR-4.2**: Compatible with MESSAGEix 3.0+ / ixmp ✅
- **NFR-4.3**: Python 3.8+ ✅

### 5.5 Maintainability
- **NFR-5.1**: Modular architecture with clear layer separation ✅
- **NFR-5.2**: Comprehensive logging ✅
- **NFR-5.3**: ~591 tests; target coverage > 70% ✅

---

## 6. Technology Stack

### 6.1 Implemented Stack

| Component | Technology |
|-----------|-----------|
| GUI Framework | **PyQt5** |
| Data Processing | **pandas**, **openpyxl** |
| Visualization | **Plotly** (rendered in `QWebEngineView`) |
| Solver Bridge | **ixmp** + **JPype** (Java 11+ required) |
| LP Solver | **GAMS** with GLPK / CPLEX / Gurobi |
| Testing | **pytest**, **pytest-qt** |
| Session Storage | JSON files via `session_manager.py` |

### 6.2 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  UI Layer (PyQt5)                   │
│  MainWindow · FileNavigator · ParameterTree         │
│  DataDisplayWidget · ChartWidget · Dashboards       │
├─────────────────────────────────────────────────────┤
│               Logic / Managers Layer                │
│  InputManager · DataFileManager · ResultsAnalyzer   │
│  SolverManager · SolverWorker · ScenarioLoader      │
│  ResultsExporter · WarningAnalyzer · SessionManager │
├─────────────────────────────────────────────────────┤
│           Analysis Layer (src/analysis/)            │
│  ElectricityAnalyzer · EmissionsAnalyzer            │
│  EnergyBalanceAnalyzer · FuelAnalyzer               │
│  SectorAnalyzer · PriceAnalyzer                     │
├─────────────────────────────────────────────────────┤
│                  Data Layer                         │
│  Excel I/O (openpyxl/pandas) · ixmp HSQLDB         │
│  JSON session files                                  │
└─────────────────────────────────────────────────────┘
```

---

## 7. User Interface

### 7.1 Main Layout

```
┌──────────────────────────────────────────────────────────┐
│  [File] [Edit] [Model] [View] [Help]            [?][□][X]│
├──────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌────────────────────────────────┐│
│  │  File Navigator  │  │   Parameter Tree (left)        ││
│  │                  │  │   + Data Table / Chart (right) ││
│  │  Scenario A      │  │                                ││
│  │  ├ Input file    │  │  [Search bar]                  ││
│  │  ├ Data file     │  │  ▾ Category                    ││
│  │  └ Results file  │  │    ▸ parameter_name            ││
│  │                  │  │                                ││
│  │  Scenario B ...  │  │  [Table / Chart / Dashboard]   ││
│  └──────────────────┘  └────────────────────────────────┘│
├──────────────────────────────────────────────────────────┤
│  Console output                                          │
├──────────────────────────────────────────────────────────┤
│  Status bar                                              │
└──────────────────────────────────────────────────────────┘
```

### 7.2 Key Screens

#### Input Editor
- Left: Parameter tree with search; filtered by category
- Center: Pivot table — dimensions as rows/columns, `value` or `lvl` cells
- Top toolbar: Save, Undo/Redo, Filter, Decipher Names, Advanced controls
- Bottom: Find widget (Ctrl+F)

#### Solver Console
- Real-time stdout/stderr streamed from `run_messageix.py` subprocess
- Warning Summary Dialog (non-modal) shown on completion if warnings detected
- One-click unit auto-fix from warning dialog → navigates to parameter

#### Results Dashboard
- Postprocessing Dashboard: electricity generation, LCOE, emissions, energy balance, sector/fuel use
- Results File Dashboard: charts from wide-format result files
- Input File Dashboard: parameter coverage matrix, set distributions

---

## 8. Data Formats

### 8.1 Input Excel Format
- Standard MESSAGEix Excel structure
- Sheets: sets (`set_*`), parameters (`par_*`), mapping sets
- Parsed by `InputManager` using `ParsingStrategy` subclasses

### 8.2 Solver Result Excel Format
- Sheets named `var_<NAME>` and `equ_<NAME>` (long format)
- Written by `ResultsExporter` after `scenario.solve()`
- Loaded by `DataFileManager._load_excel_data()`

### 8.3 Data ZIP Format
- Archive of CSV files named `set_*.csv`, `par_*.csv`, `var_*.csv`, `equ_*.csv`
- Loaded by `DataFileManager._load_zipped_csv_data()`

### 8.4 Export Formats
- Data: CSV, Excel
- Charts: PNG, SVG (via Plotly)

---

## 9. Development Phases

### Phase 1: MVP — Single-Scenario Core ✅ COMPLETE
- Main window, file navigator, scenario management
- Input Excel loading and parameter tree
- Table view and basic chart visualization
- Solver execution with console output
- Session persistence

### Phase 2: Input Editing & Validation ✅ COMPLETE
- Editable table with inline validation
- Undo/redo via Command pattern
- Save/Save-As, parameter search and filtering
- Name deciphering for codes → display names

### Phase 3: Advanced Visualization & Solver Integration ✅ COMPLETE
- Domain-specific postprocessed dashboards (electricity, emissions, energy balance, fuels, sectors, prices)
- Full MESSAGEix solver pipeline (ScenarioLoader → ixmp → GAMS → ResultsExporter)
- Solver warning analysis with unit auto-fix
- Solver results auto-loaded into parameter tree
- Search in parameter list and data table

### Phase 4: Multi-Scenario Comparison 🚧 IN PROGRESS
- Multiple scenarios in file navigator ✅
- Comparative visualizations (overlay/delta) — planned
- Scenario analysis tools — planned

### Phase 5: Stabilization & Release — PLANNED
- Cross-platform testing (macOS, Linux)
- Documentation and packaging
- Performance optimization for large files

---

## 10. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| ixmp/MESSAGEix API changes | High | Abstract via `ScenarioLoader`; unit tests for round-trip |
| Java/GAMS environment setup | High | Auto-detection of `JAVA_HOME` and `IXMP_GAMS_PATH`; clear error messages |
| Large file performance | High | Virtual/paginated table view; background loading threads |
| Unit validation failures | Medium | `KNOWN_UNIT_MAP` + dynamic retry-with-`"-"` fallback |
| Cross-platform Qt issues | Medium | CI testing; primary target is Windows |

---

## 11. Appendices

### Appendix A: Glossary
- **MESSAGEix**: Open-source framework for integrated assessment modeling
- **ixmp**: Infrastructure for message_ix; provides the Platform and Scenario API
- **GAMS**: General Algebraic Modeling System; used as the LP solver backend
- **Solver**: LP optimization engine (GLPK, CPLEX, Gurobi)
- **Parameter**: Input data defining the model (costs, demands, constraints)
- **Variable**: Result data calculated by the solver (var_ACT, var_CAP, etc.)
- **Equation**: Constraint dual values from the solver (equ_COMMODITY_BALANCE, etc.)
- **Scenario**: A named configuration with associated input, data, and results files

### Appendix B: References
- MESSAGEix Documentation: https://docs.messageix.org/
- IIASA Energy Program: https://iiasa.ac.at/energy

### Appendix C: Revision History
| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-01 | Initial draft |
| 1.0 | 2026-01-16 | Architecture and phase plan |
| 1.2 | 2026-03-05 | Updated to reflect implemented state; corrected tech stack to PyQt5; added solver pipeline, warning analyzer, DataFileManager Excel support |
