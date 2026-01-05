# Test Debugging Guide

This guide explains how to debug and run tests for the MessageIX Data Manager project.

## VS Code Debugging Configurations

The `.vscode/launch.json` file contains several debugging configurations:

### 1. **Python: Debug All Tests**
- Runs all tests in debug mode
- Stops at breakpoints in test code and application code
- Useful for debugging test failures or understanding test flow

### 2. **Python: Debug Current Test File**
- Debugs the currently open test file
- Automatically detects the active test file in the editor

### 3. **Python: Debug Specific Test**
- Debugs a specific test function or class
- Select the test name in the editor before running
- Allows debugging individual test methods

### 4. **Python: Run Tests with Coverage**
- Runs tests with coverage reporting
- Generates HTML coverage reports in `htmlcov/`
- Shows which lines are covered and which are not

## How to Use VS Code Debugging

### Setting Breakpoints
1. Open a test file or source file
2. Click in the gutter (left margin) next to the line number to set a breakpoint
3. The breakpoint will appear as a red dot

### Running Debug Configurations
1. Open the Run and Debug panel (Ctrl+Shift+D)
2. Select a debug configuration from the dropdown
3. Click the green play button or press F5

### Debugging Test Failures
1. Set breakpoints in your test code or the code being tested
2. Run the "Python: Debug All Tests" configuration
3. When a test fails, execution will stop at the breakpoint
4. Use the debug toolbar to step through code, inspect variables, etc.

## Command Line Debugging

### Using the Debug Script
```bash
# Run all tests
python debug_tests.py

# Run specific test file
python debug_tests.py tests/test_data_models.py

# Run tests matching a pattern
python debug_tests.py -k "test_parameter"

# Run with coverage
python debug_tests.py --coverage

# Debug mode (stop on first failure with pdb)
python debug_tests.py --debug
```

### Direct pytest Commands
```bash
# Basic test run
pytest tests/ -v

# Debug specific test
pytest tests/test_data_models.py::TestParameter::test_parameter_creation -v -s --pdb

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Stop on first failure
pytest tests/ -x --tb=short
```

## Common Debugging Scenarios

### 1. **Test Failing Due to Logic Error**
- Set breakpoint in the failing test method
- Step through the test to see what's happening
- Inspect variable values in the debug panel

### 2. **Application Code Not Working as Expected**
- Set breakpoint in the application code being tested
- Run the test in debug mode
- Check if the application code receives correct inputs

### 3. **File/IO Issues**
- Check temporary file creation/deletion
- Verify file paths and permissions
- Use the `--no-capture` option to see print statements

### 4. **Database/Logging Issues**
- Use in-memory databases for testing
- Check database connections are properly closed
- Verify logging handlers are cleaned up

## Debugging Tips

### **VS Code Specific**
- Use the "Variables" panel to inspect object state
- Use the "Watch" panel to monitor specific expressions
- Use conditional breakpoints for complex scenarios
- Use the "Call Stack" to understand execution flow

### **Python Debugging**
- Use `print()` statements for quick debugging
- Use `pdb.set_trace()` for interactive debugging
- Check exception tracebacks carefully
- Use assertions to validate assumptions

### **Test-Specific**
- Use `--tb=short` for concise error messages
- Use `-v` for verbose output showing each test
- Use `-k` to run only relevant tests during debugging
- Use `--pdb` to drop into debugger on test failures

## Environment Setup

Make sure your development environment is properly configured:

1. **Virtual Environment**: Use the project's virtual environment
2. **Dependencies**: Install all test dependencies
3. **Python Path**: VS Code should use the virtual environment's Python
4. **Working Directory**: Set to the project root

## Troubleshooting

### **Import Errors**
- Check that `PYTHONPATH` includes the `src` directory
- Verify the virtual environment is activated
- Ensure all dependencies are installed

### **Breakpoint Not Hit**
- Make sure the breakpoint is in executable code
- Check that the correct debug configuration is selected
- Verify the file is being executed (use print statements)

### **Test Discovery Issues**
- Check `pytest.ini` configuration
- Ensure test files follow the `test_*.py` naming convention
- Verify test classes start with `Test` and methods with `test_`

### **Coverage Not Working**
- Install `pytest-cov` package
- Check that source files are in the `src` directory
- Verify the `--cov=src` parameter is used correctly

## Performance Tips

- Use `--tb=short` for faster test runs during development
- Run only specific test files when debugging
- Use `-k` to filter tests during iterative debugging
- Consider using `--maxfail=1` to stop after first failure

## Integration with CI/CD

The debugging configurations are designed to work with automated testing:
- Coverage reports can be integrated with CI tools
- Test results can be parsed by CI systems
- Debug information helps with failure analysis

For more information about pytest and debugging, see the [pytest documentation](https://docs.pytest.org/) and [VS Code Python debugging guide](https://code.visualstudio.com/docs/python/debugging).
