"""
MessageIX Scenario Manager

Handles the creation, management, and conversion of MessageIX scenarios from
application ScenarioData objects. Provides interface between the application's
data models and MessageIX's scenario management system.
"""

import os
import tempfile
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from ..config import config, MESSAGEIX_DB_PATH
from ..core.data_models import ScenarioData, Parameter
from ..utils.error_handler import ErrorHandler
from ..managers.logging_manager import logging_manager


class MessageIXScenarioManager:
    """
    Manager for MessageIX scenario operations.

    Handles conversion between application ScenarioData and MessageIX Scenario objects,
    provides scenario creation, cloning, and result extraction capabilities.
    """

    def __init__(self):
        """
        Initialize the MessageIX Scenario Manager.

        Sets up IXMP platform connection and prepares for scenario operations.
        """
        self.ixmp_platform = None
        self._initialize_platform()

    def _initialize_platform(self) -> None:
        """
        Initialize the IXMP platform connection.

        Creates or connects to the MessageIX database platform.
        """
        try:
            import ixmp

            db_path = MESSAGEIX_DB_PATH or str(Path(__file__).parent.parent.parent / 'db' / 'messageix.db')

            # Ensure database directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            # Initialize platform
            self.ixmp_platform = ixmp.Platform(db_path)
            logging_manager.log_info(f"MessageIX platform initialized with database: {db_path}")

        except ImportError as e:
            logging_manager.log_error(f"MessageIX not available: {e}")
            self.ixmp_platform = None
        except Exception as e:
            logging_manager.log_error(f"Failed to initialize MessageIX platform: {e}")
            self.ixmp_platform = None

    def is_available(self) -> bool:
        """
        Check if MessageIX is available and properly configured.

        Returns:
            True if MessageIX is available, False otherwise
        """
        return self.ixmp_platform is not None

    def create_scenario_from_excel(
        self,
        scenario_data: ScenarioData,
        model_name: str = "MESSAGE",
        scenario_name: str = "auto_generated",
        version: str = "new"
    ) -> Optional['ixmp.Scenario']:
        """
        Create a MessageIX scenario from application ScenarioData.

        Args:
            scenario_data: Application ScenarioData object
            model_name: Name of the MessageIX model
            scenario_name: Name for the scenario
            version: Version identifier

        Returns:
            MessageIX Scenario object if successful, None otherwise
        """
        if not self.is_available():
            logging_manager.log_error("MessageIX platform not available")
            return None

        try:
            # Create new scenario
            scenario = self.ixmp_platform.scenario.create(
                model=model_name,
                scenario=scenario_name,
                version=version
            )

            logging_manager.log_info(f"Created MessageIX scenario: {model_name}/{scenario_name}")

            # Populate scenario with data
            success = self._populate_scenario(scenario, scenario_data)

            if success:
                # Commit the scenario
                scenario.commit("Created from MessageIX Data Manager")
                logging_manager.log_info("Scenario committed successfully")
                return scenario
            else:
                logging_manager.log_error("Failed to populate scenario")
                return None

        except Exception as e:
            logging_manager.log_error(f"Failed to create MessageIX scenario: {e}")
            return None

    def _populate_scenario(self, scenario: 'ixmp.Scenario', scenario_data: ScenarioData) -> bool:
        """
        Populate a MessageIX scenario with data from ScenarioData.

        Args:
            scenario: MessageIX scenario to populate
            scenario_data: Application scenario data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add sets first (required for parameters)
            self._add_sets_to_scenario(scenario, scenario_data)

            # Add parameters
            self._add_parameters_to_scenario(scenario, scenario_data)

            return True

        except Exception as e:
            logging_manager.log_error(f"Failed to populate scenario: {e}")
            return False

    def _add_sets_to_scenario(self, scenario: 'ixmp.Scenario', scenario_data: ScenarioData) -> None:
        """
        Add sets from ScenarioData to MessageIX scenario.

        Args:
            scenario: MessageIX scenario
            scenario_data: Application scenario data
        """
        # Standard MESSAGEix sets
        standard_sets = {
            'node': ['World'],  # Simplified - add more as needed
            'technology': [],
            'commodity': [],
            'level': [],
            'year': [],
            'time': ['year'],
            'mode': ['standard'],
        }

        # Extract sets from parameters
        for param_name, param in scenario_data.parameters.items():
            if param.df is not None and not param.df.empty:
                # Infer sets from parameter dimensions
                self._infer_sets_from_parameter(standard_sets, param)

        # Add sets to scenario
        for set_name, elements in standard_sets.items():
            if elements:  # Only add non-empty sets
                try:
                    scenario.add_set(set_name, elements)
                    logging_manager.log_debug(f"Added set '{set_name}' with {len(elements)} elements")
                except Exception as e:
                    logging_manager.log_warning(f"Failed to add set '{set_name}': {e}")

    def _infer_sets_from_parameter(self, sets: Dict[str, List], param: Parameter) -> None:
        """
        Infer set elements from parameter data.

        Args:
            sets: Dictionary of sets to update
            param: Parameter object
        """
        if param.df is None or param.df.empty:
            return

        # Common dimension mappings for MESSAGEix
        dimension_mappings = {
            'node': ['node', 'node_loc', 'node_dest', 'node_origin'],
            'technology': ['technology', 'tec'],
            'commodity': ['commodity', 'comm'],
            'level': ['level'],
            'year': ['year', 'year_vtg', 'year_act'],
            'mode': ['mode'],
        }

        # Check each column for set membership
        for col in param.df.columns:
            col_lower = col.lower()
            for set_name, possible_names in dimension_mappings.items():
                if any(name in col_lower for name in possible_names):
                    # Extract unique values
                    unique_values = param.df[col].dropna().unique().tolist()
                    # Convert to strings and add to set
                    unique_strings = [str(x) for x in unique_values if x is not None]
                    sets[set_name].extend(unique_strings)

        # Remove duplicates
        for set_name in sets:
            sets[set_name] = list(set(sets[set_name]))

    def _add_parameters_to_scenario(self, scenario: 'ixmp.Scenario', scenario_data: ScenarioData) -> None:
        """
        Add parameters from ScenarioData to MessageIX scenario.

        Args:
            scenario: MessageIX scenario
            scenario_data: Application scenario data
        """
        for param_name, param in scenario_data.parameters.items():
            if param.df is not None and not param.df.empty:
                try:
                    # Convert parameter data to MessageIX format
                    param_data = self._convert_parameter_data(param)
                    if param_data is not None:
                        scenario.add_par(param_name, param_data)
                        logging_manager.log_debug(f"Added parameter '{param_name}'")
                except Exception as e:
                    logging_manager.log_warning(f"Failed to add parameter '{param_name}': {e}")

    def _convert_parameter_data(self, param: Parameter) -> Optional[Dict[str, Any]]:
        """
        Convert application Parameter to MessageIX parameter format.

        Args:
            param: Application parameter object

        Returns:
            Dictionary in MessageIX parameter format, or None if conversion fails
        """
        try:
            df = param.df.copy()

            # Remove value column if it exists (MESSAGEix expects it separate)
            value_col = None
            if 'value' in df.columns:
                value_col = 'value'
            elif 'val' in df.columns:
                value_col = 'val'
            else:
                # Assume last column is value
                value_col = df.columns[-1]

            # Extract index columns (all except value)
            index_cols = [col for col in df.columns if col != value_col]

            if not index_cols:
                logging_manager.log_warning(f"No index columns found for parameter {param.name}")
                return None

            # Create MultiIndex from index columns
            df_indexed = df.set_index(index_cols)[value_col]

            # Convert to MessageIX format
            param_data = {
                'value': df_indexed.to_dict(),
                'unit': getattr(param, 'unit', 'dimensionless')
            }

            return param_data

        except Exception as e:
            logging_manager.log_error(f"Failed to convert parameter {param.name}: {e}")
            return None

    def solve_scenario(
        self,
        scenario: 'ixmp.Scenario',
        solver_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Solve a MessageIX scenario.

        Args:
            scenario: MessageIX scenario to solve
            solver_config: Solver configuration options

        Returns:
            Dictionary with solve results and status
        """
        result = {
            'success': False,
            'status': 'failed',
            'message': '',
            'solve_time': None,
            'iterations': None,
            'objective_value': None
        }

        if not self.is_available():
            result['message'] = 'MessageIX platform not available'
            return result

        try:
            import time
            start_time = time.time()

            # Default solver config
            if solver_config is None:
                solver_config = {}

            # Solve the scenario
            scenario.solve(**solver_config)

            solve_time = time.time() - start_time

            # Check solution status
            if hasattr(scenario, 'var') and len(scenario.var_list()) > 0:
                result['success'] = True
                result['status'] = 'optimal'
                result['solve_time'] = solve_time
                result['message'] = 'Scenario solved successfully'

                # Try to get objective value (if available)
                try:
                    # This is model-specific and may need adjustment
                    if 'OBJ' in scenario.var_list():
                        obj_values = scenario.var('OBJ')
                        if obj_values:
                            result['objective_value'] = float(list(obj_values.values())[0])
                except:
                    pass

                logging_manager.log_info(f"Scenario solved successfully in {solve_time:.2f} seconds")
            else:
                result['message'] = 'No solution found'
                logging_manager.log_warning("Scenario solve completed but no variables found")

        except Exception as e:
            result['message'] = f"Solve failed: {str(e)}"
            logging_manager.log_error(f"Scenario solve failed: {e}")

        return result

    def export_results(self, scenario: 'ixmp.Scenario') -> Dict[str, Any]:
        """
        Export results from a solved MessageIX scenario.

        Args:
            scenario: Solved MessageIX scenario

        Returns:
            Dictionary with results data
        """
        results = {
            'variables': {},
            'equations': {},
            'parameters': {},
            'metadata': {}
        }

        if not self.is_available():
            return results

        try:
            # Export variables
            for var_name in scenario.var_list():
                try:
                    var_data = scenario.var(var_name)
                    if var_data is not None:
                        results['variables'][var_name] = var_data.to_series().to_dict() if hasattr(var_data, 'to_series') else dict(var_data)
                except Exception as e:
                    logging_manager.log_warning(f"Failed to export variable {var_name}: {e}")

            # Export equations (if available)
            if hasattr(scenario, 'equ_list'):
                for equ_name in scenario.equ_list():
                    try:
                        equ_data = scenario.equ(equ_name)
                        if equ_data is not None:
                            results['equations'][equ_name] = equ_data.to_series().to_dict() if hasattr(equ_data, 'to_series') else dict(equ_data)
                    except Exception as e:
                        logging_manager.log_warning(f"Failed to export equation {equ_name}: {e}")

            # Export parameters (if available)
            if hasattr(scenario, 'par_list'):
                for par_name in scenario.par_list():
                    try:
                        par_data = scenario.par(par_name)
                        if par_data is not None:
                            results['parameters'][par_name] = par_data.to_series().to_dict() if hasattr(par_data, 'to_series') else dict(par_data)
                    except Exception as e:
                        logging_manager.log_warning(f"Failed to export parameter {par_name}: {e}")

            # Add metadata
            results['metadata'] = {
                'model': scenario.model,
                'scenario': scenario.scenario,
                'version': scenario.version,
                'has_solution': len(results['variables']) > 0
            }

            logging_manager.log_info(f"Exported {len(results['variables'])} variables, {len(results['equations'])} equations")

        except Exception as e:
            logging_manager.log_error(f"Failed to export results: {e}")

        return results

    def clone_scenario(
        self,
        scenario: 'ixmp.Scenario',
        new_name: str,
        keep_solution: bool = False
    ) -> Optional['ixmp.Scenario']:
        """
        Clone a MessageIX scenario.

        Args:
            scenario: Scenario to clone
            new_name: Name for the new scenario
            keep_solution: Whether to keep the solution in the clone

        Returns:
            New cloned scenario, or None if cloning fails
        """
        if not self.is_available():
            return None

        try:
            cloned = scenario.clone(new_name, keep_solution=keep_solution)
            logging_manager.log_info(f"Cloned scenario to: {new_name}")
            return cloned
        except Exception as e:
            logging_manager.log_error(f"Failed to clone scenario: {e}")
            return None

    def delete_scenario(self, scenario: 'ixmp.Scenario') -> bool:
        """
        Delete a MessageIX scenario.

        Args:
            scenario: Scenario to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            return False

        try:
            scenario.remove()
            logging_manager.log_info(f"Deleted scenario: {scenario.scenario}")
            return True
        except Exception as e:
            logging_manager.log_error(f"Failed to delete scenario: {e}")
            return False

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """
        List all available scenarios in the platform.

        Returns:
            List of scenario information dictionaries
        """
        if not self.is_available():
            return []

        try:
            scenarios = []
            for model_scenarios in self.ixmp_platform.scenario.list():
                scenarios.extend(model_scenarios)
            return scenarios
        except Exception as e:
            logging_manager.log_error(f"Failed to list scenarios: {e}")
            return []

    def close(self) -> None:
        """
        Close the MessageIX platform connection.
        """
        if self.ixmp_platform:
            try:
                self.ixmp_platform.close()
                self.ixmp_platform = None
                logging_manager.log_info("MessageIX platform closed")
            except Exception as e:
                logging_manager.log_error(f"Error closing MessageIX platform: {e}")
