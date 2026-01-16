# Development Plan: Data Table Right-Click Context Menu, Clipboard Operations, Edit Menu, and Enhanced Undo/Redo with Command Objects

## Overview
This document outlines the implementation plan for adding right-click context menu functionality to data table columns, clipboard operations, undo/redo functionality using command objects, and an Edit menu to the MessageIX Data Manager application. The undo/redo system will utilize autonomous command objects that encapsulate all necessary information for do and undo operations, stored in a stack for repeated undo calls. Additionally, a new phase introduces functionality to add and remove parameters in input files.

## Current Application Architecture
- **Framework**: PyQt5 desktop application
- **Data Table**: `QTableWidget` (`param_table`) in `DataDisplayWidget` component
- **Data Structure**: Parameters stored as pandas DataFrames with editing capabilities
- **UI Structure**: Main window with menu bar (File, Run, View menus exist)
- **No existing clipboard/undo functionality** found

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
1. [ ] Design and implement `Command` base class and specific command subclasses (e.g., `EditCellCommand`, `InsertColumnCommand`, `DeleteColumnCommand`, `PasteColumnCommand`)
2. [ ] Update `UndoManager` class to manage Command objects in stacks:
   - `undo_stack`: List of executed commands
   - `redo_stack`: List of undone commands
   - Methods: `execute(command)`, `undo()`, `redo()`, `clear()`
3. [ ] Integrate with existing operations: Each data-modifying action creates and executes a command via `UndoManager`
4. [x] Add keyboard shortcuts (Ctrl+Z for undo, Ctrl+Y for redo)
5. [ ] Ensure commands hold all state: No reliance on external snapshots; each command is self-contained

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

### Phase 7: Add and Remove Parameters in Input Files
**Objective**: Implement functionality to add and remove parameters in input files, extending the application's parameter management capabilities.

**Implementation Steps**:
1. [ ] Create command objects for parameter operations: `AddParameterCommand` and `RemoveParameterCommand`
   - `AddParameterCommand`: Holds parameter name, data type, default values, and file reference; do() adds parameter to file and updates UI; undo() removes it
   - `RemoveParameterCommand`: Holds parameter data and file reference; do() removes parameter; undo() restores it
2. [ ] Create new `ParameterManager` to handle file-level parameter operations
3. [ ] Update InputManager to use ParameterManager when loading files
3. [ ] Add UI elements: Buttons and menu options in input file views to add/remove parameters
4. [ ] Integrate with undo/redo system: All parameter additions/removals go through command execution
5. [ ] Validate parameter operations: Check for dependencies, data integrity, and file format compliance
6. [ ] Refresh data displays and dependent components after parameter changes

**Key Technical Details**:
- Support multiple input file formats (e.g., CSV, Excel)
- Maintain parameter metadata consistency across files
- Handle cascading effects on related parameters and calculations
- Ensure operations are reversible via undo/redo

**Testing Requirements**:
- Unit tests for `AddParameterCommand` and `RemoveParameterCommand` execution and undo operations
- Integration tests for parameter operations with undo/redo functionality
- UI tests for add/remove parameter buttons and menu options
- Edge case handling (invalid parameter names, dependency conflicts, unsupported file formats, large files)

**Valid MessageIX Parameters**:
New parameters should be taken from a list of valid MessageIX parameters, with proper column names and types. Below is an extracted list from the MessageIX documentation:

#### 1. Techno-Economic Parameters
These parameters define how technologies convert commodities, their efficiencies, and their operational lifetimes.

| Parameter | Index Dimensions | Description | Type |
|-----------|------------------|-------------|------|
| input | node_loc, technology, year_vtg, year_act, mode, node_origin, commodity, level, time, time_origin | Input consumption per unit of activity (Efficiency inverse). | Numeric |
| output | node_loc, technology, year_vtg, year_act, mode, node_dest, commodity, level, time, time_dest | Output yield per unit of activity. | Numeric |
| capacity_factor | node_loc, technology, year_vtg, year_act, time | Maximum utilization rate of a technology in a specific time slice. | Numeric |
| technical_lifetime | node_loc, technology, year_vtg | The duration (years) a technology remains operational after investment. | Numeric |
| duration_period | year | Length of a model period in years. | Numeric |
| duration_time | time | Duration of a sub-annual time slice (fraction of a year). | Numeric |
| construction_time | node_loc, technology, year_vtg | Time required to build a technology before it becomes active. | Numeric |

#### 2. Cost & Economic Parameters
These parameters define the financial drivers of the model, including capital expenditures, operational costs, and discount rates.

| Parameter | Index Dimensions | Description | Type |
|-----------|------------------|-------------|------|
| inv_cost | node_loc, technology, year_vtg | Investment cost per unit of new capacity. | Currency |
| fix_cost | node_loc, technology, year_vtg, year_act | Fixed operation and maintenance costs (per unit capacity). | Currency |
| var_cost | node_loc, technology, year_vtg, year_act, mode, time | Variable operation and maintenance costs (per unit activity). | Currency |
| interest_rate | year | Annual interest rate used for discounting. | Percentage |
| tax_emission | node_loc, emission, type_emission, year | Tax applied per unit of emission. | Currency |
| tax_var_cost | node_loc, technology, year_vtg, year_act, mode, time | Specific tax applied to the variable operation of a technology. | Currency |

#### 3. Demand and Resource Parameters
These parameters represent the exogenous drivers of the model, such as energy demand and the availability of primary resources.

| Parameter | Index Dimensions | Description | Type |
|-----------|------------------|-------------|------|
| demand | node, commodity, level, year, time | Exogenous demand for a specific commodity. | Energy |
| resource_volume | node, commodity, grade | Total available volume of a primary resource. | Energy |
| resource_cost | node, commodity, grade, year | Extraction cost of a primary resource. | Currency |
| bound_total_capacity_up | node_loc, technology, year_act | Upper limit on the total installed capacity. | Capacity |
| bound_activity_up | node_loc, technology, year_act, mode, time | Upper limit on the activity of a technology. | Activity |
| bound_new_capacity_up | node_loc, technology, year_vtg | Upper limit on the new capacity built in a period. | Capacity |

#### 4. Environmental and Emission Parameters
These are used to track and constrain pollutants or greenhouse gases.

| Parameter | Index Dimensions | Description | Type |
|-----------|------------------|-------------|------|
| emission_factor | node_loc, technology, year_vtg, year_act, mode, emission | Emissions produced per unit of activity. | Mass/Energy |
| bound_emission | node_loc, emission, type_emission, year | Upper bound on cumulative or annual emissions. | Mass |
| emission_scaling | type_emission, emission | Scaling factor to aggregate specific emissions into types (e.g., CO2e). | Numeric |

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

## Estimated Timeline
- Phase 1: 2-3 days
- Phase 2: 2-3 days
- Phase 3: 2 days
- Phase 4: 3-4 days
- Phase 5: 1-2 days
- Phase 6: 2-3 days
- Phase 7: 4-5 days (including integration and testing)

Total: 16-21 days depending on testing and integration complexity.
