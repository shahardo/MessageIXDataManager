"""
Custom column header view with context menu support.
Provides column selection, clipboard operations, and bulk operations.

Extracted from data_display_widget.py as part of refactoring.
"""
from PyQt5.QtWidgets import QHeaderView, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


class ColumnHeaderView(QHeaderView):
    """
    Enhanced table header with context menu for column operations.

    Provides right-click context menu with:
    - Cut/Copy/Paste column data
    - Insert/Delete column
    - Delimiter selection for clipboard operations

    Signals:
        column_cut_requested(int): Column cut requested
        column_copy_requested(int): Column copy requested
        column_paste_requested(int): Column paste requested
        column_insert_requested(int): Column insert requested
        column_delete_requested(int): Column delete requested
        delimiter_changed(str): Clipboard delimiter changed
    """

    # Signals for column operations
    column_cut_requested = pyqtSignal(int)
    column_copy_requested = pyqtSignal(int)
    column_paste_requested = pyqtSignal(int)
    column_insert_requested = pyqtSignal(int)
    column_delete_requested = pyqtSignal(int)
    delimiter_changed = pyqtSignal(str)

    def __init__(self, orientation=Qt.Horizontal, parent: Optional['QWidget'] = None):
        """
        Initialize the custom column header.

        Args:
            orientation: Header orientation (default: Horizontal)
            parent: Parent widget
        """
        super().__init__(orientation, parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Reference to data display widget for direct method calls (legacy support)
        self.data_display_widget = None

        # Current delimiter setting
        self._delimiter = '\t'

    def mousePressEvent(self, event):
        """Handle mouse press to select the entire column."""
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            # Get the column index
            column = self.logicalIndexAt(event.pos())
            if column >= 0:
                # Select the entire column
                table = self.parent()
                if table and hasattr(table, 'selectColumn'):
                    table.selectColumn(column)
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        """Show context menu for column header."""
        # Get the column index from the position
        column = self.logicalIndexAt(pos)
        if column < 0:
            return

        # Create the context menu
        menu = QMenu(self)

        # Cut action
        cut_action = QAction("&Cut", self)
        cut_action.setStatusTip("Cut column data to clipboard")
        cut_action.triggered.connect(lambda: self._cut_column(column))
        menu.addAction(cut_action)

        # Copy action
        copy_action = QAction("C&opy", self)
        copy_action.setStatusTip("Copy column data to clipboard")
        copy_action.triggered.connect(lambda: self._copy_column(column))
        menu.addAction(copy_action)

        # Paste action
        paste_action = QAction("&Paste", self)
        paste_action.setStatusTip("Paste data from clipboard to column")
        paste_action.triggered.connect(lambda: self._paste_column(column))
        menu.addAction(paste_action)

        menu.addSeparator()

        # Insert column action
        insert_action = QAction("&Insert Column", self)
        insert_action.setStatusTip("Insert a new column")
        insert_action.triggered.connect(lambda: self._insert_column(column))
        menu.addAction(insert_action)

        # Delete column action
        delete_action = QAction("&Delete Column", self)
        delete_action.setStatusTip("Delete this column")
        delete_action.triggered.connect(lambda: self._delete_column(column))
        menu.addAction(delete_action)

        menu.addSeparator()

        # Delimiter submenu
        delimiter_menu = menu.addMenu("&Delimiter")
        delimiter_menu.setStatusTip("Set delimiter for clipboard operations")

        # Tab delimiter
        tab_action = QAction("&Tab", self)
        tab_action.setCheckable(True)
        tab_action.setChecked(self._delimiter == '\t')
        tab_action.triggered.connect(lambda: self._set_delimiter('\t'))
        delimiter_menu.addAction(tab_action)

        # Comma delimiter
        comma_action = QAction("&Comma", self)
        comma_action.setCheckable(True)
        comma_action.setChecked(self._delimiter == ',')
        comma_action.triggered.connect(lambda: self._set_delimiter(','))
        delimiter_menu.addAction(comma_action)

        # Semicolon delimiter
        semicolon_action = QAction("&Semicolon", self)
        semicolon_action.setCheckable(True)
        semicolon_action.setChecked(self._delimiter == ';')
        semicolon_action.triggered.connect(lambda: self._set_delimiter(';'))
        delimiter_menu.addAction(semicolon_action)

        # Space delimiter
        space_action = QAction("&Space", self)
        space_action.setCheckable(True)
        space_action.setChecked(self._delimiter == ' ')
        space_action.triggered.connect(lambda: self._set_delimiter(' '))
        delimiter_menu.addAction(space_action)

        # Show the menu at the cursor position
        menu.exec_(self.mapToGlobal(pos))

    def _cut_column(self, column: int):
        """Cut column data to clipboard."""
        print(f"DEBUG: _cut_column called with column={column}")
        self._copy_column(column)
        self._clear_column(column)
        self.column_cut_requested.emit(column)

    def _clear_column(self, column: int):
        """Clear all data in the specified column."""
        print(f"DEBUG: _clear_column called with column={column}")
        # Get the table widget
        table = self.parent()
        if not table or not hasattr(table, 'rowCount') or not hasattr(table, 'columnCount'):
            print("DEBUG: Could not find table widget")
            return

        # Clear all items in the column
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item:
                item.setText("")
        print(f"DEBUG: Cleared column {column}")

    def _copy_column(self, column: int):
        """Copy column data to clipboard."""
        print(f"DEBUG: _copy_column called with column={column}")
        # Try legacy direct method call first
        if self.data_display_widget and hasattr(self.data_display_widget, 'copy_column_data'):
            print(f"DEBUG: Calling copy_column_data on DataDisplayWidget")
            self.data_display_widget.copy_column_data(column)
        else:
            # Emit signal for decoupled handling
            self.column_copy_requested.emit(column)
            print("DEBUG: Emitted column_copy_requested signal")

    def _paste_column(self, column: int):
        """Paste data from clipboard to column."""
        print(f"DEBUG: _paste_column called with column={column}")
        # Try legacy direct method call first
        if self.data_display_widget and hasattr(self.data_display_widget, 'paste_column_data'):
            print(f"DEBUG: Calling paste_column_data on DataDisplayWidget")
            self.data_display_widget.paste_column_data(column)
        else:
            # Emit signal for decoupled handling
            self.column_paste_requested.emit(column)
            print("DEBUG: Emitted column_paste_requested signal")

    def _insert_column(self, column: int):
        """Insert a new column."""
        print(f"DEBUG: _insert_column called with column={column}")
        # Try legacy direct method call first
        if self.data_display_widget and hasattr(self.data_display_widget, 'insert_column'):
            print(f"DEBUG: Calling insert_column on DataDisplayWidget")
            self.data_display_widget.insert_column(column)
        else:
            # Emit signal for decoupled handling
            self.column_insert_requested.emit(column)
            print("DEBUG: Emitted column_insert_requested signal")

    def _delete_column(self, column: int):
        """Delete a column."""
        print(f"DEBUG: _delete_column called with column={column}")
        # Try legacy direct method call first
        if self.data_display_widget and hasattr(self.data_display_widget, 'delete_column'):
            print(f"DEBUG: Calling delete_column on DataDisplayWidget")
            self.data_display_widget.delete_column(column)
        else:
            # Emit signal for decoupled handling
            self.column_delete_requested.emit(column)
            print("DEBUG: Emitted column_delete_requested signal")

    def _set_delimiter(self, delimiter: str):
        """Set the delimiter for clipboard operations."""
        print(f"DEBUG: _set_delimiter called with delimiter='{delimiter}'")
        self._delimiter = delimiter

        # Try legacy direct method call first
        if self.data_display_widget and hasattr(self.data_display_widget, 'set_clipboard_delimiter'):
            print(f"DEBUG: Calling set_clipboard_delimiter on DataDisplayWidget")
            self.data_display_widget.set_clipboard_delimiter(delimiter)

        # Always emit signal
        self.delimiter_changed.emit(delimiter)

    @property
    def delimiter(self) -> str:
        """Get the current delimiter setting."""
        return self._delimiter
