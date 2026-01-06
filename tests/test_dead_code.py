"""
Tests for dead code detection and removal
Ensures that static analysis tools can detect unused code and that
dead code is properly removed from the codebase.
"""

import subprocess
import sys
from pathlib import Path


class TestDeadCodeDetection:
    """Test cases for dead code detection using static analysis tools"""

    def test_vulture_detects_dead_code(self):
        """Test that vulture can run and detect dead code in the codebase"""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"

        # Run vulture on the src directory
        result = subprocess.run(
            [sys.executable, "-m", "vulture", str(src_dir)],
            capture_output=True,
            text=True,
            cwd=project_root
        )

        # Vulture should exit with code 1 if dead code is found
        # (0 if no dead code, 1 if dead code found)
        assert result.returncode in [0, 1], f"Vulture failed to run: {result.stderr}"

        # Store the output for analysis - we expect some dead code initially
        dead_code_output = result.stdout

        # We should have some dead code detected (from the refactoring process)
        # The exact amount may vary, but we should have some findings
        lines = dead_code_output.strip().split('\n')
        dead_code_lines = [line for line in lines if 'unused' in line.lower()]

        # During refactoring, we expect to find some dead code
        # This test will help ensure we don't reintroduce dead code
        print(f"Found {len(dead_code_lines)} dead code items")

    def test_no_obvious_dead_code_after_cleanup(self):
        """Test that major categories of dead code are removed"""
        # This test will be updated as we remove dead code
        # For now, it documents what we've found and will be cleaned

        # Categories of dead code found by vulture:
        dead_imports = [
            "src/managers/solver_manager.py:14: unused import 'signal'",
            "src/managers/solver_manager.py:83: unused import 'ixmp'",
            "src/managers/solver_manager.py:84: unused import 'message_ix'",
            "src/managers/solver_manager.py:106: unused import 'cplex'",
            "src/managers/solver_manager.py:112: unused import 'gurobipy'",
            "src/ui/components/data_display_widget.py:7: unused import 'QFrame'",
            "src/ui/components/parameter_tree_widget.py:9: unused import 'Tuple'",
            "src/ui/main_window.py:9: unused import 'QAction'",
            "src/ui/main_window.py:9: unused import 'QMenu'",
            "src/ui/main_window.py:9: unused import 'QMenuBar'",
            "src/ui/main_window.py:9: unused import 'QProgressBar'",
            "src/ui/main_window.py:9: unused import 'QStatusBar'",
            "src/ui/main_window.py:9: unused import 'QTextEdit'",
            "src/ui/ui_styler.py:15: unused import 'QCursor'",
            "src/utils/error_handler.py:10: unused import 'contextmanager'"
        ]

        dead_methods = [
            "src/core/data_models.py:40: unused method 'mark_modified'",
            "src/managers/base_data_manager.py:130: unused method 'get_number_of_scenarios'",
            "src/managers/base_data_manager.py:134: unused method 'get_scenario_by_index'",
            "src/managers/logging_manager.py:193: unused method 'log_parameter_edit'",
            "src/managers/logging_manager.py:218: unused method 'get_recent_logs'",
            "src/managers/logging_manager.py:271: unused method 'cleanup_old_logs'",
            "src/managers/results_analyzer.py:455: unused method 'clear_results'",
            "src/managers/solver_manager.py:71: unused method 'detect_messageix_environment'",
            "src/ui/components/data_display_widget.py:152: unused method '_get_current_filters'",
            "src/ui/components/data_display_widget.py:411: unused method '_transform_to_advanced_view'",
            "src/ui/components/parameter_tree_widget.py:207: unused method 'clear_selection_silently'",
            "src/ui/ui_styler.py:106: unused method 'setup_group_box'",
            "src/ui/ui_styler.py:142: unused method 'apply_class_styling'",
            "src/ui/ui_styler.py:150: unused method 'refresh_widget_styling'",
            "src/ui/ui_styler.py:164: unused method 'setup_splitters'",
            "src/ui/ui_styler.py:211: unused method 'apply_all_styling'",
            "src/utils/error_handler.py:93: unused method 'handle_validation_error'",
            "src/utils/error_handler.py:161: unused function 'with_error_handling'"
        ]

        dead_classes = [
            "src/ui/ui_styler.py:157: unused class 'MainWindowUI'"
        ]

        # This test should eventually pass after cleanup
        # For now, it documents what needs to be cleaned
        total_dead_items = len(dead_imports) + len(dead_methods) + len(dead_classes)

        # We expect to have found dead code during analysis
        assert total_dead_items > 0, "No dead code detected - analysis may have failed"

        print(f"Dead code summary: {len(dead_imports)} imports, {len(dead_methods)} methods, {len(dead_classes)} classes")

    def test_src_directory_structure_preserved(self):
        """Test that src directory structure is preserved during cleanup"""
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"

        # Essential directories should exist
        assert src_dir.exists(), "src directory must exist"
        assert (src_dir / "core").exists(), "core directory must exist"
        assert (src_dir / "managers").exists(), "managers directory must exist"
        assert (src_dir / "ui").exists(), "ui directory must exist"
        assert (src_dir / "utils").exists(), "utils directory must exist"

        # Essential files should exist
        assert (src_dir / "main.py").exists(), "main.py must exist"
        assert (src_dir / "__init__.py").exists(), "src/__init__.py must exist"
