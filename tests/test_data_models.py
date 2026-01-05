"""
Tests for core data models
"""

import pytest
import pandas as pd
import os
import sys
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import Parameter, ScenarioData


class TestParameter:
    """Test cases for Parameter class"""

    def test_parameter_creation(self):
        """Test basic parameter creation"""
        df = pd.DataFrame({
            'dim1': [1, 2],
            'dim2': ['a', 'b'],
            'value': [10.0, 20.0]
        })
        metadata = {
            'units': 'MW',
            'desc': 'Test parameter',
            'dims': ['dim1', 'dim2']
        }
        param = Parameter('test_param', df, metadata)

        assert param.name == 'test_param'
        assert len(param.df) == 2
        assert param.metadata['units'] == 'MW'
        assert param.metadata['dims'] == ['dim1', 'dim2']

    def test_parameter_with_metadata(self):
        """Test parameter with various metadata"""
        df = pd.DataFrame({'value': [100]})
        metadata = {
            'units': 'USD',
            'desc': 'Cost parameter',
            'dims': [],
            'value_column': 'value',
            'shape': (1, 1)
        }
        param = Parameter('cost', df, metadata)

        assert param.metadata['units'] == 'USD'
        assert param.metadata['desc'] == 'Cost parameter'


class TestScenarioData:
    """Test cases for ScenarioData class"""

    def test_scenario_initialization(self):
        """Test scenario initialization"""
        scenario = ScenarioData()

        assert len(scenario.parameters) == 0
        assert len(scenario.sets) == 0
        assert len(scenario.modified) == 0
        assert len(scenario.change_history) == 0
        assert len(scenario.mappings) == 0

    def test_add_and_get_parameter(self):
        """Test adding and retrieving parameters"""
        scenario = ScenarioData()
        df = pd.DataFrame({'value': [1, 2, 3]})
        param = Parameter('test_param', df, {'desc': 'Test'})

        scenario.add_parameter(param)

        assert len(scenario.parameters) == 1
        assert scenario.get_parameter('test_param') is param
        assert scenario.get_parameter('nonexistent') is None

    def test_get_parameter_names(self):
        """Test getting parameter names"""
        scenario = ScenarioData()

        # Empty scenario
        assert scenario.get_parameter_names() == []

        # Add parameters
        scenario.add_parameter(Parameter('param1', pd.DataFrame(), {}))
        scenario.add_parameter(Parameter('param2', pd.DataFrame(), {}))

        names = scenario.get_parameter_names()
        assert len(names) == 2
        assert 'param1' in names
        assert 'param2' in names

    def test_mark_modified(self):
        """Test marking parameters as modified"""
        scenario = ScenarioData()
        df = pd.DataFrame({'value': [1]})
        param = Parameter('test', df, {})
        scenario.add_parameter(param)

        # Initially not modified
        assert len(scenario.modified) == 0
        assert len(scenario.change_history) == 0

        # Mark as modified
        scenario.mark_modified('test')

        assert 'test' in scenario.modified
        assert len(scenario.change_history) == 1

        # Check change history
        change = scenario.change_history[0]
        assert change['action'] == 'modify'
        assert change['parameter'] == 'test'
        assert isinstance(change['timestamp'], pd.Timestamp)

    def test_mark_modified_nonexistent_parameter(self):
        """Test marking nonexistent parameter as modified"""
        scenario = ScenarioData()

        # Should track the modification attempt even for nonexistent parameters
        scenario.mark_modified('nonexistent')

        assert len(scenario.modified) == 1
        assert 'nonexistent' in scenario.modified
        assert len(scenario.change_history) == 1
        assert scenario.change_history[0]['parameter'] == 'nonexistent'

    def test_scenario_with_sets(self):
        """Test scenario with sets"""
        scenario = ScenarioData()

        # Add a set
        scenario.sets['technology'] = pd.Series(['coal', 'solar', 'wind'])
        scenario.sets['region'] = pd.Series(['north', 'south'])

        assert len(scenario.sets) == 2
        assert 'technology' in scenario.sets
        assert len(scenario.sets['technology']) == 3

    def test_scenario_with_mappings(self):
        """Test scenario with mappings"""
        scenario = ScenarioData()

        # Add a mapping
        mapping_df = pd.DataFrame({
            'input': ['coal', 'solar'],
            'output': ['electricity', 'electricity']
        })
        scenario.mappings['input_output'] = mapping_df

        assert len(scenario.mappings) == 1
        assert 'input_output' in scenario.mappings

    def test_multiple_parameters(self):
        """Test scenario with multiple parameters"""
        scenario = ScenarioData()

        # Add multiple parameters
        for i in range(3):
            df = pd.DataFrame({'value': [i]})
            param = Parameter(f'param_{i}', df, {'index': i})
            scenario.add_parameter(param)

        assert len(scenario.parameters) == 3
        names = scenario.get_parameter_names()
        assert len(names) == 3
        assert all(name.startswith('param_') for name in names)
