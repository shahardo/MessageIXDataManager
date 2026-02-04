"""
File Navigator Widget - Handles scenario loading UI and recent scenarios

Extracted from MainWindow to provide focused file navigation functionality.
Implements the scenario-based architecture as defined in refactoring guide.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QLineEdit
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap
from core.data_models import Scenario
from managers.session_manager import SessionManager
from utils.error_handler import ErrorHandler
import os


class FileNavigatorWidget(QWidget):
    """
    File Navigator Widget - Handles scenario loading UI and recent scenarios
    
    Implements the scenario-based architecture with proper separation of concerns.
    Manages scenario display, selection, and basic operations.
    """

    # Signals to match the original interface for backward compatibility
    file_selected = pyqtSignal(str, str)  # file_path, file_type
    load_files_requested = pyqtSignal(str)  # file_type
    file_removed = pyqtSignal(str, str)  # file_path, file_type
    
    # New scenario-based signals
    scenario_selected = pyqtSignal(Scenario)
    scenario_created = pyqtSignal(str)  # scenario_name
    scenario_deleted = pyqtSignal(str)  # scenario_name

    def __init__(self, parent=None, session_manager=None):
        super().__init__(parent)
        self.session_manager = session_manager if session_manager else SessionManager()
        self.error_handler = ErrorHandler()
        self.current_scenarios = []
        
        self.setup_ui()
        self.load_initial_state()

    def setup_ui(self):
        """Set up the UI with scenario-based navigation"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header section
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.header_label = QLabel("Scenarios")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        # Add scenario button
        self.add_scenario_btn = QPushButton("+")
        self.add_scenario_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.add_scenario_btn.clicked.connect(self._on_add_scenario)
        self.add_scenario_btn.setToolTip("Add scenario")
        
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.add_scenario_btn)
        
        # Navigation area
        self.navigation_frame = QFrame()
        self.navigation_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.navigation_layout = QVBoxLayout(self.navigation_frame)
        self.navigation_layout.setContentsMargins(5, 5, 5, 5)
        
        # No scenarios placeholder
        self.no_scenarios_widget = QWidget()
        no_scenarios_layout = QVBoxLayout(self.no_scenarios_widget)
        no_scenarios_layout.setContentsMargins(10, 10, 10, 10)
        
        no_scenarios_label = QLabel("No scenarios loaded")
        no_scenarios_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_scenarios_label.setStyleSheet("color: gray; font-style: italic;")
        
        load_files_btn = QPushButton("Load Input Files")
        load_files_btn.clicked.connect(lambda: self.load_files_requested.emit("input"))
        
        no_scenarios_layout.addWidget(no_scenarios_label)
        no_scenarios_layout.addWidget(load_files_btn)
        
        self.navigation_layout.addWidget(self.no_scenarios_widget)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.navigation_frame)
        
        self.setLayout(layout)

    def load_initial_state(self):
        """Load initial state from session manager and auto-load previously opened files"""
        scenarios = self.session_manager.get_scenarios()
        if scenarios:
            self.update_scenarios(scenarios)
            # Note: File loading and scenario selection will be done by main window
        else:
            self._show_no_scenarios()

    def _auto_load_open_files(self, scenarios):
        """Auto-load files that were open when application was last closed"""
        for scenario in scenarios:
            # Load input file if it exists
            if scenario.input_file and os.path.exists(scenario.input_file):
                self._auto_load_file(scenario, "input", scenario.input_file)
            
            # Load data file if it exists
            if scenario.message_scenario_file and os.path.exists(scenario.message_scenario_file):
                self._auto_load_file(scenario, "data", scenario.message_scenario_file)
            
            # Load results file if it exists
            if scenario.results_file and os.path.exists(scenario.results_file):
                self._auto_load_file(scenario, "results", scenario.results_file)

    def _auto_load_file(self, scenario, file_type, file_path):
        """Auto-load a specific file for a scenario"""
        try:
            # Emit signal to load the file
            if file_type == "input":
                self.file_selected.emit(file_path, "input")
            elif file_type == "results":
                self.file_selected.emit(file_path, "results")
            
            # Update scenario status to indicate it's loaded
            scenario.status = "loaded"
            self.session_manager.add_scenario(scenario)
            
        except Exception as e:
            # Log the error but don't crash
            print(f"Warning: Failed to auto-load {file_type} file: {file_path}")
            print(f"Error: {str(e)}")

    def _select_last_selected_scenario(self, scenarios):
        """Select the last selected scenario if it exists in the current scenarios"""
        session_state = self.session_manager.load_session_state()
        last_selected_name = session_state.get('selected_scenario')
        
        print(f"DEBUG: Last selected scenario from session: {last_selected_name}")
        print(f"DEBUG: Available scenarios: {[s.name for s in scenarios]}")
        
        if last_selected_name:
            # Find the scenario with the matching name
            for scenario in scenarios:
                if scenario.name == last_selected_name:
                    print(f"DEBUG: Selecting last selected scenario: {last_selected_name}")
                    self.scenario_selected.emit(scenario)
                    return
        
        # If no last selected scenario or it doesn't exist, select the first scenario
        if scenarios:
            print(f"DEBUG: Selecting first scenario: {scenarios[0].name}")
            self.scenario_selected.emit(scenarios[0])

    def update_scenarios(self, scenarios):
        """
        Update the scenarios display with loaded scenarios.
        
        Args:
            scenarios: List of Scenario objects
        """
        self.current_scenarios = scenarios
        
        # Clear all widgets from navigation layout
        while self.navigation_layout.count() > 0:
            item = self.navigation_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
        
        if not scenarios:
            self._show_no_scenarios()
        else:
            self._show_scenario_list(scenarios)

    def _show_no_scenarios(self):
        """Show the no scenarios placeholder"""
        self.navigation_layout.addWidget(self.no_scenarios_widget)
        self.no_scenarios_widget.show()
        self.navigation_frame.setStyleSheet("")

    def _show_scenario_list(self, scenarios):
        """Show the list of scenarios"""
        for scenario in scenarios:
            scenario_widget = self._create_scenario_widget(scenario)
            self.navigation_layout.addWidget(scenario_widget)
        
        # Add stretch at the end to push scenarios to top
        self.navigation_layout.addStretch()

    def _create_scenario_widget(self, scenario):
        """Create a widget for displaying a single scenario with file entries"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 2px 0;
                padding: 8px;
            }
            QWidget:hover {
                background-color: #e9ecef;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header row with editable title and trashcan
        header_layout = QHBoxLayout()
        
        # Scenario title button (styled as label, clickable to edit)
        scenario_title_button = QPushButton(scenario.name)
        scenario_title_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 11px;
                color: #495057;
                border: none;
                background: transparent;
                outline: none;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                border: none;
                background: transparent;
                outline: none;
            }
            QPushButton:focus {
                border: none;
                background: transparent;
                outline: none;
            }
            QPushButton:pressed {
                border: none;
                background: transparent;
                outline: none;
            }
        """)
        scenario_title_button.setCursor(Qt.PointingHandCursor)
        scenario_title_button.clicked.connect(lambda checked, s=scenario, b=scenario_title_button: self._start_editing_title(s, b))
        
        # Trashcan delete button
        delete_btn = QPushButton()
        delete_btn.setIcon(QIcon.fromTheme("user-trash"))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #dc3545;
            }
        """)
        delete_btn.setFixedSize(24, 24)
        delete_btn.clicked.connect(lambda: self._on_scenario_deleted(scenario))
        delete_btn.setToolTip("Delete scenario")
        
        header_layout.addWidget(scenario_title_button, 1)
        header_layout.addWidget(delete_btn, 0)
        
        # File entries section
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(5, 3, 5, 3)
        files_layout.setSpacing(2)
        
        # Input file entry
        input_widget = self._create_file_entry_widget(
            "Input File", scenario.input_file, 
            lambda: self._open_file_dialog(scenario, "input"),
            lambda: self._remove_scenario_file(scenario, "input")
        )
        
        # Data file entry
        data_widget = self._create_file_entry_widget(
            "Data File", scenario.message_scenario_file,
            lambda: self._open_file_dialog(scenario, "data"),
            lambda: self._remove_scenario_file(scenario, "data")
        )
        
        # Results file entry
        results_widget = self._create_file_entry_widget(
            "Results File", scenario.results_file,
            lambda: self._open_file_dialog(scenario, "results"),
            lambda: self._remove_scenario_file(scenario, "results")
        )
        
        files_layout.addWidget(input_widget)
        files_layout.addWidget(data_widget)
        files_layout.addWidget(results_widget)
        
        layout.addLayout(header_layout)
        layout.addLayout(files_layout)
        
        return widget

    def _get_scenario_icon(self, scenario):
        """Get the appropriate icon for a scenario based on its status"""
        from PyQt5.QtGui import QIcon
        
        if scenario.status == "loaded":
            return QIcon.fromTheme("dialog-ok-apply")
        elif scenario.status == "modified":
            return QIcon.fromTheme("dialog-cancel")
        else:
            return QIcon.fromTheme("file")

    def _get_status_style(self, status):
        """Get CSS style for status indicator"""
        if status == "loaded":
            return "color: green; font-weight: bold;"
        elif status == "modified":
            return "color: orange; font-weight: bold;"
        else:
            return "color: gray;"

    def _start_editing_title(self, scenario, button):
        """Replace the button with an editable text field"""
        # Find the parent layout
        parent_layout = button.parent().layout()
        
        # Find the header layout (first sub-layout containing the button)
        header_layout = None
        for i in range(parent_layout.count()):
            item = parent_layout.itemAt(i)
            if item.layout():
                header_layout = item.layout()
                break
        
        if not header_layout:
            return  # Safety check
        
        # Create the edit field
        edit_field = QLineEdit(scenario.name)
        edit_field.setStyleSheet("""
            QLineEdit {
                border: 1px solid #007bff;
                border-radius: 3px;
                padding: 2px 4px;
                font-weight: bold;
                font-size: 11px;
                background-color: white;
            }
        """)
        
        # Replace the button with the edit field in the header layout
        for i in range(header_layout.count()):
            item = header_layout.itemAt(i)
            if item and item.widget() == button:
                header_layout.replaceWidget(button, edit_field)
                button.setParent(None)  # Remove the old button
                break
        
        # Focus and select all text
        edit_field.setFocus()
        edit_field.selectAll()
        
        # Connect the editing finished signal
        edit_field.editingFinished.connect(lambda: self._finish_editing_title(scenario, edit_field, header_layout))

    def _finish_editing_title(self, scenario, edit_field, header_layout):
        """Replace the edit field back with a label"""
        new_title = edit_field.text().strip()
        if new_title and new_title != scenario.name:
            # Remove the scenario with the old name first
            old_name = scenario.name
            self.session_manager.remove_scenario(old_name)
            
            # Update the scenario name
            scenario.name = new_title
            
            # Add the scenario back with the new name
            self.session_manager.add_scenario(scenario)
        
        # Create new button
        button = QPushButton(scenario.name)
        button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 11px;
                color: #495057;
                border: none;
                background: transparent;
                outline: none;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                border: none;
                background: transparent;
                outline: none;
            }
            QPushButton:focus {
                border: none;
                background: transparent;
                outline: none;
            }
            QPushButton:pressed {
                border: none;
                background: transparent;
                outline: none;
            }
        """)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda checked, s=scenario, b=button: self._start_editing_title(s, b))
        
        # Replace the edit field with the button in the header layout
        header_layout.replaceWidget(edit_field, button)
        edit_field.setParent(None)  # Remove the old edit field

    def _on_scenario_title_changed(self, scenario, new_title):
        """Handle scenario title editing"""
        if new_title.strip() and new_title != scenario.name:
            scenario.name = new_title.strip()
            self.session_manager.add_scenario(scenario)
            # Update the display
            self.update_scenarios(self.current_scenarios)

    def _on_scenario_deleted(self, scenario):
        """Handle scenario deletion"""
        # Confirm deletion
        from PyQt5.QtWidgets import QMessageBox
        
        result = QMessageBox.warning(
            self, "Delete Scenario",
            f"Are you sure you want to delete scenario '{scenario.name}'?\n"
            "This will remove the scenario from the list but not delete the files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            # Remove from session manager
            self.session_manager.remove_scenario(scenario.name)
            
            # Remove from current list
            self.current_scenarios = [s for s in self.current_scenarios if s.name != scenario.name]
            
            # Update display
            self.update_scenarios(self.current_scenarios)
            
            # Emit signals
            self.scenario_deleted.emit(scenario.name)
            self.file_removed.emit(scenario.input_file, "input")

    def _on_add_scenario(self):
        """Handle add scenario button click"""
        self.load_files_requested.emit("input")

    def add_scenario(self, scenario):
        """
        Add a new scenario to the navigator.
        
        Args:
            scenario: Scenario object to add
        """
        # Add to session manager
        self.session_manager.add_scenario(scenario)
        
        # Update current list
        self.current_scenarios.append(scenario)
        
        # Update display
        self.update_scenarios(self.current_scenarios)
        
        # Emit signal
        self.scenario_created.emit(scenario.name)

    def remove_scenario(self, scenario_name):
        """
        Remove a scenario from the navigator.
        
        Args:
            scenario_name: Name of the scenario to remove
        """
        # Remove from session manager
        self.session_manager.remove_scenario(scenario_name)
        
        # Update current list
        self.current_scenarios = [s for s in self.current_scenarios if s.name != scenario_name]
        
        # Update display
        self.update_scenarios(self.current_scenarios)

    def update_input_files(self, files_list):
        """
        Update the input files display.
        
        For backward compatibility, this method is kept but now works with scenarios.
        """
        # In the new architecture, this would trigger scenario creation
        # For now, we'll just update the display to show "no scenarios" if empty
        if not files_list and not self.current_scenarios:
            self._show_no_scenarios()

    def update_result_files(self, files_list):
        """
        Update the results files display.
        
        For backward compatibility, this method is kept.
        """
        # Results files are now part of scenarios, so this is handled automatically
        pass

    def add_recent_file(self, file_path, file_type="input"):
        """
        Add a file to recent files.
        
        For backward compatibility, this method is kept.
        """
        # In the new architecture, this would be handled through scenarios
        # For now, we'll just ensure the session manager has the file
        self.session_manager.add_recent_file(file_path, file_type)

    def get_selected_scenario(self):
        """
        Get the currently selected scenario.
        
        Returns:
            Scenario object or None
        """
        # This would need to be implemented based on selection state
        # For now, return the first scenario if any exist
        return self.current_scenarios[0] if self.current_scenarios else None

    def clear_selection(self):
        """Clear the current selection"""
        # Implementation would depend on selection mechanism
        pass

    def _create_file_entry_widget(self, file_type, file_path, open_callback, close_callback):
        """Create a widget for displaying a file entry with clickable icon and close button"""
        widget = FileEntryWidget()
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # File type label (plain text)
        type_label = QLabel(file_type)
        type_label.setStyleSheet("font-size: 11px; color: #495057;")
        type_label.setFixedWidth(75)
        
        if file_path and os.path.exists(file_path):
            # Show file name
            file_name = os.path.basename(file_path)
            file_label = QLabel(file_name)
            file_label.setStyleSheet("font-size: 10px; color: #495057;")
            file_label.setToolTip(file_path)
            file_label.setWordWrap(False)
            layout.addWidget(type_label, 0)
            layout.addWidget(file_label, 1)
            
            # Close button
            close_btn = QPushButton("✕")
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-weight: bold;
                    font-size: 8px;
                    padding: 0px 3px;
                }
            """)
            close_btn.setFixedSize(16, 16)
            close_btn.clicked.connect(close_callback)
            close_btn.setToolTip(f"Remove {file_type}")
            layout.addWidget(close_btn, 0)
            
            # Store reference to close button for hover handling
            widget.close_button = close_btn
        else:
            # Show open file icon button
            open_btn = QPushButton()
            open_btn.setIcon(QIcon.fromTheme("document-open"))
            open_btn.setIconSize(QSize(12, 12))
            open_btn.setFixedSize(18, 18)
            open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    border: 1px solid #0056b3;
                    border-radius: 2px;
                    padding: 1px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #003d82;
                }
            """)
            open_btn.clicked.connect(open_callback)
            open_btn.setToolTip(f"Load {file_type}")
            layout.addWidget(type_label, 0)
            layout.addWidget(open_btn, 0)
            
            # No close button for empty entries
            widget.close_button = None
        
        layout.addStretch()
        return widget

    def _open_file_dialog(self, scenario, file_type):
        """Open file dialog for the specified file type"""
        from PyQt5.QtWidgets import QFileDialog
        
        if file_type == "input":
            file_filter = "Excel Files (*.xlsx *.xls);;All Files (*)"
            title = "Open Input File"
        elif file_type == "data":
            file_filter = "Message Data Files (*.zip);;All Files (*)"
            title = "Open Data File"
        elif file_type == "results":
            file_filter = "Excel Files (*.xlsx *.xls);;All Files (*)"
            title = "Open Results File"
        else:
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", file_filter
        )
        
        if file_path:
            self._update_scenario_file(scenario, file_type, file_path)

    def _update_scenario_file(self, scenario, file_type, file_path):
        """Update scenario file and refresh display"""
        # Update the scenario object
        if file_type == "input":
            scenario.input_file = file_path
        elif file_type == "data":
            scenario.message_scenario_file = file_path
        elif file_type == "results":
            scenario.results_file = file_path
        
        # Update session manager
        self.session_manager.add_scenario(scenario)
        
        # Refresh the display
        self.update_scenarios(self.current_scenarios)
        
        # Emit file selected signal for backward compatibility
        if file_type in ["input", "results", "data"]:
            self.file_selected.emit(file_path, file_type)

    def _remove_scenario_file(self, scenario, file_type):
        """Remove a file from a scenario"""
        # Clear the file path
        if file_type == "input":
            scenario.input_file = None
        elif file_type == "data":
            scenario.message_scenario_file = None
        elif file_type == "results":
            scenario.results_file = None
        
        # Update session manager
        self.session_manager.add_scenario(scenario)
        
        # Refresh the display
        self.update_scenarios(self.current_scenarios)

    def refresh(self):
        """Refresh the navigator display"""
        scenarios = self.session_manager.get_scenarios()
        self.update_scenarios(scenarios)


class FileEntryWidget(QWidget):
    """Custom widget for file entries that highlights close button on hover"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.close_button = None
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
    
    def enterEvent(self, event):
        """Handle mouse enter event - highlight close button"""
        if self.close_button:
            self.close_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-weight: bold;
                    font-size: 8px;
                    padding: 0px 3px;
                }
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave event - reset close button style"""
        if self.close_button:
            self.close_button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-weight: bold;
                    font-size: 8px;
                    padding: 0px 3px;
                }
            """)
        super().leaveEvent(event)
