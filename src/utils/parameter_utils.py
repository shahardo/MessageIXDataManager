import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from core.data_models import Parameter

def create_parameter_from_data(param_name: str, param_data: List, headers: List[str],
                              metadata_overrides: Optional[Dict[str, Any]] = None) -> Optional[Parameter]:
    """
    Create a Parameter object from raw Excel data with comprehensive data cleaning.

    Args:
        param_name: Name of the parameter
        param_data: List of row data from Excel
        headers: Column headers
        metadata_overrides: Optional metadata to override defaults

    Returns:
        Parameter object or None if creation fails
    """
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

        # Filter all-zero columns (treat as empty)
        for col in df.columns:
            col_data = df[col]
            if col_data.dtype in ['int64', 'float64'] and (col_data.dropna() == 0).all():
                df[col] = col_data.replace(0, np.nan)

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
