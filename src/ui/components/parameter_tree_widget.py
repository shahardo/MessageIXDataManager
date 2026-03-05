"""
Parameter Tree Widget - Handles parameter/result tree navigation

Extracted from MainWindow to provide focused tree navigation functionality.
"""

from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QLabel, QPushButton,
    QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QHeaderView, QMenu,
    QAction, QMessageBox, QLineEdit, QStyledItemDelegate, QApplication, QStyle,
    QShortcut,
)
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QFont, QColor, QKeySequence
from typing import Optional, List, Dict

from core.data_models import ScenarioData


class SearchHighlightDelegate(QStyledItemDelegate):
    """
    Item delegate that paints a yellow highlight around the substring that
    matched the current search text.  Non-matching items fall back to the
    default rendering.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_text: str = ""

    def set_search_text(self, text: str) -> None:
        """Update the substring to highlight (case-insensitive)."""
        self._search_text = text.lower().strip()

    def paint(self, painter, option, index) -> None:
        text: str = index.data(Qt.DisplayRole) or ""
        search = self._search_text
        pos = text.lower().find(search) if search else -1

        if pos < 0:
            # No match — use default rendering
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        is_selected = bool(option.state & QStyle.State_Selected)
        style = option.widget.style() if option.widget else QApplication.style()

        # Text rect must be queried BEFORE we wipe option.text
        text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, option, option.widget)
        if not text_rect.isValid():
            text_rect = option.rect.adjusted(2, 0, 0, 0)

        # Draw the row (background, selection highlight, icon) without text
        option.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)

        # Split text around the match
        before = text[:pos]
        match_str = text[pos: pos + len(search)]
        after = text[pos + len(search):]

        fm = painter.fontMetrics()
        baseline_y = text_rect.y() + (text_rect.height() - fm.height()) // 2 + fm.ascent()

        pen_color = (
            option.palette.highlightedText().color() if is_selected
            else option.palette.text().color()
        )

        painter.save()
        painter.setFont(option.font)
        painter.setClipRect(text_rect)
        painter.setPen(pen_color)

        x = text_rect.x()
        if before:
            painter.drawText(x, baseline_y, before)
            x += fm.horizontalAdvance(before)

        mw = fm.horizontalAdvance(match_str)
        hl_color = QColor(255, 210, 0, 160 if is_selected else 210)
        painter.fillRect(x, text_rect.y() + 2, mw, text_rect.height() - 4, hl_color)
        painter.drawText(x, baseline_y, match_str)
        x += mw

        if after:
            painter.drawText(x, baseline_y, after)

        painter.restore()


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

        # Delegate that draws search-match highlights
        self._highlight_delegate = SearchHighlightDelegate(self)
        self.setItemDelegate(self._highlight_delegate)

        self.setup_ui()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def setup_ui(self):
        """Set up the tree widget"""
        self.setHeaderLabel("Parameters")
        self.itemSelectionChanged.connect(self._on_item_selected)

        # Add parameter button (far-right of header)
        self.add_button = QPushButton("+", self)
        self.add_button.setToolTip("Add Parameter")
        self.add_button.setFixedSize(28, 22)
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
                border-radius: 3px;
            }
        """)
        self.add_button.clicked.connect(self._add_parameter)

        # 🔍 toggle button — always visible, sits just left of '+'.
        # Clicking shows/hides the search field.
        _icon_btn_style = """
            QPushButton {
                font-size: 15px;
                padding: 0px;
                border: none;
                background: transparent;
            }
            QPushButton:hover { background: rgba(0,0,0,0.08); border-radius: 3px; }
            QPushButton:checked { background: transparent; }
        """
        self.search_icon_btn = QPushButton("🔍", self)
        self.search_icon_btn.setToolTip("Filter parameters  (click to show/hide)")
        self.search_icon_btn.setCheckable(True)
        self.search_icon_btn.setFixedSize(26, 22)
        self.search_icon_btn.setStyleSheet(_icon_btn_style)
        self.search_icon_btn.clicked.connect(self._toggle_search)

        # Search field — hidden until toggled.
        # Layout when open:  [✕ ______text______ 🔍][+]
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("filter parameters…")
        self.search_bar.setVisible(False)
        self.search_bar.textChanged.connect(self._filter_items)
        self.search_bar.installEventFilter(self)  # Up/Down/Enter/Escape
        self.search_bar.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 9px;
                padding-left: 22px;
                padding-right: 26px;
                background: #f2f2f2;
                font-size: 11px;
            }
            QLineEdit:focus { border-color: #66afe9; }
        """)

        # ✕ clear button — overlaid on the left edge of the search field.
        # Qt.NoFocus keeps mouse click from stealing focus away from search_bar.
        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setToolTip("Clear filter")
        self.clear_btn.setVisible(False)
        self.clear_btn.setFixedSize(18, 18)
        self.clear_btn.setFocusPolicy(Qt.NoFocus)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                color: #888;
                padding: 0px;
                border: none;
                border-radius: 9px;
                background: transparent;
            }
            QPushButton:hover {
                color: #222;
                background: rgba(0, 0, 0, 0.15);
            }
        """)
        self.clear_btn.clicked.connect(self._clear_search_and_refocus)

        # Keyboard shortcut — Ctrl+Shift+F opens/closes the search field
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        shortcut.setContext(Qt.WindowShortcut)
        shortcut.activated.connect(self._toggle_search)

        self._position_buttons()

    def update_tree_with_sections(self, scenario: ScenarioData, sections_data: Dict[str, List]):
        """
        Update the tree with multiple sections containing categorized data

        Args:
            scenario: The scenario data
            sections_data: Dict mapping section_type to list of (name, item) tuples
        """
        self._reset_search()
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
                elif section_type == "postprocessing":
                    # Postprocessed results have their own categorization
                    category = self._categorize_postprocessed(item_name, item)
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
                    row_count = len(item.df) if item.df is not None else 0
                    param_item.setText(0, f"{item_name} ({row_count} rows)")
                    param_item.setData(0, Qt.UserRole, item_name)

                    # Add metadata to tooltip based on section type
                    if section_type in ["parameters", "variables"]:
                        dims_info = f"Dimensions: {', '.join(item.metadata.get('dims', []))}" if item.metadata.get('dims') else "No dimensions"
                        tooltip = f"{section_type.title()[:-1]}: {item_name}\n{dims_info}"
                    elif section_type == "postprocessing":
                        dims_info = f"Dimensions: {', '.join(item.metadata.get('dims', []))}" if item.metadata.get('dims') else "No dimensions"
                        units_info = f"Units: {item.metadata.get('units', 'N/A')}"
                        tooltip = f"Postprocessed: {item_name}\n{dims_info}\n{units_info}"
                    else:  # results
                        dims_info = f"Dimensions: {', '.join(item.metadata.get('dims', []))}" if item.metadata.get('dims') else "No dimensions"
                        shape_info = f"Shape: {item.metadata.get('shape', ('?', '?'))}"
                        units_info = f"Units: {item.metadata.get('units', 'N/A')}"
                        tooltip = f"Result: {item_name}\n{dims_info}\n{shape_info}\n{units_info}"

                    param_item.setToolTip(0, tooltip)

                category_item.setExpanded(True)

            section_item.setExpanded(True)

        # Add sets section if the scenario has any sets
        if scenario.sets:
            sets_section = QTreeWidgetItem(self)
            sets_section.setText(0, f"Sets ({len(scenario.sets)})")
            sets_section.setToolTip(0, "MESSAGEix sets (codelists and mapping sets)")
            sets_section.setBackground(0, QColor(240, 240, 240))
            font = sets_section.font(0)
            font.setBold(True)
            sets_section.setFont(0, font)

            for set_name, set_values in sorted(scenario.sets.items()):
                set_item = QTreeWidgetItem(sets_section)
                set_item.setText(0, f"{set_name} ({len(set_values)} rows)")
                set_item.setToolTip(0, f"Set: {set_name}\nRows: {len(set_values)}")
                # Store raw name so selection handler can look it up without the row-count suffix
                set_item.setData(0, Qt.UserRole, set_name)

            sets_section.setExpanded(True)

    def update_parameters(self, scenario: ScenarioData, is_results: bool = False):
        """Update the tree with parameters from a scenario"""
        # For now, maintain backward compatibility by showing parameters in a single section
        # This will be updated when we implement the full section-based system
        self._reset_search()
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
                row_count = len(parameter.df) if parameter.df is not None else 0
                param_item.setText(0, f"{param_name} ({row_count} rows)")
                param_item.setData(0, Qt.UserRole, param_name)

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
                set_item.setText(0, f"{set_name} ({len(set_values)} rows)")
                set_item.setToolTip(0, f"Set: {set_name}\nRows: {len(set_values)}")
                # Store the raw name so selection handler can look it up
                set_item.setData(0, Qt.UserRole, set_name)

            sets_item.setExpanded(True)

    def update_results(self, scenario: ScenarioData):
        """Update the tree with results from a scenario"""
        self._reset_search()
        self.clear()
        self.current_scenario = scenario

        if not scenario:
            return

        # Add dashboard item at the top
        dashboard_item = QTreeWidgetItem(self)
        dashboard_item.setText(0, "Dashboard")
        dashboard_item.setToolTip(0, "Display dashboard with key metrics and charts")

        # Separate raw results from postprocessed results
        raw_categories = {}
        postprocessed_categories = {}

        for result_name in scenario.get_parameter_names():
            result = scenario.get_parameter(result_name)
            if not result:
                continue

            result_type = result.metadata.get('result_type', 'result')

            if result_type == 'postprocessed':
                # Categorize postprocessed results by content type
                category = self._categorize_postprocessed(result_name, result)
                if category not in postprocessed_categories:
                    postprocessed_categories[category] = []
                postprocessed_categories[category].append((result_name, result))
            else:
                # Categorize raw results by variable/equation type
                if result_type == 'variable':
                    category = "Variables"
                elif result_type == 'equation':
                    category = "Equations"
                else:
                    category = "Results"

                if category not in raw_categories:
                    raw_categories[category] = []
                raw_categories[category].append((result_name, result))

        # Create Postprocessed Results section first (if any)
        if postprocessed_categories:
            total_postprocessed = sum(len(items) for items in postprocessed_categories.values())
            postprocessed_section = QTreeWidgetItem(self)
            postprocessed_section.setText(0, f"Postprocessed Results ({total_postprocessed})")
            postprocessed_section.setToolTip(0, "Derived metrics calculated from raw results")
            # Style the section header
            postprocessed_section.setBackground(0, QColor(230, 245, 255))  # Light blue
            font = postprocessed_section.font(0)
            font.setBold(True)
            postprocessed_section.setFont(0, font)

            # Add subcategories for postprocessed results
            for category in sorted(postprocessed_categories.keys()):
                results_list = postprocessed_categories[category]
                category_item = QTreeWidgetItem(postprocessed_section)
                category_item.setText(0, f"{category} ({len(results_list)})")

                # Sort results within category
                results_list.sort(key=lambda x: x[0])

                for result_name, result in results_list:
                    result_item = QTreeWidgetItem(category_item)
                    result_item.setText(0, result_name)

                    # Add metadata to tooltip
                    dims_info = f"Dimensions: {', '.join(result.metadata.get('dims', []))}" if result.metadata.get('dims') else "No dimensions"
                    units_info = f"Units: {result.metadata.get('units', 'N/A')}"
                    tooltip = f"Postprocessed: {result_name}\n{dims_info}\n{units_info}"
                    result_item.setToolTip(0, tooltip)

                category_item.setExpanded(True)

            postprocessed_section.setExpanded(True)

        # Create raw results sections
        sorted_categories = sorted(raw_categories.keys())

        for category in sorted_categories:
            results_list = raw_categories[category]
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

    def _categorize_postprocessed(self, result_name: str, result) -> str:
        """Categorize a postprocessed result based on its name"""
        name_lower = result_name.lower()

        # Prices (check before electricity so "Electricity Price" → Prices)
        if 'price' in name_lower:
            return "Prices"

        # Electricity/Power sector
        elif any(keyword in name_lower for keyword in ['electricity', 'power plant', 'elec']):
            return "Electricity"

        # Emissions
        elif any(keyword in name_lower for keyword in ['emission', 'ghg', 'co2']):
            return "Emissions"

        # Energy balances (primary, final, useful)
        elif any(keyword in name_lower for keyword in ['primary energy', 'final energy', 'useful energy']):
            return "Energy Balances"

        # Trade (imports/exports)
        elif any(keyword in name_lower for keyword in ['import', 'export', 'trade']):
            return "Trade"

        # Sectoral energy use
        elif any(keyword in name_lower for keyword in ['transport', 'industry', 'buildings', 'feedstock']):
            return "Sectoral Use"

        # Fuel supply and utilization
        elif any(keyword in name_lower for keyword in ['gas', 'coal', 'oil', 'biomass']):
            return "Fuels"

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
        # Prefer the raw name stored in UserRole (set items store name without row-count suffix)
        raw_name = selected_item.data(0, Qt.UserRole)
        emit_name = raw_name if raw_name else item_name

        # For multi-section view, determine source from section hierarchy
        is_results = self.current_view == "results"
        if self.current_view == "multi":
            # Find which section this parameter belongs to
            parent = selected_item.parent()
            while parent:
                if isinstance(parent, SectionTreeItem):
                    # Postprocessing, variables, and results sections are all results data
                    if parent.section_type in ["variables", "results", "postprocessing"]:
                        is_results = True
                    break
                parent = parent.parent()

        self.parameter_selected.emit(emit_name, is_results)

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
        """Handle resize to reposition the header widgets"""
        super().resizeEvent(e)
        self._position_buttons()

    def _position_buttons(self):
        """
        Lay out the header widgets.

        Collapsed: [Parameters title] ········· [🔍][+]
        Expanded:  [Parameters title] [✕ text   ][🔍][+]

        The 🔍 toggle is always at a fixed position just left of +.
        When expanded the search_bar fills the gap between title and 🔍.
        The ✕ clear button is overlaid on the left edge of the search_bar.
        """
        header = self.header()
        if header is None or not hasattr(self, 'add_button'):
            return

        hh = header.height()
        hw = header.width()

        # Measure header title to find where the text ends
        hi = self.headerItem()
        title_text = hi.text(0) if hi else "Parameters"
        title_w = header.fontMetrics().horizontalAdvance(title_text) + 18  # +indent/margin

        # Vertical helpers
        def _centre(h): return max(0, (hh - h) // 2)

        # [+] add button — far right
        bw, bh = 28, 22
        self.add_button.setGeometry(hw - bw - 2, _centre(bh), bw, bh)

        # [🔍] toggle — always at a fixed position just left of [+]
        iw, ih = 26, 22
        icon_x = hw - bw - 2 - iw - 2          # 2 px gap between + and 🔍
        self.search_icon_btn.setGeometry(icon_x, _centre(ih), iw, ih)

        # [search_bar] and [✕] — only when search is open.
        # The bar extends rightward to enclose the 🔍 icon visually.
        if hasattr(self, 'search_bar') and self.search_bar.isVisible():
            bar_x = title_w + 6                         # 6 px gap after title
            bar_right = icon_x + iw + 2                 # right edge touches [+]
            bar_w = bar_right - bar_x
            bar_h = max(16, hh - 4)
            bar_y = _centre(bar_h)
            self.search_bar.setGeometry(bar_x, bar_y, bar_w, bar_h)

            if hasattr(self, 'clear_btn'):
                cb_size = 18
                self.clear_btn.setGeometry(
                    bar_x + 3, bar_y + (bar_h - cb_size) // 2, cb_size, cb_size
                )

            # Raise overlaid widgets above the search_bar in z-order
            self.search_icon_btn.raise_()
            self.clear_btn.raise_()

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def _clear_search_and_refocus(self):
        """Clear the search field and keep keyboard focus inside it."""
        self.search_bar.clear()
        self.search_bar.setFocus()

    def _toggle_search(self):
        """Show or hide the search field (called by the 🔍 button)."""
        if self.search_bar.isVisible():
            self._close_search()
        else:
            self.search_bar.setVisible(True)
            self.clear_btn.setVisible(True)
            self.search_icon_btn.setChecked(True)
            self._position_buttons()        # re-layout with bar now visible
            self.search_bar.setFocus()
            self.search_bar.selectAll()

    def _close_search(self):
        """Hide the search field and clear any active filter."""
        self.search_bar.blockSignals(True)
        self.search_bar.clear()
        self.search_bar.blockSignals(False)
        self.search_bar.setVisible(False)
        self.clear_btn.setVisible(False)
        self.search_icon_btn.setChecked(False)
        self._show_all_items()

    def _reset_search(self):
        """Reset search (called when tree content is replaced)."""
        self._close_search()

    def eventFilter(self, obj, event):
        """Intercept key presses on the search bar for navigation."""
        if obj is self.search_bar and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self._close_search()
                return True
            elif key == Qt.Key_Down:
                self._navigate_search_selection(1)
                return True
            elif key == Qt.Key_Up:
                self._navigate_search_selection(-1)
                return True
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                # Confirm the current selection and close search
                self._confirm_search_selection()
                return True
        return super().eventFilter(obj, event)

    def _navigate_search_selection(self, direction: int):
        """Move the current selection up (-1) or down (+1) through visible leaves."""
        leaves = self._get_all_visible_leaves()
        if not leaves:
            return
        current = self.currentItem()
        try:
            idx = leaves.index(current)
        except ValueError:
            idx = -1 if direction > 0 else len(leaves)
        new_idx = max(0, min(len(leaves) - 1, idx + direction))
        self.setCurrentItem(leaves[new_idx])
        self.scrollToItem(leaves[new_idx])

    def _confirm_search_selection(self):
        """Emit parameter_selected for the currently highlighted item."""
        self._on_item_selected()

    def _filter_items(self, text: str):
        """Filter tree items to those whose name contains *text* (case-insensitive)."""
        text = text.strip().lower()

        # Update highlight delegate so matching text is painted yellow
        self._highlight_delegate.set_search_text(text)

        if not text:
            self._show_all_items()
            return

        first_leaf = None

        for i in range(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            visible = self._apply_filter_recursive(top, text)
            top.setHidden(not visible)
            if visible and first_leaf is None:
                first_leaf = self._find_first_visible_leaf(top)

        # Auto-select the top match so the user can immediately navigate
        if first_leaf:
            self.setCurrentItem(first_leaf)
            self.scrollToItem(first_leaf)

        self.viewport().update()    # repaint to show new highlights

    def _apply_filter_recursive(self, item: QTreeWidgetItem, text: str) -> bool:
        """
        Recursively show/hide *item* and its subtree.

        Returns True if *item* itself or any descendant matches *text*.
        """
        if item.childCount() == 0:
            # Leaf node: visible iff its label contains the search text
            matches = text in item.text(0).lower()
            item.setHidden(not matches)
            return matches

        # Parent node: visible iff at least one child is visible
        any_child_visible = False
        for i in range(item.childCount()):
            child = item.child(i)
            child_visible = self._apply_filter_recursive(child, text)
            child.setHidden(not child_visible)
            if child_visible:
                any_child_visible = True

        if any_child_visible:
            item.setExpanded(True)  # expand parent so matches are reachable

        return any_child_visible

    def _show_all_items(self):
        """Restore full visibility for every item in the tree."""
        def _show(item: QTreeWidgetItem):
            item.setHidden(False)
            for i in range(item.childCount()):
                _show(item.child(i))

        for i in range(self.topLevelItemCount()):
            _show(self.topLevelItem(i))
        self.clearSelection()

        # Remove highlights
        self._highlight_delegate.set_search_text("")
        self.viewport().update()

    def _find_first_visible_leaf(self, item: QTreeWidgetItem) -> Optional[QTreeWidgetItem]:
        """Return the first visible leaf node in *item*'s subtree, or None."""
        if item.isHidden():
            return None
        if item.childCount() == 0:
            return item
        for i in range(item.childCount()):
            result = self._find_first_visible_leaf(item.child(i))
            if result is not None:
                return result
        return None

    def _get_all_visible_leaves(self) -> List[QTreeWidgetItem]:
        """Return all visible leaf items in top-to-bottom tree order."""
        result: List[QTreeWidgetItem] = []

        def _collect(item: QTreeWidgetItem):
            if item.isHidden():
                return
            if item.childCount() == 0:
                result.append(item)
            else:
                for i in range(item.childCount()):
                    _collect(item.child(i))

        for i in range(self.topLevelItemCount()):
            _collect(self.topLevelItem(i))
        return result

    # ------------------------------------------------------------------

    def _show_context_menu(self, position):
        """Show context menu for parameter operations and search."""
        selected_items = self.selectedItems()
        menu = QMenu(self)

        # Search action — always available when the tree has content
        if self.current_scenario:
            search_action = QAction("Search Parameters", self)
            search_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
            search_action.triggered.connect(self._toggle_search)
            menu.addAction(search_action)

        # Input-mode-only actions
        if self.current_scenario and self.current_view == "input":
            menu.addSeparator()

            if selected_items and selected_items[0].parent() is None:
                add_action = QAction("Add Parameter...", self)
                add_action.triggered.connect(self._add_parameter)
                menu.addAction(add_action)
            elif selected_items and selected_items[0].parent() is not None:
                remove_action = QAction("Remove Parameter", self)
                remove_action.triggered.connect(self._remove_parameter)
                menu.addAction(remove_action)

        if not menu.isEmpty():
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
