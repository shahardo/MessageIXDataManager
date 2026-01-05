# MessageIX Data Manager - Refactoring Guide

This document provides detailed descriptions of proposed refactoring changes to make the codebase more comprehensive and lighter.

## 1. Eliminate Massive Duplication Between InputManager and ResultsAnalyzer

### Current Problem
The `InputManager` and `ResultsAnalyzer` classes share approximately 80% identical code, including:
- File loading logic (`load_excel_file` vs `load_results_file`)
- Scenario management methods
- File path tracking
- Data retrieval methods (`get_current_scenario` vs `get_current_results`)
- File removal logic (`remove_file`)
- Data validation methods

### Proposed Solution
Create a base `DataManager` abstract class containing all shared functionality:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from core.data_models import ScenarioData

class DataManager(ABC):
    """Base class for data managers handling Excel file loading and scenario management"""

    def __init__(self):
        self.scenarios: List[ScenarioData] = []
        self.loaded_file_paths: List[str] = []

    def load_file(self, file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScenarioData:
        """Common file loading logic with error handling and progress reporting"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        scenario = ScenarioData()

        try:
            if progress_callback:
                progress_callback(0, "Loading workbook...")

            wb = load_workbook(file_path, data_only=True)

            if progress_callback:
                progress_callback(20, "Workbook loaded, parsing data...")

            # Delegate to subclass for specific parsing
            self._parse_workbook(wb, scenario, progress_callback)

            self.scenarios.append(scenario)
            self.loaded_file_paths.append(file_path)

            if progress_callback:
                progress_callback(100, "Loading complete")

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise ValueError(f"Error parsing file: {str(e)}")

        return scenario

    @abstractmethod
    def _parse_workbook(self, wb, scenario: ScenarioData, progress_callback):
        """Subclass-specific parsing logic"""
        pass

    def get_current_scenario(self) -> Optional[ScenarioData]:
        """Get combined scenario from all loaded files"""
        if not self.scenarios:
            return None
        if len(self.scenarios) == 1:
            return self.scenarios[0]

        # Combine multiple scenarios
        combined = ScenarioData()
        for scenario in self.scenarios:
            self._merge_scenario(combined, scenario)
        return combined

    def _merge_scenario(self, combined: ScenarioData, scenario: ScenarioData):
        """Merge scenario data - can be overridden by subclasses"""
        # Common merging logic for sets and parameters
        pass

    # Additional shared methods...
```

### Benefits
- Reduces code duplication by ~60%
- Easier maintenance of shared functionality
- Consistent behavior across managers
- Easier to add new data manager types

### Implementation Steps
1. Create `BaseDataManager` class with shared methods
2. Refactor `InputManager` to inherit and implement `_parse_workbook`
3. Refactor `ResultsAnalyzer` to inherit and implement `_parse_workbook`
4. Update imports and references throughout codebase

## 2. Extract Parameter Creation Logic

### Current Problem
Both `InputManager` and `ResultsAnalyzer` contain nearly identical `_create_parameter` methods (~50 lines each) that:
- Handle None/NaN value conversion
- Convert integer columns to float when containing NaN
- Filter out all-zero columns
- Remove empty rows
- Create metadata dictionaries
- Instantiate `Parameter` objects

### Proposed Solution
Extract to a utility module `src/utils/parameter_utils.py`:

```python
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from core.data_models import Parameter

def create_parameter_from_data(param_name: str, param_data: List, headers: List[str],
                              metadata_overrides: Dict[str, Any] = None) -> Optional[Parameter]:
    """
    Create a Parameter object from raw Excel data with comprehensive data cleaning.

    Args:
        param_name: Name of the parameter
        param_data: List of row data from Excel
        headers: Column headers
        metadata_overrides: Optional metadata to override defaults

    Returns:
        Parameter object or None if creation fails
    """
    try:
        # Input validation
        if not param_data or not headers:
            return None

        # Create DataFrame with proper type handling
        df = pd.DataFrame(param_data, columns=headers)

        # Convert None to NaN
        df = df.replace({None: np.nan})

        # Handle integer columns with NaN
        for col in df.columns:
            col_data = df[col]
            if col_data.dtype in ['int64', 'int32'] and col_data.isna().any():
                df[col] = col_data.astype('float64')

        # Filter all-zero columns (treat as empty)
        for col in df.columns:
            col_data = df[col]
            if col_data.dtype in ['int64', 'float64'] and (col_data.dropna() == 0).all():
                df[col] = col_data.replace(0, np.nan)

        # Remove completely empty rows
        df = df.dropna(how='all')

        if df.empty:
            return None

        # Determine dimensions and value column
        dims = headers[:-1] if len(headers) > 1 else []
        value_col = headers[-1] if len(headers) > 0 else 'value'

        # Create metadata
        metadata = {
            'units': 'N/A',
            'desc': f'Parameter {param_name}',
            'dims': dims,
            'value_column': value_col,
            'shape': df.shape
        }

        # Apply overrides
        if metadata_overrides:
            metadata.update(metadata_overrides)

        return Parameter(param_name, df, metadata)

    except Exception as e:
        print(f"Warning: Could not create parameter {param_name}: {str(e)}")
        return None
```

### Benefits
- Single source of truth for parameter creation
- Consistent data cleaning across all parameters
- Easier to modify parameter creation logic
- Better testability of parameter creation

### Implementation Steps
1. Create `src/utils/parameter_utils.py`
2. Move and consolidate parameter creation logic
3. Update both managers to use the utility function
4. Add comprehensive tests for parameter creation

## 3. Break Down the MainWindow God Object

### Current Problem
The `MainWindow` class exceeds 2000 lines and handles:
- UI initialization and setup
- File loading dialogs and logic
- Data display and formatting
- Chart rendering and management
- Parameter/result tree navigation
- Settings management
- Progress tracking
- Error handling and user feedback

This violates single responsibility principle and makes the code hard to maintain.

### Proposed Solution
Split into focused components using composition:

```python
class DataDisplayWidget(QWidget):
    """Handles data table display, raw/advanced views, and formatting"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def display_parameter(self, parameter: Parameter):
        # Handle table display logic

    def toggle_view_mode(self):
        # Switch between raw and advanced views

class ChartWidget(QWidget):
    """Handles chart rendering and management"""
    def __init__(self, parent=None):
        super().__init__(parent)

    def update_chart(self, data: pd.DataFrame, chart_type: str):
        # Render charts using plotly

class FileNavigatorWidget(QWidget):
    """Handles file loading UI and recent files"""
    def __init__(self, input_manager, results_analyzer, parent=None):
        super().__init__(parent)
        self.input_manager = input_manager
        self.results_analyzer = results_analyzer

    def show_load_dialog(self, file_type: str):
        # File loading UI logic

class ParameterTreeWidget(QTreeWidget):
    """Handles parameter/result tree navigation"""
    def __init__(self, parent=None):
        super().__init__(parent)

    def update_parameters(self, scenario: ScenarioData):
        # Tree population logic

class MainWindow(QMainWindow):
    """Main application window - orchestrates components"""
    def __init__(self):
        super().__init__()

        # Initialize managers
        self.input_manager = InputManager()
        self.results_analyzer = ResultsAnalyzer()

        # Create UI components
        self.data_display = DataDisplayWidget()
        self.chart_widget = ChartWidget()
        self.file_navigator = FileNavigatorWidget(self.input_manager, self.results_analyzer)
        self.param_tree = ParameterTreeWidget()

        # Setup layout and connections
        self.setup_ui()
        self.connect_signals()
```

### Benefits
- Each component has a single responsibility
- Easier testing of individual components
- Better code organization and readability
- Reduced cognitive load when working on specific features

### Implementation Steps
1. Create individual widget classes in `src/ui/components/`
2. Move related methods from MainWindow to appropriate components
3. Update MainWindow to use composition
4. Ensure proper signal/slot connections between components

## 4. Extract Common Display Logic

### Current Problem
`_display_parameter_data` and `_display_result_data` methods are 95% identical (~150 lines each), differing only in:
- Title text ("Parameter:" vs "Result:")
- Chart update method calls
- Minor metadata handling differences

### Proposed Solution
Create a unified display method with parameters:

```python
def display_data_table(self, data: Parameter, title_prefix: str, is_results: bool = False):
    """
    Unified method for displaying parameter/result data in table and chart views.

    Args:
        data: Parameter object to display
        title_prefix: "Parameter" or "Result" for titles
        is_results: Whether this is results data (affects some logic)
    """
    df = data.df

    # Update title
    self.param_title.setText(f"{title_prefix}: {data.name}")
    self.param_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; padding: 5px; background-color: #f0f0f0;")

    if df.empty:
        self._clear_table_display()
        return

    # Handle view mode (raw vs advanced)
    if self.table_display_mode == "advanced":
        current_filters = self._get_current_filters()
        display_df = self._transform_to_advanced_view(df, current_filters, is_results)
        self._setup_property_selectors(df)
    else:
        display_df = df

    # Set up table dimensions and headers
    self._configure_table(display_df, is_results)

    # Format and populate table data
    self._populate_table(display_df, data)

    # Update chart
    chart_df = self._transform_to_advanced_view(df, self._get_current_filters(), is_results, hide_empty=True)
    self._update_chart(chart_df, data.name, is_results)

    # Enable controls and update status
    self._finalize_display(display_df, data, title_prefix, is_results)
```

### Benefits
- Eliminates code duplication
- Consistent display behavior
- Easier maintenance of display logic
- Single point for display-related bug fixes

### Implementation Steps
1. Create `display_data_table` method combining common logic
2. Extract helper methods for specific differences
3. Update method calls to use the unified approach
4. Test both parameter and result display functionality

## 5. Simplify Complex Methods

### Current Problem
Several methods are excessively long and complex:
- `_transform_to_advanced_view`: ~200 lines with nested logic
- `_display_parameter_data`: ~150 lines
- `_open_input_file`: ~80 lines with deep nesting
- Various parsing methods with complex conditional logic

### Proposed Solution
Break down into smaller, focused functions:

```python
def _transform_to_advanced_view(self, df: pd.DataFrame, current_filters: dict = None,
                               is_results: bool = False, hide_empty: bool = None) -> pd.DataFrame:
    """Transform data to advanced 2D view format"""
    if df.empty:
        return df

    if hide_empty is None:
        hide_empty = self.hide_empty_columns

    # Identify column types
    column_info = self._identify_columns(df)

    # Apply filters
    filtered_df = self._apply_filters(df, current_filters, column_info)

    # Transform data structure
    transformed_df = self._transform_data_structure(filtered_df, column_info, is_results)

    # Clean and finalize output
    final_df = self._clean_output(transformed_df, hide_empty, is_results)

    return final_df

def _identify_columns(self, df: pd.DataFrame) -> Dict[str, List[str]]:
    """Identify different types of columns in the DataFrame"""
    year_cols = []
    property_cols = []
    filter_cols = []
    value_col = None

    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ['value', 'val']:
            value_col = col
        elif col_lower in ['year_vtg', 'year_act', 'year', 'period']:
            year_cols.append(col)
        elif col_lower in ['node_loc', 'technology', 'commodity']:
            filter_cols.append(col)
        elif col_lower in ['technology', 'commodity', 'type']:
            property_cols.append(col)

    return {
        'year_cols': year_cols,
        'property_cols': property_cols,
        'filter_cols': filter_cols,
        'value_col': value_col
    }

def _apply_filters(self, df: pd.DataFrame, filters: dict, column_info: dict) -> pd.DataFrame:
    """Apply current filter selections to DataFrame"""
    filtered_df = df.copy()
    for filter_col, filter_value in filters.items():
        if filter_value and filter_value != "All" and filter_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[filter_col] == filter_value]
    return filtered_df

def _transform_data_structure(self, df: pd.DataFrame, column_info: dict, is_results: bool) -> pd.DataFrame:
    """Transform DataFrame structure based on data type"""
    # Pivoting logic for input data
    if not is_results and self._should_pivot(df, column_info):
        return self._perform_pivot(df, column_info)
    else:
        return self._prepare_2d_format(df, column_info)

def _clean_output(self, df: pd.DataFrame, hide_empty: bool, is_results: bool) -> pd.DataFrame:
    """Clean and filter final output DataFrame"""
    if hide_empty:
        df = self._hide_empty_columns(df, is_results)

    # Additional cleaning logic
    return df
```

### Benefits
- Improved readability and maintainability
- Easier testing of individual components
- Better error isolation
- More focused code reviews

### Implementation Steps
1. Identify methods exceeding 50 lines
2. Break down into logical sub-functions
3. Extract repeated code patterns
4. Add comprehensive docstrings to each function
5. Test each component function individually

## 6. Reduce Inline UI Setup Code

### Current Problem
UI setup code is scattered throughout methods with:
- Inline widget styling (50+ lines in `__init__`)
- Repeated styling patterns
- Hard-coded style strings
- Mixed concerns (logic + presentation)

### Proposed Solution
Create dedicated styling and UI setup:

**styles.qss** (Qt stylesheet file):
```css
/* Application-wide styles */
QMainWindow {
    background-color: #f5f5f5;
}

QTableWidget {
    gridline-color: #ddd;
    selection-background-color: #e3f2fd;
}

.parameter-title {
    font-weight: bold;
    font-size: 14px;
    color: #333;
    padding: 5px;
    background-color: #f0f0f0;
}

.chart-container {
    border: 1px solid #ccc;
    border-radius: 3px;
}

/* Additional styles... */
```

**ui_setup.py**:
```python
class UIStyler:
    """Centralized UI styling and setup"""

    @staticmethod
    def apply_stylesheet(app: QApplication):
        """Load and apply application stylesheet"""
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, 'r') as f:
                app.setStyleSheet(f.read())

    @staticmethod
    def setup_table_widget(table: QTableWidget):
        """Configure table widget with consistent settings"""
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(22)
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                background-color: white;
            }
        """)

    @staticmethod
    def setup_button_group(buttons: List[QPushButton], checkable: bool = False):
        """Setup a group of related buttons"""
        for button in buttons:
            if checkable:
                button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)

class MainWindowUI:
    """UI setup logic extracted from MainWindow"""

    def __init__(self, main_window):
        self.main_window = main_window

    def setup_splitters(self):
        """Configure all splitter properties"""
        # Splitter setup code...

    def setup_chart_buttons(self):
        """Setup chart type selection buttons"""
        # Button setup code...

    def setup_table_styling(self):
        """Configure table appearance"""
        # Table styling code...
```

### Benefits
- Separation of presentation and logic
- Consistent styling across components
- Easier theme changes
- Reduced code duplication

### Implementation Steps
1. Create `src/ui/styles.qss` stylesheet
2. Create `UIStyler` and `MainWindowUI` helper classes
3. Move inline styling to centralized locations
4. Update component initialization to use helpers

## 7. Add Comprehensive Error Handling

### Current Problem
Error handling is minimal and inconsistent:
- Bare `except Exception` blocks
- Generic error messages
- No graceful degradation
- Limited logging of errors
- User experience suffers from crashes

### Proposed Solution
Implement comprehensive error handling framework:

```python
class ErrorHandler:
    """Centralized error handling and user feedback"""

    @staticmethod
    def handle_file_loading_error(error: Exception, file_path: str, logger=None) -> str:
        """Handle file loading errors with appropriate user feedback"""
        error_msg = f"Failed to load file {os.path.basename(file_path)}: {str(error)}"

        if isinstance(error, FileNotFoundError):
            user_msg = f"File not found: {file_path}"
        elif isinstance(error, PermissionError):
            user_msg = f"Permission denied accessing: {file_path}"
        elif "Invalid file format" in str(error):
            user_msg = f"Invalid Excel format in: {os.path.basename(file_path)}"
        else:
            user_msg = f"Error loading file: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return user_msg

    @staticmethod
    def handle_data_processing_error(error: Exception, context: str, logger=None):
        """Handle data processing errors"""
        error_msg = f"Data processing error in {context}: {str(error)}"

        if logger:
            logger.error(error_msg, exc_info=True)

        return f"Data processing failed: {str(error)}"

class SafeOperation:
    """Context manager for safe operations with automatic error handling"""

    def __init__(self, operation_name: str, error_handler=None, logger=None):
        self.operation_name = operation_name
        self.error_handler = error_handler or ErrorHandler()
        self.logger = logger

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            error_msg = self.error_handler.handle_operation_error(
                exc_val, self.operation_name, self.logger
            )
            # Could show user dialog or log to console
            return True  # Suppress exception if handled
        return False
```

Usage examples:
```python
# Safe file loading
try:
    with SafeOperation("file loading", error_handler, logger):
        scenario = self.input_manager.load_excel_file(file_path, progress_callback)
except Exception as e:
    QMessageBox.warning(self, "Load Error", str(e))
    return

# Data processing with error recovery
try:
    processed_data = self._process_data(raw_data)
except DataProcessingError as e:
    self._handle_data_error(e)
    processed_data = self._get_fallback_data()
```

### Benefits
- Consistent error handling across application
- Better user experience with informative messages
- Comprehensive logging for debugging
- Graceful degradation when possible

### Implementation Steps
1. Create `ErrorHandler` and `SafeOperation` classes
2. Identify all error-prone operations
3. Add appropriate try/catch blocks with specific error types
4. Implement user-friendly error dialogs
5. Add comprehensive logging

## 8. Improve Documentation and Type Hints

### Current Problem
Documentation and type hints are incomplete:
- Many methods lack docstrings
- Type hints missing for many parameters/returns
- No parameter descriptions or examples
- Inconsistent documentation format

### Proposed Solution
Comprehensive documentation standards:

```python
from typing import Optional, List, Dict, Callable, Union, Any
import pandas as pd

class InputManager(DataManager):
    """
    Manages loading and parsing of MESSAGEix input Excel files.

    This class handles the complex process of reading MESSAGEix scenario data
    from Excel workbooks, parsing sets and parameters, and providing access
    to the loaded data for analysis and visualization.

    Attributes:
        scenarios: List of loaded ScenarioData objects
        loaded_file_paths: Corresponding file paths for loaded scenarios
    """

    def load_excel_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ScenarioData:
        """
        Load and parse a MESSAGEix Excel input file.

        This method performs comprehensive validation and parsing of MESSAGEix
        input files, extracting sets, parameters, and metadata.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls format).
                      File must exist and be readable.
            progress_callback: Optional callback function for progress updates.
                             Receives (percentage: int, message: str) parameters.
                             Called at key milestones during loading process.

        Returns:
            ScenarioData object containing parsed sets and parameters.

        Raises:
            FileNotFoundError: If the specified file_path does not exist.
            ValueError: If the file format is invalid or parsing fails.
            PermissionError: If file cannot be read due to permissions.

        Example:
            >>> manager = InputManager()
            >>> def progress(pct, msg): print(f"{pct}%: {msg}")
            >>> scenario = manager.load_excel_file("data.xlsx", progress)
            >>> print(f"Loaded {len(scenario.parameters)} parameters")
        """
        # Implementation...

    def get_parameter(self, name: str) -> Optional[Parameter]:
        """
        Retrieve a parameter by name from the current scenario.

        Args:
            name: Name of the parameter to retrieve (case-sensitive).

        Returns:
            Parameter object if found, None otherwise.

        Note:
            This method searches only the current combined scenario.
            For individual file access, use get_scenario_by_file_path().
        """
        # Implementation...
```

### Benefits
- Improved developer experience with better IDE support
- Self-documenting code with clear contracts
- Easier onboarding for new developers
- Better maintainability and refactoring confidence

### Implementation Steps
1. Define documentation standards (Google/Numpy style)
2. Add comprehensive type hints to all methods
3. Write detailed docstrings for public methods
4. Add usage examples for complex methods
5. Use tools like `mypy` for type checking

## 9. Remove Unused/Dead Code

### Current Problem
Codebase contains unused elements:
- Commented-out code blocks
- Unused imports
- Methods that are never called
- Duplicate import statements
- Legacy code from previous versions

### Proposed Solution
Systematic cleanup using static analysis:

1. **Import Cleanup**:
```python
# Before
import os
import sys
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Callable
import pandas as pd  # Duplicate!

# After
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Callable
```

2. **Method Removal**:
- Identify unused private methods
- Remove deprecated public methods (with deprecation warnings first)
- Consolidate duplicate methods

3. **Dead Code Identification**:
Use tools to find unused code:
```bash
# Use vulture for dead code detection
pip install vulture
vulture src/
```

4. **Configuration Cleanup**:
- Remove unused settings from config files
- Clean up old TODO comments
- Remove obsolete requirements

### Benefits
- Reduced bundle size
- Faster startup times
- Easier maintenance
- Clearer codebase

### Implementation Steps
1. Run static analysis tools (vulture, pylint)
2. Review and remove unused imports
3. Identify and remove dead methods
4. Clean up configuration files
5. Update tests to reflect removed code

## 10. Introduce Design Patterns

### Current Problem
Code lacks established design patterns, leading to:
- Tight coupling between components
- Difficult testing
- Hard to extend functionality
- Inconsistent interfaces

### Proposed Solution
Implement key design patterns:

**Observer Pattern for Data Updates**:
```python
from typing import Protocol

class DataObserver(Protocol):
    """Protocol for objects that observe data changes"""
    def on_data_loaded(self, scenario: ScenarioData): ...
    def on_data_removed(self, file_path: str): ...

class ObservableDataManager(DataManager):
    """DataManager that notifies observers of changes"""

    def __init__(self):
        super().__init__()
        self._observers: List[DataObserver] = []

    def add_observer(self, observer: DataObserver):
        """Add an observer for data changes"""
        self._observers.append(observer)

    def remove_observer(self, observer: DataObserver):
        """Remove an observer"""
        self._observers.remove(observer)

    def _notify_data_loaded(self, scenario: ScenarioData):
        """Notify observers of new data"""
        for observer in self._observers:
            observer.on_data_loaded(scenario)

    def load_file(self, file_path: str, progress_callback=None) -> ScenarioData:
        scenario = super().load_file(file_path, progress_callback)
        self._notify_data_loaded(scenario)
        return scenario
```

**Factory Pattern for Parameter Creation**:
```python
class ParameterFactory:
    """Factory for creating different types of parameters"""

    @staticmethod
    def create_from_excel_data(param_name: str, data: List, headers: List[str],
                              param_type: str = 'input') -> Optional[Parameter]:
        """Create parameter based on type"""
        if param_type == 'input':
            return InputParameterFactory.create(param_name, data, headers)
        elif param_type == 'result':
            return ResultParameterFactory.create(param_name, data, headers)
        else:
            return StandardParameterFactory.create(param_name, data, headers)
```

**Strategy Pattern for Parsing**:
```python
from abc import ABC, abstractmethod

class ParsingStrategy(ABC):
    """Strategy for parsing different Excel sheet types"""

    @abstractmethod
    def parse_sheet(self, sheet, scenario: ScenarioData) -> None:
        pass

class SetParsingStrategy(ParsingStrategy):
    def parse_sheet(self, sheet, scenario: ScenarioData):
        # Set-specific parsing logic

class ParameterParsingStrategy(ParsingStrategy):
    def parse_sheet(self, sheet, scenario: ScenarioData):
        # Parameter-specific parsing logic

class ExcelParser:
    """Parser that uses different strategies based on sheet type"""

    def __init__(self):
        self.strategies = {
            'set': SetParsingStrategy(),
            'parameter': ParameterParsingStrategy(),
        }

    def parse_sheet(self, sheet_name: str, sheet, scenario: ScenarioData):
        strategy = self._get_strategy(sheet_name)
        strategy.parse_sheet(sheet, scenario)
```

### Benefits
- Loose coupling between components
- Easier testing with dependency injection
- Extensible architecture
- Consistent interfaces

### Implementation Steps
1. Identify areas where patterns would help
2. Implement Observer pattern for data updates
3. Create Factory pattern for object creation
4. Add Strategy pattern for parsing logic
5. Refactor existing code to use patterns
6. Add comprehensive tests for pattern implementations
