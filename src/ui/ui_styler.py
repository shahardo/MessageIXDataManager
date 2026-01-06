"""
UI Styler - Centralized styling utilities for MessageIX Data Manager

This module provides centralized styling and setup methods to reduce inline
styling code throughout the application.
"""

import os
from typing import List, Optional
from PyQt5.QtWidgets import (
    QApplication, QTableWidget, QPushButton, QComboBox, QLabel,
    QCheckBox, QGroupBox, QTreeWidget, QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor


class UIStyler:
    """Centralized UI styling and setup utilities"""

    @staticmethod
    def apply_stylesheet(app: QApplication) -> None:
        """Load and apply the application stylesheet"""
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
        else:
            print(f"Warning: Stylesheet not found at {style_path}")

    @staticmethod
    def setup_table_widget(table: QTableWidget) -> None:
        """Configure table widget with consistent settings"""
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(22)

        # Apply table styling class
        current_style = table.styleSheet()
        table.setStyleSheet(current_style + "\nQTableWidget { /* Additional table styling */ }")

    @staticmethod
    def setup_table_header(header: QHeaderView) -> None:
        """Configure table header with consistent styling"""
        # The main styling is handled by the stylesheet, but we can add specific configurations here
        header.setStretchLastSection(True)

    @staticmethod
    def setup_button_group(buttons: List[QPushButton], checkable: bool = False) -> None:
        """Setup a group of related buttons with consistent properties"""
        for button in buttons:
            if checkable:
                button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)

    @staticmethod
    def setup_parameter_title_label(label: QLabel, is_small: bool = False) -> None:
        """Setup parameter title label with appropriate styling class"""
        if is_small:
            label.setProperty("class", "parameter-title-small")
        else:
            label.setProperty("class", "parameter-title")
        # Force style recalculation
        label.style().unpolish(label)
        label.style().polish(label)

    @staticmethod
    def setup_view_toggle_button(button: QPushButton) -> None:
        """Setup view toggle button with appropriate styling class"""
        button.setProperty("class", "view-toggle-button")
        button.setCheckable(True)
        button.setChecked(False)
        button.setCursor(Qt.PointingHandCursor)
        button.setEnabled(False)
        # Force style recalculation
        button.style().unpolish(button)
        button.style().polish(button)

    @staticmethod
    def setup_filter_label(label: QLabel) -> None:
        """Setup filter label with appropriate styling class"""
        label.setProperty("class", "filter-label")
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # Apply explicit styling to ensure no outlines
        current_style = label.styleSheet()
        label.setStyleSheet(current_style + "QLabel { border: none; outline: none; } QLabel:focus { border: none; outline: none; } QLabel:hover { border: none; outline: none; }")
        # Force style recalculation
        label.style().unpolish(label)
        label.style().polish(label)

    @staticmethod
    def setup_combo_box(combo: QComboBox) -> None:
        """Setup combo box with consistent styling"""
        # The main styling is handled by the stylesheet
        pass

    @staticmethod
    def setup_checkbox(checkbox: QCheckBox) -> None:
        """Setup checkbox with consistent styling"""
        # Apply explicit styling to ensure no outlines
        current_style = checkbox.styleSheet()
        checkbox.setStyleSheet(current_style + "QCheckBox { border: none; outline: none; } QCheckBox:focus { border: none; outline: none; } QCheckBox:hover { border: none; outline: none; }")
        # The main styling is handled by the stylesheet
        pass

    @staticmethod
    def setup_group_box(group_box: QGroupBox) -> None:
        """Setup group box with consistent styling"""
        # The main styling is handled by the stylesheet
        pass

    @staticmethod
    def setup_tree_widget(tree: QTreeWidget) -> None:
        """Setup tree widget with consistent styling and settings"""
        tree.setAlternatingRowColors(True)

    @staticmethod
    def setup_splitter(splitter: QSplitter) -> None:
        """Setup splitter with consistent styling"""
        # The main styling is handled by the stylesheet
        pass

    @staticmethod
    def setup_chart_button(button: QPushButton) -> None:
        """Setup chart type button with appropriate styling class"""
        button.setProperty("class", "chart-button")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        # Force style recalculation
        button.style().unpolish(button)
        button.style().polish(button)

    @staticmethod
    def setup_remove_button(button: QPushButton) -> None:
        """Setup remove button with appropriate styling class"""
        button.setProperty("class", "remove-button")
        button.setFixedSize(20, 20)
        # Force style recalculation
        button.style().unpolish(button)
        button.style().polish(button)

    @staticmethod
    def apply_class_styling(widget, class_name: str) -> None:
        """Apply a CSS class to a widget for styling"""
        widget.setProperty("class", class_name)
        # Force style recalculation
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @staticmethod
    def refresh_widget_styling(widget) -> None:
        """Force refresh of widget styling after property changes"""
        widget.style().unpolish(widget)
        widget.style().polish(widget)


class MainWindowUI:
    """UI setup logic extracted from MainWindow for better organization"""

    def __init__(self, main_window):
        """Initialize with reference to main window"""
        self.main_window = main_window

    def setup_splitters(self) -> None:
        """Configure all splitter properties"""
        # Left splitter (navigator and parameter tree)
        self.main_window.leftSplitter.setStretchFactor(0, 0)  # navigator fixed
        self.main_window.leftSplitter.setStretchFactor(1, 1)  # parameter tree stretches

        # Main splitter (left panel and content)
        self.main_window.splitter.setSizes([300, 900])
        self.main_window.splitter.setStretchFactor(0, 0)  # left panel fixed
        self.main_window.splitter.setStretchFactor(1, 1)  # content area stretches

        # Content splitter (data and console)
        self.main_window.contentSplitter.setStretchFactor(0, 1)  # data container stretches
        self.main_window.contentSplitter.setStretchFactor(1, 0)  # console fixed

        # Data splitter (table and chart)
        self.main_window.dataSplitter.setSizes([600, 400])
        self.main_window.dataSplitter.setStretchFactor(0, 0)  # table container fixed
        self.main_window.dataSplitter.setStretchFactor(1, 1)  # graph container stretches

    def setup_table_styling(self) -> None:
        """Configure table appearance and behavior"""
        # Apply consistent table styling
        UIStyler.setup_table_widget(self.main_window.param_table)

        # Configure header
        header = self.main_window.param_table.horizontalHeader()
        UIStyler.setup_table_header(header)

    def setup_chart_buttons(self) -> None:
        """Setup chart type selection buttons"""
        buttons = [
            self.main_window.simple_bar_btn,
            self.main_window.stacked_bar_btn,
            self.main_window.line_chart_btn,
            self.main_window.stacked_area_btn
        ]

        UIStyler.setup_button_group(buttons, checkable=True)

        # Set initial state
        self.main_window.simple_bar_btn.setChecked(True)

    def setup_navigator_styling(self) -> None:
        """Setup navigator widget styling"""
        UIStyler.setup_tree_widget(self.main_window.file_navigator)

    def apply_all_styling(self) -> None:
        """Apply all centralized styling to main window components"""
        # Apply parameter title styling
        UIStyler.setup_parameter_title_label(self.main_window.param_title)

        # Apply table styling
        self.setup_table_styling()

        # Apply chart button styling
        self.setup_chart_buttons()

        # Apply navigator styling
        self.setup_navigator_styling()

        # Apply splitter styling
        UIStyler.setup_splitter(self.main_window.splitter)
        UIStyler.setup_splitter(self.main_window.leftSplitter)
        UIStyler.setup_splitter(self.main_window.contentSplitter)
        UIStyler.setup_splitter(self.main_window.dataSplitter)
