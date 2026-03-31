"""
ScenarioSelectorDialog — lets the user pick two scenarios to compare.

Layout: two QListWidget panels side by side (Scenario A on the left,
Scenario B on the right).  Both lists always show all loaded scenarios.
The Compare button is enabled only when a selection has been made in
each list AND the two selections differ.
"""

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
    QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt
from typing import List, Tuple

from core.data_models import Scenario


class ScenarioSelectorDialog(QDialog):
    """Dialog for selecting two scenarios to compare."""

    def __init__(self, scenarios: List[Scenario], parent=None):
        super().__init__(parent)
        self._scenarios = scenarios
        self.setWindowTitle("Compare Scenarios")
        self.setMinimumSize(520, 320)
        self._setup_ui()
        self._populate_lists()
        self._validate()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Column headers
        header_row = QHBoxLayout()
        lbl_a = QLabel("<b>Scenario A</b>")
        lbl_b = QLabel("<b>Scenario B</b>")
        lbl_a.setAlignment(Qt.AlignCenter)
        lbl_b.setAlignment(Qt.AlignCenter)
        header_row.addWidget(lbl_a)
        header_row.addWidget(lbl_b)
        root.addLayout(header_row)

        # Two list widgets
        lists_row = QHBoxLayout()
        self.list_a = QListWidget()
        self.list_b = QListWidget()
        for lw in (self.list_a, self.list_b):
            lw.setAlternatingRowColors(True)
        lists_row.addWidget(self.list_a)
        lists_row.addWidget(self.list_b)
        root.addLayout(lists_row)

        # Warning label (shown when both sides select the same scenario)
        self._warning = QLabel("Select two <i>different</i> scenarios.")
        self._warning.setStyleSheet("color: #c0392b; font-size: 11px;")
        self._warning.setAlignment(Qt.AlignCenter)
        self._warning.setVisible(False)
        root.addWidget(self._warning)

        # OK / Cancel buttons
        self._buttons = QDialogButtonBox(self)
        self._compare_btn = self._buttons.addButton(
            "Compare", QDialogButtonBox.AcceptRole
        )
        self._compare_btn.setEnabled(False)
        self._buttons.addButton(QDialogButtonBox.Cancel)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # Connect selection signals
        self.list_a.currentRowChanged.connect(self._validate)
        self.list_b.currentRowChanged.connect(self._validate)

    def _populate_lists(self) -> None:
        """Fill both list widgets with every loaded scenario name."""
        for scenario in self._scenarios:
            self.list_a.addItem(scenario.name)
            self.list_b.addItem(scenario.name)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        """Enable Compare only when two different scenarios are selected."""
        item_a = self.list_a.currentItem()
        item_b = self.list_b.currentItem()

        both_selected = item_a is not None and item_b is not None
        same = both_selected and item_a.text() == item_b.text()

        self._warning.setVisible(same)
        self._compare_btn.setEnabled(both_selected and not same)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def selected_scenarios(self) -> Tuple[Scenario, Scenario]:
        """Return the two chosen Scenario objects (A, B)."""
        by_name = {s.name: s for s in self._scenarios}
        name_a = self.list_a.currentItem().text()
        name_b = self.list_b.currentItem().text()
        return by_name[name_a], by_name[name_b]
