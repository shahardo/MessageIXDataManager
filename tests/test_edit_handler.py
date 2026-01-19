"""
Tests for EditHandler class
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock

from src.ui.controllers.edit_handler import EditHandler
from src.core.data_models import ScenarioData, Parameter
from managers.commands import EditCellCommand, EditPivotCommand


class TestEditHandler:
    """Test cases for EditHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create mock scenario
        self.mock_scenario = Mock(spec=ScenarioData)
        self.mock_scenario.mark_modified = Mock()

        # Create mock parameter
        self.mock_parameter = Mock(spec=Parameter)
        self.mock_parameter.df = pd.DataFrame({
            'region': ['Region1', 'Region1'],
            'technology': ['Tech1', 'Tech2'],
            'year': [2020, 2020],
            'value': [100.0, 200.0]
        })
        self.mock_parameter.name = "test_parameter"

        # Mock scenario methods
        self.mock_scenario.get_parameter.return_value = self.mock_parameter

        # Create mock data display
        self.mock_data_display = Mock()
        self.mock_data_display.table_display_mode = "raw"
        self.mock_data_display._identify_columns.return_value = {
            'year_cols': ['year'],
            'pivot_cols': ['technology'],
            'value_col': 'value',
            'filter_cols': ['region']
        }

        # Create handler
        self.handler = EditHandler(
            lambda is_results: self.mock_scenario,
            self.mock_data_display
        )

    def test_initialization(self):
        """Test handler initialization"""
        assert self.handler.get_current_scenario is not None
        assert self.handler.data_display == self.mock_data_display

    def test_handle_cell_value_change_raw_mode(self):
        """Test handling cell value change in raw mode"""
        # Mock undo manager
        mock_undo_manager = Mock()
        mock_undo_manager.execute.return_value = True

        # Mock get_current_displayed_parameter
        self.handler._get_current_displayed_parameter = Mock(return_value="test_parameter")

        result = self.handler.handle_cell_value_change(
            mode="raw",
            row_or_year=0,
            col_or_tech="value",
            new_value="150.0",
            undo_manager=mock_undo_manager
        )

        assert result is True
        self.mock_scenario.mark_modified.assert_called_with("test_parameter")
        mock_undo_manager.execute.assert_called_once()

        # Verify the command was an EditCellCommand
        call_args = mock_undo_manager.execute.call_args[0][0]
        assert isinstance(call_args, EditCellCommand)

    def test_handle_cell_value_change_advanced_mode(self):
        """Test handling cell value change in advanced mode"""
        # Mock undo manager
        mock_undo_manager = Mock()
        mock_undo_manager.execute.return_value = True

        # Mock get_current_displayed_parameter
        self.handler._get_current_displayed_parameter = Mock(return_value="test_parameter")

        # Set advanced mode
        self.mock_data_display.table_display_mode = "advanced"

        result = self.handler.handle_cell_value_change(
            mode="advanced",
            row_or_year=2020,
            col_or_tech="Tech1",
            new_value="150.0",
            undo_manager=mock_undo_manager
        )

        assert result is True
        self.mock_scenario.mark_modified.assert_called_with("test_parameter")
        mock_undo_manager.execute.assert_called_once()

        # Verify the command was an EditPivotCommand
        call_args = mock_undo_manager.execute.call_args[0][0]
        assert isinstance(call_args, EditPivotCommand)

    def test_handle_cell_value_change_invalid_value(self):
        """Test handling cell value change with invalid value"""
        mock_undo_manager = Mock()
        self.handler._get_current_displayed_parameter = Mock(return_value="test_parameter")

        result = self.handler.handle_cell_value_change(
            mode="raw",
            row_or_year=0,
            col_or_tech="value",
            new_value="invalid_text",
            undo_manager=mock_undo_manager
        )

        assert result is False
        mock_undo_manager.execute.assert_not_called()

    def test_handle_cell_value_change_no_scenario(self):
        """Test handling cell value change when no scenario available"""
        # Override get_current_scenario to return None
        self.handler.get_current_scenario = Mock(return_value=None)

        mock_undo_manager = Mock()
        self.handler._get_current_displayed_parameter = Mock(return_value="test_parameter")

        result = self.handler.handle_cell_value_change(
            mode="raw",
            row_or_year=0,
            col_or_tech="value",
            new_value="150.0",
            undo_manager=mock_undo_manager
        )

        assert result is False
        mock_undo_manager.execute.assert_not_called()

    def test_handle_cell_value_change_no_parameter(self):
        """Test handling cell value change when no parameter found"""
        self.handler._get_current_displayed_parameter = Mock(return_value=None)

        mock_undo_manager = Mock()

        result = self.handler.handle_cell_value_change(
            mode="raw",
            row_or_year=0,
            col_or_tech="value",
            new_value="150.0",
            undo_manager=mock_undo_manager
        )

        assert result is False
        mock_undo_manager.execute.assert_not_called()

    def test_handle_raw_edit_valid(self):
        """Test raw edit with valid parameters"""
        df = pd.DataFrame({
            'value': [100.0, 200.0],
            'other_col': ['a', 'b']
        })

        result = self.handler._handle_raw_edit(df, 0, 'value', 150.0)

        assert result is not None
        assert result[0] == 100.0  # Old value
        assert df.loc[0, 'value'] == 150.0  # New value set

    def test_handle_raw_edit_invalid_row(self):
        """Test raw edit with invalid row index"""
        df = pd.DataFrame({'value': [100.0, 200.0]})

        result = self.handler._handle_raw_edit(df, 10, 'value', 150.0)

        assert result is None

    def test_handle_raw_edit_invalid_column(self):
        """Test raw edit with invalid column name"""
        df = pd.DataFrame({'value': [100.0, 200.0]})

        result = self.handler._handle_raw_edit(df, 0, 'nonexistent_col', 150.0)

        assert result is None

    def test_handle_advanced_edit_valid(self):
        """Test advanced edit with valid parameters"""
        # Create a more complex DataFrame for pivoting
        df = pd.DataFrame({
            'region': ['Region1', 'Region1'],
            'technology': ['Tech1', 'Tech2'],
            'year': [2020, 2020],
            'value': [100.0, 200.0]
        })

        result = self.handler._handle_advanced_edit(df, 2020, 'Tech1', 150.0)

        assert result is not None
        old_value, year_col, tech_col, value_col = result
        assert old_value == 100.0
        assert year_col == 'year'
        assert tech_col == 'technology'
        assert value_col == 'value'

        # Verify the value was updated
        mask = (df['year'] == 2020) & (df['technology'] == 'Tech1')
        assert df.loc[mask, 'value'].iloc[0] == 150.0

    def test_handle_advanced_edit_no_match(self):
        """Test advanced edit when no matching rows found"""
        df = pd.DataFrame({
            'region': ['Region1'],
            'technology': ['Tech1'],
            'year': [2020],
            'value': [100.0]
        })

        # Try to edit Tech2 in 2025 (doesn't exist)
        result = self.handler._handle_advanced_edit(df, 2025, 'Tech2', 150.0)

        assert result is None

    def test_handle_advanced_edit_missing_columns(self):
        """Test advanced edit when required columns are missing"""
        df = pd.DataFrame({
            'region': ['Region1'],
            'value': [100.0]
        })

        # Mock _identify_columns to return missing columns
        self.mock_data_display._identify_columns.return_value = {
            'year_cols': [],  # No year columns
            'pivot_cols': [],
            'value_col': 'value'
        }

        result = self.handler._handle_advanced_edit(df, 2020, 'Tech1', 150.0)

        assert result is None

    def test_sync_advanced_to_raw_data(self):
        """Test syncing advanced mode changes back to raw data"""
        # Create test DataFrame
        df = pd.DataFrame({
            'region': ['Region1'],
            'technology': ['Tech1'],
            'year': [2020],
            'value': [100.0]
        })

        # Mock table items
        mock_vertical_item = Mock()
        mock_vertical_item.text.return_value = "2020"

        mock_horizontal_item = Mock()
        mock_horizontal_item.text.return_value = "Tech1"

        self.mock_data_display.param_table.verticalHeaderItem.return_value = mock_vertical_item
        self.mock_data_display.param_table.horizontalHeaderItem.return_value = mock_horizontal_item

        result = self.handler.sync_advanced_to_raw_data(0, 0, 150.0, self.mock_scenario, "test_parameter")

        assert result is True
        # Verify value was updated
        assert self.mock_parameter.df.loc[0, 'value'] == 150.0

    def test_sync_advanced_to_raw_data_invalid_headers(self):
        """Test syncing when table headers return invalid data"""
        # Mock table items with invalid data
        mock_vertical_item = Mock()
        mock_vertical_item.text.return_value = "invalid_year"

        self.mock_data_display.param_table.verticalHeaderItem.return_value = mock_vertical_item

        result = self.handler.sync_advanced_to_raw_data(0, 0, 150.0, self.mock_scenario, "test_parameter")

        assert result is False

    def test_get_current_displayed_parameter_default(self):
        """Test default implementation of get_current_displayed_parameter"""
        result = self.handler._get_current_displayed_parameter()

        assert result is None

    def test_handle_cell_value_change_empty_value(self):
        """Test handling cell value change with empty string (should become 0)"""
        mock_undo_manager = Mock()
        mock_undo_manager.execute.return_value = True

        self.handler._get_current_displayed_parameter = Mock(return_value="test_parameter")

        result = self.handler.handle_cell_value_change(
            mode="raw",
            row_or_year=0,
            col_or_tech="value",
            new_value="",  # Empty string
            undo_manager=mock_undo_manager
        )

        assert result is True
        # Verify the command was created with 0.0 as the value
        call_args = mock_undo_manager.execute.call_args[0][0]
        assert call_args.new_value == 0.0
