"""
Project Navigator component for MESSAGEix Data Manager

Provides a tree-based navigation interface for managing loaded scenarios,
with support for scenario management and selection.
"""

import os
from typing import List, Optional, Dict
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout, QWidget, QHeaderView, QInputDialog, QMessageBox, QStyle
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QIcon, QResizeEvent, QFont
from .ui_styler import UIStyler
from core.data_models import Scenario


class ProjectNavigator(QTreeWidget):
    """
    ProjectNavigator class for displaying and managing loaded scenarios.

    A tree widget that shows loaded scenarios with options to manage them,
    and provides placeholders for creating new scenarios when none are present.

    Attributes:
        scenarios: List of currently loaded Scenario objects

    Signals:
        scenario_selected: Emitted when a scenario is selected (scenario: Scenario)
        load_scenario_requested: Emitted when "no scenarios loaded" placeholder is clicked
        scenario_removed: Emitted when a scenario removal is requested (scenario_name: str)
        scenario_renamed: Emitted when a scenario is renamed (old_name: str, new_name: str)
    """

    # Signal emitted when a scenario is selected
    scenario_selected = pyqtSignal(Scenario)

    # Signal emitted when "no scenarios loaded" is clicked
    load_scenario_requested = pyqtSignal()

    # Signal emitted when a scenario is removed
    scenario_removed = pyqtSignal(str)

    # Signal emitted when a scenario is renamed
    scenario_renamed = pyqtSignal(str, str)

    def __init__(self) -> None:
        """
        Initialize the ProjectNavigator.

        Sets up the tree widget with proper headers, initializes scenario lists,
        and connects signals for user interaction.
        """
        super().__init__()
        self.setHeaderLabels(["Scenarios", ""])  # Two columns: scenario name and action
        self.scenarios: List[Scenario] = []  # Store Scenario objects
        self.excel_icon = self._load_excel_icon()
        self._setup_ui()
        self._load_recent_scenarios()
        self.itemSelectionChanged.connect(self._on_item_selected)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _setup_ui(self) -> None:
        """
        Set up the navigator UI.

        Configures the tree widget dimensions, column widths, and visual properties.
        """
        self.setMinimumWidth(200)  # Increased minimum width for scenario details

        # Set column resize modes
        self.setColumnWidth(0, 350)   # Scenario name column
        self.setColumnWidth(1, 60)    # Action column

        # Set font for better readability
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

    def _load_recent_scenarios(self) -> None:
        """
        Load and display recent scenarios structure.

        Creates the initial tree structure with placeholder items for scenarios
        and recent scenarios sections.
        """
        # Root items
        scenarios_item = QTreeWidgetItem(self)
        scenarios_item.setText(0, "Scenarios")
        scenarios_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))

        # Add some example items (these would be loaded from config)
        no_scenarios = QTreeWidgetItem(scenarios_item)
        no_scenarios.setText(0, "No scenarios loaded")
        no_scenarios.setData(0, Qt.UserRole, ("no_scenarios",))  # Mark as clickable
        no_scenarios.setFont(0, QFont("Arial", 10, QFont.StyleItalic))

        # Expand top-level items
        scenarios_item.setExpanded(True)

    def add_scenario(self, scenario: Scenario) -> None:
        """
        Add a scenario to the navigator.

        Args:
            scenario: Scenario object to add
        """
        # Find scenarios item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Scenarios":
                # Clear "no scenarios loaded" placeholder if present
                if item.childCount() == 1 and item.child(0).data(0, Qt.UserRole) == ("no_scenarios",):
                    item.takeChildren()

                # Create scenario item
                scenario_item = QTreeWidgetItem(item)
                scenario_item.setText(0, scenario.name)
                scenario_item.setToolTip(0, f"Input: {os.path.basename(scenario.input_file)}\nStatus: {scenario.status}")
                scenario_item.setData(0, Qt.UserRole, ("scenario", scenario))  # Store scenario object
                scenario_item.setIcon(0, self._get_scenario_icon(scenario))

                # Add status indicator
                status_label = QPushButton(scenario.status.capitalize())
                UIStyler.setup_status_button(status_label)
                status_label.clicked.connect(lambda _, s=scenario: self._show_scenario_details(s))
                self.setItemWidget(scenario_item, 1, status_label)

                # Add remove button
                remove_btn = QPushButton("×")
                UIStyler.setup_remove_button(remove_btn)
                remove_btn.clicked.connect(lambda _, sn=scenario.name: self._remove_scenario(sn))
                self.setItemWidget(scenario_item, 2, remove_btn)

                # Add rename button
                rename_btn = QPushButton("✎")
                UIStyler.setup_rename_button(rename_btn)
                rename_btn.clicked.connect(lambda _, sn=scenario.name: self._rename_scenario(sn))
                self.setItemWidget(scenario_item, 3, rename_btn)

                item.setExpanded(True)
                break

        # Add to internal list
        self.scenarios.append(scenario)

    def update_scenarios(self, scenarios: List[Scenario]) -> None:
        """
        Update the scenarios section with loaded scenarios.

        Refreshes the scenarios display in the navigator tree, showing either
        a placeholder message or the list of loaded scenarios with management options.

        Args:
            scenarios: List of Scenario objects, or None for empty list
        """
        self.scenarios = scenarios or []

        # Find scenarios item
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) == "Scenarios":
                # Clear existing children
                item.takeChildren()

                if not scenarios:
                    no_scenarios = QTreeWidgetItem(item)
                    no_scenarios.setText(0, "No scenarios loaded")
                    no_scenarios.setData(0, Qt.UserRole, ("no_scenarios",))  # Mark as clickable
                    no_scenarios.setFont(0, QFont("Arial", 10, QFont.StyleItalic))
                else:
                    for scenario in scenarios:
                        scenario_item = QTreeWidgetItem(item)
                        scenario_item.setText(0, scenario.name)
                        scenario_item.setToolTip(0, f"Input: {os.path.basename(scenario.input_file)}\nStatus: {scenario.status}")
                        scenario_item.setData(0, Qt.UserRole, ("scenario", scenario))  # Store scenario object
                        scenario_item.setIcon(0, self._get_scenario_icon(scenario))

                        # Add status indicator
                        status_label = QPushButton(scenario.status.capitalize())
                        UIStyler.setup_status_button(status_label)
                        status_label.clicked.connect(lambda _, s=scenario: self._show_scenario_details(s))
                        self.setItemWidget(scenario_item, 1, status_label)

                        # Add remove button
                        remove_btn = QPushButton("×")
                        UIStyler.setup_remove_button(remove_btn)
                        remove_btn.clicked.connect(lambda _, sn=scenario.name: self._remove_scenario(sn))
                        self.setItemWidget(scenario_item, 2, remove_btn)

                        # Add rename button
                        rename_btn = QPushButton("✎")
                        UIStyler.setup_rename_button(rename_btn)
                        rename_btn.clicked.connect(lambda _, sn=scenario.name: self._rename_scenario(sn))
                        self.setItemWidget(scenario_item, 3, rename_btn)

                item.setExpanded(True)
                break

    def _load_excel_icon(self) -> QIcon:
        """
        Load the Excel icon for XLSX files.

        Returns:
            QIcon: Excel icon with multiple sizes, or default file icon if loading fails
        """
        excel_icon = QIcon()
        icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons")

        # Add multiple PNG sizes to the icon
        sizes = [64, 48, 32, 16]
        for size in sizes:
            png_path = os.path.join(icons_dir, f"excel_icon_{size}x{size}.png")
            if os.path.exists(png_path):
                excel_icon.addFile(png_path, QSize(size, size))

        # Return the icon (will be null if no files were found, which is handled)
        return excel_icon

    def _get_scenario_icon(self, scenario: Scenario) -> QIcon:
        """
        Get the appropriate icon for a scenario based on its status.

        Args:
            scenario: Scenario object

        Returns:
            QIcon: Scenario icon based on status
        """
        # Use basic icons instead of QStyle icons
        if scenario.status == "loaded":
            return QIcon.fromTheme("dialog-ok-apply")
        elif scenario.status == "modified":
            return QIcon.fromTheme("dialog-cancel")
        else:
            return QIcon.fromTheme("file")

    def _show_scenario_details(self, scenario: Scenario) -> None:
        """
        Show detailed information about a scenario.

        Args:
            scenario: Scenario object to show details for
        """
        details = f"""
        Scenario: {scenario.name}
        Status: {scenario.status}
        Input File: {scenario.input_file}
        Scenario File: {scenario.message_scenario_file}
        Results File: {scenario.results_file or "None"}
        Parameters: {len(scenario.data.parameters)}
        Sets: {len(scenario.data.sets)}
        Created: {scenario.created_at}
        Modified: {scenario.modified_at}
        """
        QMessageBox.information(self, f"Scenario Details: {scenario.name}", details)

    def _remove_scenario(self, scenario_name: str) -> None:
        """
        Handle scenario removal request.

        Args:
            scenario_name: Name of the scenario to remove
        """
        # Confirm removal
        result = QMessageBox.warning(
            self, "Remove Scenario",
            f"Are you sure you want to remove scenario '{scenario_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self.scenario_removed.emit(scenario_name)

    def _rename_scenario(self, old_name: str) -> None:
        """
        Handle scenario rename request.

        Args:
            old_name: Current name of the scenario to rename
        """
        # Get new name from user
        new_name, ok = QInputDialog.getText(
            self, "Rename Scenario",
            f"Enter new name for scenario '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            self.scenario_renamed.emit(old_name, new_name)

    def _on_item_selected(self) -> None:
        """
        Handle item selection in the navigator.

        Processes the selected item to determine if it's a placeholder for creating
        new scenarios or an actual loaded scenario, and emits appropriate signals.
        """
        selected_items = self.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]

        # Check if this is a "no scenarios loaded" item
        item_text = selected_item.text(0)
        if item_text == "No scenarios loaded":
            self.load_scenario_requested.emit()
            return

        # Check if this is a scenario item (has user data)
        item_data = selected_item.data(0, Qt.UserRole)
        if item_data and isinstance(item_data, tuple) and len(item_data) == 2 and item_data[0] == "scenario":
            scenario = item_data[1]
            self.scenario_selected.emit(scenario)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handle item double-click to show scenario details.

        Args:
            item: The clicked tree widget item
            column: The column that was clicked
        """
        item_data = item.data(0, Qt.UserRole)
        if item_data and isinstance(item_data, tuple) and len(item_data) == 2 and item_data[0] == "scenario":
            scenario = item_data[1]
            self._show_scenario_details(scenario)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Handle resize events to ensure the scenario name column fills available space.

        Overrides the base resizeEvent to manually adjust column widths.
        """
        super().resizeEvent(event)
        # Force column 0 to fill available space minus the fixed action columns
        available_width = self.viewport().width()
        self.setColumnWidth(0, available_width - 120)  # 60 for status + 60 for remove + 60 for rename

    def add_recent_file(self, file_path: str, file_type: str) -> None:
        """
        Add a file to recent files.

        Args:
            file_path: Path to the file to add
            file_type: Type of file ("input" or "results")
        """
        # For now, this is a placeholder method
        # In a real implementation, this would add the file to the recent files section
        pass
