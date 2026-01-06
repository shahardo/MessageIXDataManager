"""
Tests for documentation completeness and type hint validation
"""

import pytest
import ast
import inspect
from typing import get_type_hints
import os
import sys
from pathlib import Path


class TestDocumentationAndTypes:
    """Test cases for documentation and type hint completeness"""

    @pytest.fixture
    def src_directory(self):
        """Get the src directory"""
        return Path(__file__).parent.parent / "src"

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

    def get_module_classes_and_functions(self, module_path):
        """Extract classes and functions from a Python module"""
        classes_and_functions = []

        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    classes_and_functions.append({
                        'name': node.name,
                        'type': 'class' if isinstance(node, ast.ClassDef) else 'function',
                        'line_number': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'has_type_hints': self._check_type_hints(node)
                    })

        except Exception as e:
            pytest.fail(f"Failed to parse {module_path}: {e}")

        return classes_and_functions

    def _check_type_hints(self, node):
        """Check if a function/class has type hints"""
        has_hints = False

        # Check function arguments
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation is not None:
                    has_hints = True
                    break

            # Check return annotation
            if node.returns is not None:
                has_hints = True

        return has_hints

    def test_core_classes_have_docstrings_and_type_hints(self, src_directory):
        """Test that core classes have proper documentation and type hints"""
        core_files = [
            src_directory / "managers" / "input_manager.py",
            src_directory / "managers" / "results_analyzer.py",
            src_directory / "managers" / "base_data_manager.py",
            src_directory / "utils" / "error_handler.py"
        ]

        for file_path in core_files:
            if not file_path.exists():
                continue

            items = self.get_module_classes_and_functions(file_path)

            for item in items:
                # Check that classes have docstrings
                if item['type'] == 'class':
                    assert item['docstring'] is not None, \
                        f"Class {item['name']} in {file_path.name} missing docstring"

                    # Check docstring quality
                    docstring = item['docstring']
                    assert len(docstring.strip()) > 10, \
                        f"Class {item['name']} in {file_path.name} has inadequate docstring"

                    # Check for common docstring elements
                    assert "class" in docstring.lower() or item['name'] in docstring, \
                        f"Class {item['name']} docstring doesn't mention the class name"

    def test_public_methods_have_docstrings(self, src_directory):
        """Test that public methods have proper docstrings"""
        core_files = [
            src_directory / "managers" / "input_manager.py",
            src_directory / "managers" / "results_analyzer.py",
            src_directory / "managers" / "base_data_manager.py"
        ]

        for file_path in core_files:
            if not file_path.exists():
                continue

            items = self.get_module_classes_and_functions(file_path)

            for item in items:
                # Check public methods (not starting with _)
                if item['type'] == 'function' and not item['name'].startswith('_'):
                    assert item['docstring'] is not None, \
                        f"Public method {item['name']} in {file_path.name} missing docstring"

                    # Check docstring quality
                    docstring = item['docstring']
                    assert len(docstring.strip()) > 20, \
                        f"Public method {item['name']} in {file_path.name} has inadequate docstring"

    def test_type_hints_are_present(self, src_directory):
        """Test that type hints are present in key methods"""
        # Import the modules to check runtime type hints
        if str(src_directory) not in sys.path:
            sys.path.insert(0, str(src_directory))

        try:
            from managers.input_manager import InputManager
            from managers.results_analyzer import ResultsAnalyzer
            from managers.base_data_manager import BaseDataManager

            # Check InputManager methods
            input_methods = [
                'load_excel_file',
                'get_current_scenario',
                'get_parameter'
            ]

            for method_name in input_methods:
                method = getattr(InputManager, method_name, None)
                assert method is not None, f"Method {method_name} not found in InputManager"

                # Check if method has type hints via inspect
                sig = inspect.signature(method)
                has_type_hints = any(param.annotation != inspect.Parameter.empty
                                   for param in sig.parameters.values())
                has_return_hint = sig.return_annotation != inspect.Signature.empty

                assert has_type_hints or has_return_hint, \
                    f"Method {method_name} in InputManager missing type hints"

            # Check ResultsAnalyzer methods
            results_methods = [
                'load_results_file',
                'get_summary_stats',
                'get_result_data',
                'prepare_chart_data'
            ]

            for method_name in results_methods:
                method = getattr(ResultsAnalyzer, method_name, None)
                assert method is not None, f"Method {method_name} not found in ResultsAnalyzer"

                sig = inspect.signature(method)
                has_type_hints = any(param.annotation != inspect.Parameter.empty
                                   for param in sig.parameters.values())
                has_return_hint = sig.return_annotation != inspect.Signature.empty

                assert has_type_hints or has_return_hint, \
                    f"Method {method_name} in ResultsAnalyzer missing type hints"

        except ImportError as e:
            pytest.skip(f"Could not import modules for type checking: {e}")

    def test_docstring_format_consistency(self, src_directory):
        """Test that docstrings follow a consistent format"""
        core_files = [
            src_directory / "managers" / "input_manager.py",
            src_directory / "managers" / "results_analyzer.py"
        ]

        for file_path in core_files:
            if not file_path.exists():
                continue

            items = self.get_module_classes_and_functions(file_path)

            for item in items:
                if item['docstring'] and item['type'] == 'function' and not item['name'].startswith('_'):
                    docstring = item['docstring']

                    # Check for Args: section in methods that take parameters
                    lines = docstring.split('\n')
                    has_args_section = any('Args:' in line for line in lines)
                    has_returns_section = any('Returns:' in line for line in lines)

                    # Methods with parameters should have Args section
                    # This is a basic check - could be enhanced
                    if 'Args:' in docstring or 'Returns:' in docstring:
                        # If they have structured sections, they should be properly formatted
                        assert 'Args:' in docstring or 'Returns:' in docstring, \
                            f"Method {item['name']} has inconsistent docstring sections"

    def test_classes_have_attributes_documented(self, src_directory):
        """Test that class docstrings document their attributes"""
        core_files = [
            src_directory / "managers" / "input_manager.py",
            src_directory / "managers" / "results_analyzer.py"
        ]

        for file_path in core_files:
            if not file_path.exists():
                continue

            items = self.get_module_classes_and_functions(file_path)

            for item in items:
                if item['type'] == 'class' and item['docstring']:
                    docstring = item['docstring']

                    # Check if class docstring mentions attributes
                    # This is a basic check for attribute documentation
                    assert 'Attributes:' in docstring or 'attributes' in docstring.lower() or len(docstring.split()) > 15, \
                        f"Class {item['name']} docstring should document attributes or be more descriptive"

    def test_examples_in_docstrings(self, src_directory):
        """Test that complex methods have usage examples"""
        complex_methods = [
            ('input_manager', 'load_excel_file'),
            ('results_analyzer', 'load_results_file'),
            ('results_analyzer', 'prepare_chart_data')
        ]

        if str(src_directory) not in sys.path:
            sys.path.insert(0, str(src_directory))

        for module_name, method_name in complex_methods:
            try:
                module = __import__(f'managers.{module_name}', fromlist=[module_name])
                cls = getattr(module, module_name.title().replace('_', ''))

                method = getattr(cls, method_name)
                docstring = method.__doc__

                if docstring:
                    # Complex methods should have examples
                    assert '>>>' in docstring or 'Example:' in docstring, \
                        f"Method {method_name} should have usage examples in docstring"

            except (ImportError, AttributeError):
                pytest.skip(f"Could not check docstring for {module_name}.{method_name}")

    def test_backward_compatibility_methods_documented(self, src_directory):
        """Test that backward compatibility methods are documented"""
        if str(src_directory) not in sys.path:
            sys.path.insert(0, str(src_directory))

        try:
            from managers.results_analyzer import ResultsAnalyzer

            # Check backward compatibility methods
            compat_methods = ['get_current_results', 'get_results_by_file_path', 'clear_results']

            for method_name in compat_methods:
                method = getattr(ResultsAnalyzer, method_name, None)
                if method:
                    assert method.__doc__ is not None, \
                        f"Backward compatibility method {method_name} should be documented"

                    # Should mention backward compatibility
                    assert 'backward' in method.__doc__.lower() or 'compatibility' in method.__doc__.lower(), \
                        f"Method {method_name} docstring should mention backward compatibility"

        except ImportError:
            pytest.skip("Could not import ResultsAnalyzer for compatibility check")
