"""
Data file loading and processing for solver output files.
Handles ZIP extraction, CSV parsing, and DataFrame assembly.

Extracted from main_window.py as part of refactoring to reduce God Class.
"""
from typing import Dict, Optional, Tuple, List, Set, Callable, Any
import pandas as pd
import zipfile
import re
import os

from core.data_models import ScenarioData, Parameter


class DataFileManager:
    """
    Manages loading and parsing of solver output data files.

    Supports ZIP files containing CSV tables with the following naming convention:
    - set_xxx.csv: message sets (input)
    - par_xxx.csv: message parameters (input)
    - var_xxx.csv: message variables (output)
    - equ_xxx.csv: message equations (output)
    """

    # Prefixes for file categorization
    VAR_PREFIX = "var_"
    PAR_PREFIX = "par_"
    SET_PREFIX = "set_"
    EQU_PREFIX = "equ_"

    # Internal solver rows to filter out (patterns like _res#, _ref#, _cv#, _hist_####)
    INTERNAL_SOLVER_PATTERN = re.compile(r'.*_((res|ref|cv)\d|hist_\d+)$')

    def __init__(
        self,
        tech_descriptions: Optional[Dict[str, Any]] = None,
        console_callback: Optional[Callable[[str], None]] = None,
        log_callback: Optional[Callable[[str, str, str, Dict], None]] = None
    ):
        """
        Initialize the data file manager.

        Args:
            tech_descriptions: Optional mapping of technology codes to descriptions
            console_callback: Optional callback for console output (message)
            log_callback: Optional callback for logging (level, module, message, extra)
        """
        self.tech_descriptions = tech_descriptions or {}
        self._console_callback = console_callback
        self._log_callback = log_callback

    def set_console_callback(self, callback: Callable[[str], None]) -> None:
        """Set the console output callback."""
        self._console_callback = callback

    def set_log_callback(self, callback: Callable[[str, str, str, Dict], None]) -> None:
        """Set the logging callback."""
        self._log_callback = callback

    def _log(self, level: str, message: str, extra: Optional[Dict] = None) -> None:
        """Log a message using the configured callback."""
        if self._log_callback:
            self._log_callback(level, 'DATA_FILE_MANAGER', message, extra or {})
        print(f"DEBUG [{level}]: {message}")

    def _console(self, message: str) -> None:
        """Output to console using the configured callback."""
        if self._console_callback:
            self._console_callback(message)

    def load_data_file(
        self,
        file_path: str,
        existing_scenario: Optional[ScenarioData] = None
    ) -> Tuple[Optional[ScenarioData], List[Tuple[str, str]]]:
        """
        Load a data file (ZIP with CSVs).

        Args:
            file_path: Path to the data file
            existing_scenario: Optional existing scenario data for conflict detection

        Returns:
            Tuple of (ScenarioData or None, list of (item_type, item_name) tuples for replaced items)
        """
        if not file_path.endswith('.zip'):
            self._console(f"Unsupported file format: {file_path}")
            return None, []

        return self._load_zipped_csv_data(file_path, existing_scenario)

    def _load_zipped_csv_data(
        self,
        zip_path: str,
        existing_scenario: Optional[ScenarioData] = None
    ) -> Tuple[Optional[ScenarioData], List[Tuple[str, str]]]:
        """
        Extract and parse CSV files from a ZIP archive.

        Args:
            zip_path: Path to the zip file
            existing_scenario: Optional existing scenario for conflict detection

        Returns:
            Tuple of (ScenarioData, list of replaced items)
        """
        scenario_data = ScenarioData()
        replaced_items: List[Tuple[str, str]] = []

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Get list of CSV files in the archive
                csv_files = [f for f in zf.namelist() if f.lower().endswith('.csv')]
                print(f"DEBUG: Found {len(csv_files)} CSV files in zip archive")

                # First pass: collect electricity-generating technologies from par_output
                electricity_technologies = self._extract_electricity_technologies(zf, csv_files)

                # Second pass: process all CSV files
                for csv_name in csv_files:
                    try:
                        result = self._process_csv_file(
                            zf, csv_name, electricity_technologies, existing_scenario
                        )
                        if result:
                            item_type, name, data = result
                            if item_type == 'set':
                                # Check for existing set
                                if existing_scenario and name in existing_scenario.sets:
                                    replaced_items.append(('set', name))
                                scenario_data.sets[name] = data
                            elif item_type in ('parameter', 'variable', 'equation'):
                                # Check for existing parameter
                                if existing_scenario and existing_scenario.get_parameter(name):
                                    replaced_items.append((item_type, name))
                                scenario_data.add_parameter(data, mark_modified=False, add_to_history=False)
                    except Exception as e:
                        print(f"ERROR loading CSV {csv_name}: {e}")
                        self._console(f"Error loading {csv_name}: {e}")
                        self._log('ERROR', f"Error loading CSV {csv_name}", {
                            'file_path': zip_path,
                            'csv_name': csv_name,
                            'error': str(e)
                        })

        except zipfile.BadZipFile:
            print(f"ERROR: {zip_path} is not a valid zip file")
            self._console(f"Error: {os.path.basename(zip_path)} is not a valid zip file")
            self._log('ERROR', "Bad zip file", {'file_path': zip_path})
            return None, []
        except Exception as e:
            print(f"ERROR opening zip file {zip_path}: {e}")
            self._console(f"Error opening zip file: {e}")
            self._log('ERROR', "Error opening zip file", {'file_path': zip_path, 'error': str(e)})
            return None, []

        return scenario_data, replaced_items

    def _extract_electricity_technologies(
        self,
        zf: zipfile.ZipFile,
        csv_files: List[str]
    ) -> Set[str]:
        """
        Extract electricity-generating technologies from par_output file.

        Args:
            zf: Open ZipFile object
            csv_files: List of CSV filenames in the archive

        Returns:
            Set of technology names that generate electricity
        """
        electricity_technologies: Set[str] = set()

        for csv_name in csv_files:
            base_name = os.path.basename(csv_name)
            name_without_ext = os.path.splitext(base_name)[0]

            if name_without_ext.lower() == 'par_output':
                with zf.open(csv_name) as csv_file:
                    output_df = pd.read_csv(csv_file)

                # Find technologies that output 'electr' commodity with value > 0
                if 'commodity' in output_df.columns and 'value' in output_df.columns:
                    tec_col = self._find_technology_column(output_df)
                    if tec_col:
                        electr_mask = (output_df['commodity'] == 'electr') & (output_df['value'] > 0)
                        electricity_technologies = set(output_df.loc[electr_mask, tec_col].unique())
                        print(f"DEBUG: Found {len(electricity_technologies)} electricity-generating technologies")
                break

        return electricity_technologies

    def _find_technology_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the technology column name in a DataFrame."""
        if 'technology' in df.columns:
            return 'technology'
        elif 'tec' in df.columns:
            return 'tec'
        return None

    def _process_csv_file(
        self,
        zf: zipfile.ZipFile,
        csv_name: str,
        electricity_technologies: Set[str],
        existing_scenario: Optional[ScenarioData]
    ) -> Optional[Tuple[str, str, Any]]:
        """
        Process a single CSV file from the archive.

        Args:
            zf: Open ZipFile object
            csv_name: Name of the CSV file
            electricity_technologies: Set of electricity-generating technology names
            existing_scenario: Optional existing scenario for conflict detection

        Returns:
            Tuple of (item_type, name, data) or None if file should be skipped
        """
        # Extract base name without path and extension
        base_name = os.path.basename(csv_name)
        name_without_ext = os.path.splitext(base_name)[0]

        # Read CSV into DataFrame
        with zf.open(csv_name) as csv_file:
            df = pd.read_csv(csv_file)

        if df.empty:
            return None

        # Categorize by prefix
        if name_without_ext.lower().startswith(self.SET_PREFIX):
            return self._process_set_file(name_without_ext, df)
        elif name_without_ext.lower().startswith(self.PAR_PREFIX):
            return self._process_parameter_file(name_without_ext, df)
        elif name_without_ext.lower().startswith(self.VAR_PREFIX):
            return self._process_variable_file(name_without_ext, df, electricity_technologies)
        elif name_without_ext.lower().startswith(self.EQU_PREFIX):
            return self._process_equation_file(name_without_ext, df, electricity_technologies)
        else:
            return None

    def _process_set_file(
        self,
        name_without_ext: str,
        df: pd.DataFrame
    ) -> Tuple[str, str, pd.Series]:
        """Process a set CSV file."""
        set_name = name_without_ext[4:]  # Remove 'set_' prefix

        # Store set - use first column as the set values
        if len(df.columns) == 1:
            set_data = df.iloc[:, 0]
        else:
            # Multi-column set - store first column
            set_data = df.iloc[:, 0]

        return ('set', set_name, set_data)

    def _process_parameter_file(
        self,
        name_without_ext: str,
        df: pd.DataFrame
    ) -> Tuple[str, str, Parameter]:
        """Process a parameter CSV file."""
        param_name = name_without_ext[4:]  # Remove 'par_' prefix

        # Determine dimensions (exclude value/unit columns)
        dims = [col for col in df.columns if col not in ['value', 'unit']]

        metadata = {
            'dims': dims,
            'units': df['unit'].iloc[0] if 'unit' in df.columns and len(df) > 0 else 'unknown',
            'result_type': None  # Input parameter
        }

        param = Parameter(name=param_name, df=df, metadata=metadata)
        return ('parameter', param_name, param)

    def _process_variable_file(
        self,
        name_without_ext: str,
        df: pd.DataFrame,
        electricity_technologies: Set[str]
    ) -> Tuple[str, str, Parameter]:
        """Process a variable CSV file."""
        var_name = name_without_ext[4:]  # Remove 'var_' prefix

        # Apply technology filtering
        df = self._filter_to_electricity_technologies(df, electricity_technologies, var_name)
        df = self._filter_internal_solver_rows(df, var_name)

        # Determine dimensions (exclude level/marginal/unit columns)
        dims = [col for col in df.columns if col not in ['lvl', 'mrg', 'level', 'marginal', 'unit']]

        metadata = {
            'dims': dims,
            'units': df['unit'].iloc[0] if 'unit' in df.columns and len(df) > 0 else 'unknown',
            'result_type': 'variable'
        }

        param = Parameter(name=var_name, df=df, metadata=metadata)
        return ('variable', var_name, param)

    def _process_equation_file(
        self,
        name_without_ext: str,
        df: pd.DataFrame,
        electricity_technologies: Set[str]
    ) -> Tuple[str, str, Parameter]:
        """Process an equation CSV file."""
        equ_name = name_without_ext[4:]  # Remove 'equ_' prefix

        # Apply technology filtering
        df = self._filter_to_electricity_technologies(df, electricity_technologies, equ_name)
        df = self._filter_internal_solver_rows(df, equ_name)

        # Determine dimensions
        dims = [col for col in df.columns if col not in ['lvl', 'mrg', 'level', 'marginal', 'unit']]

        metadata = {
            'dims': dims,
            'units': 'unknown',
            'result_type': 'equation'
        }

        param = Parameter(name=equ_name, df=df, metadata=metadata)
        return ('equation', equ_name, param)

    def _filter_to_electricity_technologies(
        self,
        df: pd.DataFrame,
        electricity_technologies: Set[str],
        name: str
    ) -> pd.DataFrame:
        """Filter DataFrame to only electricity-generating technologies."""
        tec_col = self._find_technology_column(df)
        if tec_col and electricity_technologies:
            rows_before = len(df)
            df = df[df[tec_col].isin(electricity_technologies)]
            rows_filtered = rows_before - len(df)
        return df

    def _filter_internal_solver_rows(
        self,
        df: pd.DataFrame,
        name: str
    ) -> pd.DataFrame:
        """Filter out internal solver rows (_res#, _ref#, _cv#, _hist_####)."""
        tec_col = self._find_technology_column(df)
        if tec_col and len(df) > 0:
            rows_before = len(df)
            mask = ~df[tec_col].astype(str).str.match(self.INTERNAL_SOLVER_PATTERN)
            df = df[mask]
            rows_filtered = rows_before - len(df)
            if rows_filtered > 0:
                print(f"DEBUG: Filtered out {rows_filtered} internal solver rows from {name}")
        return df

    def get_load_summary(self, scenario_data: ScenarioData) -> str:
        """
        Get a summary string for loaded data.

        Args:
            scenario_data: The loaded scenario data

        Returns:
            Summary string describing what was loaded
        """
        num_sets = len(scenario_data.sets)
        num_params = len([p for p in scenario_data.parameters.values()
                         if not p.metadata.get('result_type')])
        num_vars = len([p for p in scenario_data.parameters.values()
                       if p.metadata.get('result_type') == 'variable'])
        num_eqs = len([p for p in scenario_data.parameters.values()
                      if p.metadata.get('result_type') == 'equation'])

        parts = [f"{num_sets} sets", f"{num_params} parameters"]
        if num_vars:
            parts.append(f"{num_vars} variables")
        if num_eqs:
            parts.append(f"{num_eqs} equations")

        return ", ".join(parts)
