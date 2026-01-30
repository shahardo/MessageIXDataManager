import pytest
import os
import sys
import pandas as pd
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from managers.input_manager import InputManager
from managers.results_analyzer import ResultsAnalyzer
from core.data_models import Scenario, ScenarioData

# Fixtures
@pytest.fixture
def input_manager():
    return InputManager()

@pytest.fixture
def results_analyzer():
    # Mock parent if needed, as MainWindow passes self
    return ResultsAnalyzer(main_window=MagicMock())

# Tests for InputManager
def test_input_manager_file_not_found(input_manager):
    """Test loading a non-existent input file"""
    with pytest.raises(FileNotFoundError):
        input_manager.load_excel_file("non_existent_file.xlsx")

def test_input_manager_invalid_extension(input_manager, tmp_path):
    """Test loading a file with invalid extension"""
    p = tmp_path / "test.txt"
    p.write_text("content", encoding='utf-8')
    # Assuming the manager checks extension or pandas fails
    with pytest.raises(Exception):
        input_manager.load_excel_file(str(p))

def test_input_manager_corrupted_file(input_manager, tmp_path):
    """Test loading a corrupted Excel file"""
    p = tmp_path / "corrupted.xlsx"
    p.write_text("not an excel file", encoding='utf-8')
    with pytest.raises(Exception): # likely zipfile.BadZipFile or ValueError
        input_manager.load_excel_file(str(p))

@patch('managers.base_data_manager.load_workbook')
def test_input_manager_success_mock(mock_load_workbook, input_manager):
    """Test successful loading with mocked openpyxl"""
    # Mock workbook
    mock_wb = MagicMock()
    mock_wb.sheetnames = ['parameters']
    
    # Mock sheet
    mock_sheet = MagicMock()
    mock_sheet.title = 'parameters'
    
    # Mock headers access (sheet[1])
    h1 = MagicMock(); h1.value = 'parameter'
    h2 = MagicMock(); h2.value = 'value'
    mock_sheet.__getitem__.return_value = [h1, h2]
    
    # Mock iter_rows
    def iter_rows_side_effect(**kwargs):
        if kwargs.get('min_row') == 2:
            yield ('test_param', 100)
        else:
            yield ('parameter', 'value')
            yield ('test_param', 100)
    mock_sheet.iter_rows.side_effect = iter_rows_side_effect
    
    mock_wb.__getitem__.return_value = mock_sheet
    mock_load_workbook.return_value = mock_wb
    
    # We need to mock os.path.exists to return True for our fake file
    with patch('os.path.exists', return_value=True):
        try:
            scenario = input_manager.load_excel_file("dummy.xlsx")
            # If it returns a Scenario, check it
            if scenario:
                assert isinstance(scenario, ScenarioData)
        except Exception as e:
            pytest.fail(f"InputManager raised exception with valid mock data: {e}")

# Tests for ResultsAnalyzer
def test_results_analyzer_file_not_found(results_analyzer):
    """Test loading a non-existent results file"""
    with pytest.raises(FileNotFoundError):
        results_analyzer.load_results_file("non_existent_results.xlsx")

def test_results_analyzer_corrupted_file(results_analyzer, tmp_path):
    """Test loading a corrupted results file"""
    p = tmp_path / "corrupted_results.xlsx"
    p.write_text("not an excel file", encoding='utf-8')
    with pytest.raises(Exception):
        results_analyzer.load_results_file(str(p))

@patch('managers.base_data_manager.load_workbook')
def test_results_analyzer_success_mock(mock_load_workbook, results_analyzer):
    """Test successful results loading with mocked openpyxl"""
    # Mock workbook
    mock_wb = MagicMock()
    mock_wb.sheetnames = ['var_ACT']
    
    # Mock sheet
    mock_sheet = MagicMock()
    mock_sheet.title = 'var_ACT'
    
    # Mock headers access (sheet[1])
    h1 = MagicMock(); h1.value = 'node'
    h2 = MagicMock(); h2.value = 'value'
    mock_sheet.__getitem__.return_value = [h1, h2]
    
    # Mock iter_rows
    def iter_rows_side_effect(**kwargs):
        if kwargs.get('min_row') == 2:
            yield ('node1', 100)
        else:
            yield ('node', 'value')
            yield ('node1', 100)
    mock_sheet.iter_rows.side_effect = iter_rows_side_effect
    
    mock_wb.__getitem__.return_value = mock_sheet
    mock_load_workbook.return_value = mock_wb
    
    with patch('os.path.exists', return_value=True):
        try:
            scenario = results_analyzer.load_results_file("dummy_results.xlsx")
            if scenario:
                assert isinstance(scenario, ScenarioData)
        except Exception as e:
            pytest.fail(f"ResultsAnalyzer raised exception with valid mock data: {e}")

# Integration tests (skipped if files don't exist)
def test_integration_load_input_file(input_manager):
    """Integration test with real file if available"""
    file_path = "files/Solar Scenario Data.xlsx"
    if not os.path.exists(file_path):
        pytest.skip(f"Integration test file not found: {file_path}")
    
    scenario = input_manager.load_excel_file(file_path)
    assert isinstance(scenario, ScenarioData)
    assert len(scenario.get_parameter_names()) > 0

def test_integration_load_results_file(results_analyzer):
    """Integration test with real file if available"""
    file_path = "files/Results_Solar.xlsx"
    if not os.path.exists(file_path):
        pytest.skip(f"Integration test file not found: {file_path}")
    
    scenario = results_analyzer.load_results_file(file_path)
    assert isinstance(scenario, ScenarioData)