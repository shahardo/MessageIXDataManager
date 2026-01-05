"""
Parameter Tree Widget - Handles parameter/result tree navigation

Extracted from MainWindow to provide focused tree navigation functionality.
"""

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import pyqtSignal
from typing import Optional, List, Dict, Tuple

from core.data_models import ScenarioData


class ParameterTreeWidget(QTreeWidget):
    """Handles parameter/result tree navigation"""

    # Signals
    parameter_selected = pyqtSignal(object, bool)  # parameter, is_results

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "input"  # "input" or "results"
        self.setup_ui()

    def setup_ui(self):
        """Set up the tree widget"""
        self.setHeaderLabel("Parameters")
        self.itemSelectionChanged.connect(self._on_item_selected)

    def update_parameters(self, scenario: ScenarioData, is_results: bool = False):
        """Update the tree with parameters from a scenario"""
        self.clear()

        if not scenario:
            return

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

        if not scenario:
            return

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

        # Economic parameters
        if any(keyword in name_lower for keyword in ['cost', 'price', 'revenue', 'profit', 'subsidy']):
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

        # Environmental
        elif any(keyword in name_lower for keyword in ['emission', 'emiss', 'carbon', 'co2']):
            return "Environmental"

        # Temporal
        elif any(keyword in name_lower for keyword in ['duration', 'lifetime', 'year']):
            return "Temporal"

        # Operational
        elif any(keyword in name_lower for keyword in ['operation', 'oper', 'maintenance']):
            return "Operational"

        # Bounds and constraints
        elif any(keyword in name_lower for keyword in ['bound', 'limit', 'max', 'min']):
            return "Bounds & Constraints"

        # Default category
        else:
            return "Other"

    def _on_item_selected(self):
        """Handle item selection in the tree"""
        selected_items = self.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]

        # Check if it's a parameter/result item (not a category)
        if selected_item.parent() is None:
            # It's a category, emit None to clear displays
            self.parameter_selected.emit(None, self.current_view == "results")
            return

        # Get parameter/result name
        item_name = selected_item.text(0)

        # For now, emit the name - the parent will need to look up the actual parameter
        # This could be improved by storing the parameter object in the item data
        self.parameter_selected.emit(item_name, self.current_view == "results")

    def set_view_mode(self, is_results: bool):
        """Set whether this tree shows parameters or results"""
        self.current_view = "results" if is_results else "input"
        self.setHeaderLabel("Results" if is_results else "Parameters")

    def clear_selection_silently(self):
        """Clear selection without emitting signals"""
        self.blockSignals(True)
        self.clearSelection()
        self.blockSignals(False)
