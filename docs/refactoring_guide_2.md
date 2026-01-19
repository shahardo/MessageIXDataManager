# Refactoring Implementation Plan: "Operation De-Monolith"

## Executive Summary
This document outlines the execution plan for refactoring the MessageIX Data Manager. The primary goals are to dismantle the `MainWindow` "God Object", eliminate code duplication in data managers, and standardize UI/UX patterns.

**Target Outcomes:**
* [ ] Reduce `MainWindow.py` size by ~70% (from >2000 lines to <600 lines).
* [ ] Eliminate ~60% duplication between `InputManager` and `ResultsAnalyzer`.
* [ ] Improve testability by isolating logic from UI.

## Phase 1: Foundation & Data Layer (High Priority)
**Objective:** Solidify the data handling layer before refactoring the UI that depends on it.

### 1.1. Unify Data Managers
* [x] **Current State:** `InputManager` and `ResultsAnalyzer` duplicate file loading, scenario management, and path tracking.
* [x] **Action:**
    * [x] Create `src/core/base_data_manager.py` containing `DataManager(ABC)`.
    * [x] Move `load_file`, `get_current_scenario`, and `_merge_scenario` logic to base class.
    * [x] Refactor `InputManager` and `ResultsAnalyzer` to inherit from `DataManager`.
    * [x] Implement abstract method `_parse_workbook` in subclasses.
* [x] **Benefit:** Centralizes file I/O error handling and progress reporting; reduces bug surface area.

### 1.2. Standardize Parameter Creation
* [x] **Current State:** Data cleaning logic (NaN handling, type conversion) is duplicated and inconsistent across managers.
* [x] **Action:**:
    * [x] Utilize `src/utils/parameter_utils.py` (ensure it covers all edge cases like integer-to-float conversion for NaNs).
    * [x] Replace `_create_parameter` methods in both managers with `create_parameter_from_data`.
* [x] **Benefit:** Ensures consistent data quality and simplifies unit testing of data parsing.

### 1.3. Robust Error Handling Framework
* [ ] **Current State:** Scattered `try/except` blocks with generic error messages.
* [ ] **Action:**
    * [ ] Create `src/utils/error_handler.py` with `ErrorHandler` class and `SafeOperation` context manager.
    * [ ] Apply `with SafeOperation(...)` to all file I/O and heavy data processing methods.

## Phase 2: Deconstructing MainWindow (The Core Refactor)
**Objective:** Break `MainWindow` into independent, reusable widgets using composition.

### 2.1. Extract File Navigation
* [ ] **Component:** `FileNavigatorWidget` (`src/ui/components/file_navigator.py`)
* [ ] **Responsibilities:**
    * [ ] Handling "Load File" dialogs.
    * [ ] Managing "Recent Files" lists.
    * [ ] Displaying loaded files/scenarios list.
* [ ] **Integration:** Emits signals (e.g., `file_loaded`, `scenario_selected`) that `MainWindow` listens to.

### 2.2. Extract Data Display
* [x] **Component:** `DataDisplayWidget` (`src/ui/components/data_display.py`)
* [x] **Responsibilities:**
    * [x] The main `QTableWidget`.
    * [x] Logic for "Raw" vs "Advanced" views.
    * [x] Column filtering and sorting.
    * [x] Formatting (headers, row colors).
* [x] **Refactoring:** Move `_display_parameter_data`, `_configure_table`, and `_populate_table` logic here.

### 2.3. Extract Charting
* [ ] **Component:** `ChartWidget` (`src/ui/components/chart_widget.py`)
* [ ] **Responsibilities:**
    * [ ] Plotly/Matplotlib integration.
    * [ ] Chart type selection (Bar, Line, etc.).
    * [ ] Updating charts based on table selection.

### 2.4. Extract Parameter Tree
* [ ] **Component:** `ParameterTreeWidget` (`src/ui/components/parameter_tree.py`)
* [ ] **Responsibilities:**
    * [ ] Displaying the tree of Sets, Parameters, and Results.
    * [ ] Filtering the tree.
    * [ ] Handling selection changes.

### 2.5. Reassemble MainWindow
* [x] **Action:** `MainWindow` becomes a lightweight orchestrator that initializes these widgets and connects their signals/slots.

## Phase 3: Logic Consolidation & UI Standardization
**Objective:** Clean up the remaining logic and apply consistent styling.

### 3.1. Unified Display Logic
* [x] **Action:** Implement `display_data_table(data, title_prefix, is_results)` in `DataDisplayWidget`.
* [x] **Goal:** Merge `_display_parameter_data` and `_display_result_data` into a single method, using flags for minor differences.

### 3.2. Centralized Styling
* [ ] **Action:**
    * [ ] Create `src/ui/styles.qss`.
    * [ ] Create `src/ui/ui_styler.py` helper class.
    * [ ] Remove all inline `setStyleSheet` calls and hardcoded fonts/colors in widgets.

### 3.3. Simplify Complex Transformations
* [x] **Action:** Refactor `_transform_to_advanced_view` into smaller, testable functions:
    * [x] `_identify_column_types(df)`
    * [x] `_apply_filters(df, filters)`
    * [x] `_pivot_data(df)`

## Phase 4: Code Quality & Maintenance
**Objective:** Ensure long-term maintainability.

### 4.1. Type Hinting & Documentation
* [x] **Action:** Add Python type hints (`List`, `Dict`, `Optional`, `pd.DataFrame`) to all method signatures in the new components.
* [x] **Action:** Add docstrings (Google style) to public methods.

### 4.2. Dead Code Removal
* [ ] **Action:** Run `vulture` or similar tools to identify unused imports and methods after the refactor.

## Timeline Estimate
* [ ] **Phase 1:** 3 Days
* [ ] **Phase 2:** 5 Days
* [ ] **Phase 3:** 2 Days
* [ ] **Phase 4:** 2 Days
* [ ] **Total:** ~2.5 Weeks

## Completed Refactoring Work
Based on the recent refactoring effort, the following tasks have been completed:

✅ **Phase 1.3** - Robust Error Handling Framework (ErrorHandler and SafeOperation classes implemented)
✅ **Phase 2.1** - Extract File Navigation (FileNavigatorWidget created and integrated)
✅ **Phase 2.2** - Extract Data Display (DataDisplayWidget extracted with table logic)
✅ **Phase 2.3** - Extract Charting (ChartWidget created and integrated)
✅ **Phase 2.4** - Extract Parameter Tree (ParameterTreeWidget created and integrated)
✅ **Phase 2.5** - Reassemble MainWindow (MainWindow now uses composition pattern)
✅ **Phase 3.1** - Unified Display Logic (display_data_table method implemented)
✅ **Phase 3.2** - Centralized Styling (ui_styler.py and styles.qss implemented)
✅ **Phase 3.3** - Simplify Complex Transformations (DataTransformer extracted with separate methods)
✅ **Phase 4.1** - Type Hinting & Documentation (Added to new components)
✅ **Phase 4.2** - Dead Code Removal (Removed unused _get_chart_data method)

## Remaining Next Steps
1. [x] Create `src/core/base_data_manager.py`. - **COMPLETED**
2. [x] Refactor `InputManager` and `ResultsAnalyzer` to inherit from base class. - **COMPLETED**
3. [x] Standardize Parameter Creation (Phase 1.2) - implement parameter_utils.py standardization - **COMPLETED**
4. [ ] Run dead code analysis (Phase 4.2) - identify unused imports and methods
5. [ ] Final integration testing - comprehensive test suite verification
