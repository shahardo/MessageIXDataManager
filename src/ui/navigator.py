"""
Project Navigator component
"""

import os
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from .ui_styler import UIStyler


class ProjectNavigator(QTreeWidget):
    """Project navigator showing recent files and project structure"""

    # Signal emitted when a file is selected (file_path, file_type)
    file_selected = pyqtSignal(str, str)

    # Signal emitted when "no files loaded" is clicked (file_type: "input" or "results")
    load_files_requested = pyqtSignal(str)

    # Signal emitted when a file is removed (file_path, file_type)
    file_removed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Files", ""])  # Two columns: filename and action
        self.input_files = []  # Store input file paths
        self.results_files = []  # Store results file paths
        self._setup_ui()
        self._load_recent_files()
        self.itemSelectionChanged.connect(self._on_item_selected)

    def _setup_ui(self):
        """Set up the navigator UI"""
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

        # Set column widths
        self.setColumnWidth(0, 180)  # File name column
        self.setColumnWidth(1, 30)   # Action column

        # Enable context menu
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self._show_context_menu)

    def _load_recent_files(self):
        """Load and display recent files"""
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

    def add_recent_file(self, file_path, file_type="input"):
        """Add a file to the recent files list"""
        # TODO: Implement actual recent files management
        print(f"Adding recent file: {file_path} (type: {file_type})")

    def _remove_file(self, file_path, file_type):
        """Handle file removal request"""
        self.file_removed.emit(file_path, file_type)

    def update_input_files(self, files_list):
        """Update the inputs section with loaded files"""
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

    def update_result_files(self, files_list):
        """Update the results section with loaded files"""
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

    def _on_item_selected(self):
        """Handle item selection in the navigator"""
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
