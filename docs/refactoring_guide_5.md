# Refactoring Guide 5 - Consolidation & Quality Assurance

## 1. Executive Summary

Following the "Operation De-Monolith" (Guide 4), the codebase is in a transitional state. While the UI layer is significantly cleaner, the business logic layer—specifically results processing and analysis—remains tightly coupled within `ResultsAnalyzer` and `ResultsPostprocessor`.

This phase focuses on **completing the architectural transition**, separating data loading from business logic, standardizing the Dashboard hierarchy, and establishing a rigorous quality assurance baseline.

**Primary Goals:**
1. Complete the Strategy Pattern implementation for `ResultsAnalyzer`.
2. Decompose the monolithic `ResultsPostprocessor` (~1600 lines) into domain-specific analyzers.
3. Standardize all Dashboards on `BaseDashboard`.
4. Eliminate dead code and enforce strict separation of concerns in `DataDisplayWidget`.

---

## 2. Critical Refactoring Tasks

### 2.1 Results Analyzer Decomposition (Priority: HIGH)

**Current State:**
`src/managers/results_analyzer.py` (~900 lines) handles file parsing, summary statistics, AND complex post-processing calculations like LCOE and dashboard metrics. It violates the Single Responsibility Principle.

**Action Plan:**
1.  **Implement Parsing Strategies**:
    -   Ensure `ResultsAnalyzer` uses `ResultParsingStrategy` from `src/utils/parsing_strategies.py`.
    -   Remove legacy parsing methods: `_parse_variables_section`, `_parse_equations_section`.

2.  **Extract Business Logic**:
    -   Move `calculate_dashboard_metrics` and `calculate_electricity_cost_breakdown` out of `ResultsAnalyzer` and into the new analysis modules (see 2.2).

**Target:** Reduce `results_analyzer.py` to < 300 lines (purely a data loader).

### 2.2 Results Postprocessor Decomposition (Priority: HIGH)

**Current State:**
`src/managers/results_postprocessor.py` is a ~1600 line God Class handling Electricity, Emissions, Energy Balance, Fuels, Sectoral Use, and Prices. It shares overlapping logic with `ResultsAnalyzer` (e.g., LCOE calculations).

**Action Plan:**
1.  **Create `src/analysis/` Package**:
    -   `base_analyzer.py`: Base class containing shared helpers (`_group`, `_multiply_df`, `_model_output`, `_add_history`).
    -   `electricity_analyzer.py`: Capacity, generation, usage, LCOE, and cost breakdown logic.
    -   `emissions_analyzer.py`: Emissions by sector, type, and fuel.
    -   `energy_balance_analyzer.py`: Primary/Final energy, imports/exports.
    -   `fuel_analyzer.py`: Gas, Oil, Coal, Biomass supply and usage.
    -   `sector_analyzer.py`: Buildings, Industry, Transport metrics.
    -   `price_analyzer.py`: Energy prices and indices.

2.  **Refactor `ResultsPostprocessor`**:
    -   Transform it into a facade/orchestrator that initializes and calls these specific analyzers.
    -   Ensure `ResultsAnalyzer` delegates cost/metric calculations to these new analyzers instead of doing it itself.

**Target:** Split `results_postprocessor.py` into 6-7 focused files, each < 300 lines.

### 2.3 Dashboard Hierarchy Standardization (Priority: MEDIUM)

**Current State:**
`BaseDashboard` exists but isn't fully utilized. `InputFileDashboard` and `ResultsFileDashboard` contain duplicated tab management and HTML generation code.

**Action Plan:**
1.  **Refactor `InputFileDashboard`**:
    -   Inherit from `BaseDashboard`.
    -   Use `_create_tabs()` for Overview, Technologies, etc.
    -   Remove manual `uic.loadUi` calls if possible, or integrate them cleanly.

2.  **Refactor `ResultsFileDashboard`**:
    -   Inherit from `BaseDashboard`.
    -   Use `DashboardChartMixin` for chart rendering logic.
    -   Delegate metric calculations to the new `MetricsCalculator`.

### 2.4 Data Display Logic Separation (Priority: MEDIUM)

**Current State:**
`DataDisplayWidget` (~1200 lines) still contains significant data transformation logic (pivoting, filtering) mixed with UI handling.

**Action Plan:**
1.  **Verify `DataTransformer` Usage**:
    -   Ensure `src/utils/data_transformer.py` handles all dataframe reshaping.
    -   Remove `_transform_to_advanced_view`, `_perform_pivot`, `_apply_filters` from `DataDisplayWidget` if they duplicate `DataTransformer`.
2.  **Cleanup**:
    -   Remove unused methods identified by `vulture`.

---

## 3. Configuration & Infrastructure

### 3.1 Unified Configuration Management (Priority: LOW)

**Current State:**
Settings are scattered between `UserPreferences` (QObject), `QSettings` (in `SessionManager`), and hardcoded values.

**Action Plan:**
1.  Create `src/managers/configuration_manager.py`.
2.  Centralize:
    -   Solver executable paths.
    -   Default directories.
    -   UI theme preferences.
    -   Logging levels.

---

## 4. Code Quality & Cleanup

### 4.1 Dead Code Removal (Priority: HIGH)

**Current State:**
The extraction of controllers and managers left behind unused methods in `MainWindow` and `BaseDataManager`.

**Action Plan:**
1.  **Run Vulture**: Execute static analysis to confirm unused code.
2.  **Remove Legacy Methods**:
    -   `MainWindow`: `_load_data_file`, `_load_zipped_csv_data`, `_open_input_file` (legacy versions).
    -   `DataDisplayWidget`: `_get_current_filters` (if moved).
    -   `UIStyler`: Unused styling methods.

### 4.2 Type Hinting & Docstrings

**Action Plan:**
1.  Enforce `mypy` checks on `src/core` and `src/managers`.
2.  Ensure all public methods in new classes have Google-style docstrings.

---

## 5. Implementation Roadmap

| Phase | Task | Status | Files Affected |
|-------|------|--------|----------------|
| **5.1** | **Analyzer Extraction** | ✅ DONE | `src/managers/results_postprocessor.py` → facade; `src/analysis/` package created |
| **5.2** | **ResultsAnalyzer Cleanup** | ✅ DONE | `src/managers/results_analyzer.py` — 941 → 310 lines, pure data loader |
| **5.3** | **Dashboard Cleanup** | ✅ DONE | `InputFileDashboard`, `ResultsFileDashboard` both inherit `BaseDashboard` |
| **5.4** | **Data Display Cleanup** | ⬜ PENDING | `src/ui/components/data_display_widget.py` |
| **5.5** | **Dead Code Purge** | ⬜ PENDING | `src/ui/main_window.py` |

## 6. Verification Checklist

- [x] `ResultsAnalyzer` does not contain LCOE or Metric calculation logic.
- [x] `ResultsPostprocessor` delegates to classes in `src/analysis/`.
- [x] `InputFileDashboard` and `ResultsFileDashboard` inherit from `BaseDashboard`.
- [ ] `DataDisplayWidget` delegates transformation to `DataTransformer`.
- [ ] `vulture src/` returns minimal/zero confidence results for dead code.
- [x] Application loads results and displays cost breakdown correctly using `ElectricityAnalyzer`.