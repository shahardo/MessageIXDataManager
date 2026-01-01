"""
Tests for Python syntax checking and module importing
Ensures all Python source files are syntactically valid and can be imported
"""

import os
import sys
import ast
import importlib.util
import pytest
from pathlib import Path


class TestPythonSyntaxAndImports:
    """Test cases for Python syntax validation and import testing"""

    @pytest.fixture
    def project_root(self):
        """Get the project root directory"""
        return Path(__file__).parent.parent

    @pytest.fixture
    def src_directory(self, project_root):
        """Get the src directory"""
        return project_root / "src"

    def get_all_python_files(self, directory):
        """Recursively find all Python files in a directory"""
        python_files = []
        for root, dirs, files in os.walk(directory):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        return python_files

    def test_all_python_files_syntax_valid(self, src_directory):
        """Test that all Python files have valid syntax"""
        python_files = self.get_all_python_files(src_directory)

        assert len(python_files) > 0, "No Python files found in src directory"

        syntax_errors = []

        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source_code = f.read()

                # Parse the AST to check syntax
                ast.parse(source_code, filename=str(py_file))

            except SyntaxError as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'error': str(e),
                    'line': e.lineno,
                    'offset': e.offset
                })
            except UnicodeDecodeError as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'error': f"Unicode decode error: {e}",
                    'line': None,
                    'offset': None
                })
            except Exception as e:
                syntax_errors.append({
                    'file': str(py_file),
                    'error': f"Unexpected error: {e}",
                    'line': None,
                    'offset': None
                })

        if syntax_errors:
            error_msg = "Syntax errors found in Python files:\n"
            for error in syntax_errors:
                error_msg += f"  {error['file']}"
                if error['line']:
                    error_msg += f" (line {error['line']})"
                error_msg += f": {error['error']}\n"
            pytest.fail(error_msg)

    def test_all_modules_can_be_imported(self, project_root, src_directory):
        """Test that all Python modules can be imported without errors"""
        python_files = self.get_all_python_files(src_directory)

        # Add src directory to Python path
        if str(src_directory) not in sys.path:
            sys.path.insert(0, str(src_directory))

        import_errors = []

        for py_file in python_files:
            # Skip __init__.py files for now (they might not be directly importable)
            if py_file.name == '__init__.py':
                continue

            # Convert file path to module path
            relative_path = py_file.relative_to(src_directory)
            module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')

            try:
                # Try to import the module
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None:
                    import_errors.append({
                        'module': module_name,
                        'file': str(py_file),
                        'error': "Could not create module spec"
                    })
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            except ImportError as e:
                import_errors.append({
                    'module': module_name,
                    'file': str(py_file),
                    'error': f"Import error: {e}"
                })
            except Exception as e:
                import_errors.append({
                    'module': module_name,
                    'file': str(py_file),
                    'error': f"Unexpected error during import: {e}"
                })

        if import_errors:
            error_msg = "Import errors found in Python modules:\n"
            for error in import_errors:
                error_msg += f"  {error['module']} ({error['file']}): {error['error']}\n"
            pytest.fail(error_msg)

    def test_src_directory_structure(self, src_directory):
        """Test that src directory has expected structure"""
        assert src_directory.exists(), "src directory must exist"
        assert src_directory.is_dir(), "src must be a directory"

        # Check that we have at least some Python files
        python_files = list(src_directory.rglob("*.py"))
        assert len(python_files) > 0, "src directory must contain Python files"

        # Check for main entry point
        main_py = src_directory / "main.py"
        assert main_py.exists(), "main.py must exist in src directory"

    def test_no_duplicate_module_names(self, src_directory):
        """Test that there are no duplicate module names (case-insensitive on Windows)"""
        python_files = self.get_all_python_files(src_directory)

        # Group files by module name (relative path without extension, normalized)
        modules_by_name = {}

        for py_file in python_files:
            relative_path = py_file.relative_to(src_directory)
            module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')

            # Normalize for case-insensitive comparison on Windows
            normalized_name = module_name.lower() if os.name == 'nt' else module_name

            if normalized_name not in modules_by_name:
                modules_by_name[normalized_name] = []

            modules_by_name[normalized_name].append(str(py_file))

        # Check for duplicates
        duplicates = []
        for module_name, files in modules_by_name.items():
            if len(files) > 1:
                duplicates.append({
                    'module': module_name,
                    'files': files
                })

        if duplicates:
            error_msg = "Duplicate module names found:\n"
            for dup in duplicates:
                error_msg += f"  Module '{dup['module']}':\n"
                for file in dup['files']:
                    error_msg += f"    - {file}\n"
            pytest.fail(error_msg)

    def test_all_init_files_exist(self, src_directory):
        """Test that all directories containing Python files have __init__.py"""
        python_files = self.get_all_python_files(src_directory)

        missing_inits = []

        # Get all directories that contain Python files
        dirs_with_py = set()
        for py_file in python_files:
            # Add all parent directories
            current = py_file.parent
            while current != src_directory.parent:  # Stop at src parent
                if current.is_relative_to(src_directory):
                    dirs_with_py.add(current)
                current = current.parent

        # Check each directory has __init__.py
        for directory in dirs_with_py:
            init_file = directory / "__init__.py"
            if not init_file.exists():
                missing_inits.append(str(directory))

        if missing_inits:
            error_msg = "Missing __init__.py files in directories:\n"
            for dir_path in sorted(missing_inits):
                error_msg += f"  - {dir_path}\n"
            pytest.fail(error_msg)
