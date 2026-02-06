"""
Data Transformation Utility

Provides data transformation and filtering utilities for both table display
and chart preparation. Extracted from MainWindow and DataDisplayWidget to
centralize data transformation logic.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Union
from core.data_models import Parameter


class DataTransformer:
    """
    Utility class for transforming MESSAGEix data for display and analysis.

    Provides methods for:
    - Transforming raw data to display formats (advanced/pivot views)
    - Applying filters and year ranges
    - Preparing data for chart visualization
    - Identifying column types and structures
    """

    @staticmethod
    def prepare_chart_data(parameter: Parameter, is_results: bool = False,
                          scenario_options: Optional[Dict[str, Any]] = None,
                          filters: Optional[Dict[str, str]] = None,
                          hide_empty: bool = False) -> Optional[pd.DataFrame]:
        """
        Prepare parameter data for chart display.

        Args:
            parameter: Parameter object to transform
            is_results: Whether this is results data
            scenario_options: Scenario options (year limits, etc.)
            filters: Filter selections to apply
            hide_empty: Whether to hide empty columns

        Returns:
            Transformed DataFrame ready for chart display
        """
        if not parameter or parameter.df.empty:
            return None

        df = parameter.df

        # Apply year filtering to raw data first (before transformation)
        if scenario_options and not df.empty:
            df = DataTransformer.apply_year_filtering(df, scenario_options)

        # Transform to display format using common logic
        transformed_df = DataTransformer.transform_for_display(
            df, is_results=is_results, display_mode="advanced",
            filters=filters, hide_empty=hide_empty, for_chart=True
        )

        return transformed_df

    @staticmethod
    def apply_year_filtering(df: pd.DataFrame, scenario_options: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply year filtering to DataFrame based on scenario options.
        Filters on ALL year columns found (year, year_act, year_vtg) to ensure
        the filtered data is consistent regardless of which column the pivot uses.

        Args:
            df: DataFrame to filter
            scenario_options: Dictionary containing year limits

        Returns:
            Filtered DataFrame
        """
        if df.empty or not scenario_options.get('YearsLimitEnabled', True):
            return df

        min_year = scenario_options.get('MinYear', 2020)
        max_year = scenario_options.get('MaxYear', 2050)

        result_df = df.copy()
        filtered_any = False

        # Filter on ALL year columns found in the DataFrame
        year_col_names = ['year', 'year_act', 'year_vtg']
        for year_col in year_col_names:
            if year_col in result_df.columns:
                try:
                    year_values = pd.to_numeric(result_df[year_col], errors='coerce')
                    mask = (year_values >= min_year) & (year_values <= max_year)
                    result_df = result_df[mask]
                    filtered_any = True
                except (TypeError, ValueError):
                    pass  # Skip if conversion fails

        if filtered_any:
            return result_df

        # If no column filtering happened, check for year in index
        if isinstance(df.index, pd.MultiIndex):
            for year_level in year_col_names:
                if year_level in df.index.names:
                    try:
                        year_values = pd.to_numeric(df.index.get_level_values(year_level), errors='coerce')
                        mask = (year_values >= min_year) & (year_values <= max_year)
                        return df[mask].copy()
                    except (TypeError, ValueError):
                        pass
        elif hasattr(df.index, 'name') and df.index.name in year_col_names:
            try:
                year_values = pd.to_numeric(pd.Series(df.index), errors='coerce')
                mask = (year_values >= min_year) & (year_values <= max_year)
                return df[mask.values].copy()
            except (TypeError, ValueError):
                pass

        return result_df

    @staticmethod
    def transform_for_display(df: pd.DataFrame, is_results: bool = False,
                             display_mode: str = "raw", filters: Optional[Dict[str, str]] = None,
                             hide_empty: bool = False, for_chart: bool = False) -> pd.DataFrame:
        """
        Transform data to display format for both table and chart views.

        Args:
            df: Input DataFrame
            is_results: Whether this is results data
            display_mode: "raw" or "advanced"
            filters: Filter selections to apply
            hide_empty: Whether to hide empty columns
            for_chart: Whether this is for chart display

        Returns:
            Transformed DataFrame ready for display
        """
        try:
            if df.empty:
                return df

            if display_mode == "raw" and not is_results:
                # Raw mode for input data - return as-is after filtering
                filtered_df = DataTransformer._apply_filters(df, filters)
                return filtered_df

            # For advanced mode or results data, transform structure
            if hide_empty is None:
                hide_empty = False  # Default to not hiding if not specified

            # Identify column types (pass is_results to correctly identify value column for variables)
            column_info = DataTransformer._identify_columns(df, is_results)

            # Apply filters
            filtered_df = DataTransformer._apply_filters(df, filters)

            # Transform data structure
            transformed_df = DataTransformer._transform_data_structure(filtered_df, column_info, is_results, for_chart)

            # Clean and finalize output
            final_df = DataTransformer._clean_output(transformed_df, hide_empty, is_results)

            return final_df
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    @staticmethod
    def _identify_columns(df: pd.DataFrame, is_results: bool = False) -> Dict[str, Union[List[str], Optional[str]]]:
        """Identify different types of columns in the DataFrame

        Args:
            df: Input DataFrame
            is_results: True if this is results data (variables/equations use 'lvl' column)
        """
        year_cols = []
        pivot_cols = []  # Columns that become pivot table headers
        filter_cols = []  # Columns used for filtering
        ignored_cols = []  # Columns to ignore completely
        value_col = None

        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['value', 'val']:
                value_col = col
            elif col_lower == 'lvl' and is_results:
                # For result variables/equations, 'lvl' (level) is the value column
                value_col = col
            elif col_lower in ['year_vtg', 'year_act', 'year', 'period', 'year_vintage', 'year_rel', 'year_active']:
                year_cols.append(col)
            elif col_lower in ['time', 'unit', 'units', 'mrg']:
                # Ignore these columns completely (mrg is marginal for results)
                ignored_cols.append(col)
            elif col_lower in ['commodity', 'technology', 'type', 'tec', 'category', 'relation']:
                # These become pivot table column headers
                # 'category' is used by postprocessed results (e.g., technology types, fuel types)
                # 'relation' is used by REL variable
                pivot_cols.append(col)
            elif col_lower in ['region', 'node', 'node_loc', 'node_rel', 'node_dest', 'node_origin',
                              'mode', 'level', 'grade', 'fuel', 'sector', 'subcategory']:
                # These are used for filtering
                filter_cols.append(col)

        # Fallback: if no value column found for results, check for 'lvl'
        if value_col is None and is_results and 'lvl' in df.columns:
            value_col = 'lvl'

        return {
            'year_cols': year_cols,
            'pivot_cols': pivot_cols,
            'filter_cols': filter_cols,
            'ignored_cols': ignored_cols,
            'value_col': value_col
        }

    @staticmethod
    def _apply_filters(df: pd.DataFrame, filters: Optional[Dict[str, str]]) -> pd.DataFrame:
        """Apply current filter selections to DataFrame"""
        try:
            filtered_df = df.copy()
            if filters:
                for filter_col, filter_value in filters.items():
                    if filter_value and filter_value != "All" and filter_col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[filter_col] == filter_value]
            return filtered_df
        except Exception as e:
            print(f"ERROR in _apply_filters: {e}")
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    @staticmethod
    def _transform_data_structure(df: pd.DataFrame, column_info: dict, is_results: bool, for_chart: bool = False) -> pd.DataFrame:
        """Transform DataFrame structure based on data type"""
        # Pivoting logic for both input and results data
        # Results data uses 'lvl' column as value, identified in _identify_columns
        if DataTransformer._should_pivot(df, column_info):
            return DataTransformer._perform_pivot(df, column_info)
        else:
            return DataTransformer._prepare_2d_format(df, column_info)

    @staticmethod
    def _clean_output(df: pd.DataFrame, hide_empty: bool, is_results: bool) -> pd.DataFrame:
        """Clean and filter final output DataFrame"""
        if hide_empty:
            df = DataTransformer._hide_empty_columns(df, is_results)

        # Additional cleaning logic
        return df

    @staticmethod
    def _should_pivot(df: pd.DataFrame, column_info: dict) -> bool:
        """Determine if DataFrame should be pivoted based on column structure"""
        # Pivoting logic - simplified for now
        year_cols = column_info.get('year_cols', [])
        pivot_cols = column_info.get('pivot_cols', [])
        value_col = column_info.get('value_col')

        # Pivot if we have year columns, pivot columns, and a value column
        return bool(year_cols and pivot_cols and value_col)

    @staticmethod
    def _perform_pivot(df: pd.DataFrame, column_info: dict) -> pd.DataFrame:
        """Perform pivot operation on DataFrame"""
        try:
            year_cols = column_info.get('year_cols', [])
            pivot_cols = column_info.get('pivot_cols', [])
            value_col = column_info.get('value_col')

            if not (year_cols and pivot_cols and value_col):
                return df

            # Try different combinations of year and pivot columns
            for index_col in year_cols:
                for columns_col in pivot_cols:
                    try:
                        pivoted = df.pivot_table(
                            values=value_col,
                            index=index_col,
                            columns=columns_col,
                            aggfunc=lambda x: x.iloc[0] if len(x) > 0 else np.nan
                        )
                        return pivoted
                    except Exception as e:
                        continue

            # Fallback to original data if all pivot attempts fail
            return df
        except Exception as e:
            print(f"ERROR in _perform_pivot: {e}")
            import traceback
            traceback.print_exc()
            # Return original df as fallback
            return df

    @staticmethod
    def _prepare_2d_format(df: pd.DataFrame, column_info: dict) -> pd.DataFrame:
        """Prepare DataFrame in 2D format without pivoting"""
        # For results data in advanced view, set year as index and remove year column
        year_cols = column_info.get('year_cols', [])
        if year_cols:
            # Use the first year column found
            year_col = year_cols[0]
            if year_col in df.columns:
                # Set year as index and remove from columns
                df = df.set_index(year_col)
                df.index.name = year_col
        return df

    @staticmethod
    def _hide_empty_columns(df: pd.DataFrame, is_results: bool) -> pd.DataFrame:
        """Hide columns that are entirely empty or zero"""
        if df.empty:
            return df

        # Identify column indices to keep (use iloc to handle duplicate column names)
        columns_to_keep = []
        for i, col in enumerate(df.columns):
            col_data = df.iloc[:, i]  # Use iloc to get column by position, not name
            if col_data.dtype in ['int64', 'float64']:
                # Keep numeric columns that have at least one non-zero, non-NaN value
                if not (col_data.dropna() == 0).all():
                    columns_to_keep.append(i)
            else:
                # Keep non-numeric columns that have at least one non-empty value
                if not col_data.isna().all():
                    columns_to_keep.append(i)

        return df.iloc[:, columns_to_keep] if columns_to_keep else df
