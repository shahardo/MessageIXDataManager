# MessageIX Data Manager

A cross-platform desktop application for energy systems modelers to load, view, edit, and solve message_ix scenarios.

## Features

- **Excel Integration**: Load and parse message_ix Excel input files
- **Interactive Visualization**: View parameters in categorized tree and table formats
- **Data Validation**: Built-in validation for loaded scenarios
- **Solver Integration**: Execute model solves with real-time output
- **Results Analysis**: Load and analyze solution results

## Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (automatically created)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd MessageIXDataManager

# Run the application
python src/main.py
```

### Running Tests
```bash
# Run all tests
python run_tests.py

# Or run tests directly with pytest
python -m pytest tests/
```

## Project Structure

```
MessageIXDataManager/
├── src/                    # Source code
│   ├── core/              # Data models
│   ├── managers/          # Business logic managers
│   └── ui/                # User interface components
├── tests/                 # Test suite
├── assets/                # Icons and resources
├── files/                 # Sample data files
├── requirements.txt       # Python dependencies
├── pytest.ini            # Test configuration
├── run_tests.py          # Test runner script
└── README.md             # This file
```

## Development

### Setting up Development Environment
```bash
# Create virtual environment (if not exists)
python -m venv env

# Activate environment
# Windows:
env\Scripts\activate
# Unix/Mac:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_input_manager.py -v

# Run with coverage
python -m pytest --cov=src tests/
```

### Debugging
- Use F5 in VS Code/Cursor to start debugging
- Breakpoints can be set in any Python file
- Debug configuration is set up in `.vscode/launch.json`

## Architecture

The application follows a layered architecture:

- **UI Layer**: PyQt5-based interface with tree views, tables, and charts
- **Logic Layer**: Managers handle business logic (input parsing, solving, validation)
- **Data Layer**: SQLite storage for metadata, Excel files for model data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python run_tests.py`
4. Ensure all tests pass
5. Submit a pull request

## License

[Add license information here]

## Contact

[Add contact information here]
