"""
Results Analyzer - handles loading and parsing of message_ix result Excel files
"""

import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from typing import Dict, List, Optional, Any, Callable

from core.data_models import ScenarioData, Parameter


class ResultsAnalyzer:
    """Analyzes message_ix result Excel files and prepares data for visualization"""

    def __init__(self):
        self.results: List[ScenarioData] = []
        self.loaded_file_paths: List[str] = []
        self.summary_stats: Dict[str, Any] = {}

    def load_results_file(self, file_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScenarioData:
        """
        Load and parse a message_ix results Excel file

        Args:
            file_path: Path to the results Excel file
            progress_callback: Optional callback function for progress updates (value, message)

        Returns:
            ScenarioData object containing parsed results

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Results file not found: {file_path}")

        print(f"Loading results file: {file_path}")

        # Create new results data
        results = ScenarioData()

        try:
            # Initialize progress
            if progress_callback:
                progress_callback(0, "Loading results workbook...")

            # Load workbook
            wb = load_workbook(file_path, data_only=True)

            if progress_callback:
                progress_callback(20, "Workbook loaded, parsing results...")

            # Parse results (typically in var_* and equ_* sheets)
            self._parse_results(wb, results, progress_callback)

            if progress_callback:
                progress_callback(80, "Calculating summary statistics...")

            # Calculate summary statistics for all loaded results
            combined_results = self.get_current_results()
            if combined_results:
                self._calculate_summary_stats(combined_results)

            # Store reference
            self.results.append(results)
            self.loaded_file_paths.append(file_path)

            if progress_callback:
                progress_callback(100, "Results loading complete")

            print(f"Successfully loaded results with {len(results.parameters)} variables/equations")

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise ValueError(f"Error parsing results file: {str(e)}")

        return results

    def _parse_results(self, wb, results: ScenarioData, progress_callback: Optional[Callable[[int, str], None]] = None):
        """Parse results from workbook"""
        # Look for result sheets (typically var_* for variables, equ_* for equations)
        result_sheets = [sheet_name for sheet_name in wb.sheetnames if sheet_name.startswith(('var_', 'equ_'))]

        # Also include sheets that look like result data (have headers and data rows)
        # Exclude sheets that are clearly input-related
        input_indicators = ['parameter', 'parameters', 'set', 'sets', 'data']
        potential_result_sheets = [sheet_name for sheet_name in wb.sheetnames
                                 if not any(indicator.lower() in sheet_name.lower() for indicator in input_indicators)
                                 and sheet_name not in result_sheets]

        # Check which potential sheets actually contain result-like data
        for sheet_name in potential_result_sheets:
            sheet = wb[sheet_name]
            if self._is_result_sheet(sheet):
                result_sheets.append(sheet_name)

        total_sheets = len(result_sheets)

        for i, sheet_name in enumerate(result_sheets):
            if progress_callback and total_sheets > 0:
                progress = 20 + int((i / total_sheets) * 60)  # Progress from 20% to 80%
                progress_callback(progress, f"Parsing result sheet: {sheet_name}")

            sheet = wb[sheet_name]
            self._parse_result_sheet(sheet, results, sheet_name)

    def _is_result_sheet(self, sheet) -> bool:
        """Check if a sheet contains result-like data"""
        try:
            # Get all rows
            rows = list(sheet.iter_rows(values_only=True))

            # Need at least headers + 1 data row
            if len(rows) < 2:
                return False

            # Check if first row looks like headers (strings)
            headers = rows[0]
            if not headers or not any(isinstance(h, str) and h.strip() for h in headers):
                return False

            # Check if we have at least one data row with some numeric values
            has_numeric_data = False
            for row in rows[1:]:
                if any(isinstance(cell, (int, float)) and not pd.isna(cell) for cell in row):
                    has_numeric_data = True
                    break

            return has_numeric_data

        except Exception:
            return False

    def _parse_result_sheet(self, sheet, results: ScenarioData, sheet_name: str):
        """Parse individual result sheet"""
        # Get all headers (including None)
        all_headers = [cell.value for cell in sheet[1]]

        # Check if first column should be included as year column
        include_year_column = False
        if len(all_headers) > 0 and all_headers[0] is None:
            # Check if first column data looks like years
            year_values = []
            for row in sheet.iter_rows(min_row=2, max_row=min(10, sheet.max_row), values_only=True):
                if row and len(row) > 0 and row[0] is not None:
                    try:
                        year_val = float(row[0])
                        if 1900 <= year_val <= 2100:  # Reasonable year range
                            year_values.append(year_val)
                    except (ValueError, TypeError):
                        pass

            # Include as year column if we found year-like values
            if len(year_values) >= 3:  # At least a few years
                include_year_column = True

        # Filter out None headers and get their indices
        headers = []
        valid_indices = []
        for i, header in enumerate(all_headers):
            if header is not None:
                headers.append(str(header))
                valid_indices.append(i)
            elif i == 0 and include_year_column:
                # Include first column as year column
                headers.append("year")
                valid_indices.append(i)

        if not headers:
            return

        # Make headers unique, as duplicate column names can cause issues with pandas
        unique_headers = []
        counts = {}
        for col in headers:
            if col in counts:
                counts[col] += 1
                unique_headers.append(f"{col}.{counts[col]-1}")
            else:
                counts[col] = 1
                unique_headers.append(col)
        headers = unique_headers

        # Parse data, keeping only columns with valid headers
        data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row and any(cell is not None for cell in row):
                # Filter row to only include valid columns
                filtered_row = [row[i] for i in valid_indices if i < len(row)]
                if filtered_row:  # Only add if we have some valid data
                    data.append(filtered_row)

        if data and len(data) > 0:
            df = pd.DataFrame(data, columns=headers)
            # Ensure None values are converted to NaN to preserve empty cells
            df = df.replace({None: np.nan})

            # Convert any integer columns that contain NaN to float to preserve NaN values
            for col in df.columns:
                col_data = df[col]
                if hasattr(col_data, 'dtype') and col_data.dtype in ['int64', 'int32', 'int16', 'int8'] and col_data.isna().any():
                    df[col] = col_data.astype('float64')

            # Convert columns that are all zeros to NaN (treat as empty)
            for col in df.columns:
                col_data = df[col]
                if hasattr(col_data, 'dtype') and col_data.dtype in ['int64', 'int32', 'int16', 'int8', 'float64', 'float32']:
                    # Check if all non-NaN values are 0
                    non_nan_values = col_data.dropna()
                    if len(non_nan_values) > 0 and (non_nan_values == 0).all():
                        df[col] = col_data.replace(0, np.nan)

            # Create parameter object for this result
            metadata = {
                'units': 'N/A',
                'desc': f'Result {sheet_name}',
                'dims': headers[:-1] if len(headers) > 1 else [],
                'result_type': 'variable' if sheet_name.startswith('var_') else 'equation'
            }

            parameter = Parameter(sheet_name, df, metadata)
            results.add_parameter(parameter)

    def _calculate_summary_stats(self, results: ScenarioData):
        """Calculate summary statistics from results"""
        self.summary_stats = {
            'total_variables': 0,
            'total_equations': 0,
            'total_data_points': 0,
            'result_sheets': []
        }

        for param in results.parameters.values():
            self.summary_stats['total_data_points'] += len(param.df)

            if param.metadata.get('result_type') == 'variable':
                self.summary_stats['total_variables'] += 1
            else:
                self.summary_stats['total_equations'] += 1

            self.summary_stats['result_sheets'].append(param.name)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of loaded results"""
        return self.summary_stats.copy()

    def get_result_data(self, result_name: str) -> Optional[Parameter]:
        """Get specific result data by name"""
        results = self.get_current_results()
        if results:
            return results.get_parameter(result_name)
        return None

    def get_all_result_names(self) -> List[str]:
        """Get list of all result names"""
        results = self.get_current_results()
        if results:
            return results.get_parameter_names()
        return []

    def prepare_chart_data(self, result_name: str, chart_type: str = 'line') -> Optional[Dict[str, Any]]:
        """
        Prepare data for charting

        Args:
            result_name: Name of the result to chart
            chart_type: Type of chart ('line', 'bar', 'stacked_bar', 'stacked_area', 'area')

        Returns:
            Dictionary with chart data or None if not available
        """
        parameter = self.get_result_data(result_name)
        if not parameter:
            return None

        df = parameter.df

        # Basic data preparation (would be more sophisticated in real implementation)
        chart_data = {
            'title': f'{result_name} Results',
            'x_label': 'Index',
            'y_label': 'Value',
            'data': []
        }

        # Simple chart preparation
        if len(df.columns) >= 2:
            # For line charts, use index as x
            x_data = list(range(len(df)))

            if chart_type == 'line':
                # Assume last column is the value column
                value_col = df.columns[-1]
                chart_data['data'] = [{
                    'x': x_data,
                    'y': df[value_col].fillna(0).tolist(),
                    'type': 'line',
                    'name': result_name
                }]
            elif chart_type in ['bar', 'stacked_bar']:
                # For bar charts, create traces for each numeric column
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    for col in numeric_cols:
                        chart_data['data'].append({
                            'x': df.index.tolist() if hasattr(df, 'index') else x_data,
                            'y': df[col].fillna(0).tolist(),
                            'name': str(col)
                        })
                else:
                    # Fallback to last column
                    value_col = df.columns[-1]
                    chart_data['data'] = [{
                        'x': x_data,
                        'y': df[value_col].fillna(0).tolist(),
                        'name': result_name
                    }]

        return chart_data

    def get_current_results(self) -> Optional[ScenarioData]:
        """Get the combined results from all loaded files"""
        if not self.results:
            return None

        if len(self.results) == 1:
            return self.results[0]

        # Combine multiple results
        combined = ScenarioData()
        for result in self.results:
            # Merge sets (avoid duplicates)
            for set_name, set_data in result.sets.items():
                if set_name not in combined.sets:
                    combined.sets[set_name] = set_data.copy()
                else:
                    # Merge set elements - concatenate Series and drop duplicates
                    combined.sets[set_name] = pd.concat([combined.sets[set_name], set_data]).drop_duplicates().reset_index(drop=True)

            # Merge parameters (results are typically variables and equations)
            for param_name, param in result.parameters.items():
                if param_name not in combined.parameters:
                    # Create a copy of the parameter with copied DataFrame
                    param_copy = Parameter(param.name, param.df.copy(), param.metadata.copy())
                    combined.parameters[param_name] = param_copy
                else:
                    # Merge result data (append rows) - create new DataFrame
                    existing_data = combined.parameters[param_name].df
                    new_data = param.df
                    combined.parameters[param_name].df = pd.concat([existing_data, new_data], ignore_index=True)

        return combined

    def get_loaded_file_paths(self) -> List[str]:
        """Get list of all loaded file paths"""
        return self.loaded_file_paths.copy()

    def get_results_by_file_path(self, file_path: str) -> Optional[ScenarioData]:
        """Get specific results by file path"""
        if file_path in self.loaded_file_paths:
            index = self.loaded_file_paths.index(file_path)
            return self.results[index]
        return None

    def clear_results(self):
        """Clear all loaded results"""
        self.results.clear()
        self.loaded_file_paths.clear()

    def remove_file(self, file_path: str) -> bool:
        """
        Remove a loaded results file and its associated data

        Args:
            file_path: Path to the file to remove

        Returns:
            True if file was found and removed, False otherwise
        """
        if file_path in self.loaded_file_paths:
            # Find the index of the file
            index = self.loaded_file_paths.index(file_path)

            # Remove from both lists
            self.loaded_file_paths.pop(index)
            self.results.pop(index)

            print(f"Removed results file: {file_path}")
            return True

        return False
