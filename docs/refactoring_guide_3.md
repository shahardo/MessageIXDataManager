## Current Architecture Analysis

The application currently uses a file-based system with:
- Separate input and results files managed through ProjectNavigator
- Session persistence using QSettings with separate file lists
- Data loaded into ScenarioData objects
- Separate dashboards for input and results files

## Refactoring Plan

### 1. Create Scenario Data Model
Create a new `Scenario` class that encapsulates:
- `name`: Scenario name (user-defined)
- `input_file`: Path to input Excel file
- `message_scenario_file`: Path to pickle file with scenario snapshot
- `results_file`: Optional path to results Excel file
- `status`: Current status (loaded, modified, etc.)

**Implementation Tasks:**
- [x] Create new `Scenario` class in `src/core/data_models.py`
- [x] Add scenario name property with validation
- [x] Implement file path properties with validation
- [x] Add status tracking (loaded, modified, etc.)
- [x] Create scenario factory methods for loading/saving
- [x] Add scenario comparison methods for detecting changes

### 2. Modify Session Management
Update SessionManager to:
- Store scenarios as a list instead of separate file lists
- Persist scenario names and file associations
- Handle scenario deletion and renaming

**Implementation Tasks:**
- [x] Modify `SessionManager` in `src/managers/session_manager.py`
- [x] Replace `get_last_opened_files()` with `get_scenarios()`
- [x] Update `add_recent_file()` to `add_scenario()`
- [x] Modify `remove_recent_file()` to `remove_scenario()`
- [x] Update session state to store scenarios instead of file lists
- [x] Add scenario persistence methods
- [x] Implement scenario name validation and uniqueness

### 3. Update ProjectNavigator
Refactor ProjectNavigator to:
- Display scenarios as top-level items instead of file categories
- Show scenario name, input file, and results file status
- Add scenario management actions (rename, delete)
- Handle scenario selection instead of file selection

**Implementation Tasks:**
- [x] Modify `ProjectNavigator` in `src/ui/navigator.py`
- [x] Replace file-based tree structure with scenario-based structure
- [x] Add scenario name display and editing
- [x] Implement scenario status indicators
- [x] Add rename and delete scenario actions
- [x] Update file selection logic to handle scenarios
- [x] Modify UI to show scenario details in navigator

### 4. Implement Scenario File Handling
Create new scenario file handlers:
- `ScenarioFileHandler` for loading/saving scenarios
- Pickle loading for message scenario files using the provided code
- Integration with existing InputManager and ResultsAnalyzer

**Implementation Tasks:**
- [x] Create new `ScenarioFileHandler` class in `src/managers/file_handlers.py`
- [x] Implement scenario serialization to pickle format
- [x] Add scenario loading from pickle files
- [x] Integrate with existing `InputManager` and `ResultsAnalyzer`
- [x] Add scenario validation and error handling
- [x] Implement scenario backup and recovery

### 5. Update Main Window Logic
Modify MainWindow to:
- Handle scenario selection instead of file selection
- Update dashboards to work with scenarios
- Maintain backward compatibility for existing file operations

**Implementation Tasks:**
- [x] Update `MainWindow` in `src/ui/main_window.py`
- [x] Replace file selection logic with scenario selection
- [x] Modify `_on_file_selected()` to `_on_scenario_selected()`
- [x] Update dashboard integration to work with scenarios
- [x] Add scenario switching logic
- [x] Maintain backward compatibility for file operations
- [x] Update scenario state management

### 6. Add Scenario Management UI
Enhance the UI with:
- Scenario naming interface
- Delete scenario functionality
- Scenario status indicators
- Scenario creation workflow

**Implementation Tasks:**
- [ ] Add scenario management dialog in `src/ui/dialogs/`
- [ ] Create scenario creation wizard
- [ ] Implement scenario rename functionality
- [ ] Add scenario status indicators to UI
- [ ] Create scenario deletion confirmation dialog
- [ ] Update main window UI to include scenario management
- [ ] Add scenario import/export functionality

### 7. Data Flow Changes
Update the data flow to:
- Load complete scenarios instead of individual files
- Maintain scenario state across sessions
- Handle scenario switching and updates

**Implementation Tasks:**
- [ ] Update data flow in `src/main.py`
- [ ] Modify scenario loading sequence
- [ ] Implement scenario state persistence
- [ ] Add scenario switching logic
- [ ] Update data validation for scenarios
- [ ] Implement scenario change tracking
- [ ] Add scenario comparison and conflict resolution

## Implementation Steps

1. **Create Scenario Model** - Define the Scenario class and data structure
2. **Update Session Manager** - Modify persistence to handle scenarios
3. **Refactor ProjectNavigator** - Change UI to display scenarios
4. **Implement Scenario Handlers** - Create file handling for scenarios
5. **Update Main Window** - Modify core logic for scenario management
6. **Add UI Enhancements** - Implement scenario management interface
7. **Test and Validate** - Ensure all functionality works correctly

## Key Technical Considerations

- **Backward Compatibility**: Maintain support for existing file operations
- **Data Integrity**: Ensure scenario state is properly saved and restored
- **Performance**: Optimize scenario loading and switching
- **User Experience**: Provide clear scenario management interface
- **Error Handling**: Robust handling of missing or corrupted scenario files

## Specific Technical Details

### File Structure Changes
- [x] Add new `Scenario` class to `src/core/data_models.py`
- [x] Create new `ScenarioFileHandler` in `src/managers/file_handlers.py`
- [ ] Add scenario management dialogs in `src/ui/dialogs/`
- [ ] Update existing UI files to support scenarios

### Data Model Changes
- [x] Replace `ScenarioData` with `Scenario` class
- [x] Add scenario metadata and state tracking
- [x] Implement scenario serialization/deserialization
- [x] Add scenario validation and error handling

### UI Changes
- [x] Modify navigator to show scenarios instead of files
- [ ] Add scenario management actions to main window
- [ ] Update dashboards to work with scenarios
- [ ] Add scenario status indicators to UI

### Session Management Changes
- [x] Replace file-based session storage with scenario-based
- [x] Add scenario name persistence
- [x] Implement scenario auto-save functionality
- [x] Add scenario conflict resolution

### File Handling Changes
- [x] Add scenario file format support
- [x] Implement scenario backup and recovery
- [x] Add scenario import/export functionality
- [x] Update file validation for scenarios

## Testing Requirements

### Unit Tests
- [x] Test Scenario class functionality
- [x] Test scenario serialization/deserialization
- [x] Test scenario validation and error handling
- [ ] Test scenario management operations

### Integration Tests
- [x] Test scenario loading and switching
- [ ] Test scenario persistence across sessions
- [ ] Test scenario UI interactions
- [ ] Test backward compatibility with existing files

### UI Tests
- [x] Test scenario management dialogs
- [ ] Test scenario selection and display
- [ ] Test scenario status indicators
- [ ] Test scenario creation and deletion workflows

## Migration Strategy

### Phase 1: Foundation
- [x] Create Scenario class and basic functionality
- [x] Implement scenario file handling
- [ ] Add basic scenario management UI

### Phase 2: Integration
- [x] Update session management to use scenarios
- [x] Modify main window to handle scenarios
- [x] Update navigator to display scenarios

### Phase 3: Enhancement
- [ ] Add advanced scenario management features
- [ ] Implement scenario import/export
- [ ] Add scenario conflict resolution

### Phase 4: Optimization
- [ ] Optimize scenario loading and switching
- [ ] Add scenario performance monitoring
- [ ] Implement scenario caching

## Performance Considerations

### Loading Performance
- [ ] Optimize scenario deserialization
- [ ] Implement scenario lazy loading
- [ ] Add scenario loading progress indicators

### Memory Usage
- [ ] Implement scenario memory management
- [ ] Add scenario cleanup on deletion
- [ ] Optimize scenario data structures

### UI Responsiveness
- [ ] Implement scenario loading in background threads
- [ ] Add scenario loading cancellation
- [ ] Optimize scenario display updates

## Error Handling Strategy

### File Errors
- [ ] Handle missing scenario files
- [ ] Handle corrupted scenario files
- [ ] Implement scenario file recovery

### Data Errors
- [ ] Validate scenario data integrity
- [ ] Handle scenario data conflicts
- [ ] Implement scenario data repair

### UI Errors
- [ ] Handle scenario UI errors gracefully
- [ ] Implement scenario error recovery
- [ ] Add scenario error logging and reporting