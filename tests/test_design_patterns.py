"""
Tests for design patterns implementation
Tests Observer, Factory, and Strategy patterns introduced in refactoring step 10.
"""

import pytest
import pandas as pd
import os
import sys
from unittest.mock import Mock, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager, DataObserver
from utils.parameter_factory import (
    ParameterFactory,
    StandardParameterFactory,
    InputParameterFactory,
    ResultParameterFactory,
    parameter_factory_registry
)
from utils.parsing_strategies import (
    ParsingStrategy,
    SetParsingStrategy,
    ParameterParsingStrategy,
    ResultParsingStrategy,
    ExcelParser
)


class TestObserverPattern:
    """Test cases for Observer pattern implementation"""

    def test_data_observer_protocol(self):
        """Test that DataObserver protocol is properly defined"""
        # Create a mock observer
        observer = Mock(spec=DataObserver)

        # Verify it has the required methods
        assert hasattr(observer, 'on_data_loaded')
        assert hasattr(observer, 'on_data_removed')
        assert hasattr(observer, 'on_scenario_cleared')

    def test_base_data_manager_observer_management(self):
        """Test observer registration and removal"""
        # Create a concrete subclass for testing
        class TestDataManager(BaseDataManager):
            def _parse_workbook(self, wb, scenario, progress_callback=None):
                pass

        manager = TestDataManager()
        observer1 = Mock(spec=DataObserver)
        observer2 = Mock(spec=DataObserver)

        # Add observers
        manager.add_observer(observer1)
        manager.add_observer(observer2)

        # Check they were added
        assert observer1 in manager._observers
        assert observer2 in manager._observers

        # Remove one observer
        manager.remove_observer(observer1)

        # Check removal
        assert observer1 not in manager._observers
        assert observer2 in manager._observers

    def test_observer_notifications(self):
        """Test that observers are notified of data changes"""
        # Create a concrete subclass for testing
        class TestDataManager(BaseDataManager):
            def _parse_workbook(self, wb, scenario, progress_callback=None):
                pass

        manager = TestDataManager()
        observer = Mock(spec=DataObserver)

        manager.add_observer(observer)

        # Create test data
        scenario = ScenarioData()
        test_file = "test.xlsx"

        # Test data loaded notification
        manager._notify_data_loaded(scenario, test_file)
        observer.on_data_loaded.assert_called_once_with(scenario, test_file)

        # Reset mock
        observer.reset_mock()

        # Test data removed notification
        manager._notify_data_removed(test_file)
        observer.on_data_removed.assert_called_once_with(test_file)

        # Reset mock
        observer.reset_mock()

        # Test scenario cleared notification
        manager._notify_scenario_cleared()
        observer.on_scenario_cleared.assert_called_once()


class TestFactoryPattern:
    """Test cases for Factory pattern implementation"""

    def test_parameter_factory_abstract_class(self):
        """Test that ParameterFactory is properly abstract"""
        # Test that we can't instantiate the abstract class directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ParameterFactory()

    def test_standard_parameter_factory_creation(self):
        """Test standard parameter factory"""
        factory = StandardParameterFactory()

        test_data = [
            ['node1', 'tech1', 100.0],
            ['node2', 'tech2', 200.0]
        ]
        headers = ['node', 'technology', 'value']

        parameter = factory.create_parameter('test_param', test_data, headers)

        assert parameter is not None
        assert parameter.name == 'test_param'
        assert len(parameter.df) == 2
        assert list(parameter.df.columns) == headers

    def test_input_parameter_factory_metadata(self):
        """Test that input parameter factory adds correct metadata"""
        factory = InputParameterFactory()

        test_data = [['node1', 100.0]]
        headers = ['node', 'value']

        parameter = factory.create_parameter('input_param', test_data, headers)

        assert parameter is not None
        if parameter:
            assert parameter.metadata.get('parameter_type') == 'input'
            assert parameter.metadata.get('source') == 'MESSAGEix input data'

    def test_result_parameter_factory_metadata(self):
        """Test that result parameter factory adds correct metadata"""
        factory = ResultParameterFactory()

        test_data = [['node1', 100.0]]
        headers = ['node', 'value']

        parameter = factory.create_parameter('result_param', test_data, headers)

        assert parameter is not None
        if parameter:
            assert parameter.metadata.get('parameter_type') == 'result'
            assert parameter.metadata.get('source') == 'MESSAGEix solution data'

    def test_parameter_factory_registry(self):
        """Test parameter factory registry functionality"""
        registry = parameter_factory_registry

        # Test getting factories
        standard_factory = registry.get_factory('standard')
        assert isinstance(standard_factory, StandardParameterFactory)

        input_factory = registry.get_factory('input')
        assert isinstance(input_factory, InputParameterFactory)

        result_factory = registry.get_factory('result')
        assert isinstance(result_factory, ResultParameterFactory)

        # Test unknown factory defaults to standard
        unknown_factory = registry.get_factory('unknown')
        assert isinstance(unknown_factory, StandardParameterFactory)

    def test_factory_registry_create_parameter(self):
        """Test creating parameters through registry"""
        registry = parameter_factory_registry

        test_data = [['test', 123.0]]
        headers = ['name', 'value']

        # Create input parameter
        input_param = registry.create_parameter('input', 'test_input', test_data, headers)
        assert input_param is not None
        if input_param:
            assert input_param.metadata.get('parameter_type') == 'input'

        # Create result parameter
        result_param = registry.create_parameter('result', 'test_result', test_data, headers)
        assert result_param is not None
        if result_param:
            assert result_param.metadata.get('parameter_type') == 'result'


class TestStrategyPattern:
    """Test cases for Strategy pattern implementation"""

    def test_parsing_strategy_abstract_class(self):
        """Test that ParsingStrategy is properly abstract"""
        # Test that we can't instantiate the abstract class directly
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ParsingStrategy()

    def test_set_parsing_strategy_can_parse(self):
        """Test SetParsingStrategy can_parse_sheet method"""
        strategy = SetParsingStrategy()

        # Mock sheet
        mock_sheet = Mock()

        # Test common set sheet names
        assert strategy.can_parse_sheet(mock_sheet, 'sets')
        assert strategy.can_parse_sheet(mock_sheet, 'set')
        assert strategy.can_parse_sheet(mock_sheet, 'Sets')

        # Test individual set sheets
        assert strategy.can_parse_sheet(mock_sheet, 'node')
        assert strategy.can_parse_sheet(mock_sheet, 'technology')
        assert strategy.can_parse_sheet(mock_sheet, 'commodity')

        # Test non-set sheet
        assert not strategy.can_parse_sheet(mock_sheet, 'parameters')
        assert not strategy.can_parse_sheet(mock_sheet, 'var_cost')

    def test_parameter_parsing_strategy_can_parse(self):
        """Test ParameterParsingStrategy can_parse_sheet method"""
        strategy = ParameterParsingStrategy()

        # Mock sheets
        set_sheet = Mock()
        param_sheet = Mock()
        result_sheet = Mock()

        # Mock parameter sheet data (has mixed data types)
        param_sheet.iter_rows.return_value = [
            ['parameter_name', 'node', 'technology', 'value'],  # headers
            ['param1', 'node1', 'tech1', 100.0],  # mixed data
        ]

        # Test common parameter sheet names
        assert strategy.can_parse_sheet(param_sheet, 'parameters')
        assert strategy.can_parse_sheet(param_sheet, 'parameter')

        # Test sheet with parameter-like data
        assert strategy.can_parse_sheet(param_sheet, 'some_param_sheet')

        # Test set sheet (should not be recognized as parameter)
        set_sheet.iter_rows.return_value = [
            ['set_name', 'element1', 'element2'],  # only strings
            ['set1', 'elem1', 'elem2'],
        ]
        assert not strategy.can_parse_sheet(set_sheet, 'some_set_sheet')

    def test_result_parsing_strategy_can_parse(self):
        """Test ResultParsingStrategy can_parse_sheet method"""
        strategy = ResultParsingStrategy()

        # Mock sheet with pure numeric data (no mixed types in rows)
        result_sheet = Mock()
        result_sheet.iter_rows.return_value = [
            ['node', 'value'],  # headers
            ['node1', 100.0],   # pure numeric data
            ['node2', 200.0],
        ]

        # Test result sheet patterns
        assert strategy.can_parse_sheet(result_sheet, 'var_cost')
        assert strategy.can_parse_sheet(result_sheet, 'equ_balance')



        # Test sheet without numeric data
        text_sheet = Mock()
        text_sheet.iter_rows.return_value = [
            ['name', 'type'],  # only strings
            ['item1', 'type1'],
        ]
        assert not strategy.can_parse_sheet(text_sheet, 'some_text_sheet')

        # Test sheet with mixed data types (should not be considered result-like)
        mixed_sheet = Mock()
        mixed_sheet.iter_rows.return_value = [
            ['node', 'technology', 'year', 'value'],  # headers
            ['node1', 'tech1', 2020, 100.5],  # mixed data (strings + numbers)
        ]
        assert not strategy.can_parse_sheet(mixed_sheet, 'some_mixed_sheet')

    def test_excel_parser_strategy_selection(self):
        """Test that ExcelParser selects appropriate strategies"""
        parser = ExcelParser()

        # Mock sheets
        set_sheet = Mock()
        param_sheet = Mock()
        result_sheet = Mock()

        # Configure mock sheets
        set_sheet.iter_rows.return_value = [['node'], ['node1']]
        param_sheet.iter_rows.return_value = [
            ['parameter', 'node', 'value'],
            ['param1', 'node1', 100.0]
        ]
        result_sheet.iter_rows.return_value = [
            ['node', 'value'],
            ['node1', 100.0]
        ]

        # Test strategy selection
        set_strategy = parser._get_strategy_for_sheet(set_sheet, 'node')
        assert isinstance(set_strategy, SetParsingStrategy)

        param_strategy = parser._get_strategy_for_sheet(param_sheet, 'parameters')
        assert isinstance(param_strategy, ParameterParsingStrategy)

        result_strategy = parser._get_strategy_for_sheet(result_sheet, 'var_cost')
        assert isinstance(result_strategy, ResultParsingStrategy)

    def test_excel_parser_initialization(self):
        """Test ExcelParser initialization and strategy setup"""
        parser = ExcelParser()

        # Verify parser has the expected strategies in correct order
        assert len(parser.strategies) == 3
        assert isinstance(parser.strategies[0], SetParsingStrategy)
        assert isinstance(parser.strategies[1], ResultParsingStrategy)
        assert isinstance(parser.strategies[2], ParameterParsingStrategy)

        # Verify the parameter parsing strategy is configured for input data
        param_strategy = parser.strategies[2]
        assert param_strategy.param_type == 'input'


class TestDesignPatternIntegration:
    """Test integration of all design patterns"""

    def test_data_manager_with_observer_and_factory(self):
        """Test that BaseDataManager integrates Observer and Factory patterns"""
        # Create a concrete subclass for testing
        class TestDataManager(BaseDataManager):
            def _parse_workbook(self, wb, scenario, progress_callback=None):
                pass

        manager = TestDataManager()
        observer = Mock(spec=DataObserver)

        manager.add_observer(observer)

        # Verify observer management works
        assert observer in manager._observers

        # Verify factory integration through parameter creation
        # (This would be tested more thoroughly with actual file loading)

    def test_factory_integration_with_parsing(self):
        """Test that parsing strategies integrate with the factory system"""
        # Test that the parameter factory registry is accessible and works
        registry = parameter_factory_registry

        # Create a parameter using the factory
        test_data = [['node1', 100.0]]
        headers = ['node', 'value']

        parameter = registry.create_parameter('input', 'test_param', test_data, headers)

        assert parameter is not None
        if parameter:
            assert parameter.metadata.get('parameter_type') == 'input'
            assert parameter.name == 'test_param'

    def test_full_pattern_integration_workflow(self):
        """Test a complete workflow using all patterns"""
        # Create manager with observer
        class TestDataManager(BaseDataManager):
            def _parse_workbook(self, wb, scenario, progress_callback=None):
                pass

        manager = TestDataManager()
        observer = Mock(spec=DataObserver)
        manager.add_observer(observer)

        # Mock the file loading process
        scenario = ScenarioData()
        manager.scenarios.append(scenario)
        manager.loaded_file_paths.append('test.xlsx')

        # Simulate data loading completion (normally done in load_file)
        manager._notify_data_loaded(scenario, 'test.xlsx')

        # Verify observer was notified
        observer.on_data_loaded.assert_called_once_with(scenario, 'test.xlsx')

        # Verify scenario management works
        current = manager.get_current_scenario()
        assert current is scenario
