"""
Input Manager - handles loading and parsing of MESSAGEix Excel input files
"""

import os
import pandas as pd
import numpy as np
import logging
from openpyxl import load_workbook
from typing import Optional, List, Callable, Dict, Any

from core.data_models import ScenarioData, Parameter
from managers.base_data_manager import BaseDataManager
from utils.parsing_strategies import ExcelParser, ParameterParsingStrategy, SetParsingStrategy
from utils.error_handler import ErrorHandler, SafeOperation


class InputManager(BaseDataManager):
    """
    InputManager class for loading and parsing MESSAGEix input Excel files.

    This class handles the complex process of reading MESSAGEix scenario data
    from Excel workbooks, parsing sets and parameters, and providing access
    to the loaded data for analysis and visualization.

    Attributes:
        scenarios: List of loaded ScenarioData objects
        loaded_file_paths: Corresponding file paths for loaded scenarios
    """

    def load_excel_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> ScenarioData:
        """
        Load and parse a MESSAGEix Excel input file.

        This method performs comprehensive validation and parsing of MESSAGEix
        input files, extracting sets, parameters, and metadata.

        Args:
            file_path: Path to the Excel file (.xlsx or .xls format).
                      File must exist and be readable.
            progress_callback: Optional callback function for progress updates.
                             Receives (percentage: int, message: str) parameters.
                             Called at key milestones during loading process.

        Returns:
            ScenarioData object containing parsed sets and parameters.

        Raises:
            FileNotFoundError: If the specified file_path does not exist.
            ValueError: If the file format is invalid or parsing fails.
            PermissionError: If file cannot be read due to permissions.

        Example:
            >>> manager = InputManager()
            >>> def progress(pct, msg): print(f"{pct}%: {msg}")
            >>> scenario = manager.load_excel_file("data.xlsx", progress)
            >>> print(f"Loaded {len(scenario.parameters)} parameters")
        """
        return self.load_file(file_path, progress_callback)

    def _parse_workbook(
        self,
        wb: Any,
        scenario: ScenarioData,
        file_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """
        Parse workbook for input data using Strategy pattern - implements abstract method.

        Args:
            wb: Openpyxl workbook object
            scenario: ScenarioData object to populate
            progress_callback: Optional progress callback function
        """
        # Use ExcelParser with appropriate strategies for input data
        parser = ExcelParser()
        # Replace default strategies with input-specific ones
        parser.strategies = [
            SetParsingStrategy(),
            ParameterParsingStrategy('input')
        ]

        parser.parse_workbook(wb, scenario, file_path, progress_callback)



    # Keep backward compatibility - get_current_scenario is now inherited
    # All other inherited methods from BaseDataManager are available
