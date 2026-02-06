"""
Parameter Tree Widget - Handles parameter/result tree navigation

Extracted from MainWindow to provide focused tree navigation functionality.
"""

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QLabel, QPushButton, QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QHeaderView, QMenu, QAction, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor
from typing import Optional, List, Dict

from core.data_models import ScenarioData


class SectionTreeItem(QTreeWidgetItem):
    """Custom tree item for section headers that can be clicked to switch dashboards"""

    def __init__(self, section_name: str, section_type: str, item_count: int = 0):
        super().__init__()
        self.section_name = section_name
        self.section_type = section_type  # "parameters", "variables", "results"
        self.item_count = item_count
        self.setText(0, f"{section_name} ({item_count})")
        self.setToolTip(0, f"Click to show {section_name.lower()} dashboard")

        # Set visual styling for section headers
        self.setBackground(0, QColor(240, 240, 240))  # Light gray background
        font = self.font(0)
        font.setBold(True)
        self.setFont(0, font)


class ParameterTreeWidget(QTreeWidget):
    """Handles parameter/result tree navigation with multi-section support"""

    # Signals
    parameter_selected = pyqtSignal(object, bool)  # parameter, is_results
    section_selected = pyqtSignal(str)  # section_type: "parameters", "variables", "results"
    options_changed = pyqtSignal()  # emitted when scenario options are modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "input"  # "input" or "results"
        self.current_scenario = None
        self.parameter_manager = None
        self.sections = {}  # section_type -> SectionTreeItem
        self.setup_ui()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def setup_ui(self):
        """Set up the tree widget"""
        self.setHeaderLabel("Parameters")
        self.itemSelectionChanged.connect(self._on_item_selected)

        # Add add parameter button to the header
        self.add_button = QPushButton("+", self)
        self.add_button.setToolTip("Add Parameter")
        self.add_button.setFixedSize(32, 24)
        self.add_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.1);
            }
        """)
        self.add_button.clicked.connect(self._add_parameter)
        self._position_buttons()

    def update_tree_with_sections(self, scenario: ScenarioData, sections_data: Dict[str, List]):
        """
        Update the tree with multiple sections containing categorized data

        Args:
            scenario: The scenario data
            sections_data: Dict mapping section_type to list of (name, item) tuples
        """
        self.clear()
        self.current_scenario = scenario
        self.sections = {}

        if not scenario:
            return

        # Create sections
        for section_type, items in sections_data.items():
            if not items:
                continue

            # Count total items for section header
            total_items = len(items)

            # Create section header
            section_name = section_type.title()  # "Parameters", "Variables", "Results"
            section_item = SectionTreeItem(section_name, section_type, total_items)
            self.addTopLevelItem(section_item)
            self.sections[section_type] = section_item

            # Group items by category
            categories = {}
            for item_name, item in items:
                # Determine category based on item type
                if section_type == "parameters":
                    category = self._categorize_parameter(item_name, item)
                elif section_type == "variables":
                    category = self._categorize_variable(item_name, item)
                elif section_type == "results":
                    category = self._categorize_result(item_name, item)
                else:
                    category = "Other"

                if category not in categories:
                    categories[category] = []
                categories[category].append((item_name, item))

            # Sort categories and add to section
            for category in sorted(categories.keys()):
                category_items = categories[category]
                category_item = QTreeWidgetItem(section_item)
                category_item.setText(0, f"{category} ({len(category_items)})")

                # Sort items within category
                category_items.sort(key=lambda x: x[0])

                for item_name, item in category_items:
                    param_item = QTreeWidgetItem(category_item)
                    param_item.setText(0, item_name)

                    # Add metadata to tooltip based on section type
                    if section_type in ["parameters", "variables"]:
                        dims_info = f"Dimensions: {', '.join(item.metadata.get('dims', []))}" if item.metadata.get('dims') else "No dimensions"
                        tooltip = f"{section_type.title()[:-1]}: {item_name}\n{dims_info}"
                    else:  # results
                        dims_info = f"Dimensions: {', '.join(item.metadata.get('dims', []))}" if item.metadata.get('dims') else "No dimensions"
                        shape_info = f"Shape: {item.metadata.get('shape', ('?', '?'))}"
                        units_info = f"Units: {item.metadata.get('units', 'N/A')}"
                        tooltip = f"Result: {item_name}\n{dims_info}\n{shape_info}\n{units_info}"

                    param_item.setToolTip(0, tooltip)

                category_item.setExpanded(True)

            section_item.setExpanded(True)

    def update_parameters(self, scenario: ScenarioData, is_results: bool = False):
        """Update the tree with parameters from a scenario"""
        # For now, maintain backward compatibility by showing parameters in a single section
        # This will be updated when we implement the full section-based system
        self.clear()
        self.current_scenario = scenario

        if not scenario:
            return

        # Add dashboard item at the top for input view
        dashboard_item = QTreeWidgetItem(self)
        dashboard_item.setText(0, "Dashboard")
        dashboard_item.setToolTip(0, "Display dashboard with comprehensive input file overview")

        # Group parameters by category with enhanced logic
        categories = {}

        for param_name in scenario.get_parameter_names():
            parameter = scenario.get_parameter(param_name)
            if not parameter:
                continue

            # Enhanced categorization based on parameter name and metadata
            category = self._categorize_parameter(param_name, parameter)

            if category not in categories:
                categories[category] = []
            categories[category].append((param_name, parameter))

        # Sort categories
        sorted_categories = sorted(categories.keys())

        # Create tree items
        for category in sorted_categories:
            params = categories[category]
            category_item = QTreeWidgetItem(self)
            category_item.setText(0, f"{category} ({len(params)} parameters)")

            # Sort parameters within category
            params.sort(key=lambda x: x[0])

            for param_name, parameter in params:
                param_item = QTreeWidgetItem(category_item)
                param_item.setText(0, param_name)

                # Add metadata to tooltip
                dims_info = f"Dimensions: {', '.join(parameter.metadata.get('dims', []))}" if parameter.metadata.get('dims') else "No dimensions"
                shape_info = f"Shape: {parameter.metadata.get('shape', ('?', '?'))}"
                tooltip = f"Parameter: {param_name}\n{dims_info}\n{shape_info}"
                param_item.setToolTip(0, tooltip)

            category_item.setExpanded(True)

        # Add sets information if available
        if scenario.sets:
            sets_item = QTreeWidgetItem(self)
            sets_item.setText(0, f"Sets ({len(scenario.sets)} sets)")

            for set_name, set_values in sorted(scenario.sets.items()):
                set_item = QTreeWidgetItem(sets_item)
                set_item.setText(0, f"{set_name} ({len(set_values)} elements)")
                set_item.setToolTip(0, f"Set: {set_name}\nElements: {len(set_values)}")

            sets_item.setExpanded(False)

    def update_results(self, scenario: ScenarioData):
        """Update the tree with results from a scenario"""
        self.clear()
        self.current_scenario = scenario

        if not scenario:
            return

        # Add dashboard item at the top
        dashboard_item = QTreeWidgetItem(self)
        dashboard_item.setText(0, "Dashboard")
        dashboard_item.setToolTip(0, "Display dashboard with key metrics and charts")

        # Group results by type
        categories = {}

        for result_name in scenario.get_parameter_names():
            result = scenario.get_parameter(result_name)
            if not result:
                continue

            # Categorize by result type
            result_type = result.metadata.get('result_type', 'result')
            if result_type == 'variable':
                category = "Variables"
            elif result_type == 'equation':
                category = "Equations"
            else:
                category = "Results"

            if category not in categories:
                categories[category] = []
            categories[category].append((result_name, result))

        # Sort categories
        sorted_categories = sorted(categories.keys())

        # Create tree items
        for category in sorted_categories:
            results_list = categories[category]
            category_item = QTreeWidgetItem(self)
            category_item.setText(0, f"{category} ({len(results_list)} results)")

            # Sort results within category
            results_list.sort(key=lambda x: x[0])

            for result_name, result in results_list:
                result_item = QTreeWidgetItem(category_item)
                result_item.setText(0, result_name)

                # Add metadata to tooltip
                dims_info = f"Dimensions: {', '.join(result.metadata.get('dims', []))}" if result.metadata.get('dims') else "No dimensions"
                shape_info = f"Shape: {result.metadata.get('shape', ('?', '?'))}"
                units_info = f"Units: {result.metadata.get('units', 'N/A')}"
                tooltip = f"Result: {result_name}\n{dims_info}\n{shape_info}\n{units_info}"
                result_item.setToolTip(0, tooltip)

            category_item.setExpanded(True)

    def _categorize_parameter(self, param_name: str, parameter) -> str:
        """Categorize a parameter based on its name and properties"""
        name_lower = param_name.lower()

        # Environmental (check first since emission_factor contains 'factor')
        if any(keyword in name_lower for keyword in ['emission', 'emiss', 'carbon', 'co2']):
            return "Environmental"
        
        # Bounds and constraints (check before capacity since capacity_lo should be bounds)
        elif (any(keyword in name_lower for keyword in ['bound', 'limit', 'max', 'min']) or
              param_name.endswith('_lo') or param_name.endswith('_up')):
            return "Bounds & Constraints"

        # Operational (check before Economic since operation_cost should be Operational)
        elif any(keyword in name_lower for keyword in ['operation', 'oper', 'maintenance']):
            return "Operational"

        # Economic parameters
        elif any(keyword in name_lower for keyword in ['cost', 'price', 'revenue', 'profit', 'subsidy']):
            return "Economic"

        # Capacity and investment
        elif any(keyword in name_lower for keyword in ['capacity', 'cap', 'investment', 'inv']):
            return "Capacity & Investment"

        # Demand and consumption
        elif any(keyword in name_lower for keyword in ['demand', 'load', 'consumption']):
            return "Demand & Consumption"

        # Technical parameters
        elif any(keyword in name_lower for keyword in ['efficiency', 'eff', 'factor', 'ratio']):
            return "Technical"

        # Temporal
        elif any(keyword in name_lower for keyword in ['duration', 'lifetime', 'year']):
            return "Temporal"

        # Default category
        else:
            return "Other"

    def _categorize_variable(self, var_name: str, variable) -> str:
        """Categorize a variable based on its name and properties"""
        name_lower = var_name.lower()

        # Activity variables
        if any(keyword in name_lower for keyword in ['activity', 'act', 'production', 'output']):
            return "Activity"

        # Capacity variables
        elif any(keyword in name_lower for keyword in ['capacity', 'cap']):
            return "Capacity"

        # Flow variables
        elif any(keyword in name_lower for keyword in ['flow', 'transport', 'trade']):
            return "Flow"

        # Storage variables
        elif any(keyword in name_lower for keyword in ['storage', 'stor']):
            return "Storage"

        # Emission variables
        elif any(keyword in name_lower for keyword in ['emission', 'emiss']):
            return "Emissions"

        # Default category
        else:
            return "Other"

    def _categorize_result(self, result_name: str, result) -> str:
        """Categorize a result based on its name and properties"""
        name_lower = result_name.lower()

        # Objective function results
        if any(keyword in name_lower for keyword in ['obj', 'objective', 'cost', 'total']):
            return "Objective"

        # Activity results
        elif any(keyword in name_lower for keyword in ['activity', 'act', 'production']):
            return "Activity"

        # Capacity results
        elif any(keyword in name_lower for keyword in ['capacity', 'cap']):
            return "Capacity"

        # Flow results
        elif any(keyword in name_lower for keyword in ['flow', 'transport', 'trade']):
            return "Flow"

        # Price results
        elif any(keyword in name_lower for keyword in ['price', 'cost', 'dual']):
            return "Prices"

        # Emission results
        elif any(keyword in name_lower for keyword in ['emission', 'emiss']):
            return "Emissions"

        # Default category
        else:
            return "Other"

    def _on_item_selected(self):
        """Handle item selection in the tree"""
        selected_items = self.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]
        item_name = selected_item.text(0)

        # Check if it's a section header
        if isinstance(selected_item, SectionTreeItem):
            self.section_selected.emit(selected_item.section_type)
            return

        # Special handling for Dashboard
        if item_name == "Dashboard":
            # In multi-section mode, dashboard is always input-style
            is_results = self.current_view == "results" and self.current_view != "multi"
            self.parameter_selected.emit("Dashboard", is_results)
            return

        # Check if it's a category (no parent, and not Dashboard)
        if selected_item.parent() is None:
            # It's a category, emit None to clear displays
            is_results = self.current_view == "results" and self.current_view != "multi"
            self.parameter_selected.emit(None, is_results)
            return

        # Get parameter/result name and determine data source
        # For multi-section view, determine source from section hierarchy
        is_results = self.current_view == "results"
        if self.current_view == "multi":
            # Find which section this parameter belongs to
            parent = selected_item.parent()
            while parent:
                if isinstance(parent, SectionTreeItem):
                    if parent.section_type in ["variables", "results"]:
                        is_results = True
                    break
                parent = parent.parent()
        
        self.parameter_selected.emit(item_name, is_results)

    def set_view_mode(self, is_results: bool):
        """Set whether this tree shows parameters or results"""
        self.current_view = "results" if is_results else "input"
        self.setHeaderLabel("Results" if is_results else "Parameters")

    def clear_selection_silently(self):
        """Clear selection without emitting signals"""
        self.blockSignals(True)
        self.clearSelection()
        self.blockSignals(False)

    def resizeEvent(self, e):
        """Handle resize to reposition the buttons"""
        super().resizeEvent(e)
        self._position_buttons()

    def _position_buttons(self):
        """Position the buttons on the header"""
        if hasattr(self, 'add_button') and self.header():
            header_height = self.header().height()
            header_width = self.header().width()
            # Position add button on the right
            self.add_button.move(header_width - 30, (header_height - 24) // 2)

    def _show_context_menu(self, position):
        """Show context menu for add/remove parameter operations."""
        if not self.current_scenario or self.current_view != "input":
            return

        selected_items = self.selectedItems()
        menu = QMenu(self)

        # Add "Add Parameter..." action to category items
        if selected_items and selected_items[0].parent() is None:
            add_action = QAction("Add Parameter...", self)
            add_action.triggered.connect(self._add_parameter)
            menu.addAction(add_action)

        # Add "Remove Parameter" action to parameter items
        elif selected_items and selected_items[0].parent() is not None:
            remove_action = QAction("Remove Parameter", self)
            remove_action.triggered.connect(self._remove_parameter)
            menu.addAction(remove_action)

        # Show the menu
        menu.exec_(self.viewport().mapToGlobal(position))

    def _add_parameter(self):
        """Handle adding a new parameter."""
        if not self.current_scenario or not self.parameter_manager:
            return

        # Get existing parameter names
        existing_params = self.current_scenario.get_parameter_names()

        # Show the add parameter dialog
        from src.ui.components.add_parameter_dialog import AddParameterDialog
        dialog = AddParameterDialog(self.parameter_manager, existing_params, self.current_scenario, self)

        if dialog.exec_() == QDialog.Accepted:
            selected_param = dialog.get_selected_parameter()
            selected_data = dialog.get_selected_data()
            if selected_param and selected_data is not None:
                # Create the parameter command and execute it with populated data
                self._execute_add_parameter_command(selected_param, selected_data)

    def _execute_add_parameter_command(self, parameter_name: str, parameter_data=None):
        """Execute the add parameter command."""
        if not self.current_scenario or not self.parameter_manager:
            return

        # Use provided data or create empty DataFrame for the parameter
        if parameter_data is not None:
            df = parameter_data
        else:
            df = self.parameter_manager.create_empty_parameter_dataframe(parameter_name)

        param_info = self.parameter_manager.get_parameter_info(parameter_name)

        # Create metadata dictionary from parameter info
        metadata = {
            'description': param_info.get('description', '') if param_info else '',
            'dimensions': param_info.get('dims', []) if param_info else [],
            'type': param_info.get('type', 'float') if param_info else 'float'
        }

        # Create and execute the command
        from src.managers.commands import AddParameterCommand
        command = AddParameterCommand(self.current_scenario, parameter_name, df, metadata)

        if command.do():
            # Refresh the tree
            self.update_parameters(self.current_scenario, self.current_view == "results")

            # Emit signal to update the display
            self.parameter_selected.emit(parameter_name, self.current_view == "results")

            # Mark scenario as modified
            self.current_scenario.mark_modified(parameter_name)

    def _remove_parameter(self):
        """Handle removing a parameter."""
        if not self.current_scenario:
            return

        selected_items = self.selectedItems()
        if not selected_items or len(selected_items) == 0:
            return

        selected_item = selected_items[0]
        if not selected_item.parent():  # It's a category, not a parameter
            return

        parameter_name = selected_item.text(0)

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Remove Parameter",
            f"Are you sure you want to remove parameter '{parameter_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._execute_remove_parameter_command(parameter_name)

    def _execute_remove_parameter_command(self, parameter_name: str):
        """Execute the remove parameter command."""
        if not self.current_scenario:
            return

        # Create and execute the command
        from src.managers.commands import RemoveParameterCommand
        command = RemoveParameterCommand(self.current_scenario, parameter_name)

        if command.do():
            # Refresh the tree
            self.update_parameters(self.current_scenario, self.current_view == "results")

            # Clear selection
            self.clear_selection_silently()

            # Mark scenario as modified
            self.current_scenario.mark_modified(parameter_name)

    def set_parameter_manager(self, parameter_manager):
        """Set the parameter manager for this tree widget."""
        self.parameter_manager = parameter_manager
