# Development Plan: Data Table Right-Click Context Menu, Clipboard Operations, and Edit Menu

## Overview
This document outlines the implementation plan for adding right-click context menu functionality to data table columns, clipboard operations, undo/redo functionality, and an Edit menu to the MessageIX Data Manager application.

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

### Phase 4: Undo Functionality [x] ✅ COMPLETED
**Objective**: Implement undo/redo system for all data modifications.

**Implementation Steps**:
1. [x] Create `UndoManager` class with command pattern:
   - Store operation history (DataFrame snapshots)
   - Support undo/redo stack with configurable depth
   - Track operation metadata (timestamp, description)
2. [x] Integrate with existing cell editing in `MainWindow._on_cell_value_changed`
3. [x] Add undo/redo methods to handle column operations
4. [x] Add keyboard shortcuts (Ctrl+Z, Ctrl+Y)

**Storage Strategy**:
- Store DataFrame copies in memory (consider memory limits)
- Use diff-based storage for efficiency
- Clear undo history on file operations

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

## Potential Challenges and Solutions

1. **Memory Usage for Undo**: Solution - Implement configurable undo depth and diff-based storage
2. **Data Type Validation**: Solution - Add robust type checking and conversion during paste operations
3. **Multi-column Selection**: Solution - Extend to support multiple column operations
4. **Performance with Large Datasets**: Solution - Optimize DataFrame operations and lazy loading

## Success Criteria
- Right-click on column headers shows context menu with all required options
- Clipboard operations work with standard delimiters
- Insert/delete operations update all dependent views
- Undo/redo works for all data modifications
- Edit menu integrates seamlessly with existing UI
- All operations maintain data integrity and proper UI feedback

## Implementation Notes
- Follow existing code patterns and naming conventions
- Add comprehensive docstrings and comments
- Write tests for new functionality
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

Total: 12-17 days depending on testing and integration complexity.
