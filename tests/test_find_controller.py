"""
Tests for FindController class
"""

import pytest
from unittest.mock import Mock, MagicMock
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem

from ui.controllers.find_controller import FindController
from core.data_models import ScenarioData, Parameter


class TestFindController:
    """Test cases for FindController class"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create real Qt widgets
        self.param_tree = QTreeWidget()
        self.param_table = QTableWidget()

        # Create controller
        self.controller = FindController(self.param_tree, self.param_table)

        # Create mock scenario with parameters
        self.mock_scenario = Mock(spec=ScenarioData)
        self.mock_param1 = Mock(spec=Parameter)
        self.mock_param1.name = "parameter1"
        self.mock_param2 = Mock(spec=Parameter)
        self.mock_param2.name = "test_parameter"
        self.mock_param3 = Mock(spec=Parameter)
        self.mock_param3.name = "another_param"

        # Create real tree items
        self.item1 = QTreeWidgetItem()
        self.item1.setText(0, "parameter1")
        self.item2 = QTreeWidgetItem()
        self.item2.setText(0, "test_parameter")
        self.item3 = QTreeWidgetItem()
        self.item3.setText(0, "another_param")

        # Create root item with children
        self.root = QTreeWidgetItem()
        self.root.addChild(self.item1)
        self.root.addChild(self.item2)
        self.root.addChild(self.item3)

        # Add root to tree
        self.param_tree.addTopLevelItem(self.root)

    def test_initialization(self):
        """Test controller initialization"""
        assert self.controller.param_tree == self.param_tree
        assert self.controller.param_table == self.param_table
        assert self.controller.parameter_matches == []
        assert self.controller.current_param_match_index == -1
        assert self.controller.table_matches == []
        assert self.controller.current_table_match_index == -1

    def test_initialize_parameter_search_with_scenario(self):
        """Test initializing parameter search with a scenario"""
        result = self.controller.initialize_parameter_search(self.mock_scenario)

        assert result is True
        assert len(self.controller.parameter_matches) == 3
        assert self.controller.current_param_match_index == -1

        # Check that parameter matches were collected
        param_names = [name for name, _ in self.controller.parameter_matches]
        assert "parameter1" in param_names
        assert "test_parameter" in param_names
        assert "another_param" in param_names

    def test_initialize_parameter_search_no_scenario(self):
        """Test initializing parameter search with no scenario"""
        result = self.controller.initialize_parameter_search(None)

        assert result is False
        assert self.controller.parameter_matches == []
        assert self.controller.current_param_match_index == -1

    def test_initialize_table_search(self):
        """Test initializing table search"""
        # Set table dimensions and items
        self.param_table.setRowCount(2)
        self.param_table.setColumnCount(2)

        # Create table items with text
        item1 = QTableWidgetItem("value1")
        item2 = QTableWidgetItem("value2")
        item3 = QTableWidgetItem("")  # Empty cell
        item4 = QTableWidgetItem("value4")

        self.param_table.setItem(0, 0, item1)
        self.param_table.setItem(0, 1, item2)
        self.param_table.setItem(1, 0, item3)
        self.param_table.setItem(1, 1, item4)

        result = self.controller.initialize_table_search()

        assert result is True
        assert len(self.controller.table_matches) == 3  # Empty cell excluded
        assert self.controller.current_table_match_index == -1

    def test_find_first_parameter_match(self):
        """Test finding first parameter match"""
        # Set up parameter matches
        self.controller.parameter_matches = [
            ("parameter1", self.item1),
            ("test_parameter", self.item2),
            ("another_param", self.item3)
        ]

        current_match, total_matches = self.controller.find_first_parameter("test")

        assert current_match == 2  # Second item (1-indexed)
        assert total_matches == 1  # Only one match for "test"
        assert self.controller.current_param_match_index == 1

        # Verify tree selection
        assert self.param_tree.currentItem() == self.item2

    def test_find_first_parameter_no_match(self):
        """Test finding first parameter when no matches exist"""
        self.controller.parameter_matches = [
            ("parameter1", self.item1),
            ("another_param", self.item3)
        ]

        current_match, total_matches = self.controller.find_first_parameter("nonexistent")

        assert current_match == 0
        assert total_matches == 0
        assert self.controller.current_param_match_index == -1

    def test_find_next_parameter(self):
        """Test finding next parameter match"""
        self.controller.parameter_matches = [
            ("parameter1", self.item1),
            ("test_parameter", self.item2),
            ("test_param2", self.item3)
        ]
        self.controller.current_param_match_index = 1  # Currently on second item

        current_match, total_matches = self.controller.find_next_parameter("test")

        assert current_match == 3  # Third item (1-indexed)
        assert total_matches == 2  # Two matches for "test"
        assert self.controller.current_param_match_index == 2

    def test_find_next_parameter_wrap_around(self):
        """Test finding next parameter with wrap-around"""
        self.controller.parameter_matches = [
            ("test_param", self.item1),
            ("parameter2", self.item2),
            ("test_param2", self.item3)
        ]
        self.controller.current_param_match_index = 2  # Currently on last item

        current_match, total_matches = self.controller.find_next_parameter("test")

        assert current_match == 1  # First item (wrapped around)
        assert total_matches == 2
        assert self.controller.current_param_match_index == 0

    def test_find_previous_parameter(self):
        """Test finding previous parameter match"""
        self.controller.parameter_matches = [
            ("test_param", self.item1),
            ("parameter2", self.item2),
            ("test_param2", self.item3)
        ]
        self.controller.current_param_match_index = 2  # Currently on last item

        current_match, total_matches = self.controller.find_previous_parameter("test")

        assert current_match == 1  # First item (1-indexed)
        assert total_matches == 2
        assert self.controller.current_param_match_index == 0

    def test_find_first_table_cell(self):
        """Test finding first table cell match"""
        # Set up table with items
        self.param_table.setRowCount(2)
        self.param_table.setColumnCount(2)
        self.param_table.setItem(0, 0, QTableWidgetItem("apple"))
        self.param_table.setItem(0, 1, QTableWidgetItem("banana"))
        self.param_table.setItem(1, 0, QTableWidgetItem("grape"))
        self.param_table.setItem(1, 1, QTableWidgetItem("apple pie"))

        # Initialize search
        self.controller.initialize_table_search()

        current_match, total_matches = self.controller.find_first_table_cell("apple")

        assert current_match == 1  # First match (1-indexed)
        assert total_matches == 2  # Two cells contain "apple"
        assert self.controller.current_table_match_index == 0

        # Verify table selection
        assert self.param_table.currentRow() == 0
        assert self.param_table.currentColumn() == 0

    def test_find_next_table_cell(self):
        """Test finding next table cell match"""
        self.controller.table_matches = [
            (0, 0, "apple"),
            (0, 1, "banana"),
            (1, 0, "apple pie"),
            (1, 1, "grape")
        ]
        self.controller.current_table_match_index = 0  # Currently on first "apple"

        current_match, total_matches = self.controller.find_next_table_cell("apple")

        assert current_match == 3  # Third item (apple pie)
        assert total_matches == 2
        assert self.controller.current_table_match_index == 2

    def test_find_previous_table_cell(self):
        """Test finding previous table cell match"""
        self.controller.table_matches = [
            (0, 0, "apple"),
            (0, 1, "banana"),
            (1, 0, "apple pie"),
            (1, 1, "grape")
        ]
        self.controller.current_table_match_index = 2  # Currently on "apple pie"

        current_match, total_matches = self.controller.find_previous_table_cell("apple")

        assert current_match == 1  # First "apple" (1-indexed)
        assert total_matches == 2
        assert self.controller.current_table_match_index == 0

    def test_select_parameter_match_expands_tree(self):
        """Test that selecting a parameter match expands parent tree items"""
        # Create a nested structure
        parent = QTreeWidgetItem()
        parent.setText(0, "Parent")
        child = QTreeWidgetItem(parent)
        child.setText(0, "test_parameter")

        self.param_tree.addTopLevelItem(parent)

        # Set up parameter matches
        self.controller.parameter_matches = [
            ("parameter1", self.item1),
            ("test_parameter", child)
        ]

        # Call private method
        self.controller._select_parameter_match(1)

        # Verify tree expansion
        assert parent.isExpanded() == True

    def test_select_table_match(self):
        """Test selecting table cell match"""
        # Set up table
        self.param_table.setRowCount(3)
        self.param_table.setColumnCount(4)
        self.param_table.setItem(2, 3, QTableWidgetItem("test_value"))

        self.controller.table_matches = [
            (2, 3, "test_value")
        ]

        self.controller._select_table_match(0)

        # Verify table selection
        assert self.param_table.currentRow() == 2
        assert self.param_table.currentColumn() == 3
