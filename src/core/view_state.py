"""
View state management for the main application window.
Centralizes all view-related state in a single, observable object.

Extracted from main_window.py as part of refactoring to reduce God Class.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Any
from core.data_models import Scenario


@dataclass
class ViewState:
    """
    Immutable-style state container for application view state.

    Use the update() method to create modified copies for state transitions.
    All view-related state variables are consolidated here for clarity.
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
    current_search_mode: str = "parameter"  # "parameter" or "table"

    def update(self, **kwargs) -> 'ViewState':
        """
        Create a new ViewState with updated values.

        Args:
            **kwargs: State fields to update

        Returns:
            New ViewState instance with updated values
        """
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

    @property
    def has_scenario(self) -> bool:
        """Check if a scenario is currently selected."""
        return self.selected_scenario is not None

    @property
    def is_input_view(self) -> bool:
        """Check if currently in input view."""
        return self.current_view == "input"

    @property
    def is_results_view(self) -> bool:
        """Check if currently in results view."""
        return self.current_view == "results"

    def get_last_selected_parameter(self) -> Optional[str]:
        """Get the last selected parameter for the current view."""
        if self.is_results_view:
            return self.last_selected_results_parameter
        return self.last_selected_input_parameter


class ViewStateManager:
    """
    Manages view state with observer pattern for change notifications.

    Usage:
        manager = ViewStateManager()
        manager.add_observer(my_callback)
        manager.update(current_view="results")  # triggers callback
    """

    def __init__(self):
        """Initialize with default state."""
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
            try:
                observer(old_state, self._state)
            except Exception as e:
                print(f"Error notifying observer: {e}")

    def add_observer(self, callback: Callable[[ViewState, ViewState], None]) -> None:
        """
        Add an observer to be notified of state changes.

        Args:
            callback: Function taking (old_state, new_state) arguments
        """
        self._observers.append(callback)

    def remove_observer(self, callback: Callable[[ViewState, ViewState], None]) -> None:
        """
        Remove an observer.

        Args:
            callback: The callback to remove
        """
        if callback in self._observers:
            self._observers.remove(callback)

    # Convenience methods for common operations

    def set_current_view(self, view: str) -> None:
        """Set the current view mode."""
        self.update(current_view=view)

    def set_input_file(self, file_path: Optional[str]) -> None:
        """Set the selected input file."""
        self.update(selected_input_file=file_path)

    def set_results_file(self, file_path: Optional[str]) -> None:
        """Set the selected results file."""
        self.update(selected_results_file=file_path)

    def set_scenario(self, scenario: Optional[Scenario]) -> None:
        """Set the selected scenario."""
        self.update(selected_scenario=scenario)

    def set_displayed_parameter(
        self,
        param_name: Optional[str],
        is_results: bool = False
    ) -> None:
        """
        Set the currently displayed parameter.

        Args:
            param_name: Name of the parameter being displayed
            is_results: Whether this is a results parameter
        """
        self.update(
            current_displayed_parameter=param_name,
            current_displayed_is_results=is_results
        )

    def remember_selected_parameter(self, param_name: str, is_results: bool) -> None:
        """
        Remember the last selected parameter for a view.

        Args:
            param_name: Name of the parameter
            is_results: Whether this is for results view
        """
        if is_results:
            self.update(last_selected_results_parameter=param_name)
        else:
            self.update(last_selected_input_parameter=param_name)

    def set_search_state(
        self,
        mode: Optional[str] = None,
        parameter_search: Optional[str] = None,
        table_search: Optional[str] = None
    ) -> None:
        """
        Update search state.

        Args:
            mode: Search mode ("parameter" or "table")
            parameter_search: Last parameter search text
            table_search: Last table search text
        """
        updates = {}
        if mode is not None:
            updates['current_search_mode'] = mode
        if parameter_search is not None:
            updates['last_parameter_search'] = parameter_search
        if table_search is not None:
            updates['last_table_search'] = table_search
        if updates:
            self.update(**updates)

    def reset(self) -> None:
        """Reset to default state."""
        self._state = ViewState()
        # Notify with empty old state
        for observer in self._observers:
            try:
                observer(ViewState(), self._state)
            except Exception as e:
                print(f"Error notifying observer during reset: {e}")
