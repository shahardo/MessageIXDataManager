# MessageIX Data Manager

A PyQt5 desktop application for energy systems modelers to load, view, edit, and solve MESSAGEix scenarios, and explore their results interactively.

## Features

- **Excel Integration**: Load and parse MESSAGEix Excel input files and solver result files
- **Scenario Management**: Manage multiple named scenarios, each with its own input, data, and results files
- **Parameter Tree**: Browse all parameters by category in a hierarchical tree; search by name
- **Interactive Table**: View and edit parameters in a pivot table with filtering, grouping, and undo/redo
- **Interactive Charts**: Plotly-based charts with legend tooltips and name deciphering
- **Solver Integration**: One-click MESSAGEix solve via GAMS (GLPK/CPLEX/Gurobi); real-time console output; warning summary with auto-fix suggestions
- **Results Analysis**: Domain-specific postprocessed dashboards (electricity, emissions, energy balance, fuels, sectors, prices)
- **Data Export**: Export parameters and results to CSV/Excel

## Quick Start

### Prerequisites
- Python 3.8+
- Java 11+ (required for ixmp/GAMS bridge when running the solver)
- GAMS installation with GLPK (for solver execution)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd MessageIXDataManager

# Create and activate virtual environment
python -m venv env
# Windows:
env\Scripts\activate
# Unix/Mac:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_input_manager.py -v

# Run with coverage
pytest --cov=src tests/
```

## Project Structure

```
MessageIXDataManager/
├── src/
│   ├── main.py                   # Application entry point
│   ├── core/                     # Data models and schemas
│   │   ├── data_models.py        # Parameter, Scenario, ScenarioData classes
│   │   ├── message_ix_schema.py  # MESSAGEix parameter definitions, codelists, tooltips
│   │   ├── user_preferences.py   # Shared user preferences (year-range filter)
│   │   └── view_state.py         # ViewState and ViewStateManager
│   ├── analysis/                 # Domain-specific result analyzers
│   │   ├── base_analyzer.py      # ScenarioDataWrapper + BaseAnalyzer
│   │   ├── electricity_analyzer.py
│   │   ├── emissions_analyzer.py
│   │   ├── energy_balance_analyzer.py
│   │   ├── fuel_analyzer.py
│   │   ├── sector_analyzer.py
│   │   └── price_analyzer.py
│   ├── managers/                 # Business logic
│   │   ├── input_manager.py      # Parse input Excel files
│   │   ├── data_file_manager.py  # Load ZIP/CSV and Excel (var_/equ_ sheets)
│   │   ├── results_analyzer.py   # Load wide-format results Excel
│   │   ├── results_postprocessor.py  # Orchestrate domain analyzers
│   │   ├── results_exporter.py   # Export solved scenario to Excel
│   │   ├── solver_manager.py     # GAMS/solver detection and command building
│   │   ├── solver_worker.py      # QThread subprocess runner
│   │   ├── run_messageix.py      # Standalone solver script (subprocess)
│   │   ├── scenario_loader.py    # Load Excel into ixmp Platform
│   │   ├── warning_analyzer.py   # Parse solver warnings, suggest fixes
│   │   ├── session_manager.py    # Session persistence
│   │   ├── parameter_manager.py  # Parameter validation/creation
│   │   ├── commands.py           # Undo/redo command objects
│   │   └── data_export_manager.py
│   ├── ui/                       # PyQt5 user interface
│   │   ├── main_window.py        # Main window
│   │   ├── input_file_dashboard.py
│   │   ├── results_file_dashboard.py
│   │   ├── postprocessing_dashboard.py
│   │   ├── dashboard_chart_mixin.py
│   │   ├── components/
│   │   │   ├── parameter_tree_widget.py
│   │   │   ├── data_display_widget.py
│   │   │   ├── chart_widget.py
│   │   │   ├── file_navigator_widget.py
│   │   │   ├── warning_summary_dialog.py
│   │   │   └── find_widget.py
│   │   └── controllers/
│   │       ├── edit_handler.py
│   │       ├── file_dialog_controller.py
│   │       └── find_controller.py
│   └── utils/
│       ├── parsing_strategies.py
│       ├── parameter_factory.py
│       ├── technology_classifier.py
│       └── data_transformer.py
├── tests/                        # pytest test suite (~591 tests)
├── assets/                       # Icons and resources
├── files/                        # Sample data files
├── docs/                         # Project documentation
├── requirements.txt
├── pytest.ini
└── run_tests.py
```

## Workflow

### Loading Input Data
1. Use the file navigator (left panel) to create a scenario or open an existing one
2. Load an input Excel file (`.xlsx`) — sets and parameters are parsed automatically
3. Browse parameters in the tree, view/edit them in the table, and visualize in charts

### Editing Parameters
- Click any cell in the table to edit inline
- Use Ctrl+Z / Ctrl+Y for undo/redo
- Modified parameters are highlighted; save changes back to Excel via File menu

### Running the Solver
1. Open the **Model** menu → **Run Solver**
2. Select the LP solver (GLPK, CPLEX, or Gurobi — detected automatically from GAMS installation)
3. Monitor real-time output in the console
4. On completion, solver results (`var_ACT`, `var_CAP`, `var_EMISS`, etc.) are automatically loaded into the parameter tree and shown in the file navigator

### Analyzing Results
- **Parameter Tree**: Navigate to any `var_*` or `equ_*` variable; view data as pivoted table and chart
- **Postprocessing Dashboard**: Click the dashboard icon for electricity, emissions, energy balance, and cost breakdowns computed from the raw solver variables

## Architecture

The application follows a layered architecture:

- **UI Layer**: PyQt5 widgets and controllers; Plotly charts rendered in `QWebEngineView`
- **Logic Layer**: Managers handle business logic (parsing, solving, analysis, export)
- **Data Layer**: Excel I/O via openpyxl/pandas; ixmp HSQLDB for solver execution; JSON session files

Key patterns: Observer (data change notifications), Strategy (Excel sheet parsing), Factory (parameter creation), Command (undo/redo).

## Development

### Setting up Development Environment
```bash
python -m venv env
env\Scripts\activate          # Windows
pip install -r requirements.txt
```

### Running Tests
```bash
# Specific test file (preferred — run only what you changed)
pytest tests/test_input_manager.py -v

# Full suite
pytest tests/ -v --tb=short
```

### Debugging
- Use F5 in VS Code to launch with the debugger (configuration in `.vscode/launch.json`)
- The integrated terminal auto-activates the `env` virtual environment

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt5 | GUI framework |
| pandas | Data manipulation |
| openpyxl | Excel I/O |
| plotly | Interactive charts |
| pytest / pytest-qt | Testing |
| ixmp / message-ix | Solver integration (optional) |
| jpype1 | Java bridge for ixmp (Java 11+ required) |

## License

[Add license information here]
