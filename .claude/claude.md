# MessageIX Data Manager

A PyQt5 desktop application for viewing, editing, and managing MESSAGEix energy modeling input files and results.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python src/main.py

# Run tests
python run_tests.py
# or
pytest tests/
```

## Project Structure

```
src/
├── main.py                 # Application entry point
├── core/                   # Data models and schemas
│   ├── data_models.py      # Parameter, Scenario, ScenarioData classes
│   └── message_ix_schema.py # MESSAGEix parameter definitions
├── managers/               # Business logic layer
│   ├── base_data_manager.py      # Abstract base with Observer pattern
│   ├── input_manager.py          # Load/parse input Excel files
│   ├── results_analyzer.py       # Load/parse results Excel files
│   ├── solver_manager.py         # MESSAGEix solver execution
│   ├── session_manager.py        # Application state persistence
│   ├── parameter_manager.py      # Parameter validation/creation
│   ├── commands.py               # Command pattern for undo/redo
│   └── file_handlers.py          # High-level file operations
├── ui/                     # User interface (PyQt5)
│   ├── main_window.py            # Main application window
│   ├── components/               # Reusable UI components
│   │   ├── parameter_tree_widget.py   # Parameter tree navigation
│   │   ├── data_display_widget.py     # Data table with editing
│   │   ├── chart_widget.py            # Plotly chart visualization
│   │   ├── file_navigator_widget.py   # File browser
│   │   └── add_parameter_dialog.py    # Add parameter dialog
│   ├── controllers/              # Event handlers
│   │   └── edit_handler.py       # Cell editing logic
│   └── *.ui                      # Qt Designer UI files
└── utils/                  # Utilities
    ├── parsing_strategies.py     # Strategy pattern for parsing
    ├── parameter_factory.py      # Factory pattern for parameters
    └── data_transformer.py       # Data transformation utilities
```

## Architecture

### Design Patterns Used

1. **Observer Pattern**: `BaseDataManager` notifies observers of data changes
2. **Strategy Pattern**: `ParsingStrategy` subclasses for different Excel sheet types
3. **Factory Pattern**: `ParameterFactory` with registry for parameter creation
4. **Command Pattern**: `UndoManager` with command objects for undo/redo
5. **Composition Pattern**: `MainWindow` composes UI components (not inheritance)

### Data Flow

```
Excel File → InputManager → ParsingStrategy → Parameter objects
                         → Scenario object
                         → ScenarioData container
```

### Key Classes

- **Parameter**: Wraps DataFrame with metadata (units, description, dimensions)
- **Scenario**: Represents a MESSAGEix scenario with input/results files
- **ScenarioData**: Container for sets, parameters, mappings
- **UndoManager**: Manages undo/redo stack with Command objects

## Coding Conventions

### Common practices
- Don't apply changes that are not required - keep changes minimal,
- Whenever possible, use .ui xml files instead of programatically creating UI objects, 
- Write test for new code, if applicable,
- Comment generously.
- if possible, when trying to identify a bug, first write a test that fails on the bug, then fix the problem, and test again to ensure the bug was fixed.

### Python Style
- Use type hints for function signatures
- Docstrings for public methods
- Follow PEP 8 naming conventions
- Use f-strings for string formatting

### PyQt5 Patterns
- Use signals/slots for component communication
- Connect signals in `_connect_signals()` methods
- Keep UI logic in controllers, not widgets
- Use composition over inheritance for UI components

### File Organization
- One class per file for major components
- Group related utilities in single files
- Keep UI files (`.ui`) alongside Python counterparts

## Common Tasks

### Adding a New Parameter Type

1. Add definition to `src/core/message_ix_schema.py`
2. Update `ParameterManager.get_parameter_definition()`
3. Add to appropriate category in `PARAMETER_CATEGORIES`

### Adding a New Command (for undo/redo)

1. Create class in `src/managers/commands.py` inheriting from `Command`
2. Implement `do()` and `undo()` methods
3. Execute via `undo_manager.execute(command)`

```python
class MyCommand(Command):
    def __init__(self, widget, data):
        self.widget = widget
        self.data = data
        self.old_data = None

    def do(self):
        self.old_data = self.widget.get_data()
        self.widget.set_data(self.data)

    def undo(self):
        self.widget.set_data(self.old_data)
```

### Adding a New UI Component

1. Create widget class in `src/ui/components/`
2. Use composition in `MainWindow` to add component
3. Connect signals in `MainWindow._connect_signals()`
4. Optionally create `.ui` file with Qt Designer

### Adding a New Parsing Strategy

1. Create class in `src/utils/parsing_strategies.py` inheriting from `ParsingStrategy`
2. Implement `parse()` method
3. Register in appropriate manager

## Testing

You are running on Windows 11 pwsh.
Assume all packages are installed. No need to pip install
Allways use venv 'env': 
```bash
# Activate virtual environment
env/scripts/activate
```

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_input_manager.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v tests/
```

### Test Fixtures (conftest.py)
- `sample_dataframe`: Basic test DataFrame
- `mock_scenario`: Mock Scenario object
- `qtbot`: PyQt5 test helper

## Important Files

| File | Purpose |
|------|---------|
| `src/main.py` | Application entry point |
| `src/ui/main_window.py` | Main window orchestration |
| `src/core/data_models.py` | Core data structures |
| `src/managers/commands.py` | Undo/redo command objects |
| `src/managers/input_manager.py` | Input file parsing |
| `src/ui/components/data_display_widget.py` | Table display with editing |
| `docs/devplan.md` | Development plan and task tracking |

## MESSAGEix Integration

This application works with MESSAGEix energy modeling framework:
- Input files: Excel workbooks with sets, parameters, mappings
- Results files: Excel workbooks with solver output variables
- Parameters follow MESSAGEix schema (see `message_ix_schema.py`)

### Parameter Categories
- Technology Input/Output (input, output, capacity factors)
- Costs (inv_cost, fix_cost, var_cost)
- Bounds (bound_activity_up/lo, bound_capacity_up/lo)
- Emissions (emission_factor, bound_emission)
- Resources (resource_volume, resource_cost)
- Demand (demand, peak_load_factor)

## Dependencies

- **PyQt5**: GUI framework
- **pandas**: Data manipulation
- **openpyxl**: Excel file handling
- **plotly**: Interactive charts
- **pytest**: Testing framework
- **pytest-qt**: PyQt5 testing utilities
