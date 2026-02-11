"""
Shared user preferences used by DataDisplayWidget, PostprocessingDashboard,
and any other component that needs year-range filtering.

MainWindow creates one instance and passes it to all consumers.  Changes made
anywhere are visible everywhere because all consumers read/write the same object.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class UserPreferences(QObject):
    """Shared user preferences (year range, etc.).

    Attributes:
        min_year (int): Lower bound of the year range.
        max_year (int): Upper bound of the year range.
        limit_enabled (bool): Whether year filtering is active.

    Signals:
        changed: Emitted when any attribute changes.
    """

    changed = pyqtSignal()

    def __init__(self, min_year: int = 2020, max_year: int = 2050,
                 limit_enabled: bool = True, parent=None):
        super().__init__(parent)
        self._min_year = min_year
        self._max_year = max_year
        self._limit_enabled = limit_enabled

    # --- properties ----------------------------------------------------------

    @property
    def min_year(self) -> int:
        return self._min_year

    @min_year.setter
    def min_year(self, value: int):
        if value != self._min_year:
            self._min_year = value
            self.changed.emit()

    @property
    def max_year(self) -> int:
        return self._max_year

    @max_year.setter
    def max_year(self, value: int):
        if value != self._max_year:
            self._max_year = value
            self.changed.emit()

    @property
    def limit_enabled(self) -> bool:
        return self._limit_enabled

    @limit_enabled.setter
    def limit_enabled(self, value: bool):
        if value != self._limit_enabled:
            self._limit_enabled = value
            self.changed.emit()

    # --- dict helpers --------------------------------------------------------

    def to_dict(self) -> dict:
        """Return year options as a dict (same format as get_year_options)."""
        return {
            'YearsLimitEnabled': self._limit_enabled,
            'MinYear': self._min_year,
            'MaxYear': self._max_year,
        }

    def update_from_dict(self, options: dict):
        """Bulk-update from a dict, emitting *changed* at most once."""
        dirty = False
        if 'MinYear' in options and options['MinYear'] != self._min_year:
            self._min_year = options['MinYear']
            dirty = True
        if 'MaxYear' in options and options['MaxYear'] != self._max_year:
            self._max_year = options['MaxYear']
            dirty = True
        if 'YearsLimitEnabled' in options and options['YearsLimitEnabled'] != self._limit_enabled:
            self._limit_enabled = options['YearsLimitEnabled']
            dirty = True
        if dirty:
            self.changed.emit()


# Backward-compatible alias
YearPreferences = UserPreferences
