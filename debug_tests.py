#!/usr/bin/env python3
"""
Debug script for running tests with enhanced debugging capabilities.

This script provides utilities for:
- Running tests with debugging enabled
- Running specific test files or functions
- Running tests with coverage reporting
- Interactive debugging mode

Usage:
    python debug_tests.py                    # Run all tests
    python debug_tests.py tests/test_data_models.py  # Run specific file
    python debug_tests.py -k "test_parameter"        # Run tests matching pattern
    python debug_tests.py --coverage                # Run with coverage
    python debug_tests.py --debug                    # Run in debug mode (break on first failure)
"""

import sys
import os
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description='Debug test runner for MessageIX Data Manager')
    parser.add_argument('test_path', nargs='?', default='tests/',
                       help='Path to test file or directory (default: tests/)')
    parser.add_argument('-k', '--keyword', help='Only run tests matching keyword expression')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage reporting')
    parser.add_argument('--debug', action='store_true', help='Debug mode - stop on first failure')
    parser.add_argument('--no-capture', action='store_true', help='Disable output capture')
    parser.add_argument('--tb', choices=['short', 'long', 'line', 'native', 'no'],
                       default='short', help='Traceback format')

    args = parser.parse_args()

    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']

    # Add test path
    cmd.append(args.test_path)

    # Add options
    if args.verbose or args.keyword:
        cmd.append('-v')

    if args.keyword:
        cmd.extend(['-k', args.keyword])

    if args.coverage:
        cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term-missing'])

    if args.debug:
        cmd.append('-x')  # Stop on first failure
        cmd.append('--pdb')  # Start debugger on failure

    if args.no_capture:
        cmd.append('--capture=no')

    cmd.extend(['--tb', args.tb])

    # Set environment
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'src')

    print(f"Running: {' '.join(cmd)}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    print("-" * 50)

    # Run the command
    try:
        result = subprocess.run(cmd, env=env, cwd=os.path.dirname(__file__))
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
