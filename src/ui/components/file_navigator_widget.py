"""
File Navigator Widget - Handles file loading UI and recent files

Extracted from MainWindow to provide focused file navigation functionality.
Wraps the existing ProjectNavigator.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

from ..navigator import ProjectNavigator


class FileNavigatorWidget(QWidget):
    """Handles file loading UI and recent files"""

    # Signals to match the original interface
    file_selected = pyqtSignal(str, str)  # file_path, file_type
    load_files_requested = pyqtSignal(str)  # file_type
    file_removed = pyqtSignal(str, str)  # file_path, file_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI with the ProjectNavigator"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Use the existing ProjectNavigator
        self.navigator = ProjectNavigator()
        layout.addWidget(self.navigator)

        # Connect signals
        self.navigator.file_selected.connect(self.file_selected)
        self.navigator.load_files_requested.connect(self.load_files_requested)
        self.navigator.file_removed.connect(self.file_removed)

        self.setLayout(layout)

    def update_input_files(self, files_list):
        """Update the input files display"""
        self.navigator.update_input_files(files_list)

    def update_result_files(self, files_list):
        """Update the results files display"""
        self.navigator.update_result_files(files_list)

    def add_recent_file(self, file_path, file_type="input"):
        """Add a file to recent files"""
        self.navigator.add_recent_file(file_path, file_type)
