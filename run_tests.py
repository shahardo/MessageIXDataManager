#!/usr/bin/env python3
"""
Test runner for MessageIX Data Manager
Runs pytest with proper configuration and environment setup
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


def main():
    """Run the test suite"""
    print("MessageIX Data Manager - Test Runner")
    print("=" * 50)

    # Get project root directory
    project_root = Path(__file__).parent.absolute()

    # Check if we're in the right directory
    if not (project_root / "src").exists():
        print("ERROR: Please run this script from the project root directory")
        sys.exit(1)

    # Check if virtual environment exists and is activated
    venv_path = project_root / "env"
    if not venv_path.exists():
        print("WARNING: Virtual environment not found at 'env/'")
        print("Installing dependencies and creating environment...")

        # Try to create and activate venv, then install dependencies
        try:
            # Create virtual environment
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

            # Install dependencies
            pip_exe = venv_path / "Scripts" / "pip.exe" if platform.system() == "Windows" else venv_path / "bin" / "pip"
            subprocess.run([str(pip_exe), "install", "-r", str(project_root / "requirements.txt")], check=True)

            print("SUCCESS: Virtual environment created and dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to set up environment: {e}")
            sys.exit(1)

    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("pytest not found. Installing...")

        # Install pytest
        pip_exe = venv_path / "Scripts" / "pip.exe" if platform.system() == "Windows" else venv_path / "bin" / "pip"
        try:
            subprocess.run([str(pip_exe), "install", "pytest", "pytest-qt"], check=True)
            print("SUCCESS: pytest installed")
        except subprocess.CalledProcessError:
            print("ERROR: Failed to install pytest")
            sys.exit(1)

    # Set up environment for pytest
    env = os.environ.copy()

    # Set headless environment variable to skip GUI tests
    env["HEADLESS"] = "true"

    # Ensure Python path includes src directory
    python_path = str(project_root / "src")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = python_path + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = python_path

    # Add virtual environment Python to PATH if not already there
    venv_python = venv_path / "Scripts" / "python.exe" if platform.system() == "Windows" else venv_path / "bin" / "python"
    if str(venv_python.parent) not in env.get("PATH", ""):
        env["PATH"] = str(venv_python.parent) + os.pathsep + env.get("PATH", "")

    print(f"Project root: {project_root}")
    print(f"Python path: {env.get('PYTHONPATH', 'Not set')}")
    print(f"Running tests in: {project_root / 'tests'}")
    print(f"HEADLESS mode: {env.get('HEADLESS', 'false')}")
    print()

    # Run pytest
    try:
        # Change to project root directory
        os.chdir(project_root)

        # Run pytest with configuration (pytest.ini is now in tests/ directory)
        cmd = [
            str(venv_python),
            "-m", "pytest",
            "tests/",
            "-c", "tests/pytest.ini",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--disable-warnings"
        ]

        print(f"Executing: {' '.join(cmd)}")
        print("-" * 50)

        result = subprocess.run(cmd, env=env, cwd=project_root)

        print("-" * 50)
        if result.returncode == 0:
            print("SUCCESS: All tests passed!")
        else:
            print(f"FAILED: Tests failed with exit code: {result.returncode}")
            print("Check the output above for details")

        return result.returncode

    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"ERROR: Error running tests: {e}")
        return 1


def show_help():
    """Show help information"""
    print("MessageIX Data Manager - Test Runner")
    print()
    print("This script runs the test suite for the MessageIX Data Manager project.")
    print()
    print("Requirements:")
    print("- Python 3.8+")
    print("- Virtual environment in 'env/' directory")
    print("- Dependencies installed (see requirements.txt)")
    print()
    print("Usage:")
    print("  python run_tests.py")
    print()
    print("The script will:")
    print("- Set up the virtual environment if needed")
    print("- Install pytest if missing")
    print("- Run all tests in the tests/ directory")
    print("- Provide detailed output and exit codes")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_help()
        sys.exit(0)

    exit_code = main()
    sys.exit(exit_code)
