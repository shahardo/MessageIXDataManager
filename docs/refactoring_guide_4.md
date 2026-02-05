# Refactoring Guide - MessageIX Data Manager

## Executive Summary

**Total Codebase Size:** ~14,300 lines across 39 Python files
**Critical Problem Areas:** 3 files contain 30% of all code
**Primary Goal:** Reduce complexity, improve maintainability, establish clear separation of concerns

| File | Current Lines | Target Lines | Reduction |
|------|---------------|--------------|-----------|
| main_window.py | 2,174 | ~800 | 63% |
| data_display_widget.py | 1,220 | ~400 | 67% |
| results_analyzer.py | 891 | ~400 | 55% |

---

## Part 1: Main Window Refactoring (Priority: CRITICAL)

### 1.1 Current State Analysis

`src/ui/main_window.py` is a **God Class** with 82 methods spanning 2,174 lines. It violates the Single Responsibility Principle by handling:

1. **File Management** - Opening, loading, removing files
2. **Data Processing** - CSV parsing, ZIP extraction, DataFrame assembly
3. **UI Orchestration** - Component setup, signal connections
4. **View State Management** - Tracking current selections
5. **Dashboard Management** - Showing/hiding dashboards
6. **Solver Execution** - Running/stopping the solver
7. **Session Persistence** - Saving/loading application state

### 1.2 Refactoring Tasks

#### [x] Task 1.2.1: Extract DataFileManager Class

**Problem:** `_load_data_file()` and `_load_zipped_csv_data()` contain 274 lines of data processing logic embedded in UI code.

**Location of code to extract:** [main_window.py:591-865](src/ui/main_window.py#L591-L865)

**Create new file:** `src/managers/data_file_manager.py`

```python
"""
Data file loading and processing for solver output files.
Handles ZIP extraction, CSV parsing, and DataFrame assembly.
"""
from typing import Dict, Optional, Tuple, List
import pandas as pd
import zipfile
import re
import os

from core.data_models import ScenarioData, Parameter


class DataFileManager:
    """Manages loading and parsing of solver output data files."""

    # Constants for file patterns
    VAR_PREFIX = "var_"
    PAR_PREFIX = "par_"
    SET_PREFIX = "set_"
    EQU_PREFIX = "equ_"

    # Internal solver rows to filter out
    INTERNAL_PATTERNS = [
        r'^_.*',  # Rows starting with underscore
        r'^z_.*', # Internal solver variables
    ]

    def __init__(self, tech_descriptions: Optional[Dict[str, str]] = None):
        """
        Initialize the data file manager.

        Args:
            tech_descriptions: Optional mapping of technology codes to descriptions
        """
        self.tech_descriptions = tech_descriptions or {}
        self._compiled_patterns = [re.compile(p) for p in self.INTERNAL_PATTERNS]

    def load_data_file(self, file_path: str) -> Tuple[Optional[ScenarioData], List[str]]:
        """
        Load a data file (ZIP with CSVs or single CSV).

        Args:
            file_path: Path to the data file

        Returns:
            Tuple of (ScenarioData or None, list of warning messages)
        """
        warnings = []

        if file_path.endswith('.zip'):
            return self._load_zipped_csv_data(file_path)
        elif file_path.endswith('.csv'):
            return self._load_single_csv(file_path)
        else:
            warnings.append(f"Unsupported file format: {file_path}")
            return None, warnings

    def _load_zipped_csv_data(self, zip_path: str) -> Tuple[Optional[ScenarioData], List[str]]:
        """Extract and parse CSV files from a ZIP archive."""
        # Move existing logic from main_window.py here
        pass

    def _filter_internal_rows(self, df: pd.DataFrame, column: str = 'node') -> pd.DataFrame:
        """Remove internal solver rows from DataFrame."""
        if column not in df.columns:
            return df

        mask = pd.Series([True] * len(df))
        for pattern in self._compiled_patterns:
            mask &= ~df[column].str.match(pattern, na=False)
        return df[mask]

    def _filter_technologies(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to only known technologies if tech_descriptions provided."""
        if not self.tech_descriptions or 'technology' not in df.columns:
            return df
        return df[df['technology'].isin(self.tech_descriptions.keys())]
```

**Integration in main_window.py:**
```python
# In __init__
self.data_file_manager = DataFileManager(tech_descriptions=self.tech_descriptions)

# Replace _load_data_file calls
scenario_data, warnings = self.data_file_manager.load_data_file(file_path)
for warning in warnings:
    self._append_to_console(warning)
```

**Estimated reduction:** 274 lines from main_window.py

---

#### [x] Task 1.2.2: Create ViewState Class

**Problem:** 11+ state variables scattered throughout MainWindow tracking current view state.

**Current state variables to consolidate:**
```python
self.current_view = "input"
self.selected_input_file = None
self.selected_results_file = None
self.selected_scenario = None
self.current_displayed_parameter = None
self.current_displayed_is_results = False
self.last_selected_input_parameter = None
self.last_selected_results_parameter = None
self.last_parameter_search = ""
self.last_table_search = ""
self.current_search_mode = ""
```

**Create new file:** `src/core/view_state.py`

```python
"""
View state management for the main application window.
Centralizes all view-related state in a single, observable object.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from core.data_models import Scenario


@dataclass
class ViewState:
    """
    Immutable-style state container for application view state.

    Use the update() method to create modified copies for state transitions.
    """
    # Current view mode
    current_view: str = "input"  # "input", "results", "data", "dashboard"

    # File selections
    selected_input_file: Optional[str] = None
    selected_results_file: Optional[str] = None
    selected_scenario: Optional[Scenario] = None

    # Parameter display state
    current_displayed_parameter: Optional[str] = None
    current_displayed_is_results: bool = False

    # Memory of last selections (for restoring state)
    last_selected_input_parameter: Optional[str] = None
    last_selected_results_parameter: Optional[str] = None

    # Search state
    last_parameter_search: str = ""
    last_table_search: str = ""
    current_search_mode: str = ""

    def update(self, **kwargs) -> 'ViewState':
        """Create a new ViewState with updated values."""
        current_values = {
            'current_view': self.current_view,
            'selected_input_file': self.selected_input_file,
            'selected_results_file': self.selected_results_file,
            'selected_scenario': self.selected_scenario,
            'current_displayed_parameter': self.current_displayed_parameter,
            'current_displayed_is_results': self.current_displayed_is_results,
            'last_selected_input_parameter': self.last_selected_input_parameter,
            'last_selected_results_parameter': self.last_selected_results_parameter,
            'last_parameter_search': self.last_parameter_search,
            'last_table_search': self.last_table_search,
            'current_search_mode': self.current_search_mode,
        }
        current_values.update(kwargs)
        return ViewState(**current_values)

    @property
    def has_input_file(self) -> bool:
        """Check if an input file is currently selected."""
        return self.selected_input_file is not None

    @property
    def has_results_file(self) -> bool:
        """Check if a results file is currently selected."""
        return self.selected_results_file is not None


class ViewStateManager:
    """
    Manages view state with observer pattern for change notifications.
    """

    def __init__(self):
        self._state = ViewState()
        self._observers: List[Callable[[ViewState, ViewState], None]] = []

    @property
    def state(self) -> ViewState:
        """Get current state (read-only)."""
        return self._state

    def update(self, **kwargs) -> None:
        """
        Update state and notify observers.

        Args:
            **kwargs: State fields to update
        """
        old_state = self._state
        self._state = self._state.update(**kwargs)

        # Notify observers of state change
        for observer in self._observers:
            observer(old_state, self._state)

    def add_observer(self, callback: Callable[[ViewState, ViewState], None]) -> None:
        """Add an observer to be notified of state changes."""
        self._observers.append(callback)

    def remove_observer(self, callback: Callable[[ViewState, ViewState], None]) -> None:
        """Remove an observer."""
        if callback in self._observers:
            self._observers.remove(callback)
```

**Integration in main_window.py:**
```python
# In __init__
from core.view_state import ViewStateManager
self.view_state = ViewStateManager()
self.view_state.add_observer(self._on_view_state_changed)

# Replace scattered state updates
self.view_state.update(
    current_view="results",
    selected_results_file=file_path
)

# Access state
if self.view_state.state.has_input_file:
    ...
```

**Estimated reduction:** 50+ lines of scattered state management

---

#### [x] Task 1.2.3: Extract FileDialogController

**Problem:** `_open_input_file()` and `_open_results_file()` contain duplicated dialog logic.

**Location:** [main_window.py:400-454](src/ui/main_window.py#L400-L454)

**Create new file:** `src/ui/controllers/file_dialog_controller.py`

```python
"""
File dialog management for the main window.
Centralizes file selection dialogs and recent files tracking.
"""
from typing import Optional, Tuple, List
from PyQt5.QtWidgets import QFileDialog, QWidget


class FileDialogController:
    """Manages file selection dialogs with consistent behavior."""

    # File type filters
    INPUT_FILE_FILTER = "Excel Files (*.xlsx);;All Files (*)"
    RESULTS_FILE_FILTER = "Excel Files (*.xlsx);;All Files (*)"
    DATA_FILE_FILTER = "ZIP Files (*.zip);;CSV Files (*.csv);;All Files (*)"

    def __init__(self, parent: QWidget, session_manager=None):
        """
        Initialize the file dialog controller.

        Args:
            parent: Parent widget for dialogs
            session_manager: Optional session manager for recent directories
        """
        self.parent = parent
        self.session_manager = session_manager
        self._last_directory = ""

    def open_input_file(self) -> Optional[str]:
        """
        Show dialog to select an input Excel file.

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Input File",
            filter=self.INPUT_FILE_FILTER
        )

    def open_results_file(self) -> Optional[str]:
        """
        Show dialog to select a results Excel file.

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Results File",
            filter=self.RESULTS_FILE_FILTER
        )

    def open_data_file(self) -> Optional[str]:
        """
        Show dialog to select a data file (ZIP or CSV).

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Data File",
            filter=self.DATA_FILE_FILTER
        )

    def save_file(self, default_name: str = "") -> Optional[str]:
        """
        Show dialog to select save location.

        Args:
            default_name: Default filename to suggest

        Returns:
            Selected file path or None if cancelled
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save File",
            self._get_initial_directory() + "/" + default_name,
            "Excel Files (*.xlsx);;All Files (*)"
        )

        if file_path:
            self._last_directory = os.path.dirname(file_path)

        return file_path if file_path else None

    def _open_file_dialog(self, title: str, filter: str) -> Optional[str]:
        """Internal helper for file open dialogs."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            title,
            self._get_initial_directory(),
            filter
        )

        if file_path:
            self._last_directory = os.path.dirname(file_path)

        return file_path if file_path else None

    def _get_initial_directory(self) -> str:
        """Get the initial directory for file dialogs."""
        if self._last_directory:
            return self._last_directory
        if self.session_manager:
            return self.session_manager.get_last_directory() or ""
        return ""
```

**Estimated reduction:** 30 lines

---

#### [x] Task 1.2.4: Consolidate Signal Connections

**Problem:** `_connect_signals()` and `_connect_component_signals()` have 30+ connections spread across methods.

**Refactoring approach:** Create a signal registry pattern.

**Create new file:** `src/ui/signal_registry.py`

```python
"""
Signal registry for centralized signal-slot management.
Provides a clear overview of all component connections.
"""
from typing import Dict, List, Tuple, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal


class SignalConnection:
    """Represents a single signal-slot connection."""

    def __init__(self,
                 source_name: str,
                 signal_name: str,
                 target: Callable,
                 description: str = ""):
        self.source_name = source_name
        self.signal_name = signal_name
        self.target = target
        self.description = description
        self._connected = False

    def connect(self, source: QObject) -> bool:
        """Connect the signal to the slot."""
        try:
            signal = getattr(source, self.signal_name)
            signal.connect(self.target)
            self._connected = True
            return True
        except Exception as e:
            print(f"Failed to connect {self.source_name}.{self.signal_name}: {e}")
            return False

    def disconnect(self, source: QObject) -> bool:
        """Disconnect the signal from the slot."""
        if not self._connected:
            return False
        try:
            signal = getattr(source, self.signal_name)
            signal.disconnect(self.target)
            self._connected = False
            return True
        except Exception:
            return False


class SignalRegistry:
    """
    Registry for managing all signal-slot connections in the application.

    Usage:
        registry = SignalRegistry()
        registry.register('file_navigator', 'file_selected', self._on_file_selected)
        registry.connect_all(components_dict)
    """

    def __init__(self):
        self._connections: List[SignalConnection] = []
        self._sources: Dict[str, QObject] = {}

    def register(self,
                 source_name: str,
                 signal_name: str,
                 target: Callable,
                 description: str = "") -> None:
        """
        Register a signal-slot connection.

        Args:
            source_name: Name of the source component
            signal_name: Name of the signal
            target: Slot function to connect
            description: Optional description of what this connection does
        """
        self._connections.append(SignalConnection(
            source_name=source_name,
            signal_name=signal_name,
            target=target,
            description=description
        ))

    def set_source(self, name: str, source: QObject) -> None:
        """Register a source component by name."""
        self._sources[name] = source

    def connect_all(self) -> Tuple[int, int]:
        """
        Connect all registered signals.

        Returns:
            Tuple of (successful connections, failed connections)
        """
        success = 0
        failed = 0

        for conn in self._connections:
            source = self._sources.get(conn.source_name)
            if source and conn.connect(source):
                success += 1
            else:
                failed += 1

        return success, failed

    def disconnect_all(self) -> None:
        """Disconnect all registered signals."""
        for conn in self._connections:
            source = self._sources.get(conn.source_name)
            if source:
                conn.disconnect(source)

    def get_connection_report(self) -> str:
        """Generate a report of all connections for debugging."""
        lines = ["Signal Registry Connections:", "-" * 40]
        for conn in self._connections:
            status = "CONNECTED" if conn._connected else "PENDING"
            lines.append(f"  [{status}] {conn.source_name}.{conn.signal_name}")
            if conn.description:
                lines.append(f"           -> {conn.description}")
        return "\n".join(lines)
```

**Usage in main_window.py:**
```python
def _setup_signal_registry(self):
    """Configure all signal-slot connections in one place."""
    self.signal_registry = SignalRegistry()

    # File navigation signals
    self.signal_registry.register(
        'file_navigator', 'file_selected',
        self._on_file_selected,
        "Handle file selection from navigator"
    )
    self.signal_registry.register(
        'file_navigator', 'file_removed',
        self._on_file_removed,
        "Handle file removal from navigator"
    )

    # Parameter tree signals
    self.signal_registry.register(
        'param_tree', 'parameter_selected',
        self._on_parameter_selected,
        "Display selected parameter data"
    )

    # ... register all other connections

    # Set sources and connect
    self.signal_registry.set_source('file_navigator', self.file_navigator)
    self.signal_registry.set_source('param_tree', self.param_tree)
    self.signal_registry.connect_all()
```

**Benefits:**
- Single location for all signal connections
- Easy to debug with `get_connection_report()`
- Clear documentation of what each connection does
- Easy to disconnect all signals on cleanup

---

### 1.3 Main Window Target Structure

After refactoring, `main_window.py` should have these focused responsibilities:

```python
class MainWindow(QMainWindow):
    """
    Main application window - orchestrates UI components.

    Responsibilities (Single Responsibility):
    - Component composition and layout
    - Signal/slot registration via SignalRegistry
    - High-level event coordination
    - Menu and toolbar actions
    """

    def __init__(self):
        # Component creation
        self._create_managers()
        self._create_ui_components()
        self._setup_signal_registry()
        self._restore_session()

    # Manager creation (delegated to factory if many)
    def _create_managers(self): ...

    # UI setup (reads from .ui file)
    def _create_ui_components(self): ...

    # Signal registration (uses SignalRegistry)
    def _setup_signal_registry(self): ...

    # High-level event handlers (delegate to appropriate components)
    def _on_file_selected(self, file_path, file_type): ...
    def _on_parameter_selected(self, param_name): ...
    def _on_view_changed(self, view_name): ...

    # Menu actions
    def _on_save(self): ...
    def _on_open(self): ...
```

**Target: ~800 lines** (down from 2,174)

---

## Part 2: Data Display Widget Refactoring (Priority: HIGH)

### 2.1 Current State Analysis

`src/ui/components/data_display_widget.py` contains 1,220 lines with **3 classes** that should be separated:

1. **UndoManager** (118 lines) - Generic undo/redo functionality
2. **ColumnHeaderView** (164 lines) - Custom table header with context menu
3. **DataDisplayWidget** (938 lines) - Main data display with editing

### 2.2 Refactoring Tasks

#### [x] Task 2.2.1: Extract UndoManager to Managers

**Location:** [data_display_widget.py:1-118](src/ui/components/data_display_widget.py#L1-L118)

**Target:** `src/managers/table_undo_manager.py`

```python
"""
Undo/redo management for table operations.
Maintains a stack of reversible commands for table editing.
"""
from typing import List, Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class TableCommand:
    """Represents a reversible table operation."""
    description: str
    do_action: Callable[[], None]
    undo_action: Callable[[], None]

    def do(self) -> None:
        """Execute the command."""
        self.do_action()

    def undo(self) -> None:
        """Reverse the command."""
        self.undo_action()


class TableUndoManager:
    """
    Manages undo/redo stack for table operations.

    Implements Command pattern with a fixed-size history.
    """

    MAX_HISTORY = 50

    def __init__(self, on_state_changed: Optional[Callable[[], None]] = None):
        """
        Initialize the undo manager.

        Args:
            on_state_changed: Callback when undo/redo availability changes
        """
        self._undo_stack: List[TableCommand] = []
        self._redo_stack: List[TableCommand] = []
        self._on_state_changed = on_state_changed

    def execute(self, command: TableCommand) -> None:
        """Execute a command and add to undo stack."""
        command.do()
        self._undo_stack.append(command)

        # Limit history size
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)

        # Clear redo stack on new action
        self._redo_stack.clear()

        self._notify_state_changed()

    def undo(self) -> bool:
        """Undo the last command. Returns True if successful."""
        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

        self._notify_state_changed()
        return True

    def redo(self) -> bool:
        """Redo the last undone command. Returns True if successful."""
        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()
        command.do()
        self._undo_stack.append(command)

        self._notify_state_changed()
        return True

    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_state_changed()

    def _notify_state_changed(self) -> None:
        """Notify observer of state change."""
        if self._on_state_changed:
            self._on_state_changed()
```

---

#### [x] Task 2.2.2: Extract ColumnHeaderView

**Location:** [data_display_widget.py:120-284](src/ui/components/data_display_widget.py#L120-L284)

**Target:** `src/ui/components/column_header_view.py`

```python
"""
Custom column header view with context menu support.
Provides column selection, sorting, and bulk operations.
"""
from PyQt5.QtWidgets import QHeaderView, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt


class ColumnHeaderView(QHeaderView):
    """
    Enhanced table header with context menu for column operations.

    Signals:
        column_copy_requested(int): Column copy requested
        column_cut_requested(int): Column cut requested
        column_paste_requested(int): Column paste requested
        column_delete_requested(int): Column delete requested
        column_sort_requested(int, Qt.SortOrder): Sort requested
    """

    column_copy_requested = pyqtSignal(int)
    column_cut_requested = pyqtSignal(int)
    column_paste_requested = pyqtSignal(int)
    column_delete_requested = pyqtSignal(int)
    column_sort_requested = pyqtSignal(int, object)  # Qt.SortOrder

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self._setup_header()
        self._context_column = -1

    def _setup_header(self):
        """Configure header behavior."""
        self.setSectionsClickable(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        """Display context menu for column operations."""
        self._context_column = self.logicalIndexAt(pos)
        if self._context_column < 0:
            return

        menu = QMenu(self)

        # Copy/Cut/Paste actions
        copy_action = menu.addAction("Copy Column")
        copy_action.triggered.connect(
            lambda: self.column_copy_requested.emit(self._context_column)
        )

        cut_action = menu.addAction("Cut Column")
        cut_action.triggered.connect(
            lambda: self.column_cut_requested.emit(self._context_column)
        )

        paste_action = menu.addAction("Paste to Column")
        paste_action.triggered.connect(
            lambda: self.column_paste_requested.emit(self._context_column)
        )

        menu.addSeparator()

        # Sort actions
        sort_asc = menu.addAction("Sort Ascending")
        sort_asc.triggered.connect(
            lambda: self.column_sort_requested.emit(self._context_column, Qt.AscendingOrder)
        )

        sort_desc = menu.addAction("Sort Descending")
        sort_desc.triggered.connect(
            lambda: self.column_sort_requested.emit(self._context_column, Qt.DescendingOrder)
        )

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("Delete Column Values")
        delete_action.triggered.connect(
            lambda: self.column_delete_requested.emit(self._context_column)
        )

        menu.exec_(self.mapToGlobal(pos))
```

---

#### [x] Task 2.2.3: Extract TableFormatter

**Problem:** DataDisplayWidget mixes display formatting with data management.

**Target:** `src/ui/components/table_formatter.py`

```python
"""
Table formatting utilities for data display.
Handles cell styling, number formatting, and conditional formatting.
"""
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt
import pandas as pd


class CellStyle:
    """Represents styling for a table cell."""

    def __init__(self,
                 background: Optional[QColor] = None,
                 foreground: Optional[QColor] = None,
                 font: Optional[QFont] = None,
                 alignment: int = Qt.AlignLeft | Qt.AlignVCenter):
        self.background = background
        self.foreground = foreground
        self.font = font
        self.alignment = alignment

    def apply_to(self, item: QTableWidgetItem) -> None:
        """Apply this style to a table item."""
        if self.background:
            item.setBackground(QBrush(self.background))
        if self.foreground:
            item.setForeground(QBrush(self.foreground))
        if self.font:
            item.setFont(self.font)
        item.setTextAlignment(self.alignment)


class TableFormatter:
    """
    Formats table cells based on data type and value.

    Handles:
    - Number formatting (decimals, thousands separator)
    - Conditional formatting (highlight changes, errors)
    - Type-based alignment
    """

    # Default colors
    CHANGED_BACKGROUND = QColor(255, 255, 200)  # Light yellow
    ERROR_BACKGROUND = QColor(255, 200, 200)    # Light red
    HEADER_BACKGROUND = QColor(240, 240, 240)   # Light gray

    def __init__(self, decimal_places: int = 4):
        """
        Initialize the formatter.

        Args:
            decimal_places: Number of decimal places for floats
        """
        self.decimal_places = decimal_places
        self._styles: Dict[str, CellStyle] = {}

    def format_value(self, value: Any, column_type: Optional[str] = None) -> str:
        """
        Format a value for display.

        Args:
            value: The value to format
            column_type: Optional type hint for the column

        Returns:
            Formatted string representation
        """
        if pd.isna(value):
            return ""

        if isinstance(value, float):
            return f"{value:.{self.decimal_places}f}"

        if isinstance(value, (int, bool)):
            return str(value)

        return str(value)

    def get_cell_style(self,
                       value: Any,
                       is_changed: bool = False,
                       is_error: bool = False) -> CellStyle:
        """
        Get the appropriate style for a cell.

        Args:
            value: The cell value
            is_changed: Whether the cell has been modified
            is_error: Whether the cell contains an error

        Returns:
            CellStyle to apply
        """
        if is_error:
            return CellStyle(background=self.ERROR_BACKGROUND)

        if is_changed:
            return CellStyle(background=self.CHANGED_BACKGROUND)

        # Type-based styling
        if isinstance(value, (int, float)):
            return CellStyle(alignment=Qt.AlignRight | Qt.AlignVCenter)

        return CellStyle()

    def create_table_item(self,
                          value: Any,
                          editable: bool = True,
                          is_changed: bool = False,
                          is_error: bool = False) -> QTableWidgetItem:
        """
        Create a formatted table item.

        Args:
            value: The value for the cell
            editable: Whether the cell should be editable
            is_changed: Whether the cell has been modified
            is_error: Whether the cell contains an error

        Returns:
            Configured QTableWidgetItem
        """
        text = self.format_value(value)
        item = QTableWidgetItem(text)

        # Set editability
        if editable:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
        else:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        # Apply styling
        style = self.get_cell_style(value, is_changed, is_error)
        style.apply_to(item)

        return item
```

---

### 2.3 Data Display Widget Target Structure

After extraction, `data_display_widget.py` should focus only on display coordination:

```python
class DataDisplayWidget(QWidget):
    """
    Widget for displaying and editing parameter data in a table.

    Responsibilities:
    - Table widget management
    - Display mode switching (raw, advanced, pivot)
    - Cell editing coordination
    - Selection management
    """

    def __init__(self, parent=None):
        self.undo_manager = TableUndoManager()
        self.formatter = TableFormatter()
        # ... component setup

    def set_data(self, df: pd.DataFrame, parameter: Parameter): ...
    def get_data(self) -> pd.DataFrame: ...
    def set_display_mode(self, mode: str): ...
```

**Target: ~400 lines** (down from 938 for DataDisplayWidget class alone)

---

## Part 3: Results Analyzer Refactoring (Priority: HIGH)

### 3.1 Current State Analysis

`src/managers/results_analyzer.py` has 891 lines with parsing logic that should use the Strategy pattern like `InputManager`.

**Problem areas:**
- `_parse_workbook()` - 189 lines of direct parsing
- `_parse_variables_section()` - 123 lines
- `_parse_equations_section()` - 95 lines
- `_parse_extra_results_section()` - 78 lines

### 3.2 Refactoring Tasks

#### [x] Task 3.2.1: Create Results Parsing Strategies

**Target:** Add to `src/utils/parsing_strategies.py`

```python
"""
Strategy classes for parsing results Excel sheets.
Follows the same pattern as input file parsing strategies.
"""

class ResultsVariableParsingStrategy(ParsingStrategy):
    """
    Strategy for parsing MESSAGEix variable result sheets.

    Handles sheets with variable output data from the solver,
    typically containing columns: lvl, mrg, and dimension columns.
    """

    # Expected columns in variable sheets
    REQUIRED_COLUMNS = ['lvl', 'mrg']

    def parse(self, df: pd.DataFrame, sheet_name: str) -> Optional[Parameter]:
        """
        Parse a variable results sheet.

        Args:
            df: DataFrame from Excel sheet
            sheet_name: Name of the sheet (used as variable name)

        Returns:
            Parameter object or None if parsing fails
        """
        if df.empty:
            return None

        # Validate required columns
        if not all(col in df.columns for col in self.REQUIRED_COLUMNS):
            return None

        # Extract dimension columns (everything except lvl, mrg)
        dimension_cols = [c for c in df.columns if c not in self.REQUIRED_COLUMNS]

        return Parameter(
            name=sheet_name,
            data=df,
            dimensions=dimension_cols,
            units=self._infer_units(sheet_name),
            description=f"Results variable: {sheet_name}",
            is_results=True
        )

    def _infer_units(self, var_name: str) -> str:
        """Infer units from variable name patterns."""
        # Common MESSAGEix variable patterns
        if 'CAP' in var_name.upper():
            return 'GW'
        if 'ACT' in var_name.upper():
            return 'GWa'
        if 'COST' in var_name.upper():
            return 'M$'
        return ''


class ResultsEquationParsingStrategy(ParsingStrategy):
    """
    Strategy for parsing MESSAGEix equation/constraint sheets.

    Handles sheets with dual values and constraint information.
    """

    REQUIRED_COLUMNS = ['lvl', 'mrg', 'lo', 'up', 'scale']

    def parse(self, df: pd.DataFrame, sheet_name: str) -> Optional[Parameter]:
        """Parse an equation/constraint results sheet."""
        if df.empty:
            return None

        # Validate this looks like an equation sheet
        if not any(col in df.columns for col in ['lo', 'up', 'scale']):
            return None

        dimension_cols = [c for c in df.columns if c not in self.REQUIRED_COLUMNS]

        return Parameter(
            name=sheet_name,
            data=df,
            dimensions=dimension_cols,
            units='dual',
            description=f"Equation: {sheet_name}",
            is_results=True
        )


class ResultsExtraParsingStrategy(ParsingStrategy):
    """
    Strategy for parsing extra results sheets (summaries, reports).

    Handles non-standard sheets that contain computed results.
    """

    def parse(self, df: pd.DataFrame, sheet_name: str) -> Optional[Parameter]:
        """Parse an extra results sheet with flexible structure."""
        if df.empty:
            return None

        return Parameter(
            name=sheet_name,
            data=df,
            dimensions=list(df.columns),
            units='',
            description=f"Extra results: {sheet_name}",
            is_results=True
        )
```

#### [ ] Task 3.2.2: Refactor ResultsAnalyzer to Use Strategies

```python
class ResultsAnalyzer(BaseDataManager):
    """
    Analyzer for MESSAGEix results files.

    Uses parsing strategies to handle different sheet types.
    """

    def __init__(self):
        super().__init__()

        # Register parsing strategies
        self.strategies = {
            'variable': ResultsVariableParsingStrategy(),
            'equation': ResultsEquationParsingStrategy(),
            'extra': ResultsExtraParsingStrategy(),
        }

    def _parse_workbook(self, workbook) -> ScenarioData:
        """
        Parse all sheets in a results workbook using strategies.

        Args:
            workbook: openpyxl Workbook object

        Returns:
            ScenarioData containing all parsed results
        """
        scenario_data = ScenarioData()

        for sheet_name in workbook.sheetnames:
            df = pd.read_excel(workbook, sheet_name=sheet_name)

            # Try each strategy until one succeeds
            parameter = None
            for strategy in self.strategies.values():
                parameter = strategy.parse(df, sheet_name)
                if parameter:
                    break

            if parameter:
                scenario_data.add_parameter(parameter)

        return scenario_data
```

**Target: ~400 lines** (down from 891)

---

## Part 4: Dashboard Consolidation (Priority: MEDIUM)

### 4.1 Current State Analysis

`input_file_dashboard.py` (808 lines) and `results_file_dashboard.py` share ~150 lines of duplicated code for:
- Web view initialization
- UI setup from .ui files
- HTML generation patterns
- Tab management

### 4.2 Refactoring Tasks

#### [x] Task 4.2.1: Create BaseDashboard Class

**Target:** `src/ui/components/base_dashboard.py`

```python
"""
Base class for dashboard widgets with common functionality.
Provides shared web view setup, tab management, and HTML generation.
"""
from typing import Dict, Optional, List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import pyqtSignal
import plotly.graph_objects as go


class BaseDashboard(QWidget):
    """
    Base class for file dashboard widgets.

    Subclasses should implement:
    - _create_tabs(): Create the specific tabs for this dashboard
    - _generate_content(): Generate HTML content for each tab
    """

    # Signal when dashboard needs refresh
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_views: Dict[str, QWebEngineView] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the base UI structure."""
        self.layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        # Subclass creates specific tabs
        self._create_tabs()

        # Configure all web views
        self._setup_web_views()

    def _create_tabs(self):
        """Create dashboard tabs. Override in subclass."""
        raise NotImplementedError("Subclass must implement _create_tabs()")

    def _setup_web_views(self):
        """Configure common web view settings."""
        for view in self.web_views.values():
            settings = view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)

    def _add_web_view_tab(self, name: str, title: str) -> QWebEngineView:
        """
        Add a new tab with a web view.

        Args:
            name: Internal name for the view
            title: Display title for the tab

        Returns:
            The created QWebEngineView
        """
        view = QWebEngineView()
        self.web_views[name] = view
        self.tab_widget.addTab(view, title)
        return view

    def _show_placeholder(self, view_name: str, message: str):
        """Show a placeholder message in a web view."""
        if view_name not in self.web_views:
            return

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: Arial, sans-serif;
                    color: #666;
                    background-color: #f5f5f5;
                }}
            </style>
        </head>
        <body>
            <p>{message}</p>
        </body>
        </html>
        """
        self.web_views[view_name].setHtml(html)

    def _render_plotly_chart(self, view_name: str, fig: go.Figure):
        """Render a Plotly figure in a web view."""
        if view_name not in self.web_views:
            return

        html = fig.to_html(include_plotlyjs='cdn', full_html=True)
        self.web_views[view_name].setHtml(html)

    def update_dashboard(self, scenario):
        """
        Update dashboard with scenario data. Override in subclass.

        Args:
            scenario: The scenario to display
        """
        raise NotImplementedError("Subclass must implement update_dashboard()")

    def clear(self):
        """Clear all dashboard content."""
        for name in self.web_views:
            self._show_placeholder(name, "No data loaded")
```

#### [ ] Task 4.2.2: Refactor InputFileDashboard

```python
class InputFileDashboard(BaseDashboard):
    """Dashboard for viewing input file statistics and visualizations."""

    def _create_tabs(self):
        """Create input-specific dashboard tabs."""
        self._add_web_view_tab('overview', 'Overview')
        self._add_web_view_tab('technologies', 'Technologies')
        self._add_web_view_tab('parameters', 'Parameters')

    def update_dashboard(self, scenario):
        """Update dashboard with input scenario data."""
        if not scenario or not scenario.input_data:
            self.clear()
            return

        self._update_overview(scenario)
        self._update_technologies(scenario)
        self._update_parameters(scenario)
```

**Estimated reduction:** 150+ lines of duplicated code

---

## Part 5: Logging Consolidation (Priority: MEDIUM)

### 5.1 Current State

The codebase has 74 `print()` statements mixed with `logging_manager.log()` calls and `_append_to_console()`.

### 5.2 Refactoring Tasks

#### [x] Task 5.2.1: Create UILogger Adapter

**Target:** `src/utils/ui_logger.py`

```python
"""
Unified logging adapter that outputs to both logging system and UI console.
"""
import logging
from typing import Optional, Callable
from utils.logging_manager import logging_manager


class UILogger:
    """
    Logger adapter that writes to both file/console logs and UI console.

    Replaces scattered print() statements with consistent logging.
    """

    def __init__(self,
                 name: str,
                 console_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the UI logger.

        Args:
            name: Logger name (usually __name__)
            console_callback: Optional callback to write to UI console
        """
        self.logger = logging.getLogger(name)
        self.console_callback = console_callback
        self._module_name = name.split('.')[-1] if '.' in name else name

    def set_console_callback(self, callback: Callable[[str], None]):
        """Set the UI console callback."""
        self.console_callback = callback

    def debug(self, message: str, to_console: bool = False):
        """Log debug message."""
        self.logger.debug(message)
        logging_manager.log('DEBUG', self._module_name, message)
        if to_console and self.console_callback:
            self.console_callback(f"[DEBUG] {message}")

    def info(self, message: str, to_console: bool = True):
        """Log info message."""
        self.logger.info(message)
        logging_manager.log('INFO', self._module_name, message)
        if to_console and self.console_callback:
            self.console_callback(message)

    def warning(self, message: str, to_console: bool = True):
        """Log warning message."""
        self.logger.warning(message)
        logging_manager.log('WARNING', self._module_name, message)
        if to_console and self.console_callback:
            self.console_callback(f"[WARNING] {message}")

    def error(self, message: str, to_console: bool = True, exc_info: bool = False):
        """Log error message."""
        self.logger.error(message, exc_info=exc_info)
        logging_manager.log('ERROR', self._module_name, message)
        if to_console and self.console_callback:
            self.console_callback(f"[ERROR] {message}")


# Module-level function for quick logger creation
def get_ui_logger(name: str, console_callback: Optional[Callable[[str], None]] = None) -> UILogger:
    """Get a UILogger instance for a module."""
    return UILogger(name, console_callback)
```

**Usage:**
```python
# In any module
from utils.ui_logger import get_ui_logger

logger = get_ui_logger(__name__)

# Later, set console callback
logger.set_console_callback(main_window._append_to_console)

# Replace print statements
logger.info("Loading file...")  # Goes to log + console
logger.error("Failed to parse", exc_info=True)  # Goes to log + console + traceback
```

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (Highest Impact)

| Status | Task | Files Affected | Lines Reduced | Effort |
|--------|------|----------------|---------------|--------|
| [x] | Extract DataFileManager | main_window.py | ~274 | Medium |
| [x] | Create ViewState | main_window.py | ~50 | Low |
| [x] | Extract TableUndoManager | data_display_widget.py | ~118 | Low |

**Total Phase 1 Reduction:** ~440 lines, creates reusable components

### Phase 2: Strategy Pattern

| Status | Task | Files Affected | Lines Reduced | Effort |
|--------|------|----------------|---------------|--------|
| [x] | Results parsing strategies | results_analyzer.py | ~400 | Medium |
| [x] | Extract TableFormatter | data_display_widget.py | ~150 | Low |
| [x] | Extract ColumnHeaderView | data_display_widget.py | ~164 | Low |

**Total Phase 2 Reduction:** ~700 lines

### Phase 3: UI Organization

| Status | Task | Files Affected | Lines Reduced | Effort |
|--------|------|----------------|---------------|--------|
| [x] | Create BaseDashboard | input/results dashboards | ~150 | Medium |
| [x] | SignalRegistry | main_window.py | ~50 | Medium |
| [x] | FileDialogController | main_window.py | ~30 | Low |

**Total Phase 3 Reduction:** ~230 lines of duplication

### Phase 4: Polish

| Status | Task | Files Affected | Lines Reduced | Effort |
|--------|------|----------------|---------------|--------|
| [x] | UILogger adapter | All files | 74 print→logger | Medium |
| [ ] | Consolidate error handling | All files | ~100 | Medium |
| [ ] | Add missing tests | tests/ | N/A | High |

---

## Part 7: File-by-File Summary

### Files to Create

| Status | New File | Purpose | Estimated Lines |
|--------|----------|---------|-----------------|
| [x] | `src/managers/data_file_manager.py` | ZIP/CSV data loading | ~200 |
| [x] | `src/core/view_state.py` | View state management | ~100 |
| [x] | `src/ui/controllers/file_dialog_controller.py` | File dialogs | ~80 |
| [x] | `src/ui/signal_registry.py` | Signal management | ~100 |
| [x] | `src/managers/table_undo_manager.py` | Table undo/redo | ~120 |
| [x] | `src/ui/components/column_header_view.py` | Header widget | ~170 |
| [x] | `src/ui/components/table_formatter.py` | Cell formatting | ~150 |
| [x] | `src/ui/components/base_dashboard.py` | Dashboard base | ~120 |
| [x] | `src/utils/ui_logger.py` | Unified logging | ~80 |

### Files to Modify

| Status | File | Current Lines | Target Lines | Change |
|--------|------|---------------|--------------|--------|
| [ ] | `main_window.py` | 2,174 | ~800 | -63% |
| [ ] | `data_display_widget.py` | 1,220 | ~400 | -67% |
| [ ] | `results_analyzer.py` | 891 | ~400 | -55% |
| [ ] | `input_file_dashboard.py` | 808 | ~400 | -50% |
| [ ] | `results_file_dashboard.py` | 711 | ~400 | -44% |

---

## Part 8: Testing Requirements

Before major refactoring, create tests for:

### Critical Tests to Add

1. **DataFileManager tests**
   - [ ] Test ZIP extraction
   - [ ] Test CSV parsing with various formats
   - [ ] Test technology filtering
   - [ ] Test internal row filtering

2. **ViewState tests**
   - [ ] Test state updates
   - [ ] Test observer notifications
   - [ ] Test derived properties

3. **Parsing strategy tests**
   - [ ] Test each strategy with sample data
   - [ ] Test edge cases (empty sheets, missing columns)

4. **UI component tests**
   - [ ] Test signal emissions
   - [ ] Test state changes

### Test File Structure

- [ ] `tests/test_data_file_manager.py`
- [ ] `tests/test_view_state.py`
- [ ] `tests/test_parsing_strategies.py`
- [ ] `tests/test_table_undo_manager.py`
- [ ] `tests/test_table_formatter.py`
- [ ] `tests/test_ui_logger.py`

---

## Part 9: Risk Mitigation

### High-Risk Changes

1. **DataFileManager extraction**
   - Risk: Breaking file loading functionality
   - Mitigation: Create comprehensive test suite first, compare output before/after

2. **Signal rewiring**
   - Risk: Breaking UI responsiveness
   - Mitigation: Use SignalRegistry with connection verification

3. **Dashboard refactoring**
   - Risk: Breaking visualization
   - Mitigation: Keep old code until new code verified

### Recommended Approach

- [ ] **Branch per refactoring task** - Keep changes isolated
- [ ] **Test before extracting** - Write tests for existing behavior
- [ ] **Incremental changes** - Small, verifiable steps
- [ ] **Feature flags** - Allow switching between old/new code during transition

---

## Conclusion

This refactoring plan addresses the three critical issues:

- [x] **God Class (main_window.py)** - Extract DataFileManager, ViewState, FileDialogController, SignalRegistry
- [x] **Mixed Concerns (data_display_widget.py)** - Extract UndoManager, ColumnHeaderView, TableFormatter
- [x] **Inconsistent Patterns (results_analyzer.py)** - Apply ParsingStrategy pattern

Expected outcomes:
- [x] **40% reduction** in lines for critical files
- [x] **Clear separation of concerns** following SOLID principles
- [x] **Improved testability** with smaller, focused classes
- [x] **Consistent patterns** across the codebase
