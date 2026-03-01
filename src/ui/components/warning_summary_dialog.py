"""
WarningSummaryDialog — displayed after the MESSAGEix solver finishes when
one or more warnings were detected in the solver output.

Shows a table of parsed warnings with their category, fix suggestion, and
action buttons ("Go to Parameter" and optionally "Auto-fix Unit").
"""

from __future__ import annotations

from typing import List

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from managers.warning_analyzer import (
    SolverWarning,
    WarningAnalyzer,
    CATEGORY_UNIT_NOT_FOUND,
)


# Colour codes for category badges
_CATEGORY_COLORS: dict[str, str] = {
    "unit_not_found": "#E67E22",   # orange
    "no_values":      "#3498DB",   # blue
    "duplicate":      "#9B59B6",   # purple
    "unknown":        "#7F8C8D",   # grey
}


class WarningSummaryDialog(QDialog):
    """
    Modal dialog listing all solver warnings after a run completes.

    Signals:
        navigate_requested(parameter_name): emitted when the user clicks
            "Go to Parameter" for a warning with kind == "parameter".
        autofix_requested(parameter_name, bad_unit, good_unit): emitted when
            the user clicks "Auto-fix Unit" for a fixable unit warning.
    """

    navigate_requested = pyqtSignal(str)   # parameter name
    autofix_requested  = pyqtSignal(str, str, str)  # name, bad_unit, good_unit

    # Column indices
    _COL_TYPE    = 0
    _COL_NAME    = 1
    _COL_ISSUE   = 2
    _COL_FIX     = 3
    _COL_ACTIONS = 4

    def __init__(self, warnings: List[SolverWarning], parent: QWidget | None = None):
        super().__init__(parent)
        self._warnings = warnings
        self.setWindowTitle("Solver Warnings")
        self.setMinimumSize(900, 400)
        self.resize(1100, 500)
        # Non-modal: user can interact with the main window while this is open.
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint
        )
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header
        n = len(self._warnings)
        header = QLabel(
            f"<b>Solver completed with {n} warning{'s' if n != 1 else ''}.</b><br>"
            "<span style='color:#888;'>Review the warnings below. "
            "Use the action buttons to navigate to a parameter or apply "
            "automatic fixes where available.</span>"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "Type", "Name", "Issue", "Suggested Fix", "Actions"
        ])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setDefaultSectionSize(180)
        self._table.setColumnWidth(self._COL_TYPE,    100)
        self._table.setColumnWidth(self._COL_NAME,    160)
        self._table.setColumnWidth(self._COL_ISSUE,   160)
        self._table.setColumnWidth(self._COL_FIX,     320)
        self._table.setColumnWidth(self._COL_ACTIONS, 180)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setDefaultSectionSize(56)
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._table)

        self._populate_table()

        # Resize rows to content after populating
        self._table.resizeRowsToContents()

        # Bottom buttons (plain layout — no QDialogButtonBox so the window
        # stays non-modal and the standard Close shortcut isn't intercepted)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(copy_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _populate_table(self):
        self._table.setRowCount(len(self._warnings))
        for row, w in enumerate(self._warnings):
            self._add_row(row, w)

    def _add_row(self, row: int, w: SolverWarning):
        # --- Type badge -------------------------------------------------------
        label = WarningAnalyzer.category_label(w.category)
        type_item = QTableWidgetItem(label)
        type_item.setTextAlignment(Qt.AlignCenter)
        color = _CATEGORY_COLORS.get(w.category, "#7F8C8D")
        type_item.setBackground(QColor(color))
        type_item.setForeground(QColor("#FFFFFF"))
        bold = QFont()
        bold.setBold(True)
        type_item.setFont(bold)
        self._table.setItem(row, self._COL_TYPE, type_item)

        # --- Name -------------------------------------------------------------
        name_item = QTableWidgetItem(w.name)
        name_item.setFont(QFont("Consolas", 9))
        self._table.setItem(row, self._COL_NAME, name_item)

        # --- Issue (short exception) ------------------------------------------
        issue_text = w.exception_text[:120] + ("…" if len(w.exception_text) > 120 else "")
        issue_item = QTableWidgetItem(issue_text)
        issue_item.setToolTip(w.exception_text)
        self._table.setItem(row, self._COL_ISSUE, issue_item)

        # --- Suggested fix ----------------------------------------------------
        fix_item = QTableWidgetItem(w.fix_description)
        fix_item.setToolTip(w.fix_description)
        self._table.setItem(row, self._COL_FIX, fix_item)

        # --- Actions ----------------------------------------------------------
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)

        if w.kind == "parameter":
            nav_btn = QPushButton("Go to Parameter")
            nav_btn.setToolTip(f"Navigate to parameter '{w.name}' in the table view")
            nav_btn.clicked.connect(lambda _, name=w.name: self._on_navigate(name))
            action_layout.addWidget(nav_btn)

        if w.fix_available and w.category == CATEGORY_UNIT_NOT_FOUND and w.good_unit:
            fix_btn = QPushButton(f"Fix unit → '{w.good_unit}'")
            fix_btn.setToolTip(
                f"Replace unit '{w.bad_unit}' with '{w.good_unit}' in '{w.name}'"
            )
            fix_btn.setStyleSheet("QPushButton { color: #27AE60; font-weight: bold; }")
            fix_btn.clicked.connect(
                lambda _, name=w.name, bad=w.bad_unit, good=w.good_unit:
                    self._on_autofix(name, bad, good)
            )
            action_layout.addWidget(fix_btn)

        action_layout.addStretch()
        self._table.setCellWidget(row, self._COL_ACTIONS, action_widget)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_navigate(self, parameter_name: str):
        """Emit navigate signal; main window is brought to front."""
        self.navigate_requested.emit(parameter_name)

    def _on_autofix(self, parameter_name: str, bad_unit: str, good_unit: str):
        """Emit autofix signal; keep window open so user can continue reviewing."""
        self.autofix_requested.emit(parameter_name, bad_unit, good_unit)

    def _copy_to_clipboard(self):
        """Copy the warning table as plain text to the system clipboard."""
        lines = ["\t".join(["Type", "Name", "Issue", "Suggested Fix"])]
        for w in self._warnings:
            lines.append("\t".join([
                WarningAnalyzer.category_label(w.category),
                w.name,
                w.exception_text,
                w.fix_description,
            ]))
        QApplication.clipboard().setText("\n".join(lines))
