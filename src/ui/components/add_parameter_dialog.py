"""
Add Parameter Dialog for MessageIX Data Manager.

This dialog allows users to select from valid MESSAGEix parameters that are not yet in the scenario
and shows description and required dimensions for the selected parameter.
After parameter selection, users can choose elements and years to initialize the parameter with.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                            QListWidgetItem, QTextEdit, QPushButton, QTreeWidget,
                            QTreeWidgetItem, QComboBox, QMessageBox, QGroupBox,
                            QScrollArea, QWidget, QCheckBox, QSplitter)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Dict, Optional, Any, Set
import pandas as pd
import numpy as np

class AddParameterDialog(QDialog):
    """Dialog for adding new parameters to a scenario."""

    # Define which dimensions are considered sets vs years
    SET_DIMENSIONS = {
        'tec', 'commodity', 'node', 'node_loc', 'node_dest', 'node_origin',
        'level', 'mode', 'time', 'time_origin', 'time_dest', 'emission',
        'land_scenario', 'land_type', 'rating', 'type_addon', 'type_emission',
        'type_tec', 'type_year', 'shares', 'relation', 'node_rel', 'node_share',
        'grade', 'type_emiss'
    }

    # Mapping from dimension names to set names
    DIMENSION_TO_SET_MAPPING = {
        'tec': 'technology',
        'commodity': 'commodity',
        'node': 'node',
        'node_loc': 'node',
        'node_dest': 'node',
        'node_origin': 'node',
        'level': 'level',
        'mode': 'mode',
        'time': 'time',
        'time_origin': 'time',
        'time_dest': 'time',
        'emission': 'emission',
        'land_scenario': 'land_scenario',
        'land_type': 'land_type',
        'rating': 'rating',
        'type_addon': 'type_addon',
        'type_emission': 'type_emission',
        'type_tec': 'type_tec',
        'type_year': 'type_year',
        'shares': 'shares',
        'relation': 'relation',
        'node_rel': 'node',
        'node_share': 'node',
        'grade': 'grade',
        'type_emiss': 'type_emiss'
    }

    YEAR_DIMENSIONS = {
        'year', 'year_act', 'year_vtg', 'year_rel'
    }

    def __init__(self, parameter_manager, existing_parameters: List[str], scenario, parent=None):
        super().__init__(parent)
        self.parameter_manager = parameter_manager
        self.existing_parameters = existing_parameters
        self.scenario = scenario
        self.selected_parameter = None
        self.selected_elements = {}  # dim -> set of selected elements
        self.selected_years = set()

        self.setWindowTitle("Add Parameter")
        self.setMinimumSize(1000, 700)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout(self)

        # Category selection at the top
        category_layout = QHBoxLayout()
        category_label = QLabel("Category:")
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.parameter_manager.get_parameter_categories().keys())
        self.category_combo.currentTextChanged.connect(self._update_parameter_list)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        main_layout.addLayout(category_layout)

        # Main content area with parameter selection on left, elements/years on right
        content_layout = QHBoxLayout()

        # Parameter selection column (constrained width, left side)
        selection_widget = QWidget()
        selection_widget.setMaximumWidth(300)  # Constrain entire parameter selection column
        selection_layout = QVBoxLayout(selection_widget)

        # Available parameters list
        available_label = QLabel("Available Parameters:")
        available_label.setFont(QFont("Arial", 10, QFont.Bold))
        available_label.setFixedHeight(int(available_label.sizeHint().height() * 0.8))  # Limit to text height
        selection_layout.addWidget(available_label)

        self.available_list = QListWidget()
        self.available_list.itemSelectionChanged.connect(self._show_parameter_details)
        # self.available_list.setMaximumHeight(200)  # Limit height to leave space for details
        selection_layout.addWidget(self.available_list)

        # Parameter details below the list
        details_label = QLabel("Parameter Details:")
        details_label.setFont(QFont("Arial", 10, QFont.Bold))
        details_label.setFixedHeight(int(details_label.sizeHint().height() * 0.8))  # Limit to text height
        selection_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)  # Limit height for details
        selection_layout.addWidget(self.details_text)

        content_layout.addWidget(selection_widget)

        # Elements and years selection (right side, takes remaining space)
        selection_area = QWidget()
        selection_layout = QVBoxLayout(selection_area)

        # Elements and years in horizontal layout
        elements_years_layout = QHBoxLayout()

        # Elements selection (left side of selection area)
        elements_group = QGroupBox("Elements Selection")
        elements_layout = QVBoxLayout(elements_group)

        self.elements_scroll = QScrollArea()
        self.elements_scroll.setWidgetResizable(True)
        self.elements_container = QWidget()
        self.elements_layout = QVBoxLayout(self.elements_container)
        self.elements_scroll.setWidget(self.elements_container)
        elements_layout.addWidget(self.elements_scroll)

        elements_years_layout.addWidget(elements_group)

        # Years selection (right side of selection area)
        years_group = QGroupBox("Years Selection")
        years_layout = QVBoxLayout(years_group)

        self.years_scroll = QScrollArea()
        self.years_scroll.setWidgetResizable(True)
        self.years_container = QWidget()
        self.years_layout = QVBoxLayout(self.years_container)
        self.years_scroll.setWidget(self.years_container)
        years_layout.addWidget(self.years_scroll)

        elements_years_layout.addWidget(years_group)

        selection_layout.addLayout(elements_years_layout)
        content_layout.addWidget(selection_area)

        main_layout.addLayout(content_layout)

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

    # Removed duplicate method

    def _add_parameter(self):
        """Handle the add parameter action."""
        if not self.selected_parameter:
            return

        self.accept()

    def get_selected_parameter(self) -> Optional[str]:
        """Get the selected parameter name."""
        return self.selected_parameter

    def _get_dimension_type(self, dimension: str) -> str:
        """Classify a dimension as 'set', 'year', or 'other'."""
        if dimension in self.SET_DIMENSIONS:
            return 'set'
        elif dimension in self.YEAR_DIMENSIONS:
            return 'year'
        else:
            return 'other'

    def _count_element_usage(self, dimension: str) -> Dict[str, int]:
        """Count how many times each element appears in existing parameters for a given dimension."""
        usage_counts = {}

        # Get the actual set name for this dimension
        set_name = self.DIMENSION_TO_SET_MAPPING.get(dimension, dimension)

        # Check if the set exists in scenario
        if set_name not in self.scenario.sets:
            return usage_counts

        available_elements = self.scenario.sets[set_name]

        # Count occurrences in all existing parameters
        for param_name, parameter in self.scenario.parameters.items():
            df = parameter.df

            # Check if this dimension is used in the parameter
            if dimension in df.columns:
                # Count occurrences of each element in this dimension
                value_counts = df[dimension].value_counts()
                for element, count in value_counts.items():
                    if element in available_elements.values:
                        usage_counts[element] = usage_counts.get(element, 0) + count

        return usage_counts

    def _get_available_years(self) -> List[int]:
        """Get available years from scenario options and existing parameters."""
        years = set()

        # Add years from scenario options
        if hasattr(self.scenario, 'options'):
            min_year = self.scenario.options.get('MinYear', 2020)
            max_year = self.scenario.options.get('MaxYear', 2050)
            years.update(range(min_year, max_year + 1))

        # Add years from existing parameters
        for param_name, parameter in self.scenario.parameters.items():
            df = parameter.df
            for col in df.columns:
                if col in self.YEAR_DIMENSIONS:
                    try:
                        # Convert to numeric and add to set
                        numeric_years = pd.to_numeric(df[col], errors='coerce').dropna().astype(int)
                        years.update(numeric_years.unique())
                    except:
                        continue

        return sorted(list(years))

    def _show_parameter_details(self):
        """Show details for the selected parameter and populate element/year selection."""
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            self.details_text.clear()
            self.add_button.setEnabled(False)
            # Clear element/year selections
            self._clear_element_year_selections()
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

        # Populate element and year selections
        self._populate_element_year_selections(dimensions)

        # Enable add button if we have dimensions to select from
        has_selectable_dims = any(self._get_dimension_type(dim) in ['set', 'year'] for dim in dimensions)
        self.add_button.setEnabled(has_selectable_dims)

    def _clear_element_year_selections(self):
        """Clear all element and year selection widgets."""
        def clear_layout(layout):
            """Recursively clear a layout and delete widgets."""
            while layout.count():
                child = layout.takeAt(0)
                if child:
                    widget = child.widget()
                    if widget:
                        widget.deleteLater()
                    # If it's a nested layout, clear it too
                    elif child.layout():
                        clear_layout(child.layout())

        # Clear elements container
        clear_layout(self.elements_layout)

        # Clear years container
        clear_layout(self.years_layout)

        # Reset selections
        self.selected_elements = {}
        self.selected_years = set()

    def _populate_element_year_selections(self, dimensions: List[str]):
        """Populate the element and year selection UI based on parameter dimensions."""
        self._clear_element_year_selections()

        set_dimensions = []
        year_dimensions = []

        for dim in dimensions:
            dim_type = self._get_dimension_type(dim)
            if dim_type == 'set':
                set_dimensions.append(dim)
            elif dim_type == 'year':
                year_dimensions.append(dim)

        # Create element selection widgets
        if set_dimensions:
            for dim in set_dimensions:
                self._create_element_selection_widget(dim)

        # Create year selection widgets
        if year_dimensions:
            self._create_year_selection_widget()

    def _create_element_selection_widget(self, dimension: str):
        """Create a checkbox list for selecting elements of a dimension."""
        # Get the actual set name for this dimension
        set_name = self.DIMENSION_TO_SET_MAPPING.get(dimension, dimension)

        if set_name not in self.scenario.sets:
            return  # Skip if no set available

        group = QGroupBox(f"{dimension.title()} Elements")
        layout = QVBoxLayout(group)

        # Get elements sorted by usage frequency
        usage_counts = self._count_element_usage(dimension)
        elements = list(self.scenario.sets[set_name].values)

        # Sort by usage (most used first), then alphabetically
        elements.sort(key=lambda x: (-usage_counts.get(x, 0), x))

        # Create checkboxes
        checkboxes = []
        for element in elements:
            checkbox = QCheckBox(str(element))
            checkbox.setToolTip(f"Used {usage_counts.get(element, 0)} times in existing parameters")
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)

        self.elements_layout.addWidget(group)

        # Store checkboxes for later access
        if not hasattr(self, '_element_checkboxes'):
            self._element_checkboxes = {}
        self._element_checkboxes[dimension] = checkboxes

    def _create_year_selection_widget(self):
        """Create a checkbox list for selecting years."""
        group = QGroupBox("Years")
        layout = QVBoxLayout(group)

        years = self._get_available_years()

        # Create checkboxes
        checkboxes = []
        for year in years:
            checkbox = QCheckBox(str(year))
            layout.addWidget(checkbox)
            checkboxes.append(checkbox)

        self.years_layout.addWidget(group)

        # Store checkboxes for later access
        self._year_checkboxes = checkboxes

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

    def get_selected_data(self) -> Optional[pd.DataFrame]:
        """Get the DataFrame with selected elements and years."""
        if not self.selected_parameter:
            return None

        param_info = self.parameter_manager.get_parameter_info(self.selected_parameter)
        if not param_info:
            return None

        dimensions = param_info['dims']

        # Check if this parameter has any selectable dimensions
        has_selectable_dims = any(self._get_dimension_type(dim) in ['set', 'year'] for dim in dimensions)

        # If no selectable dimensions, return empty DataFrame (original behavior)
        if not has_selectable_dims:
            return pd.DataFrame(columns=dimensions + ['value'])

        # Collect selected elements for each dimension
        selected_values = {}
        for dim in dimensions:
            dim_type = self._get_dimension_type(dim)
            if dim_type == 'set' and dim in self._element_checkboxes:
                selected = [cb.text() for cb in self._element_checkboxes[dim] if cb.isChecked()]
                if selected:
                    selected_values[dim] = selected
                # Don't return None here - allow empty selections to fall through
            elif dim_type == 'year':
                if hasattr(self, '_year_checkboxes'):
                    selected = [int(cb.text()) for cb in self._year_checkboxes if cb.isChecked()]
                    if selected:
                        selected_values[dim] = selected
                    # Don't return None here - allow empty selections to fall through

        # If no selections were made, return empty DataFrame
        if not selected_values:
            return pd.DataFrame(columns=dimensions + ['value'])

        # Generate all combinations
        import itertools
        value_lists = [selected_values[dim] for dim in dimensions if dim in selected_values]
        if not value_lists:
            return pd.DataFrame(columns=dimensions + ['value'])

        combinations = list(itertools.product(*value_lists))

        # Create DataFrame with proper data types
        df_data = []
        for combo in combinations:
            row = {}
            for i, dim in enumerate([d for d in dimensions if d in selected_values]):
                val = combo[i]
                # Ensure year dimensions are integers
                if dim in self.YEAR_DIMENSIONS:
                    row[dim] = int(val)
                else:
                    row[dim] = val
            row['value'] = np.nan  # Empty value
            df_data.append(row)

        df = pd.DataFrame(df_data, columns=dimensions + ['value'])

        return df
