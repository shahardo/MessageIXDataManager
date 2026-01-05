import pytest
from openpyxl import Workbook
import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from managers.input_manager import InputManager

@pytest.fixture
def temp_excel_file_1():
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb = Workbook()
        ws_params = wb.active
        ws_params.title = "parameters"
        ws_params['A1'] = 'parameter'
        ws_params['B1'] = 'value'
        ws_params['A2'] = 'param1'
        ws_params['B2'] = 10
        wb.save(tmp.name)
        yield tmp.name
    os.unlink(tmp.name)

@pytest.fixture
def temp_excel_file_2():
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        wb = Workbook()
        ws_params = wb.active
        ws_params.title = "parameters"
        ws_params['A1'] = 'parameter'
        ws_params['B1'] = 'value'
        ws_params['A2'] = 'param2'
        ws_params['B2'] = 20
        wb.save(tmp.name)
        yield tmp.name
    os.unlink(tmp.name)

def test_load_multiple_files_separately(temp_excel_file_1, temp_excel_file_2):
    manager = InputManager()

    # Load first file
    manager.load_excel_file(temp_excel_file_1)
    
    # Load second file
    manager.load_excel_file(temp_excel_file_2)

    # Check that there are two scenarios loaded
    assert manager.get_number_of_scenarios() == 2
    assert len(manager.get_loaded_file_paths()) == 2

    # Get the first scenario by index and check its data
    scenario1_by_index = manager.get_scenario_by_index(0)
    assert scenario1_by_index is not None
    assert 'param1' in scenario1_by_index.get_parameter_names()
    assert 'param2' not in scenario1_by_index.get_parameter_names()
    param1_from_index = scenario1_by_index.get_parameter('param1')
    assert len(param1_from_index.df) == 1
    assert param1_from_index.df['value'].iloc[0] == 10

    # Get the first scenario by path and check its data
    scenario1 = manager.get_scenario_by_file_path(temp_excel_file_1)
    assert scenario1 is not None
    assert 'param1' in scenario1.get_parameter_names()
    assert 'param2' not in scenario1.get_parameter_names()
    param1 = scenario1.get_parameter('param1')
    assert len(param1.df) == 1
    assert param1.df['value'].iloc[0] == 10

    # Get the second scenario and check its data
    scenario2 = manager.get_scenario_by_file_path(temp_excel_file_2)
    assert scenario2 is not None
    assert 'param2' in scenario2.get_parameter_names()
    assert 'param1' not in scenario2.get_parameter_names()
    param2 = scenario2.get_parameter('param2')
    assert len(param2.df) == 1
    assert param2.df['value'].iloc[0] == 20

    # Get the combined scenario and check its data
    combined_scenario = manager.get_current_scenario()
    assert combined_scenario is not None
    assert 'param1' in combined_scenario.get_parameter_names()
    assert 'param2' in combined_scenario.get_parameter_names()
    
    # Verify the original scenarios were not modified
    # Get the first scenario AGAIN and check its data
    scenario1_again = manager.get_scenario_by_file_path(temp_excel_file_1)
    param1_again = scenario1_again.get_parameter('param1')
    assert len(param1_again.df) == 1
    assert param1_again.df['value'].iloc[0] == 10

