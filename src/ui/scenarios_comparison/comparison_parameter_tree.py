"""
ComparisonParameterTreeWidget

A read-only parameter tree that merges two ScenarioData objects and shows:
  • parameters/variables present in BOTH scenarios  → normal, selectable
  • parameters/variables in only ONE scenario       → gray + italic + [A]/[B] badge, disabled

Uses the same section icons, category icons, and sidebar as ParameterTreeWidget.
"""

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from core.data_models import Parameter, ScenarioData

# Re-use icon tables and the search-highlight delegate from parameter_tree_widget
from ui.components.parameter_tree_widget import (
    _CATEGORY_ICONS,
    _SECTION_ICONS,
    _SECTION_TOOLTIPS,
    SearchHighlightDelegate,
)


# ---------------------------------------------------------------------------
# Helpers — inline copies so we don't couple tightly to unexported internals
# ---------------------------------------------------------------------------

def _categorize_parameter(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ['emission', 'emiss', 'carbon', 'co2']):
        return "Environmental"
    if any(k in n for k in ['bound', 'limit', 'max', 'min']) or name.endswith(('_lo', '_up')):
        return "Bounds & Constraints"
    if any(k in n for k in ['operation', 'oper', 'maintenance']):
        return "Operational"
    if any(k in n for k in ['cost', 'price', 'revenue', 'profit', 'subsidy']):
        return "Economic"
    if any(k in n for k in ['capacity', 'cap', 'investment', 'inv']):
        return "Capacity & Investment"
    if any(k in n for k in ['demand', 'load', 'consumption']):
        return "Demand & Consumption"
    if any(k in n for k in ['efficiency', 'eff', 'factor', 'ratio']):
        return "Technical"
    if any(k in n for k in ['duration', 'lifetime', 'year']):
        return "Temporal"
    return "Other"


def _categorize_variable(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ['activity', 'act', 'production', 'output']):
        return "Activity"
    if any(k in n for k in ['capacity', 'cap']):
        return "Capacity"
    if any(k in n for k in ['flow', 'transport', 'trade']):
        return "Flow"
    if any(k in n for k in ['storage', 'stor']):
        return "Storage"
    if any(k in n for k in ['emission', 'emiss']):
        return "Emissions"
    return "Other"


def _categorize_postprocessed(name: str) -> str:
    n = name.lower()
    if 'price' in n:
        return "Prices"
    if any(k in n for k in ['electricity', 'power plant', 'elec']):
        return "Electricity"
    if any(k in n for k in ['emission', 'ghg', 'co2']):
        return "Emissions"
    if any(k in n for k in ['primary energy', 'final energy', 'useful energy']):
        return "Energy Balances"
    if any(k in n for k in ['import', 'export', 'trade']):
        return "Trade"
    if any(k in n for k in ['transport', 'industry', 'buildings', 'feedstock']):
        return "Sectoral Use"
    if any(k in n for k in ['gas', 'coal', 'oil', 'biomass']):
        return "Fuels"
    return "Other"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MergedParameter:
    """Represents one parameter/variable/set entry in the merged view."""
    name: str
    presence: Literal['both', 'a_only', 'b_only']
    # row counts are None when the parameter doesn't exist in that scenario
    row_count_a: Optional[int]
    row_count_b: Optional[int]
    # section this entry belongs to
    section: str  # 'parameters' | 'variables' | 'postprocessing' | 'sets'


def _row_count(param: Optional[Parameter]) -> Optional[int]:
    if param is None:
        return None
    return len(param.df) if param.df is not None else 0


def _determine_section(name: str, param: Optional[Parameter]) -> str:
    """Return which tree section this parameter belongs to."""
    if param is None:
        return 'parameters'
    rt = param.metadata.get('result_type', '')
    if rt == 'postprocessed':
        return 'postprocessing'
    if rt in ('variable', 'equation'):
        return 'variables'
    return 'parameters'


def _build_merged_list(
    data_a: ScenarioData,
    data_b: ScenarioData,
) -> Tuple[List[MergedParameter], List[MergedParameter]]:
    """
    Compute merged parameter list and merged sets list.

    Returns (merged_params, merged_sets).
    """
    names_a: set = set(data_a.get_parameter_names())
    names_b: set = set(data_b.get_parameter_names())
    all_names = names_a | names_b

    merged: List[MergedParameter] = []
    for name in all_names:
        param_a = data_a.get_parameter(name)
        param_b = data_b.get_parameter(name)

        if name in names_a and name in names_b:
            presence = 'both'
        elif name in names_a:
            presence = 'a_only'
        else:
            presence = 'b_only'

        section = _determine_section(name, param_a or param_b)
        merged.append(MergedParameter(
            name=name,
            presence=presence,
            row_count_a=_row_count(param_a),
            row_count_b=_row_count(param_b),
            section=section,
        ))

    # Sets
    sets_a = set(data_a.sets.keys()) if data_a.sets else set()
    sets_b = set(data_b.sets.keys()) if data_b.sets else set()
    all_sets = sets_a | sets_b

    merged_sets: List[MergedParameter] = []
    for name in all_sets:
        if name in sets_a and name in sets_b:
            presence = 'both'
            rc_a = len(data_a.sets[name])
            rc_b = len(data_b.sets[name])
        elif name in sets_a:
            presence = 'a_only'
            rc_a = len(data_a.sets[name])
            rc_b = None
        else:
            presence = 'b_only'
            rc_a = None
            rc_b = len(data_b.sets[name])

        merged_sets.append(MergedParameter(
            name=name,
            presence=presence,
            row_count_a=rc_a,
            row_count_b=rc_b,
            section='sets',
        ))

    return merged, merged_sets


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

_GRAY = QColor('#999999')
_SIDEBAR_WIDTH = 28


class ComparisonParameterTreeWidget(QTreeWidget):
    """
    Read-only parameter tree for the comparison window.

    Signals
    -------
    parameter_selected(str)
        Emitted when the user clicks a parameter that exists in BOTH
        scenarios.  The argument is the raw parameter name.
    section_jumped(str)
        Emitted when a sidebar icon button is clicked.
    """

    parameter_selected = pyqtSignal(str)
    section_jumped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data_a: Optional[ScenarioData] = None
        self._data_b: Optional[ScenarioData] = None
        self._label_a: str = "A"
        self._label_b: str = "B"

        # Maps section_type → top-level QTreeWidgetItem
        self._section_items: Dict[str, QTreeWidgetItem] = {}

        # Highlight delegate for search
        self._delegate = SearchHighlightDelegate(self)
        self.setItemDelegate(self._delegate)

        self._setup_ui()
        self._setup_sidebar()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setHeaderLabel("Parameters")
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.itemClicked.connect(self._on_item_clicked)

        # Search bar (hidden by default)
        self._search_bar = QLineEdit(self)
        self._search_bar.setPlaceholderText("filter…")
        self._search_bar.setVisible(False)
        self._search_bar.textChanged.connect(self._filter_items)
        self._search_bar.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 9px;
                padding-left: 6px;
                background: #f2f2f2;
                font-size: 11px;
            }
            QLineEdit:focus { border-color: #66afe9; }
        """)

        # 🔍 toggle button
        self._search_btn = QPushButton("🔍", self)
        self._search_btn.setCheckable(True)
        self._search_btn.setFixedSize(26, 22)
        self._search_btn.setStyleSheet(
            "QPushButton { font-size:15px; border:none; background:transparent; }"
            "QPushButton:hover { background: rgba(0,0,0,0.08); border-radius:3px; }"
        )
        self._search_btn.clicked.connect(self._toggle_search)

        self._position_header_buttons()

    def _setup_sidebar(self) -> None:
        """Create the 28-px icon sidebar (same approach as ParameterTreeWidget)."""
        self._sidebar = QWidget(self)
        self._sidebar.setObjectName("cmpSidebar")
        self._sidebar.setStyleSheet("""
            QWidget#cmpSidebar {
                background: #f0f0f0;
                border-right: 1px solid #d0d0d0;
            }
        """)
        self._sidebar_layout = QVBoxLayout(self._sidebar)
        self._sidebar_layout.setContentsMargins(2, 4, 2, 4)
        self._sidebar_layout.setSpacing(3)
        self._sidebar_layout.addStretch()
        self._sidebar.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(
        self,
        data_a: ScenarioData,
        data_b: ScenarioData,
        label_a: str = "A",
        label_b: str = "B",
    ) -> None:
        """Build the merged tree from two ScenarioData objects."""
        self._data_a = data_a
        self._data_b = data_b
        self._label_a = label_a
        self._label_b = label_b

        self.clear()
        self._section_items.clear()

        merged_params, merged_sets = _build_merged_list(data_a, data_b)

        # Group merged params by section
        by_section: Dict[str, List[MergedParameter]] = {}
        for mp in merged_params:
            by_section.setdefault(mp.section, []).append(mp)

        section_order = ['parameters', 'variables', 'postprocessing']
        for section_type in section_order:
            items = by_section.get(section_type, [])
            if not items:
                continue
            self._add_section(section_type, items)

        # Sets section
        if merged_sets:
            self._add_sets_section(merged_sets)

        self._rebuild_sidebar()

    # ------------------------------------------------------------------
    # Tree building helpers
    # ------------------------------------------------------------------

    def _add_section(self, section_type: str, items: List[MergedParameter]) -> None:
        icon = _SECTION_ICONS.get(section_type, '•')
        tip = _SECTION_TOOLTIPS.get(section_type, section_type)
        section_item = QTreeWidgetItem(self)
        section_item.setText(0, f"{icon}  {section_type.title()} ({len(items)})")
        section_item.setToolTip(0, tip)
        section_item.setBackground(0, QColor(240, 240, 240))
        f = section_item.font(0)
        f.setBold(True)
        section_item.setFont(0, f)
        # Not selectable — clicking a section header shouldn't emit parameter_selected
        section_item.setFlags(section_item.flags() & ~Qt.ItemIsSelectable)
        self._section_items[section_type] = section_item

        # Group by category
        categories: Dict[str, List[MergedParameter]] = {}
        for mp in items:
            if section_type == 'parameters':
                cat = _categorize_parameter(mp.name)
            elif section_type == 'variables':
                cat = _categorize_variable(mp.name)
            elif section_type == 'postprocessing':
                cat = _categorize_postprocessed(mp.name)
            else:
                cat = "Other"
            categories.setdefault(cat, []).append(mp)

        for cat in sorted(categories.keys()):
            cat_icon = _CATEGORY_ICONS.get(cat, '•')
            cat_item = QTreeWidgetItem(section_item)
            cat_item.setText(0, f"{cat_icon}  {cat} ({len(categories[cat])})")
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsSelectable)

            for mp in sorted(categories[cat], key=lambda x: x.name):
                self._add_param_item(cat_item, mp)

            cat_item.setExpanded(True)

        section_item.setExpanded(True)

    def _add_sets_section(self, merged_sets: List[MergedParameter]) -> None:
        icon = _SECTION_ICONS.get('sets', '🗂')
        section_item = QTreeWidgetItem(self)
        section_item.setText(0, f"{icon}  Sets ({len(merged_sets)})")
        section_item.setBackground(0, QColor(240, 240, 240))
        f = section_item.font(0)
        f.setBold(True)
        section_item.setFont(0, f)
        section_item.setFlags(section_item.flags() & ~Qt.ItemIsSelectable)
        self._section_items['sets'] = section_item

        for mp in sorted(merged_sets, key=lambda x: x.name):
            self._add_param_item(section_item, mp)

        section_item.setExpanded(True)

    def _add_param_item(self, parent: QTreeWidgetItem, mp: MergedParameter) -> None:
        """Add one leaf item with correct styling based on presence."""
        badge = ''
        if mp.presence == 'a_only':
            badge = f' [{self._label_a}]'
        elif mp.presence == 'b_only':
            badge = f' [{self._label_b}]'

        # Row count label
        if mp.presence == 'both':
            count_str = f'(A:{mp.row_count_a} / B:{mp.row_count_b})'
        elif mp.presence == 'a_only':
            count_str = f'({mp.row_count_a} rows)'
        else:
            count_str = f'({mp.row_count_b} rows)'

        item = QTreeWidgetItem(parent)
        item.setText(0, f"{mp.name}{badge}  {count_str}")
        item.setData(0, Qt.UserRole, mp.name if mp.presence == 'both' else None)

        if mp.presence != 'both':
            # Gray + italic + disabled
            item.setForeground(0, QBrush(_GRAY))
            font = item.font(0)
            font.setItalic(True)
            item.setFont(0, font)
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)

        # Tooltip
        if mp.presence == 'both':
            tip = (f"{mp.name}\n"
                   f"{self._label_a}: {mp.row_count_a} rows\n"
                   f"{self._label_b}: {mp.row_count_b} rows")
        elif mp.presence == 'a_only':
            tip = f"{mp.name}\nOnly in {self._label_a} ({mp.row_count_a} rows)"
        else:
            tip = f"{mp.name}\nOnly in {self._label_b} ({mp.row_count_b} rows)"
        item.setToolTip(0, tip)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _rebuild_sidebar(self) -> None:
        """Recreate sidebar icon buttons to match current sections."""
        while self._sidebar_layout.count() > 1:
            it = self._sidebar_layout.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()

        sections = list(self._section_items.keys())
        if not sections:
            self._sidebar.hide()
            self.setViewportMargins(0, 0, 0, 0)
            return

        for sec in sections:
            icon = _SECTION_ICONS.get(sec, '•')
            tip = _SECTION_TOOLTIPS.get(sec, sec)
            btn = QPushButton(icon, self._sidebar)
            btn.setToolTip(tip)
            btn.setFixedSize(_SIDEBAR_WIDTH - 4, _SIDEBAR_WIDTH - 4)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    border: none;
                    background: transparent;
                    padding: 0px;
                }
                QPushButton:hover {
                    background: rgba(0,0,0,0.1);
                    border-radius: 3px;
                }
            """)
            # Capture sec in closure
            btn.clicked.connect(lambda _checked, s=sec: self._jump_to_section(s))
            self._sidebar_layout.insertWidget(self._sidebar_layout.count() - 1, btn)

        self._sidebar.show()
        self.setViewportMargins(_SIDEBAR_WIDTH, 0, 0, 0)
        self._position_sidebar()

    def _jump_to_section(self, section_type: str) -> None:
        item = self._section_items.get(section_type)
        if item:
            self.scrollToItem(item, QTreeWidget.PositionAtTop)
            self.section_jumped.emit(section_type)

    # ------------------------------------------------------------------
    # Selection handler
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """Emit parameter_selected only for 'both' leaf items."""
        raw_name = item.data(0, Qt.UserRole)
        if raw_name:
            self.parameter_selected.emit(raw_name)

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def _toggle_search(self) -> None:
        visible = not self._search_bar.isVisible()
        self._search_bar.setVisible(visible)
        if visible:
            self._search_bar.setFocus()
        else:
            self._search_bar.clear()
        self._position_header_buttons()

    def _filter_items(self, text: str) -> None:
        """Show/hide leaf items matching *text*; always show parents of visible items."""
        text = text.strip().lower()
        self._delegate.set_search_text(text)

        def _visit(item: QTreeWidgetItem) -> bool:
            """Return True if this item or any child is visible."""
            item_text = item.text(0).lower()
            match = not text or text in item_text
            child_visible = False
            for i in range(item.childCount()):
                child_visible = _visit(item.child(i)) or child_visible
            visible = match or child_visible
            item.setHidden(not visible)
            return visible

        for i in range(self.topLevelItemCount()):
            _visit(self.topLevelItem(i))

        self.viewport().update()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_header_buttons()
        self._position_sidebar()

    def _position_header_buttons(self) -> None:
        header = self.header()
        if header is None:
            return
        hh = header.height()
        hw = header.width()
        bw, bh = 26, 22
        # Search icon — far right
        self._search_btn.setGeometry(hw - bw - 2, max(0, (hh - bh) // 2), bw, bh)
        # Search bar — fills remaining space
        if self._search_bar.isVisible():
            self._search_bar.setGeometry(2, max(0, (hh - bh) // 2), hw - bw - 6, bh)

    def _position_sidebar(self) -> None:
        if not self._sidebar.isVisible():
            return
        vp = self.viewport()
        # Sidebar overlaps the left margin we reserved via setViewportMargins
        self._sidebar.setGeometry(0, self.header().height(), _SIDEBAR_WIDTH, vp.height())
