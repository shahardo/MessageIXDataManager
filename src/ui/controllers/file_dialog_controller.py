"""
File dialog management for the main window.
Centralizes file selection dialogs and recent files tracking.

Part of the refactoring to reduce complexity in main_window.py.
"""
from typing import Optional, Tuple, List
from PyQt5.QtWidgets import QFileDialog, QWidget
import os


class FileDialogController:
    """
    Manages file selection dialogs with consistent behavior.

    Provides centralized file dialog functionality for:
    - Opening input files
    - Opening results files
    - Opening data files (ZIP/CSV)
    - Saving files
    - Tracking last used directories

    Usage:
        controller = FileDialogController(parent_widget)
        file_path = controller.open_input_file()
        if file_path:
            # process file
    """

    # File type filters
    EXCEL_FILTER = "Excel Files (*.xlsx *.xls);;All Files (*)"
    DATA_FILE_FILTER = "ZIP Files (*.zip);;CSV Files (*.csv);;All Files (*)"
    ALL_SUPPORTED_FILTER = "All Supported (*.xlsx *.xls *.zip *.csv);;Excel Files (*.xlsx *.xls);;ZIP Files (*.zip);;CSV Files (*.csv);;All Files (*)"

    def __init__(
        self,
        parent: QWidget,
        session_manager=None,
        initial_directory: str = ""
    ):
        """
        Initialize the file dialog controller.

        Args:
            parent: Parent widget for dialogs
            session_manager: Optional session manager for recent directories
            initial_directory: Initial directory to use
        """
        self.parent = parent
        self.session_manager = session_manager
        self._last_directory = initial_directory

    def open_input_file(self) -> Optional[str]:
        """
        Show dialog to select an input Excel file.

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Input File",
            file_filter=self.EXCEL_FILTER
        )

    def open_results_file(self) -> Optional[str]:
        """
        Show dialog to select a results Excel file.

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Results File",
            file_filter=self.EXCEL_FILTER
        )

    def open_data_file(self) -> Optional[str]:
        """
        Show dialog to select a data file (ZIP or CSV).

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open Data File",
            file_filter=self.DATA_FILE_FILTER
        )

    def open_any_file(self) -> Optional[str]:
        """
        Show dialog to select any supported file type.

        Returns:
            Selected file path or None if cancelled
        """
        return self._open_file_dialog(
            title="Open File",
            file_filter=self.ALL_SUPPORTED_FILTER
        )

    def open_multiple_files(
        self,
        title: str = "Select Files",
        file_filter: str = None
    ) -> List[str]:
        """
        Show dialog to select multiple files.

        Args:
            title: Dialog title
            file_filter: File type filter (default: all supported)

        Returns:
            List of selected file paths (empty if cancelled)
        """
        if file_filter is None:
            file_filter = self.ALL_SUPPORTED_FILTER

        file_paths, _ = QFileDialog.getOpenFileNames(
            self.parent,
            title,
            self._get_initial_directory(),
            file_filter
        )

        if file_paths:
            # Update last directory from first file
            self._last_directory = os.path.dirname(file_paths[0])

        return file_paths

    def save_file(
        self,
        default_name: str = "",
        title: str = "Save File",
        file_filter: str = None
    ) -> Optional[str]:
        """
        Show dialog to select save location.

        Args:
            default_name: Default filename to suggest
            title: Dialog title
            file_filter: File type filter

        Returns:
            Selected file path or None if cancelled
        """
        if file_filter is None:
            file_filter = self.EXCEL_FILTER

        initial_path = self._get_initial_directory()
        if default_name:
            initial_path = os.path.join(initial_path, default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            title,
            initial_path,
            file_filter
        )

        if file_path:
            self._last_directory = os.path.dirname(file_path)
            return file_path

        return None

    def select_directory(self, title: str = "Select Directory") -> Optional[str]:
        """
        Show dialog to select a directory.

        Args:
            title: Dialog title

        Returns:
            Selected directory path or None if cancelled
        """
        directory = QFileDialog.getExistingDirectory(
            self.parent,
            title,
            self._get_initial_directory()
        )

        if directory:
            self._last_directory = directory
            return directory

        return None

    def _open_file_dialog(
        self,
        title: str,
        file_filter: str
    ) -> Optional[str]:
        """
        Internal helper for file open dialogs.

        Args:
            title: Dialog title
            file_filter: File type filter

        Returns:
            Selected file path or None if cancelled
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            title,
            self._get_initial_directory(),
            file_filter
        )

        if file_path:
            self._last_directory = os.path.dirname(file_path)
            return file_path

        return None

    def _get_initial_directory(self) -> str:
        """
        Get the initial directory for file dialogs.

        Tries in order:
        1. Last used directory
        2. Session manager's last directory
        3. Current working directory

        Returns:
            Directory path to use
        """
        if self._last_directory and os.path.isdir(self._last_directory):
            return self._last_directory

        if self.session_manager:
            session_dir = getattr(self.session_manager, 'get_last_directory', lambda: None)()
            if session_dir and os.path.isdir(session_dir):
                return session_dir

        return os.getcwd()

    @property
    def last_directory(self) -> str:
        """Get the last used directory."""
        return self._last_directory

    @last_directory.setter
    def last_directory(self, value: str) -> None:
        """Set the last used directory."""
        if value and os.path.isdir(value):
            self._last_directory = value

    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        Determine the type of file based on extension.

        Args:
            file_path: Path to the file

        Returns:
            File type: 'excel', 'zip', 'csv', or 'unknown'
        """
        if not file_path:
            return 'unknown'

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.xlsx', '.xls']:
            return 'excel'
        elif ext == '.zip':
            return 'zip'
        elif ext == '.csv':
            return 'csv'
        else:
            return 'unknown'

    @staticmethod
    def validate_file_exists(file_path: str) -> Tuple[bool, str]:
        """
        Validate that a file exists and is readable.

        Args:
            file_path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path:
            return False, "No file path provided"

        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"

        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"

        return True, ""
