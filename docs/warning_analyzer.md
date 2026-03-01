# Plan: Solver Warning Analysis & Fix Suggestions

## Context
When the MESSAGEix solver runs, warnings like "Warning: could not add parameter 'X': The unit 'million' does not exist" are printed as plain text in the console with no highlighting, no summary, and no guidance on how to fix them. The user wants the app to parse these warnings, explain what went wrong, and where possible suggest or apply fixes to the input data.

---

## Implementation Plan

### ✅ Step 1: Create `src/managers/warning_analyzer.py`

New module that:
- Defines `SolverWarning` dataclass with fields: `kind` ("parameter"|"set"|"unknown"), `name`, `raw_message`, `category`, `fix_description`, `fix_available`
- Defines `WarningAnalyzer` class with:
  - `parse_line(line: str) -> SolverWarning | None` — regex-matches known warning patterns
  - `_classify(warning: SolverWarning)` — categorizes by exception text:
    - **Unit not found**: matches `"does not exist in the database"` or `"unit.*not found"`
    - **No values supplied**: matches `"no parameter values supplied"`
    - **Duplicate entries**: matches `"duplicate"`
    - **Unknown**: everything else
  - `category_label(category)` — returns human-readable label
  - `KNOWN_UNIT_MAP: dict[str, str]` — maps common bad units to valid ixmp alternatives (e.g. `"million" → "1e6"`, `"Mt" → "Mt CO2"`)

**File**: `src/managers/warning_analyzer.py` ✅ implemented

---

### ✅ Step 2: Enhance `main_window._append_to_console()` with warning coloring

Modified `_append_to_console()` to detect warning lines and apply HTML color formatting in the `QTextEdit`:
- Lines matching `"Warning: could not add"` → **orange** (`#FFA500`)
- Lines matching `"[ERROR]"` → **red** (`#FF5555`)
- Lines matching `"solved successfully"` or solver completion → **green** (`#44BB44`)
- All other lines → default (no colour tag)

Also accumulates `SolverWarning` objects in `self._solver_warnings: List[SolverWarning]` during the run, reset at start of each solver run.

**File**: `src/ui/main_window.py` ✅ implemented
**Methods**: `_append_to_console()`, `_run_solver()` (reset `_solver_warnings`)

---

### ✅ Step 3: Create `src/ui/components/warning_summary_dialog.py`

New `WarningSummaryDialog(QDialog)` that:
- Shows a summary header: "Solver completed with N warning(s)"
- Has a `QTableWidget` with columns: **Type**, **Parameter/Set Name**, **Issue**, **Suggested Fix**, **Actions**
- Each row has a "Go to Parameter" button (`QPushButton`) that emits `navigate_requested(parameter_name: str)`
- For unit warnings where a known mapping exists: adds "Fix unit → 'X'" button emitting `autofix_requested(name, bad_unit, good_unit)`
- Has a bottom "Close" and "Copy to Clipboard" button

**File**: `src/ui/components/warning_summary_dialog.py` ✅ implemented

---

### ✅ Step 4: Show warning summary after solver finishes

In `main_window._on_solver_finished()`:
- After result-loading, checks `self._solver_warnings`
- If non-empty, shows `WarningSummaryDialog`
- `navigate_requested(name)` → `_navigate_to_parameter(name)`: uses `param_tree.findItems()` + `setCurrentItem()` to select the parameter
- `autofix_requested(name, bad_unit, good_unit)` → `_autofix_parameter_unit(...)`: patches the 'unit' column in `ScenarioData`, marks scenario modified

**File**: `src/ui/main_window.py` ✅ implemented
**Methods**: `_on_solver_finished()`, `_navigate_to_parameter()`, `_autofix_parameter_unit()`

---

### ✅ Step 5: Unit pre-validation in `scenario_loader.py`

Added unit remapping in `_prepare_parameter_df()`:
- Iterates `KNOWN_UNIT_MAP` and replaces matching values in the 'unit' column before calling `add_par()`
- Prevents the warning from ever appearing for common bad units like `"million"`, `"percent"`, etc.
- Logs an info message when a substitution is made

**File**: `src/managers/scenario_loader.py` ✅ implemented

---

## Critical Files

| File | Status |
|------|--------|
| `src/managers/warning_analyzer.py` | ✅ Created |
| `src/ui/components/warning_summary_dialog.py` | ✅ Created |
| `src/ui/main_window.py` | ✅ Modified |
| `src/managers/scenario_loader.py` | ✅ Modified |

---

## Verification

1. Run the solver with a known-bad input (e.g. a parameter with unit "million")
2. Confirm:
   - Warning lines appear **orange** in the console
   - After run finishes, a summary dialog appears listing the warning
   - "Go to Parameter" button navigates to that parameter in the table view
   - "Fix unit → '1e6'" button updates the unit in the DataFrame and marks scenario modified
3. Run solver with no warnings → confirm dialog does NOT appear
4. Test with "no parameter values supplied" warning → confirm correct suggestion shown
