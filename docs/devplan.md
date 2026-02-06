# Development Guide: message_ix data manater

## Overview
This app allows reading input and output data files of the message_ix model, visually present the input (parameters) and output (variables) data, and allow to edit and otherwise manipulate the data before running the solever model.

This document outlines the implementation plan for adding right-click context menu functionality to data table columns, clipboard operations, undo/redo functionality using command objects, and an Edit menu to the MessageIX Data Manager application. The undo/redo system will utilize autonomous command objects that encapsulate all necessary information for do and undo operations, stored in a stack for repeated undo calls. Additionally, a new phase introduces functionality to add and remove parameters in input files.

## Current Application Architecture
- **Framework**: PyQt5 desktop application
- **Data Table**: `QTableWidget` (`param_table`) in `DataDisplayWidget` component
- **Data Structure**: Parameters stored as pandas DataFrames with editing capabilities
- **UI Structure**: Main window with menu bar (File, Run, View menus exist)
- **Clipboard**: Allow for copy and paste of data in tables
- **Undo/redo functionality**: Based on Command objects

## Detailed Development Plan

### Phase 1: Right-Click Context Menu on Column Headers [x] ✅ COMPLETED
**Objective**: Add right-click menu to table column headers with cut, copy, paste, delimiter, insert, delete options.

**Implementation Steps**:
1. [x] Create a custom `QHeaderView` subclass in `data_display_widget.py` that overrides `contextMenuEvent`
2. [x] Add menu creation logic with actions for:
   - Cut (Ctrl+X)
   - Copy (Ctrl+C)
   - Paste (Ctrl+V)
   - Insert Column
   - Delete Column
   - Delimiter options (Tab, Comma, Semicolon, Space)
3. [x] Connect menu actions to handler methods
4. [x] Track which column was right-clicked for context-aware operations

**Key Technical Details**:
- Use `QTableWidget.horizontalHeader()` to set custom header view
- Store column index in menu event for action context
- Handle keyboard shortcuts in addition to menu items

### Phase 2: Clipboard Operations Implementation [x] ✅ COMPLETED
**Objective**: Handle data transfer to/from system clipboard with proper formatting.

**Implementation Steps**:
1. [x] Add clipboard management methods to `DataDisplayWidget`:
   - `copy_column_data()`: Extract column data as delimited text
   - `paste_column_data()`: Parse clipboard text and update column
   - `cut_column_data()`: Copy then clear column data
2. [x] Use `QApplication.clipboard()` for system integration
3. [x] Implement delimiter-aware parsing for paste operations
4. [x] Handle data type conversion (string → numeric) during paste
5. [x] Keep the distinction between zero and empty cells

**Data Format Considerations**:
- Export: Column data as single column with headers. Allow multi column selection.
- Import: Support CSV/TSV formats with auto-detection
- Validation: Ensure pasted data matches expected types

### Phase 3: Insert/Delete Operations [x] ✅ COMPLETED
**Objective**: Allow users to add/remove table columns dynamically.

**Implementation Steps**:
1. [x] Add `insert_column()` method:
   - Prompt for column name and data type
   - Insert new column in DataFrame and refresh table
   - Handle both raw and advanced view modes
2. [x] Add `delete_column()` method:
   - Confirm deletion dialog
   - Remove column from DataFrame
   - Update dependent views (charts, filters)

**Data Integrity**:
- Mark scenario as modified after structural changes
- Update parameter metadata
- Refresh all dependent UI components

### Phase 4: Undo/Redo Mechanism with Command Objects [x] ✅ COMPLETED
**Objective**: Implement a robust undo/redo system using command objects that encapsulate do and undo operations autonomously, holding all required information, and stored in a stack for repeated undo calls.

**Command Object Design**:
- Create a base `Command` class with `do()` and `undo()` methods
- Each command object holds all necessary data for its operations (e.g., original data, new data, column indices)
- Commands are autonomous: they perform the operation and can reverse it without external dependencies
- Stack-based storage: Commands are pushed onto an undo stack after execution; undo pops and reverses the command, pushing to redo stack

**Implementation Steps**:
1. [x] Design and implement `Command` base class and specific command subclasses (e.g., `EditCellCommand`, `InsertColumnCommand`, `DeleteColumnCommand`, `PasteColumnCommand`, `AddParameterCommand`, `RemoveParameterCommand`)
2. [x] Update `UndoManager` class to manage Command objects in stacks:
   - `undo_stack`: List of executed commands
   - `redo_stack`: List of undone commands
   - Methods: `execute(command)`, `undo()`, `redo()`, `clear()`
3. [x] Integrate with existing operations: Each data-modifying action creates and executes a command via `UndoManager`
4. [x] Add keyboard shortcuts (Ctrl+Z for undo, Ctrl+Y for redo)
5. [x] Ensure commands hold all state: No reliance on external snapshots; each command is self-contained

**Key Technical Details**:
- Commands store pre-operation state for undo (e.g., original cell value, column data)
- Memory efficiency: Commands store minimal necessary data, not full DataFrame copies
- Configurable stack depth to prevent memory issues
- Automatic clearing of redo stack on new operations

### Phase 5: Edit Menu Integration [x] ✅ COMPLETED
**Objective**: Add Edit menu to main window menu bar.

**Implementation Steps**:
1. [x] Update `main_window.ui` to include Edit menu with:
   - Undo (Ctrl+Z)
   - Redo (Ctrl+Y)
   - Cut (Ctrl+X)
   - Copy (Ctrl+C)
   - Paste (Ctrl+V)
   - Insert Column
   - Delete Column
2. [x] Connect menu actions to `DataDisplayWidget` methods
3. [x] Enable/disable menu items based on context (data loaded, operations available)
4. [x] Add status bar updates for operation feedback

### Phase 6: Testing and Integration [x] ✅ COMPLETED
**Objective**: Ensure all features work correctly and integrate with existing functionality.

**Testing Requirements**:
- [x] Unit tests for clipboard parsing/formatting
- [x] Integration tests for undo operations
- [x] UI tests for menu interactions
- [x] Edge case handling (empty clipboard, invalid data, memory limits)

**Integration Points**:
- [x] Coordinate with existing save/modified tracking
- [x] Update chart refresh logic for column changes
- [x] Maintain compatibility with raw/advanced view switching

### Phase 7: Add and Remove Parameters

## Overview
We will implement the ability to add and remove parameters in the active scenario. This will be done by operating on the in-memory `ScenarioData` structure, allowing for Undo/Redo support via the existing `UndoManager`. The changes will only be persisted to disk when the user explicitly saves the file.

## Key Changes

### 1. Core Data Models (`src/core/data_models.py`)
*  [x] **`ScenarioData`**: Add a `remove_parameter(name)` method to complement the existing `add_parameter`.

### 2. Parameter Manager (`src/managers/parameter_manager.py`)
*  [x] **Refactor**: Remove the file-based Command classes (`AddParameterCommand`, `RemoveParameterCommand`) which incorrectly modify files directly.
*  [x] **Enhance**: Focus this class on providing parameter definitions (dimensions, types) and factory methods for creating new, empty parameter DataFrames.
*  [x] **Validation**: Keep and improve validation logic to ensure added parameters follow MESSAGEix standards.

### 3. Commands (`src/managers/commands.py`)
*  [x] **New Commands**: Implement memory-based `AddParameterCommand` and `RemoveParameterCommand`.
    * [x]  `AddParameterCommand`: Adds a `Parameter` object to `ScenarioData`. Undo removes it.
    * [x]  `RemoveParameterCommand`: Removes a parameter from `ScenarioData`, storing the deleted object. Undo restores it.

### 4. UI Components (`src/ui/components/`)
*  [x] **`ParameterTreeWidget` (`src/ui/components/parameter_tree_widget.py`)**:
    * [x] Add a context menu with "Add Parameter..." and "Remove Parameter".
    * [x] Add an "Add Parameter" button (optional, or reuse the "Options" area).
*  [x] **`AddParameterDialog` (new file)**:
    * [x] A dialog allowing the user to select from a list of valid MESSAGEix parameters that are not yet in the scenario.
    * [x] Shows description and required dimensions for the selected parameter.

### 5. Main Window (`src/ui/main_window.py`)
*  [x] **Integration**: Connect the `ParameterTreeWidget` signals to the `UndoManager` to execute the new commands.
*  [x] **Updates**: Ensure the tree view refreshes correctly after adding/removing parameters.

## Implementation Steps

1. [x] **Update `ScenarioData`**: Add `remove_parameter` method to `src/core/data_models.py`.
2. [x] **Refactor `ParameterManager`**: Clean up `src/managers/parameter_manager.py`, removing file I/O commands and ensuring it serves as a definition provider.
3. [x] **Implement Commands**: Add `AddParameterCommand` and `RemoveParameterCommand` to `src/managers/commands.py`.
4. [x] **Create UI Dialog**: Create `src/ui/components/add_parameter_dialog.py`.
5. [x] **Update Tree Widget**: Modify `src/ui/components/parameter_tree_widget.py` to include the context menu and handling for add/remove actions.
6. [x] **Integrate in MainWindow**: Wire everything together in `src/ui/main_window.py`.
7. [x] **Testing**: Verify adding/removing parameters, undo/redo functionality, and ensuring data is preserved/restored correctly.

## Technical Considerations
*   **Memory Management**: `RemoveParameterCommand` will hold a reference to the removed `Parameter` object (including its DataFrame). This is acceptable as it's consistent with how `UndoManager` works, but we should be mindful of very large parameters.
*   **State Consistency**: Adding/removing parameters counts as a modification, so the "Save" button should become enabled.
*   **Validation**: When adding a parameter, we create an empty DataFrame with the correct columns (indices + value).

## Success Criteria
*   User can right-click the parameter tree to add or remove parameters.
*   "Add Parameter" shows a list of valid, missing MESSAGEix parameters.
*   Adding a parameter creates it in the tree and table view with correct columns.
*   Removing a parameter removes it from the view.
*   Undo/Redo correctly reverses these operations.
*   Changes are not written to disk until "Save" is clicked.

## Future Development - TODO List

- When openning the app, or after openning input file, select the 'parameters' line in the parameters tree and show the input dashboard
- For postprocessing data, show the same dashboard as for output file.
- Remove output file code, use only postprocessin.
- Use consistend color scheme for charts.
- Add costs chart, stacked bars by fuel source
- Allow cleaning up input data - remove redundant years, remove un-needed parameters.
- Allow to run the model directly from the app.
- Unify the pivot code between the data tables and the charts

## Valid MessageIX Parameters

New parameters should be taken from the canonical MESSAGEix scheme. Below is the structured list of valid parameters, grouped logically.

**Conventions**:
* All parameters are **numeric (float)** unless explicitly noted.
* `year_vtg` = vintage year, `year_act` = activity year
* `node_loc` = location of activity, `node_origin/dest` = trade origin/destination
* `mode` = mode of operation
* `time` = subannual time slice
* `level` = energy/material level (primary, final, useful, etc.)

#### 1. Core Technology Input–Output Parameters

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `input` | node_loc, tec, year_vtg, year_act, mode, node_origin, commodity, level, time, time_origin | Quantity of input commodity required per unit of technology activity |
| `output` | node_loc, tec, year_vtg, year_act, mode, node_dest, commodity, level, time, time_dest | Quantity of output commodity produced per unit of activity |
| `input_cap` | node_loc, tec, year_vtg, year_act, node_origin, commodity, level, time_origin | Input flow per unit of installed capacity |
| `output_cap` | node_loc, tec, year_vtg, year_act, node_dest, commodity, level, time_dest | Output flow per unit of installed capacity |
| `input_cap_new` | node_loc, tec, year_vtg, node_origin, commodity, level, time_origin | Input per unit of **newly built** capacity |
| `output_cap_new` | node_loc, tec, year_vtg, node_dest, commodity, level, time_dest | Output per unit of **newly built** capacity |
| `input_cap_ret` | node_loc, tec, year_vtg, node_origin, commodity, level, time_origin | Input associated with retired capacity |
| `output_cap_ret` | node_loc, tec, year_vtg, node_dest, commodity, level, time_dest | Output associated with retired capacity |

#### 2. Technical Performance Parameters

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `capacity_factor` | node_loc, tec, year_vtg, year_act, time | Maximum utilization rate of capacity in a given time slice |
| `operation_factor` | node_loc, tec, year_vtg, year_act | Fraction of the year the technology can operate |
| `min_utilization_factor` | node_loc, tec, year_vtg, year_act | Minimum utilization requirement for installed capacity |
| `technical_lifetime` | node_loc, tec, year_vtg | Lifetime of a technology before retirement |
| `construction_time` | node_loc, tec, year_vtg | Time delay between investment and availability |
| `rating_bin` | node, tec, year_act, commodity, level, time, rating | Share of output assigned to a reliability rating bin |
| `reliability_factor` | node, tec, year_act, commodity, level, time, rating | Contribution of a rating bin to firm capacity |
| `flexibility_factor` | node_loc, tec, year_vtg, year_act, mode, commodity, level, time, rating | Contribution of a technology to system flexibility |
| `addon_conversion` | node, tec, year_vtg, year_act, mode, time, type_addon | Conversion factor for add-on technologies |
| `storage_initial` | node, tec, level, commodity, year_act, time | Initial storage level |
| `storage_self_discharge` | node, tec, level, commodity, year_act, time | Fraction of stored energy lost per time slice |
| `time_order` | lvl_temporal, time | Ordering of subannual time slices |

#### 3. Cost and Economic Parameters

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `inv_cost` | node_loc, tec, year_vtg | Investment cost per unit of new capacity |
| `fix_cost` | node_loc, tec, year_vtg, year_act | Fixed O&M cost per unit of capacity |
| `var_cost` | node_loc, tec, year_vtg, year_act, mode, time | Variable cost per unit of activity |
| `levelized_cost` | node_loc, tec, year_vtg, time | Exogenously specified levelized cost |
| `construction_time_factor` | node, tec, year | Capital cost weighting during construction |
| `remaining_capacity` | node, tec, year | Fraction of capacity remaining from earlier vintages |
| `remaining_capacity_extended` | node, tec, year | Extended formulation of remaining capacity |
| `end_of_horizon_factor` | node, tec, year | Salvage value factor at model horizon |
| `beyond_horizon_lifetime` | node, tec, year | Remaining lifetime beyond model horizon |
| `beyond_horizon_factor` | node, tec, year | Discount factor for post-horizon capacity |

#### 4. Capacity and Activity Bounds (Hard)

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `bound_new_capacity_up` | node_loc, tec, year_vtg | Upper bound on new capacity additions |
| `bound_new_capacity_lo` | node_loc, tec, year_vtg | Lower bound on new capacity additions |
| `bound_total_capacity_up` | node_loc, tec, year_act | Upper bound on total installed capacity |
| `bound_total_capacity_lo` | node_loc, tec, year_act | Lower bound on total installed capacity |
| `bound_activity_up` | node_loc, tec, year_act, mode, time | Upper bound on activity |
| `bound_activity_lo` | node_loc, tec, year_act, mode, time | Lower bound on activity |

#### 5. Dynamic Growth Constraints

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `initial_new_capacity_up` | node_loc, tec, year_vtg | Initial upper bound on new capacity |
| `growth_new_capacity_up` | node_loc, tec, year_vtg | Growth rate limit for new capacity (up) |
| `initial_new_capacity_lo` | node_loc, tec, year_vtg | Initial lower bound on new capacity |
| `growth_new_capacity_lo` | node_loc, tec, year_vtg | Growth rate limit for new capacity (down) |
| `initial_activity_up` | node_loc, tec, year_act, time | Initial activity upper bound |
| `growth_activity_up` | node_loc, tec, year_act, time | Activity growth limit (up) |
| `initial_activity_lo` | node_loc, tec, year_act, time | Initial activity lower bound |
| `growth_activity_lo` | node_loc, tec, year_act, time | Activity growth limit (down) |

#### 6. Soft Constraints (Penalty-Based)

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `soft_new_capacity_up` | node_loc, tec, year_vtg | Soft upper bound on new capacity |
| `soft_new_capacity_lo` | node_loc, tec, year_vtg | Soft lower bound on new capacity |
| `soft_activity_up` | node_loc, tec, year_act, time | Soft upper bound on activity |
| `soft_activity_lo` | node_loc, tec, year_act, time | Soft lower bound on activity |
| `abs_cost_new_capacity_soft_up` | node_loc, tec, year_vtg | Absolute penalty for violating new-capacity upper bound |
| `level_cost_new_capacity_soft_up` | node_loc, tec, year_vtg | Marginal penalty for new-capacity upper bound |
| `abs_cost_activity_soft_up` | node_loc, tec, year_act, time | Absolute penalty for activity upper bound |
| `level_cost_activity_soft_up` | node_loc, tec, year_act, time | Marginal penalty for activity upper bound |

#### 7. Emissions (Technology Level)

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `emission_factor` | node_loc, tec, year_vtg, year_act, mode, emission | Emissions per unit of activity |

#### 8. Emissions Accounting & Policy

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `historical_emission` | node, emission, type_tec, year | Exogenous historical emissions |
| `emission_scaling` | type_emission, emission | Scaling factor for emissions aggregation |
| `bound_emission` | node, type_emission, type_tec, type_year | Emissions cap |
| `tax_emission` | node, type_emission, type_tec, type_year | Emissions tax |

#### 9. Resources & Extraction

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `resource_volume` | node, commodity, grade | Total available resource |
| `resource_cost` | node, commodity, grade, year | Extraction cost |
| `resource_remaining` | node, commodity, grade, year | Remaining resource stock |
| `bound_extraction_up` | node, commodity, level, year | Upper bound on extraction |
| `commodity_stock` | node, commodity, level, year | Stock of commodity |
| `historical_extraction` | node, commodity, grade, year | Historical extraction levels |

#### 10. Demand & Load Representation

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `demand` (`demand_fixed`) | node, commodity, level, year, time | Exogenous final demand |
| `peak_load_factor` | node, commodity, year | Ratio of peak to average load |

#### 11. Land-Use & Bioenergy Emulator

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `historical_land` | node, land_scenario, year | Historical land allocation |
| `land_cost` | node, land_scenario, year | Cost of land use |
| `land_input` | node, land_scenario, year, commodity, level, time | Inputs to land system |
| `land_output` | node, land_scenario, year, commodity, level, time | Outputs from land system |
| `land_use` | node, land_scenario, year, land_type | Land allocation by type |
| `land_emission` | node, land_scenario, year, emission | Emissions from land use |
| `initial_land_up / lo` | node, year, land_type | Initial land bounds |
| `growth_land_up / lo` | node, year, land_type | Land growth limits |

#### 12. Share Constraints

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `share_commodity_up` | shares, node_share, year_act, time | Upper bound on commodity share |
| `share_commodity_lo` | shares, node, year_act, time | Lower bound on commodity share |
| `share_mode_up` | shares, node_loc, tec, mode, year_act, time | Upper bound on mode share |
| `share_mode_lo` | shares, node_loc, tec, mode, year_act, time | Lower bound on mode share |

#### 13. Generic Relations

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `relation_upper` | relation, node_rel, year_rel | Upper bound on relation |
| `relation_lower` | relation, node_rel, year_rel | Lower bound on relation |
| `relation_cost` | relation, node_rel, year_rel | Cost of relation slack |
| `relation_new_capacity` | relation, node_rel, year_rel, tec | Capacity term in relation |
| `relation_total_capacity` | relation, node_rel, year_rel, tec | Total capacity term |
| `relation_activity` | relation, node_rel, year_rel, node_loc, tec, year_act, mode | Activity term |

#### 14. Fixed Variables (Exogenous Decisions)

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `fixed_extraction` | node, commodity, grade, year | Fixed extraction level |
| `fixed_stock` | node, commodity, level, year | Fixed stock level |
| `fixed_new_capacity` | node, tec, year_vtg | Fixed new capacity |
| `fixed_capacity` | node, tec, year_vtg, year_act | Fixed installed capacity |
| `fixed_activity` | node, tec, year_vtg, year_act, mode, time | Fixed activity |
| `fixed_land` | node, land_scenario, year | Fixed land allocation |

#### 15. Reporting / Auxiliary Outputs

| Parameter | Index Dimensions | Description |
|-----------|------------------|-------------|
| `total_cost` | node, year | Total system cost |
| `trade_cost` | node, year | Net trade cost |
| `import_cost` | node, commodity, year | Import expenditure |
| `export_cost` | node, commodity, year | Export revenue |

## Potential Challenges and Solutions

1. **Memory Usage for Undo**: Solution - Use command objects with minimal state storage instead of full snapshots
2. **Data Type Validation**: Solution - Add robust type checking and conversion during paste operations
3. **Multi-column Selection**: Solution - Extend to support multiple column operations
4. **Performance with Large Datasets**: Solution - Optimize DataFrame operations and lazy loading
5. **Command Object Complexity**: Solution - Design clean base class and specific implementations with clear separation of concerns
6. **Parameter Dependencies**: Solution - Implement dependency tracking for safe add/remove operations

## Success Criteria
- Right-click on column headers shows context menu with all required options
- Clipboard operations work with standard delimiters
- Insert/delete operations update all dependent views
- Undo/redo works for all data modifications using autonomous command objects
- Edit menu integrates seamlessly with existing UI
- Parameter add/remove functionality works in input files with full undo/redo support
- All operations maintain data integrity and proper UI feedback

## Implementation Notes
- Follow existing code patterns and naming conventions
- Add comprehensive docstrings and comments
- Write tests for new functionality, including command object tests
- Maintain backward compatibility with existing features
- Update user documentation as needed

## Dependencies
- PyQt5 (already in use)
- pandas (already in use)
- Standard Python libraries for clipboard operations

