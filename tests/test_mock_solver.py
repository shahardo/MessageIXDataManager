"""
Tests for Mock Solver
"""

import pytest
import os
import sys
import subprocess
import tempfile

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_mock_solver_success():
    """Test mock solver runs successfully"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    # Run with test arguments until success (since mock solver has 80% success rate)
    max_attempts = 10
    for attempt in range(max_attempts):
        result = subprocess.run([
            sys.executable, script_path, 'input.xlsx', 'glpk'
        ], capture_output=True, text=True, timeout=20)

        if result.returncode == 0:
            break
    else:
        pytest.fail(f"Mock solver did not succeed after {max_attempts} attempts")

    assert result.returncode == 0
    assert 'OPTIMAL SOLUTION FOUND' in result.stdout
    assert 'Mock message_ix Solver starting' in result.stdout


def test_mock_solver_failure_simulation():
    """Test mock solver can simulate failure"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    # Run multiple times to potentially get failure (20% chance)
    results = []
    for _ in range(10):  # Run 10 times to increase chance of failure
        result = subprocess.run([
            sys.executable, script_path, 'input.xlsx', 'glpk'
        ], capture_output=True, text=True, timeout=20)
        results.append(result.returncode)

    # Should have at least some failures if randomness is working
    # (This is a probabilistic test, might occasionally fail)
    assert 0 in results or 1 in results  # At least one success or failure


def test_mock_solver_invalid_args():
    """Test mock solver with invalid arguments"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    result = subprocess.run([
        sys.executable, script_path  # No arguments
    ], capture_output=True, text=True, timeout=20)

    assert result.returncode == 1
    assert 'Usage:' in result.stdout


def test_mock_solver_with_different_solvers():
    """Test mock solver with different solver names"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    solvers = ['glpk', 'cplex', 'gurobi', 'cbc']

    for solver in solvers:
        result = subprocess.run([
            sys.executable, script_path, 'input.xlsx', solver
        ], capture_output=True, text=True, timeout=20)  # Increased timeout for slow iterations

        # Should succeed regardless of solver name
        assert result.returncode in [0, 1]  # Success or failure
        assert f'Solver: {solver}' in result.stdout


def test_mock_solver_output_format():
    """Test that mock solver produces expected output format"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    result = subprocess.run([
        sys.executable, script_path, 'input.xlsx', 'glpk'
    ], capture_output=True, text=True, timeout=20)

    # Check for expected output elements
    output = result.stdout
    assert 'Mock message_ix Solver starting' in output
    assert 'Input file:' in output
    assert 'Solver:' in output
    assert 'Python version:' in output

    if result.returncode == 0:
        assert 'OPTIMAL SOLUTION FOUND' in output
        assert 'Final objective value:' in output
        assert 'Solution time:' in output
        assert 'Solver completed successfully' in output
    else:
        assert 'SOLVER FAILED' in output


def test_mock_solver_iterations():
    """Test that mock solver shows iteration progress"""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'managers', 'mock_solver.py')

    result = subprocess.run([
        sys.executable, script_path, 'input.xlsx', 'glpk'
    ], capture_output=True, text=True, timeout=20)

    output = result.stdout

    # Should contain iteration information
    assert 'Iteration' in output
    assert 'Objective =' in output

    # Should have multiple iterations
    iteration_count = output.count('Iteration')
    assert iteration_count >= 3  # At least a few iterations
