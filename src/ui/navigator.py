"""
Project Navigator component for MESSAGEix Data Manager

Provides a tree-based navigation interface for managing loaded input and result files,
with support for file removal and loading new files.
"""

import os
from typing import List, Optional
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout, QWidget, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QResizeEvent
from .ui_styler import UIStyler


class ProjectNavigator(QTreeWidget):
    """
    ProjectNavigator class for displaying and managing loaded files.

    A tree widget that shows loaded input and result files with options to remove them,
    and provides placeholders for loading new files when none are present.

    Attributes:
        input_files: List of currently loaded input file paths
        results_files: List of currently loaded result file paths

    Signals:
        file_selected: Emitted when a file is selected (file_path: str, file_type: str)
        load_files_requested: Emitted when "no files loaded" placeholder is clicked (file_type: str)
        file_removed: Emitted when a file removal is requested (file_path: str, file_type: str)
    """

    # Signal emitted when a file is selected (file_path, file_type)
    file_selected = pyqtSignal(str, str)

    # Signal emitted when "no files loaded" is clicked (file_type: "input" or "results")
    load_files_requested = pyqtSignal(str)

    # Signal emitted when a file is removed (file_path, file_type)
    file_removed = pyqtSignal(str, str)

    def __init__(self) -> None:
        """
        Initialize the ProjectNavigator.

        Sets up the tree widget with proper headers, initializes file lists,
        and connects signals for user interaction.
        """
        super().__init__()
        self.setHeaderLabels(["Files", ""])  # Two columns: filename and action
        self.input_files: List[str] = []  # Store input file paths
        self.results_files: List[str] = []  # Store results file paths
        self._setup_ui()
        self._load_recent_files()
        self.itemSelectionChanged.connect(self._on_item_selected)

    def _setup_ui(self) -> None:
        """
        Set up the navigator UI.

        Configures the tree widget dimensions, column widths, and visual properties.
        """
        self.setMinimumWidth(150)  # Reduced minimum width to allow more flexibility

        # Set column resize modes
        self.setColumnWidth(0, 300)   # Action column width
        self.setColumnWidth(1, 30)   # Action column width

        # Enable context menu
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self._show_context_menu)

    def _load_recent_files(self) -> None:
        """
        Load and display recent files structure.

        Creates the initial tree structure with placeholder items for inputs,
        results, and recent files sections.
        """
        # For now, create placeholder structure
        # TODO: Load from settings/config file

        # Root items
        inputs_item = QTreeWidgetItem(self)
        inputs_item.setText(0, "Inputs")
        inputs_item.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))

        results_item = QTreeWidgetItem(self)
        results_item.setText(0, "Results")
        results_item.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))

        recent_item = QTreeWidgetItem(self)
        recent_item.setText(0, "Recent Files")
        recent_item.setIcon(0, self.style().standardIcon(self.style().SP_DirIcon))

        # Add some example items (these would be loaded from config)
        example_input = QTreeWidgetItem(inputs_item)
        example_input.setText(0, "No input files loaded")
        example_input.setData(0, Qt.UserRole, ("no_files", "input"))  # Mark as clickable

        example_result = QTreeWidgetItem(results_item)
        example_result.setText(0, "No result files loaded")
        example_result.setData(0, Qt.UserRole, ("no_files", "results"))  # Mark as clickable

        # Expand top-level items
        inputs_item.setExpanded(True)
        results_item.setExpanded(True)
        recent_item.setExpanded(True)

    def add_recent_file(self, file_path: str, file_type: str = "input") -> None:
        """
        Add a file to the recent files list.

        Args:
            file_path: Path to the file to add
            file_type: Type of file ("input" or "results")
        """
        # TODO: Implement actual recent files management
        print(f"Adding recent file: {file_path} (type: {file_type})")

    def _remove_file(self, file_path: str, file_type: str) -> None:
        """
        Handle file removal request.

        Emits the file_removed signal to notify listeners that a file
        should be removed from the application.

        Args:
            file_path: Path of the file to remove
            file_type: Type of file being removed ("input" or "results")
        """
        self.file_removed.emit(file_path, file_type)

    def update_input_files(self, files_list: Optional[List[str]]) -> None:
        """
        Update the inputs section with loaded files.

        Refreshes the input files display in the navigator tree, showing either
        a placeholder message or the list of loaded files with remove buttons.

        Args:
            files_list: List of input file paths, or None for empty list
        """
        self.input_files = files_list or []

        # Find inputs item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Inputs":
                # Clear existing children
                item.takeChildren()

                if not files_list:
                    no_files = QTreeWidgetItem(item)
                    no_files.setText(0, "No input files loaded")
                    no_files.setData(0, Qt.UserRole, ("no_files", "input"))  # Mark as clickable
                else:
                    for file_path in files_list:
                        file_item = QTreeWidgetItem(item)
                        file_item.setText(0, os.path.basename(file_path))
                        file_item.setToolTip(0, file_path)
                        file_item.setData(0, Qt.UserRole, ("input", file_path))  # Store file type and path
                        file_item.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

                        # Add remove button in second column
                        remove_btn = QPushButton("×")
                        UIStyler.setup_remove_button(remove_btn)
                        remove_btn.clicked.connect(lambda checked, fp=file_path, ft="input": self._remove_file(fp, ft))
                        self.setItemWidget(file_item, 1, remove_btn)

                item.setExpanded(True)
                break

    def update_result_files(self, files_list: Optional[List[str]]) -> None:
        """
        Update the results section with loaded files.

        Refreshes the result files display in the navigator tree, showing either
        a placeholder message or the list of loaded files with remove buttons.

        Args:
            files_list: List of result file paths, or None for empty list
        """
        self.results_files = files_list or []

        # Find results item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Results":
                # Clear existing children
                item.takeChildren()

                if not files_list:
                    no_files = QTreeWidgetItem(item)
                    no_files.setText(0, "No result files loaded")
                    no_files.setData(0, Qt.UserRole, ("no_files", "results"))  # Mark as clickable
                else:
                    for file_path in files_list:
                        file_item = QTreeWidgetItem(item)
                        file_item.setText(0, os.path.basename(file_path))
                        file_item.setToolTip(0, file_path)
                        file_item.setData(0, Qt.UserRole, ("results", file_path))  # Store file type and path
                        file_item.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

                        # Add remove button in second column
                        remove_btn = QPushButton("×")
                        UIStyler.setup_remove_button(remove_btn)
                        remove_btn.clicked.connect(lambda checked, fp=file_path, ft="results": self._remove_file(fp, ft))
                        self.setItemWidget(file_item, 1, remove_btn)

                item.setExpanded(True)
                break

    def _on_item_selected(self) -> None:
        """
        Handle item selection in the navigator.

        Processes the selected item to determine if it's a placeholder for loading
        new files or an actual loaded file, and emits appropriate signals.
        """
        selected_items = self.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]

        # Check if this is a "no files loaded" item
        item_text = selected_item.text(0)
        if item_text == "No input files loaded":
            self.load_files_requested.emit("input")
            return
        elif item_text == "No result files loaded":
            self.load_files_requested.emit("results")
            return

        # Check if this is a file item (has user data)
        file_data = selected_item.data(0, Qt.UserRole)
        if file_data and isinstance(file_data, tuple) and len(file_data) == 2:
            file_type, file_path = file_data
            self.file_selected.emit(file_path, file_type)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Handle resize events to ensure the filename column fills available space.

        Overrides the base resizeEvent to manually adjust column widths.
        """
        super().resizeEvent(event)
        # Force column 0 to fill available space minus the fixed action column
        available_width = self.viewport().width()
        self.setColumnWidth(0, available_width - 30)
