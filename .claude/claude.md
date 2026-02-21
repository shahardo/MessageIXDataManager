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
│   ├── message_ix_schema.py # MESSAGEix parameter definitions, codelists, tooltips
│   ├── user_preferences.py  # Shared user preferences (UserPreferences QObject)
│   └── view_state.py        # ViewState and ViewStateManager classes
├── analysis/               # Domain-specific result analyzers (created in refactoring guide 5)
│   ├── __init__.py               # Package init re-exporting all analyzers
│   ├── base_analyzer.py          # ScenarioDataWrapper + BaseAnalyzer with shared helpers
│   ├── electricity_analyzer.py   # Generation, capacity, LCOE, cost breakdown, dashboard metrics
│   ├── emissions_analyzer.py     # GHG emissions by type, sector, fuel
│   ├── energy_balance_analyzer.py # Primary/final energy, trade, feedstock, oil derivatives
│   ├── fuel_analyzer.py          # Gas, coal, oil, biomass supply and use
│   ├── sector_analyzer.py        # Buildings, industry, transport energy use
│   └── price_analyzer.py         # Energy prices by level, sector, fuel
├── managers/               # Business logic layer
│   ├── base_data_manager.py      # Abstract base with Observer pattern
│   ├── input_manager.py          # Load/parse input Excel files
│   ├── results_analyzer.py       # Load/parse results Excel files (pure data loader, < 300 lines)
│   ├── results_postprocessor.py  # Facade/orchestrator delegating to src/analysis/ domain analyzers
│   ├── solver_manager.py         # MESSAGEix solver execution
│   ├── session_manager.py        # Application state persistence
│   ├── parameter_manager.py      # Parameter validation/creation
│   ├── commands.py               # Command pattern for undo/redo
│   ├── file_handlers.py          # High-level file operations
│   ├── data_file_manager.py      # ZIP/CSV data loading
│   ├── data_export_manager.py    # Data export functionality
│   ├── table_undo_manager.py     # TableUndoManager (UndoManager alias)
│   └── logging_manager.py        # Logging configuration
├── ui/                     # User interface (PyQt5)
│   ├── main_window.py            # Main application window
│   ├── dashboard.py              # Results dashboard (legacy)
│   ├── dashboard_chart_mixin.py  # Shared chart rendering for dashboards
│   ├── postprocessing_dashboard.py # Postprocessed results dashboard
│   ├── results_file_dashboard.py # Results file dashboard
│   ├── input_file_dashboard.py   # Input file overview dashboard
│   ├── signal_registry.py        # SignalRegistry for centralized signal-slot management
│   ├── ui_styler.py              # UI styling utilities
│   ├── navigator.py              # Navigation utilities
│   ├── components/               # Reusable UI components
│   │   ├── parameter_tree_widget.py   # Parameter tree navigation
│   │   ├── data_display_widget.py     # Data table with editing, pivoting, deciphering
│   │   ├── chart_widget.py            # Plotly chart visualization with legend tooltips
│   │   ├── file_navigator_widget.py   # File browser
│   │   ├── add_parameter_dialog.py    # Add parameter dialog
│   │   ├── column_header_view.py      # ColumnHeaderView with signals
│   │   ├── table_formatter.py         # CellStyle, TableFormatter, DIMENSION_DISPLAY_NAMES
│   │   ├── base_dashboard.py          # BaseDashboard with web view setup
│   │   └── find_widget.py             # Find/search widget
│   ├── controllers/              # Event handlers
│   │   ├── edit_handler.py       # Cell editing logic
│   │   ├── file_dialog_controller.py # File dialog controller
│   │   └── find_controller.py    # Find/search controller
│   └── *.ui                      # Qt Designer UI files
└── utils/                  # Utilities
    ├── parsing_strategies.py     # Strategy pattern for parsing
    ├── parameter_factory.py      # Factory pattern for parameters
    ├── data_transformer.py       # Data transformation utilities
    ├── technology_classifier.py  # Technology grouping and energy-level classification
    ├── error_handler.py          # Error handling utilities
    ├── parameter_utils.py        # Parameter utility functions
    └── ui_logger.py              # UILogger adapter for unified logging
```

## Architecture

### Design Patterns Used

1. **Observer Pattern**: `BaseDataManager` notifies observers of data changes
2. **Strategy Pattern**: `ParsingStrategy` subclasses for different Excel sheet types
3. **Factory Pattern**: `ParameterFactory` with registry for parameter creation
4. **Command Pattern**: `UndoManager` with command objects for undo/redo
5. **Composition Pattern**: `MainWindow` composes UI components (not inheritance)
6. **Shared Preferences**: `UserPreferences` QObject shared between `DataDisplayWidget` and `PostprocessingDashboard` for synchronized year-range filtering
7. **Mixin Pattern**: `DashboardChartMixin` for shared chart rendering across dashboards

### Data Flow

Two file types are supported:

**Data file** (`.zip` archive of CSVs) — loaded by `DataFileManager`:
```
data.zip (contains set_*.csv, par_*.csv, var_*.csv, equ_*.csv)
  → DataFileManager._load_zipped_csv_data()
    → set_*.csv  → ScenarioData sets (input)
    → par_*.csv  → Parameter objects with long-format DataFrames (input)
    → var_*.csv  → Parameter objects marked as variables (results)
    → equ_*.csv  → Parameter objects marked as equations (results)
```

**Results file** (`.xlsx` workbook with wide tables) — loaded by `ResultsAnalyzer`:
```
results.xlsx (sheets with pre-pivoted wide-format tables)
  → ResultsAnalyzer.load_results_file()
    → ParsingStrategy subclasses → Parameter objects
    → ResultsPostprocessor → Derived metrics (LCOE, generation, emissions)
```

**Input file** (`.xlsx` workbook) — loaded by `InputManager`:
```
input.xlsx (sheets: sets, parameters, mappings)
  → InputManager → ParsingStrategy → Parameter objects
                 → Scenario object → ScenarioData container
```

**Display pipeline for var_* variables**:
```
var_* Parameter → TechnologyClassifier.filter_by_energy_level()
               → TechnologyClassifier.apply_technology_grouping()
               → DataDisplayWidget (pivot, filter, decipher)
               → ChartWidget (Plotly visualization)
```

### Key Classes

- **Parameter**: Wraps DataFrame with metadata (units, description, dimensions)
- **Scenario**: Represents a MESSAGEix scenario with input/results files
- **ScenarioData**: Container for sets, parameters, mappings
- **UndoManager**: Manages undo/redo stack with Command objects
- **UserPreferences**: Shared QObject holding `min_year`, `max_year`, `limit_enabled` with a `changed` signal
- **DashboardChartMixin**: Shared chart rendering methods (stacked bar, pie, placeholder) used by `ResultsFileDashboard` and `PostprocessingDashboard`
- **ResultsPostprocessor**: Thin facade/orchestrator — delegates to domain analyzers in `src/analysis/`, then converts shared `results` dict to `Parameter` objects
- **BaseAnalyzer**: Base class for all domain analyzers; holds shared state (`msg`, `scenario`, `plotyrs`, `results`) and provides helpers (`_group`, `_model_output`, `_add_history`, `_multiply_df`, etc.)
- **ElectricityAnalyzer**: Electricity generation, capacity, LCOE, cost breakdown, dashboard metrics (static methods `calculate_dashboard_metrics`, `calculate_electricity_cost_breakdown`)
- **TechnologyClassifier**: Maps technologies to energy levels, provides grouping (coal, gas, emissions, etc.), and filters var_* data by energy level with dynamic emission detection
- **InputFileDashboard**: Inherits `BaseDashboard`; shows commodities, technologies, years, regions, and parameter coverage matrices
- **ResultsFileDashboard**: Inherits `DashboardChartMixin, BaseDashboard`; shows result metrics and charts

### Results Variable Display (var_*)

When displaying result variables (var_ACT, var_CAP, var_EMISS, etc.):

1. **Energy Level Filter**: `TechnologyClassifier.build_level_technology_map()` discovers levels from input scenario. For "emissions" level, also dynamically matches technologies via `_EMISSION_TECH_PATTERNS` regex
2. **Technology Grouping**: `TechnologyClassifier.apply_technology_grouping()` aggregates technologies by prefix/suffix patterns (e.g., `coal_ppl + coal_adv → "Coal"`)
3. **Column Classification** (`_identify_columns` in `DataDisplayWidget`):
   - Pivot columns: `technology`, `commodity`, `type_tec`, `category`, `relation`
   - Filter columns: `node`, `mode`, `level`, `emission`, `sector`, etc.
   - Value column: `lvl` (for results) or `value` (for inputs)
4. **Aggregation**: Results pivot uses `sum` aggregation; input pivot uses first-value

### Name Deciphering

- `get_code_display_names()` in `message_ix_schema.py` returns combined dict of code→name mappings from `MESSAGE_IX_COMMODITIES` and `MESSAGE_IX_TECHNOLOGIES`
- `generate_legend_tooltip_script()` injects JavaScript into Plotly charts for hover tooltips on legend items
- "Decipher Names" checkbox in advanced display controls applies to both table headers/cells and chart legends

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

### Adding MESSAGEix Codelists

1. Add entries to `MESSAGE_IX_COMMODITIES` or `MESSAGE_IX_TECHNOLOGIES` in `message_ix_schema.py`
2. Update `COMMODITY_CATEGORIES` or `TECHNOLOGY_CATEGORIES` as needed
3. Names are auto-discovered by `get_code_display_names()` for deciphering

### Adding Technology Groups

1. Add group entry to `TECHNOLOGY_GROUPS` in `src/utils/technology_classifier.py`
2. For emission-related patterns, also update `_EMISSION_TECH_PATTERNS` regex
3. Suffix patterns (starting with `_`) are checked before prefix patterns

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

### Known Test Issues
- `test_data_models.py::test_mark_modified` - Pre-existing failure (test expects modified set empty after clear, but add_parameter marks it)
- Full test suite may crash during Qt/WebEngine teardown (not related to test logic)

## Important Files

| File | Purpose |
|------|---------|
| `src/main.py` | Application entry point |
| `src/ui/main_window.py` | Main window orchestration |
| `src/core/data_models.py` | Core data structures |
| `src/core/message_ix_schema.py` | MESSAGEix schema, codelists (commodities, technologies), tooltip scripts |
| `src/managers/commands.py` | Undo/redo command objects |
| `src/managers/input_manager.py` | Input file parsing |
| `src/managers/results_postprocessor.py` | Thin facade — orchestrates `src/analysis/` domain analyzers |
| `src/analysis/base_analyzer.py` | `ScenarioDataWrapper` + `BaseAnalyzer` with shared calculation helpers |
| `src/analysis/electricity_analyzer.py` | Electricity generation, LCOE, cost breakdown, dashboard metrics |
| `src/ui/components/data_display_widget.py` | Table display with editing, pivoting, name deciphering |
| `src/ui/components/chart_widget.py` | Plotly chart visualization with legend tooltips |
| `src/ui/input_file_dashboard.py` | Input file overview dashboard |
| `src/ui/dashboard_chart_mixin.py` | Shared chart rendering for dashboards |
| `src/ui/postprocessing_dashboard.py` | Postprocessed results dashboard |
| `src/utils/technology_classifier.py` | Technology grouping, energy-level classification, emission detection |
| `src/core/user_preferences.py` | Shared user preferences (UserPreferences) |
| `docs/devplan.md` | Development plan and task tracking |

## MESSAGEix Integration

This application works with MESSAGEix energy modeling framework:
- Input files: Excel workbooks with sets, parameters, mappings
- Results files: Excel workbooks with solver output variables
- Parameters follow MESSAGEix schema (see `message_ix_schema.py`)
- Commodities and technologies follow official codelists

### Parameter Categories
- Technology Input/Output (input, output, capacity factors)
- Costs (inv_cost, fix_cost, var_cost)
- Bounds (bound_activity_up/lo, bound_capacity_up/lo)
- Emissions (emission_factor, bound_emission)
- Resources (resource_volume, resource_cost)
- Demand (demand, peak_load_factor)

### Technology Groups (for var_* display)
- Energy: Coal, Natural Gas, Nuclear, Hydro, Biomass, Wind, Solar, Geothermal, etc.
- Emissions: CO2/CH4/N2O/SO2/SF6/CF4/HFC/NOx emissions, total emissions, emission mitigation
- Trade: imports, exports
- Infrastructure: Refinery, Hydrogen, Storage, Synfuels, Electricity

## Dependencies

- **PyQt5**: GUI framework
- **pandas**: Data manipulation
- **openpyxl**: Excel file handling
- **plotly**: Interactive charts
- **pytest**: Testing framework
- **pytest-qt**: PyQt5 testing utilities
