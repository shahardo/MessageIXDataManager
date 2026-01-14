"""
Parameter Factory - Factory pattern for creating different types of parameters
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.data_models import Parameter


class ParameterFactory(ABC):
    """Abstract base class for parameter factories"""

    @abstractmethod
    def create_parameter(self, param_name: str, param_data: List, headers: List[str],
                        metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Create a parameter with specific factory logic"""
        pass


class StandardParameterFactory(ParameterFactory):
    """Factory for standard parameters"""

    def create_parameter(self, param_name: str, param_data: List, headers: List[str],
                        metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Create a standard parameter"""
        return self._create_from_data(param_name, param_data, headers, metadata_overrides)

    def _create_from_data(self, param_name: str, param_data: List, headers: List[str],
                         metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Core parameter creation logic"""
        import pandas as pd
        import numpy as np

        try:
            # Input validation
            if not param_data or not headers:
                return None

            # Create DataFrame with proper type handling
            df = pd.DataFrame(param_data, columns=headers)

            # Convert None to NaN
            df = df.replace({None: np.nan})

            # Handle integer columns with NaN
            for col in df.columns:
                col_data = df[col]
                if col_data.dtype in ['int64', 'int32'] and col_data.isna().any():
                    df[col] = col_data.astype('float64')



            # Remove completely empty rows
            df = df.dropna(how='all')

            if df.empty:
                return None

            # Determine dimensions and value column
            dims = headers[:-1] if len(headers) > 1 else []
            value_col = headers[-1] if len(headers) > 0 else 'value'

            # Create metadata
            metadata = {
                'units': 'N/A',
                'desc': f'Parameter {param_name}',
                'dims': dims,
                'value_column': value_col,
                'shape': df.shape
            }

            # Apply overrides
            if metadata_overrides:
                metadata.update(metadata_overrides)

            return Parameter(param_name, df, metadata)

        except Exception as e:
            print(f"Warning: Could not create parameter {param_name}: {str(e)}")
            return None


class InputParameterFactory(StandardParameterFactory):
    """Factory for MESSAGEix input parameters"""

    def create_parameter(self, param_name: str, param_data: List, headers: List[str],
                        metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Create an input parameter with input-specific metadata"""
        # Add input-specific metadata
        input_overrides = {
            'parameter_type': 'input',
            'source': 'MESSAGEix input data'
        }

        if metadata_overrides:
            input_overrides.update(metadata_overrides)

        return super()._create_from_data(param_name, param_data, headers, input_overrides)


class ResultParameterFactory(StandardParameterFactory):
    """Factory for MESSAGEix result parameters"""

    def create_parameter(self, param_name: str, param_data: List, headers: List[str],
                        metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Create a result parameter with result-specific metadata"""
        # Add result-specific metadata
        result_overrides = {
            'parameter_type': 'result',
            'source': 'MESSAGEix solution data'
        }

        if metadata_overrides:
            result_overrides.update(metadata_overrides)

        return super()._create_from_data(param_name, param_data, headers, result_overrides)


class ParameterFactoryRegistry:
    """Registry for managing parameter factories"""

    def __init__(self):
        self._factories = {
            'standard': StandardParameterFactory(),
            'input': InputParameterFactory(),
            'result': ResultParameterFactory()
        }

    def get_factory(self, param_type: str = 'standard') -> ParameterFactory:
        """Get a factory by type"""
        return self._factories.get(param_type, self._factories['standard'])

    def register_factory(self, param_type: str, factory: ParameterFactory):
        """Register a new factory"""
        self._factories[param_type] = factory

    def create_parameter(self, param_type: str, param_name: str, param_data: List,
                        headers: List[str], metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
        """Create parameter using specified factory type"""
        factory = self.get_factory(param_type)
        return factory.create_parameter(param_name, param_data, headers, metadata_overrides)


# Global registry instance
parameter_factory_registry = ParameterFactoryRegistry()
