"""
Add Parameter Dialog for MessageIX Data Manager.

This dialog allows users to select from valid MESSAGEix parameters that are not yet in the scenario
and shows description and required dimensions for the selected parameter.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                            QListWidgetItem, QTextEdit, QPushButton, QTreeWidget,
                            QTreeWidgetItem, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Dict, Optional, Any

class AddParameterDialog(QDialog):
    """Dialog for adding new parameters to a scenario."""

    def __init__(self, parameter_manager, existing_parameters: List[str], parent=None):
        super().__init__(parent)
        self.parameter_manager = parameter_manager
        self.existing_parameters = existing_parameters
        self.selected_parameter = None

        self.setWindowTitle("Add Parameter")
        self.setMinimumSize(800, 600)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)

        # Category selection
        category_layout = QHBoxLayout()
        category_label = QLabel("Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.parameter_manager.get_parameter_categories().keys())
        self.category_combo.currentTextChanged.connect(self._update_parameter_list)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        main_layout.addLayout(category_layout)

        # Parameter selection
        selection_layout = QHBoxLayout()

        # Available parameters list
        available_group = QVBoxLayout()
        available_label = QLabel("Available Parameters:")
        available_label.setFont(QFont("Arial", 10, QFont.Bold))
        available_group.addWidget(available_label)

        self.available_list = QListWidget()
        self.available_list.itemSelectionChanged.connect(self._show_parameter_details)
        available_group.addWidget(self.available_list)
        selection_layout.addLayout(available_group)

        # Parameter details
        details_group = QVBoxLayout()
        details_label = QLabel("Parameter Details:")
        details_label.setFont(QFont("Arial", 10, QFont.Bold))
        details_group.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_group.addWidget(self.details_text)
        selection_layout.addLayout(details_group)

        main_layout.addLayout(selection_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.add_button = QPushButton("Add Parameter")
        self.add_button.clicked.connect(self._add_parameter)
        self.add_button.setEnabled(False)
        button_layout.addWidget(self.add_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

        # Initialize the parameter list
        self._update_parameter_list()

    def _update_parameter_list(self):
        """Update the list of available parameters based on selected category."""
        selected_category = self.category_combo.currentText()
        category_params = self.parameter_manager.get_parameters_by_category(selected_category)

        # Filter out existing parameters
        available_params = [p for p in category_params if p not in self.existing_parameters]

        self.available_list.clear()
        for param_name in sorted(available_params):
            item = QListWidgetItem(param_name)
            self.available_list.addItem(item)

        # Clear details if no parameter is selected
        if self.available_list.count() == 0:
            self.details_text.clear()
            self.add_button.setEnabled(False)

    def _show_parameter_details(self):
        """Show details for the selected parameter."""
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            self.details_text.clear()
            self.add_button.setEnabled(False)
            return

        param_name = selected_items[0].text()
        self.selected_parameter = param_name

        # Get parameter details
        description = self.parameter_manager.get_parameter_description(param_name)
        dimensions = self.parameter_manager.get_parameter_dimensions(param_name)

        # Format details
        details = f"<b>{param_name}</b><br><br>"
        details += f"<b>Description:</b><br>{description}<br><br>"
        details += f"<b>Dimensions:</b><br>{', '.join(dimensions)}"

        self.details_text.setHtml(details)
        self.add_button.setEnabled(True)

    def _add_parameter(self):
        """Handle the add parameter action."""
        if not self.selected_parameter:
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Add Parameter",
            f"Are you sure you want to add parameter '{self.selected_parameter}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.accept()
        else:
            self.selected_parameter = None
            self.add_button.setEnabled(False)

    def get_selected_parameter(self) -> Optional[str]:
        """Get the selected parameter name."""
        return self.selected_parameter

    def get_parameter_metadata(self) -> Dict[str, Any]:
        """Get metadata for the selected parameter."""
        if not self.selected_parameter:
            return {}

        param_info = self.parameter_manager.get_parameter_info(self.selected_parameter)
        return {
            'description': param_info.get('description', ''),
            'dimensions': param_info.get('dims', []),
            'type': param_info.get('type', 'float')
        }
