# Scenario Comparison Feature — Development Plan

## Overview

Add a **Compare Scenarios** command that opens a dedicated comparison window. The window shows a synchronized parameter/variable tree for two selected scenarios, highlights common vs. scenario-exclusive items, and displays a side-by-side data table and comparison chart when a shared parameter is selected.

---

## User Story

1. User has two or more scenarios loaded in the main window.
2. User opens **Tools → Compare Scenarios…** (or keyboard shortcut).
3. A dialog prompts the user to pick **Scenario A** and **Scenario B** from the currently loaded scenarios.
4. The Comparison Window opens, showing:
   - **Left sidebar**: Parameter tree with the same sections, category icons, and sidebar navigation as the main window.
     - Parameters/variables present in **both** scenarios → normal appearance, selectable.
     - Parameters/variables present in **only one** scenario → grayed-out, italic, with a badge `[A]` or `[B]`, and **not selectable** (greyed, disabled).
   - **Main area**: When a shared parameter is selected, a split view shows:
     - A **comparison table**: merged DataFrame with one column per scenario plus Δ and Δ% columns, color-coded.
     - A **comparison chart**: grouped or overlaid Plotly chart rendering both scenarios simultaneously.

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ui/scenario_comparison_window.py` | Top-level `QMainWindow` for the comparison view |
| `src/ui/scenario_comparison_window.ui` | Qt Designer layout for the comparison window |
| `src/ui/components/comparison_parameter_tree.py` | `ComparisonParameterTreeWidget` — synchronized dual-scenario sidebar |
| `src/ui/components/comparison_data_widget.py` | `ComparisonDataWidget` — merged side-by-side table |
| `src/ui/components/comparison_chart_widget.py` | `ComparisonChartWidget` — grouped/overlaid Plotly chart |
| `src/ui/dialogs/scenario_selector_dialog.py` | `ScenarioSelectorDialog` — pick two scenarios from a list |
| `tests/test_comparison_parameter_tree.py` | Unit tests for tree merging logic |
| `tests/test_comparison_data_widget.py` | Unit tests for DataFrame merging and delta computation |

### Modified Files

| File | Change |
|------|--------|
| `src/ui/main_window.ui` | Add **Tools** menu with `actionCompare_Scenarios` |
| `src/ui/main_window.py` | Wire `actionCompare_Scenarios.triggered` → `_open_comparison_window()` |

---

## Phase 1 — Menu Entry & Scenario Selector Dialog [x]

### 1.1 Add Menu Action [x]

In `main_window.ui`, add a **Tools** top-level menu (insert after **Run**, before any future additions):

```xml
<widget class="QMenu" name="menuTools">
  <property name="title"><string>Tools</string></property>
  <addaction name="actionCompare_Scenarios"/>
</widget>
```

Action definition:
```xml
<action name="actionCompare_Scenarios">
  <property name="text"><string>Compare Scenarios…</string></property>
  <property name="shortcut"><string>Ctrl+Shift+C</string></property>
  <property name="toolTip"><string>Open the scenario comparison view</string></property>
</action>
```

Add action to menubar:
```xml
<addaction name="menuTools"/>
```

### 1.2 Wire in `main_window.py` [x]

```python
def _connect_signals(self):
    ...
    self.actionCompare_Scenarios.triggered.connect(self._open_comparison_window)

def _open_comparison_window(self):
    """Open the ScenarioSelectorDialog, then show ScenarioComparisonWindow."""
    scenarios = list(self.scenario_manager.get_all_scenarios().values())
    if len(scenarios) < 2:
        QMessageBox.information(
            self, "Compare Scenarios",
            "At least two loaded scenarios are required for comparison."
        )
        return
    dialog = ScenarioSelectorDialog(scenarios, parent=self)
    if dialog.exec_() == QDialog.Accepted:
        scenario_a, scenario_b = dialog.selected_scenarios()
        window = ScenarioComparisonWindow(scenario_a, scenario_b, parent=self)
        window.show()
        self._comparison_windows.append(window)  # keep reference alive
```

### 1.3 `ScenarioSelectorDialog` [x]

**File**: `src/ui/dialogs/scenario_selector_dialog.py`

```
┌─────────────────────────────────────────────────────────────┐
│  Compare Scenarios                                          │
│                                                             │
│  Scenario A                     Scenario B                  │
│  ┌───────────────────────┐      ┌───────────────────────┐  │
│  │ ▶ Model_Baseline      │      │   Model_Baseline       │  │
│  │   Model_ETS           │      │ ▶ Model_ETS            │  │
│  │   Model_HighDemand    │      │   Model_HighDemand     │  │
│  │   ...                 │      │   ...                  │  │
│  └───────────────────────┘      └───────────────────────┘  │
│                                                             │
│  [Cancel]                                     [Compare]    │
└─────────────────────────────────────────────────────────────┘
```

- Two `QListWidget` panels side by side, both populated with all loaded scenario names.
- User clicks one item in the left list (Scenario A) and one in the right list (Scenario B).
- Selected item in each list is highlighted; a `▶` marker indicates the active selection.
- **Compare** button is enabled only when both lists have a selection **and** the two selections differ.
- Selecting a scenario in one list does **not** remove it from the other list (both lists always show all scenarios), but if the same scenario is selected on both sides, the button remains disabled and a warning label reads *"Select two different scenarios."*
- `selected_scenarios() → tuple[Scenario, Scenario]`

Implementation notes:
```python
class ScenarioSelectorDialog(QDialog):
    def __init__(self, scenarios: list[Scenario], parent=None):
        ...
        self.list_a = QListWidget()   # left panel
        self.list_b = QListWidget()   # right panel
        for s in scenarios:
            self.list_a.addItem(s.name)
            self.list_b.addItem(s.name)
        self.list_a.currentRowChanged.connect(self._validate)
        self.list_b.currentRowChanged.connect(self._validate)

    def _validate(self):
        row_a = self.list_a.currentRow()
        row_b = self.list_b.currentRow()
        valid = (row_a >= 0 and row_b >= 0
                 and self.list_a.currentItem().text()
                     != self.list_b.currentItem().text())
        self.warning_label.setVisible(
            row_a >= 0 and row_b >= 0 and not valid
        )
        self.compare_button.setEnabled(valid)

    def selected_scenarios(self) -> tuple[Scenario, Scenario]:
        name_a = self.list_a.currentItem().text()
        name_b = self.list_b.currentItem().text()
        by_name = {s.name: s for s in self._scenarios}
        return by_name[name_a], by_name[name_b]
```

---

## Phase 2 — Comparison Window Layout [x]

### 2.1 `scenario_comparison_window.ui` [x] (implemented programmatically, no .ui file needed)

Overall layout mirrors the main window's left-sidebar + main-area structure:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Title bar: "Comparing: <Scenario A> vs <Scenario B>"                 │
├──────────────┬─────────────────────────────────────────────────────────┤
│  Section     │  [Scenario A name]           [Scenario B name]          │
│  sidebar     ├──────────────────────────────────────────────────────── │
│  (28px,      │  COMPARISON TABLE                                       │
│   icons)     │  ┌──────────────────────────────────────────────────┐  │
│              │  │ dim1 | dim2 | year | Value A | Value B | Δ | Δ%  │  │
│  Parameter   │  │ ...  | ...  | 2025 |  100    |  120    |+20|+20% │  │
│  tree        │  │ ...  | ...  | 2030 |  150    |  130    |-20|-13% │  │
│  (merged,    │  └──────────────────────────────────────────────────┘  │
│   synced)    ├──────────────────────────────────────────────────────── │
│              │  COMPARISON CHART                                       │
│              │  [Plotly grouped/overlaid chart]                        │
│              │                                                         │
└──────────────┴─────────────────────────────────────────────────────────┘
```

**Splitters**:
- Horizontal splitter: `[sidebar 300px] | [main area]`
- Vertical splitter in main area: `[table 60%] | [chart 40%]`

The sidebar itself uses the same two-pane layout as the main window:
- Left strip (28px): section icon buttons
- Right pane: `ComparisonParameterTreeWidget`

### 2.2 `ScenarioComparisonWindow` class [x]

```python
class ScenarioComparisonWindow(QMainWindow):
    def __init__(self, scenario_a: Scenario, scenario_b: Scenario, parent=None):
        super().__init__(parent)
        self.scenario_a = scenario_a
        self.scenario_b = scenario_b
        self._setup_ui()
        self._build_merged_tree()

    def _setup_ui(self): ...          # load .ui, set title, create splitters
    def _build_merged_tree(self): ... # populate ComparisonParameterTreeWidget
    def _on_parameter_selected(self, param_name: str): ...  # load and display data
```

---

## Phase 3 — Comparison Parameter Tree [x]

### 3.1 `ComparisonParameterTreeWidget` [x]

**File**: `src/ui/components/comparison_parameter_tree.py`

Extends or wraps `ParameterTreeWidget` logic. Does **not** inherit (to avoid overriding extensive internals); instead reuses the same helper methods via composition and mirrors the exact tree-building approach.

#### Merged Parameter Set

```python
@dataclass
class MergedParameter:
    name: str
    presence: Literal['both', 'a_only', 'b_only']
    row_count_a: Optional[int]
    row_count_b: Optional[int]
```

Building:
```python
names_a = set(scenario_a.data.get_parameter_names())
names_b = set(scenario_b.data.get_parameter_names())
# also include variables from each scenario's data
both    = names_a & names_b
a_only  = names_a - names_b
b_only  = names_b - names_a
```

#### Tree Item Styling Rules

| Presence | Foreground | Italic | Selectable | Badge |
|----------|-----------|--------|-----------|-------|
| `both`   | Default   | No     | Yes       | —     |
| `a_only` | Gray `#999` | Yes  | No (disabled) | ` [A]` appended to name |
| `b_only` | Gray `#999` | Yes  | No (disabled) | ` [B]` appended to name |

Implementation:
```python
item = QTreeWidgetItem([merged_param.name + badge])
if merged_param.presence != 'both':
    item.setForeground(0, QBrush(QColor('#999999')))
    font = item.font(0)
    font.setItalic(True)
    item.setFont(0, font)
    # Disable selection
    item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
```

#### Sections and Categories

Use the **same** section names, section icons, and category icons as `ParameterTreeWidget`:
- `_SECTION_ICONS` (📋 📊 ⚡ 📈 🗂)
- `_CATEGORY_ICONS` (🌿 🔒 ⚙ 💰 🏭 📈 🔧 ⏱ ⚡ 🏭 🔄 🗃 💨 🎯 💲 ⚡ ⚖ 🔄 🏘 🔥)
- Section sidebar (28px icon buttons) identical to main window

#### Categories

For shared parameters, show row counts from both scenarios:
```
inv_cost  (A: 48 rows, B: 52 rows)
```
For exclusive parameters, show only the source scenario count:
```
some_param [A]  (A: 30 rows)
```

#### Signals

```python
parameter_selected = pyqtSignal(str)   # emits param_name, only for 'both' items
section_selected   = pyqtSignal(str)   # same as original
```

#### Search

Full-text search with yellow highlight, identical to `ParameterTreeWidget` — but grayed items remain grayed even when matched.

---

## Phase 4 — Comparison Data Widget [x]

### 4.1 `ComparisonDataWidget` [x]

**File**: `src/ui/components/comparison_data_widget.py`

#### Data Merging

Given two `Parameter` objects (`param_a`, `param_b`) with the same name:

```python
def _merge_parameters(param_a: Parameter, param_b: Parameter,
                       label_a: str, label_b: str) -> pd.DataFrame:
    """
    Merge two long-format DataFrames on dimension columns.
    Returns wide DataFrame with columns:
        [dim1, dim2, ..., dimN, value_A, value_B, delta, delta_pct]
    """
    dim_cols = [c for c in param_a.df.columns if c != 'value']
    df_a = param_a.df.rename(columns={'value': f'value_{label_a}'})
    df_b = param_b.df.rename(columns={'value': f'value_{label_b}'})
    merged = pd.merge(df_a, df_b, on=dim_cols, how='outer')
    merged['Δ'] = merged[f'value_{label_b}'] - merged[f'value_{label_a}']
    merged['Δ%'] = (merged['Δ'] / merged[f'value_{label_a}'].replace(0, pd.NA)) * 100
    return merged
```

#### Table Display

- Columns: `[dim1, dim2, …, Value A, Value B, Δ, Δ%]`
- **Color coding** applied per row to the Δ and Δ% cells:
  - Δ > 0 → light green background (`#d4edda`)
  - Δ < 0 → light red background (`#f8d7da`)
  - Δ = 0 or NaN → default background
- Rows where a value exists in only one scenario: the missing side shows `—` in italic gray.
- Column headers show scenario names: `"Value (Model_Baseline)"`, `"Value (Model_ETS)"`.

#### Pivot Mode

A **Pivot** control (same as `DataDisplayWidget`'s advanced mode) lets users choose which dimension to pivot on (e.g., `year_act`). When pivoted:
- Year columns appear as: `2025 (A) | 2025 (B) | …` or with a color-coded diff suffix.

#### Controls Bar

```
[Scenario A label]  [Scenario B label]  |  [Pivot by: ComboBox ▼]  [Show Δ only ☐]
```

- **Show Δ only**: hides the `Value A` and `Value B` columns; shows only `Δ` and `Δ%`.
- **Year Range**: reuse `UserPreferences` min/max year filtering.

---

## Phase 5 — Comparison Chart Widget [x]

### 5.1 `ComparisonChartWidget` [x]

**File**: `src/ui/components/comparison_chart_widget.py`

Wraps a `QWebEngineView` (same as `ChartWidget`) and renders Plotly HTML.

#### Chart Modes (toggle in toolbar)

| Mode | Description |
|------|-------------|
| **Grouped Bar** | Side-by-side bars for each category/year pair: A (solid) vs B (hatched/lighter) |
| **Overlaid Line** | Two line series per technology, dashed for B |
| **Delta Bar** | Single bar chart showing `Δ` values; green for positive, red for negative |

#### Default Rendering (Grouped Bar)

```python
traces = []
for tech in technologies:
    traces.append(go.Bar(
        name=f"{tech} ({label_a})",
        x=years, y=values_a[tech],
        marker_color=COLORS[tech],
        legendgroup=tech,
    ))
    traces.append(go.Bar(
        name=f"{tech} ({label_b})",
        x=years, y=values_b[tech],
        marker_color=COLORS[tech],
        marker_pattern_shape='/',   # hatching distinguishes B
        legendgroup=tech,
        showlegend=True,
    ))
layout = go.Layout(barmode='group', ...)
```

#### Legend Tooltips

Same `generate_legend_tooltip_script()` injection as `ChartWidget`, with tooltips showing the full scenario name on hover.

#### Placeholder

When no parameter is selected: render the same styled placeholder message as `ChartWidget._show_chart_placeholder()`.

---

## Phase 6 — Integration & Polish [x]

### 6.1 Title Bar [x]

```
Scenario Comparison: <Scenario A name>  vs  <Scenario B name>
```

If either scenario has unsaved modifications, append `*` to its name.

### 6.2 Status Bar [x]

Show summary on parameter selection:
```
inv_cost — A: 48 rows  |  B: 52 rows  |  Common rows: 45  |  A-only: 3  |  B-only: 7
```

### 6.3 Export [x]

Add **File → Export Comparison…** in the comparison window's own menu bar:
- Exports the merged DataFrame to Excel with two sheets: `Merged` and `Delta`.

### 6.4 Window Management [x]

- Multiple comparison windows can be open simultaneously.
- `MainWindow._comparison_windows: list[ScenarioComparisonWindow]` keeps references alive.
- Windows are independent; closing the main window does not force-close them (but warns).

---

## Data Flow

```
actionCompare_Scenarios.triggered
  → _open_comparison_window()
    → ScenarioSelectorDialog.exec_()
      → ScenarioComparisonWindow(scenario_a, scenario_b)
        → ComparisonParameterTreeWidget(scenario_a.data, scenario_b.data)
            → builds MergedParameter list
            → renders tree with presence-based styling
        → user selects param_name (presence=='both')
          → ScenarioComparisonWindow._on_parameter_selected(param_name)
            → param_a = scenario_a.data.get_parameter(param_name)
            → param_b = scenario_b.data.get_parameter(param_name)
            → ComparisonDataWidget.display(param_a, param_b, label_a, label_b)
                → _merge_parameters() → merged_df
                → populate QTableWidget with color-coded cells
            → ComparisonChartWidget.update_chart(param_a, param_b, label_a, label_b)
                → build grouped Plotly traces
                → render HTML → QWebEngineView
```

---

## Testing Plan [x]

### Unit Tests [x]

**`tests/test_comparison_parameter_tree.py`** — 15 tests, all pass
- [x] `test_common_params_detected_as_both`
- [x] `test_a_only_param_detected`
- [x] `test_b_only_param_detected`
- [x] `test_row_counts_populated_for_both`
- [x] `test_row_count_none_for_missing_scenario`
- [x] `test_sets_merged_correctly`
- [x] `test_variables_assigned_to_variables_section`
- [x] `test_emission_param_categorized_environmental`
- [x] `test_cost_param_categorized_economic`
- [x] `test_capacity_param_categorized_capacity`
- [x] `test_bounds_categorized_correctly`
- [x] `test_var_act_categorized_activity` / `test_var_cap_categorized_capacity` / `test_emission_variable_categorized_emissions`
- [x] `test_section_icons_present_for_all_expected_sections` / `test_category_icons_populated`
- [x] `test_populate_does_not_raise` / `test_both_items_selectable` / `test_exclusive_items_disabled`

**`tests/test_comparison_data_widget.py`** — 20 tests, all pass
- [x] `test_common_rows_produce_both_values`
- [x] `test_delta_calculation` / `test_delta_negative`
- [x] `test_delta_pct_calculation`
- [x] `test_delta_pct_zero_denominator_is_na`
- [x] `test_outer_join_a_only_row` / `test_outer_join_b_only_row`
- [x] `test_lvl_column_treated_as_value`
- [x] `test_column_labels_reflect_scenario_names`
- [x] `test_display_populates_table` / `test_table_has_delta_columns`
- [x] `test_positive_delta_cell_green` / `test_negative_delta_cell_red` / `test_zero_delta_cell_default_background`
- [x] `test_get_merged_df_returns_dataframe` / `test_clear_hides_table`

### Integration Tests (manual / smoke) [ ]

- [v] Open two scenarios → Tools → Compare Scenarios → dialog shows both
- [v] Select same scenario for A and B → Compare button disabled
- [v] Comparison window opens with correct title
- [ ] Grayed items are not selectable (click does nothing)
- [v] Selecting a common parameter populates table and chart
- [v] Chart mode toggle (grouped/overlaid/delta) re-renders chart
- [ ] Closing comparison window removes it from `_comparison_windows`

---

## Implementation Order

| Phase | Effort | Deliverable | Status |
|-------|--------|-------------|--------|
| 1 — Menu + Dialog | Small | `ScenarioSelectorDialog`, menu wiring | [x] |
| 2 — Window Shell | Small | `ScenarioComparisonWindow` (programmatic) | [x] |
| 3 — Comparison Tree | Medium | `ComparisonParameterTreeWidget` with styling | [x] |
| 4 — Data Widget | Medium | `ComparisonDataWidget` with merge + color coding | [x] |
| 5 — Chart Widget | Medium | `ComparisonChartWidget` with grouped bar default | [x] |
| 6 — Polish + Tests | Small | Status bar, export, unit tests | [x] |

---

## Open Questions / Future Enhancements

- **3-way comparison**: Extend to compare 3 or more scenarios (adds complexity to merge logic and column layout).
- **Diff highlight in tree**: Show a badge with `▲N` or `▼N` next to parameter names indicating number of changed rows.
- **Synchronized scrolling**: Scroll both "scenario columns" in the table together when table is split vertically.
- **Parameter availability by section type**: Variables and postprocessing results may not be present in all scenarios (e.g., results only loaded for one). Handle gracefully with an info tooltip.
- **Copy merged table to clipboard**: Add a toolbar button to copy the merged comparison table in Excel-compatible format.
