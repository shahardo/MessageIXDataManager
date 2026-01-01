"""
Project Navigator component
"""

import os
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt


class ProjectNavigator(QTreeWidget):
    """Project navigator showing recent files and project structure"""

    def __init__(self):
        super().__init__()
        self.setHeaderLabel("Project Navigator")
        self._setup_ui()
        self._load_recent_files()

    def _setup_ui(self):
        """Set up the navigator UI"""
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

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
        example_input.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

        example_result = QTreeWidgetItem(results_item)
        example_result.setText(0, "No result files loaded")
        example_result.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

        # Expand top-level items
        inputs_item.setExpanded(True)
        results_item.setExpanded(True)
        recent_item.setExpanded(True)

    def add_recent_file(self, file_path, file_type="input"):
        """Add a file to the recent files list"""
        # TODO: Implement actual recent files management
        print(f"Adding recent file: {file_path} (type: {file_type})")

    def _show_context_menu(self, position):
        """Show context menu for navigator items"""
        # TODO: Implement context menu
        pass

    def update_input_files(self, files_list):
        """Update the inputs section with loaded files"""
        # Find inputs item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Inputs":
                # Clear existing children
                item.takeChildren()

                if not files_list:
                    no_files = QTreeWidgetItem(item)
                    no_files.setText(0, "No input files loaded")
                    no_files.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))
                else:
                    for file_path in files_list:
                        file_item = QTreeWidgetItem(item)
                        file_item.setText(0, os.path.basename(file_path))
                        file_item.setToolTip(0, file_path)
                        file_item.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

                item.setExpanded(True)
                break

    def update_result_files(self, files_list):
        """Update the results section with loaded files"""
        # Find results item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Results":
                # Clear existing children
                item.takeChildren()

                if not files_list:
                    no_files = QTreeWidgetItem(item)
                    no_files.setText(0, "No result files loaded")
                    no_files.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))
                else:
                    for file_path in files_list:
                        file_item = QTreeWidgetItem(item)
                        file_item.setText(0, os.path.basename(file_path))
                        file_item.setToolTip(0, file_path)
                        file_item.setIcon(0, self.style().standardIcon(self.style().SP_FileIcon))

                item.setExpanded(True)
                break
