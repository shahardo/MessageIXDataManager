"""
Find Widget - Provides floating search functionality for parameters and data tables

A context-aware find widget that can search either parameter trees or data tables
based on current selection context.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QEvent
from PyQt5.QtGui import QKeyEvent
from typing import Optional, List, Tuple


class FindWidget(QWidget):
    """Floating find widget with navigation capabilities"""

    # Signals
    find_next_requested = pyqtSignal(str)  # search_text
    find_previous_requested = pyqtSignal(str)  # search_text
    find_text_changed = pyqtSignal(str)  # search_text
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Widget is now a child of the parent window, no special attributes needed

        self.setFixedHeight(34)
        self.setMinimumWidth(260)
        self.setMaximumWidth(560)

        # State
        self.current_matches = 0
        self.total_matches = 0
        self.current_match_index = -1

        self.setup_ui()
        self.setup_connections()

    # Stylesheet applied to search_input to signal "no match" state
    _NO_MATCH_INPUT_STYLE = """
        QLineEdit {
            border: 1px solid #e08080;
            border-radius: 4px;
            padding: 1px 6px;
            background: #fff0f0;
            font-size: 12px;
        }
    """
    _NORMAL_INPUT_STYLE = ""   # empty = inherits from widget stylesheet

    def setup_ui(self):
        """Set up the find widget UI"""
        self.inner_widget = QWidget(self)
        self.inner_widget.setObjectName("findInnerWidget")

        layout = QHBoxLayout(self.inner_widget)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(2)

        # Search input — expands to fill available space; no "Find:" label needed
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find in table…")
        self.search_input.setFixedHeight(24)
        layout.addWidget(self.search_input, stretch=1)

        layout.addSpacing(4)

        # Match counter — shown as "3 / 12", hidden when idle
        self.match_label = QLabel("")
        self.match_label.setObjectName("matchLabel")
        self.match_label.setFixedWidth(52)
        self.match_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.match_label)

        # Thin vertical divider between counter and nav buttons
        divider = QWidget()
        divider.setFixedSize(1, 18)
        divider.setStyleSheet("background: #d0d0d0;")
        layout.addWidget(divider)

        layout.addSpacing(2)

        # ↑ Previous / ↓ Next navigation
        self.prev_button = QPushButton("↑")
        self.prev_button.setObjectName("navBtn")
        self.prev_button.setToolTip("Previous match  (Shift+Enter)")
        self.prev_button.setFixedSize(26, 26)
        self.prev_button.setEnabled(False)
        layout.addWidget(self.prev_button)

        self.next_button = QPushButton("↓")
        self.next_button.setObjectName("navBtn")
        self.next_button.setToolTip("Next match  (Enter)")
        self.next_button.setFixedSize(26, 26)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        layout.addSpacing(2)

        # Close button
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeBtn")
        self.close_button.setToolTip("Close  (Esc)")
        self.close_button.setFixedSize(24, 26)
        layout.addWidget(self.close_button)

        # Outer layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.inner_widget)

        self.setStyleSheet("""
            #findInnerWidget {
                background: #e0e0e0;
                border: 1px solid #a0a0a0;
                border-radius: 5px;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 1px 6px;
                background: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
            }
            #matchLabel {
                color: #999;
                font-size: 11px;
            }
            QPushButton#navBtn {
                font-size: 15px;
                border: none;
                border-radius: 4px;
                background: transparent;
                color: #555;
            }
            QPushButton#navBtn:hover  { background: rgba(0,0,0,0.08); color: #111; }
            QPushButton#navBtn:pressed { background: rgba(0,0,0,0.15); }
            QPushButton#navBtn:disabled { color: #ccc; }
            QPushButton#closeBtn {
                font-size: 12px;
                border: none;
                border-radius: 4px;
                background: transparent;
                color: #888;
            }
            QPushButton#closeBtn:hover { background: rgba(200,0,0,0.1); color: #c00; }
        """)

    def setup_connections(self):
        """Set up signal connections"""
        self.search_input.textChanged.connect(self._on_text_changed)
        # NOTE: returnPressed is NOT connected here; Return/Shift+Return are
        # handled entirely in the event filter so there is exactly one code path
        # per key press and no risk of double-firing.
        self.next_button.clicked.connect(self._on_next_clicked)
        self.prev_button.clicked.connect(self._on_previous_clicked)
        self.close_button.clicked.connect(self._on_close_clicked)
        # The event filter intercepts navigation keys before QLineEdit consumes them.
        self.search_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Handle navigation keys inside the search field.

        All keys that drive match navigation are consumed here (return True) so
        that QLineEdit never sees them and cannot emit a duplicate signal.
        """
        if obj is self.search_input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() & Qt.ShiftModifier:
                self._on_previous_clicked()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._on_next_clicked()
                return True
            if key == Qt.Key_Down:
                self._on_next_clicked()
                return True
            if key == Qt.Key_Up:
                self._on_previous_clicked()
                return True
        return super().eventFilter(obj, event)

    def show_at_position(self, position: QPoint, search_mode: str = "parameter"):
        """Show the find widget at a specific position"""
        self.move(position)
        self.search_input.setFocus()
        self.search_input.selectAll()
        self.show()
        self.raise_()

        # Update placeholder based on search mode
        if search_mode == "parameter":
            self.search_input.setPlaceholderText("Find parameter…")
        else:
            self.search_input.setPlaceholderText("Find in table…")

    def update_match_count(self, current: int, total: int):
        """Update the match counter display and apply no-match styling if needed."""
        self.current_matches = current
        self.total_matches = total
        self.current_match_index = current - 1 if total > 0 else -1

        has_text = bool(self.search_input.text().strip())

        if total == 0:
            # Show "0 / 0" when searching but nothing matched; blank when idle
            self.match_label.setText("0 / 0" if has_text else "")
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            # Pink tint on the input field when text is present but nothing matched
            self.search_input.setStyleSheet(
                self._NO_MATCH_INPUT_STYLE if has_text else self._NORMAL_INPUT_STYLE
            )
        else:
            self.match_label.setText(f"{current} / {total}")
            self.next_button.setEnabled(True)
            self.prev_button.setEnabled(total > 1)
            self.search_input.setStyleSheet(self._NORMAL_INPUT_STYLE)

    def get_search_text(self) -> str:
        """Get current search text"""
        return self.search_input.text().strip()

    def set_search_text(self, text: str):
        """Set search text"""
        self.search_input.setText(text)
        self.search_input.selectAll()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events on the widget itself (not the input field).
        Navigation keys are fully handled by the eventFilter on search_input.
        """
        if event.key() == Qt.Key_Escape:
            self._on_close_clicked()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _on_text_changed(self, text: str):
        """Handle search text changes"""
        search_text = text.strip()
        if search_text:
            self.find_text_changed.emit(search_text)
        else:
            self.update_match_count(0, 0)

    def _on_next_clicked(self):
        """Handle next button click"""
        search_text = self.get_search_text()
        if search_text:
            self.find_next_requested.emit(search_text)

    def _on_previous_clicked(self):
        """Handle previous button click"""
        search_text = self.get_search_text()
        if search_text:
            self.find_previous_requested.emit(search_text)

    def _on_close_clicked(self):
        """Handle close button click"""
        self.hide()
        self.closed.emit()

    def focusOutEvent(self, event):
        """Handle focus out - keep widget visible but don't close automatically"""
        # Don't hide on focus out - let user close explicitly or via keyboard
        super().focusOutEvent(event)
