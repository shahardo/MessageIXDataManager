"""
Find Controller - Manages search functionality for parameters and table data

Extracted from MainWindow to provide focused find/search functionality.
"""

from PyQt5.QtWidgets import QTreeWidgetItem, QTableWidgetItem
from typing import List, Tuple, Optional


class FindController:
    """
    Controller for managing search operations across parameter trees and data tables.

    Handles parameter tree searching and table cell searching with state management.
    """

    def __init__(self, param_tree, param_table):
        """
        Initialize the find controller.

        Args:
            param_tree: The parameter tree widget for parameter searches
            param_table: The table widget for table cell searches
        """
        self.param_tree = param_tree
        self.param_table = param_table

        # Parameter search state
        self.parameter_matches: List[Tuple[str, QTreeWidgetItem]] = []
        self.current_param_match_index = -1

        # Table search state
        self.table_matches: List[Tuple[int, int, str]] = []
        self.current_table_match_index = -1

    def initialize_parameter_search(self, scenario) -> bool:
        """
        Initialize parameter search by collecting all parameter names.

        Args:
            scenario: Current scenario data

        Returns:
            True if search was initialized successfully
        """
        if not scenario:
            return False

        self.parameter_matches = []
        self.current_param_match_index = -1

        # Collect all parameter names from the tree
        def collect_parameters(parent_item, path=[]):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                item_name = child.text(0)

                # Skip category headers (they contain counts)
                if not item_name.startswith(("Parameters", "Results", "Economic", "Variables", "Sets")) and not item_name.endswith(")"):
                    self.parameter_matches.append((item_name, child))

                # Recursively collect from children
                collect_parameters(child, path + [item_name])

        root = self.param_tree.invisibleRootItem()
        collect_parameters(root)
        return True

    def initialize_table_search(self) -> bool:
        """
        Initialize table search by scanning all table cells.

        Returns:
            True if search was initialized successfully
        """
        self.table_matches = []
        self.current_table_match_index = -1

        # Scan all cells in the current table view
        for row in range(self.param_table.rowCount()):
            for col in range(self.param_table.columnCount()):
                item = self.param_table.item(row, col)
                if item:
                    cell_text = item.text().strip().lower()
                    if cell_text:
                        self.table_matches.append((row, col, cell_text))

        return True

    def find_first_parameter(self, search_text: str) -> Tuple[int, int]:
        """
        Find first parameter match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        # Find first match
        for i, (param_name, tree_item) in enumerate(self.parameter_matches):
            if search_lower in param_name.lower():
                self.current_param_match_index = i
                self._select_parameter_match(i)
                total_matches = len([p for p, _ in self.parameter_matches if search_lower in p.lower()])
                return i + 1, total_matches

        # No matches found
        return 0, 0

    def find_next_parameter(self, search_text: str) -> Tuple[int, int]:
        """
        Find next parameter match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        total_matches = len([p for p, _ in self.parameter_matches if search_lower in p.lower()])
        if total_matches == 0:
            return 0, 0

        # Find next match
        start_index = (self.current_param_match_index + 1) % len(self.parameter_matches)
        for i in range(len(self.parameter_matches)):
            check_index = (start_index + i) % len(self.parameter_matches)
            param_name, tree_item = self.parameter_matches[check_index]
            if search_lower in param_name.lower():
                self.current_param_match_index = check_index
                self._select_parameter_match(check_index)
                return check_index + 1, total_matches

        return 0, 0

    def find_previous_parameter(self, search_text: str) -> Tuple[int, int]:
        """
        Find previous parameter match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        total_matches = len([p for p, _ in self.parameter_matches if search_lower in p.lower()])
        if total_matches == 0:
            return 0, 0

        # Find previous match
        start_index = (self.current_param_match_index - 1) % len(self.parameter_matches)
        for i in range(len(self.parameter_matches)):
            check_index = (start_index - i) % len(self.parameter_matches)
            param_name, tree_item = self.parameter_matches[check_index]
            if search_lower in param_name.lower():
                self.current_param_match_index = check_index
                self._select_parameter_match(check_index)
                return check_index + 1, total_matches

        return 0, 0

    def find_first_table_cell(self, search_text: str) -> Tuple[int, int]:
        """
        Find first table cell match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        # Find first match
        for i, (row, col, cell_text) in enumerate(self.table_matches):
            if search_lower in cell_text:
                self.current_table_match_index = i
                self._select_table_match(i)
                total_matches = len([c for _, _, c in self.table_matches if search_lower in c])
                return i + 1, total_matches

        # No matches found
        return 0, 0

    def find_next_table_cell(self, search_text: str) -> Tuple[int, int]:
        """
        Find next table cell match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        total_matches = len([c for _, _, c in self.table_matches if search_lower in c])
        if total_matches == 0:
            return 0, 0

        # Find next match
        start_index = (self.current_table_match_index + 1) % len(self.table_matches)
        for i in range(len(self.table_matches)):
            check_index = (start_index + i) % len(self.table_matches)
            row, col, cell_text = self.table_matches[check_index]
            if search_lower in cell_text:
                self.current_table_match_index = check_index
                self._select_table_match(check_index)
                return check_index + 1, total_matches

        return 0, 0

    def find_previous_table_cell(self, search_text: str) -> Tuple[int, int]:
        """
        Find previous table cell match.

        Args:
            search_text: Text to search for

        Returns:
            Tuple of (current_match_index, total_matches)
        """
        search_lower = search_text.lower().strip()
        if not search_lower:
            return 0, 0

        total_matches = len([c for _, _, c in self.table_matches if search_lower in c])
        if total_matches == 0:
            return 0, 0

        # Find previous match
        start_index = (self.current_table_match_index - 1) % len(self.table_matches)
        for i in range(len(self.table_matches)):
            check_index = (start_index - i) % len(self.table_matches)
            row, col, cell_text = self.table_matches[check_index]
            if search_lower in cell_text:
                self.current_table_match_index = check_index
                self._select_table_match(check_index)
                return check_index + 1, total_matches

        return 0, 0

    def _select_parameter_match(self, match_index: int):
        """Select the parameter match in the tree"""
        if 0 <= match_index < len(self.parameter_matches):
            param_name, tree_item = self.parameter_matches[match_index]
            self.param_tree.setCurrentItem(tree_item)
            self.param_tree.scrollToItem(tree_item)
            # Expand parent categories to show the item
            parent = tree_item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

    def _select_table_match(self, match_index: int):
        """Select the table cell match"""
        if 0 <= match_index < len(self.table_matches):
            row, col, cell_text = self.table_matches[match_index]
            self.param_table.setCurrentCell(row, col)
            self.param_table.scrollToItem(self.param_table.item(row, col))
