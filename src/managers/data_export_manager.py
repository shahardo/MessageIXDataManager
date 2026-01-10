"""
Data Export Manager - Handles saving modified MESSAGEix data back to Excel files

Provides functionality to export modified scenario data back to Excel format.
"""

import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment
import os
from typing import Dict, List, Optional, Any
from core.data_models import ScenarioData, Parameter


class DataExportManager:
    """Manager for exporting MESSAGEix scenario data to Excel files"""

    def __init__(self):
        self.export_formats = {
            'xlsx': self._export_to_xlsx,
            'xls': self._export_to_xlsx  # Use xlsx format for both
        }

    def save_scenario(self, scenario: ScenarioData, file_path: str,
                     modified_only: bool = True) -> bool:
        """
        Save scenario data to Excel file

        Args:
            scenario: ScenarioData object to save
            file_path: Path to save the file
            modified_only: If True, only save modified parameters

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower().lstrip('.')

            if ext not in self.export_formats:
                ext = 'xlsx'  # Default to xlsx

            # Call appropriate export method
            export_method = self.export_formats.get(ext, self._export_to_xlsx)
            return export_method(scenario, file_path, modified_only)

        except Exception as e:
            print(f"Error saving scenario: {str(e)}")
            return False

    def _export_to_xlsx(self, scenario: ScenarioData, file_path: str,
                       modified_only: bool = True) -> bool:
        """Export scenario to Excel format"""
        try:
            # Create workbook
            workbook = openpyxl.Workbook()

            # Remove default sheet
            workbook.remove(workbook.active)

            # Export parameters
            parameters_to_export = {}
            if modified_only:
                # Only export modified parameters
                for param_name in scenario.modified:
                    param = scenario.get_parameter(param_name)
                    if param:
                        parameters_to_export[param_name] = param
            else:
                # Export all parameters
                parameters_to_export = scenario.parameters

            # Group parameters by category for better organization
            param_groups = self._group_parameters_by_category(parameters_to_export)

            for group_name, params in param_groups.items():
                # Create worksheet for this group
                sheet_name = self._sanitize_sheet_name(group_name)
                worksheet = workbook.create_sheet(title=sheet_name)

                # Export parameters in this group
                self._export_parameter_group(worksheet, params, group_name)

            # Save workbook
            workbook.save(file_path)
            return True

        except Exception as e:
            print(f"Error exporting to Excel: {str(e)}")
            return False

    def _group_parameters_by_category(self, parameters: Dict[str, Parameter]) -> Dict[str, Dict[str, Parameter]]:
        """Group parameters by category for better Excel organization"""
        groups = {}

        # Define category mappings (similar to parameter tree categorization)
        category_keywords = {
            'Economic': ['cost', 'price', 'demand', 'supply', 'revenue', 'profit', 'investment'],
            'Capacity': ['capacity', 'factor', 'efficiency', 'availability'],
            'Technical': ['duration', 'lifetime', 'construction', 'operation'],
            'Environmental': ['emission', 'carbon', 'co2', 'pollutant'],
            'Operational': ['operation', 'maintenance', 'fuel', 'consumption'],
            'Bounds': ['bound', 'limit', 'minimum', 'maximum'],
            'Sets': ['set', 'category', 'technology', 'commodity', 'region'],
        }

        # Default group for uncategorized parameters
        groups['Parameters'] = {}

        for param_name, param in parameters.items():
            # Try to categorize the parameter
            categorized = False
            param_name_lower = param_name.lower()

            for category, keywords in category_keywords.items():
                if any(keyword in param_name_lower for keyword in keywords):
                    if category not in groups:
                        groups[category] = {}
                    groups[category][param_name] = param
                    categorized = True
                    break

            # If not categorized, put in default group
            if not categorized:
                groups['Parameters'][param_name] = param

        return groups

    def _sanitize_sheet_name(self, name: str) -> str:
        """Sanitize sheet name to be Excel-compatible"""
        # Excel sheet names cannot contain: \ / ? * [ ]
        # and cannot be longer than 31 characters
        invalid_chars = ['\\', '/', '?', '*', '[', ']']
        sanitized = name

        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')

        # Truncate to 31 characters
        return sanitized[:31]

    def _export_parameter_group(self, worksheet, parameters: Dict[str, Parameter], group_name: str):
        """Export a group of parameters to a worksheet"""
        current_row = 1

        # Add group header
        worksheet.cell(row=current_row, column=1, value=f"{group_name} Parameters")
        worksheet.cell(row=current_row, column=1).font = Font(bold=True, size=14)
        current_row += 2

        for param_name, param in parameters.items():
            # Parameter header
            worksheet.cell(row=current_row, column=1, value=f"Parameter: {param_name}")
            worksheet.cell(row=current_row, column=1).font = Font(bold=True, size=12)
            current_row += 1

            # Add metadata if available
            if param.metadata:
                metadata_text = []
                if 'units' in param.metadata:
                    metadata_text.append(f"Units: {param.metadata['units']}")
                if 'desc' in param.metadata:
                    metadata_text.append(f"Description: {param.metadata['desc']}")

                if metadata_text:
                    worksheet.cell(row=current_row, column=1, value="; ".join(metadata_text))
                    worksheet.cell(row=current_row, column=1).font = Font(italic=True)
                    current_row += 1

            # Export DataFrame
            df = param.df
            if not df.empty:
                # Write DataFrame to worksheet
                for r, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=current_row):
                    for c, value in enumerate(row, start=1):
                        cell = worksheet.cell(row=r, column=c, value=value)
                        # Style header row
                        if r == current_row:
                            cell.font = Font(bold=True)
                            cell.alignment = Alignment(horizontal='center')

                current_row += len(df) + 3  # Add spacing between parameters
            else:
                worksheet.cell(row=current_row, column=1, value="(No data)")
                current_row += 2

    def has_modified_data(self, scenario: ScenarioData) -> bool:
        """Check if scenario has modified data"""
        return bool(scenario.modified)

    def get_modified_parameters_count(self, scenario: ScenarioData) -> int:
        """Get count of modified parameters"""
        return len(scenario.modified)

    def clear_modified_flags(self, scenario: ScenarioData):
        """Clear all modified flags after successful save"""
        scenario.modified.clear()
        scenario.change_history.clear()
