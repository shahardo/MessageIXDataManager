"""
Undo/redo management for table operations.
Maintains a stack of reversible commands for table editing.

Extracted from data_display_widget.py as part of refactoring.
This is an alias module for backwards compatibility - the UndoManager
class is also available from ui.components.data_display_widget for
existing code that imports it from there.
"""
from typing import List, Optional, Callable

from managers.commands import Command


class TableUndoManager:
    """
    Manages undo/redo stack for table operations.

    Implements Command pattern with a fixed-size history.
    Works with any Command object that implements do() and undo() methods.

    Usage:
        manager = TableUndoManager()
        manager.execute(EditCellCommand(...))  # Execute and add to stack
        manager.undo()  # Undo last command
        manager.redo()  # Redo last undone command
    """

    DEFAULT_MAX_HISTORY = 50

    def __init__(
        self,
        max_history: int = DEFAULT_MAX_HISTORY,
        on_state_changed: Optional[Callable[[], None]] = None
    ):
        """
        Initialize the undo manager.

        Args:
            max_history: Maximum number of commands to keep in history
            on_state_changed: Optional callback when undo/redo availability changes
        """
        self.max_history = max_history
        self._on_state_changed = on_state_changed
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def set_state_changed_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback for state changes."""
        self._on_state_changed = callback

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def execute(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack if successful.

        Args:
            command: Command object to execute

        Returns:
            True if command executed successfully
        """
        try:
            success = command.do()
            if success:
                # Add to undo stack
                self._undo_stack.append(command)

                # Clear redo stack when new operation is performed
                self._redo_stack.clear()

                # Limit stack size
                if len(self._undo_stack) > self.max_history:
                    self._undo_stack.pop(0)

                self._notify_state_changed()

            return success
        except Exception as e:
            print(f"Error executing command: {e}")
            return False

    def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if undo was performed successfully
        """
        if not self.can_undo():
            return False

        # Get the last command
        command = self._undo_stack.pop()

        try:
            # Undo the command
            success = command.undo()
            if success:
                # Add to redo stack
                self._redo_stack.append(command)
            else:
                # Put command back on undo stack if undo failed
                self._undo_stack.append(command)

            self._notify_state_changed()
            return success
        except Exception as e:
            print(f"Error undoing command: {e}")
            # Put command back on undo stack
            self._undo_stack.append(command)
            return False

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if redo was performed successfully
        """
        if not self.can_redo():
            return False

        # Get the last undone command
        command = self._redo_stack.pop()

        try:
            # Redo the command
            success = command.do()
            if success:
                # Add back to undo stack
                self._undo_stack.append(command)
            else:
                # Put command back on redo stack if redo failed
                self._redo_stack.append(command)

            self._notify_state_changed()
            return success
        except Exception as e:
            print(f"Error redoing command: {e}")
            # Put command back on redo stack
            self._redo_stack.append(command)
            return False

    def clear(self) -> None:
        """Clear all undo/redo history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_state_changed()

    # Alias for clear() to maintain compatibility
    def clear_history(self) -> None:
        """Clear all undo/redo history. Alias for clear()."""
        self.clear()

    def get_undo_description(self) -> str:
        """
        Get description of the operation that can be undone.

        Returns:
            Description string or empty string if no undo available
        """
        if self.can_undo():
            return getattr(self._undo_stack[-1], 'description', 'Undo')
        return ""

    def get_redo_description(self) -> str:
        """
        Get description of the operation that can be redone.

        Returns:
            Description string or empty string if no redo available
        """
        if self.can_redo():
            return getattr(self._redo_stack[-1], 'description', 'Redo')
        return ""

    def get_undo_count(self) -> int:
        """Get the number of undoable operations."""
        return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Get the number of redoable operations."""
        return len(self._redo_stack)

    def _notify_state_changed(self) -> None:
        """Notify observer of state change."""
        if self._on_state_changed:
            try:
                self._on_state_changed()
            except Exception as e:
                print(f"Error in state changed callback: {e}")


# Alias for backwards compatibility with existing imports
UndoManager = TableUndoManager
