"""
Find Widget - Provides floating search functionality for parameters and data tables

A context-aware find widget that can search either parameter trees or data tables
based on current selection context.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
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

        # Set minimum size to prevent compression
        self.setMinimumSize(300, 40)
        self.setMaximumSize(600, 50)

        # State
        self.current_matches = 0
        self.total_matches = 0
        self.current_match_index = -1

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Set up the find widget UI"""
        # Create inner container widget with background
        self.inner_widget = QWidget(self)
        self.inner_widget.setObjectName("findInnerWidget")
 
        # Main layout
        layout = QHBoxLayout(self.inner_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Find label
        find_label = QLabel("Find:")
        find_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(find_label)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search text...")
        self.search_input.setFixedWidth(200)
        # self.search_input.setMaximumWidth(300)
        layout.addWidget(self.search_input)

        # Previous button
        self.prev_button = QPushButton("<")
        self.prev_button.setToolTip("Find Previous (Shift+Enter)")
        self.prev_button.setFixedSize(30, 25)
        self.prev_button.setEnabled(False)
        layout.addWidget(self.prev_button)

        # Next button
        self.next_button = QPushButton(">")
        self.next_button.setToolTip("Find Next (Enter)")
        self.next_button.setFixedSize(30, 25)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        # Match counter
        self.match_label = QLabel("0 of 0")
        self.match_label.setStyleSheet("color: #666; font-size: 11px;")
        self.match_label.setFixedWidth(60)
        layout.addWidget(self.match_label)

        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setToolTip("Close (Esc)")
        self.close_button.setFixedSize(25, 25)
        self.close_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                border: none;
                background: transparent;
                color: #666;
            }
            QPushButton:hover {
                color: #333;
                background: rgba(255, 0, 0, 0.1);
            }
        """)
        layout.addWidget(self.close_button)

        # Main layout for the outer widget
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.inner_widget)

        # Styling - only the inner widget gets the background and border
        self.setStyleSheet("""
            #findInnerWidget {
                background: rgba(250, 250, 250, 0.98);
                border: 1px solid #999;
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            }
            QLineEdit {
                padding: 3px 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #4a90e2;
            }
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 3px;
                background: #f8f8f8;
                padding: 2px;
            }
            QPushButton:hover {
                background: #e8e8e8;
            }
            QPushButton:pressed {
                background: #d8d8d8;
            }
            QPushButton:disabled {
                background: #f0f0f0;
                color: #999;
            }
        """)

    def setup_connections(self):
        """Set up signal connections"""
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        self.next_button.clicked.connect(self._on_next_clicked)
        self.prev_button.clicked.connect(self._on_previous_clicked)
        self.close_button.clicked.connect(self._on_close_clicked)

    def show_at_position(self, position: QPoint, search_mode: str = "parameter"):
        """Show the find widget at a specific position"""
        self.move(position)
        self.search_input.setFocus()
        self.search_input.selectAll()
        self.show()
        self.raise_()

        # Update placeholder based on search mode
        if search_mode == "parameter":
            self.search_input.setPlaceholderText("Search parameters...")
        else:
            self.search_input.setPlaceholderText("Search table data...")

    def update_match_count(self, current: int, total: int):
        """Update the match counter display"""
        self.current_matches = current
        self.total_matches = total
        self.current_match_index = current - 1 if total > 0 else -1

        if total == 0:
            self.match_label.setText("0 of 0")
            self.next_button.setEnabled(False)
            self.prev_button.setEnabled(False)
        else:
            self.match_label.setText(f"{current} of {total}")
            self.next_button.setEnabled(True)
            self.prev_button.setEnabled(total > 1)

    def get_search_text(self) -> str:
        """Get current search text"""
        return self.search_input.text().strip()

    def set_search_text(self, text: str):
        """Set search text"""
        self.search_input.setText(text)
        self.search_input.selectAll()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self._on_close_clicked()
            event.accept()
        elif event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
            self._on_previous_clicked()
            event.accept()
        elif event.key() == Qt.Key_Return:
            self._on_next_clicked()
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

    def _on_return_pressed(self):
        """Handle return key press"""
        self._on_next_clicked()

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
