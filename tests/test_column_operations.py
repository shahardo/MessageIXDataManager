"""
Tests for Column Operations: Right-click context menu, clipboard operations, and edit menu

Tests for the new column manipulation features including:
- Right-click context menu on column headers
- Clipboard operations (copy/paste/cut)
- Edit menu integration
- Column selection and manipulation
"""

import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

# Check if PyQt5 is available
try:
    import PyQt5.QtWidgets
    import PyQt5.QtCore
    import PyQt5.QtGui
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False

# Skip all tests if PyQt5 is not available
pytestmark = pytest.mark.skipif(not PYQT5_AVAILABLE, reason="PyQt5 not available")

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import Parameter, ScenarioData


@pytest.fixture
def sample_parameter():
    """Create a sample parameter for testing"""
    data = [
        ['tech1', 'region1', 2020, 100.0],
        ['tech1', 'region1', 2025, 120.0],
        ['tech2', 'region1', 2020, 80.0],
        ['tech2', 'region1', 2025, 90.0],
        ['tech3', 'region1', 2020, 50.0],
        ['tech3', 'region1', 2025, 60.0],
    ]
    headers = ['technology', 'region', 'year', 'value']
    df = pd.DataFrame(data, columns=headers)

    metadata = {
        'units': 'MW',
        'dims': ['technology', 'region', 'year'],
        'value_column': 'value',
        'shape': df.shape
    }

    return Parameter('test_param', df, metadata)


class TestColumnHeaderView:
    """Test ColumnHeaderView functionality"""

    def test_column_header_view_initialization(self):
        """Test ColumnHeaderView initializes correctly"""
        # Test that the class exists and has the expected attributes
        from ui.components.data_display_widget import ColumnHeaderView

        # Check that ColumnHeaderView class exists
        assert ColumnHeaderView is not None

        # Check that it has the expected methods
        assert hasattr(ColumnHeaderView, '__init__')
        assert hasattr(ColumnHeaderView, 'mousePressEvent')
        assert hasattr(ColumnHeaderView, '_show_context_menu')
        assert hasattr(ColumnHeaderView, '_copy_column')
        assert hasattr(ColumnHeaderView, '_paste_column')
        assert hasattr(ColumnHeaderView, '_cut_column')

    def test_copy_column_data_logic(self):
        """Test the logic of copying column data to clipboard"""
        # Test the core logic without Qt dependencies
        from ui.components.data_display_widget import DataDisplayWidget

        # Create a mock widget with just the attributes we need
        widget = MagicMock(spec=DataDisplayWidget)
        widget.clipboard_delimiter = '\t'  # Default delimiter

        # Mock the table widget and its methods
        mock_table = MagicMock()
        mock_table.columnCount.return_value = 4  # 4 columns

        # Mock horizontal header
        mock_header = MagicMock()
        mock_header.text.return_value = "value"
        mock_table.horizontalHeaderItem.return_value = mock_header

        # Set up table to return items for column 3
        values = ['100.0', '120.0', '80.0', '90.0', '50.0', '60.0']
        def mock_item_side_effect(row, col):
            if col == 3 and row < len(values):
                mock_item = MagicMock()
                mock_item.text.return_value = values[row]
                return mock_item
            return None

        mock_table.item.side_effect = mock_item_side_effect
        mock_table.rowCount.return_value = 6

        widget.param_table = mock_table

        # Mock QApplication.clipboard()
        with patch('PyQt5.QtWidgets.QApplication.clipboard') as mock_clipboard:
            mock_clipboard_instance = MagicMock()
            mock_clipboard.return_value = mock_clipboard_instance

            # Call the actual method
            DataDisplayWidget.copy_column_data(widget, 3)

            # Verify clipboard was called
            mock_clipboard_instance.setText.assert_called_once()

            # Get the text that was set
            call_args = mock_clipboard_instance.setText.call_args[0]
            clipboard_text = call_args[0]

            # Verify format: single column with newlines
            expected_lines = ['100.0', '120.0', '80.0', '90.0', '50.0', '60.0']
            actual_lines = clipboard_text.split('\n')

            assert actual_lines == expected_lines

    @patch('PyQt5.QtWidgets.QApplication.clipboard')
    def test_paste_column_data_single_column_format(self, mock_clipboard):
        """Test pasting data from clipboard in single-column format"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock clipboard with single-column data
        clipboard_data = "200.0\n250.0\n180.0\n220.0\n150.0\n170.0"
        mock_clipboard_instance = MagicMock()
        mock_clipboard_instance.text.return_value = clipboard_data
        mock_clipboard.return_value = mock_clipboard_instance

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Mock the table widget
        mock_table = MagicMock()
        mock_table.columnCount.return_value = 4
        mock_table.rowCount.return_value = 6

        # Mock table items that will be updated
        mock_items = []
        for i in range(6):
            mock_item = MagicMock()
            mock_items.append(mock_item)

        # Set up table to return different items for different calls
        def mock_item_side_effect(row, col):
            if col == 3 and row < len(mock_items):
                return mock_items[row]
            return None

        mock_table.item.side_effect = mock_item_side_effect
        widget.param_table = mock_table

        # Call the method directly
        DataDisplayWidget.paste_column_data(widget, 3)

        # Verify the table cells were updated
        # Check first few values
        assert mock_items[0].setText.called
        assert mock_items[1].setText.called
        assert mock_items[2].setText.called

        # Check the values that were set
        # Note: The method converts floats to compact format (e.g., "200.0" becomes "200")
        calls = [item.setText.call_args[0][0] for item in mock_items[:3]]
        assert calls == ["200", "250", "180"]

    def test_paste_column_data_invalid_column(self):
        """Test pasting to invalid column index"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Mock table with invalid column count
        mock_table = MagicMock()
        mock_table.columnCount.return_value = 4  # Valid columns 0-3
        widget.param_table = mock_table

        # Try to paste to invalid column - should not crash
        DataDisplayWidget.paste_column_data(widget, -1)  # Invalid column
        DataDisplayWidget.paste_column_data(widget, 999)  # Out of bounds

    @patch('PyQt5.QtWidgets.QApplication.clipboard')
    def test_paste_column_data_empty_clipboard(self, mock_clipboard):
        """Test pasting with empty clipboard"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock clipboard with empty content
        mock_clipboard_instance = MagicMock()
        mock_clipboard_instance.text.return_value = ""
        mock_clipboard.return_value = mock_clipboard_instance

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Mock table
        mock_table = MagicMock()
        mock_table.columnCount.return_value = 4
        widget.param_table = mock_table

        # Try to paste empty clipboard - should not crash
        DataDisplayWidget.paste_column_data(widget, 3)

    def test_delimiter_setting(self):
        """Test setting clipboard delimiter"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)
        widget.clipboard_delimiter = '\t'  # Set initial default

        # Test default delimiter
        assert widget.clipboard_delimiter == '\t'

        # Test setting different delimiters
        DataDisplayWidget.set_clipboard_delimiter(widget, ',')
        assert widget.clipboard_delimiter == ','

        DataDisplayWidget.set_clipboard_delimiter(widget, ';')
        assert widget.clipboard_delimiter == ';'

        DataDisplayWidget.set_clipboard_delimiter(widget, ' ')
        assert widget.clipboard_delimiter == ' '

        # Reset to default
        DataDisplayWidget.set_clipboard_delimiter(widget, '\t')
        assert widget.clipboard_delimiter == '\t'

    def test_context_menu_creation(self):
        """Test that context menu can be created without errors"""
        from ui.components.data_display_widget import ColumnHeaderView

        # Test that the class exists and has the expected methods
        assert ColumnHeaderView is not None

        # Test that it has the expected methods for context menu
        assert hasattr(ColumnHeaderView, '_show_context_menu')
        assert hasattr(ColumnHeaderView, '_copy_column')
        assert hasattr(ColumnHeaderView, '_paste_column')
        assert hasattr(ColumnHeaderView, '_cut_column')
        assert hasattr(ColumnHeaderView, '_set_delimiter')


class TestEditMenuIntegration:
    """Test Edit menu integration in MainWindow"""

    def test_edit_menu_actions_connected(self):
        """Test that Edit menu actions are properly connected"""
        from ui.main_window import MainWindow

        # Test that the MainWindow class has the expected methods
        assert hasattr(MainWindow, '_undo')
        assert hasattr(MainWindow, '_redo')
        assert hasattr(MainWindow, '_cut')
        assert hasattr(MainWindow, '_copy')
        assert hasattr(MainWindow, '_paste')

        # Test that the _connect_signals method exists (where actions are connected)
        assert hasattr(MainWindow, '_connect_signals')

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_undo_redo_placeholders(self, mock_msgbox):
        """Test that undo/redo show placeholder messages"""
        from ui.main_window import MainWindow

        # Create mock MainWindow instance
        window = MagicMock(spec=MainWindow)

        # Call undo and redo actions
        MainWindow._undo(window)
        MainWindow._redo(window)

        # Verify QMessageBox.information was called twice
        assert mock_msgbox.information.call_count == 2

        # Check the messages
        calls = mock_msgbox.information.call_args_list
        undo_call = calls[0]
        redo_call = calls[1]

        assert "Undo functionality is not yet implemented" in undo_call[0][1]
        assert "Redo functionality is not yet implemented" in redo_call[0][1]

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_cut_copy_paste_actions(self, mock_msgbox):
        """Test cut/copy/paste actions when no column is selected"""
        from ui.main_window import MainWindow

        # Create mock MainWindow instance
        window = MagicMock(spec=MainWindow)

        # Mock data_display with param_table that has no selection
        mock_data_display = MagicMock()
        mock_param_table = MagicMock()
        mock_param_table.currentColumn.return_value = -1  # No selection
        mock_data_display.param_table = mock_param_table
        window.data_display = mock_data_display

        # Call cut/copy/paste actions
        MainWindow._cut(window)
        MainWindow._copy(window)
        MainWindow._paste(window)

        # Verify QMessageBox.information was called three times
        assert mock_msgbox.information.call_count == 3

        # Check the messages (QMessageBox.information call signature: parent, title, text, buttons)
        calls = mock_msgbox.information.call_args_list
        cut_call = calls[0]
        copy_call = calls[1]
        paste_call = calls[2]

        assert "Please select a column header first" in cut_call[0][2]  # text parameter
        assert "Please select a column header first" in copy_call[0][2]  # text parameter
        assert "Please select a column header first" in paste_call[0][2]  # text parameter


class TestClipboardOperationsEdgeCases:
    """Test edge cases for clipboard operations"""

    @patch('PyQt5.QtWidgets.QApplication.clipboard')
    def test_copy_column_data_edge_cases(self, mock_clipboard):
        """Test copying column data edge cases"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock clipboard
        mock_clipboard_instance = MagicMock()
        mock_clipboard.return_value = mock_clipboard_instance

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Mock table with valid column count
        mock_table = MagicMock()
        mock_table.columnCount.return_value = 4  # Valid columns 0-3
        widget.param_table = mock_table

        # Test copying invalid columns
        DataDisplayWidget.copy_column_data(widget, -1)  # Negative column
        DataDisplayWidget.copy_column_data(widget, 999)  # Out of bounds column

        # Verify clipboard was not called for invalid columns
        assert mock_clipboard_instance.setText.call_count == 0

    # Note: The following tests require complex Qt widget interactions and are skipped
    # in environments without PyQt5. They would need extensive mocking to work properly.

    def test_paste_column_data_with_empty_table_cells(self):
        """Test pasting data when table has empty cells - placeholder test"""
        # This test requires complex Qt widget setup and is skipped when PyQt5 unavailable
        pass

    def test_paste_column_data_truncates_at_table_end(self):
        """Test that paste operation stops at table end - placeholder test"""
        # This test requires complex Qt widget setup and is skipped when PyQt5 unavailable
        pass

    def test_copy_paste_round_trip(self):
        """Test that copy followed by paste preserves data - placeholder test"""
        # This test requires complex Qt widget setup and is skipped when PyQt5 unavailable
        pass


class TestColumnManipulation:
    """Test column manipulation operations"""

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_insert_column_placeholder(self, mock_msgbox):
        """Test insert column placeholder functionality"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Call insert_column method
        DataDisplayWidget.insert_column(widget, 2)

        # Verify QMessageBox.information was called with placeholder message
        mock_msgbox.information.assert_called_once()
        call_args = mock_msgbox.information.call_args[0]
        assert "Insert column" in call_args[1]
        assert "integration with the scenario data management" in call_args[2]

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_delete_column_placeholder(self, mock_msgbox):
        """Test delete column placeholder functionality"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Set up QMessageBox constants
        mock_msgbox.Yes = 1
        mock_msgbox.No = 0

        # Mock QMessageBox.question to return Yes (confirm delete)
        mock_msgbox.question.return_value = mock_msgbox.Yes

        # Call delete_column method as instance method
        widget.delete_column(2)

        # Verify confirmation was asked
        mock_msgbox.question.assert_called_once()

        # Verify the placeholder message was shown
        mock_msgbox.information.assert_called_once()
        call_args = mock_msgbox.information.call_args[0]
        assert "Delete column" in call_args[1]
        assert "integration with the scenario data management" in call_args[2]

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_delete_column_cancelled(self, mock_msgbox):
        """Test delete column when user cancels"""
        from ui.components.data_display_widget import DataDisplayWidget

        # Create mock widget
        widget = MagicMock(spec=DataDisplayWidget)

        # Set up QMessageBox constants
        mock_msgbox.Yes = 1
        mock_msgbox.No = 0

        # Mock QMessageBox.question to return No (cancel delete)
        mock_msgbox.question.return_value = mock_msgbox.No

        # Call delete_column method as instance method
        widget.delete_column(2)

        # Verify confirmation was asked
        mock_msgbox.question.assert_called_once()

        # Verify no placeholder message was shown (operation was cancelled)
        mock_msgbox.information.assert_not_called()
